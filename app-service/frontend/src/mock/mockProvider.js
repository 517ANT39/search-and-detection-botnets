import { HTTP_ENDPOINTS, WS_CHANNELS } from '../api/endpoints.js'

/**
 * Демонстрационные данные. Используются ТОЛЬКО когда VITE_USE_MOCK=true.
 * При переключении на реальный backend (VITE_USE_MOCK=false) этот файл
 * не участвует в работе приложения — можно спокойно удалить папку mock.
 */

const rnd = (min, max) => Math.round((min + Math.random() * (max - min)) * 10) / 10

function trafficHistory() {
  const points = []
  const now = Date.now()
  for (let i = 24; i >= 0; i--) {
    points.push({
      time: new Date(now - i * 30 * 60000).toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit' }),
      in: Math.round(60 + Math.random() * 140),
      out: Math.round(40 + Math.random() * 100),
    })
  }
  return points
}

function seededHistoryForNode(nodeId) {
  const seed = [...nodeId].reduce((a, ch) => a + ch.charCodeAt(0), 0)
  const baseIn = 40 + (seed % 60)
  const baseOut = 30 + (seed % 40)
  const points = []
  const now = Date.now()
  for (let i = 24; i >= 0; i--) {
    points.push({
      time: new Date(now - i * 30 * 60000).toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit' }),
      in: Math.max(5, Math.round(baseIn + (Math.random() - 0.5) * 70)),
      out: Math.max(5, Math.round(baseOut + (Math.random() - 0.5) * 50)),
    })
  }
  return points
}

function nodeLoadBuckets() {
  const labels = ['-24ч', '-21ч', '-18ч', '-15ч', '-12ч', '-9ч', '-6ч', '-3ч', 'Сейчас']
  return labels.map((time) => ({
    time,
    low: 1 + Math.round(Math.random() * 3),
    medium: Math.round(Math.random() * 3),
    high: Math.round(Math.random() * 2),
  }))
}

const NODES = [
  { id: 'WS-MSK-21', label: 'WS-MSK-21', group: 'Офис Москва', status: 'ok' },
  { id: 'WS-MSK-22', label: 'WS-MSK-22', group: 'Офис Москва', status: 'ok' },
  { id: 'SRV-MSK-01', label: 'SRV-MSK-01', group: 'Офис Москва', status: 'ok' },
  { id: 'FW-DC', label: 'FW-DC', group: 'ЦОД', status: 'critical' },
  { id: 'SRV-CORE-01', label: 'SRV-CORE-01', group: 'ЦОД', status: 'ok' },
  { id: 'SRV-APP-01', label: 'SRV-APP-01', group: 'ЦОД', status: 'ok' },
  { id: 'SRV-DB-01', label: 'SRV-DB-01', group: 'ЦОД', status: 'warning' },
  { id: 'SRV-FILE-01', label: 'SRV-FILE-01', group: 'ЦОД', status: 'ok' },
  { id: 'WS-SPB-12', label: 'WS-SPB-12', group: 'Офис СПб', status: 'ok' },
  { id: 'WS-SPB-11', label: 'WS-SPB-11', group: 'Офис СПб', status: 'ok' },
  { id: 'SRV-SPB-01', label: 'SRV-SPB-01', group: 'Офис СПб', status: 'ok' },
  { id: 'VPC-NETSENTRY', label: 'VPC-NETSENTRY', group: 'Облако', status: 'ok' },
  { id: 'SRV-CLOUD-01', label: 'SRV-CLOUD-01', group: 'Облако', status: 'ok' },
  { id: 'SRV-CLOUD-02', label: 'SRV-CLOUD-02', group: 'Облако', status: 'ok' },
]

const INCIDENTS = [
  { id: 'INC-2024-05-24-102431', time: '24.05.2024 10:24:31', level: 'critical', title: 'Несанкционированный доступ', source: 'WS-CLI-23', target: 'SRV-DB-01 (10.10.1.15)', status: 'new' },
  { id: 'INC-2024-05-24-095812', time: '24.05.2024 09:58:12', level: 'high', title: 'Подозрительное сканирование портов', source: 'WS-CLI-17', target: '10.10.1.0/24', status: 'in_progress' },
  { id: 'INC-2024-05-24-094107', time: '24.05.2024 09:41:07', level: 'high', title: 'Массовое обращение к серверу', source: 'SRV-APP-01', target: 'SRV-APP-01 (10.10.2.30)', status: 'new' },
  { id: 'INC-2024-05-24-092218', time: '24.05.2024 09:22:18', level: 'medium', title: 'Аномальный исходящий трафик', source: 'SRV-FILE-01', target: '185.220.101.12', status: 'new' },
  { id: 'INC-2024-05-24-085533', time: '24.05.2024 08:55:33', level: 'medium', title: 'DNS-туннелирование', source: 'WS-CLI-21', target: '8.8.8.8', status: 'in_progress' },
  { id: 'INC-2024-05-24-081209', time: '24.05.2024 08:12:09', level: 'low', title: 'Изменение конфигурации системы', source: 'SW-MSK-01', target: '—', status: 'closed' },
  { id: 'INC-2024-05-24-075844', time: '24.05.2024 07:58:44', level: 'low', title: 'Событие политики безопасности', source: 'FW-DC', target: '—', status: 'closed' },
]

const EVENTS = [
  { time: '10:24:45', level: 'warning', text: 'Попытка доступа к ресурсу', source: 'SRV-DB-01' },
  { time: '10:24:31', level: 'critical', text: 'Повышение привилегий', source: 'admin_db' },
  { time: '10:24:15', level: 'warning', text: 'Изменение данных', source: 'Таблица customers' },
  { time: '10:24:08', level: 'info', text: 'Сетевое соединение', source: '185.220.112.443' },
  { time: '10:23:57', level: 'warning', text: 'Аномальный трафик', source: 'SRV-FILE-01' },
]

const NOTIFICATIONS = [
  { id: 1, level: 'critical', text: 'Обнаружен несанкционированный доступ к SRV-DB-01', time: '10:24:31', read: false },
  { id: 2, level: 'warning', text: 'Подозрительное сканирование портов с WS-CLI-17', time: '09:58:12', read: false },
  { id: 3, level: 'info', text: 'Еженедельный отчёт готов к загрузке', time: '08:00:00', read: true },
]

export async function getMock(endpointOrKey) {
  await new Promise((r) => setTimeout(r, 150 + Math.random() * 250))

  // Динамический путь /nodes/{id}/traffic
  const nodeTrafficMatch = typeof endpointOrKey === 'string' && endpointOrKey.match(/^\/nodes\/([^/]+)\/traffic$/)
  if (nodeTrafficMatch) {
    const id = nodeTrafficMatch[1]
    const node = NODES.find((n) => n.id === id)
    return { nodeId: id, label: node?.label || id, history: seededHistoryForNode(id) }
  }

  switch (endpointOrKey) {
    case HTTP_ENDPOINTS.overview.summary:
      return {
        totalTraffic: { value: 2.47, unit: 'ТБ', delta: 18.6 },
        outboundTraffic: { value: 1.35, unit: 'ТБ', percent: 54.7 },
        inboundTraffic: { value: 1.12, unit: 'ТБ', percent: 45.3 },
        activeNodes: { active: 128, total: 172, percent: 74 },
        suspiciousActivity: { value: 23, delta24h: 5 },
        criticalIncidents: { value: 7, delta24h: 2 },
      }
    case HTTP_ENDPOINTS.overview.trafficHistory:
      return trafficHistory()
    case HTTP_ENDPOINTS.overview.nodeLoadHeatmap:
      return nodeLoadBuckets()
    case HTTP_ENDPOINTS.overview.trafficByNode:
      return NODES.map((n) => ({ id: n.id, label: n.label, group: n.group, history: seededHistoryForNode(n.id) }))
    case HTTP_ENDPOINTS.overview.channelUsage:
      return [
        { label: 'Основной канал', percent: 78 },
        { label: 'Резервный канал', percent: 34 },
        { label: 'Канал в ЦОД', percent: 61 },
      ]
    case HTTP_ENDPOINTS.overview.protocols:
      return [
        { label: 'HTTP/HTTPS', percent: 38.6, color: '#2f6fed' },
        { label: 'SMB', percent: 22.1, color: '#3aa0ff' },
        { label: 'DNS', percent: 11.3, color: '#2ecc71' },
        { label: 'RDP', percent: 7.8, color: '#f5a623' },
        { label: 'Прочее', percent: 20.2, color: '#c7ccd6' },
      ]
    case HTTP_ENDPOINTS.overview.topology:
    case HTTP_ENDPOINTS.topology.graph:
      return { nodes: NODES }
    case HTTP_ENDPOINTS.overview.recentEvents:
    case HTTP_ENDPOINTS.events.list:
      return EVENTS
    case HTTP_ENDPOINTS.overview.incidents:
    case HTTP_ENDPOINTS.incidents.list:
      return INCIDENTS
    case HTTP_ENDPOINTS.nodes.list:
      return NODES
    case HTTP_ENDPOINTS.rules.list:
      return [
        { id: 1, name: 'Политика доступа к БД', type: 'Доступ', status: 'active', severity: 'critical' },
        { id: 2, name: 'Блокировка сканирования портов', type: 'Сеть', status: 'active', severity: 'high' },
        { id: 3, name: 'Контроль исходящего трафика', type: 'Трафик', status: 'disabled', severity: 'medium' },
      ]
    case HTTP_ENDPOINTS.reports.list:
      return [
        { id: 1, name: 'Еженедельный отчёт по инцидентам', date: '19.05.2024', format: 'PDF' },
        { id: 2, name: 'Отчёт по трафику узлов', date: '12.05.2024', format: 'XLSX' },
      ]
    case HTTP_ENDPOINTS.settings.get:
      return {
        clusters: ['Все кластеры', 'Москва', 'Санкт-Петербург', 'Облако'],
        siemIntegration: true,
        version: '2.4.1',
      }
    case HTTP_ENDPOINTS.notifications.list:
      return NOTIFICATIONS
    default:
      return null
  }
}

// Простейшая эмуляция realtime-потока для демо-режима (заменяет WebSocket)
export function getMockStream(channel, callback) {
  let cancelled = false

  const tick = () => {
    if (cancelled) return
    if (channel === WS_CHANNELS.metrics) {
      callback({
        totalTraffic: { value: rnd(2.2, 2.7), unit: 'ТБ', delta: rnd(10, 22) },
        activeNodes: { active: 120 + Math.round(Math.random() * 10), total: 172 },
        suspiciousActivity: { value: 18 + Math.round(Math.random() * 10) },
        criticalIncidents: { value: 5 + Math.round(Math.random() * 4) },
      })
    }
    if (channel === WS_CHANNELS.traffic) {
      callback({ in: rnd(60, 200), out: rnd(40, 140), time: new Date().toLocaleTimeString('ru-RU') })
    }
    if (channel === WS_CHANNELS.events) {
      const pool = ['Попытка доступа', 'Сетевое соединение', 'Аномальный трафик', 'Изменение конфигурации']
      callback({ time: new Date().toLocaleTimeString('ru-RU'), level: 'info', text: pool[Math.floor(Math.random() * pool.length)], source: 'auto' })
    }
    if (channel === WS_CHANNELS.notifications && Math.random() < 0.3) {
      callback({
        id: Date.now(),
        level: Math.random() > 0.6 ? 'critical' : 'warning',
        text: 'Новое событие безопасности требует внимания',
        time: new Date().toLocaleTimeString('ru-RU'),
        read: false,
      })
    }
  }

  const id = setInterval(tick, 4000)
  tick()
  return () => { cancelled = true; clearInterval(id) }
}
