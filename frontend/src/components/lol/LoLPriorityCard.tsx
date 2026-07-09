import { Target } from 'lucide-react'
import { cn } from '@/lib/utils'

export interface LoLPriorityCardProps {
  title:          string
  evidence?:      string
  recommendation?: string
  impactScore?:   number   // 0-100
  metricKey?:     string
  unit?:          string
  currentValue?:  number | null
  targetValue?:   number | null
  className?:     string
}

function ImpactBar({ score }: { score: number }) {
  const color =
    score >= 80 ? 'bg-red-400' :
    score >= 60 ? 'bg-orange-400' :
    score >= 40 ? 'bg-yellow-400' :
    'bg-muted-foreground/40'

  return (
    <div className="h-1 w-full rounded-full bg-muted/50">
      <div
        className={cn('h-full rounded-full transition-all duration-500', color)}
        style={{ width: `${score}%` }}
      />
    </div>
  )
}

export function LoLPriorityCard({
  title, evidence, recommendation, impactScore,
  currentValue, targetValue, unit, className
}: LoLPriorityCardProps) {
  return (
    <div className={cn(
      'rounded-lg border border-border bg-card/60 p-4 space-y-3',
      className
    )}>
      {/* Header */}
      <div className="flex items-start gap-2.5">
        <div className="mt-0.5 rounded-md bg-primary/15 p-1.5 shrink-0">
          <Target className="h-3.5 w-3.5 text-primary" />
        </div>
        <div className="flex-1 min-w-0">
          <p className="text-sm font-semibold leading-snug">{title}</p>
          {evidence && (
            <p className="mt-0.5 text-xs text-muted-foreground leading-relaxed">{evidence}</p>
          )}
        </div>
        {impactScore != null && (
          <span className="shrink-0 text-xs font-bold text-muted-foreground tabular-nums">
            {impactScore}
          </span>
        )}
      </div>

      {/* Impact bar */}
      {impactScore != null && <ImpactBar score={impactScore} />}

      {/* Current → Target */}
      {currentValue != null && targetValue != null && (
        <div className="flex items-center gap-2 text-xs text-muted-foreground">
          <span className="font-mono">{currentValue.toFixed(1)}{unit && ` ${unit}`}</span>
          <span className="text-muted-foreground/40">→</span>
          <span className="font-mono font-medium text-primary">{targetValue.toFixed(1)}{unit && ` ${unit}`}</span>
        </div>
      )}

      {/* Recommendation */}
      {recommendation && (
        <p className="text-xs text-muted-foreground border-t border-border/60 pt-2.5 leading-relaxed">
          {recommendation}
        </p>
      )}
    </div>
  )
}
