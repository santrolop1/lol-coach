import { useNavigate, useParams } from 'react-router-dom'
import { AlertTriangle, Target, Lightbulb } from 'lucide-react'
import { motion } from 'framer-motion'
import { Skeleton } from '@/components/ui/skeleton'
import { LoLSection } from '@/components/lol/LoLSection'
import { LoLErrorState } from '@/components/lol/LoLErrorState'
import { LoLInsightCard } from '@/components/lol/LoLInsightCard'
import { ReviewHeader } from '../components/ReviewHeader'
import { OverallScorePanel } from '../components/OverallScorePanel'
import { DimensionDetailCard } from '../components/DimensionDetailCard'
import { useMatchReview } from '../hooks/useMatchReview'

function ReviewSkeleton() {
  return (
    <div className="space-y-5 p-6">
      <Skeleton className="h-24 rounded-2xl" />
      <Skeleton className="h-32 rounded-2xl" />
      <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
        {[0, 1, 2].map((i) => <Skeleton key={i} className="h-48 rounded-xl" />)}
      </div>
      <Skeleton className="h-20 rounded-lg" />
    </div>
  )
}

export default function MatchReviewPage() {
  const { matchId } = useParams<{ matchId: string }>()
  const navigate    = useNavigate()
  const id          = matchId ? decodeURIComponent(matchId) : undefined

  const { data, isLoading, isError, error, refetch } = useMatchReview(id)

  const goBack = () => navigate('/matches')

  if (isLoading) return <ReviewSkeleton />

  if (isError) {
    const msg = error instanceof Error ? error.message : 'No se pudo cargar la revisión.'
    return (
      <div className="flex h-full items-center justify-center p-6">
        <LoLErrorState title="Error al cargar la partida" message={msg} onRetry={() => refetch()} size="lg" />
      </div>
    )
  }

  if (!data || !data.found) {
    return (
      <div className="flex h-full items-center justify-center p-6">
        <LoLErrorState title="Partida no encontrada" message="Puede que haya sido eliminada o el ID sea incorrecto." onRetry={goBack} retryLabel="Volver a partidas" size="lg" />
      </div>
    )
  }

  if (!data.role_supported) {
    return (
      <div className="flex flex-col h-full">
        <ReviewHeader data={data} onBack={goBack} />
        <div className="flex-1 flex items-center justify-center p-6">
          <LoLErrorState title={`Rol ${data.role} no soportado`} message="El análisis detallado está disponible para ADC y TOP." onRetry={goBack} retryLabel="Volver" size="lg" />
        </div>
      </div>
    )
  }

  const bestDim  = data.dimensions.find((d) => d.is_best)
  const worstDim = data.dimensions.find((d) => d.is_worst)

  return (
    <div className="flex flex-col h-full">
      <ReviewHeader data={data} onBack={goBack} />

      <div className="flex-1 overflow-y-auto">
        <div className="mx-auto max-w-3xl space-y-6 p-6">

          {/* Score general */}
          <OverallScorePanel data={data} />

          {/* Lo que hiciste bien */}
          {bestDim && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: 0.15 }}
            >
              <LoLSection title="Lo que hiciste bien">
                <LoLInsightCard
                  variant="success"
                  title={`${bestDim.name_es} — tu punto fuerte (${bestDim.score?.toFixed(0)}/100)`}
                  body={bestDim.context}
                />
              </LoLSection>
            </motion.div>
          )}

          {/* Error principal */}
          {(data.key_error_title || worstDim) && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: 0.2 }}
            >
              <LoLSection title="Error principal">
                <LoLInsightCard
                  icon={AlertTriangle}
                  variant="warning"
                  title={data.key_error_title ?? `${worstDim?.name_es} — rendimiento bajo`}
                  body={data.key_error_body ?? worstDim?.context}
                />
              </LoLSection>
            </motion.div>
          )}

          {/* Análisis por dimensión */}
          <LoLSection
            title="Análisis por dimensión"
            subtitle="Comparado con tu promedio histórico en este rol"
          >
            <div className="grid grid-cols-1 gap-3 md:grid-cols-3">
              {data.dimensions.map((dim, i) => (
                <DimensionDetailCard key={dim.name} dim={dim} delay={i * 0.07} />
              ))}
            </div>
          </LoLSection>

          {/* Para la próxima partida */}
          {data.focus_tip && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: 0.35 }}
            >
              <LoLSection title="Para la próxima partida">
                <LoLInsightCard
                  icon={Target}
                  variant="tip"
                  title="Prioridad de trabajo"
                  body={data.focus_tip}
                />
              </LoLSection>
            </motion.div>
          )}

          {/* Nota de muestra baja */}
          {data.confidence === 'insufficient' && (
            <LoLInsightCard
              icon={Lightbulb}
              variant="info"
              title="Análisis con muestra reducida"
              body={`Solo hay ${data.sample_size} partida${data.sample_size !== 1 ? 's' : ''} de referencia para este rol. Los scores mejorarán en precisión con más partidas.`}
            />
          )}
        </div>
      </div>
    </div>
  )
}
