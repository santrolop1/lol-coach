import { motion } from 'framer-motion'
import { HelpCircle, Activity, TrendingUp } from 'lucide-react'
import type { Exercise } from '../types'

interface ExerciseCardProps {
  exercise: Exercise
  delay?:   number
}

export function ExerciseCard({ exercise, delay = 0 }: ExerciseCardProps) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, delay }}
      className="rounded-xl border bg-card p-4 space-y-3"
    >
      <p className="text-sm font-semibold">{exercise.title}</p>

      {/* ¿Por qué? */}
      <div className="flex gap-2 rounded-lg bg-secondary/50 px-3 py-2">
        <HelpCircle className="h-3.5 w-3.5 shrink-0 mt-0.5 text-muted-foreground/50" />
        <p className="text-xs text-muted-foreground leading-relaxed">{exercise.why}</p>
      </div>

      {/* Cómo se mide */}
      <div className="flex gap-2 rounded-lg bg-secondary/50 px-3 py-2">
        <Activity className="h-3.5 w-3.5 shrink-0 mt-0.5 text-blue-400" />
        <p className="text-xs text-muted-foreground leading-relaxed">{exercise.how_measured}</p>
      </div>

      {/* Qué mejora */}
      <div className="flex gap-2 rounded-lg bg-emerald-500/5 border border-emerald-500/15 px-3 py-2">
        <TrendingUp className="h-3.5 w-3.5 shrink-0 mt-0.5 text-emerald-400" />
        <p className="text-xs text-muted-foreground leading-relaxed">{exercise.expected_gain}</p>
      </div>

      {/* Meta */}
      <div className="text-[11px] text-muted-foreground text-right">
        {exercise.required_success} de {exercise.target_games} partidas para completar
      </div>
    </motion.div>
  )
}
