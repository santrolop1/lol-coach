import { useState } from 'react'
import { Eye, EyeOff, ExternalLink, Loader2, CheckCircle2, AlertCircle } from 'lucide-react'
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter
} from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { useSaveApiKey, useSyncMatches } from '@/features/settings/hooks/useApiKey'
import { toast } from '@/components/ui/use-toast'
import { cn } from '@/lib/utils'

interface ApiKeyModalProps {
  open:       boolean
  onClose:    () => void
  onSuccess?: () => void
}

type FieldState = 'idle' | 'valid' | 'invalid'

export function ApiKeyModal({ open, onClose, onSuccess }: ApiKeyModalProps) {
  const [value,     setValue]     = useState('')
  const [showKey,   setShowKey]   = useState(false)
  const [fieldState, setFieldState] = useState<FieldState>('idle')
  const [serverError, setServerError] = useState<string | null>(null)

  const saveKey  = useSaveApiKey()
  const syncNow  = useSyncMatches()

  const isPending = saveKey.isPending || syncNow.isPending

  function handleChange(e: React.ChangeEvent<HTMLInputElement>) {
    const v = e.target.value
    setValue(v)
    setServerError(null)
    if (v.length === 0) {
      setFieldState('idle')
    } else if (/^RGAPI-[0-9a-f\-]{8,}$/i.test(v.trim())) {
      setFieldState('valid')
    } else {
      setFieldState('invalid')
    }
  }

  async function handleSave() {
    if (!value.trim() || fieldState === 'invalid') return
    setServerError(null)

    try {
      await saveKey.mutateAsync(value.trim())
      // Sincronización automática después de guardar exitosamente
      try {
        await syncNow.mutateAsync()
      } catch {
        // la sync puede fallar sin bloquear el flujo
      }
      toast({ title: '✓ Riot API configurada', description: 'Sincronización iniciada automáticamente.' })
      setValue('')
      setFieldState('idle')
      onSuccess?.()
      onClose()
    } catch (err: unknown) {
      const msg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail
        ?? 'Error al validar la key. Comprueba que sea correcta.'
      setServerError(msg)
      setFieldState('invalid')
    }
  }

  function handleOpenChange(next: boolean) {
    if (!next) {
      setValue('')
      setFieldState('idle')
      setServerError(null)
      onClose()
    }
  }

  function openRiotDev() {
    // Electron: abre en el navegador del sistema, no en Electron
    if (window.api?.app) {
      window.api.app.openExternal?.('https://developer.riotgames.com/')
    } else {
      window.open('https://developer.riotgames.com/', '_blank', 'noopener')
    }
  }

  const inputBorder =
    fieldState === 'valid'   ? 'border-emerald-500/60 focus:border-emerald-500' :
    fieldState === 'invalid' ? 'border-destructive/60 focus:border-destructive' :
    'border-border focus:border-primary/60'

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Configurar Riot API</DialogTitle>
          <DialogDescription className="text-muted-foreground text-sm">
            Las Riot Developer API Keys expiran aproximadamente cada 24 horas.
          </DialogDescription>
        </DialogHeader>

        {/* Campo de key */}
        <div className="space-y-2 py-2">
          <label htmlFor="apikey" className="text-sm font-medium">
            API Key
          </label>
          <div className="relative">
            <input
              id="apikey"
              type={showKey ? 'text' : 'password'}
              value={value}
              onChange={handleChange}
              onKeyDown={(e) => e.key === 'Enter' && handleSave()}
              placeholder="RGAPI-xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
              autoComplete="off"
              spellCheck={false}
              disabled={isPending}
              className={cn(
                'w-full rounded-lg border bg-background px-3 py-2 pr-10',
                'text-sm font-mono placeholder:text-muted-foreground/40',
                'outline-none transition-colors',
                'disabled:opacity-50',
                inputBorder
              )}
            />
            <button
              type="button"
              onClick={() => setShowKey((p) => !p)}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground transition-colors"
              tabIndex={-1}
              aria-label={showKey ? 'Ocultar key' : 'Mostrar key'}
            >
              {showKey ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
            </button>
          </div>

          {/* Validación visual inline */}
          {fieldState === 'valid' && (
            <p className="flex items-center gap-1.5 text-xs text-emerald-400">
              <CheckCircle2 className="h-3.5 w-3.5" /> Formato correcto
            </p>
          )}
          {fieldState === 'invalid' && !serverError && (
            <p className="flex items-center gap-1.5 text-xs text-destructive">
              <AlertCircle className="h-3.5 w-3.5" /> El formato no es válido. Debe comenzar con RGAPI-
            </p>
          )}
          {serverError && (
            <p className="flex items-start gap-1.5 text-xs text-destructive leading-relaxed">
              <AlertCircle className="h-3.5 w-3.5 mt-0.5 shrink-0" /> {serverError}
            </p>
          )}
        </div>

        <DialogFooter className="flex-col gap-2 sm:flex-row sm:justify-between sm:items-center">
          {/* Obtener key — abre navegador */}
          <Button
            variant="ghost"
            size="sm"
            type="button"
            onClick={openRiotDev}
            className="text-muted-foreground hover:text-foreground text-xs w-full sm:w-auto justify-start"
          >
            <ExternalLink className="h-3.5 w-3.5" />
            Obtener Riot API Key
          </Button>

          <div className="flex gap-2 w-full sm:w-auto">
            <Button
              variant="outline"
              size="sm"
              onClick={onClose}
              disabled={isPending}
              className="flex-1 sm:flex-none"
            >
              Cancelar
            </Button>
            <Button
              size="sm"
              onClick={handleSave}
              disabled={isPending || !value.trim() || fieldState === 'invalid'}
              className="flex-1 sm:flex-none"
            >
              {isPending && <Loader2 className="h-3.5 w-3.5 animate-spin" />}
              {isPending ? (syncNow.isPending ? 'Sincronizando…' : 'Validando…') : 'Guardar'}
            </Button>
          </div>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
