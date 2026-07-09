/**
 * OverlayNotification — notificación efímera prioritaria.
 * Aparece sobre los widgets y desaparece automáticamente (controlado por backend via ttl).
 */

import { motion } from 'framer-motion'
import type { NotificationData } from '../types'

interface Props {
  notification: NotificationData
}

const PRIORITY_BG: Record<number, string> = {
  40: 'bg-red-900/80 border-red-500/60',      // CRITICAL
  30: 'bg-yellow-900/80 border-yellow-500/60', // HIGH
  20: 'bg-[#0d1117]/90 border-[#1e3a5f]/60',  // NORMAL
  10: 'bg-[#0d1117]/80 border-[#1e3a5f]/30',  // LOW
}

export function OverlayNotification({ notification }: Props) {
  const bgClass = PRIORITY_BG[notification.priority] ?? PRIORITY_BG[20]

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.96, y: -8 }}
      animate={{ opacity: 1, scale: 1, y: 0 }}
      exit={{ opacity: 0, scale: 0.96, y: -8 }}
      transition={{ duration: 0.2 }}
      className={`mx-2 mt-1 px-3 py-2 rounded-md border ${bgClass} ${
        notification.highlight ? 'ring-1 ring-yellow-400/50' : ''
      }`}
    >
      <p className="text-xs font-bold text-[#e2e8f0] mb-0.5">{notification.title}</p>
      {notification.lines.filter(Boolean).map((line, i) => (
        <p key={i} className="text-xs text-[#a0aec0] leading-snug">{line}</p>
      ))}
    </motion.div>
  )
}
