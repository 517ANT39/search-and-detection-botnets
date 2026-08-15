import React, { useState } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import { ShieldPlus, Lock, User } from 'lucide-react'
import { useAuth } from '../context/AuthContext.jsx'

export default function Login() {
  const { login } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const from = location.state?.from?.pathname || '/'

  async function handleSubmit(e) {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      await login(username, password)
      navigate(from, { replace: true })
    } catch (err) {
      setError('Не удалось выполнить вход. Проверьте логин и пароль или настройки API.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-surface flex items-center justify-center px-4">
      <div className="w-full max-w-sm card p-8">
        <div className="flex flex-col items-center mb-6">
          <div className="w-11 h-11 rounded-xl bg-brand-500 text-white flex items-center justify-center mb-3">
            <ShieldPlus size={22} />
          </div>
          <div className="font-semibold text-lg tracking-wide">NETSENTRY</div>
          <div className="text-[12px] text-muted">Анализ сетевой активности</div>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="text-[12px] text-muted">Логин</label>
            <div className="mt-1 flex items-center gap-2 h-10 px-3 rounded-lg border border-border bg-white">
              <User size={15} className="text-muted" />
              <input
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                className="outline-none w-full text-[13px]"
                placeholder="admin"
                autoFocus
              />
            </div>
          </div>
          <div>
            <label className="text-[12px] text-muted">Пароль</label>
            <div className="mt-1 flex items-center gap-2 h-10 px-3 rounded-lg border border-border bg-white">
              <Lock size={15} className="text-muted" />
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="outline-none w-full text-[13px]"
                placeholder="••••••••"
              />
            </div>
          </div>

          {error && <div className="text-[12px] text-critical">{error}</div>}

          <button
            type="submit"
            disabled={loading}
            className="w-full h-10 rounded-lg bg-brand-500 hover:bg-brand-600 text-white text-[13px] font-medium transition-colors disabled:opacity-60"
          >
            {loading ? 'Вход...' : 'Войти'}
          </button>
        </form>

        <div className="mt-5 text-[11px] text-muted text-center">
          Аутентификация настраивается в src/api/endpoints.js (auth.login) и src/context/AuthContext.jsx
        </div>
      </div>
    </div>
  )
}
