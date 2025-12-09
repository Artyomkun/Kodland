#!/bin/bash
# update.sh - Скрипт для ручного обновления

echo "Остановка контейнеров..."
docker-compose down

echo "Обновление образов..."
docker-compose pull

echo "Пересборка приложения..."
docker-compose build --no-cache cors-proxy

echo "Запуск контейнеров..."
docker-compose up -d

echo "Очистка старых образов..."
docker image prune -f

echo "Обновление завершено!"