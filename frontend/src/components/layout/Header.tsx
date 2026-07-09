import { useLocation } from 'react-router-dom'
import { Minus, Square, X, Sun, Moon } from 'lucide-react'
import { useAppStore } from '@/store/appStore'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'

const PAGE_LABELS: Record<string, string> = {
  '/':         'Dashboard',
  '/coaching': 'Coaching',
  '/matches':  'Partidas',
  '/draft':    'Draft',
  '/settings': 'Ajustes'
}

function WindowControls() {
  const isMac = typeof window !== 'undefined' && navigator.platform.startsWith('Mac')
  if (isMac) return null

  return (
    <div className="flex items-center no-drag">
      <button
        onClick={() => window.api?.window.minimize()}
        className="flex h-8 w-11 items-center justify-center text-muted-foreground/60 hover:text-foreground hover:bg-secondary transition-colors"
      >
        <Minus className="h-3 w-3" />
      </button>
      <button
        onClick={() => window.api?.window.maximize()}
        className="flex h-8 w-11 items-center justify-center text-muted-foreground/60 hover:text-foreground hover:bg-secondary transition-colors"
      >
        <Square className="h-3 w-3" />
      </button>
      <button
        onClick={() => window.api?.window.close()}
        className="flex h-8 w-11 items-center justify-center text-muted-foreground/60 hover:text-white hover:bg-red-500 transition-colors"
      >
        <X className="h-3.5 w-3.5" />
      </button>
    </div>
  )
}

export function Header() {
  const location   = useLocation()
  const { playerName, playerRank, playerLp, theme, setTheme, backendStatus } = useAppStore()
  const pageLabel  = PAGE_LABELS[location.pathname] ?? ''

  return (
    <header className="drag-region flex h-14 shrink-0 items-center justify-between border-b border-border bg-card/50 backdrop-blur-sm px-4">
      {/* Título de página */}
      <div className="flex items-center gap-3 no-drag">
        <h1 className="text-sm font-semibold text-foreground">{pageLabel}</h1>
        {backendStatus !== 'connected' && (
          <Badge variant="warning" className="text-xs">
            {backendStatus === 'connecting' ? 'Conectando…' : 'Sin conexión'}
          </Badge>
        )}
      </div>

      {/* Centro: info del jugador */}
      {playerName && (
        <div className="absolute left-1/2 -translate-x-1/2 flex items-center gap-2 no-drag">
          <span className="text-xs font-medium text-foreground">{playerName}</span>
          {playerRank && (
            <span className="text-xs text-muted-foreground">
              {playerRank}{playerLp != null ? ` · ${playerLp} LP` : ''}
            </span>
          )}
        </div>
      )}

      {/* Derecha: controles */}
      <div className="flex items-center gap-1 no-drag">
        <Button
          variant="ghost"
          size="icon"
          className="h-8 w-8"
          onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')}
        >
          {theme === 'dark'
            ? <Sun className="h-4 w-4 text-muted-foreground" />
            : <Moon className="h-4 w-4 text-muted-foreground" />
          }
        </Button>
      </div>

      <WindowControls />
    </header>
  )
}
