import { motion } from 'framer-motion'
import { Target, CheckCircle2, Zap, Clock, AlertTriangle } from 'lucide-react'
import { cn } from '@/lib/utils'
import type { Goal } from '@/features/knowledge/types'

const STATUS_CFG = {
  completed:   { icon: CheckCircle2, color: 'text-emerald-400', bg: 'border-emerald-500/30 bg-emerald-500/6', bar: 'bg-emerald-500' },
  on_track:    { icon: Zap,          color: 'text-blue-400',    bg: 'border-blue-500/30    bg-blue-500/6',    bar: 'bg-blue-500'    },
  at_risk:     { icon: AlertTriangle,color: 'text-yellow-400',  bg: 'border-yellow-500/30  bg-yellow-500/6',  bar: 'bg-yellow-500'  },
  not_started: { icon: Clock,        color: 'text-muted-foreground', bg: 'border-border bg-card/60',          bar: 'bg-muted'       },
}

function deriveStatus(goal: Goal): 'completed' | 'on_track' | 'at_risk' | 'not_started' {
  if (goal.status === 'completed') return 'completed'
  if (goal.pct >= 80) return 'on_track'
  if (goal.pct >= 30) return 'at_risk'
  return 'not_started'
}

interface AdaptiveGoalCardProps {
  goal: Goal
}

export function AdaptiveGoalCard({ goal }: AdaptiveGoalCardProps) {
  const status = deriveStatus(goal)
  const cfg    = STATUS_CFG[status]
  const Icon   = cfg.icon

  const statusLabels = {
    completed: 'Objetivo completado', on_track: 'En camino', at_risk: 'En riesgo', not_started: 'Por empezar'
  }

  const total = goal.total_count || goal.check_window

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.98 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ duration: 0.4 }}
      className={cn('rounded-2xl border p-5 space-y-4', cfg.bg)}
    >
      {/* Header */}
      <div className="flex items-start justify-between gap-3 flex-wrap">
        <div className="flex items-center gap-2.5">
          <div className={cn('flex h-9 w-9 items-center justify-center rounded-xl border', cfg.bg)}>
            <Target className={cn('h-5 w-5', cfg.color)} />
          </div>
          <div>
            <p className="text-[10px] uppercase tracking-wider text-muted-foreground font-semibold">Objetivo adaptativo</p>
            <p className="text-base font-bold leading-tight mt-0.5">{goal.target_str} de {goal.metric_label}</p>
          </div>
        </div>
        <span className={cn('inline-flex items-center gap-1.5 rounded-full border px-3 py-1 text-[11px] font-semibold', cfg.bg, cfg.color)}>
          <Icon className="h-3 w-3" />
          {statusLabels[status]}
        </span>
      </div>

      {/* Progress */}
      <div className="space-y-1.5">
        <div className="flex items-center justify-between text-xs">
          <span className="text-muted-foreground">
            {goal.progress_count} de {total} partidas cumpliendo el objetivo
          </span>
          <span className={cn('font-bold', cfg.color)}>{goal.pct.toFixed(0)}%</span>
        </div>
        <div className="h-2 w-full rounded-full bg-border/50 overflow-hidden">
          <motion.div
            className={cn('h-full rounded-full', cfg.bar)}
            initial={{ width: 0 }}
            animate={{ width: `${goal.pct}%` }}
            transition={{ duration: 0.7, ease: 'easeOut', delay: 0.25 }}
          />
        </div>
        <div className="flex gap-1.5">
          {Array.from({ length: total }).map((_, i) => (
            <div
              key={i}
              className={cn('h-1.5 flex-1 rounded-full', i < goal.progress_count ? cfg.bar : 'bg-border/50')}
            />
          ))}
        </div>
      </div>

      {/* Started */}
      <p className="text-xs text-muted-foreground">
        Objetivo iniciado el {goal.created_at.slice(0, 10)}
        {goal.completed_at && ` · Completado el ${goal.completed_at.slice(0, 10)}`}
      </p>
    </motion.div>
  )
}
