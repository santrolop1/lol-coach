import { cn } from '@/lib/utils'

type MetricTrend = 'up' | 'down' | 'neutral'

export interface LoLMetricCardProps {
  label:       string
  value:       string | number
  sublabel?:   string
  trend?:      MetricTrend
  trendLabel?: string
  size?:       'sm' | 'md' | 'lg'
  accent?:     boolean
  className?:  string
}

const TREND_ICONS: Record<MetricTrend, string>   = { up: '↑', down: '↓', neutral: '→' }
const TREND_COLORS: Record<MetricTrend, string>  = {
  up:      'text-emerald-400',
  down:    'text-red-400',
  neutral: 'text-muted-foreground'
}

const VALUE_SIZES = { sm: 'text-lg', md: 'text-2xl', lg: 'text-3xl' }
const LABEL_SIZES = { sm: 'text-xs', md: 'text-xs',  lg: 'text-sm'  }

export function LoLMetricCard({
  label, value, sublabel, trend, trendLabel, size = 'md', accent = false, className
}: LoLMetricCardProps) {
  return (
    <div className={cn(
      'flex flex-col gap-1 rounded-lg px-3 py-2.5',
      accent ? 'bg-primary/10 border border-primary/20' : 'bg-muted/30 border border-border/60',
      className
    )}>
      <span className={cn('font-medium text-muted-foreground uppercase tracking-wider', LABEL_SIZES[size])}>
        {label}
      </span>

      <div className="flex items-baseline gap-1.5">
        <span className={cn('font-bold tabular-nums', VALUE_SIZES[size], accent && 'text-primary')}>
          {value}
        </span>
        {trend && (
          <span className={cn('text-xs font-medium', TREND_COLORS[trend])}>
            {TREND_ICONS[trend]}{trendLabel ? ` ${trendLabel}` : ''}
          </span>
        )}
      </div>

      {sublabel && (
        <span className="text-xs text-muted-foreground/70 leading-tight">{sublabel}</span>
      )}
    </div>
  )
}
