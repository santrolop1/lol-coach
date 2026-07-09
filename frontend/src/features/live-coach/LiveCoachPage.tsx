/**
 * LiveCoachPage — hub del Live Coach dentro de la app principal.
 *
 * Tabs:
 *   Estado    — vista del overlay en tiempo real (widgets + decisión)
 *   Demo Mode — selector de escenarios + simulador de eventos
 *   Debug     — panel de depuración completo (solo dev)
 */

import { useState, lazy, Suspense } from 'react'
import { useLiveCoach } from './useLiveCoach'
import { DemoPanel } from './DemoPanel'
import { DecisionCard } from './components/DecisionCard'

const DebugPanel = lazy(() => import('./DebugPanel').then(m => ({ default: m.DebugPanel })))

type Tab = 'estado' | 'demo' | 'debug'

function TabBar({ active, onChange }: { active: Tab; onChange: (t: Tab) => void }) {
  const tabs: { id: Tab; label: string }[] = [
    { id: 'estado', label: 'Estado en vivo' },
    { id: 'demo',   label: 'Demo Mode' },
    { id: 'debug',  label: 'Debug' },
  ]
  return (
    <div className="flex gap-1 p-1 bg-black/30 rounded-lg border border-white/10 w-fit">
      {tabs.map(t => (
        <button
          key={t.id}
          onClick={() => onChange(t.id)}
          className={`
            px-4 py-1.5 rounded text-sm font-medium transition-all
            ${active === t.id
              ? 'bg-yellow-400/20 text-yellow-400 border border-yellow-400/30'
              : 'text-white/50 hover:text-white/80'}
          `}
        >
          {t.label}
        </button>
      ))}
    </div>
  )
}

function WidgetsList({ widgets }: { widgets: { id: string; title: string; lines: string[]; icon: string; highlight: boolean }[] }) {
  if (!widgets.length) {
    return <p className="text-sm text-white/30 italic text-center py-8">Sin widgets activos</p>
  }
  return (
    <div className="space-y-2">
      {widgets.map(w => (
        <div
          key={w.id}
          className={`p-3 rounded-lg border transition-all ${
            w.highlight
              ? 'border-yellow-400/40 bg-yellow-950/30'
              : 'border-white/10 bg-white/5'
          }`}
        >
          <div className="flex items-center gap-2 mb-1">
            {w.icon && <span className="text-base">{w.icon}</span>}
            <span className="text-sm font-semibold text-white">{w.title}</span>
          </div>
          {w.lines.map((line, i) => (
            <p key={i} className="text-xs text-white/60 leading-relaxed">{line}</p>
          ))}
        </div>
      ))}
    </div>
  )
}

function StatusIndicator({ connected, active }: { connected: boolean; active: boolean }) {
  return (
    <div className="flex items-center gap-3">
      <span className={`flex items-center gap-1.5 text-xs ${connected ? 'text-green-400' : 'text-red-400'}`}>
        <span className={`w-1.5 h-1.5 rounded-full ${connected ? 'bg-green-400 animate-pulse' : 'bg-red-400'}`} />
        {connected ? 'Conectado' : 'Sin conexión'}
      </span>
      {active && (
        <span className="text-xs text-yellow-400 bg-yellow-400/10 border border-yellow-400/20 px-2 py-0.5 rounded">
          En partida
        </span>
      )}
    </div>
  )
}

export function LiveCoachPage() {
  const [tab, setTab] = useState<Tab>('estado')
  const { state, connected, connectionMode, setChampion } = useLiveCoach()

  const formatTime = (seconds: number) => {
    const m = Math.floor(seconds / 60)
    const s = Math.floor(seconds % 60)
    return `${m}:${s.toString().padStart(2, '0')}`
  }

  return (
    <div className="max-w-2xl mx-auto p-6 space-y-6">
      {/* Header */}
      <div className="space-y-1">
        <div className="flex items-center justify-between">
          <h1 className="text-2xl font-bold text-white">Live Coach</h1>
          <StatusIndicator connected={connected} active={state.active} />
        </div>
        <p className="text-sm text-white/50">
          Asistente en tiempo real durante la partida •{' '}
          <span className="text-white/30 font-mono text-xs">{connectionMode}</span>
        </p>
      </div>

      {/* Tabs */}
      <TabBar active={tab} onChange={setTab} />

      {/* ── Tab: Estado ── */}
      {tab === 'estado' && (
        <div className="space-y-4">

          {/* Sesión activa */}
          {state.active ? (
            <div className="flex items-center gap-4 p-3 rounded-lg bg-white/5 border border-white/10">
              <div className="text-2xl font-bold text-white capitalize">{state.champion || '—'}</div>
              <div className="text-white/40">•</div>
              <div className="text-sm text-white/60">{state.role}</div>
              <div className="ml-auto text-sm font-mono text-white/60">{formatTime(state.game_time)}</div>
              <div className="text-xs text-white/40">
                {state.player.kills}/{state.player.deaths}/{state.player.assists}
              </div>
            </div>
          ) : (
            <div className="p-4 rounded-lg bg-white/5 border border-white/10 text-center space-y-2">
              <p className="text-white/40 text-sm">Sin partida activa</p>
              <p className="text-white/25 text-xs">Abre una partida en League of Legends o activa el Demo Mode</p>
            </div>
          )}

          {/* Decisión actual */}
          {state.current_decision && (
            <div className="space-y-1">
              <p className="text-xs text-white/40 uppercase tracking-wider font-semibold">Decision Engine</p>
              <DecisionCard decision={state.current_decision} />
            </div>
          )}

          {/* Widgets */}
          <div className="space-y-2">
            <p className="text-xs text-white/40 uppercase tracking-wider font-semibold">
              Widgets activos ({state.widgets.filter(w => w.visible).length})
            </p>
            <WidgetsList widgets={state.widgets.filter(w => w.visible)} />
          </div>

          {/* Notificación activa */}
          {state.notification && (
            <div className="p-3 rounded-lg border border-orange-400/30 bg-orange-950/30 space-y-1">
              <p className="text-sm font-semibold text-orange-300">{state.notification.title}</p>
              {state.notification.lines.map((l, i) => (
                <p key={i} className="text-xs text-white/60">{l}</p>
              ))}
            </div>
          )}

          {/* Configurar campeón manualmente */}
          {!state.active && (
            <ChampionSelector onSet={setChampion} />
          )}
        </div>
      )}

      {/* ── Tab: Demo ── */}
      {tab === 'demo' && <DemoPanel />}

      {/* ── Tab: Debug ── */}
      {tab === 'debug' && (
        <Suspense fallback={<div className="text-white/40 text-sm py-8 text-center">Cargando panel...</div>}>
          <DebugPanel />
        </Suspense>
      )}
    </div>
  )
}

function ChampionSelector({ onSet }: { onSet: (champion: string, role: string) => void }) {
  const [champ, setChamp] = useState('')
  const [role, setRole] = useState('TOP')
  const roles = ['TOP', 'JGL', 'MID', 'ADC', 'SUP']

  return (
    <div className="p-4 rounded-lg bg-white/5 border border-white/10 space-y-3">
      <p className="text-xs text-white/50 uppercase tracking-wider">Configurar campeón</p>
      <div className="flex gap-2">
        <input
          type="text"
          value={champ}
          onChange={e => setChamp(e.target.value.toLowerCase())}
          placeholder="tryndamere"
          className="flex-1 bg-black/30 border border-white/20 rounded px-3 py-2 text-sm text-white placeholder:text-white/30 focus:outline-none focus:border-yellow-400/50"
        />
        <select
          value={role}
          onChange={e => setRole(e.target.value)}
          className="bg-black/30 border border-white/20 rounded px-3 py-2 text-sm text-white focus:outline-none focus:border-yellow-400/50"
        >
          {roles.map(r => <option key={r} value={r}>{r}</option>)}
        </select>
        <button
          onClick={() => champ && onSet(champ, role)}
          disabled={!champ.trim()}
          className="px-4 py-2 rounded bg-yellow-400/20 text-yellow-400 border border-yellow-400/30 text-sm font-medium hover:bg-yellow-400/30 disabled:opacity-40 disabled:cursor-not-allowed"
        >
          Aplicar
        </button>
      </div>
    </div>
  )
}

export default LiveCoachPage
