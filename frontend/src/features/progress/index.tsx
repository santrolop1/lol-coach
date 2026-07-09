import { BarChart3 } from 'lucide-react'
import { Skeleton } from '@/components/ui/skeleton'
import { LoLSection } from '@/components/lol/LoLSection'
import { LoLEmptyState } from '@/components/lol/LoLEmptyState'
import { LoLErrorState } from '@/components/lol/LoLErrorState'
import { ProgressHero } from './components/ProgressHero'
import { ProgressTimeline } from './components/ProgressTimeline'
import { GoalCard } from './components/GoalCard'
import { HabitCard } from './components/HabitCard'
import { TrendInsightCard } from './components/TrendInsightCard'
import { RecommendationCard } from './components/RecommendationCard'
import { useProgress } from './hooks/useProgress'

function ProgressSkeleton() {
  return (
    <div className="p-6 max-w-3xl space-y-6">
      <Skeleton className="h-36 rounded-2xl" />
      <Skeleton className="h-24 rounded-xl" />
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <Skeleton className="h-48 rounded-xl" />
        <Skeleton className="h-48 rounded-xl" />
      </div>
      <Skeleton className="h-32 rounded-xl" />
    </div>
  )
}

export default function ProgressPage() {
  const { data, isLoading, isError, refetch } = useProgress()

  if (isLoading) return <ProgressSkeleton />

  if (isError) {
    return (
      <div className="flex h-full items-center justify-center p-6">
        <LoLErrorState
          title="Error al cargar el progreso"
          message="No se pudo conectar con el backend."
          onRetry={() => refetch()}
          size="lg"
        />
      </div>
    )
  }

  if (!data?.has_data) {
    return (
      <div className="flex h-full items-center justify-center p-6">
        <LoLEmptyState
          icon={BarChart3}
          title={data?.games_needed_msg ?? 'Sin datos suficientes'}
          description={`Necesitas al menos ${data?.min_games_needed ?? 10} partidas del mismo rol para ver tu progreso de coaching.`}
          size="lg"
        />
      </div>
    )
  }

  const hasInsights  = data.improving.length + data.declining.length + data.stable.length > 0
  const hasHabits    = data.habits.length > 0
  const hasRecs      = data.recommendations.length > 0
  const hasChampions = data.champion_insights.length > 0

  return (
    <div className="h-full overflow-y-auto">
      <div className="mx-auto max-w-3xl space-y-6 p-6">

        {/* Hero — responde "¿Estoy mejorando?" */}
        <ProgressHero data={data} />

        {/* Timeline — "¿Cómo ha evolucionado?" */}
        {data.timeline.length >= 2 && (
          <LoLSection
            title="Evolución histórica"
            subtitle="Puntuación media por período · Oldest → Hoy"
          >
            <ProgressTimeline points={data.timeline} />
          </LoLSection>
        )}

        {/* Objetivo semanal — "¿Qué debo entrenar?" */}
        {data.weekly_goal && (
          <GoalCard goal={data.weekly_goal} />
        )}

        {/* Insights — "¿En qué estoy mejorando / empeorando?" */}
        {hasInsights && (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* Mejoras */}
            {data.improving.length > 0 && (
              <LoLSection title="Lo que mejoró">
                <div className="space-y-2">
                  {data.improving.map((ins, i) => (
                    <TrendInsightCard key={ins.dim_name + i} insight={ins} delay={i * 0.06} />
                  ))}
                </div>
              </LoLSection>
            )}

            {/* Retrocesos */}
            {data.declining.length > 0 && (
              <LoLSection title="Lo que empeoró">
                <div className="space-y-2">
                  {data.declining.map((ins, i) => (
                    <TrendInsightCard key={ins.dim_name + i} insight={ins} delay={i * 0.06} />
                  ))}
                </div>
              </LoLSection>
            )}

            {/* Estable */}
            {data.stable.length > 0 && (
              <LoLSection title="Estable">
                <div className="space-y-2">
                  {data.stable.map((ins, i) => (
                    <TrendInsightCard key={ins.dim_name + i} insight={ins} delay={i * 0.05} />
                  ))}
                </div>
              </LoLSection>
            )}
          </div>
        )}

        {/* Hábitos */}
        {hasHabits && (
          <LoLSection
            title="Patrones detectados"
            subtitle={`${data.habits.length} patrón${data.habits.length !== 1 ? 'es' : ''} en tus últimas 10 partidas`}
          >
            <div className="space-y-2">
              {data.habits.map((h, i) => (
                <HabitCard key={h.title + i} habit={h} delay={i * 0.05} />
              ))}
            </div>
          </LoLSection>
        )}

        {/* Análisis por campeón */}
        {hasChampions && (
          <LoLSection title="Rendimiento por campeón">
            <div className="grid grid-cols-1 gap-1.5">
              {data.champion_insights.map((c, i) => {
                const delta      = c.vs_overall
                const deltaColor = delta >= 5 ? 'text-emerald-400' : delta <= -5 ? 'text-red-400' : 'text-muted-foreground'
                const hue        = c.champion.split('').reduce((a, ch) => a + ch.charCodeAt(0), 0) % 360
                return (
                  <div key={c.champion + i} className="flex items-center gap-3 rounded-lg border bg-card/60 px-3 py-2.5">
                    <div
                      className="h-7 w-7 shrink-0 rounded-md flex items-center justify-center text-xs font-bold text-white"
                      style={{ backgroundColor: `hsl(${hue} 50% 35%)` }}
                    >
                      {c.champion.slice(0, 2).toUpperCase()}
                    </div>
                    <div className="flex-1 min-w-0">
                      <span className="text-sm font-medium">{c.champion}</span>
                      <span className="ml-2 text-xs text-muted-foreground">{c.games} partidas</span>
                    </div>
                    <div className="text-right">
                      <p className="text-sm font-bold tabular-nums">{c.avg_score.toFixed(0)}</p>
                      <p className={`text-xs tabular-nums ${deltaColor}`}>
                        {delta >= 0 ? '+' : ''}{delta.toFixed(0)} vs media
                      </p>
                    </div>
                  </div>
                )
              })}
            </div>
          </LoLSection>
        )}

        {/* Recomendaciones */}
        {hasRecs && (
          <LoLSection
            title="Qué entrenar ahora"
            subtitle="Ordenado por impacto esperado en tu winrate"
          >
            <div className="space-y-3">
              {data.recommendations.map((rec, i) => (
                <RecommendationCard key={rec.rank} rec={rec} delay={i * 0.08} />
              ))}
            </div>
          </LoLSection>
        )}

      </div>
    </div>
  )
}
