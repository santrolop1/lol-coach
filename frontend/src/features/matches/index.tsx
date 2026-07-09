import { useState } from 'react'
import { Swords, Settings } from 'lucide-react'
import { Skeleton } from '@/components/ui/skeleton'
import { Button } from '@/components/ui/button'
import { LoLSection } from '@/components/lol/LoLSection'
import { LoLEmptyState } from '@/components/lol/LoLEmptyState'
import { LoLErrorState } from '@/components/lol/LoLErrorState'
import { MatchListCard } from './components/MatchListCard'
import { useMatches } from './hooks/useMatches'

const ROLES = ['Todos', 'ADC', 'TOP'] as const
type RoleFilter = (typeof ROLES)[number]

function ListSkeleton() {
  return (
    <div className="space-y-2">
      {Array.from({ length: 8 }).map((_, i) => (
        <Skeleton key={i} className="h-[60px] rounded-lg" />
      ))}
    </div>
  )
}

export default function MatchesPage() {
  const [role, setRole] = useState<RoleFilter>('Todos')
  const { data, isLoading, isError, refetch } = useMatches(role !== 'Todos' ? role : null)

  if (isLoading) {
    return (
      <div className="p-6 max-w-2xl space-y-6">
        <Skeleton className="h-8 w-40" />
        <ListSkeleton />
      </div>
    )
  }

  if (isError) {
    return (
      <div className="flex h-full items-center justify-center p-6">
        <LoLErrorState title="Error al cargar partidas" onRetry={() => refetch()} size="lg" />
      </div>
    )
  }

  if (!data?.has_config) {
    return (
      <div className="flex h-full items-center justify-center p-6">
        <LoLEmptyState
          icon={Settings}
          title="Configura tu cuenta"
          description="Ve a Configuración para configurar tu Riot ID y sincronizar partidas."
          size="lg"
        />
      </div>
    )
  }

  const cards = data.recent_cards ?? []

  return (
    <div className="h-full overflow-y-auto">
      <div className="mx-auto max-w-2xl space-y-6 p-6">
        {/* Header + filtros */}
        <div className="flex items-center justify-between gap-4 flex-wrap">
          <div>
            <h1 className="text-xl font-bold">Partidas recientes</h1>
            <p className="text-sm text-muted-foreground mt-0.5">
              {data.summary.total} partidas · {data.summary.winrate.toFixed(0)}% de winrate
            </p>
          </div>
          <div className="flex gap-1.5">
            {ROLES.map((r) => (
              <Button
                key={r}
                variant={role === r ? 'default' : 'outline'}
                size="sm"
                onClick={() => setRole(r)}
              >
                {r}
              </Button>
            ))}
          </div>
        </div>

        {/* Lista de partidas */}
        {cards.length === 0 ? (
          <LoLEmptyState
            icon={Swords}
            title="Sin partidas"
            description="Sincroniza tus partidas en Configuración para ver tu historial."
            size="lg"
          />
        ) : (
          <LoLSection title={`${cards.length} partidas`}>
            <div className="space-y-1.5">
              {cards.map((card, i) => (
                <MatchListCard key={card.match_id} card={card} index={i} />
              ))}
            </div>
          </LoLSection>
        )}
      </div>
    </div>
  )
}
