#!/bin/bash

# Скрипт для создания бэкапа базы данных
# Использование: ./backup_db.sh [HOST] [USER] [DATABASE] [OUTPUT_DIR]

set -e

# Параметры по умолчанию
HOST="${1:-172.16.1.110}"
USER="${2:-postgres}"
DATABASE="${3:-pogran-bot-main}"
OUTPUT_DIR="${4:-./backups}"

# Создаем директорию для бэкапов, если её нет
mkdir -p "$OUTPUT_DIR"

# Генерируем имя файла с датой и временем
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$OUTPUT_DIR/pogran_bot_backup_${TIMESTAMP}.dump"

echo "=========================================="
echo "Создание бэкапа базы данных"
echo "=========================================="
echo "Хост: $HOST"
echo "Пользователь: $USER"
echo "База данных: $DATABASE"
echo "Файл бэкапа: $BACKUP_FILE"
echo "=========================================="

# Создаем бэкап
pg_dump -h "$HOST" -U "$USER" -d "$DATABASE" -F c -f "$BACKUP_FILE"

# Проверяем размер файла
FILE_SIZE=$(du -h "$BACKUP_FILE" | cut -f1)

echo ""
echo "✅ Бэкап успешно создан!"
echo "📁 Файл: $BACKUP_FILE"
echo "📦 Размер: $FILE_SIZE"
echo ""
echo "Для восстановления используйте:"
echo "  pg_restore -h $HOST -U $USER -d <TARGET_DB> -v $BACKUP_FILE"
echo ""
