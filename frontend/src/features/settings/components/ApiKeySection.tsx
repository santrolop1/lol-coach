import { useState } from 'react'
import { KeyRound, RefreshCw, Trash2, Clock } from 'lucide-react'
import { Button }   from '@/components/ui/button'
import { Badge }    from '@/components/ui/badge'
import { Skeleton } from '@/components/ui/skeleton'
import { ApiKeyModal } from './ApiKeyModal'
import { useApiKeyStatus, useDeleteApiKey } from '@/features/settings/hooks/useApiKey'
import { toast } from '@/components/ui/use-toast'

// ── Status badge ───────────────────────────────────────────────────────────────

type ApiKeyStatus = 'active' | 'expiring_soon' | 'expired' | 'not_configured'

const STATUS_BADGE: Record<ApiKeyStatus, { label: string; variant: 'success' | 'warning' | 'destructive' | 'secondary' }> = {
  active:          { label: 'Activa',               variant: 'success'     },
  expiring_soon:   { label: 'Próxima a expirar',    variant: 'warning'     },
  expired:         { label: 'Expirada',             variant: 'destructive' },
  not_configured:  { label: 'No configurada',       variant: 'secondary'   },
}

function StatusBadge({ status }: { status: ApiKeyStatus }) {
  const { label, variant } = STATUS_BADGE[status]
  return <Badge variant={variant}>{label}</Badge>
}

function formatSavedAt(isoStr: string | null, hoursOld: number | null): string {
  if (!isoStr) return ''
  if (hoursOld != null) {
    if (hoursOld < 1)   return 'hace menos de 1 hora'
    if (hoursOld < 24)  return `hace ${Math.floor(hoursOld)}h`
    return `hace ${Math.floor(hoursOld / 24)} días`
  }
  try {
    return new Date(isoStr).toLocaleString('es', { dateStyle: 'short', timeStyle: 'short' })
  } catch {
    return ''
  }
}

// ── Main component ─────────────────────────────────────────────────────────────

export function ApiKeySection() {
  const [modalOpen, setModalOpen] = useState(false)
  const { data, isLoading }  = useApiKeyStatus()
  const deleteKey = useDeleteApiKey()

  async function handleDelete() {
    if (!confirm('¿Eliminar la API key guardada?')) return
    try {
      await deleteKey.mutateAsync()
      toast({ title: 'API key eliminada.' })
    } catch {
      toast({ title: 'Error al eliminar la key.', variant: 'destructive' })
    }
  }

  const status = (data?.status ?? 'not_configured') as ApiKeyStatus
  const isConfigured = data?.configured ?? false
  const buttonLabel  =
    status === 'not_configured' ? 'Configurar' :
    status === 'expired'        ? 'Actualizar' :
    'Reemplazar'

  if (isLoading) {
    return (
      <div className="flex items-center justify-between py-1">
        <div className="space-y-1.5">
          <Skeleton className="h-4 w-20" />
          <Skeleton className="h-3 w-32" />
        </div>
        <Skeleton className="h-8 w-24 rounded-lg" />
      </div>
    )
  }

  return (
    <>
      <div className="space-y-3">
        {/* Row principal */}
        <div className="flex items-start justify-between gap-4">
          <div className="flex items-start gap-2.5">
            <div className="mt-0.5 rounded-md bg-muted/50 p-1.5 shrink-0">
              <KeyRound className="h-3.5 w-3.5 text-muted-foreground" />
            </div>
            <div className="space-y-1">
              <div className="flex items-center gap-2 flex-wrap">
                <span className="text-sm font-medium">Riot API</span>
                <StatusBadge status={status} />
              </div>
              {isConfigured && data?.masked_key && (
                <p className="text-xs font-mono text-muted-foreground tracking-wider">
                  {data.masked_key}
                </p>
              )}
              {isConfigured && data?.saved_at && (
                <p className="flex items-center gap-1 text-xs text-muted-foreground/60">
                  <Clock className="h-3 w-3" />
                  Actualizada {formatSavedAt(data.saved_at, data.hours_old ?? null)}
                  {(data.hours_old ?? 0) >= 20 && (
                    <span className="text-yellow-400 ml-1">· Renovar pronto</span>
                  )}
                </p>
              )}
            </div>
          </div>

          {/* Acciones */}
          <div className="flex items-center gap-1.5 shrink-0">
            <Button
              variant={status === 'expired' || status === 'not_configured' ? 'default' : 'outline'}
              size="sm"
              onClick={() => setModalOpen(true)}
            >
              {status === 'expired'
                ? <><RefreshCw className="h-3.5 w-3.5" />{buttonLabel}</>
                : buttonLabel
              }
            </Button>
            {isConfigured && (
              <Button
                variant="ghost"
                size="sm"
                onClick={handleDelete}
                disabled={deleteKey.isPending}
                aria-label="Eliminar API key"
                className="text-muted-foreground hover:text-destructive"
              >
                <Trash2 className="h-3.5 w-3.5" />
              </Button>
            )}
          </div>
        </div>

        {/* Alerta expirada */}
        {status === 'expired' && (
          <div className="rounded-lg border border-destructive/20 bg-destructive/10 px-3 py-2.5">
            <p className="text-xs text-destructive leading-relaxed">
              La API key ha expirado. Genera una nueva en{' '}
              <button
                className="underline underline-offset-2 hover:no-underline"
                onClick={() => setModalOpen(true)}
              >
                developer.riotgames.com
              </button>{' '}
              y actualízala aquí.
            </p>
          </div>
        )}

        {/* Alerta expirando pronto */}
        {status === 'expiring_soon' && (
          <div className="rounded-lg border border-yellow-500/20 bg-yellow-500/10 px-3 py-2.5">
            <p className="text-xs text-yellow-300 leading-relaxed">
              Esta key lleva más de 20 horas activa y podría expirar pronto. Considera renovarla.
            </p>
          </div>
        )}
      </div>

      <ApiKeyModal
        open={modalOpen}
        onClose={() => setModalOpen(false)}
      />
    </>
  )
}
