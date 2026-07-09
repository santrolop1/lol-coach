import { CheckCircle2, XCircle, Flame } from 'lucide-react'
import { motion } from 'framer-motion'
import { cn } from '@/lib/utils'
import type { Habit } from '@/features/progress/types'

interface HabitCardProps {
  habit: Habit
  delay?: number
}

export function HabitCard({ habit, delay = 0 }: HabitCardProps) {
  const isPositive = habit.type === 'positive'

  return (
    <motion.div
      initial={{ opacity: 0, y: 6 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, delay }}
      className={cn(
        'rounded-lg border p-3 flex items-start gap-3',
        isPositive
          ? 'bg-emerald-500/6 border-emerald-500/20'
          : 'bg-red-500/6    border-red-500/20'
      )}
    >
      {isPositive
        ? <CheckCircle2 className="h-4 w-4 mt-0.5 shrink-0 text-emerald-400" />
        : <XCircle     className="h-4 w-4 mt-0.5 shrink-0 text-red-400"     />
      }

      <div className="flex-1 min-w-0">
        <div className="flex items-center justify-between gap-2">
          <p className="text-sm font-medium leading-none">{habit.title}</p>
          <div className="flex items-center gap-1 shrink-0">
            {habit.is_active && <Flame className="h-3 w-3 text-orange-400" />}
            <span className={cn(
              'text-xs font-bold',
              isPositive ? 'text-emerald-400' : 'text-red-400'
            )}>
              {habit.streak}×
            </span>
          </div>
        </div>
        <p className="mt-1 text-xs text-muted-foreground leading-relaxed">{habit.description}</p>
      </div>
    </motion.div>
  )
}
