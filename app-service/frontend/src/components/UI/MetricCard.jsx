import React from 'react'
import { ArrowUpRight, ArrowDownRight } from 'lucide-react'

export default function MetricCard({ label, value, unit, sub, deltaLabel, deltaPositive = true, accent, children, onClick }) {
  const clickable = typeof onClick === 'function'
  return (
    <div
      onClick={onClick}
      className={`card p-4 flex flex-col gap-2 min-w-[150px] flex-1 transition ${
        clickable ? 'cursor-pointer hover:shadow-md hover:-translate-y-0.5 hover:border-brand-200' : ''
      }`}
    >
      <div className="text-[12px] text-muted">{label}</div>
      <div className="flex items-baseline gap-1">
        <span className={`text-2xl font-semibold ${accent || 'text-[#1a2233]'}`}>{value}</span>
        {unit && <span className="text-[13px] text-muted">{unit}</span>}
      </div>
      {children}
      {sub && <div className="text-[12px] text-muted">{sub}</div>}
      {deltaLabel && (
        <div className={`flex items-center gap-1 text-[12px] ${deltaPositive ? 'text-success' : 'text-critical'}`}>
          {deltaPositive ? <ArrowUpRight size={13} /> : <ArrowDownRight size={13} />} {deltaLabel}
        </div>
      )}
    </div>
  )
}
