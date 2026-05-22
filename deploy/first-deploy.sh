#!/bin/bash
set -e

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}=== Первый деплой: Восстановление базы данных ===${NC}"

# Переходим в директорию проекта
cd /opt/pogran-bot

# Проверяем наличие backup файла
BACKUP_FILE="docs/pogran_bot_backup_20251117_190829.dump"
if [ ! -f "$BACKUP_FILE" ]; then
    echo -e "${RED}ОШИБКА: Файл backup не найден: $BACKUP_FILE${NC}"
    exit 1
fi

# Проверяем, что PostgreSQL запущен
echo -e "${YELLOW}Проверка подключения к PostgreSQL...${NC}"
if ! docker-compose exec -T postgres pg_isready -U postgres > /dev/null 2>&1; then
    echo -e "${RED}ОШИБКА: PostgreSQL не запущен. Запустите: docker-compose up -d postgres${NC}"
    exit 1
fi

# Активируем виртуальное окружение
source venv/bin/activate

# Останавливаем бота перед восстановлением БД
echo -e "${YELLOW}Остановка сервиса бота...${NC}"
sudo systemctl stop pogran-bot.service || true

# Восстанавливаем базу данных из backup
echo -e "${YELLOW}Восстановление базы данных из backup...${NC}"
docker-compose exec -T postgres pg_restore -U postgres -d pogran_bot --clean --if-exists < "$BACKUP_FILE"

if [ $? -eq 0 ]; then
    echo -e "${GREEN}База данных успешно восстановлена${NC}"
else
    echo -e "${RED}ОШИБКА: Не удалось восстановить базу данных${NC}"
    exit 1
fi

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

echo -e "${GREEN}=== Первый деплой завершен успешно ===${NC}"
echo -e "${GREEN}Бот запущен и готов к работе${NC}"

