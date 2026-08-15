/**
 * =====================================================================
 *  ЕДИНАЯ ТОЧКА НАСТРОЙКИ ВСЕХ HTTP/WS МАРШРУТОВ ПРИЛОЖЕНИЯ
 * =====================================================================
 * Здесь нет ни одного "зашитого" URL внутри компонентов — все страницы
 * и хуки берут пути ИСКЛЮЧИТЕЛЬНО отсюда. Чтобы подключить свой backend,
 * достаточно отредактировать значения ниже (или .env — см. httpClient.js
 * и wsClient.js) — компоненты менять не нужно.
 *
 * baseURL для HTTP берётся из VITE_API_BASE_URL (см. .env.example)
 * URL для WebSocket берётся из VITE_WS_URL
 *
 * Формат WS-сообщений: { type: '<channel>', payload: {...} }
 * Вы можете переименовать каналы ниже под свой протокол backend.
 */

export const HTTP_ENDPOINTS = {
  auth: {
    login: '/auth/login',
    logout: '/auth/logout',
    me: '/auth/me',
    refresh: '/auth/refresh',
    updateProfile: '/auth/profile',
  },
  overview: {
    summary: '/overview/summary',
    trafficHistory: '/overview/traffic-history',
    channelUsage: '/overview/channel-usage',
    nodeLoadHeatmap: '/overview/node-load',
    trafficByNode: '/overview/traffic-by-node',
    protocols: '/overview/protocols',
    topology: '/overview/topology',
    recentEvents: '/overview/events/recent',
    incidents: '/overview/incidents',
  },
  topology: {
    graph: '/topology/graph',
  },
  nodes: {
    list: '/nodes',
    details: (id) => `/nodes/${id}`,
    traffic: (id) => `/nodes/${id}/traffic`,
  },
  incidents: {
    list: '/incidents',
    details: (id) => `/incidents/${id}`,
    timeline: (id) => `/incidents/${id}/timeline`,
    relatedEvents: (id) => `/incidents/${id}/related-events`,
    update: (id) => `/incidents/${id}`,
  },
  events: {
    list: '/events',
  },
  traffic: {
    stats: '/traffic/stats',
    byChannel: '/traffic/channels',
  },
  rules: {
    list: '/rules',
    details: (id) => `/rules/${id}`,
    create: '/rules',
    update: (id) => `/rules/${id}`,
    remove: (id) => `/rules/${id}`,
  },
  reports: {
    list: '/reports',
    generate: '/reports/generate',
    download: (id) => `/reports/${id}/download`,
  },
  notifications: {
    list: '/notifications',
    markRead: (id) => `/notifications/${id}/read`,
  },
  settings: {
    get: '/settings',
    update: '/settings',
    clusters: '/settings/clusters',
    users: '/settings/users',
  },
}

// Каналы WebSocket-подписок (тип сообщения в конверте {type, payload})
export const WS_CHANNELS = {
  metrics: 'metrics.update',
  traffic: 'traffic.update',
  incidents: 'incidents.update',
  events: 'events.new',
  nodes: 'nodes.update',
  topology: 'topology.update',
  notifications: 'notifications.new',
}
