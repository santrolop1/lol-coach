import { motion } from 'framer-motion'
import { getGrade, getScoreColor } from '@/features/shared/utils/formatters'
import { cn } from '@/lib/utils'
import type { TimelinePoint } from '@/features/progress/types'

function ScoreBubble({ score }: { score: number | null }) {
  if (score == null) return (
    <div className="h-10 w-10 rounded-full border-2 border-border bg-card flex items-center justify-center text-xs text-muted-foreground">
      ?
    </div>
  )
  const grade = getGrade(score)
  const color = getScoreColor(score)
  const bgMap: Record<string, string> = {
    S: 'bg-emerald-500/15 border-emerald-500/40',
    A: 'bg-blue-500/15    border-blue-500/40',
    B: 'bg-yellow-500/15  border-yellow-500/40',
    C: 'bg-orange-500/15  border-orange-500/40',
    D: 'bg-red-500/15     border-red-500/40',
  }
  return (
    <div className={cn('h-10 w-10 rounded-full border-2 flex flex-col items-center justify-center', bgMap[grade])}>
      <span className={cn('text-[10px] font-bold leading-none', color)}>{grade}</span>
      <span className="text-[10px] text-muted-foreground leading-none">{score.toFixed(0)}</span>
    </div>
  )
}

const ARROW_ICONS: Record<string, string> = { up: '↑', down: '↓', flat: '→', '': '' }
const ARROW_COLOR: Record<string, string> = {
  up: 'text-emerald-400', down: 'text-red-400', flat: 'text-muted-foreground/50', '': ''
}

interface ProgressTimelineProps {
  points: TimelinePoint[]
}

export function ProgressTimeline({ points }: ProgressTimelineProps) {
  return (
    <div className="overflow-x-auto pb-2">
      <div className="flex items-end gap-0 min-w-max">
        {points.map((pt, i) => (
          <motion.div
            key={pt.label}
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: i * 0.07, duration: 0.3 }}
            className="flex flex-col items-center"
          >
            {/* Content */}
            <div className="flex flex-col items-center gap-1.5 px-4">
              <ScoreBubble score={pt.avg_score} />
              {pt.dominant_champion && (
                <span className="text-[10px] text-muted-foreground text-center max-w-[64px] truncate">
                  {pt.dominant_champion}
                </span>
              )}
            </div>

            {/* Connector line + arrow */}
            <div className="relative flex items-center w-full mt-3">
              {i > 0 && <div className="absolute left-0 top-1/2 -translate-y-1/2 w-1/2 h-px bg-border" />}
              {i < points.length - 1 && (
                <>
                  <div className="absolute right-0 top-1/2 -translate-y-1/2 w-1/2 h-px bg-border" />
                  {pt.trend_arrow && (
                    <span className={cn('absolute right-0 -translate-x-1/2 text-xs font-bold', ARROW_COLOR[pt.trend_arrow])}>
                      {ARROW_ICONS[pt.trend_arrow]}
                    </span>
                  )}
                </>
              )}
              <div className="mx-auto h-2 w-2 rounded-full bg-border z-10" />
            </div>

            {/* Label */}
            <span className="mt-2 text-[10px] text-muted-foreground text-center whitespace-nowrap px-2">
              {pt.label}
            </span>
          </motion.div>
        ))}
      </div>
    </div>
  )
}
