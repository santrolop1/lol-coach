import { AlertTriangle, RefreshCw } from 'lucide-react'
import { cn } from '@/lib/utils'
import { Button } from '@/components/ui/button'

export interface LoLErrorStateProps {
  title?:       string
  message?:     string
  onRetry?:     () => void
  retryLabel?:  string
  className?:   string
  size?:        'sm' | 'md' | 'lg'
}

const ICON_SIZES  = { sm: 'h-6 w-6',  md: 'h-8 w-8',  lg: 'h-10 w-10' }
const TITLE_SIZES = { sm: 'text-sm',   md: 'text-base', lg: 'text-lg'   }
const DESC_SIZES  = { sm: 'text-xs',   md: 'text-sm',   lg: 'text-sm'   }

export function LoLErrorState({
  title = 'Error al cargar',
  message,
  onRetry,
  retryLabel = 'Reintentar',
  className,
  size = 'md'
}: LoLErrorStateProps) {
  return (
    <div className={cn(
      'flex flex-col items-center justify-center gap-4 py-8 text-center',
      className
    )}>
      <div className="rounded-xl bg-destructive/10 border border-destructive/20 p-4">
        <AlertTriangle className={cn('text-destructive', ICON_SIZES[size])} />
      </div>
      <div className="space-y-1 max-w-xs">
        <p className={cn('font-medium', TITLE_SIZES[size])}>{title}</p>
        {message && (
          <p className={cn('text-muted-foreground', DESC_SIZES[size])}>{message}</p>
        )}
      </div>
      {onRetry && (
        <Button variant="outline" size="sm" onClick={onRetry}>
          <RefreshCw className="h-3.5 w-3.5" />
          {retryLabel}
        </Button>
      )}
    </div>
  )
}
