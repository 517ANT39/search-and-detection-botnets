import { api } from './api.js';

/**
 * Собирает текущий набор фильтров из DOM.
 */
export function collectFilters(root = document) {
  const get = id => root.querySelector(id)?.value || undefined;
  const num = id => {
    const v = root.querySelector(id)?.value;
    return v === '' || v == null ? undefined : Number(v);
  };
  return {
    minutes:    num('#f-minutes') ?? 60,
    start_time: get('#f-start') || undefined,
    end_time:   get('#f-end')   || undefined,
    src_ip:     get('#f-src')   || undefined,
    dst_ip:     get('#f-dst')   || undefined,
    host_ip:    get('#f-host')  || undefined,
    protocol:   num('#f-protocol'),
    direction:  num('#f-direction'),
  };
}

export function applyFiltersToForm(data) {
  const set = (id, v) => {
    const el = document.querySelector(id);
    if (el) el.value = v ?? '';
  };
  set('#f-minutes',    data.minutes);
  set('#f-start',      data.start_time);
  set('#f-end',        data.end_time);
  set('#f-src',        data.src_ip);
  set('#f-dst',        data.dst_ip);
  set('#f-host',       data.host_ip);
  set('#f-protocol',   data.protocol);
  set('#f-direction',  data.direction);
}

export async function loadFilterList() {
  try {
    return await api('/api/filters');
  } catch {
    return [];
  }
}

export async function saveCurrentFilter(name) {
  const fd = collectFilters();
  return api('/api/filters', {
    method: 'POST',
    body: JSON.stringify({ name, filter_data: fd }),
  });
}

export async function deleteFilterById(id) {
  return api(`/api/filters/${id}`, { method: 'DELETE' });
}

export function buildQueryString(filters) {
  const q = new URLSearchParams();
  Object.entries(filters).forEach(([k, v]) => {
    if (v !== undefined && v !== null && v !== '') q.set(k, v);
  });
  return q.toString();
}