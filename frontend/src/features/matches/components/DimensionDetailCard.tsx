import { CheckCircle2, AlertTriangle } from 'lucide-react'
import { motion } from 'framer-motion'
import { LoLCard } from '@/components/lol/LoLCard'
import { LoLScoreRing, LoLGradeBadge } from '@/components/lol/LoLScoreBadge'
import { getGrade } from '@/features/shared/utils/formatters'
import { cn } from '@/lib/utils'
import type { DimensionReview, MetricReview } from '@/features/matches/types'

// ── Metric row ─────────────────────────────────────────────────────────────────

function MetricRow({ m }: { m: MetricReview }) {
  const dirColor =
    m.direction === 'better' ? 'text-emerald-400' :
    m.direction === 'worse'  ? 'text-red-400'     :
    'text-muted-foreground'

  const dirIcon =
    m.direction === 'better' ? '↑' :
    m.direction === 'worse'  ? '↓' :
    '→'

  return (
    <div className="flex items-center justify-between py-1.5 border-b border-border/40 last:border-0">
      <span className="text-xs text-muted-foreground">{m.label}</span>
      <div className="flex items-center gap-3">
        {m.avg_str && (
          <span className="text-xs text-muted-foreground/50 tabular-nums">
            prom. {m.avg_str}
          </span>
        )}
        <span className={cn('text-xs font-bold tabular-nums flex items-center gap-0.5', dirColor)}>
          <span>{dirIcon}</span>
          <span>{m.value_str}</span>
        </span>
      </div>
    </div>
  )
}

// ── Main card ──────────────────────────────────────────────────────────────────

interface DimensionDetailCardProps {
  dim:   DimensionReview
  delay?: number
}

export function DimensionDetailCard({ dim, delay = 0 }: DimensionDetailCardProps) {
  const grade = dim.score != null ? getGrade(dim.score) : 'D'

  const headerBg =
    dim.is_best  ? 'border-emerald-500/30 bg-emerald-500/5' :
    dim.is_worst ? 'border-red-500/30 bg-red-500/5'         :
    'border-border bg-card/60'

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.35, delay }}
    >
      <LoLCard padding="none" className={cn('overflow-hidden border', headerBg)}>
        {/* Header */}
        <div className="flex items-center justify-between gap-3 px-4 py-3 border-b border-border/50">
          <div className="flex items-center gap-2">
            {dim.is_best && <CheckCircle2 className="h-3.5 w-3.5 text-emerald-400 shrink-0" />}
            {dim.is_worst && <AlertTriangle className="h-3.5 w-3.5 text-red-400 shrink-0" />}
            <span className="text-sm font-semibold">{dim.name_es}</span>
          </div>
          {dim.score != null && (
            <div className="flex items-center gap-2">
              <LoLGradeBadge grade={grade} size="sm" />
              <span className="text-sm font-bold tabular-nums">{dim.score.toFixed(0)}</span>
            </div>
          )}
        </div>

        {/* Score visual + context */}
        <div className="flex items-center gap-3 px-4 py-3 border-b border-border/40">
          {dim.score != null && <LoLScoreRing score={dim.score} size="sm" />}
          <div className="flex-1 min-w-0">
            <p className="text-xs text-muted-foreground leading-relaxed">{dim.context}</p>
            {dim.avg_score != null && (
              <p className="text-xs text-muted-foreground/50 mt-0.5">
                Media: {dim.avg_score.toFixed(0)}/100
              </p>
            )}
          </div>
        </div>

        {/* Metrics */}
        <div className="px-4 py-2">
          {dim.metrics.map((m) => (
            <MetricRow key={m.key} m={m} />
          ))}
        </div>

        {/* Notes (collapse by default — solo las más relevantes) */}
        {dim.notes.length > 0 && dim.notes[0] && (
          <p className="px-4 pb-3 text-[11px] text-muted-foreground/50 leading-relaxed border-t border-border/30 pt-2">
            {dim.notes[0]}
          </p>
        )}
      </LoLCard>
    </motion.div>
  )
}
