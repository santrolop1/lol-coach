/**
 * OverlayStatusBar — barra inferior del overlay.
 * Muestra tiempo de partida, KDA rápido y estado de conexión.
 */

import type { PlayerSnapshot } from '../types'

interface Props {
  phase: string
  game_time: number
  player: PlayerSnapshot
  connectionMode: 'ws' | 'poll' | 'offline'
}

function formatTime(seconds: number): string {
  const m = Math.floor(seconds / 60)
  const s = Math.floor(seconds % 60)
  return `${m}:${s.toString().padStart(2, '0')}`
}

const CONNECTION_LABELS = {
  ws:      { label: 'WS', color: 'text-green-400' },
  poll:    { label: 'REST', color: 'text-yellow-400' },
  offline: { label: '–', color: 'text-[#4a5568]' },
}

export function OverlayStatusBar({ phase, game_time, player, connectionMode }: Props) {
  const { label, color } = CONNECTION_LABELS[connectionMode]

  return (
    <div className="flex items-center justify-between px-3 py-1.5 bg-[#0d1117]/90 border-t border-[#1e3a5f]/40 rounded-b-lg">
      <div className="flex items-center gap-2 text-[10px] text-[#4a5568]">
        {phase === 'in_game' && game_time > 0 && (
          <span className="text-[#718096]">{formatTime(game_time)}</span>
        )}
        {(player.kills > 0 || player.deaths > 0 || player.assists > 0) && (
          <span>
            <span className="text-green-400">{player.kills}</span>
            <span className="text-[#4a5568]">/</span>
            <span className="text-red-400">{player.deaths}</span>
            <span className="text-[#4a5568]">/</span>
            <span className="text-blue-400">{player.assists}</span>
          </span>
        )}
        {player.cs > 0 && (
          <span className="text-[#718096]">{player.cs} CS</span>
        )}
      </div>

      <span className={`text-[10px] font-mono ${color}`} title={`Modo: ${connectionMode}`}>
        {label}
      </span>
    </div>
  )
}
