import { motion } from 'framer-motion'
import { TrendingUp, TrendingDown, Minus, Shield } from 'lucide-react'
import { LoLTrendChart } from '@/components/lol/LoLTrendChart'
import { cn } from '@/lib/utils'
import type { ProgressResponse } from '@/features/progress/types'

const TREND_CONFIG = {
  improving:  { icon: TrendingUp,   color: 'text-emerald-400', bg: 'bg-emerald-500/10 border-emerald-500/25', glow: 'bg-emerald-400/8' },
  declining:  { icon: TrendingDown, color: 'text-red-400',     bg: 'bg-red-500/10     border-red-500/25',     glow: 'bg-red-400/8'     },
  stable:     { icon: Minus,        color: 'text-blue-400',    bg: 'bg-blue-500/10    border-blue-500/25',    glow: 'bg-blue-400/8'    },
}

const CONF_LABELS: Record<string, string> = {
  reliable:     'Análisis fiable',
  preliminary:  'Análisis preliminar',
  insufficient: 'Muestra reducida',
}

interface ProgressHeroProps {
  data: ProgressResponse
}

export function ProgressHero({ data }: ProgressHeroProps) {
  const cfg   = TREND_CONFIG[data.overall_trend] ?? TREND_CONFIG.stable
  const Icon  = cfg.icon
  const delta = data.overall_delta

  return (
    <motion.div
      initial={{ opacity: 0, y: -10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4 }}
      className="relative overflow-hidden rounded-2xl border border-border bg-card p-6"
    >
      {/* Ambient glow */}
      <div className={cn('pointer-events-none absolute -right-10 -top-10 h-40 w-40 rounded-full blur-3xl', cfg.glow)} />

      <div className="relative flex flex-col gap-5 sm:flex-row sm:items-center sm:gap-8">
        {/* Left: status */}
        <div className="flex-1 space-y-3">
          <div className="flex items-center gap-2.5">
            <span className={cn('inline-flex items-center gap-1.5 rounded-full border px-3 py-1 text-xs font-semibold', cfg.bg, cfg.color)}>
              <Icon className="h-3.5 w-3.5" />
              {data.overall_trend_label}
            </span>
            <span className="text-xs text-muted-foreground">
              {CONF_LABELS[data.confidence] ?? data.confidence}
            </span>
          </div>

          <div>
            <h1 className="text-2xl font-bold leading-tight">
              {data.overall_trend === 'improving'
                ? 'Estás mejorando'
                : data.overall_trend === 'declining'
                ? 'Hay margen de mejora'
                : 'Rendimiento estable'}
            </h1>
            <p className="mt-1 text-sm text-muted-foreground">
              Últimas {Math.min(data.total_matches, 10)} partidas de {data.role}
              {data.avg_recent != null && ` · ${data.avg_recent.toFixed(0)}/100 de promedio`}
            </p>
          </div>

          {/* Delta badge */}
          {delta != null && (
            <div className="flex items-center gap-2">
              <span className={cn(
                'text-sm font-semibold tabular-nums',
                delta >= 0 ? 'text-emerald-400' : 'text-red-400'
              )}>
                {delta >= 0 ? '+' : ''}{delta.toFixed(0)} puntos
              </span>
              <span className="text-xs text-muted-foreground">vs las 10–30 anteriores</span>
            </div>
          )}
        </div>

        {/* Right: sparkline */}
        {data.score_series.length >= 3 && (
          <div className="shrink-0 flex flex-col items-end gap-1.5">
            <LoLTrendChart
              data={data.score_series}
              width={160}
              height={56}
              showDots={false}
            />
            <div className="flex items-center gap-2 text-xs text-muted-foreground">
              <Shield className="h-3 w-3" />
              <span>{data.total_matches} partidas analizadas</span>
            </div>
          </div>
        )}
      </div>
    </motion.div>
  )
}
