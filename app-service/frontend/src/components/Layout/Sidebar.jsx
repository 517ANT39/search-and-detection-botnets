import React from 'react'
import { NavLink } from 'react-router-dom'
import {
  LayoutGrid, Share2, Server, AlertTriangle, ListTree, Activity,
  ShieldCheck, FileBarChart, Settings, ShieldPlus, ChevronLeft,
} from 'lucide-react'

const NAV = [
  { to: '/', icon: LayoutGrid, label: 'Обзор', end: true },
  { to: '/topology', icon: Share2, label: 'Топология' },
  { to: '/nodes', icon: Server, label: 'Узлы' },
  { to: '/incidents', icon: AlertTriangle, label: 'Инциденты' },
  { to: '/events', icon: ListTree, label: 'События' },
  { to: '/traffic', icon: Activity, label: 'Трафик' },
  { to: '/rules', icon: ShieldCheck, label: 'Правила' },
  { to: '/reports', icon: FileBarChart, label: 'Отчёты' },
  { to: '/settings', icon: Settings, label: 'Настройки' },
]

export default function Sidebar({ collapsed, onToggle }) {
  return (
    <aside className={`h-screen sticky top-0 bg-panel border-r border-border flex flex-col transition-all ${collapsed ? 'w-[76px]' : 'w-[240px]'}`}>
      <div className="flex items-center gap-2 px-5 h-16 border-b border-border">
        <div className="w-8 h-8 rounded-lg bg-brand-500 flex items-center justify-center text-white shrink-0">
          <ShieldPlus size={18} />
        </div>
        {!collapsed && (
          <div>
            <div className="font-semibold text-[15px] tracking-wide leading-none">NETSENTRY</div>
            <div className="text-[11px] text-muted leading-none mt-1">Анализ сетевой активности</div>
          </div>
        )}
      </div>

      <nav className="flex-1 py-3 px-2 space-y-1 overflow-y-auto">
        {NAV.map(({ to, icon: Icon, label, end }) => (
          <NavLink
            key={to}
            to={to}
            end={end}
            className={({ isActive }) =>
              `flex items-center gap-3 px-3 h-10 rounded-lg text-[14px] transition-colors ${
                isActive ? 'bg-brand-50 text-brand-600 font-medium' : 'text-[#4a5468] hover:bg-surface'
              }`
            }
          >
            <Icon size={18} className="shrink-0" />
            {!collapsed && <span>{label}</span>}
          </NavLink>
        ))}
      </nav>

      <button
        onClick={onToggle}
        className="flex items-center gap-2 px-5 h-12 border-t border-border text-muted hover:text-brand-600 text-[13px]"
      >
        <ChevronLeft size={16} className={`transition-transform ${collapsed ? 'rotate-180' : ''}`} />
        {!collapsed && 'Свернуть'}
      </button>
    </aside>
  )
}
