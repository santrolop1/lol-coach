import { CheckCircle2, Clock, SkipForward } from 'lucide-react'
import { motion } from 'framer-motion'
import { cn } from '@/lib/utils'
import type { MemoryEntry } from '@/features/knowledge/types'

const STATUS_CFG = {
  completed: { icon: CheckCircle2, color: 'text-emerald-400', dot: 'bg-emerald-500', line: 'bg-emerald-500/30' },
  active:    { icon: Clock,        color: 'text-primary',     dot: 'bg-primary',     line: 'bg-primary/30'     },
  skipped:   { icon: SkipForward,  color: 'text-muted-foreground', dot: 'bg-muted', line: 'bg-border'          },
}

const STATUS_LABEL: Record<string, string> = {
  completed: 'Completado', active: 'En progreso', skipped: 'Omitido'
}

interface MemoryTimelineProps {
  entries: MemoryEntry[]
}

export function MemoryTimeline({ entries }: MemoryTimelineProps) {
  if (entries.length === 0) return null

  return (
    <div className="space-y-0">
      {entries.map((entry, i) => {
        const cfg  = STATUS_CFG[entry.status] ?? STATUS_CFG.skipped
        const Icon = cfg.icon
        const isLast = i === entries.length - 1

        return (
          <motion.div
            key={i}
            initial={{ opacity: 0, x: -6 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: i * 0.06, duration: 0.25 }}
            className="flex gap-3"
          >
            {/* Timeline dot + line */}
            <div className="flex flex-col items-center">
              <div className={cn('h-6 w-6 rounded-full border-2 border-background flex items-center justify-center shrink-0', cfg.dot)}>
                <Icon className="h-3 w-3 text-background" />
              </div>
              {!isLast && (
                <div className={cn('w-0.5 flex-1 min-h-[24px]', cfg.line)} />
              )}
            </div>

            {/* Content */}
            <div className={cn('flex-1 pb-4 min-w-0', isLast ? 'pb-0' : '')}>
              <div className="flex items-start justify-between gap-2">
                <p className="text-sm font-medium leading-snug">{entry.goal_title}</p>
                <span className={cn('shrink-0 text-[11px] font-semibold', cfg.color)}>
                  {STATUS_LABEL[entry.status]}
                </span>
              </div>
              <div className="flex items-center gap-2 mt-0.5 text-[11px] text-muted-foreground">
                <span>Iniciado: {entry.created_at}</span>
                {entry.completed_at && (
                  <>
                    <span>·</span>
                    <span>Completado: {entry.completed_at}</span>
                  </>
                )}
              </div>
            </div>
          </motion.div>
        )
      })}
    </div>
  )
}
