import React, { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  AreaChart, Area, LineChart, Line, BarChart, Bar, ComposedChart,
  ResponsiveContainer, XAxis, YAxis, Tooltip, CartesianGrid, Legend,
} from 'recharts'
import { AlertTriangle, Info, ShieldAlert, ChevronRight, Maximize2, HelpCircle } from 'lucide-react'
import { useApi } from '../hooks/useApi.js'
import { useWebSocketChannel } from '../hooks/useWebSocket.js'
import { HTTP_ENDPOINTS, WS_CHANNELS } from '../api/endpoints.js'
import MetricCard from '../components/UI/MetricCard.jsx'
import StatusBadge from '../components/UI/StatusBadge.jsx'
import TopologyMap from '../components/TopologyMap.jsx'
import Modal from '../components/UI/Modal.jsx'

function LevelIcon({ level }) {
  if (level === 'critical') return <ShieldAlert size={14} className="text-critical" />
  if (level === 'warning') return <AlertTriangle size={14} className="text-warning" />
  return <Info size={14} className="text-info" />
}

// Небольшой tooltip-подсказка при наведении (без внешних зависимостей)
function InfoHint({ text }) {
  const [show, setShow] = useState(false)
  return (
    <span className="relative inline-flex" onMouseEnter={() => setShow(true)} onMouseLeave={() => setShow(false)}>
      <HelpCircle size={13} className="text-muted cursor-help" />
      {show && (
        <span className="absolute left-1/2 -translate-x-1/2 bottom-5 w-56 bg-[#1a2233] text-white text-[11px] rounded-lg p-2 shadow-card z-30 leading-snug">
          {text}
        </span>
      )}
    </span>
  )
}

export default function Overview() {
  const { data: summary } = useApi(HTTP_ENDPOINTS.overview.summary, {}, { pollIntervalMs: 15000 })
  const { data: totalTraffic } = useApi(HTTP_ENDPOINTS.overview.trafficHistory)
  const { data: channels } = useApi(HTTP_ENDPOINTS.overview.channelUsage)
  const { data: nodeLoad } = useApi(HTTP_ENDPOINTS.overview.nodeLoadHeatmap)
  const { data: trafficByNode } = useApi(HTTP_ENDPOINTS.overview.trafficByNode, {}, { pollIntervalMs: 30000 })
  const { data: protocols } = useApi(HTTP_ENDPOINTS.overview.protocols)
  const { data: events } = useApi(HTTP_ENDPOINTS.overview.recentEvents, {}, { pollIntervalMs: 20000 })
  const { data: incidents } = useApi(HTTP_ENDPOINTS.overview.incidents)
  const { data: liveMetrics } = useWebSocketChannel(WS_CHANNELS.metrics)
  const [selected, setSelected] = useState(null)
  const [expandedNode, setExpandedNode] = useState(null)
  const [showTotalOverlay, setShowTotalOverlay] = useState(false)
  const navigate = useNavigate()

  const m = liveMetrics || summary

  // Данные для развёрнутого графика (клик по мини-карточке сервера)
  const expandedHistory = (() => {
    if (!expandedNode) return []
    if (!showTotalOverlay) return expandedNode.history
    // объединяем историю узла с общим трафиком по времени (опционально)
    return expandedNode.history.map((point, i) => ({
      ...point,
      totalIn: totalTraffic?.[i]?.in,
      totalOut: totalTraffic?.[i]?.out,
    }))
  })()

  return (
    <div className="space-y-4">
      {/* Метрики */}
      <div className="flex flex-wrap gap-3">
        <MetricCard label="Трафик (всего)" value={m?.totalTraffic?.value ?? '—'} unit={m?.totalTraffic?.unit}
          deltaLabel={m?.totalTraffic?.delta ? `${m.totalTraffic.delta}% к норме` : null}
          onClick={() => navigate('/traffic')} />
        <MetricCard label="Исходящий трафик" value={summary?.outboundTraffic?.value ?? '—'} unit={summary?.outboundTraffic?.unit}
          sub={summary?.outboundTraffic ? `${summary.outboundTraffic.percent}%` : null}
          onClick={() => navigate('/traffic')} />
        <MetricCard label="Входящий трафик" value={summary?.inboundTraffic?.value ?? '—'} unit={summary?.inboundTraffic?.unit}
          sub={summary?.inboundTraffic ? `${summary.inboundTraffic.percent}%` : null}
          onClick={() => navigate('/traffic')} />
        <MetricCard label="Активные узлы" value={m?.activeNodes ? `${m.activeNodes.active} / ${m.activeNodes.total}` : '—'}
          onClick={() => navigate('/nodes')} />
        <MetricCard label="Подозрительная активность" value={m?.suspiciousActivity?.value ?? '—'} accent="text-warning"
          deltaLabel={m?.suspiciousActivity?.value ? 'за последние 24ч' : null}
          onClick={() => navigate('/events')} />
        <MetricCard label="Критические инциденты" value={m?.criticalIncidents?.value ?? '—'} accent="text-critical"
          deltaLabel="за последние 24ч"
          onClick={() => navigate('/incidents')} />
      </div>

      <div className="grid grid-cols-12 gap-4">
        {/* Левая колонка */}
        <div className="col-span-12 lg:col-span-3 space-y-4">
          {/* Сетка графиков трафика по серверам */}
          <div className="card p-4">
            <div className="flex items-center justify-between mb-2">
              <div className="text-[13px] font-medium">Трафик по серверам</div>
              <button
                onClick={() => setExpandedNode({ id: '__total__', label: 'Общий трафик (все узлы)', history: totalTraffic || [] })}
                className="text-[11px] text-brand-600 hover:underline"
              >
                Общий трафик
              </button>
            </div>
            <div className="grid grid-cols-2 gap-2">
              {(trafficByNode || []).slice(0, 6).map((node) => (
                <button
                  key={node.id}
                  onClick={() => { setShowTotalOverlay(false); setExpandedNode(node) }}
                  className="group relative border border-border rounded-lg p-2 text-left hover:border-brand-300 hover:shadow-card transition"
                >
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-[10px] font-medium text-[#1a2233] truncate">{node.label}</span>
                    <Maximize2 size={11} className="text-muted opacity-0 group-hover:opacity-100 transition" />
                  </div>
                  <div className="h-[46px]">
                    <ResponsiveContainer width="100%" height="100%">
                      <LineChart data={node.history}>
                        <Line type="monotone" dataKey="in" stroke="#2f6fed" strokeWidth={1.5} dot={false} />
                        <Line type="monotone" dataKey="out" stroke="#2ecc71" strokeWidth={1.5} dot={false} />
                      </LineChart>
                    </ResponsiveContainer>
                  </div>
                </button>
              ))}
              {!trafficByNode?.length && (
                <div className="col-span-2 text-muted text-[11px] py-4 text-center">Нет данных трафика по узлам</div>
              )}
            </div>
          </div>

          <div className="card p-4">
            <div className="flex items-center gap-1.5 mb-3">
              <div className="text-[13px] font-medium">Использование каналов</div>
              <InfoHint text="Показывает процент загрузки пропускной способности каждого канала связи: основной интернет-канал, резервный (на случай сбоя основного) и выделенный канал до ЦОД. Помогает вовремя увидеть, когда канал приближается к пределу и требует расширения." />
            </div>
            <div className="space-y-3">
              {(channels || []).map((c) => (
                <div key={c.label}>
                  <div className="flex justify-between text-[12px] text-muted mb-1">
                    <span>{c.label}</span><span>{c.percent}%</span>
                  </div>
                  <div className="h-2 rounded-full bg-surface overflow-hidden">
                    <div className="h-full bg-brand-500 rounded-full" style={{ width: `${c.percent}%` }} />
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Нагрузка по узлам -- столбчатая диаграмма */}
          <div className="card p-4">
            <div className="text-[13px] font-medium mb-2">Нагрузка по узлам</div>
            <div className="h-[150px]">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={nodeLoad || []} barGap={2}>
                  <XAxis dataKey="time" tick={{ fontSize: 9 }} interval={0} />
                  <YAxis tick={{ fontSize: 9 }} width={20} allowDecimals={false} />
                  <Tooltip contentStyle={{ fontSize: 11, borderRadius: 8 }} />
                  <Bar dataKey="low" stackId="a" fill="#2f6fed" radius={[0, 0, 0, 0]} />
                  <Bar dataKey="medium" stackId="a" fill="#f5a623" />
                  <Bar dataKey="high" stackId="a" fill="#e5484d" radius={[3, 3, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
            <div className="flex gap-3 text-[10px] text-muted mt-1">
              <span className="flex items-center gap-1"><i className="w-2 h-2 rounded-full bg-brand-500 inline-block" /> Низкая</span>
              <span className="flex items-center gap-1"><i className="w-2 h-2 rounded-full bg-warning inline-block" /> Средняя</span>
              <span className="flex items-center gap-1"><i className="w-2 h-2 rounded-full bg-critical inline-block" /> Высокая</span>
            </div>
          </div>
        </div>

        {/* Центр -- топология */}
        <div className="col-span-12 lg:col-span-6 card p-4">
          <div className="text-[13px] font-medium mb-2">Карта топологии</div>
          <TopologyMap />
        </div>

        {/* Правая колонка */}
        <div className="col-span-12 lg:col-span-3 space-y-4">
          <div className="card p-4">
            <div className="text-[13px] font-medium mb-3">Протоколы и сервисы</div>
            <div className="space-y-2">
              {(protocols || []).map((p) => (
                <div key={p.label} className="flex items-center gap-2 text-[12px]">
                  <span className="w-2 h-2 rounded-full" style={{ background: p.color }} />
                  <span className="flex-1 text-[#4a5468]">{p.label}</span>
                  <span className="text-muted">{p.percent}%</span>
                </div>
              ))}
            </div>
          </div>

          <div className="card p-4">
            <div className="flex items-center justify-between mb-2">
              <div className="text-[13px] font-medium">Журнал событий (последние)</div>
            </div>
            <div className="space-y-2 max-h-[220px] overflow-y-auto">
              {(events || []).map((e, i) => (
                <div key={i} onClick={() => navigate('/events')}
                  className="flex items-start gap-2 text-[12px] border-b border-border/60 pb-2 last:border-0 cursor-pointer hover:bg-surface rounded-md px-1 -mx-1 transition">
                  <LevelIcon level={e.level} />
                  <div className="flex-1">
                    <div className="text-[#1a2233]">{e.text}</div>
                    <div className="text-muted text-[11px]">{e.source}</div>
                  </div>
                  <div className="text-muted text-[11px]">{e.time}</div>
                </div>
              ))}
            </div>
            <button onClick={() => navigate('/events')} className="text-brand-600 text-[12px] flex items-center gap-1 mt-2 hover:underline">
              Все события <ChevronRight size={13} />
            </button>
          </div>
        </div>
      </div>

      {/* Инциденты и события таблица */}
      <div className="grid grid-cols-12 gap-4">
        <div className="col-span-12 xl:col-span-7 card p-4">
          <div className="text-[13px] font-medium mb-3">Инциденты и события</div>
          <div className="overflow-x-auto">
            <table className="w-full text-[12px]">
              <thead>
                <tr className="text-muted text-left border-b border-border">
                  <th className="py-2 font-medium">Время</th>
                  <th className="py-2 font-medium">Уровень</th>
                  <th className="py-2 font-medium">Событие</th>
                  <th className="py-2 font-medium">Источник</th>
                  <th className="py-2 font-medium">Назначение</th>
                  <th className="py-2 font-medium">Статус</th>
                </tr>
              </thead>
              <tbody>
                {(incidents || []).map((row) => (
                  <tr
                    key={row.id}
                    onClick={() => setSelected(row)}
                    className={`border-b border-border/60 cursor-pointer hover:bg-surface ${selected?.id === row.id ? 'bg-brand-50' : ''}`}
                  >
                    <td className="py-2">{row.time}</td>
                    <td className="py-2"><StatusBadge value={row.level} /></td>
                    <td className="py-2">{row.title}</td>
                    <td className="py-2 text-muted">{row.source}</td>
                    <td className="py-2 text-muted">{row.target}</td>
                    <td className="py-2"><StatusBadge value={row.status} /></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <button onClick={() => navigate('/incidents')} className="text-brand-600 text-[12px] flex items-center gap-1 mt-3 hover:underline">
            Все инциденты <ChevronRight size={13} />
          </button>
        </div>

        <div className="col-span-12 xl:col-span-5 card p-4">
          <div className="flex items-center justify-between mb-3">
            <div className="text-[13px] font-medium">Несанкционированный доступ</div>
            {selected && <StatusBadge value={selected.level} />}
          </div>
          {selected ? (
            <div className="space-y-3 text-[12px]">
              <div className="text-muted">ID: {selected.id}</div>
              <div className="grid grid-cols-2 gap-y-2">
                <div className="text-muted">Описание:</div>
                <div className="text-right">{selected.title}</div>
                <div className="text-muted">Категория:</div>
                <div className="text-right">Нарушение доступа</div>
                <div className="text-muted">Правило:</div>
                <div className="text-right">Политика доступа к БД</div>
                <div className="text-muted">Статус:</div>
                <div className="text-right"><StatusBadge value={selected.status} /></div>
              </div>
            </div>
          ) : (
            <div className="text-muted text-[12px]">Выберите инцидент из списка слева, чтобы посмотреть детали и хронологию событий.</div>
          )}
        </div>
      </div>

      {/* Развёрнутый график по клику на мини-карточку сервера */}
      <Modal open={!!expandedNode} onClose={() => setExpandedNode(null)} title={expandedNode?.label} width="max-w-3xl">
        {expandedNode && (
          <div>
            {expandedNode.id !== '__total__' && (
              <label className="flex items-center gap-2 text-[12px] text-muted mb-3 cursor-pointer select-none">
                <input
                  type="checkbox"
                  checked={showTotalOverlay}
                  onChange={(e) => setShowTotalOverlay(e.target.checked)}
                  className="accent-brand-500"
                />
                Наложить общий трафик сети (опционально)
              </label>
            )}
            <div className="h-[320px]">
              <ResponsiveContainer width="100%" height="100%">
                <ComposedChart data={expandedHistory}>
                  <defs>
                    <linearGradient id="exp-in" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#2f6fed" stopOpacity={0.3} />
                      <stop offset="95%" stopColor="#2f6fed" stopOpacity={0} />
                    </linearGradient>
                    <linearGradient id="exp-out" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#2ecc71" stopOpacity={0.3} />
                      <stop offset="95%" stopColor="#2ecc71" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="#eef1f6" />
                  <XAxis dataKey="time" tick={{ fontSize: 11 }} />
                  <YAxis tick={{ fontSize: 11 }} width={35} />
                  <Tooltip contentStyle={{ fontSize: 12, borderRadius: 8 }} />
                  <Legend wrapperStyle={{ fontSize: 11 }} />
                  <Area type="monotone" dataKey="in" name="Входящий" stroke="#2f6fed" fill="url(#exp-in)" strokeWidth={2} />
                  <Area type="monotone" dataKey="out" name="Исходящий" stroke="#2ecc71" fill="url(#exp-out)" strokeWidth={2} />
                  {showTotalOverlay && (
                    <>
                      <Line type="monotone" dataKey="totalIn" name="Общий входящий" stroke="#8a93a6" strokeDasharray="4 3" dot={false} />
                      <Line type="monotone" dataKey="totalOut" name="Общий исходящий" stroke="#c7ccd6" strokeDasharray="4 3" dot={false} />
                    </>
                  )}
                </ComposedChart>
              </ResponsiveContainer>
            </div>
          </div>
        )}
      </Modal>
    </div>
  )
}
