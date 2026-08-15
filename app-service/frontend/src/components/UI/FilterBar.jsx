import React from 'react'
import { Search, X } from 'lucide-react'

/**
 * Переиспользуемый набор фильтров для списковых страниц
 * (Инциденты, События, Узлы). Список фильтров и их опции
 * передаются пропсами — компонент не завязан на конкретные поля,
 * поэтому подходит для любых данных вашего backend.
 *
 * @param {Array<{key,label,options:[{value,label}]}>} filters
 * @param {object} values - текущие выбранные значения { [key]: value }
 * @param {(key, value) => void} onChange
 * @param {string} search - значение поля поиска (опционально)
 * @param {(value) => void} onSearchChange
 */
export default function FilterBar({ filters = [], values = {}, onChange, search, onSearchChange, searchPlaceholder = 'Поиск...' }) {
  const activeCount = Object.values(values).filter(Boolean).length + (search ? 1 : 0)

  function reset() {
    filters.forEach((f) => onChange(f.key, ''))
    if (onSearchChange) onSearchChange('')
  }

  return (
    <div className="flex flex-wrap items-center gap-2 mb-3">
      {onSearchChange && (
        <div className="flex items-center gap-2 h-9 px-3 rounded-lg border border-border bg-white text-[13px] text-muted min-w-[200px] flex-1 max-w-xs">
          <Search size={14} />
          <input
            value={search || ''}
            onChange={(e) => onSearchChange(e.target.value)}
            placeholder={searchPlaceholder}
            className="outline-none w-full bg-transparent placeholder:text-muted"
          />
        </div>
      )}

      {filters.map((f) => (
        <select
          key={f.key}
          value={values[f.key] || ''}
          onChange={(e) => onChange(f.key, e.target.value)}
          className="h-9 px-3 rounded-lg border border-border text-[13px] bg-white text-[#4a5468] focus:outline-none"
        >
          <option value="">{f.label}: Все</option>
          {f.options.map((o) => (
            <option key={o.value} value={o.value}>{o.label}</option>
          ))}
        </select>
      ))}

      {activeCount > 0 && (
        <button
          onClick={reset}
          className="h-9 px-3 rounded-lg border border-border text-[13px] flex items-center gap-1.5 text-muted hover:bg-surface"
        >
          <X size={13} /> Сбросить ({activeCount})
        </button>
      )}
    </div>
  )
}
