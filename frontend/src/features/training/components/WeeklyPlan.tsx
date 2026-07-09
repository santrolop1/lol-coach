import { motion } from 'framer-motion'
import { CheckCircle2, Zap, Clock } from 'lucide-react'
import { cn } from '@/lib/utils'
import type { WeeklySlot } from '../types'

const STATUS_CFG = {
  completed: { icon: CheckCircle2, color: 'text-emerald-400', bg: 'bg-emerald-500/8  border-emerald-500/25', label: 'Completado' },
  active:    { icon: Zap,          color: 'text-primary',     bg: 'bg-primary/10     border-primary/30',      label: 'Esta semana' },
  upcoming:  { icon: Clock,        color: 'text-muted-foreground/50', bg: 'bg-secondary/30 border-border/50', label: 'Próximamente' },
}

interface WeeklyPlanProps {
  slots: WeeklySlot[]
}

export function WeeklyPlan({ slots }: WeeklyPlanProps) {
  return (
    <div className="space-y-2">
      {slots.map((slot, i) => {
        const cfg  = STATUS_CFG[slot.status]
        const Icon = cfg.icon
        return (
          <motion.div
            key={slot.week}
            initial={{ opacity: 0, x: -8 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.25, delay: i * 0.06 }}
            className={cn(
              'flex items-start gap-3 rounded-xl border px-4 py-3',
              cfg.bg,
              slot.status === 'upcoming' ? 'opacity-60' : ''
            )}
          >
            {/* Week badge */}
            <div className={cn(
              'flex h-8 w-8 shrink-0 items-center justify-center rounded-lg text-xs font-bold',
              slot.is_current ? 'bg-primary text-primary-foreground' : 'bg-border text-muted-foreground'
            )}>
              S{slot.week}
            </div>

            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2">
                <p className="text-sm font-semibold">{slot.skill_name}</p>
                <span className={cn('text-[10px] font-bold', cfg.color)}>{cfg.label}</span>
              </div>
              <p className="text-xs text-muted-foreground mt-0.5 leading-relaxed line-clamp-2">
                {slot.goal_str}
              </p>
            </div>

            <Icon className={cn('h-4 w-4 shrink-0 mt-0.5', cfg.color)} />
          </motion.div>
        )
      })}
    </div>
  )
}
