import React, { useState } from 'react'
import { useApi } from '../hooks/useApi.js'
import { HTTP_ENDPOINTS } from '../api/endpoints.js'
import { setApiBaseUrl } from '../api/httpClient.js'
import { useAuth } from '../context/AuthContext.jsx'
import { User, Mail, Lock, Save } from 'lucide-react'

export default function Settings() {
  const { data } = useApi(HTTP_ENDPOINTS.settings.get)
  const { user, updateProfile } = useAuth()
  const [apiUrl, setApiUrl] = useState(import.meta.env.VITE_API_BASE_URL || '/api')
  const [wsUrl, setWsUrl] = useState(import.meta.env.VITE_WS_URL || '/ws')

  const [email, setEmail] = useState(user?.email || '')
  const [username, setUsername] = useState(user?.username || user?.name || '')
  const [currentPassword, setCurrentPassword] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [profileMsg, setProfileMsg] = useState(null)
  const [savingProfile, setSavingProfile] = useState(false)

  function saveConnection() {
    setApiBaseUrl(apiUrl)
    window.localStorage.setItem('netsentry.wsUrl', wsUrl)
    alert('Настройки подключения сохранены. Перезагрузите страницу для применения WS-адреса.')
  }

  async function saveProfile(e) {
    e.preventDefault()
    setProfileMsg(null)

    if ((newPassword || username !== (user?.username || user?.name)) && !currentPassword) {
      setProfileMsg({ type: 'error', text: 'Введите текущий пароль, чтобы подтвердить изменения.' })
      return
    }
    if (newPassword && newPassword !== confirmPassword) {
      setProfileMsg({ type: 'error', text: 'Новый пароль и подтверждение не совпадают.' })
      return
    }

    setSavingProfile(true)
    try {
      await updateProfile({
        email: email || undefined,
        newUsername: username && username !== (user?.username || user?.name) ? username : undefined,
        newPassword: newPassword || undefined,
        currentPassword: currentPassword || undefined,
      })
      setProfileMsg({ type: 'success', text: 'Данные профиля успешно обновлены.' })
      setCurrentPassword(''); setNewPassword(''); setConfirmPassword('')
    } catch (err) {
      setProfileMsg({ type: 'error', text: err?.response?.data?.detail || 'Не удалось сохранить изменения.' })
    } finally {
      setSavingProfile(false)
    }
  }

  return (
    <div className="space-y-4">
      {/* Профиль пользователя: смена email / логина / пароля */}
      <div className="card p-4">
        <div className="text-[14px] font-medium mb-3 flex items-center gap-2">
          <User size={16} className="text-brand-500" /> Профиль пользователя
        </div>
        <form onSubmit={saveProfile} className="grid grid-cols-1 md:grid-cols-2 gap-3">
          <div>
            <label className="text-[12px] text-muted flex items-center gap-1"><Mail size={12} /> Email</label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="mt-1 w-full h-9 px-3 rounded-lg border border-border text-[13px]"
              placeholder="you@company.local"
            />
          </div>
          <div>
            <label className="text-[12px] text-muted flex items-center gap-1"><User size={12} /> Логин</label>
            <input
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              className="mt-1 w-full h-9 px-3 rounded-lg border border-border text-[13px]"
            />
          </div>
          <div>
            <label className="text-[12px] text-muted flex items-center gap-1"><Lock size={12} /> Текущий пароль</label>
            <input
              type="password"
              value={currentPassword}
              onChange={(e) => setCurrentPassword(e.target.value)}
              className="mt-1 w-full h-9 px-3 rounded-lg border border-border text-[13px]"
              placeholder="Требуется для подтверждения"
            />
          </div>
          <div />
          <div>
            <label className="text-[12px] text-muted flex items-center gap-1"><Lock size={12} /> Новый пароль</label>
            <input
              type="password"
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
              className="mt-1 w-full h-9 px-3 rounded-lg border border-border text-[13px]"
              placeholder="Оставьте пустым, если не меняете"
            />
          </div>
          <div>
            <label className="text-[12px] text-muted flex items-center gap-1"><Lock size={12} /> Подтверждение пароля</label>
            <input
              type="password"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              className="mt-1 w-full h-9 px-3 rounded-lg border border-border text-[13px]"
            />
          </div>

          {profileMsg && (
            <div className={`md:col-span-2 text-[12px] rounded-lg px-3 py-2 ${
              profileMsg.type === 'error' ? 'bg-critical/10 text-critical' : 'bg-success/10 text-success'
            }`}>
              {profileMsg.text}
            </div>
          )}

          <div className="md:col-span-2">
            <button
              type="submit"
              disabled={savingProfile}
              className="h-9 px-4 rounded-lg bg-brand-500 text-white text-[12px] flex items-center gap-1.5 disabled:opacity-60"
            >
              <Save size={13} /> {savingProfile ? 'Сохранение…' : 'Сохранить профиль'}
            </button>
          </div>
        </form>
      </div>

      <div className="card p-4">
        <div className="text-[14px] font-medium mb-3">Подключение к backend</div>
        <p className="text-[12px] text-muted mb-3">
          Значения по умолчанию берутся из .env (VITE_API_BASE_URL, VITE_WS_URL).
          Здесь их можно переопределить без пересборки проекта — они сохраняются в localStorage.
        </p>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          <div>
            <label className="text-[12px] text-muted">HTTP API base URL</label>
            <input value={apiUrl} onChange={(e) => setApiUrl(e.target.value)}
              className="mt-1 w-full h-9 px-3 rounded-lg border border-border text-[13px]" />
          </div>
          <div>
            <label className="text-[12px] text-muted">WebSocket URL</label>
            <input value={wsUrl} onChange={(e) => setWsUrl(e.target.value)}
              className="mt-1 w-full h-9 px-3 rounded-lg border border-border text-[13px]" />
          </div>
        </div>
        <button onClick={saveConnection} className="mt-3 h-9 px-4 rounded-lg bg-brand-500 text-white text-[12px]">
          Сохранить
        </button>
      </div>

      <div className="card p-4">
        <div className="text-[14px] font-medium mb-3">Кластеры</div>
        <div className="flex flex-wrap gap-2">
          {(data?.clusters || []).map((c) => (
            <span key={c} className="px-3 py-1 rounded-lg bg-surface border border-border text-[12px]">{c}</span>
          ))}
        </div>
      </div>

      <div className="card p-4 text-[12px] text-muted">
        Интеграция с SIEM: {data?.siemIntegration ? 'активна' : 'выключена'} · Версия: {data?.version || '—'}
      </div>
    </div>
  )
}
