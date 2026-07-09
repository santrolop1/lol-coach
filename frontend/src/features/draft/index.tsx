import { Layers, Wifi, WifiOff, Clock, Shield, Swords } from 'lucide-react'
import { motion } from 'framer-motion'
import { Skeleton } from '@/components/ui/skeleton'
import { LoLSection } from '@/components/lol/LoLSection'
import { LoLEmptyState } from '@/components/lol/LoLEmptyState'
import { LoLErrorState } from '@/components/lol/LoLErrorState'
import { LoLHeroCard } from '@/components/lol/LoLHeroCard'
import { cn } from '@/lib/utils'
import { useDraft } from './hooks/useDraft'
import type { DraftResponse } from './types'

// ── Skeleton ──────────────────────────────────────────────────────────────────

function DraftSkeleton() {
  return (
    <div className="p-6 max-w-3xl space-y-6">
      <Skeleton className="h-10 w-48" />
      <Skeleton className="h-28 rounded-2xl" />
      <div className="grid grid-cols-2 gap-3">
        <Skeleton className="h-40 rounded-xl" />
        <Skeleton className="h-40 rounded-xl" />
      </div>
    </div>
  )
}

// ── Connection badge ───────────────────────────────────────────────────────────

function LcuBadge({ connected }: { connected: boolean }) {
  return (
    <div className={cn(
      'flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-xs font-medium',
      connected
        ? 'border-emerald-500/30 bg-emerald-500/10 text-emerald-400'
        : 'border-muted-foreground/20 bg-muted/30 text-muted-foreground'
    )}>
      {connected
        ? <Wifi className="h-3 w-3" />
        : <WifiOff className="h-3 w-3" />}
      {connected ? 'Cliente conectado' : 'Cliente desconectado'}
    </div>
  )
}

// ── Waiting state (LCU conectado pero no en champion select) ──────────────────

function WaitingForChampSelect({ phase_label }: { phase_label: string }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      className="flex flex-col items-center justify-center gap-4 py-16 text-center"
    >
      <div className="rounded-2xl border border-primary/20 bg-primary/5 p-5">
        <Clock className="h-10 w-10 text-primary/60" />
      </div>
      <div>
        <p className="font-semibold text-lg">Esperando champion select</p>
        <p className="text-sm text-muted-foreground mt-1">
          Estado actual: <span className="text-foreground">{phase_label}</span>
        </p>
        <p className="text-xs text-muted-foreground/60 mt-2">
          El análisis de draft se activará automáticamente cuando entres en selección de campeones.
        </p>
      </div>
    </motion.div>
  )
}

// ── Champion list ──────────────────────────────────────────────────────────────

function ChampionTag({ name, variant = 'default' }: { name: string; variant?: 'ally' | 'enemy' | 'ban' | 'default' }) {
  const styles = {
    ally:    'bg-blue-500/15 border-blue-500/30 text-blue-300',
    enemy:   'bg-red-500/15 border-red-500/30 text-red-300',
    ban:     'bg-muted/30 border-border/60 text-muted-foreground line-through',
    default: 'bg-muted/30 border-border/60 text-foreground',
  }
  return (
    <span className={cn(
      'inline-flex rounded-md border px-2 py-1 text-xs font-medium',
      styles[variant]
    )}>
      {name}
    </span>
  )
}

// ── Session panel ─────────────────────────────────────────────────────────────

interface ChampionSlotData {
  cell_id:           number
  champion_id:       number
  champion_name:     string
  assigned_position: string
  spell1_id:         number
  spell2_id:         number
  is_local_player:   boolean
}

interface BanPhaseData {
  my_team_bans:    string[]
  their_team_bans: string[]
}

function pickedChampionNames(slots: ChampionSlotData[] | undefined): string[] {
  return (slots ?? [])
    .filter((s) => s.champion_id !== 0)
    .map((s) => s.champion_name)
}

function SessionPanel({ data }: { data: DraftResponse }) {
  const session = data.session as Record<string, unknown> | null
  const advice  = data.advice
  const pool    = data.champion_pool

  // Extraer equipos de la sesión si están disponibles
  const myTeam    = pickedChampionNames(session?.my_team as ChampionSlotData[] | undefined)
  const enemyTeam = pickedChampionNames(session?.their_team as ChampionSlotData[] | undefined)
  const banPhase  = session?.bans as BanPhaseData | undefined
  const bans      = [...(banPhase?.my_team_bans ?? []), ...(banPhase?.their_team_bans ?? [])]

  return (
    <div className="space-y-5">

      {/* Equipos */}
      {(myTeam.length > 0 || enemyTeam.length > 0) && (
        <div className="grid grid-cols-2 gap-4">
          {myTeam.length > 0 && (
            <div className="space-y-2">
              <p className="text-xs font-semibold uppercase tracking-wider text-blue-400 flex items-center gap-1.5">
                <Shield className="h-3.5 w-3.5" /> Tu equipo
              </p>
              <div className="flex flex-wrap gap-1.5">
                {myTeam.map((c) => <ChampionTag key={c} name={c} variant="ally" />)}
              </div>
            </div>
          )}
          {enemyTeam.length > 0 && (
            <div className="space-y-2">
              <p className="text-xs font-semibold uppercase tracking-wider text-red-400 flex items-center gap-1.5">
                <Swords className="h-3.5 w-3.5" /> Enemigos
              </p>
              <div className="flex flex-wrap gap-1.5">
                {enemyTeam.map((c) => <ChampionTag key={c} name={c} variant="enemy" />)}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Bans */}
      {bans.length > 0 && (
        <div className="space-y-2">
          <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
            Bans
          </p>
          <div className="flex flex-wrap gap-1.5">
            {bans.map((c) => <ChampionTag key={c} name={c} variant="ban" />)}
          </div>
        </div>
      )}

      {/* Advice */}
      {advice && (
        <>
          {Array.isArray(advice.picks) && advice.picks.length > 0 && (
            <LoLSection title="Picks sugeridos" subtitle="Basado en tu historial y la composición actual">
              <div className="flex flex-wrap gap-1.5">
                {(advice.picks as string[]).map((c) => (
                  <ChampionTag key={c} name={c} variant="ally" />
                ))}
              </div>
            </LoLSection>
          )}
          {Array.isArray(advice.bans) && advice.bans.length > 0 && (
            <LoLSection title="Bans recomendados">
              <div className="flex flex-wrap gap-1.5">
                {(advice.bans as string[]).map((c) => (
                  <ChampionTag key={c} name={c} variant="ban" />
                ))}
              </div>
            </LoLSection>
          )}
          {Array.isArray(advice.notes) && advice.notes.length > 0 && (
            <LoLSection title="Notas del análisis">
              <ul className="space-y-1.5">
                {(advice.notes as string[]).map((note, i) => (
                  <li key={i} className="flex items-start gap-2 text-sm text-muted-foreground">
                    <span className="mt-1.5 h-1.5 w-1.5 rounded-full bg-primary/50 shrink-0" />
                    {note}
                  </li>
                ))}
              </ul>
            </LoLSection>
          )}
        </>
      )}

      {/* Champion pool */}
      {pool && Array.isArray(pool.champions) && pool.champions.length > 0 && (
        <LoLSection
          title="Tu pool de campeones"
          subtitle={`${data.role ?? ''} · por winrate`}
        >
          <div className="grid grid-cols-2 gap-2 sm:grid-cols-3">
            {(pool.champions as Array<{ champion: string; games: number; winrate: number; grade?: string }>)
              .slice(0, 6)
              .map((c) => (
                <div
                  key={c.champion}
                  className="rounded-lg border border-border/60 bg-card/40 px-3 py-2 space-y-0.5"
                >
                  <p className="text-sm font-medium truncate">{c.champion}</p>
                  <p className="text-xs text-muted-foreground">
                    {(c.winrate * 100).toFixed(0)}% WR · {c.games}G
                  </p>
                </div>
              ))}
          </div>
        </LoLSection>
      )}

      {/* Sin datos de sesión todavía */}
      {!session && !advice && !pool && (
        <p className="text-sm text-muted-foreground text-center py-8">
          Esperando datos de champion select…
        </p>
      )}
    </div>
  )
}

// ── Page ───────────────────────────────────────────────────────────────────────

export default function DraftPage() {
  const { data, isLoading, isError, refetch } = useDraft()

  if (isLoading) return <DraftSkeleton />

  if (isError) {
    return (
      <div className="flex h-full items-center justify-center p-6">
        <LoLErrorState title="Error al cargar el Draft" onRetry={() => refetch()} size="lg" />
      </div>
    )
  }

  if (!data) {
    return (
      <div className="flex h-full items-center justify-center p-6">
        <LoLEmptyState icon={Layers} title="Sin datos de draft" size="lg" />
      </div>
    )
  }

  const inChampSelect = data.phase === 'ChampSelect'

  return (
    <div className="h-full overflow-y-auto">
      <div className="mx-auto max-w-3xl space-y-6 p-6">

        {/* Header */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <Layers className="h-5 w-5 text-primary" />
            <h1 className="text-xl font-bold">Draft Intelligence</h1>
          </div>
          <LcuBadge connected={data.lcu_connected} />
        </div>

        {/* LCU desconectado */}
        {!data.lcu_connected && (
          <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }}>
            <LoLEmptyState
              icon={WifiOff}
              title="Cliente de League no detectado"
              description="Abre el cliente de League of Legends para activar el análisis de draft en tiempo real."
              size="md"
            />
          </motion.div>
        )}

        {/* Conectado pero no en champion select */}
        {data.lcu_connected && !inChampSelect && (
          <WaitingForChampSelect phase_label={data.phase_label} />
        )}

        {/* En champion select */}
        {data.lcu_connected && inChampSelect && (
          <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }}>
            <LoLHeroCard
              title="Champion Select activo"
              subtitle={data.role ? `Rol detectado: ${data.role}` : 'Detectando rol…'}
              icon={Layers}
              accent={data.role_supported ? 'primary' : 'accent'}
              meta={!data.role_supported && data.role ? `Análisis limitado — ${data.role} no tiene scorer completo aún` : undefined}
            >
              <SessionPanel data={data} />
            </LoLHeroCard>
          </motion.div>
        )}

      </div>
    </div>
  )
}
