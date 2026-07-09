import { forwardRef } from 'react'
import { cva, type VariantProps } from 'class-variance-authority'
import { cn } from '@/lib/utils'

const cardVariants = cva('rounded-xl border transition-all duration-200', {
  variants: {
    variant: {
      default:   'bg-card border-border',
      elevated:  'bg-card border-border shadow-xl shadow-black/30',
      highlight: 'bg-card border-primary/40 shadow-lg shadow-primary/5',
      glass:     'bg-card/60 border-border/50 backdrop-blur-md',
      ghost:     'bg-transparent border-transparent',
      inset:     'bg-background/40 border-border/60'
    },
    padding: {
      none: '',
      xs:   'p-3',
      sm:   'p-4',
      md:   'p-5',
      lg:   'p-6',
      xl:   'p-8'
    },
    interactive: {
      true:  'cursor-pointer hover:border-primary/30 hover:bg-card/80',
      false: ''
    }
  },
  defaultVariants: { variant: 'default', padding: 'md', interactive: false }
})

export interface LoLCardProps
  extends React.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof cardVariants> {}

export const LoLCard = forwardRef<HTMLDivElement, LoLCardProps>(
  ({ className, variant, padding, interactive, ...props }, ref) => (
    <div
      ref={ref}
      className={cn(cardVariants({ variant, padding, interactive }), className)}
      {...props}
    />
  )
)
LoLCard.displayName = 'LoLCard'
