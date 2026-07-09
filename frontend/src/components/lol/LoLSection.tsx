import { cn } from '@/lib/utils'

export interface LoLSectionProps {
  title:       string
  subtitle?:   string
  action?:     React.ReactNode
  children:    React.ReactNode
  className?:  string
  divider?:    boolean
}

export function LoLSection({ title, subtitle, action, children, className, divider = false }: LoLSectionProps) {
  return (
    <section className={cn('space-y-4', className)}>
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xs font-semibold uppercase tracking-widest text-muted-foreground">
            {title}
          </h2>
          {subtitle && (
            <p className="mt-0.5 text-sm text-muted-foreground/70">{subtitle}</p>
          )}
        </div>
        {action && <div className="shrink-0">{action}</div>}
      </div>
      {divider && <div className="h-px bg-border" />}
      {children}
    </section>
  )
}
