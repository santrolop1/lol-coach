import { useState } from 'react'
import { Loader2, AlertCircle } from 'lucide-react'
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter
} from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { useChangeAccount } from '@/features/settings/hooks/useApiKey'
import { toast } from '@/components/ui/use-toast'
import { cn } from '@/lib/utils'

interface AccountChangeModalProps {
  open:           boolean
  onClose:        () => void
  currentPlatform?: string
}

const PLATFORMS: { label: string; value: string }[] = [
  { label: 'Latinoamérica Norte (LA1)', value: 'la1' },
  { label: 'Latinoamérica Sur (LA2)',   value: 'la2' },
  { label: 'Norteamérica (NA1)',        value: 'na1' },
  { label: 'Europa Oeste (EUW1)',       value: 'euw1' },
  { label: 'Europa Norte/Este (EUN1)',  value: 'eun1' },
  { label: 'Brasil (BR1)',              value: 'br1' },
  { label: 'Corea (KR)',                value: 'kr' },
  { label: 'Japón (JP1)',               value: 'jp1' },
  { label: 'Oceanía (OC1)',             value: 'oc1' },
]

export function AccountChangeModal({ open, onClose, currentPlatform }: AccountChangeModalProps) {
  const [gameName, setGameName] = useState('')
  const [tagLine,  setTagLine]  = useState('')
  const [platform, setPlatform] = useState(currentPlatform ?? 'la1')
  const [serverError, setServerError] = useState<string | null>(null)

  const changeAccount = useChangeAccount()

  async function handleSave() {
    if (!gameName.trim() || !tagLine.trim()) return
    setServerError(null)

    try {
      const res = await changeAccount.mutateAsync({
        game_name: gameName.trim(),
        tag_line:  tagLine.trim().replace(/^#/, ''),
        platform,
      })
      toast({ title: '✓ Cuenta actualizada', description: `${res.riot_id}#${res.tag}` })
      setGameName('')
      setTagLine('')
      onClose()
    } catch (err: unknown) {
      const msg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail
        ?? 'No se pudo cambiar de cuenta. Verificá el Riot ID.'
      setServerError(msg)
    }
  }

  function handleOpenChange(next: boolean) {
    if (!next) {
      setGameName('')
      setTagLine('')
      setServerError(null)
      onClose()
    }
  }

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Cambiar de cuenta</DialogTitle>
          <DialogDescription className="text-muted-foreground text-sm">
            La cuenta activa no se sincroniza automáticamente con el cliente de League. Ingresá el Riot ID al que querés cambiar.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-3 py-2">
          <div className="flex gap-2">
            <div className="flex-1 space-y-1.5">
              <label htmlFor="game-name" className="text-sm font-medium">Nombre de invocador</label>
              <input
                id="game-name"
                type="text"
                value={gameName}
                onChange={(e) => { setGameName(e.target.value); setServerError(null) }}
                placeholder="Lil Rionuske"
                autoComplete="off"
                disabled={changeAccount.isPending}
                className={cn(
                  'w-full rounded-lg border bg-background px-3 py-2 text-sm',
                  'outline-none transition-colors border-border focus:border-primary/60',
                  'disabled:opacity-50'
                )}
              />
            </div>
            <div className="w-24 space-y-1.5">
              <label htmlFor="tag-line" className="text-sm font-medium">Tag</label>
              <input
                id="tag-line"
                type="text"
                value={tagLine}
                onChange={(e) => { setTagLine(e.target.value); setServerError(null) }}
                placeholder="DMT"
                autoComplete="off"
                disabled={changeAccount.isPending}
                className={cn(
                  'w-full rounded-lg border bg-background px-3 py-2 text-sm',
                  'outline-none transition-colors border-border focus:border-primary/60',
                  'disabled:opacity-50'
                )}
              />
            </div>
          </div>

          <div className="space-y-1.5">
            <label htmlFor="platform" className="text-sm font-medium">Plataforma</label>
            <select
              id="platform"
              value={platform}
              onChange={(e) => setPlatform(e.target.value)}
              disabled={changeAccount.isPending}
              className={cn(
                'w-full rounded-lg border bg-background px-3 py-2 text-sm',
                'outline-none transition-colors border-border focus:border-primary/60',
                'disabled:opacity-50'
              )}
            >
              {PLATFORMS.map((p) => (
                <option key={p.value} value={p.value}>{p.label}</option>
              ))}
            </select>
          </div>

          {serverError && (
            <p className="flex items-start gap-1.5 text-xs text-destructive leading-relaxed">
              <AlertCircle className="h-3.5 w-3.5 mt-0.5 shrink-0" /> {serverError}
            </p>
          )}
        </div>

        <DialogFooter className="flex-col gap-2 sm:flex-row sm:justify-end sm:items-center">
          <div className="flex gap-2 w-full sm:w-auto">
            <Button
              variant="outline"
              size="sm"
              onClick={onClose}
              disabled={changeAccount.isPending}
              className="flex-1 sm:flex-none"
            >
              Cancelar
            </Button>
            <Button
              size="sm"
              onClick={handleSave}
              disabled={changeAccount.isPending || !gameName.trim() || !tagLine.trim()}
              className="flex-1 sm:flex-none"
            >
              {changeAccount.isPending && <Loader2 className="h-3.5 w-3.5 animate-spin" />}
              {changeAccount.isPending ? 'Verificando…' : 'Cambiar cuenta'}
            </Button>
          </div>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
