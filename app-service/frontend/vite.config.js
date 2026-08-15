import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// Прокси для локальной разработки: перенаправляет /api и /ws на бэкенд.
// Настраивается через переменные окружения VITE_API_PROXY_TARGET / VITE_WS_PROXY_TARGET
// либо просто отредактируйте target ниже под свой backend.
export default defineConfig({
  plugins: [react()],
  server: {
    host: '0.0.0.0',       // критично для Docker/удалённых машин — слушать все интерфейсы, не только localhost
    port: 5173,
    strictPort: true,       // не переключаться на другой порт молча, если 5173 занят
    watch: {
      usePolling: true,     // на некоторых Docker/Windows/WSL файловых системах inotify не работает без polling
    },
    proxy: {
      '/api': {
        target: process.env.VITE_API_PROXY_TARGET || 'http://localhost:8000',
        changeOrigin: true,
      },
      '/ws': {
        target: process.env.VITE_WS_PROXY_TARGET || 'ws://localhost:8000',
        ws: true,
      },
    },
  },
  preview: {
    host: '0.0.0.0',
    port: 5173,
  },
})
