import { motion } from 'framer-motion'
import { TrendingUp, TrendingDown, Minus, RefreshCw, AlertCircle } from 'lucide-react'
import { useDashboard } from '@/api/queries/dashboard'
import { Skeleton } from '@/components/ui/skeleton'
import { Badge }    from '@/components/ui/badge'
import { Button }   from '@/components/ui/button'
import { cn, formatScore, formatPercent, scoreToBg } from '@/lib/utils'
import type { RoleSummary } from '@/api/types'

const FADE_UP = {
  hidden:  { opacity: 0, y: 12 },
  visible: (i: number) => ({ opacity: 1, y: 0, transition: { delay: i * 0.08, duration: 0.3 } })
}

export default function DashboardPage() {
  const { data, isLoading, isError, refetch } = useDashboard()

  if (isLoading) return <DashboardSkeleton />
  if (isError)   return <DashboardError onRetry={refetch} />

  const adc = data?.roles?.ADC
  const top = data?.roles?.TOP

  return (
    <div className="p-6 space-y-6">
      {/* Hero: jugador */}
      <motion.div
        variants={FADE_UP}
        initial="hidden"
        animate="visible"
        custom={0}
        className="flex items-end justify-between"
      >
        <div>
          <p className="text-xs font-medium uppercase tracking-widest text-muted-foreground mb-1">
            Invocador
          </p>
          <h2 className="text-2xl font-bold">{data?.player_name ?? '—'}</h2>
          <div className="flex items-center gap-2 mt-1">
            {data?.rank && <Badge variant="secondary">{data.rank}</Badge>}
            {data?.lp != null && (
              <span className="text-sm text-muted-foreground">{data.lp} LP</span>
            )}
            <span className="text-xs text-muted-foreground">{data?.sync_label ?? ''}</span>
          </div>
        </div>
        <Button variant="ghost" size="icon" onClick={() => refetch()} className="h-8 w-8">
          <RefreshCw className="h-4 w-4 text-muted-foreground" />
        </Button>
      </motion.div>

      {/* Cards por rol */}
      <div className="grid grid-cols-2 gap-4">
        {[
          { role: 'ADC', data: adc },
          { role: 'TOP', data: top }
        ].map(({ role, data: roleData }, i) => (
          <motion.div
            key={role}
            variants={FADE_UP}
            initial="hidden"
            animate="visible"
            custom={i + 1}
          >
            <RoleCard role={role} data={roleData} />
          </motion.div>
        ))}
      </div>

      {/* Placeholder de contenido futuro */}
      <motion.div
        variants={FADE_UP}
        initial="hidden"
        animate="visible"
        custom={3}
        className="surface p-4 text-center text-sm text-muted-foreground"
      >
        Las pantallas de Coaching, Partidas y Draft se integran en E-4.
      </motion.div>
    </div>
  )
}

function RoleCard({ role, data }: { role: string; data?: RoleSummary }) {
  const hasData = data?.has_data !== false && data != null

  return (
    <div className="surface p-5 space-y-4">
      <div className="flex items-center justify-between">
        <span className="text-xs font-semibold uppercase tracking-widest text-muted-foreground">
          {role}
        </span>
        {hasData && data.confidence_level && (
          <Badge variant="outline" className="text-xs">{data.confidence_level}</Badge>
        )}
      </div>

      {!hasData ? (
        <div className="py-4 text-center text-sm text-muted-foreground">
          Sin datos suficientes
        </div>
      ) : (
        <>
          {/* Score principal */}
          <div className="flex items-end gap-3">
            <span className={cn('text-4xl font-bold tabular-nums', scoreToBg(data.overall_score ?? 0).split(' ')[0].replace('bg-', 'text-'))}>
              {formatScore(data.overall_score)}
            </span>
            <div className="pb-1">
              <TrendIcon trend={data.trend} />
            </div>
          </div>

          {/* Métricas */}
          <div className="grid grid-cols-2 gap-2 text-xs">
            <Metric label="Winrate"     value={formatPercent(data.winrate)} />
            <Metric label="Partidas"    value={String(data.sample_size ?? 0)} />
            <Metric label="Prioridad"   value={data.top_priority ?? '—'} wide />
          </div>

          {/* Problema principal */}
          {data.primary_problem && (
            <div className="rounded-md bg-secondary/50 px-3 py-2 text-xs text-muted-foreground">
              {data.primary_problem}
            </div>
          )}
        </>
      )}
    </div>
  )
}

function Metric({ label, value, wide }: { label: string; value: string; wide?: boolean }) {
  return (
    <div className={cn('space-y-0.5', wide && 'col-span-2')}>
      <p className="text-muted-foreground/70">{label}</p>
      <p className="font-medium text-foreground truncate">{value}</p>
    </div>
  )
}

function TrendIcon({ trend }: { trend?: string }) {
  if (!trend) return null
  if (trend === 'improving') return <TrendingUp  className="h-4 w-4 text-emerald-400" />
  if (trend === 'declining') return <TrendingDown className="h-4 w-4 text-red-400" />
  return <Minus className="h-4 w-4 text-muted-foreground" />
}

function DashboardSkeleton() {
  return (
    <div className="p-6 space-y-6">
      <div className="space-y-2">
        <Skeleton className="h-3 w-20" />
        <Skeleton className="h-8 w-48" />
        <Skeleton className="h-4 w-32" />
      </div>
      <div className="grid grid-cols-2 gap-4">
        {[0, 1].map((i) => (
          <div key={i} className="surface p-5 space-y-4">
            <Skeleton className="h-3 w-12" />
            <Skeleton className="h-10 w-20" />
            <div className="grid grid-cols-2 gap-2">
              {[0,1,2,3].map(j => <Skeleton key={j} className="h-8" />)}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

function DashboardError({ onRetry }: { onRetry: () => void }) {
  return (
    <div className="flex h-full flex-col items-center justify-center gap-4 p-8">
      <AlertCircle className="h-8 w-8 text-destructive" />
      <p className="text-sm text-muted-foreground">Error al cargar el dashboard</p>
      <Button variant="outline" size="sm" onClick={onRetry}>
        <RefreshCw className="h-4 w-4" /> Reintentar
      </Button>
    </div>
  )
}
