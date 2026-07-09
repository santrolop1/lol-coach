import { motion } from 'framer-motion'
import { Target, CheckCircle2, AlertTriangle, Clock, Zap } from 'lucide-react'
import { cn } from '@/lib/utils'
import type { WeeklyGoal } from '@/features/progress/types'

const STATUS_CONFIG = {
  completed:   { icon: CheckCircle2, color: 'text-emerald-400', bg: 'border-emerald-500/30 bg-emerald-500/5',  bar: 'bg-emerald-500' },
  on_track:    { icon: Zap,          color: 'text-blue-400',    bg: 'border-blue-500/30    bg-blue-500/5',     bar: 'bg-blue-500'    },
  at_risk:     { icon: AlertTriangle,color: 'text-yellow-400',  bg: 'border-yellow-500/30  bg-yellow-500/5',   bar: 'bg-yellow-500'  },
  not_started: { icon: Clock,        color: 'text-muted-foreground', bg: 'border-border bg-card/60',           bar: 'bg-muted'       },
}

interface GoalCardProps {
  goal: WeeklyGoal
}

export function GoalCard({ goal }: GoalCardProps) {
  const cfg  = STATUS_CONFIG[goal.status]
  const Icon = cfg.icon

  const statusLabels = {
    completed:   'Objetivo alcanzado',
    on_track:    'En camino',
    at_risk:     'En riesgo',
    not_started: 'Por empezar',
  }

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.98 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ duration: 0.35 }}
      className={cn('rounded-2xl border p-5 space-y-4', cfg.bg)}
    >
      {/* Header */}
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-center gap-2.5">
          <div className={cn('flex h-8 w-8 items-center justify-center rounded-lg border', cfg.bg)}>
            <Target className={cn('h-4 w-4', cfg.color)} />
          </div>
          <div>
            <p className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
              Objetivo semanal
            </p>
            <p className="text-sm font-bold leading-tight mt-0.5">{goal.title}</p>
          </div>
        </div>
        <span className={cn('shrink-0 inline-flex items-center gap-1 rounded-full border px-2.5 py-1 text-[11px] font-semibold', cfg.bg, cfg.color)}>
          <Icon className="h-3 w-3" />
          {statusLabels[goal.status]}
        </span>
      </div>

      {/* Progress bar */}
      <div className="space-y-1.5">
        <div className="flex items-center justify-between text-xs">
          <span className="text-muted-foreground">
            {goal.progress_count} / {goal.total_count} partidas cumpliendo el objetivo
          </span>
          <span className={cn('font-bold', cfg.color)}>{goal.pct.toFixed(0)}%</span>
        </div>
        <div className="h-2 w-full rounded-full bg-border/60 overflow-hidden">
          <motion.div
            className={cn('h-full rounded-full', cfg.bar)}
            initial={{ width: 0 }}
            animate={{ width: `${goal.pct}%` }}
            transition={{ duration: 0.6, ease: 'easeOut', delay: 0.2 }}
          />
        </div>
        {/* Individual dots */}
        <div className="flex gap-1.5 pt-0.5">
          {Array.from({ length: goal.total_count }).map((_, i) => (
            <div
              key={i}
              className={cn(
                'h-1.5 flex-1 rounded-full transition-colors',
                i < goal.progress_count ? cfg.bar : 'bg-border/60'
              )}
            />
          ))}
        </div>
      </div>

      {/* Motivation */}
      <p className="text-xs text-muted-foreground leading-relaxed">{goal.motivation}</p>
    </motion.div>
  )
}
