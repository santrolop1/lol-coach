import { Brain, BookOpen } from 'lucide-react'
import { Skeleton } from '@/components/ui/skeleton'
import { LoLSection } from '@/components/lol/LoLSection'
import { LoLEmptyState } from '@/components/lol/LoLEmptyState'
import { LoLErrorState } from '@/components/lol/LoLErrorState'
import { SessionSummary } from './components/SessionSummary'
import { AdaptiveGoalCard } from './components/AdaptiveGoalCard'
import { PatternCard } from './components/PatternCard'
import { InsightCard } from './components/InsightCard'
import { KnowledgeRecommendationCard } from './components/KnowledgeRecommendationCard'
import { MemoryTimeline } from './components/MemoryTimeline'
import { useKnowledge } from './hooks/useKnowledge'

function KnowledgeSkeleton() {
  return (
    <div className="p-6 max-w-3xl space-y-6">
      <Skeleton className="h-10 w-56" />
      <Skeleton className="h-48 rounded-2xl" />
      <Skeleton className="h-32 rounded-2xl" />
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        {[0, 1].map((i) => <Skeleton key={i} className="h-40 rounded-xl" />)}
      </div>
      <Skeleton className="h-28 rounded-xl" />
    </div>
  )
}

export default function KnowledgePage() {
  const { data, isLoading, isError, refetch } = useKnowledge()

  if (isLoading) return <KnowledgeSkeleton />

  if (isError) {
    return (
      <div className="flex h-full items-center justify-center p-6">
        <LoLErrorState title="Error al cargar el Coach" onRetry={() => refetch()} size="lg" />
      </div>
    )
  }

  if (!data?.has_data) {
    return (
      <div className="flex h-full items-center justify-center p-6">
        <LoLEmptyState
          icon={Brain}
          title={data?.games_needed_msg ?? 'Sin datos suficientes'}
          description="El Knowledge Engine necesita historial de partidas para analizar tu evolución."
          size="lg"
        />
      </div>
    )
  }

  const confLabel: Record<string, string> = {
    reliable: 'Análisis fiable',
    preliminary: 'Análisis preliminar',
    insufficient: 'Muestra reducida',
  }

  return (
    <div className="h-full overflow-y-auto">
      <div className="mx-auto max-w-3xl space-y-6 p-6">

        {/* Header */}
        <div>
          <div className="flex items-center gap-2.5">
            <Brain className="h-5 w-5 text-primary" />
            <h1 className="text-xl font-bold">Coach Personal</h1>
            <span className="ml-auto text-xs text-muted-foreground">
              {confLabel[data.confidence] ?? data.confidence} · {data.total_matches} partidas de {data.role}
            </span>
          </div>
          <p className="text-sm text-muted-foreground mt-1">
            Basado en tu historial completo — sin estadísticas genéricas.
          </p>
        </div>

        {/* Sesión de hoy */}
        {data.session.has_session && (
          <SessionSummary session={data.session} />
        )}

        {/* Objetivo adaptativo — lo más importante */}
        {data.active_goal && (
          <AdaptiveGoalCard goal={data.active_goal} />
        )}

        {/* Recomendaciones — qué entrenar ahora */}
        {data.recommendations.length > 0 && (
          <LoLSection
            title="Qué entrenar ahora"
            subtitle="Ordenado por impacto esperado en tu winrate"
          >
            <div className="space-y-3">
              {data.recommendations.map((rec, i) => (
                <KnowledgeRecommendationCard key={rec.rank} rec={rec} delay={i * 0.08} />
              ))}
            </div>
          </LoLSection>
        )}

        {/* Insights — observaciones con evidencia */}
        {data.insights.length > 0 && (
          <LoLSection
            title="Lo que el Coach observa"
            subtitle="Insights basados en tu historial real — con evidencia"
          >
            <div className="space-y-2">
              {data.insights.map((ins, i) => (
                <InsightCard key={ins.rank} insight={ins} delay={i * 0.05} />
              ))}
            </div>
          </LoLSection>
        )}

        {/* Patrones detectados */}
        {data.patterns.length > 0 && (
          <LoLSection
            title="Patrones detectados"
            subtitle="Correlaciones descubiertas en tu forma de jugar"
          >
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              {data.patterns.map((p, i) => (
                <PatternCard key={p.id} pattern={p} delay={i * 0.07} />
              ))}
            </div>
          </LoLSection>
        )}

        {/* Memoria de objetivos */}
        {data.memory.length > 0 && (
          <LoLSection
            title="Historial de objetivos"
            subtitle="El Coach recuerda lo que ya superaste"
            action={<BookOpen className="h-4 w-4 text-muted-foreground/50" />}
          >
            <MemoryTimeline entries={data.memory} />
          </LoLSection>
        )}

      </div>
    </div>
  )
}
