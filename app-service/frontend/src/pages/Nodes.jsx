import React, { useMemo, useState } from 'react'
import { Server, X, MapPin, Wifi } from 'lucide-react'
import { useApi } from '../hooks/useApi.js'
import { HTTP_ENDPOINTS } from '../api/endpoints.js'
import StatusBadge from '../components/UI/StatusBadge.jsx'
import FilterBar from '../components/UI/FilterBar.jsx'

export default function Nodes() {
  const { data, loading, error } = useApi(HTTP_ENDPOINTS.nodes.list)
  const [search, setSearch] = useState('')
  const [filters, setFilters] = useState({ status: '', group: '' })
  const [selected, setSelected] = useState(null)

  const nodes = data || []

  const groupOptions = useMemo(() => {
    const set = new Set(nodes.map((n) => n.group).filter(Boolean))
    return Array.from(set).map((g) => ({ value: g, label: g }))
  }, [nodes])

  const filtered = nodes.filter((n) => {
    const matchesSearch = !search ||
      (n.label || '').toLowerCase().includes(search.toLowerCase()) ||
      (n.ip || '').toLowerCase().includes(search.toLowerCase()) ||
      (n.group || '').toLowerCase().includes(search.toLowerCase())
    const matchesStatus = !filters.status || n.status === filters.status
    const matchesGroup = !filters.group || n.group === filters.group
    return matchesSearch && matchesStatus && matchesGroup
  })

  return (
    <div className="grid grid-cols-12 gap-4">
      <div className={`card p-4 ${selected ? 'col-span-12 xl:col-span-8' : 'col-span-12'}`}>
        <div className="text-[14px] font-medium mb-3">Узлы сети</div>

        <FilterBar
          search={search}
          onSearchChange={setSearch}
          searchPlaceholder="Поиск по имени, IP или площадке..."
          filters={[
            { key: 'status', label: 'Статус', options: [
              { value: 'ok', label: 'ОК' },
              { value: 'warning', label: 'Внимание' },
              { value: 'critical', label: 'Критический' },
            ] },
            { key: 'group', label: 'Площадка', options: groupOptions },
          ]}
          values={filters}
          onChange={(key, value) => setFilters((f) => ({ ...f, [key]: value }))}
        />

        {loading && <div className="text-muted text-[12px]">Загрузка...</div>}
        {error && <div className="text-critical text-[12px]">Не удалось получить список узлов. Проверьте подключение к API.</div>}
        {!loading && !error && filtered.length === 0 && (
          <div className="text-muted text-[12px]">Узлы не найдены — измените фильтры или поиск.</div>
        )}

        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-3">
          {filtered.map((n) => (
            <div
              key={n.id}
              onClick={() => setSelected(n)}
              className={`border rounded-xl2 p-3 flex items-center gap-3 cursor-pointer transition hover:shadow-md hover:border-brand-200 ${
                selected?.id === n.id ? 'border-brand-400 bg-brand-50/50' : 'border-border'
              }`}
            >
              <div className="w-9 h-9 rounded-lg bg-brand-50 text-brand-600 flex items-center justify-center shrink-0">
                <Server size={16} />
              </div>
              <div className="flex-1 min-w-0">
                <div className="text-[13px] font-medium truncate">{n.label || n.id}</div>
                <div className="text-[11px] text-muted truncate">{n.group}{n.ip ? ` · ${n.ip}` : ''}</div>
              </div>
              <StatusBadge value={n.status} />
            </div>
          ))}
        </div>
      </div>

      {selected && (
        <div className="col-span-12 xl:col-span-4 card p-4 h-fit sticky top-20">
          <div className="flex items-center justify-between mb-3">
            <div className="text-[14px] font-medium">Детали узла</div>
            <button onClick={() => setSelected(null)} className="text-muted hover:text-[#1a2233]">
              <X size={16} />
            </button>
          </div>
          <div className="space-y-3 text-[13px]">
            <div className="flex items-center gap-2">
              <div className="w-10 h-10 rounded-lg bg-brand-50 text-brand-600 flex items-center justify-center">
                <Server size={18} />
              </div>
              <div>
                <div className="font-medium">{selected.label || selected.id}</div>
                <StatusBadge value={selected.status} />
              </div>
            </div>
            <div className="grid grid-cols-[100px_1fr] gap-y-2 text-[12px] pt-2 border-t border-border">
              <div className="text-muted flex items-center gap-1"><MapPin size={12} /> Площадка</div>
              <div>{selected.group || '—'}</div>
              <div className="text-muted flex items-center gap-1"><Wifi size={12} /> IP-адрес</div>
              <div>{selected.ip || '—'}</div>
              <div className="text-muted">ID узла</div>
              <div className="truncate">{selected.id}</div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
