import { motion } from 'framer-motion'
import { LoLScoreRing, LoLGradeBadge } from '@/components/lol/LoLScoreBadge'
import { getGrade, getScoreColor } from '@/features/shared/utils/formatters'
import { cn } from '@/lib/utils'
import type { MatchReviewResponse } from '@/features/matches/types'

interface OverallScorePanelProps {
  data: MatchReviewResponse
}

function DeltaBadge({ delta }: { delta: number }) {
  const positive = delta >= 0
  return (
    <span className={cn(
      'inline-flex items-center rounded-full px-2.5 py-1 text-xs font-semibold',
      positive
        ? 'bg-emerald-500/10 border border-emerald-500/25 text-emerald-400'
        : 'bg-red-500/10 border border-red-500/25 text-red-400'
    )}>
      {delta >= 0 ? '↑' : '↓'} {Math.abs(delta).toFixed(0)} vs tu promedio
    </span>
  )
}

export function OverallScorePanel({ data }: OverallScorePanelProps) {
  const score = data.overall_score
  const grade = score != null ? getGrade(score) : 'D'

  const gradeLabels: Record<string, string> = {
    S: 'Excelente', A: 'Muy bueno', B: 'Bueno', C: 'Regular', D: 'Por mejorar'
  }

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.97 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ duration: 0.4, ease: 'easeOut' }}
      className="relative overflow-hidden rounded-2xl border border-primary/20 bg-gradient-to-br from-primary/8 via-card to-card p-6"
    >
      <div className="pointer-events-none absolute -right-8 -top-8 h-32 w-32 rounded-full bg-primary/10 blur-3xl" />

      <div className="relative flex items-center gap-6">
        {/* Ring */}
        <div className="shrink-0">
          {score != null ? (
            <LoLScoreRing score={score} size="lg" />
          ) : (
            <div className="h-32 w-32 rounded-full border-4 border-border flex items-center justify-center text-muted-foreground text-sm">
              —
            </div>
          )}
        </div>

        {/* Info */}
        <div className="flex-1 space-y-3">
          <div className="flex items-center gap-3 flex-wrap">
            {score != null && <LoLGradeBadge grade={grade} size="lg" />}
            <div>
              <p className="text-lg font-bold leading-tight">
                {score != null ? gradeLabels[grade] : 'Sin datos suficientes'}
              </p>
              {data.avg_overall != null && (
                <p className="text-sm text-muted-foreground mt-0.5">
                  Tu promedio: <span className={cn('font-semibold', score != null ? getScoreColor(data.avg_overall) : '')}>
                    {data.avg_overall.toFixed(0)}/100
                  </span>
                </p>
              )}
            </div>
          </div>

          {data.overall_delta != null && (
            <DeltaBadge delta={data.overall_delta} />
          )}

          <p className="text-xs text-muted-foreground">
            Basado en {data.sample_size} partidas de {data.role}
            {data.confidence === 'insufficient' && ' · Muestra insuficiente para análisis completo'}
            {data.confidence === 'preliminary' && ' · Análisis preliminar'}
          </p>
        </div>
      </div>
    </motion.div>
  )
}
