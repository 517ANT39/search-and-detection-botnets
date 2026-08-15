/**
 * Универсальный WebSocket-клиент с автопереподключением и системой
 * подписки по каналам (аналог pub/sub). Ни один канал/URL не зашит —
 * список каналов задаётся в src/api/endpoints.js (WS_CHANNELS), а сам
 * адрес сервера — в переменной окружения VITE_WS_URL.
 *
 * Формат сообщений от сервера ожидается в виде JSON:
 *   { "type": "<channel>", "payload": <any> }
 * Если ваш backend использует другой формат — измените только метод
 * _handleMessage() ниже, остальной код (хуки/компоненты) трогать не нужно.
 */

function resolveWsUrl() {
  const fromStorage = typeof window !== 'undefined'
    ? window.localStorage.getItem('netsentry.wsUrl')
    : null
  const raw = fromStorage || import.meta.env.VITE_WS_URL || '/ws'
  if (raw.startsWith('ws://') || raw.startsWith('wss://')) return raw
  // Относительный путь -> собираем полный адрес на основе текущего origin
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  return `${protocol}//${window.location.host}${raw}`
}

class NetSentryWebSocket {
  constructor() {
    this.socket = null
    this.listeners = new Map() // channel -> Set<callback>
    this.reconnectDelay = 1000
    this.maxReconnectDelay = 15000
    this.shouldReconnect = true
    this.connected = false
    this.queue = []
  }

  connect() {
    if (this.socket && (this.socket.readyState === WebSocket.OPEN || this.socket.readyState === WebSocket.CONNECTING)) {
      return
    }
    const url = resolveWsUrl()
    this.socket = new WebSocket(url)

    this.socket.onopen = () => {
      this.connected = true
      this.reconnectDelay = 1000
      this._emit('__connection__', { status: 'connected' })
      // отправляем токен авторизации сразу после подключения (опционально)
      const token = window.localStorage.getItem('netsentry.token')
      if (token) {
        this.send('auth', { token })
      }
      // выгружаем очередь сообщений, накопленную пока не было соединения
      this.queue.forEach((msg) => this.socket.send(JSON.stringify(msg)))
      this.queue = []
    }

    this.socket.onmessage = (event) => {
      this._handleMessage(event.data)
    }

    this.socket.onclose = () => {
      this.connected = false
      this._emit('__connection__', { status: 'disconnected' })
      if (this.shouldReconnect) {
        setTimeout(() => this.connect(), this.reconnectDelay)
        this.reconnectDelay = Math.min(this.reconnectDelay * 1.6, this.maxReconnectDelay)
      }
    }

    this.socket.onerror = () => {
      this._emit('__connection__', { status: 'error' })
    }
  }

  _handleMessage(raw) {
    try {
      const data = JSON.parse(raw)
      const channel = data.type || data.channel
      this._emit(channel, data.payload !== undefined ? data.payload : data)
    } catch (e) {
      // если backend шлёт не-JSON — прокидываем как есть в служебный канал
      this._emit('__raw__', raw)
    }
  }

  _emit(channel, payload) {
    const set = this.listeners.get(channel)
    if (set) set.forEach((cb) => cb(payload))
  }

  subscribe(channel, callback) {
    if (!this.listeners.has(channel)) this.listeners.set(channel, new Set())
    this.listeners.get(channel).add(callback)
    return () => this.unsubscribe(channel, callback)
  }

  unsubscribe(channel, callback) {
    const set = this.listeners.get(channel)
    if (set) set.delete(callback)
  }

  send(type, payload) {
    const message = { type, payload }
    if (this.socket && this.socket.readyState === WebSocket.OPEN) {
      this.socket.send(JSON.stringify(message))
    } else {
      this.queue.push(message)
      this.connect()
    }
  }

  disconnect() {
    this.shouldReconnect = false
    if (this.socket) this.socket.close()
  }
}

export const wsClient = new NetSentryWebSocket()
export default wsClient
