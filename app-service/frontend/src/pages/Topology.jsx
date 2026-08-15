import React from 'react'
import TopologyMap from '../components/TopologyMap.jsx'

export default function Topology() {
  return (
    <div className="card p-4">
      <div className="text-[14px] font-medium mb-3">Топология сети</div>
      <TopologyMap />
      <p className="text-[12px] text-muted mt-3">
        Данные графа загружаются с HTTP_ENDPOINTS.topology.graph. Для realtime-обновления
        расположения/статусов узлов подпишитесь на канал WS_CHANNELS.topology.
      </p>
    </div>
  )
}
