import { TrendingUp, TrendingDown, Minus, Star } from 'lucide-react'
import { motion } from 'framer-motion'
import { LoLInsightCard } from '@/components/lol/LoLInsightCard'
import type { DashboardResponse, Role } from '@/features/shared/types/api'

interface QuickInsightsProps {
  data: DashboardResponse
}

function getBestRole(data: DashboardResponse): Role | null {
  let best: Role | null = null
  let bestScore = -1

  for (const [role, summary] of Object.entries(data.roles) as [Role, typeof data.roles[Role]][]) {
    const score = summary?.overall_score ?? -1
    if (score > bestScore) {
      bestScore = score
      best = role
    }
  }
  return best
}

function getTotalGames(data: DashboardResponse): number {
  return Object.values(data.roles).reduce(
    (acc, s) => acc + (s?.sample_size ?? 0), 0
  )
}

function getOverallTrend(data: DashboardResponse): 'improving' | 'declining' | 'stable' | null {
  const trends = Object.values(data.roles)
    .map((s) => s?.trend)
    .filter(Boolean) as string[]

  if (trends.length === 0) return null
  const improving = trends.filter((t) => t === 'improving').length
  const declining = trends.filter((t) => t === 'declining').length
  if (improving > declining) return 'improving'
  if (declining > improving) return 'declining'
  return 'stable'
}

export function QuickInsights({ data }: QuickInsightsProps) {
  const bestRole    = getBestRole(data)
  const totalGames  = getTotalGames(data)
  const overallTrend = getOverallTrend(data)

  if (totalGames === 0) return null

  const bestScore = bestRole ? (data.roles[bestRole]?.overall_score ?? null) : null
  const insights: React.ReactNode[] = []

  if (bestRole && bestScore != null) {
    insights.push(
      <LoLInsightCard
        key="best"
        icon={Star}
        variant="tip"
        title={`Mejor rol: ${bestRole} (${bestScore.toFixed(0)}/100)`}
        body="Este es tu desempeño más destacado. Mantén el foco aquí para subir elo."
      />
    )
  }

  if (overallTrend === 'improving') {
    insights.push(
      <LoLInsightCard
        key="trend"
        icon={TrendingUp}
        variant="success"
        title="Tendencia positiva"
        body="Tu rendimiento está mejorando. Continúa con la misma dinámica."
      />
    )
  } else if (overallTrend === 'declining') {
    insights.push(
      <LoLInsightCard
        key="trend"
        icon={TrendingDown}
        variant="warning"
        title="Tendencia a la baja"
        body="Tu rendimiento ha bajado recientemente. Revisa la sección de coaching para identificar el problema."
      />
    )
  } else if (overallTrend === 'stable') {
    insights.push(
      <LoLInsightCard
        key="trend"
        icon={Minus}
        variant="info"
        title={`${totalGames} partidas analizadas · Tendencia estable`}
        body="Estás en una fase consistente. Trabaja la prioridad marcada para dar el siguiente salto."
      />
    )
  }

  if (insights.length === 0) return null

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.3, delay: 0.4 }}
      className="space-y-2"
    >
      {insights}
    </motion.div>
  )
}
