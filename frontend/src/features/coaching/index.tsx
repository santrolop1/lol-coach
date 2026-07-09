import { useState } from 'react'
import { BookOpen, AlertTriangle, TrendingUp, Target, CheckCircle, ChevronRight } from 'lucide-react'
import { motion } from 'framer-motion'
import { Skeleton } from '@/components/ui/skeleton'
import { LoLSection } from '@/components/lol/LoLSection'
import { LoLEmptyState } from '@/components/lol/LoLEmptyState'
import { LoLErrorState } from '@/components/lol/LoLErrorState'
import { LoLHeroCard } from '@/components/lol/LoLHeroCard'
import { LoLMetricCard } from '@/components/lol/LoLMetricCard'
import { LoLPriorityCard } from '@/components/lol/LoLPriorityCard'
import { LoLScoreBadge } from '@/components/lol/LoLScoreBadge'
import { cn } from '@/lib/utils'
import { useCoaching } from './hooks/useCoaching'
import type { CoachingResponse } from './types'

// ── Skeleton ──────────────────────────────────────────────────────────────────

function CoachingSkeleton() {
  return (
    <div className="p-6 max-w-3xl space-y-6">
      <Skeleton className="h-10 w-56" />
      <Skeleton className="h-32 rounded-2xl" />
      <Skeleton className="h-28 rounded-xl" />
      <div className="grid grid-cols-3 gap-3">
        {[0, 1, 2].map((i) => <Skeleton key={i} className="h-20 rounded-lg" />)}
      </div>
      <Skeleton className="h-40 rounded-xl" />
    </div>
  )
}

// ── Session warning ────────────────────────────────────────────────────────────

function SessionWarning({ text }: { text: string }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: -8 }}
      animate={{ opacity: 1, y: 0 }}
      className="flex items-start gap-3 rounded-xl border border-orange-500/30 bg-orange-500/10 px-4 py-3"
    >
      <AlertTriangle className="h-4 w-4 text-orange-400 shrink-0 mt-0.5" />
      <p className="text-sm text-orange-300 leading-relaxed">{text}</p>
    </motion.div>
  )
}

// ── Score overview ─────────────────────────────────────────────────────────────

function ScoreOverview({ data }: { data: CoachingResponse }) {
  const sr = data.score_result
  if (!sr) return null

  const TREND_LABEL: Record<string, string> = {
    improving: 'Mejorando',
    declining: 'Bajando',
    stable:    'Estable',
  }

  return (
    <div className="flex items-center gap-5 rounded-xl border border-border/60 bg-card/60 p-5">
      <LoLScoreBadge score={sr.overall_score ?? 0} size="lg" />
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 flex-wrap">
          <span className="font-semibold text-lg">{data.player_name}</span>
          <span className="text-xs text-muted-foreground border border-border rounded px-1.5 py-0.5">
            {data.rank} {data.lp > 0 ? `· ${data.lp} LP` : ''}
          </span>
        </div>
        <p className="text-sm text-muted-foreground mt-0.5">
          {data.role} · {data.sample_size} partidas · {TREND_LABEL[sr.trend] ?? sr.trend}
        </p>
        {Object.keys(sr.dimensions).length > 0 && (
          <div className="flex gap-3 mt-2 flex-wrap">
            {Object.entries(sr.dimensions).map(([dim, score]) => (
              <span key={dim} className="text-xs text-muted-foreground">
                <span className="font-medium text-foreground">{score.toFixed(0)}</span> {dim}
              </span>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

// ── Primary problem ────────────────────────────────────────────────────────────

function PrimaryProblemCard({ cr }: { data: CoachingResponse; cr: NonNullable<CoachingResponse['coaching_result']> }) {
  const [expanded, setExpanded] = useState(false)

  if (!cr.primary_problem) return null

  return (
    <LoLHeroCard
      title={cr.primary_problem}
      subtitle={cr.evidence ?? undefined}
      icon={Target}
      accent="primary"
    >
      {cr.probable_cause && (
        <div className="space-y-2">
          <p className="text-sm text-muted-foreground leading-relaxed">{cr.probable_cause}</p>
          {cr.impact && (
            <button
              onClick={() => setExpanded((v) => !v)}
              className="flex items-center gap-1 text-xs text-primary/70 hover:text-primary transition-colors"
            >
              {expanded ? 'Menos' : 'Por qué importa'}
              <ChevronRight className={cn('h-3 w-3 transition-transform', expanded && 'rotate-90')} />
            </button>
          )}
          {expanded && cr.impact && (
            <motion.p
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: 'auto' }}
              className="text-xs text-muted-foreground leading-relaxed border-t border-border/40 pt-2"
            >
              {cr.impact}
            </motion.p>
          )}
        </div>
      )}
    </LoLHeroCard>
  )
}

// ── Weekly goal ────────────────────────────────────────────────────────────────

function WeeklyGoalCard({ goal }: { goal: NonNullable<CoachingResponse['coaching_result']>['weekly_goal'] }) {
  if (!goal) return null

  const pct = Math.min(100, Math.max(0,
    goal.current <= goal.target
      ? 100
      : Math.round((1 - (goal.current - goal.target) / Math.max(0.01, goal.current)) * 100)
  ))

  return (
    <div className="rounded-xl border border-primary/20 bg-primary/5 p-4 space-y-3">
      <div className="flex items-center gap-2">
        <TrendingUp className="h-4 w-4 text-primary" />
        <span className="text-xs font-semibold uppercase tracking-wider text-primary">
          Objetivo semanal
        </span>
        <span className="ml-auto text-xs text-muted-foreground">{goal.window}</span>
      </div>
      <p className="text-sm leading-relaxed">{goal.description}</p>
      <div className="space-y-1.5">
        <div className="flex justify-between text-xs text-muted-foreground">
          <span>Actual: <span className="font-mono font-medium text-foreground">{goal.current.toFixed(1)}</span></span>
          <span>Meta: <span className="font-mono font-medium text-primary">{goal.target.toFixed(1)}</span></span>
        </div>
        <div className="h-1.5 w-full rounded-full bg-muted/50">
          <div
            className="h-full rounded-full bg-primary transition-all duration-700"
            style={{ width: `${pct}%` }}
          />
        </div>
      </div>
    </div>
  )
}

// ── Training plan ──────────────────────────────────────────────────────────────

function TrainingPlanCard({ plan }: { plan: NonNullable<CoachingResponse['coaching_result']>['training_plan'] }) {
  if (!plan) return null

  return (
    <div className="rounded-xl border border-border/60 bg-card/40 p-4 space-y-3">
      <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
        Plan de práctica
      </p>
      <p className="text-sm leading-relaxed font-medium">{plan.primary}</p>
      {plan.secondary.length > 0 && (
        <ul className="space-y-2">
          {plan.secondary.map((tip, i) => (
            <li key={i} className="flex items-start gap-2 text-xs text-muted-foreground">
              <span className="mt-0.5 h-1.5 w-1.5 rounded-full bg-primary/50 shrink-0" />
              <span className="leading-relaxed">{tip}</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}

// ── Metrics grid ───────────────────────────────────────────────────────────────

function MetricsGrid({ metrics }: { metrics: CoachingResponse['metrics'] }) {
  if (!metrics) return null

  const fmt = (v: number | null, dec = 1) => v != null ? v.toFixed(dec) : '—'

  const items = [
    { label: 'CS/min',     value: fmt(metrics.cs_pm),      sublabel: `${metrics.n_wins}V / ${metrics.n_losses}D` },
    { label: 'Muertes',    value: fmt(metrics.deaths, 1),   sublabel: `${fmt(metrics.deaths_win)}V · ${fmt(metrics.deaths_loss)}D` },
    { label: 'KP',         value: metrics.kp != null ? `${(metrics.kp * 100).toFixed(0)}%` : '—', sublabel: `${metrics.kp_win != null ? (metrics.kp_win * 100).toFixed(0) : '—'}%V · ${metrics.kp_loss != null ? (metrics.kp_loss * 100).toFixed(0) : '—'}%D` },
    { label: 'Daño/min',   value: fmt(metrics.dmg_pm, 0),   sublabel: undefined },
    { label: 'Oro/min',    value: fmt(metrics.gold_pm, 0),  sublabel: undefined },
    { label: 'Visión/min', value: fmt(metrics.vision_pm),   sublabel: undefined },
  ]

  return (
    <div className="grid grid-cols-3 gap-2 sm:grid-cols-6">
      {items.map((m) => (
        <LoLMetricCard
          key={m.label}
          label={m.label}
          value={m.value}
          sublabel={m.sublabel}
          size="sm"
        />
      ))}
    </div>
  )
}

// ── Strengths ──────────────────────────────────────────────────────────────────

function StrengthsList({ strengths }: { strengths: CoachingResponse['coaching_result'] extends null ? never : NonNullable<CoachingResponse['coaching_result']>['strengths'] }) {
  if (!strengths?.length) return null

  return (
    <div className="space-y-2">
      {strengths.map((s, i) => (
        <div key={i} className="flex items-start gap-2.5 rounded-lg border border-emerald-500/20 bg-emerald-500/5 px-3 py-2.5">
          <CheckCircle className="h-3.5 w-3.5 text-emerald-400 mt-0.5 shrink-0" />
          <div>
            <p className="text-sm font-medium text-emerald-300">{s.name}</p>
            <p className="text-xs text-muted-foreground mt-0.5">{s.evidence}</p>
          </div>
        </div>
      ))}
    </div>
  )
}

// ── Trend summary ──────────────────────────────────────────────────────────────

function TrendSummary({ text }: { text: string }) {
  return (
    <div className="rounded-lg border border-border/40 bg-muted/20 px-4 py-3">
      <p className="text-xs leading-relaxed text-muted-foreground">{text}</p>
    </div>
  )
}

// ── Role selector ──────────────────────────────────────────────────────────────

function RoleSelector({ role, onChange }: { role: 'ADC' | 'TOP'; onChange: (r: 'ADC' | 'TOP') => void }) {
  return (
    <div className="flex gap-1 rounded-lg border border-border/60 bg-muted/20 p-1">
      {(['ADC', 'TOP'] as const).map((r) => (
        <button
          key={r}
          onClick={() => onChange(r)}
          className={cn(
            'rounded px-3 py-1 text-xs font-semibold transition-colors',
            role === r
              ? 'bg-primary text-primary-foreground'
              : 'text-muted-foreground hover:text-foreground'
          )}
        >
          {r}
        </button>
      ))}
    </div>
  )
}

// ── Page ───────────────────────────────────────────────────────────────────────

export default function CoachingPage() {
  const [role, setRole] = useState<'ADC' | 'TOP'>('ADC')
  const { data, isLoading, isError, refetch } = useCoaching(role)

  if (isLoading) return <CoachingSkeleton />

  if (isError) {
    return (
      <div className="flex h-full items-center justify-center p-6">
        <LoLErrorState title="Error al cargar el Coaching" onRetry={() => refetch()} size="lg" />
      </div>
    )
  }

  if (!data?.has_data) {
    return (
      <div className="flex h-full items-center justify-center p-6">
        <LoLEmptyState
          icon={BookOpen}
          title="Sin datos suficientes"
          description="El Coaching Engine necesita historial de partidas para generar recomendaciones."
          size="lg"
        />
      </div>
    )
  }

  const cr = data.coaching_result

  return (
    <div className="h-full overflow-y-auto">
      <div className="mx-auto max-w-3xl space-y-6 p-6">

        {/* Header */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <BookOpen className="h-5 w-5 text-primary" />
            <h1 className="text-xl font-bold">Coaching</h1>
          </div>
          <RoleSelector role={role} onChange={setRole} />
        </div>

        {/* Score + player */}
        <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }}>
          <ScoreOverview data={data} />
        </motion.div>

        {/* Session warning */}
        {cr?.session_warning && (
          <SessionWarning text={cr.session_warning} />
        )}

        {/* Métricas clave */}
        {data.metrics && (
          <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.05 }}>
            <MetricsGrid metrics={data.metrics} />
          </motion.div>
        )}

        {/* Problema principal */}
        {cr && cr.primary_problem && (
          <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }}>
            <PrimaryProblemCard data={data} cr={cr} />
          </motion.div>
        )}

        {/* Objetivo semanal */}
        {cr?.weekly_goal && (
          <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.15 }}>
            <WeeklyGoalCard goal={cr.weekly_goal} />
          </motion.div>
        )}

        {/* Plan de práctica */}
        {cr?.training_plan && (
          <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.2 }}>
            <TrainingPlanCard plan={cr.training_plan} />
          </motion.div>
        )}

        {/* Prioridades */}
        {data.priorities.length > 0 && (
          <LoLSection
            title="Prioridades de mejora"
            subtitle="Ordenadas por impacto estimado en tu winrate"
          >
            <div className="space-y-3">
              {data.priorities.map((p, i) => (
                <motion.div
                  key={p.metric_key}
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.25 + i * 0.06 }}
                >
                  <LoLPriorityCard
                    title={p.title}
                    evidence={p.evidence}
                    recommendation={p.recommendation}
                    impactScore={Math.min(100, p.impact_score * 20)}
                    currentValue={p.current_value}
                    targetValue={p.target_value}
                    unit={p.unit}
                  />
                </motion.div>
              ))}
            </div>
          </LoLSection>
        )}

        {/* Fortalezas */}
        {cr?.strengths && cr.strengths.length > 0 && (
          <LoLSection title="Fortalezas detectadas">
            <StrengthsList strengths={cr.strengths} />
          </LoLSection>
        )}

        {/* Tendencia */}
        {cr?.trend_summary && (
          <LoLSection title="Análisis de tendencia">
            <TrendSummary text={cr.trend_summary} />
          </LoLSection>
        )}

      </div>
    </div>
  )
}
