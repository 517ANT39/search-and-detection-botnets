#!/bin/bash
set -e

# Запускаем Nginx в фоне
nginx -g "daemon off;" &

# Запускаем Uvicorn (привязываемся к 0.0.0.0)
exec uvicorn backend.main:app --host 0.0.0.0 --port 8000