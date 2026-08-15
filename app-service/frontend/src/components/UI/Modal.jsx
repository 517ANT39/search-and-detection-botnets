import React, { useEffect } from 'react'
import { X } from 'lucide-react'

/**
 * Простое модальное окно без внешних зависимостей.
 * Закрывается по клику на фон, крестик или клавишу Escape.
 */
export default function Modal({ open, onClose, title, children, width = 'max-w-2xl' }) {
  useEffect(() => {
    if (!open) return
    const onKey = (e) => { if (e.key === 'Escape') onClose?.() }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [open, onClose])

  if (!open) return null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div className="absolute inset-0 bg-black/40" onClick={onClose} />
      <div className={`relative bg-white rounded-xl2 shadow-card w-full ${width} p-4 max-h-[90vh] overflow-y-auto`}>
        <div className="flex items-center justify-between mb-3">
          <div className="text-[14px] font-medium">{title}</div>
          <button onClick={onClose} className="text-muted hover:text-[#1a2233] p-1 rounded-md hover:bg-surface">
            <X size={16} />
          </button>
        </div>
        {children}
      </div>
    </div>
  )
}
