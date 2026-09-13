import { wsUrl, getToken } from './api.js';

let ws = null;
let reconnectTimer = null;

export function initAlertSocket({ onAlert }) {
  const connect = () => {
    try {
      // Передаём токен в query — бэкенд может его проверить, если понадобится
      const token = getToken();
      const url = wsUrl(`/ws/alerts${token ? `?token=${token}` : ''}`);
      ws = new WebSocket(url);

      ws.onopen = () => {
        console.log('[ws] connected');
        // Пингуем каждые 20 секунд, чтобы соединение не закрывалось
        const ping = setInterval(() => {
          if (ws && ws.readyState === WebSocket.OPEN) {
            ws.send('ping');
          } else {
            clearInterval(ping);
          }
        }, 20000);
      };

      ws.onmessage = (ev) => {
        try {
          const data = JSON.parse(ev.data);
          onAlert(data);
        } catch (e) {
          // не JSON — игнорируем
        }
      };

      ws.onclose = () => {
        console.log('[ws] disconnected, reconnect in 3s');
        clearTimeout(reconnectTimer);
        reconnectTimer = setTimeout(connect, 3000);
      };

      ws.onerror = () => {
        ws.close();
      };
    } catch (e) {
      console.error('[ws] error:', e);
    }
  };
  connect();
}

export function closeAlertSocket() {
  if (ws) ws.close();
  clearTimeout(reconnectTimer);
}