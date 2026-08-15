import React from 'react'
import { useApi } from '../hooks/useApi.js'
import { HTTP_ENDPOINTS } from '../api/endpoints.js'
import StatusBadge from '../components/UI/StatusBadge.jsx'
import { Shield, Plus } from 'lucide-react'

export default function Rules() {
  const { data } = useApi(HTTP_ENDPOINTS.rules.list)
  return (
    <div className="card p-4">
      <div className="flex items-start justify-between mb-1">
        <div>
          <div className="text-[14px] font-medium">Правила защиты от сетевых угроз</div>
          <p className="text-[12px] text-muted mt-1 max-w-xl">
            Здесь настраиваются правила анализа сетевого трафика: система сравнивает
            наблюдаемую активность с этими правилами и поднимает инцидент при обнаружении
            сетевой угрозы (несанкционированный доступ, сканирование портов, аномальный трафик и т.п.).
          </p>
        </div>
        <button className="h-9 px-3 rounded-lg bg-brand-500 text-white text-[12px] flex items-center gap-1 shrink-0">
          <Plus size={14} /> Новое правило
        </button>
      </div>
      <table className="w-full text-[12px] mt-3">
        <thead>
          <tr className="text-muted text-left border-b border-border">
            <th className="py-2 font-medium">Название</th>
            <th className="py-2 font-medium">Тип угрозы</th>
            <th className="py-2 font-medium">Статус</th>
          </tr>
        </thead>
        <tbody>
          {(data || []).map((r) => (
            <tr key={r.id} className="border-b border-border/60">
              <td className="py-2 flex items-center gap-2"><Shield size={14} className="text-brand-500" /> {r.name}</td>
              <td className="py-2 text-muted">{r.type}</td>
              <td className="py-2"><StatusBadge value={r.status} /></td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
