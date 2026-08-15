# NetSentry Dashboard (React)

Готовый каркас панели мониторинга сетевой активности в стиле макета NetSentry:
страница авторизации + 9 вкладок (Обзор, Топология, Узлы, Инциденты, События,
Трафик, Правила, Отчёты, Настройки), с готовым слоем связи по HTTP и WebSocket.

## Быстрый старт

```bash
npm install
cp .env.example .env
npm run dev
```

По умолчанию `VITE_USE_MOCK=true` — интерфейс сразу работает на тестовых данных,
без необходимости поднимать backend. Логин/пароль на странице входа в mock-режиме
могут быть любыми.

## Как подключить свой backend (без хардкода)

Все URL живут в **одном файле**: `src/api/endpoints.js`. Компоненты и страницы
никогда не содержат сырых строк маршрутов — они импортируют объект
`HTTP_ENDPOINTS` и константы `WS_CHANNELS` оттуда.

1. Откройте `src/api/endpoints.js` и пропишите свои реальные пути
   (например, `overview.summary: '/api/v1/dashboard/summary'`).
2. В `.env` укажите:
   - `VITE_API_BASE_URL` — базовый адрес HTTP API (например `https://api.example.com`)
   - `VITE_WS_URL` — адрес WebSocket сервера (например `wss://api.example.com/ws`)
   - `VITE_USE_MOCK=false` — чтобы приложение перестало использовать заглушки
   - `VITE_AUTH_HEADER` / `VITE_AUTH_SCHEME` — если у вас другая схема авторизации
     (например `X-API-Key` без схемы)
3. Токен авторизации автоматически подставляется в каждый HTTP-запрос
   (`src/api/httpClient.js`) и отправляется первым сообщением после подключения
   к WebSocket (`src/api/wsClient.js`).

### HTTP слой — `src/api/httpClient.js`
Обёртка над axios с автоматической подстановкой токена и обработкой 401.
Использование в коде:
```js
import { useApi, apiPost } from '../hooks/useApi.js'
import { HTTP_ENDPOINTS } from '../api/endpoints.js'

const { data, loading, error, refetch } = useApi(HTTP_ENDPOINTS.overview.summary)
await apiPost(HTTP_ENDPOINTS.rules.create, { name: 'Новое правило' })
```

### WebSocket слой — `src/api/wsClient.js`
Единый клиент с автопереподключением и системой каналов (pub/sub). Формат
сообщений от сервера: `{ "type": "<channel>", "payload": <любые данные> }`.
Если ваш backend использует другой конверт сообщений — измените только метод
`_handleMessage()` внутри `wsClient.js`, остальной код трогать не нужно.

Использование в компоненте:
```js
import { useWebSocketChannel } from '../hooks/useWebSocket.js'
import { WS_CHANNELS } from '../api/endpoints.js'

const { data, status, send } = useWebSocketChannel(WS_CHANNELS.metrics)
```

Каналы (`WS_CHANNELS`) переименуйте под свой протокол в `endpoints.js` — их
используют только хуки, компоненты обращаются исключительно к константам.

### Настройка адресов без пересборки
На вкладке **Настройки** есть поля для HTTP/WS адресов — они сохраняются в
`localStorage` и переопределяют значения из `.env` "на лету", что удобно для
переключения между тестовым и боевым backend без пересборки проекта.

### Прокси для локальной разработки
`vite.config.js` содержит прокси `/api` и `/ws` на `http://localhost:8000` —
поменяйте `target` под адрес вашего локального сервера, либо используйте
переменные `VITE_API_PROXY_TARGET` / `VITE_WS_PROXY_TARGET`.

## Структура проекта

```
src/
  api/
    endpoints.js     # ЕДИНСТВЕННОЕ место с путями HTTP/WS — правьте только здесь
    httpClient.js     # axios-обёртка + авторизация + обработка ошибок
    wsClient.js        # WebSocket клиент: подписки, переподключение, очередь
  hooks/
    useApi.js          # GET-запросы + loading/error, апи для POST/PUT/DELETE
    useWebSocket.js     # подписка на канал WebSocket в виде React-хука
  context/
    AuthContext.jsx    # логин/логаут, хранение токена, состояние пользователя
  components/
    Layout/            # Sidebar, Topbar, AppLayout
    UI/                 # MetricCard, StatusBadge
    TopologyMap.jsx     # карта топологии сети
    ProtectedRoute.jsx
  pages/                # Login, Overview, Topology, Nodes, Incidents,
                         # Events, Traffic, Rules, Reports, Settings
  mock/
    mockProvider.js     # тестовые данные (работает только при VITE_USE_MOCK=true)
```

## Замена авторизации
`src/context/AuthContext.jsx` вызывает `HTTP_ENDPOINTS.auth.login` и ожидает
в ответе `{ token, user }` (или `access_token`). При другом контракте backend
поправьте только эту функцию `login()` — остальной код (ProtectedRoute, Topbar,
страницы) не зависит от формата ответа.

## Стек
React 18 · React Router 6 · Axios · Recharts · Tailwind CSS · lucide-react · Vite
