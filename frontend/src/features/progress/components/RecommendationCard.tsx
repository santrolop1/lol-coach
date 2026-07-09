import { motion } from 'framer-motion'
import { Zap, ArrowRight } from 'lucide-react'
import { cn } from '@/lib/utils'
import type { Recommendation } from '@/features/progress/types'

interface RecommendationCardProps {
  rec:   Recommendation
  delay?: number
}

const RANK_BG = ['bg-primary/15 border-primary/30', 'bg-secondary border-border', 'bg-secondary border-border']

export function RecommendationCard({ rec, delay = 0 }: RecommendationCardProps) {
  const isHigh = rec.impact === 'high'

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, delay }}
      className="rounded-xl border bg-card p-4 flex gap-3"
    >
      {/* Rank badge */}
      <div className={cn(
        'shrink-0 h-7 w-7 rounded-full border flex items-center justify-center text-xs font-bold',
        RANK_BG[rec.rank - 1] ?? RANK_BG[2]
      )}>
        {rec.rank}
      </div>

      <div className="flex-1 min-w-0 space-y-1">
        <div className="flex items-start justify-between gap-2">
          <p className="text-sm font-semibold leading-snug">{rec.title}</p>
          {isHigh && (
            <span className="shrink-0 inline-flex items-center gap-1 rounded-full bg-orange-500/10 border border-orange-500/20 px-2 py-0.5 text-[10px] font-bold text-orange-400">
              <Zap className="h-2.5 w-2.5" /> Alto impacto
            </span>
          )}
        </div>
        <p className="text-xs text-muted-foreground leading-relaxed">{rec.body}</p>
        <p className="text-[11px] text-muted-foreground/50 flex items-center gap-1 pt-0.5">
          <ArrowRight className="h-3 w-3 shrink-0" />
          {rec.evidence}
        </p>
      </div>
    </motion.div>
  )
}
