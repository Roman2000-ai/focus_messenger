#!/bin/sh

PORT_TO_USE=${APP_PORT:-8000}

DB_INIT_SCRIPT="./backend/database/database.py"

if [ ! -f $DB_INIT_SCRIPT ]; then
    echo "Ошибка: Не найден скрипт инициализации базы данных: $DB_INIT_SCRIPT"
    exit 1
fi

echo "Проверка и инициализация базы данных..."

python3 -m database.database create

echo "Инициализация базы данных завершена."


echo "Запуск Gunicorn/Uvicorn..."
exec gunicorn --bind 0.0.0.0:"$PORT_TO_USE" -k uvicorn.workers.UvicornWorker backend.main:app