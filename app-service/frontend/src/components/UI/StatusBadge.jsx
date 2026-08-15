import React from 'react'

const MAP = {
  critical: { text: 'Критический', bg: 'bg-red-50', color: 'text-critical' },
  high: { text: 'Высокий', bg: 'bg-orange-50', color: 'text-orange-500' },
  medium: { text: 'Средний', bg: 'bg-amber-50', color: 'text-warning' },
  low: { text: 'Низкий', bg: 'bg-slate-100', color: 'text-muted' },
  new: { text: 'Новый', bg: 'bg-blue-50', color: 'text-brand-600' },
  in_progress: { text: 'В работе', bg: 'bg-amber-50', color: 'text-warning' },
  closed: { text: 'Закрыт', bg: 'bg-slate-100', color: 'text-muted' },
  ok: { text: 'ОК', bg: 'bg-green-50', color: 'text-success' },
  warning: { text: 'Внимание', bg: 'bg-amber-50', color: 'text-warning' },
  active: { text: 'Активно', bg: 'bg-green-50', color: 'text-success' },
  disabled: { text: 'Выключено', bg: 'bg-slate-100', color: 'text-muted' },
  info: { text: 'Инфо', bg: 'bg-blue-50', color: 'text-info' },
  online: { text: 'Online', bg: 'bg-green-50', color: 'text-success' },
  offline: { text: 'Offline', bg: 'bg-slate-100', color: 'text-muted' },
  unknown: { text: 'Неизвестно', bg: 'bg-slate-100', color: 'text-muted' },
}

export default function StatusBadge({ value }) {
  const cfg = MAP[value] || { text: value, bg: 'bg-slate-100', color: 'text-muted' }
  return (
    <span className={`px-2 py-0.5 rounded-md text-[11px] font-medium ${cfg.bg} ${cfg.color}`}>
      {cfg.text}
    </span>
  )
}
