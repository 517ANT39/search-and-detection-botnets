import React, { useEffect, useState } from 'react'
import { Search, SlidersHorizontal, RefreshCw, Download } from 'lucide-react'
import { useWebSocketChannel } from '../../hooks/useWebSocket.js'
import { WS_CHANNELS } from '../../api/endpoints.js'
import { triggerGlobalRefresh } from '../../utils/refreshBus.js'
import UserMenu from '../UserMenu.jsx'
import NotificationBell from '../NotificationBell.jsx'

export default function Topbar({ title = 'Обзор' }) {
  const [now, setNow] = useState(new Date())
  const [refreshing, setRefreshing] = useState(false)
  const { status } = useWebSocketChannel(WS_CHANNELS.metrics)

  useEffect(() => {
    const id = setInterval(() => setNow(new Date()), 1000)
    return () => clearInterval(id)
  }, [])

  const dateStr = now.toLocaleDateString('ru-RU', { day: '2-digit', month: '2-digit' })
  const timeStr = now.toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit' })

  function handleRefresh() {
    setRefreshing(true)
    // Перезапрашиваем данные во всех смонтированных useApi()-хуках на странице
    triggerGlobalRefresh()
    // Плавно прокручиваем контент к началу страницы
    document.getElementById('main-scroll')?.scrollTo({ top: 0, behavior: 'smooth' })
    setTimeout(() => setRefreshing(false), 700)
  }

  return (
    <header className="h-16 sticky top-0 z-10 bg-panel/90 backdrop-blur border-b border-border flex items-center gap-4 px-5">
      <select className="h-9 px-3 rounded-lg border border-border text-[13px] bg-white text-[#4a5468] focus:outline-none">
        <option>Все кластеры</option>
        <option>Москва</option>
        <option>Санкт-Петербург</option>
        <option>Облако</option>
      </select>

      <div className="flex items-center gap-2 h-9 px-3 rounded-lg border border-border bg-white flex-1 max-w-md text-[13px] text-muted">
        <Search size={15} />
        <input placeholder="Поиск узлов, пользователей, событий..." className="outline-none w-full bg-transparent placeholder:text-muted" />
      </div>

      <button className="h-9 px-3 rounded-lg border border-border text-[13px] flex items-center gap-2 text-[#4a5468] hover:bg-surface">
        <SlidersHorizontal size={15} /> Фильтры
      </button>

      <div className="ml-auto flex items-center gap-3">
        <div className="h-9 px-3 rounded-lg border border-border text-[13px] flex items-center gap-2 text-[#4a5468]">
          Последние 24 часа
        </div>
        <div className="hidden md:flex items-center gap-2 text-[12px] text-muted">
          <span>{dateStr} {timeStr}</span>
          <span className={`w-2 h-2 rounded-full ${status === 'connected' ? 'bg-success' : 'bg-warning'}`} title={status} />
        </div>
        <button
          onClick={handleRefresh}
          className="w-9 h-9 rounded-lg border border-border flex items-center justify-center text-[#4a5468] hover:bg-surface"
          title="Обновить данные"
        >
          <RefreshCw size={15} className={refreshing ? 'animate-spin' : ''} />
        </button>
        <button className="w-9 h-9 rounded-lg border border-border flex items-center justify-center text-[#4a5468] hover:bg-surface" title="Скачать отчёт">
          <Download size={15} />
        </button>
        <NotificationBell />
        <UserMenu />
      </div>
    </header>
  )
}
