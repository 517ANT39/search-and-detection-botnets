import React, { createContext, useContext, useEffect, useState, useCallback } from 'react'
import httpClient from '../api/httpClient.js'
import { HTTP_ENDPOINTS } from '../api/endpoints.js'

const AuthContext = createContext(null)
const USE_MOCK = String(import.meta.env.VITE_USE_MOCK) === 'true'

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const token = window.localStorage.getItem('netsentry.token')
    if (!token) { setLoading(false); return }
    if (USE_MOCK) {
      setUser({ name: 'Александр Иванов', role: 'Администратор', email: 'a.ivanov@netsentry.local' })
      setLoading(false)
      return
    }
    httpClient.get(HTTP_ENDPOINTS.auth.me)
      .then((res) => setUser(res.data))
      .catch(() => { window.localStorage.removeItem('netsentry.token') })
      .finally(() => setLoading(false))
  }, [])

  useEffect(() => {
    const handler = () => { setUser(null); window.localStorage.removeItem('netsentry.token') }
    window.addEventListener('netsentry:unauthorized', handler)
    return () => window.removeEventListener('netsentry:unauthorized', handler)
  }, [])

  const login = useCallback(async (username, password) => {
    if (USE_MOCK) {
      window.localStorage.setItem('netsentry.token', 'mock-token')
      setUser({ name: username || 'admin', role: 'Администратор', email: `${username || 'admin'}@netsentry.local` })
      return { ok: true }
    }
    // Подставьте свои поля запроса под контракт вашего backend при необходимости
    const res = await httpClient.post(HTTP_ENDPOINTS.auth.login, { username, password })
    const token = res.data?.token || res.data?.access_token
    if (token) window.localStorage.setItem('netsentry.token', token)
    setUser(res.data?.user || { name: username })
    return res.data
  }, [])

  const logout = useCallback(async () => {
    if (!USE_MOCK) {
      try { await httpClient.post(HTTP_ENDPOINTS.auth.logout) } catch (e) { /* игнорируем */ }
    }
    window.localStorage.removeItem('netsentry.token')
    setUser(null)
  }, [])

  // Обновление email / логина / пароля (страница «Настройки» → «Профиль»)
  const updateProfile = useCallback(async (payload) => {
    if (USE_MOCK) {
      setUser((prev) => ({
        ...prev,
        email: payload.email || prev?.email,
        name: payload.newUsername || prev?.name,
      }))
      return { ok: true, mocked: true }
    }
    const res = await httpClient.patch(HTTP_ENDPOINTS.auth.updateProfile, payload)
    if (res.data?.token) window.localStorage.setItem('netsentry.token', res.data.token)
    if (res.data?.user) setUser(res.data.user)
    return res.data
  }, [])

  return (
    <AuthContext.Provider value={{ user, loading, login, logout, updateProfile, isAuthenticated: !!user }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within AuthProvider')
  return ctx
}
