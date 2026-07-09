/**
 * DemoPanel — Demo Mode + Simulador de eventos.
 * Permite probar el Live Coach sin tener League of Legends abierto.
 */

import { useState } from 'react'
import { useDemoMode } from './hooks/useDemoMode'
import type { DemoScenario } from './types'

const DEMO_EVENTS = [
  { label: 'Level Up (→ 6)',   type: 'LEVEL_UP',        data: { level: 6, previous: 5 } },
  { label: 'Muerte',           type: 'DEATH',            data: { deaths: 1 } },
  { label: 'Respawn',          type: 'RESPAWN',          data: {} },
  { label: 'Ítem comprado',    type: 'ITEM_PURCHASED',   data: { item: 'trinity_force' } },
  { label: 'First Blood',      type: 'FIRST_BLOOD',      data: {} },
  { label: 'Torre destruida',  type: 'TOWER_DESTROYED',  data: { team: 'ORDER' } },
  { label: 'Objetivo tomado',  type: 'OBJECTIVE_TAKEN',  data: { type: 'dragon' } },
  { label: 'Recall',           type: 'RECALL',           data: {} },
  { label: 'Victoria',         type: 'VICTORY',          data: {} },
  { label: 'Derrota',          type: 'DEFEAT',           data: {} },
]

const PHASE_BADGE: Record<string, { label: string; color: string }> = {
  in_game:   { label: 'En partida', color: 'bg-green-500/20 text-green-400 border-green-500/30' },
  post_game: { label: 'Post-partida', color: 'bg-blue-500/20 text-blue-400 border-blue-500/30' },
  idle:      { label: 'Inactivo', color: 'bg-zinc-500/20 text-zinc-400 border-zinc-500/30' },
  loading:   { label: 'Cargando', color: 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30' },
}

interface ScenarioButtonProps {
  scenario: DemoScenario
  onClick: () => void
  disabled: boolean
}

function ScenarioButton({ scenario, onClick, disabled }: ScenarioButtonProps) {
  const phase = PHASE_BADGE[scenario.phase] ?? PHASE_BADGE.idle
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      className={`
        w-full text-left p-3 rounded-lg border transition-all
        ${scenario.current
          ? 'border-yellow-400/60 bg-yellow-400/10 ring-1 ring-yellow-400/30'
          : 'border-white/10 bg-white/5 hover:bg-white/10 hover:border-white/20'}
        disabled:opacity-40 disabled:cursor-not-allowed
      `}
    >
      <div className="flex items-center justify-between gap-2 mb-1">
        <span className="text-sm font-medium text-white">{scenario.label}</span>
        <span className={`text-xs px-1.5 py-0.5 rounded border ${phase.color}`}>
          {phase.label}
        </span>
      </div>
      <p className="text-xs text-white/50 leading-snug">{scenario.description}</p>
    </button>
  )
}

export function DemoPanel() {
  const { isActive, scenarios, activate, deactivate, setScenario, fireEvent, isPending } = useDemoMode()
  const [champion, setChampion] = useState('tryndamere')
  const [lastEvent, setLastEvent] = useState<string | null>(null)

  const handleActivate = () => {
    activate({ champion, scenario: 'early_game' })
  }

  const handleScenario = (id: string) => {
    if (!isActive) return
    setScenario({ scenario: id, champion })
  }

  const handleEvent = (type: string, data: Record<string, unknown>) => {
    fireEvent({ event_type: type, data })
    setLastEvent(type)
    setTimeout(() => setLastEvent(null), 2000)
  }

  return (
    <div className="space-y-6">
      {/* Header + toggle */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-semibold text-white">Demo Mode</h2>
          <p className="text-sm text-white/50">Simula partidas sin League of Legends</p>
        </div>
        <div className="flex items-center gap-3">
          {isActive && (
            <span className="text-xs px-2 py-1 rounded-full bg-green-500/20 text-green-400 border border-green-500/30 animate-pulse">
              ACTIVO
            </span>
          )}
          <button
            onClick={isActive ? () => deactivate() : handleActivate}
            disabled={isPending}
            className={`
              px-4 py-2 rounded-lg text-sm font-medium transition-all
              ${isActive
                ? 'bg-red-500/20 text-red-400 border border-red-500/30 hover:bg-red-500/30'
                : 'bg-yellow-400/20 text-yellow-400 border border-yellow-400/30 hover:bg-yellow-400/30'}
              disabled:opacity-40 disabled:cursor-not-allowed
            `}
          >
            {isPending ? '...' : isActive ? 'Desactivar' : 'Activar Demo'}
          </button>
        </div>
      </div>

      {/* Selector de campeón */}
      {!isActive && (
        <div className="p-4 rounded-lg bg-white/5 border border-white/10 space-y-2">
          <label className="text-xs text-white/50 uppercase tracking-wider">Campeón</label>
          <input
            type="text"
            value={champion}
            onChange={e => setChampion(e.target.value.toLowerCase())}
            placeholder="tryndamere"
            className="w-full bg-black/30 border border-white/20 rounded px-3 py-2 text-sm text-white placeholder:text-white/30 focus:outline-none focus:border-yellow-400/50"
          />
        </div>
      )}

      {/* Escenarios */}
      <div className="space-y-2">
        <h3 className="text-xs font-semibold text-white/50 uppercase tracking-wider">Escenarios</h3>
        <div className="grid grid-cols-1 gap-2 max-h-80 overflow-y-auto pr-1">
          {scenarios.map(s => (
            <ScenarioButton
              key={s.id}
              scenario={s}
              onClick={() => handleScenario(s.id)}
              disabled={!isActive || isPending}
            />
          ))}
        </div>
      </div>

      {/* Simulador de eventos */}
      {isActive && (
        <div className="space-y-3">
          <h3 className="text-xs font-semibold text-white/50 uppercase tracking-wider">
            Disparar evento
          </h3>
          {lastEvent && (
            <p className="text-xs text-green-400 bg-green-400/10 border border-green-400/20 rounded px-2 py-1">
              ✓ Evento disparado: {lastEvent}
            </p>
          )}
          <div className="grid grid-cols-2 gap-2">
            {DEMO_EVENTS.map(ev => (
              <button
                key={ev.type}
                onClick={() => handleEvent(ev.type, ev.data)}
                className="px-3 py-2 rounded-lg border border-white/10 bg-white/5 hover:bg-white/10 text-xs text-white/80 text-left transition-all"
              >
                {ev.label}
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
