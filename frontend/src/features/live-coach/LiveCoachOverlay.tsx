/**
 * LiveCoachOverlay — ventana de overlay del Live Coach.
 *
 * Se renderiza en la segunda BrowserWindow (transparent, alwaysOnTop).
 * Ruta: /#/overlay
 *
 * Diseño:
 *   - Fondo semitransparente oscuro (#0a0e1a con 85% opacidad)
 *   - Sin bordes ni shadow (la ventana Electron es transparent)
 *   - Draggable desde el header
 *   - Widgets independientes, ordenados por prioridad
 *   - Notificaciones efímeras en la parte superior (highlight)
 */

import { useEffect, useState } from 'react'
import { AnimatePresence } from 'framer-motion'
import { useLiveCoach } from './useLiveCoach'
import { OverlayWidget } from './components/OverlayWidget'
import { OverlayNotification } from './components/OverlayNotification'
import { OverlayHeader } from './components/OverlayHeader'
import { OverlayStatusBar } from './components/OverlayStatusBar'
import type { OverlayConfigData } from './types'
import { API_BASE } from '../../api/client'

export function LiveCoachOverlay() {
  const { state, connected, connectionMode } = useLiveCoach()
  const [config, setConfig] = useState<OverlayConfigData | null>(null)
  const [compact, setCompact] = useState(false)

  // Cargar config del backend
  useEffect(() => {
    fetch(`${API_BASE}/api/v1/live-coach/config`)
      .then(r => r.json())
      .then((cfg: OverlayConfigData) => {
        setConfig(cfg)
        setCompact(cfg.compact_mode)
        // Aplicar opacidad a la ventana Electron
        window.api?.overlay?.setOpacity?.(cfg.opacity)
      })
      .catch(() => {})
  }, [])

  const toggleCompact = () => {
    const next = !compact
    setCompact(next)
    // Persistir
    fetch(`${API_BASE}/api/v1/live-coach/config`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ compact_mode: next }),
    }).catch(() => {})
  }

  // Auto-hide cuando no hay partida activa y config lo pide
  const shouldHide = !state.active && config?.auto_hide_on_idle && !state.provider_connected

  if (shouldHide) {
    return (
      <div className="flex items-center justify-center h-screen bg-transparent">
        <div className="text-[#4a5568] text-xs text-center p-3 bg-[#0a0e1a]/60 rounded-lg">
          <span className="block text-lg mb-1">🎮</span>
          Sin partida activa
        </div>
      </div>
    )
  }

  return (
    <div
      className="h-screen w-full bg-transparent select-none overflow-hidden"
      style={{ fontFamily: 'system-ui, -apple-system, sans-serif' }}
    >
      <div className="flex flex-col h-full">
        {/* Header draggable */}
        <OverlayHeader
          champion={state.champion}
          role={state.role}
          compact={compact}
          connected={connected}
          onToggleCompact={toggleCompact}
        />

        {/* Notificación prioritaria (efímera) */}
        <AnimatePresence>
          {state.notification && (
            <OverlayNotification
              key={state.notification.title + state.notification.lines.join()}
              notification={state.notification}
            />
          )}
        </AnimatePresence>

        {/* Widgets */}
        {!compact && (
          <div className="flex-1 overflow-y-auto scrollbar-hide px-2 py-1 space-y-1">
            <AnimatePresence>
              {state.widgets
                .filter(w => w.visible)
                .sort((a, b) => b.priority - a.priority)
                .map(widget => (
                  <OverlayWidget key={widget.id} widget={widget} />
                ))}
            </AnimatePresence>
          </div>
        )}

        {/* Barra de estado */}
        <OverlayStatusBar
          phase={state.phase}
          game_time={state.game_time}
          player={state.player}
          connectionMode={connectionMode}
        />
      </div>
    </div>
  )
}
