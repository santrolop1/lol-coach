import { Loader2 } from 'lucide-react'
import { cn } from '@/lib/utils'

export interface LoLLoadingStateProps {
  label?:     string
  size?:      'sm' | 'md' | 'lg'
  className?: string
  fullHeight?: boolean
}

const ICON_SIZES  = { sm: 'h-4 w-4', md: 'h-6 w-6', lg: 'h-8 w-8' }
const LABEL_SIZES = { sm: 'text-xs',  md: 'text-sm',  lg: 'text-base' }

export function LoLLoadingState({ label, size = 'md', className, fullHeight = false }: LoLLoadingStateProps) {
  return (
    <div className={cn(
      'flex flex-col items-center justify-center gap-3 text-muted-foreground',
      fullHeight && 'h-full min-h-[200px]',
      className
    )}>
      <Loader2 className={cn('animate-spin', ICON_SIZES[size])} />
      {label && (
        <span className={cn(LABEL_SIZES[size])}>{label}</span>
      )}
    </div>
  )
}
