import type { LucideIcon } from 'lucide-react'
import { Inbox } from 'lucide-react'
import { cn } from '@/lib/utils'

export interface LoLEmptyStateProps {
  icon?:        LucideIcon
  title:        string
  description?: string
  action?:      React.ReactNode
  size?:        'sm' | 'md' | 'lg'
  className?:   string
}

const ICON_SIZES  = { sm: 'h-8  w-8',  md: 'h-10 w-10', lg: 'h-12 w-12' }
const ICON_WRAP   = { sm: 'p-3',        md: 'p-4',        lg: 'p-5'       }
const TITLE_SIZES = { sm: 'text-sm',    md: 'text-base',  lg: 'text-lg'   }
const DESC_SIZES  = { sm: 'text-xs',    md: 'text-sm',    lg: 'text-sm'   }

export function LoLEmptyState({
  icon: Icon = Inbox, title, description, action, size = 'md', className
}: LoLEmptyStateProps) {
  return (
    <div className={cn(
      'flex flex-col items-center justify-center gap-4 py-8 text-center',
      className
    )}>
      <div className={cn('rounded-xl bg-muted/40 border border-border/60', ICON_WRAP[size])}>
        <Icon className={cn('text-muted-foreground', ICON_SIZES[size])} />
      </div>
      <div className="space-y-1 max-w-xs">
        <p className={cn('font-medium', TITLE_SIZES[size])}>{title}</p>
        {description && (
          <p className={cn('text-muted-foreground', DESC_SIZES[size])}>{description}</p>
        )}
      </div>
      {action && <div>{action}</div>}
    </div>
  )
}
