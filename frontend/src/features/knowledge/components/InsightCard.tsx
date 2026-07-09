import { motion } from 'framer-motion'
import { TrendingUp, TrendingDown, Minus } from 'lucide-react'
import { cn } from '@/lib/utils'
import type { Insight } from '@/features/knowledge/types'

const CATEGORY_CFG = {
  positive: { icon: TrendingUp,   color: 'text-emerald-400', bg: 'bg-emerald-500/8  border-emerald-500/20' },
  negative: { icon: TrendingDown, color: 'text-red-400',     bg: 'bg-red-500/8      border-red-500/20'     },
  neutral:  { icon: Minus,        color: 'text-blue-400',    bg: 'bg-blue-500/8     border-blue-500/20'    },
}

interface InsightCardProps {
  insight: Insight
  delay?:  number
}

export function InsightCard({ insight, delay = 0 }: InsightCardProps) {
  const cfg  = CATEGORY_CFG[insight.category] ?? CATEGORY_CFG.neutral
  const Icon = cfg.icon

  return (
    <motion.div
      initial={{ opacity: 0, x: -6 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ duration: 0.28, delay }}
      className={cn('rounded-lg border p-3.5 flex gap-3', cfg.bg)}
    >
      <span className="shrink-0 flex h-5 w-5 items-center justify-center rounded-full bg-background/40 text-[11px] font-bold text-muted-foreground mt-0.5">
        {insight.rank}
      </span>
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium leading-snug">{insight.text}</p>
        <div className="flex items-center gap-2 mt-1.5 flex-wrap">
          <Icon className={cn('h-3 w-3 shrink-0', cfg.color)} />
          <p className="text-[11px] text-muted-foreground leading-relaxed">{insight.evidence}</p>
          <span className={cn('ml-auto text-[11px] font-bold tabular-nums', cfg.color)}>
            {Math.round(insight.confidence * 100)}%
          </span>
        </div>
      </div>
    </motion.div>
  )
}
