/**
 * Простая шина событий для глобального «Обновить».
 * Кнопка Refresh в Topbar вызывает triggerGlobalRefresh() —
 * все активные useApi()-хуки на странице подписаны через
 * onGlobalRefresh() и автоматически перезапрашивают свои данные.
 * Никакой бизнес-логики/эндпоинтов тут нет — только событие.
 */
const EVENT_NAME = 'netsentry:refresh-all'

export function triggerGlobalRefresh() {
  window.dispatchEvent(new CustomEvent(EVENT_NAME))
}

export function onGlobalRefresh(callback) {
  window.addEventListener(EVENT_NAME, callback)
  return () => window.removeEventListener(EVENT_NAME, callback)
}
