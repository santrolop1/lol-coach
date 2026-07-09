/**
 * OverlayHeader — barra superior del overlay, draggable.
 *
 * -webkit-app-region: drag permite mover la ventana sin bordes nativos.
 */

interface Props {
  champion: string
  role: string
  compact: boolean
  connected: boolean
  onToggleCompact: () => void
}

export function OverlayHeader({ champion, role, compact, connected, onToggleCompact }: Props) {
  const title = champion
    ? `${champion.charAt(0).toUpperCase() + champion.slice(1)} ${role}`
    : 'LoL Coach'

  return (
    <div
      className="flex items-center justify-between px-3 py-2 bg-[#0d1117]/90 border-b border-[#1e3a5f]/60 rounded-t-lg"
      style={{ WebkitAppRegion: 'drag' } as React.CSSProperties}
    >
      <div className="flex items-center gap-2">
        <span className="text-[#c89b3c] text-xs font-bold tracking-wide">
          {title}
        </span>
        {connected && (
          <span className="w-1.5 h-1.5 rounded-full bg-green-400 animate-pulse" title="Conectado" />
        )}
      </div>

      {/* Botón compact — no draggable */}
      <button
        onClick={onToggleCompact}
        className="text-[#4a5568] hover:text-[#c89b3c] text-xs transition-colors"
        style={{ WebkitAppRegion: 'no-drag' } as React.CSSProperties}
        title={compact ? 'Expandir' : 'Compactar'}
      >
        {compact ? '▼' : '▲'}
      </button>
    </div>
  )
}
