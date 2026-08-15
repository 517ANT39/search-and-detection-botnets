# ===================== STAGE 1: build frontend =====================
FROM node:20-alpine AS frontend-build
WORKDIR /app/frontend
COPY frontend/package*.json ./
# В проекте нет package-lock.json, поэтому используем npm install.
# Если у вас есть package-lock.json — можно вернуть "npm ci" для более быстрой и детерминированной сборки.
RUN npm install
COPY frontend/ ./
# VITE_* переменные можно переопределить через --build-arg
ARG VITE_API_BASE_URL=/api
ARG VITE_WS_URL=/ws
ARG VITE_USE_MOCK=false
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL
ENV VITE_WS_URL=$VITE_WS_URL
ENV VITE_USE_MOCK=$VITE_USE_MOCK
RUN npm run build

# ===================== STAGE 2: backend deps =====================
FROM python:3.11-slim AS backend-build
WORKDIR /app/backend
COPY backend/requirements.txt ./
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# ===================== STAGE 3: final runtime =====================
FROM python:3.11-slim

# nginx для раздачи фронтенда и проксирования API/WS
RUN apt-get update && apt-get install -y --no-install-recommends nginx \
    && rm -rf /var/lib/apt/lists/*

# бэкенд
COPY --from=backend-build /install /usr/local
COPY backend/ /app/backend/

# собранный фронтенд
COPY --from=frontend-build /app/frontend/dist /usr/share/nginx/html

# конфиг nginx и стартовый скрипт
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY entrypoint.sh /entrypoint.sh
RUN rm -f /etc/nginx/sites-enabled/default 2>/dev/null; chmod +x /entrypoint.sh

WORKDIR /app/backend
EXPOSE 80

ENTRYPOINT ["/entrypoint.sh"]
