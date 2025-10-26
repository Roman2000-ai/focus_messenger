#!/bin/sh


DB_INIT_SCRIPT="./database/database.py"

if [ ! -f $DB_INIT_SCRIPT ]; then
    echo "Ошибка: Не найден скрипт инициализации базы данных: $DB_INIT_SCRIPT"
    exit 1
fi

echo "Проверка и инициализация базы данных..."

python3 -m database.database create

echo "Инициализация базы данных завершена."


echo "Запуск Gunicorn/Uvicorn..."
exec gunicorn --bind 0.0.0.0:8000 -k uvicorn.workers.UvicornWorker main:app