import './style.css';
import { api, login, isLoggedIn, logout } from './api.js';
import {
  multiAxisLine, barChart, doughnut, lineChart,
} from './charts.js';
import { initAlertSocket } from './alerts.js';
import {
  collectFilters, applyFiltersToForm, loadFilterList,
  saveCurrentFilter, deleteFilterById, buildQueryString,
} from './filters.js';
import {
  initTopology, updateTopology, resetTopology,
  fitTopology, zoomIn, zoomOut, setPhysics,
} from './topology.js';

/* ============================================================
 *  Глобальное состояние
 * ============================================================ */
const state = {
  filters: {},
  alerts: [],              // последние 500
  activePage: 'overview',
  wsConnected: false,
};

const PROTOCOL_NAME = { 0: 'TCP', 1: 'UDP', 2: 'ICMP', 3: 'UNKNOWN' };
const SEVERITY_RU = { critical: 'Критично', warning: 'Внимание', info: 'Инфо' };

/* ============================================================
 *  Рендеринг — логин
 * ============================================================ */
function renderLogin() {
  document.getElementById('app').innerHTML = `
    <div class="login-wrap">
      <div class="login-card">
        <h1>🚦 Traffic Analyzer</h1>
        <p>Войдите, чтобы увидеть дашборд</p>
        <input type="text" id="lg-user" placeholder="Логин" autocomplete="username" value="admin" />
        <input type="password" id="lg-pass" placeholder="Пароль" autocomplete="current-password" value="admin" />
        <button id="lg-btn">Войти</button>
        <div class="login-error" id="lg-err"></div>
      </div>
    </div>
  `;

  const doLogin = async () => {
    const u = document.getElementById('lg-user').value.trim();
    const p = document.getElementById('lg-pass').value;
    const err = document.getElementById('lg-err');
    err.textContent = '';
    try {
      await login(u, p);
      renderApp();
    } catch (e) {
      err.textContent = e.message || 'Ошибка входа';
    }
  };
  document.getElementById('lg-btn').onclick = doLogin;
  document.getElementById('lg-pass').onkeydown = (e) => {
    if (e.key === 'Enter') doLogin();
  };
}

/* ============================================================
 *  Рендеринг — каркас приложения
 * ============================================================ */
function renderApp() {
  document.getElementById('app').innerHTML = `
    <div class="layout">
      <aside class="sidebar">
        <div class="sidebar-logo">🚦 <span>Traffic</span></div>
        <nav class="nav" id="nav">
          <div class="nav-item active" data-page="overview">📊 Обзор</div>
          <div class="nav-item" data-page="traffic">📈 Трафик</div>
          <div class="nav-item" data-page="topology">🕸 Топология</div>
          <div class="nav-item" data-page="hosts">🖥 Хосты</div>
          <div class="nav-item" data-page="alerts">⚠️ Алерты</div>
        </nav>
        <div class="sidebar-footer">
          <div id="user-info">…</div>
          <button id="logout-btn">Выйти</button>
        </div>
      </aside>

      <main class="main" id="main">
        <div class="topbar">
          <h2 id="page-title">Обзор</h2>
          <div class="kpi-strip" id="kpi-strip"></div>
        </div>

        <div class="filters-bar">
          <input type="datetime-local" id="f-start" />
          <input type="datetime-local" id="f-end" />
          <input type="text" id="f-src" placeholder="Src IP" />
          <input type="text" id="f-dst" placeholder="Dst IP" />
          <input type="text" id="f-host" placeholder="Host IP" />
          <select id="f-protocol">
            <option value="">Все протоколы</option>
            <option value="0">TCP</option>
            <option value="1">UDP</option>
            <option value="2">ICMP</option>
          </select>
          <select id="f-direction">
            <option value="">Все направления</option>
            <option value="0">Ingress</option>
            <option value="1">Egress</option>
          </select>
          <select id="f-minutes">
            <option value="15">15 мин</option>
            <option value="60" selected>1 час</option>
            <option value="360">6 часов</option>
            <option value="1440">24 часа</option>
          </select>
          <button id="apply-btn">Применить</button>
          <button class="secondary" id="save-filter-btn">Сохранить</button>
          <select id="saved-filters" style="min-width:140px">
            <option value="">Сохранённые…</option>
          </select>
        </div>

        <div id="page-overview" class="tab-page active"></div>
        <div id="page-traffic"  class="tab-page"></div>
        <div id="page-topology" class="tab-page"></div>
        <div id="page-hosts"    class="tab-page"></div>
        <div id="page-alerts"   class="tab-page"></div>
      </main>
    </div>

    <div class="toasts" id="toasts"></div>
  `;

  document.getElementById('logout-btn').onclick = () => {
    logout();
    renderLogin();
  };

  // Переключение вкладок
  document.querySelectorAll('.nav-item').forEach(el => {
    el.onclick = () => setPage(el.dataset.page);
  });

  // Кнопки фильтра
  document.getElementById('apply-btn').onclick = applyFilters;
  document.getElementById('save-filter-btn').onclick = saveFilter;
  document.getElementById('saved-filters').onchange = (e) => {
    const id = e.target.value;
    if (!id) return;
    const item = state.savedFilters?.find(f => String(f.id) === id);
    if (item) {
      applyFiltersToForm(item.filter_data);
      applyFilters();
    }
  };

  // Заголовок и пользователь
  api('/api/me').then(u => {
    document.getElementById('user-info').textContent = `👤 ${u.username}`;
  }).catch(() => {});

  // Загрузка фильтров
  refreshSavedFilters();

  // Первая страница
  setPage('overview');

  // WebSocket
  initAlertSocket({
    onAlert: (alert) => {
      state.alerts.unshift(alert);
      if (state.alerts.length > 500) state.alerts.pop();
      pushToast(alert);
      if (state.activePage === 'overview') renderOverview();
      if (state.activePage === 'alerts')   renderAlerts();
      if (state.activePage === 'topology') refreshTopology();
    },
  });

  // Автообновление KPI каждые 30 секунд
  setInterval(refreshKpi, 30000);
  refreshKpi();
}

/* ============================================================
 *  Навигация по страницам
 * ============================================================ */
function setPage(page) {
  state.activePage = page;
  document.querySelectorAll('.nav-item').forEach(el =>
    el.classList.toggle('active', el.dataset.page === page));
  document.querySelectorAll('.tab-page').forEach(el =>
    el.classList.remove('active'));
  const target = document.getElementById(`page-${page}`);
  if (target) target.classList.add('active');

  const titles = {
    overview: 'Обзор',
    traffic:  'Трафик',
    topology: 'Топология',
    hosts:    'Хосты',
    alerts:   'Алерты',
  };
  document.getElementById('page-title').textContent = titles[page] || page;

  if (page === 'overview') renderOverview();
  if (page === 'traffic')  renderTraffic();
  if (page === 'topology') renderTopology();
  if (page === 'hosts')    renderHosts();
  if (page === 'alerts')   renderAlerts();
}

/* ============================================================
 *  Фильтры
 * ============================================================ */
function applyFilters() {
  state.filters = collectFilters();
  setPage(state.activePage);   // перерисовать текущую страницу
  refreshKpi();
}

async function saveFilter() {
  const name = prompt('Название фильтра:');
  if (!name) return;
  try {
    await saveCurrentFilter(name);
    await refreshSavedFilters();
  } catch (e) {
    alert('Ошибка сохранения: ' + e.message);
  }
}

async function refreshSavedFilters() {
  const list = await loadFilterList();
  state.savedFilters = list;
  const sel = document.getElementById('saved-filters');
  if (!sel) return;
  sel.innerHTML = '<option value="">Сохранённые…</option>' +
    list.map(f => `<option value="${f.id}">${escapeHtml(f.name)}</option>`).join('');
}

/* ============================================================
 *  KPI-строка
 * ============================================================ */
async function refreshKpi() {
  try {
    const q = buildQueryString(state.filters);
    const [alerts, status] = await Promise.all([
      api(`/api/alerts?limit=200&minutes=15`),
      api(`/api/hosts/status`).catch(() => []),
    ]);

    const total     = alerts.length;
    const critical  = alerts.filter(a => a.severity === 'critical').length;
    const targets   = new Set(alerts.map(a => a.dst_ip).filter(Boolean)).size;
    const sources   = new Set(alerts.map(a => a.src_ip).filter(Boolean)).size;
    const online    = status.filter(h => !h.is_offline).length;
    const offline   = status.length - online;

    const strip = document.getElementById('kpi-strip');
    if (!strip) return;
    strip.innerHTML = `
      <div class="kpi">
        <div class="kpi-label">Алертов (15м)</div>
        <div class="kpi-value ${total > 0 ? 'warning' : 'success'}">${total}</div>
      </div>
      <div class="kpi">
        <div class="kpi-label">Критичных</div>
        <div class="kpi-value ${critical > 0 ? 'critical' : 'success'}">${critical}</div>
      </div>
      <div class="kpi">
        <div class="kpi-label">Целей</div>
        <div class="kpi-value">${targets}</div>
      </div>
      <div class="kpi">
        <div class="kpi-label">Источников</div>
        <div class="kpi-value">${sources}</div>
      </div>
      <div class="kpi">
        <div class="kpi-label">Сенсоры</div>
        <div class="kpi-value ${offline > 0 ? 'critical' : 'success'}">
          ${online}/${status.length}
        </div>
      </div>
    `;
  } catch (e) {
    console.warn('refreshKpi:', e);
  }
}

/* ============================================================
 *  Страница «Обзор»
 * ============================================================ */
async function renderOverview() {
  const el = document.getElementById('page-overview');
  if (!el) return;
  el.innerHTML = `
    <div class="grid-2">
      <div class="card">
        <div class="card-title">Трафик во времени <span class="dim">packets / bytes</span></div>
        <div class="chart-wrap"><canvas id="ch-timeline"></canvas></div>
      </div>
      <div class="card">
        <div class="card-title">Алерты во времени <span class="dim">по severity</span></div>
        <div class="chart-wrap"><canvas id="ch-alerts-tl"></canvas></div>
      </div>
    </div>

    <div class="grid-4">
      <div class="card">
        <div class="card-title">Протоколы</div>
        <div class="chart-wrap" style="height:220px"><canvas id="ch-proto"></canvas></div>
      </div>
      <div class="card">
        <div class="card-title">Направление</div>
        <div class="chart-wrap" style="height:220px"><canvas id="ch-dir"></canvas></div>
      </div>
      <div class="card">
        <div class="card-title">Severity алертов</div>
        <div class="chart-wrap" style="height:220px"><canvas id="ch-sev"></canvas></div>
      </div>
      <div class="card">
        <div class="card-title">View алертов</div>
        <div class="chart-wrap" style="height:220px"><canvas id="ch-view"></canvas></div>
      </div>
    </div>

    <div class="grid-2">
      <div class="card">
        <div class="card-title">Топ источников алертов</div>
        <div class="chart-wrap"><canvas id="ch-tsrc"></canvas></div>
      </div>
      <div class="card">
        <div class="card-title">Топ целей атак</div>
        <div class="chart-wrap"><canvas id="ch-tdst"></canvas></div>
      </div>
    </div>
  `;

  const q = buildQueryString(state.filters);
  const minutes = state.filters.minutes || 60;

  const [
    timeline, alertsTl, proto, dir, sev, view, tsrc, tdst,
  ] = await Promise.all([
    api(`/api/traffic/timeline?${q}`).catch(() => []),
    api(`/api/alerts/timeline?minutes=${minutes}`).catch(() => []),
    api(`/api/traffic/by_protocol?minutes=${minutes}`).catch(() => []),
    api(`/api/traffic/by_direction?minutes=${minutes}`).catch(() => []),
    api(`/api/alerts/by_severity?minutes=${minutes}`).catch(() => []),
    api(`/api/alerts/by_view?minutes=${minutes}`).catch(() => []),
    api(`/api/alerts/top_sources?minutes=${minutes}&limit=10`).catch(() => []),
    api(`/api/alerts/top_targets?minutes=${minutes}&limit=10`).catch(() => []),
  ]);

  // Timeline трафика
  multiAxisLine('ch-timeline', {
    labels: timeline.map(t => fmtTime(t.timestamp)),
    packets: timeline.map(t => t.packets),
    bytes:   timeline.map(t => t.bytes),
  });

  // Timeline алертов
  lineChart('ch-alerts-tl', {
    labels: alertsTl.map(t => fmtTime(t.timestamp)),
    datasets: [
      {
        label: 'Critical',
        data: alertsTl.map(t => t.critical),
        borderColor: '#ef4444',
        backgroundColor: 'rgba(239,68,68,0.15)',
        fill: true, tension: 0.25,
      },
      {
        label: 'Warning',
        data: alertsTl.map(t => t.warning),
        borderColor: '#f59e0b',
        backgroundColor: 'rgba(245,158,11,0.15)',
        fill: true, tension: 0.25,
      },
      {
        label: 'Info',
        data: alertsTl.map(t => t.info),
        borderColor: '#6366f1',
        backgroundColor: 'rgba(99,102,241,0.15)',
        fill: true, tension: 0.25,
      },
    ],
  });

  doughnut('ch-proto', {
    labels: proto.map(p => PROTOCOL_NAME[p.protocol] || p.protocol),
    data:   proto.map(p => p.packets),
  });

  barChart('ch-dir', {
    labels: dir.map(d => d.direction === 0 ? 'Ingress' : 'Egress'),
    data:   dir.map(d => d.packets),
    color:  '#3b82f6',
  });

  doughnut('ch-sev', {
    labels: sev.map(s => SEVERITY_RU[s.severity] || s.severity),
    data:   sev.map(s => s.count),
    colors: sev.map(s => s.severity === 'critical' ? '#ef4444'
                    : s.severity === 'warning'  ? '#f59e0b'
                    : '#6366f1'),
  });

  barChart('ch-view', {
    labels: view.map(v => v.view),
    data:   view.map(v => v.count),
    color:  '#8b5cf6',
  });

  barChart('ch-tsrc', {
    labels: tsrc.map(x => x.ip),
    data:   tsrc.map(x => x.count),
    color:  '#ef4444',
    horizontal: true,
  });

  barChart('ch-tdst', {
    labels: tdst.map(x => x.ip),
    data:   tdst.map(x => x.count),
    color:  '#f59e0b',
    horizontal: true,
  });
}

/* ============================================================
 *  Страница «Трафик»
 * ============================================================ */
async function renderTraffic() {
  const el = document.getElementById('page-traffic');
  if (!el) return;
  el.innerHTML = `
    <div class="card">
      <div class="card-title">Трафик во времени <span class="dim">packets / bytes</span></div>
      <div class="chart-wrap" style="height:320px"><canvas id="t-timeline"></canvas></div>
    </div>

    <div class="grid-2">
      <div class="card">
        <div class="card-title">Топ целевых портов</div>
        <div class="chart-wrap"><canvas id="t-ports"></canvas></div>
      </div>
      <div class="card">
        <div class="card-title">Топ подсетей (src → dst)</div>
        <div class="chart-wrap"><canvas id="t-subnets"></canvas></div>
      </div>
    </div>

    <div class="grid-2">
      <div class="card">
        <div class="card-title">Топ источников (трафик)</div>
        <div class="chart-wrap"><canvas id="t-tsrc"></canvas></div>
      </div>
      <div class="card">
        <div class="card-title">Топ целей (трафик)</div>
        <div class="chart-wrap"><canvas id="t-tdst"></canvas></div>
      </div>
    </div>
  `;

  const q = buildQueryString(state.filters);
  const minutes = state.filters.minutes || 60;

  const [timeline, ports, subnets, tsrc, tdst] = await Promise.all([
    api(`/api/traffic/timeline?${q}`).catch(() => []),
    api(`/api/traffic/by_port?minutes=${minutes}&port_type=dst`).catch(() => []),
    api(`/api/traffic/by_subnet?minutes=${minutes}&limit=15`).catch(() => []),
    api(`/api/traffic/top_sources?minutes=${minutes}&limit=15`).catch(() => []),
    api(`/api/traffic/top_targets?minutes=${minutes}&limit=15`).catch(() => []),
  ]);

  multiAxisLine('t-timeline', {
    labels: timeline.map(t => fmtTime(t.timestamp)),
    packets: timeline.map(t => t.packets),
    bytes:   timeline.map(t => t.bytes),
  });

  barChart('t-ports', {
    labels: ports.map(p => String(p.port)),
    data:   ports.map(p => p.packets),
    color:  '#3b82f6',
    horizontal: true,
  });

  barChart('t-subnets', {
    labels: subnets.map(s => `${s.src_subnet} → ${s.dst_subnet}`),
    data:   subnets.map(s => s.packets),
    color:  '#8b5cf6',
    horizontal: true,
  });

  barChart('t-tsrc', {
    labels: tsrc.map(x => x.ip),
    data:   tsrc.map(x => x.packets),
    color:  '#10b981',
    horizontal: true,
  });

  barChart('t-tdst', {
    labels: tdst.map(x => x.ip),
    data:   tdst.map(x => x.packets),
    color:  '#f59e0b',
    horizontal: true,
  });
}

/* ============================================================
 *  Страница «Топология»
 * ============================================================ */
async function renderTopology() {
  const el = document.getElementById('page-topology');
  if (!el) return;
  el.innerHTML = `
    <div class="card">
      <div class="card-title">
        Сетевая топология
        <span class="dim">перетаскивайте узлы мышью, двигайте canvas</span>
      </div>
      <div class="topology-controls">
        <button id="topo-fit">Уместить</button>
        <button id="topo-in">+</button>
        <button id="topo-out">−</button>
        <button id="topo-reset">Сбросить позиции</button>
        <button id="topo-physics">Упругий режим</button>
      </div>
      <div id="topology"></div>
    </div>
  `;

  document.getElementById('topo-fit').onclick    = fitTopology;
  document.getElementById('topo-in').onclick     = zoomIn;
  document.getElementById('topo-out').onclick    = zoomOut;
  document.getElementById('topo-reset').onclick  = () => {
    resetTopology();
    refreshTopology();
  };
  document.getElementById('topo-physics').onclick = (e) => {
    const btn = e.target;
    const enabled = btn.classList.toggle('active');
    setPhysics(enabled);
    btn.textContent = enabled ? 'Отключить упругость' : 'Упругий режим';
  };

  initTopology('topology');
  await refreshTopology();
}

async function refreshTopology() {
  const minutes = state.filters.minutes || 60;
  const [pairs, alerts] = await Promise.all([
    api(`/api/traffic/topology?minutes=${minutes}&min_packets=5&limit=200`).catch(() => []),
    api(`/api/alerts?minutes=${minutes}&limit=200`).catch(() => []),
  ]);
  updateTopology(pairs, alerts);
}

/* ============================================================
 *  Страница «Хосты»
 * ============================================================ */
async function renderHosts() {
  const el = document.getElementById('page-hosts');
  if (!el) return;
  el.innerHTML = `<div class="empty">Загрузка…</div>`;

  const hosts = await api('/api/hosts/status').catch(() => []);
  if (!hosts.length) {
    el.innerHTML = `<div class="card"><div class="empty">Нет зарегистрированных хостов</div></div>`;
    return;
  }

  el.innerHTML = `
    <div class="card">
      <div class="card-title">Сенсоры сбора <span class="dim">${hosts.length} шт.</span></div>
      <table>
        <thead>
          <tr>
            <th>Host ID</th>
            <th>Hostname</th>
            <th>OS / Arch</th>
            <th>Kernel</th>
            <th>Last seen</th>
            <th>Packets 1m</th>
            <th>Bytes 1m</th>
            <th>Статус</th>
          </tr>
        </thead>
        <tbody id="hosts-tbody"></tbody>
      </table>
    </div>
  `;

  const tbody = document.getElementById('hosts-tbody');
  tbody.innerHTML = hosts.map(h => `
    <tr>
      <td><code>${escapeHtml(h.host_id)}</code></td>
      <td>${escapeHtml(h.hostname)}</td>
      <td>${escapeHtml(h.os)} / ${escapeHtml(h.arch)}</td>
      <td>${escapeHtml(h.kernel_version)}</td>
      <td>${h.last_seen ? fmtTime(h.last_seen) : '—'}</td>
      <td>${Number(h.packets_1m || 0).toLocaleString()}</td>
      <td>${fmtBytes(h.bytes_1m || 0)}</td>
      <td>
        <span class="badge ${h.is_offline ? 'critical' : 'success'}">
          ${h.is_offline ? 'offline' : 'online'}
        </span>
      </td>
    </tr>
  `).join('');
}

/* ============================================================
 *  Страница «Алерты»
 * ============================================================ */
async function renderAlerts() {
  const el = document.getElementById('page-alerts');
  if (!el) return;

  // Показываем то, что уже в state (пришло по WS), плюс подтягиваем историю
  const minutes = state.filters.minutes || 60;
  const sev     = state.filters.severity  || '';
  const det     = state.filters.detector  || '';
  const vw      = state.filters.view      || '';

  const q = new URLSearchParams();
  q.set('minutes', minutes);
  q.set('limit', 200);
  if (state.filters.src_ip)  q.set('src_ip',  state.filters.src_ip);
  if (state.filters.dst_ip)  q.set('dst_ip',  state.filters.dst_ip);
  if (sev) q.set('severity', sev);
  if (det) q.set('detector', det);
  if (vw)  q.set('view', vw);

  const alerts = await api(`/api/alerts?${q}`).catch(() => []);

  el.innerHTML = `
    <div class="card">
      <div class="card-title">
        Алерты <span class="dim">${alerts.length} записей за ${minutes} мин</span>
      </div>
      <div class="filters-bar" style="margin-bottom:12px">
        <select id="a-sev">
          <option value="">Все severity</option>
          <option value="critical">Critical</option>
          <option value="warning">Warning</option>
          <option value="info">Info</option>
        </select>
        <select id="a-det">
          <option value="">Все детекторы</option>
          <option value="peer">peer</option>
        </select>
        <select id="a-view">
          <option value="">Все view</option>
          <option value="flow">flow</option>
          <option value="src_dst">src_dst</option>
          <option value="dst_service">dst_service</option>
          <option value="src">src</option>
          <option value="dst">dst</option>
          <option value="protocol">protocol</option>
        </select>
      </div>
      <div style="overflow-x:auto">
        <table>
          <thead>
            <tr>
              <th>Время</th>
              <th>Severity</th>
              <th>Detector</th>
              <th>View</th>
              <th>Источник</th>
              <th>Назначение</th>
              <th>Proto</th>
              <th>Пакеты</th>
              <th>Z-score</th>
            </tr>
          </thead>
          <tbody id="alerts-tbody"></tbody>
        </table>
      </div>
    </div>
  `;

  document.getElementById('a-sev').value  = sev;
  document.getElementById('a-det').value  = det;
  document.getElementById('a-view').value = vw;
  const rerender = () => {
    state.filters.severity = document.getElementById('a-sev').value;
    state.filters.detector = document.getElementById('a-det').value;
    state.filters.view     = document.getElementById('a-view').value;
    renderAlerts();
  };
  document.getElementById('a-sev').onchange  = rerender;
  document.getElementById('a-det').onchange  = rerender;
  document.getElementById('a-view').onchange = rerender;

  const tbody = document.getElementById('alerts-tbody');
  if (!alerts.length) {
    tbody.innerHTML = `<tr><td colspan="9"><div class="empty">Алертов нет</div></td></tr>`;
    return;
  }

  tbody.innerHTML = alerts.map(a => `
    <tr>
      <td>${fmtTime(a.timestamp)}</td>
      <td><span class="badge ${a.severity}">${a.severity}</span></td>
      <td>${escapeHtml(a.detector)}</td>
      <td><code>${escapeHtml(a.view)}</code></td>
      <td><code>${fmtEndpoint(a.src_ip, a.src_port)}</code></td>
      <td><code>${fmtEndpoint(a.dst_ip, a.dst_port)}</code></td>
      <td>${PROTOCOL_NAME[a.protocol] || '—'}</td>
      <td>${Number(a.packet_count || 0).toLocaleString()}</td>
      <td>${Number(a.z_score || 0).toFixed(2)}</td>
    </tr>
  `).join('');
}

/* ============================================================
 *  Toast-уведомления
 * ============================================================ */
function pushToast(alert) {
  const wrap = document.getElementById('toasts');
  if (!wrap) return;

  const div = document.createElement('div');
  div.className = `toast ${alert.severity || 'info'}`;
  const titleMap = {
    critical: '🚨 Критическая аномалия',
    warning:  '⚠️ Аномалия',
    info:     'ℹ️ Событие',
  };
  div.innerHTML = `
    <div class="t-title">
      <span>${titleMap[alert.severity] || 'Событие'}</span>
      <span class="t-close">✕</span>
    </div>
    <div class="t-body">
      <b>${escapeHtml(alert.view || '')}</b>
      ${escapeHtml(fmtEndpoint(alert.src_ip, alert.src_port))} →
      ${escapeHtml(fmtEndpoint(alert.dst_ip, alert.dst_port))}<br/>
      ${Number(alert.packet_count || 0).toLocaleString()} pkts ·
      Z=${Number(alert.z_score || 0).toFixed(2)}
    </div>
  `;
  div.querySelector('.t-close').onclick = () => div.remove();
  wrap.appendChild(div);
  setTimeout(() => div.remove(), 8000);
}

/* ============================================================
 *  Хелперы
 * ============================================================ */
function fmtTime(iso) {
  try {
    const d = new Date(iso);
    return d.toLocaleString('ru-RU', {
      month: '2-digit', day: '2-digit',
      hour: '2-digit', minute: '2-digit',
    });
  } catch { return iso; }
}

function fmtEndpoint(ip, port) {
  if (!ip) return '—';
  if (port == null || port < 0) return ip;
  return `${ip}:${port}`;
}

function fmtBytes(n) {
  n = Number(n) || 0;
  if (n < 1024) return n + ' B';
  if (n < 1024 ** 2) return (n / 1024).toFixed(1) + ' KB';
  if (n < 1024 ** 3) return (n / 1024 ** 2).toFixed(1) + ' MB';
  return (n / 1024 ** 3).toFixed(2) + ' GB';
}

function escapeHtml(s) {
  return String(s ?? '').replace(/[&<>"']/g, c => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;',
  }[c]));
}

/* ============================================================
 *  Boot
 * ============================================================ */
window.addEventListener('auth:logout', () => renderLogin());

if (isLoggedIn()) {
  renderApp();
} else {
  renderLogin();
}