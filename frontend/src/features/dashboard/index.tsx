import { RefreshCw, Settings } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { LoLSection } from '@/components/lol/LoLSection'
import { LoLErrorState } from '@/components/lol/LoLErrorState'
import { LoLEmptyState } from '@/components/lol/LoLEmptyState'
import { DashboardHero } from './components/DashboardHero'
import { RoleOverviewCard } from './components/RoleOverviewCard'
import { DashboardSkeleton } from './components/DashboardSkeleton'
import { QuickInsights } from './components/QuickInsights'
import { useDashboard } from './hooks/useDashboard'
import type { Role } from '@/features/shared/types/api'

const ROLE_ORDER: Role[] = ['ADC', 'TOP']

export default function DashboardPage() {
  const { data, isLoading, isError, error, refetch, isFetching } = useDashboard()

  if (isLoading) {
    return (
      <div className="p-6">
        <DashboardSkeleton />
      </div>
    )
  }

  if (isError) {
    const message = error instanceof Error ? error.message : 'No se pudo conectar con el backend.'
    return (
      <div className="flex h-full items-center justify-center p-6">
        <LoLErrorState
          title="Error al cargar el dashboard"
          message={message}
          onRetry={() => refetch()}
          size="lg"
        />
      </div>
    )
  }

  if (!data) return null

  if (!data.is_configured) {
    return (
      <div className="flex h-full items-center justify-center p-6">
        <LoLEmptyState
          icon={Settings}
          title="Configura tu cuenta"
          description="Ve a Configuración, ingresa tu Riot ID y API key para empezar a analizar tu rendimiento."
          size="lg"
        />
      </div>
    )
  }

  const roles = ROLE_ORDER.filter((r) => r in data.roles)

  return (
    <div className="h-full overflow-y-auto">
      <div className="mx-auto max-w-3xl space-y-6 p-6">

        {/* Hero */}
        <DashboardHero data={data} />

        {/* Role cards */}
        {roles.length > 0 ? (
          <LoLSection
            title="Rendimiento por rol"
            action={
              <Button
                variant="ghost"
                size="sm"
                onClick={() => refetch()}
                disabled={isFetching}
                aria-label="Actualizar datos"
              >
                <RefreshCw className={`h-3.5 w-3.5 ${isFetching ? 'animate-spin' : ''}`} />
                <span className="sr-only">Actualizar</span>
              </Button>
            }
          >
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
              {roles.map((role, i) => (
                <RoleOverviewCard
                  key={role}
                  role={role}
                  data={data.roles[role]!}
                  delay={i * 0.08}
                />
              ))}
            </div>
          </LoLSection>
        ) : (
          <LoLEmptyState
            title="Sin datos de rol"
            description="Sincroniza tus partidas en Configuración para ver tu análisis."
            size="md"
          />
        )}

        {/* Quick insights */}
        {roles.length > 0 && (
          <LoLSection title="Resumen inteligente">
            <QuickInsights data={data} />
          </LoLSection>
        )}
      </div>
    </div>
  )
}
