import { cn } from '@/lib/utils'
import type { LucideIcon } from 'lucide-react'

export interface LoLHeroCardProps {
  title:       string
  subtitle?:   string
  meta?:       string
  icon?:       LucideIcon
  badge?:      React.ReactNode
  action?:     React.ReactNode
  accent?:     'primary' | 'accent' | 'gold'
  children?:   React.ReactNode
  className?:  string
}

const ACCENT_STYLES = {
  primary: 'from-primary/10 via-transparent to-transparent border-primary/20',
  accent:  'from-accent/10  via-transparent to-transparent border-accent/20',
  gold:    'from-yellow-500/10 via-transparent to-transparent border-yellow-500/20'
}

export function LoLHeroCard({
  title, subtitle, meta, icon: Icon, badge, action, accent = 'primary', children, className
}: LoLHeroCardProps) {
  return (
    <div className={cn(
      'relative rounded-xl border bg-gradient-to-r p-5 overflow-hidden',
      ACCENT_STYLES[accent],
      className
    )}>
      {/* Background glow */}
      <div className={cn(
        'absolute left-0 top-0 h-full w-1/3 opacity-30 blur-3xl',
        accent === 'primary' && 'bg-primary',
        accent === 'accent'  && 'bg-accent',
        accent === 'gold'    && 'bg-yellow-500'
      )} />

      <div className="relative flex items-start justify-between gap-4">
        <div className="flex items-center gap-3 min-w-0">
          {Icon && (
            <div className={cn(
              'shrink-0 rounded-lg p-2.5',
              accent === 'primary' && 'bg-primary/15 text-primary',
              accent === 'accent'  && 'bg-accent/15  text-accent',
              accent === 'gold'    && 'bg-yellow-500/15 text-yellow-400'
            )}>
              <Icon className="h-5 w-5" />
            </div>
          )}
          <div className="min-w-0">
            <div className="flex items-center gap-2 flex-wrap">
              <h3 className="font-semibold truncate">{title}</h3>
              {badge}
            </div>
            {subtitle && <p className="mt-0.5 text-sm text-muted-foreground truncate">{subtitle}</p>}
            {meta    && <p className="mt-0.5 text-xs text-muted-foreground/60">{meta}</p>}
          </div>
        </div>
        {action && <div className="shrink-0">{action}</div>}
      </div>

      {children && <div className="relative mt-4">{children}</div>}
    </div>
  )
}
