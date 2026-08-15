import React, { useState } from 'react'
import { useApi } from '../hooks/useApi.js'
import { useWebSocketChannel } from '../hooks/useWebSocket.js'
import { HTTP_ENDPOINTS, WS_CHANNELS } from '../api/endpoints.js'
import { AlertTriangle, Info, ShieldAlert, X } from 'lucide-react'
import FilterBar from '../components/UI/FilterBar.jsx'

function LevelIcon({ level }) {
  if (level === 'critical') return <ShieldAlert size={14} className="text-critical shrink-0" />
  if (level === 'warning') return <AlertTriangle size={14} className="text-warning shrink-0" />
  return <Info size={14} className="text-info shrink-0" />
}

export default function Events() {
  const { data, loading, error } = useApi(HTTP_ENDPOINTS.events.list, {}, { pollIntervalMs: 15000 })
  const { data: live } = useWebSocketChannel(WS_CHANNELS.events)
  const [search, setSearch] = useState('')
  const [filters, setFilters] = useState({ level: '' })
  const [selected, setSelected] = useState(null)

  const raw = live ? [live, ...(data || [])] : (data || [])
  const list = raw.filter((e) => {
    const matchesSearch = !search ||
      (e.text || '').toLowerCase().includes(search.toLowerCase()) ||
      (e.source || '').toLowerCase().includes(search.toLowerCase())
    const matchesLevel = !filters.level || e.level === filters.level
    return matchesSearch && matchesLevel
  })

  return (
    <div className="grid grid-cols-12 gap-4">
      <div className={`card p-4 ${selected ? 'col-span-12 xl:col-span-8' : 'col-span-12'}`}>
        <div className="text-[14px] font-medium mb-3">Журнал событий</div>

        <FilterBar
          search={search}
          onSearchChange={setSearch}
          searchPlaceholder="Поиск по описанию или источнику..."
          filters={[
            { key: 'level', label: 'Уровень', options: [
              { value: 'critical', label: 'Критический' },
              { value: 'warning', label: 'Внимание' },
              { value: 'info', label: 'Инфо' },
            ] },
          ]}
          values={filters}
          onChange={(key, value) => setFilters((f) => ({ ...f, [key]: value }))}
        />

        {loading && <div className="text-muted text-[12px]">Загрузка...</div>}
        {error && <div className="text-critical text-[12px]">Не удалось загрузить события. Проверьте подключение к API.</div>}
        {!loading && !error && list.length === 0 && (
          <div className="text-muted text-[12px]">События не найдены — измените фильтры или поиск.</div>
        )}

        <div className="space-y-2">
          {list.map((e, i) => (
            <div
              key={i}
              onClick={() => setSelected(e)}
              className="flex items-start gap-2 text-[12px] border-b border-border/60 pb-2 last:border-0 cursor-pointer hover:bg-surface rounded-md px-1 -mx-1 transition"
            >
              <LevelIcon level={e.level} />
              <div className="flex-1">
                <div>{e.text}</div>
                <div className="text-muted text-[11px]">{e.source}</div>
              </div>
              <div className="text-muted text-[11px]">{e.time}</div>
            </div>
          ))}
        </div>
      </div>

      {selected && (
        <div className="col-span-12 xl:col-span-4 card p-4 h-fit sticky top-20">
          <div className="flex items-center justify-between mb-3">
            <div className="text-[14px] font-medium">Детали события</div>
            <button onClick={() => setSelected(null)} className="text-muted hover:text-[#1a2233]">
              <X size={16} />
            </button>
          </div>
          <div className="space-y-2 text-[13px]">
            <div className="flex items-center gap-2">
              <LevelIcon level={selected.level} />
              <span className="font-medium">{selected.text}</span>
            </div>
            <div className="text-muted text-[12px]">Источник: {selected.source}</div>
            <div className="text-muted text-[12px]">Время: {selected.time}</div>
          </div>
        </div>
      )}
    </div>
  )
}
