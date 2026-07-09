import { AlertTriangle, Target } from 'lucide-react'
import { motion } from 'framer-motion'
import { LoLScoreRing, LoLGradeBadge } from '@/components/lol/LoLScoreBadge'
import { LoLCard } from '@/components/lol/LoLCard'
import { LoLEmptyState } from '@/components/lol/LoLEmptyState'
import {
  getGrade, formatTrend, getTrendColor, formatConfidence,
  formatProblem, formatPercent
} from '@/features/shared/utils/formatters'
import type { RoleSummary, Role } from '@/features/shared/types/api'

// ── Subcomponents ──────────────────────────────────────────────────────────────

function MetricPill({ label, value, accent = false }: { label: string; value: string; accent?: boolean }) {
  return (
    <div className={`flex flex-col items-center rounded-lg px-3 py-2
      ${accent ? 'bg-primary/10 border border-primary/20' : 'bg-muted/30 border border-border/50'}`}
    >
      <span className="text-[10px] font-medium uppercase tracking-widest text-muted-foreground">{label}</span>
      <span className={`mt-0.5 text-sm font-bold tabular-nums ${accent ? 'text-primary' : ''}`}>{value}</span>
    </div>
  )
}

function ProblemChip({ problem }: { problem: string }) {
  return (
    <div className="flex items-center gap-2 rounded-lg bg-destructive/10 border border-destructive/20 px-3 py-2">
      <AlertTriangle className="h-3.5 w-3.5 shrink-0 text-destructive" />
      <span className="text-xs font-medium text-destructive/90">{problem}</span>
    </div>
  )
}

function PriorityRow({ priority }: { priority: string }) {
  return (
    <div className="flex items-start gap-2 rounded-lg bg-muted/20 border border-border/40 px-3 py-2">
      <Target className="mt-0.5 h-3.5 w-3.5 shrink-0 text-primary" />
      <span className="text-xs text-muted-foreground leading-relaxed">{priority}</span>
    </div>
  )
}

// ── No data state ──────────────────────────────────────────────────────────────

function NoDataCard({ role }: { role: Role }) {
  return (
    <LoLCard variant="default" padding="md" className="flex flex-col">
      <div className="mb-3 flex items-center justify-between">
        <span className="text-xs font-semibold uppercase tracking-widest text-muted-foreground">{role}</span>
      </div>
      <LoLEmptyState
        title="Sin datos suficientes"
        description="Juega al menos 5 partidas en este rol para ver tu análisis."
        size="sm"
        className="flex-1 py-6"
      />
    </LoLCard>
  )
}

// ── Main card ──────────────────────────────────────────────────────────────────

interface RoleOverviewCardProps {
  role:  Role
  data:  RoleSummary
  delay?: number
}

export function RoleOverviewCard({ role, data, delay = 0 }: RoleOverviewCardProps) {
  const hasData = data.has_data !== false && data.overall_score != null

  if (!hasData) return <NoDataCard role={role} />

  const score     = data.overall_score!
  const grade     = getGrade(score)
  const trend     = formatTrend(data.trend)
  const trendClr  = getTrendColor(data.trend)
  const confidence = formatConfidence(data.confidence_level)
  const problem   = formatProblem(data.primary_problem)
  const winrate   = formatPercent(data.winrate)
  const games     = data.sample_size ?? 0

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, ease: 'easeOut', delay }}
    >
      <LoLCard variant="default" padding="none" className="overflow-hidden">
        {/* Role header */}
        <div className="flex items-center justify-between border-b border-border px-5 py-3">
          <span className="text-xs font-bold uppercase tracking-widest text-muted-foreground">{role}</span>
          <span className={`text-xs font-medium ${trendClr}`}>{trend}</span>
        </div>

        <div className="p-5 space-y-4">
          {/* Score section */}
          <div className="flex items-center gap-4">
            <LoLScoreRing score={score} size="md" />
            <div className="space-y-1.5">
              <div className="flex items-center gap-2">
                <LoLGradeBadge grade={grade} size="md" />
                <span className="text-sm font-medium text-muted-foreground">
                  {grade === 'S' ? 'Excelente' :
                   grade === 'A' ? 'Muy bueno' :
                   grade === 'B' ? 'Bueno'     :
                   grade === 'C' ? 'Regular'   : 'Por mejorar'}
                </span>
              </div>
              <p className="text-xs text-muted-foreground/60">{confidence}</p>
            </div>
          </div>

          {/* Metrics row */}
          <div className="grid grid-cols-3 gap-2">
            <MetricPill label="Winrate"  value={winrate} accent={data.winrate != null && data.winrate >= 50} />
            <MetricPill label="Partidas" value={String(games)} />
            <MetricPill label="Confianza" value={
              data.confidence_level === 'reliable'     ? 'Alta'  :
              data.confidence_level === 'low_sample'   ? 'Media' : 'Baja'
            } />
          </div>

          {/* Problem */}
          {problem && <ProblemChip problem={problem} />}

          {/* Priority */}
          {data.top_priority && <PriorityRow priority={data.top_priority} />}
        </div>
      </LoLCard>
    </motion.div>
  )
}
