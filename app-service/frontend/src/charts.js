import {
  Chart,
  LineController, LineElement, PointElement,
  BarController, BarElement,
  DoughnutController, ArcElement,
  CategoryScale, LinearScale, TimeScale, LogarithmicScale,
  Tooltip, Legend, Filler, Title,
} from 'chart.js';
import 'chartjs-adapter-date-fns';

Chart.register(
  LineController, LineElement, PointElement,
  BarController, BarElement,
  DoughnutController, ArcElement,
  CategoryScale, LinearScale, TimeScale, LogarithmicScale,
  Tooltip, Legend, Filler, Title,
);

Chart.defaults.color = '#64748b';
Chart.defaults.borderColor = '#e2e8f0';
Chart.defaults.font.family = "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif";
Chart.defaults.font.size = 11;

// Цвета фонов для tooltip
const TOOLTIP_STYLE = {
  backgroundColor: '#ffffff',
  titleColor: '#1e293b',
  bodyColor: '#1e293b',
  borderColor: '#e2e8f0',
  borderWidth: 1,
  padding: 10,
  cornerRadius: 8,
  boxShadow: '0 4px 12px rgba(15,23,42,0.10)',
};

const registry = {};

function destroy(id) {
  if (registry[id]) {
    registry[id].destroy();
    delete registry[id];
  }
}

export function lineChart(id, { labels = [], datasets = [], logY = false, yTitle } = {}) {
  destroy(id);
  const ctx = document.getElementById(id);
  if (!ctx) return null;

  registry[id] = new Chart(ctx, {
    type: 'line',
    data: { labels, datasets },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      interaction: { mode: 'index', intersect: false },
      plugins: {
        legend: { position: 'top', align: 'end', labels: { boxWidth: 10, padding: 12 } },
        tooltip: {
          backgroundColor: 'rgba(220,38,38,0.10)',
          borderColor: '#dc2626',
          borderWidth: 1,
          padding: 10,
          titleColor: '#d7dde5',
          bodyColor: '#d7dde5',
        },
      },
      scales: {
        x: {
          type: 'category',
          grid: { color: 'rgba(45,56,70,0.5)', drawBorder: false },
          ticks: { maxRotation: 0, autoSkip: true, maxTicksLimit: 12 },
        },
        y: {
          type: logY ? 'logarithmic' : 'linear',
          grid: { color: 'rgba(45,56,70,0.5)', drawBorder: false },
          title: yTitle ? { display: true, text: yTitle } : undefined,
          beginAtZero: !logY,
        },
      },
      elements: { point: { radius: 0, hoverRadius: 4 } },
    },
  });
  return registry[id];
}

export function multiAxisLine(id, { labels, packets, bytes }) {
  destroy(id);
  const ctx = document.getElementById(id);
  if (!ctx) return null;

  registry[id] = new Chart(ctx, {
    type: 'line',
    data: {
      labels,
      datasets: [
        {
          label: 'Packets',
          data: packets,
          borderColor: '#2563eb',
          backgroundColor: 'rgba(37,99,235,0.10)',
          yAxisID: 'yP',
          tension: 0.25,
          fill: true,
          borderWidth: 2,
        },
        {
          label: 'Bytes',
          data: bytes,
          borderColor: '#f59e0b',
          backgroundColor: 'rgba(245,158,11,0.1)',
          yAxisID: 'yB',
          tension: 0.25,
          fill: true,
          borderWidth: 2,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      interaction: { mode: 'index', intersect: false },
      plugins: {
        legend: { position: 'top', align: 'end', labels: { boxWidth: 10, padding: 12 } },
      },
      scales: {
        x: {
          grid: { color: 'rgba(45,56,70,0.5)' },
          ticks: { maxRotation: 0, autoSkip: true, maxTicksLimit: 12 },
        },
        yP: {
          position: 'left',
          grid: { color: 'rgba(45,56,70,0.5)' },
          title: { display: true, text: 'Packets' },
          beginAtZero: true,
        },
        yB: {
          position: 'right',
          grid: { drawOnChartArea: false },
          title: { display: true, text: 'Bytes' },
          beginAtZero: true,
        },
      },
      elements: { point: { radius: 0, hoverRadius: 4 } },
    },
  });
  return registry[id];
}

export function barChart(id, { labels, data, color = '#3b82f6', horizontal = false, label = 'Value' } = {}) {
  destroy(id);
  const ctx = document.getElementById(id);
  if (!ctx) return null;

  registry[id] = new Chart(ctx, {
    type: 'bar',
    data: {
      labels,
      datasets: [{
        label,
        data,
        backgroundColor: color,
        borderRadius: 4,
        borderSkipped: false,
      }],
    },
    options: {
      indexAxis: horizontal ? 'y' : 'x',
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false },
        tooltip: {
          backgroundColor: '#1a2028',
          borderColor: '#2d3846',
          borderWidth: 1,
        },
      },
      scales: {
        x: { grid: { color: 'rgba(45,56,70,0.5)' }, beginAtZero: true },
        y: { grid: { color: 'rgba(45,56,70,0.5)' }, beginAtZero: true },
      },
    },
  });
  return registry[id];
}

export function doughnut(id, { labels, data, colors }) {
  destroy(id);
  const ctx = document.getElementById(id);
  if (!ctx) return null;

  const palette = colors || [
  '#2563eb', '#d97706', '#059669',
  '#dc2626', '#7c3aed', '#0891b2',
  '#db2777', '#65a30d',
];

  registry[id] = new Chart(ctx, {
    type: 'doughnut',
    data: {
      labels,
      datasets: [{
        data,
        backgroundColor: palette,
        borderWidth: 0,
        hoverOffset: 6,
      }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      cutout: '65%',
      plugins: {
        legend: {
          position: 'right',
          labels: { boxWidth: 10, padding: 10 },
        },
        tooltip: {
          backgroundColor: '#1a2028',
          borderColor: '#2d3846',
          borderWidth: 1,
        },
      },
    },
  });
  return registry[id];
}

export function destroyAll() {
  Object.keys(registry).forEach(destroy);
}