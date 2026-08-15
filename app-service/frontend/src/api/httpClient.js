import axios from 'axios'

/**
 * Универсальный HTTP-клиент.
 * baseURL полностью настраивается через переменную окружения VITE_API_BASE_URL
 * (см. .env.example). Ничего не захардкожено — при необходимости можно также
 * переопределить конфигурацию через localStorage (ключ 'netsentry.apiBaseUrl'),
 * что удобно для переключения окружений без пересборки.
 */

function resolveBaseURL() {
  const fromStorage = typeof window !== 'undefined'
    ? window.localStorage.getItem('netsentry.apiBaseUrl')
    : null
  return fromStorage || import.meta.env.VITE_API_BASE_URL || '/api'
}

export const httpClient = axios.create({
  baseURL: resolveBaseURL(),
  timeout: 15000,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Подстановка токена авторизации в каждый запрос.
// Название заголовка и схема настраиваются через .env (VITE_AUTH_HEADER / VITE_AUTH_SCHEME)
httpClient.interceptors.request.use((config) => {
  const token = window.localStorage.getItem('netsentry.token')
  const headerName = import.meta.env.VITE_AUTH_HEADER || 'Authorization'
  const scheme = import.meta.env.VITE_AUTH_SCHEME || 'Bearer'
  if (token) {
    config.headers[headerName] = scheme ? `${scheme} ${token}` : token
  }
  return config
})

// Единая обработка ошибок / истёкшего токена.
// Подключите здесь свою логику редиректа на /login при 401, если требуется.
httpClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response && error.response.status === 401) {
      window.dispatchEvent(new CustomEvent('netsentry:unauthorized'))
    }
    return Promise.reject(error)
  }
)

export function setApiBaseUrl(url) {
  window.localStorage.setItem('netsentry.apiBaseUrl', url)
  httpClient.defaults.baseURL = url
}

export default httpClient
