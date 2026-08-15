import React, { useEffect, useRef, useState } from 'react'
import { Bell, AlertTriangle, Info, ShieldAlert } from 'lucide-react'
import { useApi } from '../hooks/useApi.js'
import { useWebSocketChannel } from '../hooks/useWebSocket.js'
import { HTTP_ENDPOINTS, WS_CHANNELS } from '../api/endpoints.js'

function LevelIcon({ level }) {
  if (level === 'critical') return <ShieldAlert size={14} className="text-critical shrink-0" />
  if (level === 'warning') return <AlertTriangle size={14} className="text-warning shrink-0" />
  return <Info size={14} className="text-info shrink-0" />
}

/**
 * Колокольчик уведомлений. Список приходит с HTTP_ENDPOINTS.notifications.list,
 * реалтайм-пополнение — через WS_CHANNELS.notifications. Бейдж показывает
 * количество непрочитанных. Ничего не захардкожено — при подключении своего
 * backend достаточно, чтобы он отвечал по этим же путям/каналам.
 */
export default function NotificationBell() {
  const { data, refetch } = useApi(HTTP_ENDPOINTS.notifications.list, {}, { pollIntervalMs: 30000 })
  const { data: live } = useWebSocketChannel(WS_CHANNELS.notifications)
  const [open, setOpen] = useState(false)
  const [liveItems, setLiveItems] = useState([])
  const ref = useRef(null)

  useEffect(() => {
    if (live) setLiveItems((prev) => [live, ...prev].slice(0, 20))
  }, [live])

  useEffect(() => {
    function onClickOutside(e) {
      if (ref.current && !ref.current.contains(e.target)) setOpen(false)
    }
    document.addEventListener('mousedown', onClickOutside)
    return () => document.removeEventListener('mousedown', onClickOutside)
  }, [])

  const list = [...liveItems, ...(data || [])].slice(0, 20)
  const unread = list.filter((n) => !n.read).length

  return (
    <div className="relative" ref={ref}>
      <button
        onClick={() => { setOpen((v) => !v); if (!open) refetch() }}
        className="relative w-9 h-9 rounded-lg border border-border flex items-center justify-center text-[#4a5468] hover:bg-surface"
      >
        <Bell size={15} />
        {unread > 0 && (
          <span className="absolute -top-1 -right-1 min-w-[16px] h-4 px-0.5 rounded-full bg-critical text-white text-[10px] flex items-center justify-center">
            {unread > 9 ? '9+' : unread}
          </span>
        )}
      </button>

      {open && (
        <div className="absolute right-0 mt-2 w-80 bg-white border border-border rounded-xl2 shadow-card z-30 overflow-hidden">
          <div className="px-3 py-2.5 border-b border-border text-[13px] font-medium flex items-center justify-between">
            <span>Уведомления</span>
            {unread > 0 && <span className="text-[11px] text-muted">{unread} новых</span>}
          </div>
          <div className="max-h-80 overflow-y-auto">
            {list.length === 0 && (
              <div className="p-4 text-muted text-[12px] text-center">Нет новых уведомлений</div>
            )}
            {list.map((n, i) => (
              <div
                key={n.id ?? i}
                className={`flex items-start gap-2 px-3 py-2.5 border-b border-border/60 last:border-0 text-[12px] hover:bg-surface transition ${!n.read ? 'bg-brand-50/40' : ''}`}
              >
                <LevelIcon level={n.level} />
                <div className="flex-1 min-w-0">
                  <div className="text-[#1a2233]">{n.text}</div>
                  <div className="text-muted text-[11px] mt-0.5">{n.time}</div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
