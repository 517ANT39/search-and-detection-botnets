import React, { useState, useRef, useLayoutEffect, useCallback, useMemo } from 'react'
import { Server, ShieldAlert, Cloud, Router, X, Wifi, ZoomIn, ZoomOut, Maximize } from 'lucide-react'
import { useApi } from '../hooks/useApi.js'
import { HTTP_ENDPOINTS } from '../api/endpoints.js'
import StatusBadge from './UI/StatusBadge.jsx'

// Расположение групп (площадок) в процентах контейнера — соответствует макету.
const LAYOUT = {
  'Офис Москва': { x: 6, y: 6 },
  'ЦОД': { x: 62, y: 4 },
  'Офис СПб': { x: 6, y: 54 },
  'Облако': { x: 62, y: 54 },
}

function iconFor(status) {
  if (status === 'critical') return <ShieldAlert size={13} className="text-critical shrink-0" />
  if (status === 'warning') return <ShieldAlert size={13} className="text-warning shrink-0" />
  return <Server size={13} className="text-[#4a5468] shrink-0" />
}

function statusDot(status) {
  const color = status === 'critical' ? 'bg-critical' : status === 'warning' ? 'bg-warning' : 'bg-success'
  return <span className={`inline-block w-1.5 h-1.5 rounded-full ${color}`} />
}

export default function TopologyMap() {
  const { data } = useApi(HTTP_ENDPOINTS.topology.graph)
  const nodes = data?.nodes || []
  const [selected, setSelected] = useState(null)

  const containerRef = useRef(null)
  const internetRef = useRef(null)
  const groupRefs = useRef({})
  const [lines, setLines] = useState([])
  const [scale, setScale] = useState(1)
  const [pan, setPan] = useState({ x: 0, y: 0 })
  const dragState = useRef(null)

  // ВАЖНО: groups должен быть мемоизирован. Раньше объект пересоздавался
  // на КАЖДЫЙ рендер (даже из-за смены scale/pan/selected), из-за чего
  // recalcLines (зависящий от groups) тоже пересоздавался каждый раз,
  // useLayoutEffect срабатывал бесконечно и вызывал setLines по кругу —
  // отсюда "Maximum update depth exceeded".
  const groupKey = useMemo(
    () => nodes.map((n) => `${n.group}:${n.id}`).sort().join('|'),
    [nodes]
  )
  const groups = useMemo(() => {
    return nodes.reduce((acc, n) => {
      (acc[n.group] = acc[n.group] || []).push(n)
      return acc
    }, {})
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [groupKey])

  // Пересчёт координат линий связи «площадка -> Интернет» при монтировании/ресайзе
  const recalcLines = useCallback(() => {
    const container = containerRef.current
    const internetEl = internetRef.current
    if (!container || !internetEl) return
    const cRect = container.getBoundingClientRect()
    const iRect = internetEl.getBoundingClientRect()
    const iCenter = {
      x: (iRect.left + iRect.width / 2 - cRect.left) / scale,
      y: (iRect.top + iRect.height / 2 - cRect.top) / scale,
    }
    const newLines = Object.keys(groups).map((group) => {
      const el = groupRefs.current[group]
      if (!el) return null
      const r = el.getBoundingClientRect()
      const center = {
        x: (r.left + r.width / 2 - cRect.left) / scale,
        y: (r.top + r.height / 2 - cRect.top) / scale,
      }
      return { group, x1: center.x, y1: center.y, x2: iCenter.x, y2: iCenter.y }
    }).filter(Boolean)

    // Дополнительная защита: не обновляем state, если координаты не изменились —
    // предотвращает лишние ре-рендеры даже при корректных зависимостях.
    setLines((prev) => {
      const same =
        prev.length === newLines.length &&
        prev.every((p, i) => {
          const n = newLines[i]
          return n && p.group === n.group && p.x1 === n.x1 && p.y1 === n.y1 && p.x2 === n.x2 && p.y2 === n.y2
        })
      return same ? prev : newLines
    })
  }, [groups, scale])

  useLayoutEffect(() => {
    recalcLines()
    const onResize = () => recalcLines()
    window.addEventListener('resize', onResize)
    return () => window.removeEventListener('resize', onResize)
  }, [recalcLines, groupKey])

  // Zoom controls
  const zoomIn = () => setScale((s) => Math.min(2, +(s + 0.2).toFixed(2)))
  const zoomOut = () => setScale((s) => Math.max(0.5, +(s - 0.2).toFixed(2)))
  const resetView = () => { setScale(1); setPan({ x: 0, y: 0 }) }

  // Pan (drag) — работает мышью по фону карты
  const onMouseDown = (e) => {
    dragState.current = { startX: e.clientX, startY: e.clientY, origin: { ...pan } }
  }
  const onMouseMove = (e) => {
    if (!dragState.current) return
    const dx = e.clientX - dragState.current.startX
    const dy = e.clientY - dragState.current.startY
    setPan({ x: dragState.current.origin.x + dx, y: dragState.current.origin.y + dy })
  }
  const onMouseUp = () => { dragState.current = null }

  return (
    <div className="relative">
      {/* Панель управления масштабом */}
      <div className="absolute right-2 top-2 z-20 flex gap-1 bg-white border border-border rounded-lg shadow-card p-1">
        <button onClick={zoomOut} className="p-1.5 rounded-md hover:bg-surface text-muted hover:text-[#1a2233]" title="Уменьшить">
          <ZoomOut size={14} />
        </button>
        <button onClick={resetView} className="p-1.5 rounded-md hover:bg-surface text-muted hover:text-[#1a2233]" title="Сбросить масштаб">
          <Maximize size={14} />
        </button>
        <button onClick={zoomIn} className="p-1.5 rounded-md hover:bg-surface text-muted hover:text-[#1a2233]" title="Увеличить">
          <ZoomIn size={14} />
        </button>
      </div>

      <div
        ref={containerRef}
        className="relative h-[420px] rounded-lg bg-surface overflow-hidden cursor-grab active:cursor-grabbing"
        onMouseDown={onMouseDown}
        onMouseMove={onMouseMove}
        onMouseUp={onMouseUp}
        onMouseLeave={onMouseUp}
      >
        <div
          className="absolute inset-0 origin-center transition-transform"
          style={{ transform: `translate(${pan.x}px, ${pan.y}px) scale(${scale})` }}
        >
          {/* SVG-слой с линиями связи площадок с Интернетом */}
          <svg className="absolute inset-0 w-full h-full pointer-events-none" style={{ overflow: 'visible' }}>
            {lines.map((l) => (
              <line
                key={l.group}
                x1={l.x1} y1={l.y1} x2={l.x2} y2={l.y2}
                stroke="#c7d2e3" strokeWidth={1.5} strokeDasharray="4 3"
              />
            ))}
          </svg>

          {/* Центральный узел «Интернет» */}
          <div
            ref={internetRef}
            className="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 flex flex-col items-center z-10"
          >
            <div className="w-12 h-12 rounded-full bg-white border border-border shadow-card flex items-center justify-center text-brand-500">
              <Cloud size={20} />
            </div>
            <span className="text-[11px] text-muted mt-1">Интернет</span>
          </div>

          {Object.entries(groups).map(([group, items]) => {
            const pos = LAYOUT[group] || { x: 40, y: 40 }
            return (
              <div
                key={group}
                ref={(el) => { groupRefs.current[group] = el }}
                className="absolute"
                style={{ left: `${pos.x}%`, top: `${pos.y}%` }}
              >
                <div className="bg-white border border-border rounded-lg shadow-card p-3 w-[210px]">
                  <div className="text-[11px] font-medium text-[#1a2233] mb-2 flex items-center gap-1">
                    <Router size={13} className="text-brand-500" /> {group}
                    <span className="ml-auto text-[10px] text-muted">{items.length} узлов</span>
                  </div>
                  <div className="space-y-1.5">
                    {items.map((n) => (
                      <button
                        key={n.id}
                        onClick={() => setSelected(n)}
                        className={`w-full flex items-center gap-1.5 text-[11px] text-[#4a5468] rounded px-1 -mx-1 py-1 transition hover:bg-brand-50 ${
                          selected?.id === n.id ? 'bg-brand-50 ring-1 ring-brand-300' : ''
                        }`}
                      >
                        {iconFor(n.status)}
                        <span className="truncate flex-1 text-left">{n.label}</span>
                        {n.ip && <span className="text-[10px] text-muted hidden xl:inline">{n.ip}</span>}
                        {statusDot(n.status)}
                      </button>
                    ))}
                  </div>
                </div>
              </div>
            )
          })}
        </div>

        {!nodes.length && (
          <div className="absolute inset-0 flex items-center justify-center text-muted text-[12px] gap-2">
            Нет данных топологии — подключите HTTP_ENDPOINTS.topology.graph
          </div>
        )}
      </div>

      {selected && (
        <div className="absolute right-2 bottom-2 w-56 bg-white border border-border rounded-xl2 shadow-card p-3 z-30 text-[12px]">
          <div className="flex items-center justify-between mb-2">
            <div className="font-medium truncate">{selected.label}</div>
            <button onClick={() => setSelected(null)} className="text-muted hover:text-[#1a2233]">
              <X size={14} />
            </button>
          </div>
          <div className="space-y-1 text-muted">
            <div className="flex items-center gap-1"><Router size={12} /> {selected.group || '—'}</div>
            {selected.ip && <div className="flex items-center gap-1"><Wifi size={12} /> {selected.ip}</div>}
          </div>
          <div className="mt-2"><StatusBadge value={selected.status} /></div>
        </div>
      )}
    </div>
  )
}
