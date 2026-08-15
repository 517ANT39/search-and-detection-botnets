import { useCallback, useEffect, useRef, useState } from 'react'
import httpClient from '../api/httpClient.js'
import { getMock } from '../mock/mockProvider.js'
import { onGlobalRefresh } from '../utils/refreshBus.js'

const USE_MOCK = String(import.meta.env.VITE_USE_MOCK) === 'true'

/**
 * Универсальный хук для GET-запросов.
 * @param {string} endpoint - путь из src/api/endpoints.js
 * @param {object} params - query-параметры
 * @param {object} options - { immediate: boolean, pollIntervalMs: number, mockKey: string }
 *
 * Не содержит хардкода конкретных бизнес-полей — просто оборачивает
 * httpClient.get(endpoint, { params }) в состояние loading/data/error.
 * Если VITE_USE_MOCK=true — вместо реального запроса возвращает
 * тестовые данные из src/mock (удобно для запуска UI без backend).
 *
 * Также хук подписан на глобальное событие «Обновить» (кнопка в Topbar) —
 * при её нажатии все смонтированные useApi() перезапрашивают данные.
 */
export function useApi(endpoint, params = {}, options = {}) {
  const { immediate = true, pollIntervalMs = 0, mockKey } = options
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(immediate)
  const [error, setError] = useState(null)
  const paramsRef = useRef(params)
  paramsRef.current = params

  const fetchData = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      if (USE_MOCK) {
        const mockData = await getMock(mockKey || endpoint, paramsRef.current)
        setData(mockData)
      } else {
        const res = await httpClient.get(endpoint, { params: paramsRef.current })
        setData(res.data)
      }
    } catch (e) {
      setError(e)
    } finally {
      setLoading(false)
    }
  }, [endpoint, mockKey])

  useEffect(() => {
    if (immediate) fetchData()
    if (pollIntervalMs > 0) {
      const id = setInterval(fetchData, pollIntervalMs)
      return () => clearInterval(id)
    }
  }, [fetchData, immediate, pollIntervalMs])

  // Подписка на глобальное «Обновить» — перезапрашиваем данные по клику в Topbar
  useEffect(() => {
    if (!immediate) return
    return onGlobalRefresh(fetchData)
  }, [fetchData, immediate])

  return { data, loading, error, refetch: fetchData }
}

export async function apiPost(endpoint, body) {
  if (USE_MOCK) return { ok: true, mocked: true, body }
  const res = await httpClient.post(endpoint, body)
  return res.data
}

export async function apiPut(endpoint, body) {
  if (USE_MOCK) return { ok: true, mocked: true, body }
  const res = await httpClient.put(endpoint, body)
  return res.data
}

export async function apiPatch(endpoint, body) {
  if (USE_MOCK) return { ok: true, mocked: true, body }
  const res = await httpClient.patch(endpoint, body)
  return res.data
}

export async function apiDelete(endpoint) {
  if (USE_MOCK) return { ok: true, mocked: true }
  const res = await httpClient.delete(endpoint)
  return res.data
}
