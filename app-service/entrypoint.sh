#!/bin/sh
set -e

# Запускаем FastAPI в фоне
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 2 &
BACKEND_PID=$!

# Запускаем nginx в фоне
nginx -g "daemon off;" &
NGINX_PID=$!

term_handler() {
  kill -TERM "$BACKEND_PID" 2>/dev/null
  kill -TERM "$NGINX_PID" 2>/dev/null
  wait "$BACKEND_PID" 2>/dev/null
  wait "$NGINX_PID" 2>/dev/null
  exit 0
}
trap term_handler TERM INT

while true; do
  if ! kill -0 "$BACKEND_PID" 2>/dev/null; then
    echo "Backend (uvicorn) остановился — завершаю контейнер"
    kill -TERM "$NGINX_PID" 2>/dev/null
    exit 1
  fi
  if ! kill -0 "$NGINX_PID" 2>/dev/null; then
    echo "Nginx остановился — завершаю контейнер"
    kill -TERM "$BACKEND_PID" 2>/dev/null
    exit 1
  fi
  sleep 2
done
