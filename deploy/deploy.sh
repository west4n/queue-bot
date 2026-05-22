#!/bin/bash
set -e

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}=== Начало деплоя Pogran Bot ===${NC}"

# Переходим в директорию проекта
cd /opt/pogran-bot

# Обновляем код из Git
echo -e "${YELLOW}Обновление кода из Git...${NC}"
git fetch origin
git reset --hard origin/main
git clean -fd

# Создаем виртуальное окружение, если его нет
if [ ! -d "venv" ]; then
    echo -e "${YELLOW}Создание виртуального окружения Python...${NC}"
    python3 -m venv venv
fi

# Активируем виртуальное окружение
source venv/bin/activate

# Обновляем pip
echo -e "${YELLOW}Обновление pip...${NC}"
pip install --upgrade pip

# Устанавливаем зависимости
echo -e "${YELLOW}Установка зависимостей...${NC}"
pip install -r requirements.txt

# Проверяем наличие .env файла
if [ ! -f ".env" ]; then
    echo -e "${YELLOW}Файл .env не найден. Создание из шаблона...${NC}"
    if [ -f ".env.example" ]; then
        cp .env.example .env
        echo -e "${RED}ВНИМАНИЕ: Необходимо настроить переменные окружения в файле .env${NC}"
    else
        echo -e "${RED}ОШИБКА: Файл .env.example не найден!${NC}"
        exit 1
    fi
fi

# Запускаем Docker Compose для PostgreSQL
echo -e "${YELLOW}Запуск PostgreSQL через Docker Compose...${NC}"
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

# Активируем расширение TimescaleDB (если используется TimescaleDB)
echo -e "${YELLOW}Проверка TimescaleDB расширения...${NC}"
if docker-compose exec -T postgres psql -U postgres -d pogran_bot -c "CREATE EXTENSION IF NOT EXISTS timescaledb;" 2>/dev/null; then
    echo -e "${GREEN}TimescaleDB расширение активировано${NC}"
else
    echo -e "${YELLOW}TimescaleDB расширение не требуется или уже активировано${NC}"
fi

# Применяем миграции Alembic
echo -e "${YELLOW}Применение миграций базы данных...${NC}"
alembic upgrade head

echo -e "${GREEN}=== Деплой завершен успешно ===${NC}"

