/**
 * OverlayWidget — widget individual del overlay.
 * Renderiza title + líneas de contenido con animación de entrada/salida.
 */

import { motion } from 'framer-motion'
import type { WidgetData } from '../types'

interface Props {
  widget: WidgetData
}

const PRIORITY_STYLES: Record<string, string> = {
  40: 'border-red-500/60',     // CRITICAL
  30: 'border-yellow-500/40',  // HIGH
  20: 'border-[#1e3a5f]/60',   // NORMAL
  10: 'border-[#1e3a5f]/30',   // LOW
}

export function OverlayWidget({ widget }: Props) {
  const borderClass = PRIORITY_STYLES[String(widget.priority)] ?? 'border-[#1e3a5f]/40'

  return (
    <motion.div
      layout
      initial={{ opacity: 0, y: -4 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -4 }}
      transition={{ duration: 0.18 }}
      className={`
        px-3 py-2 rounded-md
        bg-[#0d1117]/85 border ${borderClass}
        ${widget.highlight ? 'ring-1 ring-yellow-500/40' : ''}
      `}
    >
      {/* Title */}
      <div className="flex items-center gap-1.5 mb-0.5">
        {widget.icon && (
          <span className="text-xs leading-none">{widget.icon}</span>
        )}
        <span className="text-[10px] font-semibold text-[#4a7eb5] uppercase tracking-wider">
          {widget.title}
        </span>
      </div>

      {/* Líneas de contenido */}
      {widget.lines.filter(Boolean).map((line, i) => (
        <p
          key={i}
          className={`text-xs leading-snug ${
            i === 0
              ? 'text-[#e2e8f0] font-medium'
              : 'text-[#718096]'
          }`}
        >
          {i === 0 && <span className="text-[#c89b3c] mr-1">▶</span>}
          {line}
        </p>
      ))}
    </motion.div>
  )
}
