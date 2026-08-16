// main.js
import Chart from 'chart.js/auto';
import { DataSet, Network } from 'vis-network/standalone/esm/vis-network';
import './style.css';

// ---------- Глобальные переменные ----------
const API_BASE = '/api';
let token = localStorage.getItem('token');
let currentUser = null;
let ws = null;
let trafficChart = null;
let network = null;
let currentFilters = {};

// ---------- Аутентификация ----------
const loginPage = document.getElementById('login-page');
const app = document.getElementById('app');
const loginForm = document.getElementById('login-form');
const usernameInput = document.getElementById('username');
const passwordInput = document.getElementById('password');
const userInfoSpan = document.getElementById('user-info');
const logoutBtn = document.getElementById('logout-btn');

loginForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const username = usernameInput.value;
    const password = passwordInput.value;
    const res = await fetch(`${API_BASE}/token`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: new URLSearchParams({ username, password })
    });
    if (res.ok) {
        const data = await res.json();
        token = data.access_token;
        localStorage.setItem('token', token);
        await loadUser();
        showApp();
    } else {
        alert('Login failed');
    }
});

logoutBtn.addEventListener('click', () => {
    localStorage.removeItem('token');
    token = null;
    location.reload();
});

async function loadUser() {
    try {
        const data = await apiFetch(`${API_BASE}/me`);
        currentUser = data.username;
        userInfoSpan.textContent = `👤 ${currentUser}`;
    } catch (e) {
        // если токен невалиден
        localStorage.removeItem('token');
        token = null;
        showLogin();
    }
}

function showLogin() {
    loginPage.style.display = 'block';
    app.style.display = 'none';
}

function showApp() {
    loginPage.style.display = 'none';
    app.style.display = 'block';
    initTabs();
    loadSavedFilters();
    loadDashboard();
    connectWebSocket();
}

// ---------- API запросы с токеном ----------
async function apiFetch(url, options = {}) {
    const headers = { 'Authorization': `Bearer ${token}`, ...options.headers };
    const res = await fetch(url, { ...options, headers });
    if (res.status === 401) {
        localStorage.removeItem('token');
        token = null;
        showLogin();
        throw new Error('Unauthorized');
    }
    if (!res.ok) {
        throw new Error(await res.text());
    }
    return res.json();
}

// ---------- Инициализация страницы ----------
if (token) {
    loadUser().then(() => showApp());
} else {
    showLogin();
}

// ---------- Tabs ----------
function initTabs() {
    const tabs = document.querySelectorAll('.tab');
    const contents = {
        dashboard: document.getElementById('dashboard'),
        alerts: document.getElementById('alerts'),
        hosts: document.getElementById('hosts'),
        topology: document.getElementById('topology'),
        stats: document.getElementById('stats'),
    };
    tabs.forEach(tab => {
        tab.addEventListener('click', () => {
            tabs.forEach(t => t.classList.remove('active'));
            tab.classList.add('active');
            const target = tab.dataset.tab;
            Object.keys(contents).forEach(key => {
                contents[key].classList.toggle('active', key === target);
            });
            if (target === 'topology') loadTopology();
            if (target === 'hosts') loadHosts();
            if (target === 'dashboard') loadDashboard();
            if (target === 'stats') loadStats();
            if (target === 'alerts') loadAlerts();
        });
    });
}

// ---------- Фильтры ----------
async function loadSavedFilters() {
    try {
        const filters = await apiFetch(`${API_BASE}/filters`);
        const select = document.getElementById('filter-select');
        select.innerHTML = '<option value="">-- Выберите фильтр --</option>';
        filters.forEach(f => {
            const opt = document.createElement('option');
            opt.value = f.id;
            opt.textContent = f.name;
            select.appendChild(opt);
        });
    } catch (e) { /* ignore */ }
}

function collectFilterValues() {
    return {
        start_time: document.getElementById('start-time').value || undefined,
        end_time: document.getElementById('end-time').value || undefined,
        src_ip: document.getElementById('src-ip').value || undefined,
        dst_ip: document.getElementById('dst-ip').value || undefined,
        protocol: parseInt(document.getElementById('protocol').value) || undefined,
        direction: parseInt(document.getElementById('direction').value) || undefined,
        host_ip: document.getElementById('host-ip').value || undefined,
        min_packets: parseInt(document.getElementById('min-packets').value) || 10,
        anomaly_type: document.getElementById('anomaly-type').value || undefined,
    };
}

function applyFilters() {
    currentFilters = collectFilterValues();
    // Перезагружаем все вкладки
    loadDashboard();
    loadAlerts();
    loadTopology();
    loadStats();
}

async function saveFilter() {
    const name = prompt('Введите имя фильтра:');
    if (!name) return;
    const filterData = collectFilterValues();
    await apiFetch(`${API_BASE}/filters`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name, filter_data: filterData })
    });
    loadSavedFilters();
}

async function loadFilter(id) {
    if (!id) return;
    const filters = await apiFetch(`${API_BASE}/filters`);
    const f = filters.find(x => x.id == id);
    if (f) {
        const data = f.filter_data;
        document.getElementById('start-time').value = data.start_time || '';
        document.getElementById('end-time').value = data.end_time || '';
        document.getElementById('src-ip').value = data.src_ip || '';
        document.getElementById('dst-ip').value = data.dst_ip || '';
        document.getElementById('protocol').value = data.protocol || '';
        document.getElementById('direction').value = data.direction || '';
        document.getElementById('host-ip').value = data.host_ip || '';
        document.getElementById('min-packets').value = data.min_packets || 10;
        document.getElementById('anomaly-type').value = data.anomaly_type || '';
        applyFilters();
    }
}

// ---------- Загрузка данных ----------
async function loadDashboard() {
    const params = new URLSearchParams(currentFilters);
    const data = await apiFetch(`${API_BASE}/traffic?${params}`);
    const labels = data.map(d => new Date(d.timestamp).toLocaleTimeString());
    const packets = data.map(d => d.packets);
    const bytes = data.map(d => d.bytes);

    const ctx = document.getElementById('traffic-chart').getContext('2d');
    if (trafficChart) trafficChart.destroy();
    trafficChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [
                { label: 'Packets', data: packets, borderColor: '#3498db', yAxisID: 'y1', tension: 0.2 },
                { label: 'Bytes', data: bytes, borderColor: '#e67e22', yAxisID: 'y2', tension: 0.2 }
            ]
        },
        options: {
            responsive: true,
            scales: {
                y1: { type: 'linear', position: 'left' },
                y2: { type: 'linear', position: 'right', grid: { drawOnChartArea: false } }
            }
        }
    });
}

async function loadAlerts() {
    const params = new URLSearchParams(currentFilters);
    const data = await apiFetch(`${API_BASE}/alerts?${params}`);
    const list = document.getElementById('alert-list');
    list.innerHTML = data.map(a => `
        <div class="alert-item">
            <span class="time">${new Date(a.timestamp).toLocaleString()}</span>
            <span class="ip">${a.src_ip} → ${a.dst_ip}</span>
            (packets: ${a.packet_count}, bytes: ${a.byte_sum})
            <span class="badge">${a.anomaly_type}</span>
        </div>
    `).join('');
}

async function loadHosts() {
    const data = await apiFetch(`${API_BASE}/hosts`);
    const tbody = document.querySelector('#hosts-table tbody');
    tbody.innerHTML = data.map(h => `
        <tr>
            <td>${h.host_id}</td>
            <td>${h.hostname}</td>
            <td>${h.os}</td>
            <td>${h.arch}</td>
            <td>${new Date(h.boot_time_sec * 1000).toLocaleString()}</td>
        </tr>
    `).join('');
}

async function loadTopology() {
    const params = new URLSearchParams(currentFilters);
    const data = await apiFetch(`${API_BASE}/topology?${params}`);
    if (data.length === 0) {
        document.getElementById('topology-graph').innerHTML = 'Нет данных для топологии';
        return;
    }
    const nodes = new DataSet();
    const edges = new DataSet();
    const nodeSet = new Set();
    data.forEach(e => { nodeSet.add(e.src); nodeSet.add(e.dst); });
    const nodeList = Array.from(nodeSet).map((id, idx) => ({ id, label: id, color: '#3498db' }));
    nodes.add(nodeList);
    data.forEach(e => {
        edges.add({ from: e.src, to: e.dst, value: e.packets, label: `${e.packets} pkts` });
    });
    const container = document.getElementById('topology-graph');
    if (network) network.destroy();
    const options = {
        nodes: { shape: 'dot', size: 15 },
        edges: { smooth: true, width: 2 },
        physics: { stabilization: true }
    };
    network = new Network(container, { nodes, edges }, options);
}

async function loadStats() {
    const params = new URLSearchParams(currentFilters);
    // Протоколы
    const protoData = await apiFetch(`${API_BASE}/protocol_stats?${params}`);
    const portData = await apiFetch(`${API_BASE}/port_stats?${params}`);
    // Отрисовка статистик (можно добавить графики, пока просто таблицы)
    // ...
}

// ---------- WebSocket (реалтайм алерты) ----------
function connectWebSocket() {
    const wsUrl = `ws://${location.host}/ws`;
    ws = new WebSocket(wsUrl);
    ws.onmessage = (event) => {
        const alert = JSON.parse(event.data);
        // Добавляем в список алертов
        const list = document.getElementById('alert-list');
        const div = document.createElement('div');
        div.className = 'alert-item';
        div.innerHTML = `
            <span class="time">${new Date(alert.timestamp).toLocaleString()}</span>
            <span class="ip">${alert.src_ip} → ${alert.dst_ip}</span>
            (packets: ${alert.packet_count}, bytes: ${alert.byte_sum})
            <span class="badge">${alert.anomaly_type}</span>
        `;
        list.prepend(div);
        if (list.children.length > 100) list.removeChild(list.lastChild);
    };
    ws.onclose = () => {
        setTimeout(connectWebSocket, 3000);
    };
}

// ---------- Инициализация после загрузки ----------
// (showApp вызывается из login или при валидном токене)