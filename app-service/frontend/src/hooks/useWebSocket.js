import { useEffect, useRef, useState } from 'react'
import wsClient from '../api/wsClient.js'
import { getMockStream } from '../mock/mockProvider.js'

const USE_MOCK = String(import.meta.env.VITE_USE_MOCK) === 'true'

/**
 * Подписка на канал WebSocket. Список каналов настраивается в
 * src/api/endpoints.js (WS_CHANNELS) — здесь захардкожен только сам
 * механизм подписки, а не бизнес-логика.
 *
 * @param {string} channel - имя канала (см. WS_CHANNELS)
 * @param {any} initialValue
 */
export function useWebSocketChannel(channel, initialValue = null) {
  const [data, setData] = useState(initialValue)
  const [status, setStatus] = useState('idle')

  useEffect(() => {
    if (USE_MOCK) {
      const stop = getMockStream(channel, (payload) => setData(payload))
      setStatus('connected')
      return () => stop && stop()
    }

    wsClient.connect()
    const unsubData = wsClient.subscribe(channel, (payload) => setData(payload))
    const unsubStatus = wsClient.subscribe('__connection__', (info) => setStatus(info.status))
    return () => {
      unsubData()
      unsubStatus()
    }
  }, [channel])

  const send = (payload) => wsClient.send(channel, payload)

  return { data, status, send }
}
