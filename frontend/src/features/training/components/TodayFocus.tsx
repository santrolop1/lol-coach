import { motion } from 'framer-motion'
import { Target, Lightbulb, CheckCircle, ChevronRight } from 'lucide-react'
import { cn } from '@/lib/utils'
import type { DailyPlan, Exercise } from '../types'

interface TodayFocusProps {
  plan:     DailyPlan
  exercise: Exercise
}

export function TodayFocus({ plan, exercise }: TodayFocusProps) {
  const pct       = exercise.games_checked > 0
    ? Math.round((exercise.success_count / exercise.target_games) * 100)
    : 0

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.35 }}
      className="rounded-2xl border border-primary/30 bg-gradient-to-br from-primary/8 to-primary/3 overflow-hidden"
    >
      {/* Header */}
      <div className="flex items-center gap-3 px-5 py-3.5 border-b border-primary/15">
        <Target className="h-4 w-4 text-primary shrink-0" />
        <span className="text-xs font-semibold uppercase tracking-wider text-primary/80">
          Foco de hoy — {plan.skill_name}
        </span>
        <span className="ml-auto text-[10px] text-muted-foreground">
          {plan.priority_label}
        </span>
      </div>

      {/* Exercise title */}
      <div className="px-5 pt-4 pb-2">
        <h2 className="text-lg font-bold leading-snug">{exercise.title}</h2>
        <p className="text-sm text-muted-foreground mt-1 leading-relaxed">{exercise.why}</p>
      </div>

      {/* Progress bar */}
      <div className="px-5 pb-4 space-y-2">
        <div className="flex items-center justify-between text-xs text-muted-foreground">
          <span>{exercise.success_count} / {exercise.required_success} partidas cumplidas</span>
          <span className="text-primary font-semibold">{exercise.games_checked} / {exercise.target_games} jugadas</span>
        </div>
        <div className="h-2 rounded-full bg-border overflow-hidden">
          <motion.div
            className="h-full rounded-full bg-primary"
            initial={{ width: 0 }}
            animate={{ width: `${pct}%` }}
            transition={{ duration: 0.6, ease: 'easeOut', delay: 0.2 }}
          />
        </div>

        {/* Dots */}
        <div className="flex gap-2 pt-1">
          {Array.from({ length: exercise.target_games }).map((_, i) => {
            const dot = exercise.dots[i]
            return (
              <div key={i} className={cn(
                'h-6 w-6 rounded-full border-2 flex items-center justify-center text-[10px] font-bold transition-all',
                !dot
                  ? 'border-border bg-background text-muted-foreground/40'
                  : dot.success
                  ? 'border-emerald-500 bg-emerald-500/15 text-emerald-400'
                  : 'border-red-500/50 bg-red-500/8 text-red-400'
              )}>
                {dot ? (dot.success ? '✓' : '✗') : (i + 1)}
              </div>
            )
          })}
        </div>
      </div>

      {/* Tips row */}
      <div className="grid grid-cols-2 gap-0 border-t border-primary/10">
        <div className="flex items-start gap-2 px-5 py-3 border-r border-primary/10">
          <Lightbulb className="h-3.5 w-3.5 shrink-0 mt-0.5 text-yellow-400" />
          <p className="text-xs leading-relaxed text-muted-foreground">{plan.focus_tip}</p>
        </div>
        <div className="flex items-start gap-2 px-5 py-3">
          <CheckCircle className="h-3.5 w-3.5 shrink-0 mt-0.5 text-emerald-400" />
          <p className="text-xs leading-relaxed text-muted-foreground">{plan.success_condition}</p>
        </div>
      </div>

      {/* What unlocks */}
      {exercise.unlocks && (
        <div className="flex items-center gap-2 px-5 py-2.5 bg-background/30 border-t border-primary/10">
          <ChevronRight className="h-3 w-3 text-muted-foreground/50 shrink-0" />
          <p className="text-[11px] text-muted-foreground">
            Al completarlo, desbloquearás el bloque de <span className="font-semibold text-foreground">
              {exercise.unlocks === 'farming' ? 'Farm' :
               exercise.unlocks === 'impact' ? 'Impacto' :
               exercise.unlocks === 'pressure' ? 'Presión macro' :
               exercise.unlocks === 'consistency' ? 'Consistencia' :
               exercise.unlocks}
            </span>.
          </p>
        </div>
      )}
    </motion.div>
  )
}
