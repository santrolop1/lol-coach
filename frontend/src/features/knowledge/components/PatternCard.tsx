import { motion } from 'framer-motion'
import { TrendingUp, AlertTriangle, Users, Activity, Sword } from 'lucide-react'
import { cn } from '@/lib/utils'
import type { Pattern } from '@/features/knowledge/types'

const CATEGORY_CFG: Record<string, { icon: React.ElementType; color: string; bg: string }> = {
  death:   { icon: AlertTriangle, color: 'text-red-400',     bg: 'bg-red-500/8     border-red-500/20'     },
  champion:{ icon: Sword,         color: 'text-orange-400',  bg: 'bg-orange-500/8  border-orange-500/20'  },
  pool:    { icon: Users,         color: 'text-yellow-400',  bg: 'bg-yellow-500/8  border-yellow-500/20'  },
  trend:   { icon: TrendingUp,    color: 'text-emerald-400', bg: 'bg-emerald-500/8 border-emerald-500/20' },
  habit:   { icon: Activity,      color: 'text-blue-400',    bg: 'bg-blue-500/8    border-blue-500/20'    },
}

function ConfidenceDots({ conf }: { conf: number }) {
  const filled = Math.round(conf * 5)
  return (
    <div className="flex gap-0.5 items-center">
      {Array.from({ length: 5 }).map((_, i) => (
        <div key={i} className={cn('h-1.5 w-1.5 rounded-full', i < filled ? 'bg-primary/70' : 'bg-border')} />
      ))}
      <span className="ml-1.5 text-[10px] text-muted-foreground">{Math.round(conf * 100)}% confianza</span>
    </div>
  )
}

interface PatternCardProps {
  pattern: Pattern
  delay?:  number
}

export function PatternCard({ pattern, delay = 0 }: PatternCardProps) {
  const cfg  = CATEGORY_CFG[pattern.category] ?? CATEGORY_CFG.habit
  const Icon = cfg.icon

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, delay }}
      className={cn('rounded-xl border p-4 space-y-3', cfg.bg)}
    >
      <div className="flex items-start gap-3">
        <Icon className={cn('h-4 w-4 mt-0.5 shrink-0', cfg.color)} />
        <div className="flex-1 min-w-0">
          <p className="text-sm font-semibold leading-snug">{pattern.title}</p>
          <p className="mt-1 text-xs text-muted-foreground leading-relaxed">{pattern.description}</p>
        </div>
      </div>

      {/* Actionable */}
      <div className="rounded-lg bg-background/50 border border-border/50 px-3 py-2">
        <p className="text-xs text-muted-foreground/70 uppercase tracking-wide mb-1">Qué hacer</p>
        <p className="text-xs leading-relaxed">{pattern.actionable}</p>
      </div>

      <div className="flex items-center justify-between pt-1">
        <ConfidenceDots conf={pattern.confidence} />
        <p className="text-[10px] text-muted-foreground/50">{pattern.evidence.split('.')[0]}.</p>
      </div>
    </motion.div>
  )
}
