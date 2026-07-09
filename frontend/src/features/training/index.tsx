import { Dumbbell } from 'lucide-react'
import { Skeleton } from '@/components/ui/skeleton'
import { LoLSection } from '@/components/lol/LoLSection'
import { LoLEmptyState } from '@/components/lol/LoLEmptyState'
import { LoLErrorState } from '@/components/lol/LoLErrorState'
import { TodayFocus } from './components/TodayFocus'
import { ExerciseCard } from './components/ExerciseCard'
import { SkillTree } from './components/SkillTree'
import { WeeklyPlan } from './components/WeeklyPlan'
import { TrainingHistory } from './components/TrainingHistory'
import { useTraining } from './hooks/useTraining'

function TrainingSkeleton() {
  return (
    <div className="p-6 max-w-3xl space-y-6">
      <Skeleton className="h-10 w-48" />
      <Skeleton className="h-64 rounded-2xl" />
      <div className="grid grid-cols-2 gap-3">
        {[0, 1, 2, 3].map((i) => <Skeleton key={i} className="h-28 rounded-xl" />)}
      </div>
      <Skeleton className="h-48 rounded-xl" />
    </div>
  )
}

const CONF_LABEL: Record<string, string> = {
  reliable:     'Análisis fiable',
  preliminary:  'Análisis preliminar',
  insufficient: 'Muestra reducida',
}

export default function TrainingPage() {
  const { data, isLoading, isError, refetch } = useTraining()

  if (isLoading) return <TrainingSkeleton />

  if (isError) {
    return (
      <div className="flex h-full items-center justify-center p-6">
        <LoLErrorState title="Error al cargar el Training Engine" onRetry={() => refetch()} size="lg" />
      </div>
    )
  }

  if (!data?.has_data) {
    return (
      <div className="flex h-full items-center justify-center p-6">
        <LoLEmptyState
          icon={Dumbbell}
          title={data?.games_needed_msg ?? 'Sin datos suficientes'}
          description="El Training Engine necesita historial de partidas para generar tu plan de entrenamiento."
          size="lg"
        />
      </div>
    )
  }

  return (
    <div className="h-full overflow-y-auto">
      <div className="mx-auto max-w-3xl space-y-6 p-6">

        {/* Header */}
        <div>
          <div className="flex items-center gap-2.5">
            <Dumbbell className="h-5 w-5 text-primary" />
            <h1 className="text-xl font-bold">Plan de Entrenamiento</h1>
            <span className="ml-auto text-xs text-muted-foreground">
              {CONF_LABEL[data.confidence] ?? data.confidence} · {data.total_matches} partidas de {data.role}
            </span>
          </div>
          <p className="text-sm text-muted-foreground mt-1">
            Un objetivo a la vez. Medible. Automático.
          </p>
        </div>

        {/* Foco de hoy — lo primero que ve el jugador */}
        {data.daily_plan && data.active_exercise && (
          <TodayFocus plan={data.daily_plan} exercise={data.active_exercise} />
        )}

        {/* Detalles del ejercicio activo */}
        {data.active_exercise && (
          <LoLSection
            title="Sobre este ejercicio"
            subtitle="Por qué, cómo se mide y qué consigues al completarlo"
          >
            <ExerciseCard exercise={data.active_exercise} />
          </LoLSection>
        )}

        {/* Skill Tree */}
        {data.skill_tree.length > 0 && (
          <LoLSection
            title="Árbol de habilidades"
            subtitle="Progresión de tu desarrollo como jugador"
          >
            <SkillTree nodes={data.skill_tree} />
          </LoLSection>
        )}

        {/* Hoja de ruta semanal */}
        {data.weekly_roadmap.length > 0 && (
          <LoLSection
            title="Hoja de ruta"
            subtitle="Tu progresión bloque a bloque"
          >
            <WeeklyPlan slots={data.weekly_roadmap} />
          </LoLSection>
        )}

        {/* Siguiente skill preview */}
        {data.next_skill_name && data.next_skill_reason && (
          <div className="rounded-xl border border-dashed border-primary/20 bg-primary/3 px-4 py-3">
            <p className="text-[11px] uppercase tracking-wider text-muted-foreground mb-1">
              Siguiente bloque
            </p>
            <p className="text-sm font-semibold text-primary">{data.next_skill_name}</p>
            <p className="text-xs text-muted-foreground mt-0.5">{data.next_skill_reason}</p>
          </div>
        )}

        {/* Historial */}
        {data.history.length > 0 && (
          <LoLSection
            title="Ejercicios completados"
            subtitle="Tu historial de entrenamiento"
          >
            <TrainingHistory entries={data.history} />
          </LoLSection>
        )}

      </div>
    </div>
  )
}
