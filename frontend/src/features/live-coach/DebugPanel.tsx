/**
 * DebugPanel — panel de depuración en tiempo real del Live Coach.
 * Solo para desarrollo — no incluir en build de producción.
 */

import { useState } from 'react'
import { useDebugState } from './hooks/useDebugState'

function JsonBlock({ data, label }: { data: unknown; label: string }) {
  const [open, setOpen] = useState(false)
  return (
    <div className="border border-white/10 rounded-lg overflow-hidden">
      <button
        onClick={() => setOpen(v => !v)}
        className="w-full flex items-center justify-between px-3 py-2 bg-white/5 hover:bg-white/10 text-left"
      >
        <span className="text-xs font-medium text-white/70">{label}</span>
        <span className="text-white/40 text-xs">{open ? '▲' : '▼'}</span>
      </button>
      {open && (
        <pre className="p-3 text-xs text-green-300/80 bg-black/40 overflow-auto max-h-60 leading-relaxed">
          {JSON.stringify(data, null, 2)}
        </pre>
      )}
    </div>
  )
}

function Pill({ label, value, color = 'zinc' }: { label: string; value: string | number | boolean | null | undefined; color?: string }) {
  const colors: Record<string, string> = {
    zinc:   'bg-zinc-700/50 text-zinc-300',
    green:  'bg-green-500/20 text-green-400',
    yellow: 'bg-yellow-500/20 text-yellow-400',
    red:    'bg-red-500/20 text-red-400',
    blue:   'bg-blue-500/20 text-blue-400',
    purple: 'bg-purple-500/20 text-purple-400',
  }
  return (
    <div className={`flex items-center gap-2 px-2 py-1 rounded ${colors[color] ?? colors.zinc}`}>
      <span className="text-xs opacity-60">{label}</span>
      <span className="text-xs font-mono font-medium">{String(value ?? '—')}</span>
    </div>
  )
}

export function DebugPanel() {
  const { data, isLoading, error } = useDebugState(true)

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-32 text-white/40 text-sm">
        Cargando datos de depuración...
      </div>
    )
  }

  if (error || !data) {
    return (
      <div className="flex items-center justify-center h-32 text-red-400 text-sm">
        Error al cargar el estado de depuración
      </div>
    )
  }

  const intel = data.intelligence ?? {}
  const dec = data.decision

  return (
    <div className="space-y-5 text-white">

      {/* Sesión */}
      <section className="space-y-2">
        <h3 className="text-xs font-semibold text-white/40 uppercase tracking-wider">Sesión</h3>
        <div className="flex flex-wrap gap-2">
          <Pill label="champion" value={data.session?.champion as string} color={data.session?.champion ? 'green' : 'zinc'} />
          <Pill label="phase" value={data.session?.phase as string} />
          <Pill label="game_time" value={`${Math.floor(((data.session?.game_time as number) ?? 0) / 60)}m${Math.floor(((data.session?.game_time as number) ?? 0) % 60)}s`} />
          <Pill label="connected" value={data.session?.provider_connected ? 'sí' : 'no'} color={data.session?.provider_connected ? 'green' : 'red'} />
          <Pill label="active" value={data.session?.active ? 'sí' : 'no'} color={data.session?.active ? 'green' : 'zinc'} />
        </div>
      </section>

      {/* Player stats */}
      <section className="space-y-2">
        <h3 className="text-xs font-semibold text-white/40 uppercase tracking-wider">Jugador</h3>
        <div className="flex flex-wrap gap-2">
          <Pill label="level" value={data.player?.level as number} />
          <Pill label="gold" value={`${data.player?.gold}g`} color="yellow" />
          <Pill label="cs" value={data.player?.cs as number} />
          <Pill label="KDA" value={`${data.player?.kills}/${data.player?.deaths}/${data.player?.assists}`} />
          <Pill label="hp" value={`${Math.round(((data.player?.hp_pct as number) ?? 1) * 100)}%`} color={(data.player?.hp_pct as number) < 0.3 ? 'red' : 'green'} />
          <Pill label="dead" value={data.player?.is_dead ? 'sí' : 'no'} color={data.player?.is_dead ? 'red' : 'zinc'} />
        </div>
      </section>

      {/* Inteligencia */}
      <section className="space-y-2">
        <h3 className="text-xs font-semibold text-white/40 uppercase tracking-wider">Coach Intelligence</h3>
        <div className="flex flex-wrap gap-2">
          <Pill label="state" value={String(intel.state ?? '—')} color="blue" />
          <Pill label="phase" value={String(intel.phase ?? '—')} />
          <Pill label="situation" value={String(intel.situation ?? '—')} />
          <Pill label="spike" value={intel.is_power_spike ? 'SÍ' : 'no'} color={intel.is_power_spike ? 'yellow' : 'zinc'} />
          <Pill label="recall" value={intel.is_recall_window ? 'SÍ' : 'no'} color={intel.is_recall_window ? 'blue' : 'zinc'} />
          <Pill label="mode" value={String(intel.coach_mode ?? '—')} />
        </div>

        {intel.objective && typeof intel.objective === 'object' ? (() => {
          const objective = intel.objective as Record<string, unknown>
          return (
            <div className="p-2 rounded bg-blue-950/40 border border-blue-500/20 text-xs">
              <span className="text-blue-300/70 font-medium">Objetivo: </span>
              <span className="text-white/80">{String(objective.title ?? '')}</span>
            </div>
          )
        })() : null}

        {intel.mission && typeof intel.mission === 'object' ? (() => {
          const mission = intel.mission as Record<string, unknown>
          return (
            <div className="p-2 rounded bg-emerald-950/40 border border-emerald-500/20 text-xs flex items-center gap-2">
              <span className="text-emerald-300/70 font-medium">Misión: </span>
              <span className="text-white/80">{String(mission.title ?? '')}</span>
              <span className="ml-auto text-emerald-400">
                {Math.round(Number(mission.progress_pct ?? 0) * 100)}%
              </span>
            </div>
          )
        })() : null}
      </section>

      {/* Decisión */}
      <section className="space-y-2">
        <h3 className="text-xs font-semibold text-white/40 uppercase tracking-wider">Decisión actual</h3>
        {dec && typeof dec === 'object' ? (() => {
          const d = dec as Record<string, unknown>
          return (
            <div className="p-3 rounded-lg bg-white/5 border border-white/10 space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-sm font-semibold text-white">{String(d.title ?? '')}</span>
                <span className="text-sm font-bold text-green-400">{Number(d.confidence_pct ?? 0)}%</span>
              </div>
              <div className="flex gap-2 flex-wrap">
                <Pill label="type" value={String(d.type ?? '')} color="purple" />
                <Pill label="priority" value={Number(d.priority ?? 0)} />
                <Pill label="age" value={`${Math.round(Number(d.age_seconds ?? 0))}s`} />
              </div>
            </div>
          )
        })() : (
          <p className="text-xs text-white/30 italic">Sin decisión activa</p>
        )}
      </section>

      {/* Widgets activos */}
      <section className="space-y-2">
        <h3 className="text-xs font-semibold text-white/40 uppercase tracking-wider">
          Widgets activos ({(data.widgets ?? []).filter(w => Boolean(w.visible)).length})
        </h3>
        <div className="space-y-1">
          {(data.widgets ?? []).map((w, i) => {
            const ww = w as Record<string, unknown>
            return (
              <div key={i} className={`flex items-center gap-2 text-xs px-2 py-1 rounded ${ww.visible ? 'bg-white/5' : 'bg-black/20 opacity-40'}`}>
                <span className="text-white/40 w-24 shrink-0 truncate">{String(ww.id ?? '')}</span>
                <span className="text-white/70 flex-1 truncate">{String(ww.title ?? '')}</span>
                <span className="text-white/40 text-right w-8">{Number(ww.priority ?? 0)}</span>
              </div>
            )
          })}
        </div>
      </section>

      {/* Eventos recientes */}
      <section className="space-y-2">
        <h3 className="text-xs font-semibold text-white/40 uppercase tracking-wider">Últimos eventos</h3>
        <div className="space-y-1 max-h-40 overflow-y-auto">
          {[...(data.recent_events ?? [])].reverse().map((e, i) => (
            <div key={i} className="flex items-center gap-2 text-xs px-2 py-1 rounded bg-white/5">
              <span className="text-yellow-400/70 font-mono w-28 shrink-0">{e.type}</span>
              <span className="text-white/30 font-mono text-right ml-auto">
                {new Date(e.timestamp * 1000).toLocaleTimeString()}
              </span>
            </div>
          ))}
          {!data.recent_events?.length && (
            <p className="text-xs text-white/20 italic px-2">Sin eventos recientes</p>
          )}
        </div>
      </section>

      {/* Bloques JSON colapsables */}
      <section className="space-y-2">
        <h3 className="text-xs font-semibold text-white/40 uppercase tracking-wider">Raw JSON</h3>
        <JsonBlock label="intelligence completo" data={data.intelligence} />
        <JsonBlock label="decisión completa" data={data.decision} />
        <JsonBlock label="historial de decisiones" data={data.decision_history} />
        <JsonBlock label="demo state" data={data.demo} />
      </section>
    </div>
  )
}
