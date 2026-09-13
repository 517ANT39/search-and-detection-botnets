import { Network } from 'vis-network/standalone/esm/vis-network';
import { DataSet } from 'vis-data';

let network = null;
let nodes = null;
let edges = null;
let positions = {};

const SEVERITY_COLOR = {
  critical: '#dc2626',
  warning:  '#d97706',
  info:     '#4f46e5',
};

const PROTOCOL_NAMES = { 0: 'TCP', 1: 'UDP', 2: 'ICMP', '-1': '—' };

/**
 * Радиальный layout. Хаб в центре, остальные — по кольцам.
 */
function radialLayout(nodeIds, edgesList) {
  const result = {};
  const N = nodeIds.length;
  if (N === 0) return result;
  if (N === 1) return { [nodeIds[0]]: { x: 0, y: 0 } };

  const degree = {};
  nodeIds.forEach(id => { degree[id] = 0; });
  edgesList.forEach(e => {
    if (degree[e.from] !== undefined) degree[e.from]++;
    if (degree[e.to]   !== undefined) degree[e.to]++;
  });

  const hub = nodeIds.reduce((a, b) => (degree[a] || 0) >= (degree[b] || 0) ? a : b);
  result[hub] = { x: 0, y: 0 };

  const rest = nodeIds.filter(id => id !== hub);
  const rings = Math.min(3, Math.max(2, Math.ceil(rest.length / 12)));
  const perRing = Math.ceil(rest.length / rings);

  let idx = 0;
  for (let r = 0; r < rings; r++) {
    const radius = 260 * (r + 1);
    const count = Math.min(perRing, rest.length - idx);
    if (count <= 0) break;
    for (let i = 0; i < count; i++) {
      const angle = (2 * Math.PI * i) / count - Math.PI / 2 + r * 0.4;
      const id = rest[idx++];
      result[id] = {
        x: radius * Math.cos(angle),
        y: radius * Math.sin(angle),
      };
    }
  }
  return result;
}

export function initTopology(containerId) {
  const container = document.getElementById(containerId);
  if (!container) {
    console.error('[topology] контейнер не найден:', containerId);
    return null;
  }
  if (network) {
    network.destroy();
    network = null;
  }

  nodes = new DataSet([]);
  edges = new DataSet([]);

  const data = { nodes, edges };

  const options = {
    autoResize: true,
    layout: { improvedLayout: false },
    physics: { enabled: false },
    interaction: {
      dragNodes: true,
      dragView: true,
      zoomView: true,
      hover: true,
      tooltipDelay: 100,
      keyboard: { enabled: false },
    },
    nodes: {
      shape: 'dot',
      borderWidth: 2,
      font: {
        color: '#1e293b',
        size: 12,
        face: 'ui-monospace, monospace',
        vadjust: 4,
        strokeWidth: 3,
        strokeColor: '#ffffff',
      },
    },
    edges: {
      smooth: false,
      arrows: { to: { enabled: true, scaleFactor: 0.6 } },
      color: {
        color: 'rgba(37,99,235,0.35)',
        highlight: '#2563eb',
        hover: '#2563eb',
      },
      width: 1,
    },
  };

  try {
    network = new Network(container, data, options);
    console.log('[topology] network создан');
  } catch (e) {
    console.error('[topology] ошибка создания Network:', e);
    return null;
  }

  network.on('dragEnd', (params) => {
    if (params.nodes && params.nodes.length) {
      params.nodes.forEach(id => {
        const pos = network.getPositions([id])[id];
        if (pos) positions[id] = { x: pos.x, y: pos.y };
      });
    }
  });

  network.on('doubleClick', (params) => {
    if (params.nodes && params.nodes.length) {
      network.focus(params.nodes[0], {
        scale: 1.3,
        animation: { duration: 400, easingFunction: 'easeInOutQuad' },
      });
    }
  });

  return network;
}

export function updateTopology(pairs, alerts = []) {
  if (!network) {
    console.warn('[topology] network не инициализирован');
    return;
  }

  console.log('[topology] получено пар:', pairs.length, 'алертов:', alerts.length);

  // Если пара пришла без нужных полей — отфильтруем
  const cleanPairs = pairs.filter(p => p && p.src && p.dst);
  if (!cleanPairs.length) {
    console.warn('[topology] нет валидных пар для отображения');
    // Очищаем
    nodes.clear();
    edges.clear();
    return;
  }

  const nodeSet = new Set();
  const edgeList = [];
  cleanPairs.forEach(p => {
    nodeSet.add(p.src);
    nodeSet.add(p.dst);
    edgeList.push({
      from: p.src,
      to:   p.dst,
      packets: p.packets || 0,
      bytes: p.bytes || 0,
      protocol: p.protocol,
    });
  });

  const severityByIp = {};
  alerts.forEach(a => {
    if (!a.dst_ip) return;
    const cur = severityByIp[a.dst_ip];
    const rank = { critical: 3, warning: 2, info: 1 };
    if (!cur || (rank[a.severity] || 0) > (rank[cur] || 0)) {
      severityByIp[a.dst_ip] = a.severity;
    }
  });

  // 1. Добавляем/обновляем узлы
  const newNodeIds = [];
  nodeSet.forEach(id => {
    const existing = nodes.get(id);
    const severity = severityByIp[id] || null;
    const color = severity
      ? SEVERITY_COLOR[severity]
      : (existing?.color?.background || '#2563eb');

    const node = {
      id,
      label: id,
      color: {
        background: color,
        border: color,
        highlight: { background: color, border: '#1e293b' },
      },
      size: severity === 'critical' ? 22
          : severity === 'warning'  ? 18
          : 14,
      borderWidth: severity ? 3 : 2,
    };

    if (existing) {
      nodes.update(node);
    } else {
      if (positions[id]) {
        node.x = positions[id].x;
        node.y = positions[id].y;
      }
      nodes.add(node);
      newNodeIds.push(id);
    }
  });

  // Удаляем пропавшие узлы
  const currentIds = nodes.getIds();
  const removeIds = currentIds.filter(id => !nodeSet.has(id));
  if (removeIds.length) {
    nodes.remove(removeIds);
    removeIds.forEach(id => delete positions[id]);
  }

  // 2. Раскладываем новые узлы радиально
  if (newNodeIds.length) {
    const allIds = nodes.getIds();
    const layout = radialLayout(allIds, edgeList);

    const updates = newNodeIds.map(id => {
      const pos = positions[id] || layout[id] || { x: 0, y: 0 };
      return { id, x: pos.x, y: pos.y };
    });

    nodes.update(updates);
    updates.forEach(u => {
      positions[u.id] = { x: u.x, y: u.y };    // ← ФИКС: u.id, а не id
    });
  }

  // 3. Рёбра
  const edgesData = edgeList.map(e => ({
    id: `${e.from}->${e.to}`,
    from: e.from,
    to:   e.to,
    width: Math.max(1, Math.min(8, Math.log10(e.packets + 1) * 1.5)),
    label: e.packets > 5000 ? `${Math.round(e.packets / 1000)}k` : undefined,
    font: { size: 10, color: '#64748b', strokeWidth: 3, strokeColor: '#ffffff', align: 'middle' },
    color: {
      color: `rgba(37,99,235,${Math.min(0.75, 0.2 + Math.log10(e.packets + 1) / 6)})`,
    },
    title: `${e.from} → ${e.to}\n${PROTOCOL_NAMES[e.protocol] ?? e.protocol}\n${e.packets.toLocaleString()} pkts · ${e.bytes.toLocaleString()} B`,
    arrows: { to: { enabled: true, scaleFactor: 0.5 } },
    smooth: false,
  }));

  const existingEdgeIds = edges.getIds();
  if (existingEdgeIds.length) edges.remove(existingEdgeIds);
  edges.add(edgesData);

  console.log('[topology] узлов:', nodes.length, 'рёбер:', edges.length);
  // Первый раз — автоматически уместить
  if (newNodeIds.length) {
    setTimeout(() => {
      try { network.fit({ animation: { duration: 500 } }); } catch {}
    }, 50);
  }
}

export function resetTopology() {
  if (!network) return;
  positions = {};
  nodes.clear();
  edges.clear();
  network.fit({ animation: { duration: 500 } });
}

export function fitTopology() {
  if (!network) return;
  network.fit({ animation: { duration: 500 } });
}

export function zoomIn() {
  if (!network) return;
  const s = network.getScale();
  network.moveTo({ scale: s * 1.3, animation: { duration: 200 } });
}

export function zoomOut() {
  if (!network) return;
  const s = network.getScale();
  network.moveTo({ scale: s / 1.3, animation: { duration: 200 } });
}

export function setPhysics(enabled) {
  if (!network) return;
  network.setOptions({ physics: { enabled } });
  if (enabled) {
    network.stabilize(1500);
    setTimeout(() => {
      network.setOptions({ physics: { enabled: false } });
      const pos = network.getPositions();
      Object.keys(pos).forEach(id => { positions[id] = pos[id]; });
    }, 1600);
  }
}