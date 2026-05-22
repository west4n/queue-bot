#!/bin/bash
set -e

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${GREEN}=== Восстановление базы данных из backup ===${NC}"

# Переходим в директорию проекта
cd /opt/pogran-bot

# Проверяем аргументы
if [ -z "$1" ]; then
    echo -e "${YELLOW}Использование: $0 <путь_к_backup_файлу>${NC}"
    echo -e "${YELLOW}Пример: $0 docs/pogran_bot_backup_20251116_190123.dump${NC}"
    exit 1
fi

BACKUP_FILE="$1"

# Проверяем наличие backup файла
if [ ! -f "$BACKUP_FILE" ]; then
    echo -e "${RED}ОШИБКА: Файл backup не найден: $BACKUP_FILE${NC}"
    exit 1
fi

echo -e "${BLUE}Используемый backup файл: $BACKUP_FILE${NC}"

# Останавливаем бота перед восстановлением БД
echo -e "${YELLOW}Остановка сервиса бота...${NC}"
sudo systemctl stop pogran-bot.service || true

# Проверяем, запущен ли PostgreSQL
if ! docker-compose ps postgres | grep -q "Up"; then
    echo -e "${YELLOW}PostgreSQL не запущен. Запускаем...${NC}"
    docker-compose up -d postgres
    
    # Ждем, пока PostgreSQL будет готов
    echo -e "${YELLOW}Ожидание готовности PostgreSQL...${NC}"
    timeout=60
    counter=0
    until docker-compose exec -T postgres pg_isready -U postgres > /dev/null 2>&1; do
        if [ $counter -ge $timeout ]; then
            echo -e "${RED}ОШИБКА: PostgreSQL не запустился за $timeout секунд${NC}"
            exit 1
        fi
        sleep 1
        counter=$((counter + 1))
    done
    echo -e "${GREEN}PostgreSQL готов${NC}"
fi

# Предупреждение о перезаписи данных
echo -e "${RED}⚠️  ВНИМАНИЕ: Все существующие данные в базе будут удалены!${NC}"
echo -e "${YELLOW}Вы уверены, что хотите продолжить? (yes/no)${NC}"
read -r confirmation

if [ "$confirmation" != "yes" ]; then
    echo -e "${YELLOW}Операция отменена${NC}"
    exit 0
fi

# Удаляем существующую базу данных и создаем новую
echo -e "${YELLOW}Удаление существующей базы данных...${NC}"
docker-compose exec -T postgres psql -U postgres -c "DROP DATABASE IF EXISTS pogran_bot;" || true
docker-compose exec -T postgres psql -U postgres -c "CREATE DATABASE pogran_bot;"

# Восстанавливаем базу данных из backup
echo -e "${YELLOW}Восстановление базы данных из backup...${NC}"
docker-compose exec -T postgres pg_restore -U postgres -d pogran_bot --clean --if-exists < "$BACKUP_FILE"

if [ $? -eq 0 ]; then
    echo -e "${GREEN}База данных успешно восстановлена${NC}"
else
    echo -e "${RED}ОШИБКА: Не удалось восстановить базу данных${NC}"
    exit 1
fi

# Активируем виртуальное окружение
source venv/bin/activate

# Применяем миграции Alembic до последней версии
echo -e "${YELLOW}Применение миграций Alembic до последней версии...${NC}"
alembic upgrade head

if [ $? -eq 0 ]; then
    echo -e "${GREEN}Миграции успешно применены${NC}"
else
    echo -e "${RED}ОШИБКА: Не удалось применить миграции${NC}"
    exit 1
fi

# Запускаем бота
echo -e "${YELLOW}Запуск сервиса бота...${NC}"
sudo systemctl start pogran-bot.service
sudo systemctl status pogran-bot.service --no-pager

echo -e "${GREEN}=== Восстановление базы данных завершено успешно ===${NC}"
echo -e "${GREEN}Бот запущен и готов к работе${NC}"


