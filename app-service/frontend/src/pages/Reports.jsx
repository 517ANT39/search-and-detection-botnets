import React from 'react'
import { useApi } from '../hooks/useApi.js'
import { HTTP_ENDPOINTS } from '../api/endpoints.js'
import { FileBarChart, Download, Plus } from 'lucide-react'

export default function Reports() {
  const { data } = useApi(HTTP_ENDPOINTS.reports.list)
  return (
    <div className="card p-4">
      <div className="flex items-center justify-between mb-3">
        <div className="text-[14px] font-medium">Отчёты</div>
        <button className="h-9 px-3 rounded-lg bg-brand-500 text-white text-[12px] flex items-center gap-1">
          <Plus size={14} /> Сформировать отчёт
        </button>
      </div>
      <div className="space-y-2">
        {(data || []).map((r) => (
          <div key={r.id} className="flex items-center gap-3 border border-border rounded-xl2 p-3">
            <div className="w-9 h-9 rounded-lg bg-brand-50 text-brand-600 flex items-center justify-center">
              <FileBarChart size={16} />
            </div>
            <div className="flex-1">
              <div className="text-[13px]">{r.name}</div>
              <div className="text-[11px] text-muted">{r.date} · {r.format}</div>
            </div>
            <button className="w-8 h-8 rounded-lg border border-border flex items-center justify-center text-muted hover:text-brand-600">
              <Download size={14} />
            </button>
          </div>
        ))}
      </div>
    </div>
  )
}
