import { motion } from 'framer-motion'
import { CheckCircle2, TrendingUp, TrendingDown } from 'lucide-react'
import { cn } from '@/lib/utils'
import type { TrainingHistoryEntry } from '../types'

interface TrainingHistoryProps {
  entries: TrainingHistoryEntry[]
}

function formatDate(iso: string | null) {
  if (!iso) return '—'
  try {
    return new Date(iso).toLocaleDateString('es-ES', { day: 'numeric', month: 'short' })
  } catch {
    return iso.slice(0, 10)
  }
}

export function TrainingHistory({ entries }: TrainingHistoryProps) {
  if (entries.length === 0) return null

  return (
    <div className="space-y-2">
      {entries.map((entry, i) => {
        const winRate = entry.games_checked > 0
          ? Math.round((entry.success_count / entry.games_checked) * 100)
          : 0
        const hasImpact = entry.impact !== 0

        return (
          <motion.div
            key={entry.exercise_id + i}
            initial={{ opacity: 0, y: 6 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.25, delay: i * 0.05 }}
            className="flex items-start gap-3 rounded-xl border bg-card px-4 py-3"
          >
            <CheckCircle2 className="h-4 w-4 shrink-0 mt-0.5 text-emerald-400" />

            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium leading-snug">{entry.title}</p>
              <div className="flex items-center gap-3 mt-1 text-[11px] text-muted-foreground flex-wrap">
                <span className="text-primary/80 font-semibold">{entry.skill_name}</span>
                <span>·</span>
                <span>{entry.success_count}/{entry.games_checked} partidas ({winRate}%)</span>
                <span>·</span>
                <span>{formatDate(entry.started_at)} → {formatDate(entry.completed_at)}</span>
              </div>
            </div>

            {hasImpact && (
              <div className={cn(
                'flex items-center gap-1 text-xs font-bold shrink-0',
                entry.impact > 0 ? 'text-emerald-400' : 'text-red-400'
              )}>
                {entry.impact > 0
                  ? <TrendingUp className="h-3 w-3" />
                  : <TrendingDown className="h-3 w-3" />
                }
                {entry.impact > 0 ? '+' : ''}{entry.impact.toFixed(1)}
              </div>
            )}
          </motion.div>
        )
      })}
    </div>
  )
}
