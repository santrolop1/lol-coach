import type { LucideIcon } from 'lucide-react'
import { Lightbulb } from 'lucide-react'
import { cn } from '@/lib/utils'

type InsightVariant = 'info' | 'warning' | 'success' | 'tip'

export interface LoLInsightCardProps {
  icon?:      LucideIcon
  title:      string
  body?:      string
  variant?:   InsightVariant
  action?:    React.ReactNode
  className?: string
}

const VARIANT_STYLES: Record<InsightVariant, { wrap: string; icon: string }> = {
  info:    { wrap: 'bg-blue-500/10    border-blue-500/20',    icon: 'text-blue-400'    },
  warning: { wrap: 'bg-yellow-500/10  border-yellow-500/20',  icon: 'text-yellow-400'  },
  success: { wrap: 'bg-emerald-500/10 border-emerald-500/20', icon: 'text-emerald-400' },
  tip:     { wrap: 'bg-primary/10     border-primary/20',     icon: 'text-primary'     }
}

export function LoLInsightCard({
  icon: Icon = Lightbulb, title, body, variant = 'tip', action, className
}: LoLInsightCardProps) {
  const styles = VARIANT_STYLES[variant]

  return (
    <div className={cn('rounded-lg border p-4 flex gap-3', styles.wrap, className)}>
      <Icon className={cn('h-4 w-4 mt-0.5 shrink-0', styles.icon)} />
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium leading-snug">{title}</p>
        {body && (
          <p className="mt-1 text-xs text-muted-foreground leading-relaxed">{body}</p>
        )}
        {action && <div className="mt-2">{action}</div>}
      </div>
    </div>
  )
}
