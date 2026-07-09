import { Wifi, WifiOff, Clock, Shield } from 'lucide-react'
import { motion } from 'framer-motion'
import { useAppStore } from '@/store/appStore'
import type { DashboardResponse } from '@/features/shared/types/api'

interface DashboardHeroProps {
  data: DashboardResponse
}

function RankBadge({ rank, lp }: { rank: string | null; lp: number | null }) {
  if (!rank) return null
  return (
    <span className="inline-flex items-center gap-1.5 rounded-md bg-yellow-500/10 border border-yellow-500/25 px-2.5 py-1 text-sm font-semibold text-yellow-400">
      <Shield className="h-3.5 w-3.5" />
      {rank}{lp != null ? ` · ${lp} LP` : ''}
    </span>
  )
}

function LcuDot({ connected }: { connected: boolean }) {
  return (
    <span className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-medium
      ${connected
        ? 'bg-emerald-500/10 border border-emerald-500/20 text-emerald-400'
        : 'bg-muted/40 border border-border text-muted-foreground'
      }`}
    >
      {connected
        ? <><Wifi className="h-3 w-3" />Cliente conectado</>
        : <><WifiOff className="h-3 w-3" />Sin cliente</>
      }
    </span>
  )
}

export function DashboardHero({ data }: DashboardHeroProps) {
  const lcuConnected = useAppStore((s) => s.lcuConnected)

  return (
    <motion.div
      initial={{ opacity: 0, y: -8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, ease: 'easeOut' }}
      className="relative overflow-hidden rounded-2xl border border-primary/20 bg-gradient-to-br from-primary/8 via-card to-card p-6"
    >
      {/* Ambient glow */}
      <div className="pointer-events-none absolute -left-10 -top-10 h-40 w-40 rounded-full bg-primary/15 blur-3xl" />

      <div className="relative flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        {/* Left: player info */}
        <div className="space-y-2">
          <h1 className="text-2xl font-bold tracking-tight sm:text-3xl">
            {data.player_name || 'Jugador'}
          </h1>
          <div className="flex flex-wrap items-center gap-2">
            <RankBadge rank={data.rank} lp={data.lp} />
            <LcuDot connected={lcuConnected} />
          </div>
        </div>

        {/* Right: sync info */}
        <div className="flex flex-col items-start gap-1 sm:items-end">
          {data.last_sync ? (
            <span className="flex items-center gap-1.5 text-xs text-muted-foreground">
              <Clock className="h-3 w-3" />
              {data.sync_label}
            </span>
          ) : (
            <span className="text-xs text-muted-foreground/60">Sin datos sincronizados</span>
          )}
          <span className="text-xs text-muted-foreground/40">
            {Object.keys(data.roles).length} rol{Object.keys(data.roles).length !== 1 ? 'es' : ''} analizados
          </span>
        </div>
      </div>
    </motion.div>
  )
}
