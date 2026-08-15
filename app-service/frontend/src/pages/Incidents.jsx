import React, { useState } from 'react'
import { useApi } from '../hooks/useApi.js'
import { useWebSocketChannel } from '../hooks/useWebSocket.js'
import { HTTP_ENDPOINTS, WS_CHANNELS } from '../api/endpoints.js'
import StatusBadge from '../components/UI/StatusBadge.jsx'
import FilterBar from '../components/UI/FilterBar.jsx'

export default function Incidents() {
  const { data, loading, error } = useApi(HTTP_ENDPOINTS.incidents.list)
  const { data: liveUpdate } = useWebSocketChannel(WS_CHANNELS.incidents)
  const [selected, setSelected] = useState(null)
  const [search, setSearch] = useState('')
  const [filters, setFilters] = useState({ level: '', status: '' })

  const list = (data || []).filter((row) => {
    const matchesSearch = !search ||
      (row.title || '').toLowerCase().includes(search.toLowerCase()) ||
      (row.source || '').toLowerCase().includes(search.toLowerCase()) ||
      (row.id || '').toLowerCase().includes(search.toLowerCase())
    const matchesLevel = !filters.level || row.level === filters.level
    const matchesStatus = !filters.status || row.status === filters.status
    return matchesSearch && matchesLevel && matchesStatus
  })

  return (
    <div className="grid grid-cols-12 gap-4">
      <div className="col-span-12 xl:col-span-8 card p-4">
        <div className="flex items-center justify-between mb-3">
          <div className="text-[14px] font-medium">Инциденты</div>
          {liveUpdate && <span className="text-[11px] text-success">Новое обновление получено по WebSocket</span>}
        </div>

        <FilterBar
          search={search}
          onSearchChange={setSearch}
          searchPlaceholder="Поиск по названию, источнику, ID..."
          filters={[
            { key: 'level', label: 'Уровень', options: [
              { value: 'critical', label: 'Критический' },
              { value: 'high', label: 'Высокий' },
              { value: 'medium', label: 'Средний' },
              { value: 'low', label: 'Низкий' },
            ] },
            { key: 'status', label: 'Статус', options: [
              { value: 'new', label: 'Новый' },
              { value: 'in_progress', label: 'В работе' },
              { value: 'closed', label: 'Закрыт' },
            ] },
          ]}
          values={filters}
          onChange={(key, value) => setFilters((f) => ({ ...f, [key]: value }))}
        />

        {loading && <div className="text-muted text-[12px]">Загрузка...</div>}
        {error && <div className="text-critical text-[12px]">Не удалось загрузить инциденты. Проверьте подключение к API.</div>}
        {!loading && !error && list.length === 0 && (
          <div className="text-muted text-[12px]">Инциденты не найдены — измените фильтры или поиск.</div>
        )}

        {list.length > 0 && (
          <table className="w-full text-[12px]">
            <thead>
              <tr className="text-muted text-left border-b border-border">
                <th className="py-2 font-medium">Время</th>
                <th className="py-2 font-medium">Уровень</th>
                <th className="py-2 font-medium">Событие</th>
                <th className="py-2 font-medium">Источник</th>
                <th className="py-2 font-medium">Статус</th>
              </tr>
            </thead>
            <tbody>
              {list.map((row) => (
                <tr key={row.id} onClick={() => setSelected(row)}
                  className={`border-b border-border/60 cursor-pointer hover:bg-surface transition ${selected?.id === row.id ? 'bg-brand-50' : ''}`}>
                  <td className="py-2">{row.time}</td>
                  <td className="py-2"><StatusBadge value={row.level} /></td>
                  <td className="py-2">{row.title}</td>
                  <td className="py-2 text-muted">{row.source}</td>
                  <td className="py-2"><StatusBadge value={row.status} /></td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
      <div className="col-span-12 xl:col-span-4 card p-4 h-fit sticky top-20">
        <div className="text-[14px] font-medium mb-3">Детали инцидента</div>
        {selected ? (
          <div className="space-y-2 text-[12px]">
            <div className="text-muted">ID: {selected.id}</div>
            <div className="font-medium text-[13px]">{selected.title}</div>
            {selected.description && <div className="text-muted">{selected.description}</div>}
            <div className="text-muted">Источник: {selected.source}</div>
            <div className="text-muted">Назначение: {selected.target}</div>
            {selected.category && <div className="text-muted">Категория: {selected.category}</div>}
            {selected.policy && <div className="text-muted">Правило: {selected.policy}</div>}
            <StatusBadge value={selected.status} />
            {Array.isArray(selected.timeline) && selected.timeline.length > 0 && (
              <div className="pt-2 mt-2 border-t border-border space-y-1.5">
                <div className="text-[12px] font-medium">Хронология</div>
                {selected.timeline.map((t, i) => (
                  <div key={i} className="flex gap-2 text-[11px]">
                    <span className="text-muted shrink-0">{t.time}</span>
                    <span>{t.text}{t.node ? ` — ${t.node}` : ''}</span>
                  </div>
                ))}
              </div>
            )}
          </div>
        ) : <div className="text-muted text-[12px]">Выберите инцидент из списка.</div>}
      </div>
    </div>
  )
}
