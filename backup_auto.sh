#!/bin/bash

# Автоматический скрипт для создания бэкапа базы данных PostgreSQL
# Удаляет бэкапы старше 30 дней

set -e

# Параметры подключения к базе данных
CONTAINER_NAME="pogran-bot-postgres"
DB_NAME="pogran_bot"
DB_USER="postgres"
BACKUP_DIR="/opt/pogran-bot/backups"

# Создаем директорию для бэкапов, если её нет
mkdir -p "$BACKUP_DIR"

# Генерируем имя файла с датой и временем
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/pogran_bot_backup_${TIMESTAMP}.sql.gz"

echo "=========================================="
echo "Создание бэкапа базы данных"
echo "=========================================="
echo "Контейнер: $CONTAINER_NAME"
echo "База данных: $DB_NAME"
echo "Файл бэкапа: $BACKUP_FILE"
echo "Время: $(date '+%Y-%m-%d %H:%M:%S')"
echo "=========================================="

# Проверяем, запущен ли контейнер
if ! docker ps --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
    echo "❌ Ошибка: контейнер $CONTAINER_NAME не запущен!"
    exit 1
fi

# Создаем бэкап через docker exec
docker exec -t "$CONTAINER_NAME" pg_dump -U "$DB_USER" -d "$DB_NAME" | gzip > "$BACKUP_FILE"

# Проверяем, что файл создан и не пустой
if [ ! -s "$BACKUP_FILE" ]; then
    echo "❌ Ошибка: файл бэкапа пустой или не был создан!"
    exit 1
fi

# Проверяем размер файла
FILE_SIZE=$(du -h "$BACKUP_FILE" | cut -f1)

echo ""
echo "✅ Бэкап успешно создан!"
echo "📁 Файл: $BACKUP_FILE"
echo "📦 Размер: $FILE_SIZE"

# Удаляем бэкапы старше 30 дней
echo ""
echo "Удаление старых бэкапов (старше 30 дней)..."
OLD_BACKUPS=$(find "$BACKUP_DIR" -name "pogran_bot_backup_*.sql.gz" -type f -mtime +30)

if [ -n "$OLD_BACKUPS" ]; then
    echo "$OLD_BACKUPS" | while read -r file; do
        echo "🗑️  Удаление: $file"
        rm -f "$file"
    done
    DELETED_COUNT=$(echo "$OLD_BACKUPS" | wc -l)
    echo "✅ Удалено бэкапов: $DELETED_COUNT"
else
    echo "ℹ️  Старых бэкапов не найдено"
fi

echo ""
echo "=========================================="
echo "Бэкап завершен успешно!"
echo "=========================================="
echo ""
echo "Для восстановления используйте:"
echo "  gunzip -c $BACKUP_FILE | docker exec -i $CONTAINER_NAME psql -U $DB_USER -d $DB_NAME"
echo ""
