import { TrendingUp, TrendingDown, Minus } from 'lucide-react'
import { motion } from 'framer-motion'
import { cn } from '@/lib/utils'
import type { TrendInsight } from '@/features/progress/types'

const CATEGORY_CFG = {
  improving: { icon: TrendingUp,   color: 'text-emerald-400', bg: 'bg-emerald-500/8  border-emerald-500/20', dot: 'bg-emerald-500' },
  declining: { icon: TrendingDown, color: 'text-red-400',     bg: 'bg-red-500/8      border-red-500/20',     dot: 'bg-red-500'     },
  stable:    { icon: Minus,        color: 'text-blue-400',    bg: 'bg-blue-500/8     border-blue-500/20',    dot: 'bg-blue-500'    },
}

const CONF_BADGE: Record<string, string> = {
  high:   'text-emerald-400/70 bg-emerald-500/10',
  medium: 'text-yellow-400/70  bg-yellow-500/10',
  low:    'text-muted-foreground/50 bg-border/40',
}

const CONF_LABEL: Record<string, string> = {
  high: 'Alta confianza', medium: 'Media confianza', low: 'Baja confianza'
}

interface TrendInsightCardProps {
  insight: TrendInsight
  delay?:  number
}

export function TrendInsightCard({ insight, delay = 0 }: TrendInsightCardProps) {
  const cfg  = CATEGORY_CFG[insight.category] ?? CATEGORY_CFG.stable
  const Icon = cfg.icon

  return (
    <motion.div
      initial={{ opacity: 0, x: -6 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ duration: 0.3, delay }}
      className={cn('rounded-lg border p-3.5 flex gap-3', cfg.bg)}
    >
      <Icon className={cn('h-4 w-4 mt-0.5 shrink-0', cfg.color)} />
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium leading-snug">{insight.label}</p>
        <div className="flex items-center gap-2 mt-1.5 flex-wrap">
          <span className={cn('text-[11px] rounded-full px-2 py-0.5 font-medium', CONF_BADGE[insight.confidence])}>
            {CONF_LABEL[insight.confidence] ?? insight.confidence}
          </span>
          {insight.champion && (
            <span className="text-[11px] text-muted-foreground">
              Solo con {insight.champion}
            </span>
          )}
          <span className={cn('text-[11px] font-bold tabular-nums ml-auto', cfg.color)}>
            {insight.delta >= 0 ? '+' : ''}{insight.delta.toFixed(0)} pts
          </span>
        </div>
      </div>
    </motion.div>
  )
}
