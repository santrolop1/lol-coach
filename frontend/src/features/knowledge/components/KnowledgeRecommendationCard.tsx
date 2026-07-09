import { motion } from 'framer-motion'
import { Zap, HelpCircle, BarChart2 } from 'lucide-react'
import { cn } from '@/lib/utils'
import type { Recommendation } from '@/features/knowledge/types'

const DIFF_COLOR: Record<string, string> = {
  Baja: 'text-emerald-400', Media: 'text-yellow-400', Alta: 'text-red-400'
}

interface RecommendationCardProps {
  rec:   Recommendation
  delay?: number
}

export function KnowledgeRecommendationCard({ rec, delay = 0 }: RecommendationCardProps) {
  const isHigh = rec.impact === 'Alto'
  const confPct = Math.round(rec.confidence * 100)

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.32, delay }}
      className="rounded-xl border bg-card overflow-hidden"
    >
      {/* Priority stripe */}
      <div className={cn(
        'px-4 py-2.5 flex items-center gap-3 border-b',
        isHigh
          ? 'bg-orange-500/8 border-orange-500/20'
          : 'bg-secondary border-border'
      )}>
        <span className={cn(
          'flex h-6 w-6 items-center justify-center rounded-full text-xs font-bold shrink-0',
          isHigh ? 'bg-orange-500/20 text-orange-400' : 'bg-border text-muted-foreground'
        )}>
          {rec.rank}
        </span>
        <p className="text-sm font-semibold flex-1 min-w-0 truncate">{rec.title}</p>
        {isHigh && (
          <span className="shrink-0 inline-flex items-center gap-1 text-[10px] font-bold text-orange-400">
            <Zap className="h-3 w-3" /> Alto
          </span>
        )}
      </div>

      {/* Body */}
      <div className="p-4 space-y-3">
        <p className="text-sm text-foreground/90 leading-relaxed">{rec.body}</p>

        {/* Why */}
        <div className="rounded-lg bg-background/50 border border-border/40 px-3 py-2 flex gap-2">
          <HelpCircle className="h-3.5 w-3.5 shrink-0 mt-0.5 text-muted-foreground/50" />
          <p className="text-xs text-muted-foreground leading-relaxed">{rec.why}</p>
        </div>

        {/* Goal */}
        <div className="rounded-lg border border-primary/20 bg-primary/5 px-3 py-2">
          <p className="text-[10px] uppercase tracking-wide text-muted-foreground mb-0.5">Objetivo asociado</p>
          <p className="text-xs font-medium">{rec.goal_str}</p>
        </div>

        {/* Stats row */}
        <div className="flex items-center gap-4 pt-1 text-xs flex-wrap">
          <div className="flex items-center gap-1.5">
            <BarChart2 className="h-3 w-3 text-muted-foreground/50" />
            <span className="text-muted-foreground">Impacto:</span>
            <span className="font-semibold">{rec.impact_pct}%</span>
          </div>
          <div>
            <span className="text-muted-foreground">Confianza: </span>
            <span className="font-semibold text-primary">{confPct}%</span>
          </div>
          <div>
            <span className="text-muted-foreground">Dificultad: </span>
            <span className={cn('font-semibold', DIFF_COLOR[rec.difficulty] ?? 'text-foreground')}>
              {rec.difficulty}
            </span>
          </div>
        </div>
      </div>
    </motion.div>
  )
}
