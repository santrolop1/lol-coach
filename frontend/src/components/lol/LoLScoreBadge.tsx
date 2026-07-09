import { cn } from '@/lib/utils'
import {
  getGrade, getScoreColor, getScoreStroke, getGradeColor,
  type ScoreGrade
} from '@/features/shared/utils/formatters'

const CIRCUMFERENCE = 2 * Math.PI * 38   // r = 38, viewBox 100×100

// ── Ring variant ───────────────────────────────────────────────────────────────

interface ScoreRingProps {
  score:     number
  size?:     'sm' | 'md' | 'lg'
  className?: string
}

const RING_SIZES = { sm: 'w-16 h-16', md: 'w-24 h-24', lg: 'w-32 h-32' }
const TEXT_SIZES = { sm: 'text-sm',   md: 'text-xl',   lg: 'text-3xl'  }
const SUB_SIZES  = { sm: 'text-[7px]', md: 'text-[9px]', lg: 'text-xs'  }

export function LoLScoreRing({ score, size = 'md', className }: ScoreRingProps) {
  const filled = (score / 100) * CIRCUMFERENCE
  const stroke = getScoreStroke(score)

  return (
    <div className={cn('relative flex items-center justify-center', RING_SIZES[size], className)}>
      <svg viewBox="0 0 100 100" className="absolute inset-0 w-full h-full -rotate-90">
        {/* Track */}
        <circle cx="50" cy="50" r="38"
          fill="none"
          stroke="hsl(var(--border))"
          strokeWidth="6"
        />
        {/* Arc */}
        <circle cx="50" cy="50" r="38"
          fill="none"
          stroke={stroke}
          strokeWidth="6"
          strokeLinecap="round"
          strokeDasharray={`${filled} ${CIRCUMFERENCE}`}
          style={{ transition: 'stroke-dasharray 0.6s ease' }}
        />
      </svg>
      {/* Score label */}
      <div className="relative flex flex-col items-center leading-none">
        <span className={cn('font-bold tabular-nums', TEXT_SIZES[size], getScoreColor(score))}>
          {score.toFixed(0)}
        </span>
        <span className={cn('text-muted-foreground', SUB_SIZES[size])}>
          /100
        </span>
      </div>
    </div>
  )
}

// ── Pill variant ───────────────────────────────────────────────────────────────

interface ScorePillProps {
  score:     number
  className?: string
}

export function LoLScorePill({ score, className }: ScorePillProps) {
  return (
    <span className={cn(
      'inline-flex items-center rounded-full px-2 py-0.5 text-xs font-semibold tabular-nums',
      'bg-muted/50 border border-border',
      getScoreColor(score),
      className
    )}>
      {score.toFixed(0)}
    </span>
  )
}

// ── Grade badge ────────────────────────────────────────────────────────────────

interface GradeBadgeProps {
  grade:     ScoreGrade
  size?:     'sm' | 'md' | 'lg'
  className?: string
}

const GRADE_SIZES = {
  sm: 'text-xs w-5 h-5',
  md: 'text-sm w-7 h-7',
  lg: 'text-base w-9 h-9'
}

export function LoLGradeBadge({ grade, size = 'md', className }: GradeBadgeProps) {
  return (
    <span className={cn(
      'inline-flex items-center justify-center rounded font-bold border border-current/20 bg-current/10',
      GRADE_SIZES[size],
      getGradeColor(grade),
      className
    )}>
      {grade}
    </span>
  )
}

// ── Composite: Ring + Grade ────────────────────────────────────────────────────

interface LoLScoreBadgeProps {
  score:     number | null | undefined
  size?:     'sm' | 'md' | 'lg'
  className?: string
}

export function LoLScoreBadge({ score, size = 'md', className }: LoLScoreBadgeProps) {
  if (score == null) {
    return (
      <div className={cn(
        'flex items-center justify-center rounded-full border border-border bg-muted/30',
        RING_SIZES[size],
        className
      )}>
        <span className="text-muted-foreground text-xs">—</span>
      </div>
    )
  }

  const grade = getGrade(score)

  return (
    <div className={cn('flex flex-col items-center gap-1.5', className)}>
      <LoLScoreRing score={score} size={size} />
      <LoLGradeBadge grade={grade} size={size === 'lg' ? 'md' : 'sm'} />
    </div>
  )
}
