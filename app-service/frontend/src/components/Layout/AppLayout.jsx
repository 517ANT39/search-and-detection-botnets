import React, { useState } from 'react'
import { Outlet, useLocation } from 'react-router-dom'
import Sidebar from './Sidebar.jsx'
import Topbar from './Topbar.jsx'

const TITLES = {
  '/': 'Обзор', '/topology': 'Топология', '/nodes': 'Узлы', '/incidents': 'Инциденты',
  '/events': 'События', '/traffic': 'Трафик', '/rules': 'Правила', '/reports': 'Отчёты', '/settings': 'Настройки',
}

export default function AppLayout() {
  const [collapsed, setCollapsed] = useState(false)
  const location = useLocation()
  const title = TITLES[location.pathname] || 'NetSentry'

  return (
    <div className="flex min-h-screen bg-surface">
      <Sidebar collapsed={collapsed} onToggle={() => setCollapsed((v) => !v)} />
      <div className="flex-1 min-w-0 flex flex-col">
        <Topbar title={title} />
        <main id="main-scroll" className="flex-1 p-5 overflow-y-auto max-h-screen">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
