import React from 'react'
import { AreaChart, Area, ResponsiveContainer, XAxis, YAxis, Tooltip, CartesianGrid } from 'recharts'
import { useApi } from '../hooks/useApi.js'
import { useWebSocketChannel } from '../hooks/useWebSocket.js'
import { HTTP_ENDPOINTS, WS_CHANNELS } from '../api/endpoints.js'

export default function Traffic() {
  const { data } = useApi(HTTP_ENDPOINTS.overview.trafficHistory)
  const { data: live } = useWebSocketChannel(WS_CHANNELS.traffic)

  return (
    <div className="card p-4">
      <div className="flex items-center justify-between mb-3">
        <div className="text-[14px] font-medium">Трафик в реальном времени</div>
        {live && <span className="text-[11px] text-muted">Вход: {live.in} Мбит/с · Выход: {live.out} Мбит/с</span>}
      </div>
      <div className="h-[320px]">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={data || []}>
            <defs>
              <linearGradient id="in2" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#2f6fed" stopOpacity={0.35} />
                <stop offset="95%" stopColor="#2f6fed" stopOpacity={0} />
              </linearGradient>
              <linearGradient id="out2" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#2ecc71" stopOpacity={0.35} />
                <stop offset="95%" stopColor="#2ecc71" stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="#eef1f6" />
            <XAxis dataKey="time" tick={{ fontSize: 11 }} />
            <YAxis tick={{ fontSize: 11 }} />
            <Tooltip contentStyle={{ fontSize: 12, borderRadius: 8 }} />
            <Area type="monotone" dataKey="in" stroke="#2f6fed" fill="url(#in2)" strokeWidth={2} />
            <Area type="monotone" dataKey="out" stroke="#2ecc71" fill="url(#out2)" strokeWidth={2} />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}
