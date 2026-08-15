import React, { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { User, LogOut } from 'lucide-react'
import { useAuth } from '../context/AuthContext.jsx'

/**
 * Минималистичное меню профиля пользователя.
 * Клик по аватару открывает выпадающую панель с именем, ролью,
 * email и кнопкой выхода. Данные берутся из AuthContext (user),
 * который, в свою очередь, наполняется ответом HTTP_ENDPOINTS.auth.me
 * (см. src/context/AuthContext.jsx) — никаких захардкоженных полей.
 */
export default function UserMenu() {
  const { user, logout } = useAuth()
  const [open, setOpen] = useState(false)
  const ref = useRef(null)
  const navigate = useNavigate()

  useEffect(() => {
    function onClickOutside(e) {
      if (ref.current && !ref.current.contains(e.target)) setOpen(false)
    }
    document.addEventListener('mousedown', onClickOutside)
    return () => document.removeEventListener('mousedown', onClickOutside)
  }, [])

  async function handleLogout() {
    await logout()
    navigate('/login')
  }

  const initials = (user?.name || user?.username || '?')
    .split(' ')
    .map((p) => p[0])
    .slice(0, 2)
    .join('')
    .toUpperCase()

  return (
    <div className="relative" ref={ref}>
      <button
        onClick={() => setOpen((v) => !v)}
        className="w-9 h-9 rounded-full bg-brand-100 text-brand-600 flex items-center justify-center text-[12px] font-semibold hover:ring-2 hover:ring-brand-200 transition"
        title={user?.name || 'Профиль'}
      >
        {initials || <User size={16} />}
      </button>

      {open && (
        <div className="absolute right-0 mt-2 w-60 bg-white border border-border rounded-xl2 shadow-card p-4 z-30 text-[13px]">
          <div className="flex items-center gap-3 mb-3">
            <div className="w-10 h-10 rounded-full bg-brand-100 text-brand-600 flex items-center justify-center text-[13px] font-semibold shrink-0">
              {initials || <User size={16} />}
            </div>
            <div className="min-w-0">
              <div className="font-medium text-[#1a2233] truncate">{user?.name || user?.username || 'Пользователь'}</div>
              <div className="text-muted text-[12px] truncate">{user?.role || '—'}</div>
            </div>
          </div>

          {user?.email && (
            <div className="text-muted text-[12px] truncate mb-3 pb-3 border-b border-border">
              {user.email}
            </div>
          )}

          <button
            onClick={handleLogout}
            className="w-full flex items-center justify-center gap-2 h-9 rounded-lg text-critical hover:bg-red-50 transition text-[13px] font-medium"
          >
            <LogOut size={14} /> Выйти
          </button>
        </div>
      )}
    </div>
  )
}
