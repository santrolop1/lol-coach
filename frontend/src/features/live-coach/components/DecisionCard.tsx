/**
 * DecisionCard — muestra la decisión actual del Decision Intelligence Engine.
 * Diseño de overlay: decisión única con confianza y razones.
 */

import type { CurrentDecision } from '../types'

interface DecisionCardProps {
  decision: CurrentDecision
  compact?: boolean
}

const TYPE_COLORS: Record<string, string> = {
  emergency:   'border-red-500 bg-red-950/60',
  retreat:     'border-orange-500 bg-orange-950/50',
  power_spike: 'border-yellow-400 bg-yellow-950/60',
  recall:      'border-blue-400 bg-blue-950/50',
  objective:   'border-purple-400 bg-purple-950/50',
  trade:       'border-green-400 bg-green-950/50',
  all_in:      'border-red-400 bg-red-950/40',
  freeze:      'border-cyan-400 bg-cyan-950/50',
  crash:       'border-cyan-300 bg-cyan-950/40',
  slow_push:   'border-teal-400 bg-teal-950/40',
  split_push:  'border-indigo-400 bg-indigo-950/50',
  teamfight:   'border-pink-400 bg-pink-950/50',
  rotate:      'border-violet-400 bg-violet-950/40',
  ward:        'border-yellow-600 bg-yellow-950/30',
  farm:        'border-zinc-500 bg-zinc-900/60',
  wait:        'border-zinc-600 bg-zinc-900/40',
  build:       'border-amber-400 bg-amber-950/30',
  training:    'border-emerald-400 bg-emerald-950/30',
  information: 'border-zinc-600 bg-zinc-900/30',
}

const CONFIDENCE_COLOR = (pct: number) => {
  if (pct >= 80) return 'text-green-400'
  if (pct >= 60) return 'text-yellow-400'
  if (pct >= 40) return 'text-orange-400'
  return 'text-red-400'
}

export function DecisionCard({ decision, compact = false }: DecisionCardProps) {
  const colorClass = TYPE_COLORS[decision.type] ?? TYPE_COLORS.farm

  return (
    <div className={`rounded-lg border-l-4 ${colorClass} p-3 space-y-1`}>
      {/* Header */}
      <div className="flex items-center justify-between gap-2">
        <span className="text-xs font-semibold text-white/50 uppercase tracking-wider">
          DECISIÓN ACTUAL
        </span>
        <span className={`text-sm font-bold tabular-nums ${CONFIDENCE_COLOR(decision.confidence_pct)}`}>
          {decision.confidence_pct}%
        </span>
      </div>

      {/* Título de la decisión */}
      <p className="text-sm font-semibold text-white leading-snug">
        {decision.title}
      </p>

      {/* Explicación (solo si no es compact) */}
      {!compact && (
        <p className="text-xs text-white/70 leading-relaxed">
          {decision.explanation}
        </p>
      )}

      {/* Razones */}
      {!compact && decision.reasons.length > 0 && (
        <ul className="space-y-0.5 mt-1">
          {decision.reasons.slice(0, 2).map((r, i) => (
            <li key={i} className="text-xs text-white/50 flex items-start gap-1">
              <span className="opacity-60 mt-0.5">↳</span>
              <span>{r}</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
