import { useState } from 'react'
import { motion } from 'framer-motion'
import { RefreshCw, Loader2, UserCog, Wifi } from 'lucide-react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { apiClient } from '@/api/client'
import type { SettingsResponse } from '@/api/types'
import { Button } from '@/components/ui/button'
import { Badge }  from '@/components/ui/badge'
import { Separator } from '@/components/ui/separator'
import { Skeleton } from '@/components/ui/skeleton'
import { useAppStore } from '@/store/appStore'
import { toast } from '@/components/ui/use-toast'
import { ApiKeySection } from '@/features/settings/components/ApiKeySection'
import { AccountChangeModal } from '@/features/settings/components/AccountChangeModal'
import { useDetectFromLcu } from '@/features/settings/hooks/useApiKey'

const FADE_UP = {
  hidden:  { opacity: 0, y: 10 },
  visible: (i: number) => ({ opacity: 1, y: 0, transition: { delay: i * 0.07 } })
}

export default function SettingsPage() {
  const queryClient                  = useQueryClient()
  const { theme, setTheme }          = useAppStore()
  const [accountModalOpen, setAccountModalOpen] = useState(false)
  const detectLcu = useDetectFromLcu()

  async function handleDetectLcu() {
    try {
      const res = await detectLcu.mutateAsync()
      if (res.status === 'updated') {
        toast({ title: `✓ Cuenta detectada: ${res.riot_id}#${res.tag}` })
        queryClient.invalidateQueries({ queryKey: ['settings'] })
      } else if (res.status === 'already_synced') {
        toast({ title: 'Ya estás sincronizado', description: res.message })
      } else {
        toast({ title: 'No se pudo detectar', description: res.message, variant: 'destructive' })
      }
    } catch {
      toast({ title: 'Error al detectar cuenta', variant: 'destructive' })
    }
  }

  const { data, isLoading } = useQuery<SettingsResponse>({
    queryKey: ['settings'],
    queryFn:  () => apiClient.get<SettingsResponse>('/settings').then((r) => r.data)
  })

  const syncMutation = useMutation({
    mutationFn: () => apiClient.post('/settings/sync').then((r) => r.data),
    onSuccess:  (res) => {
      queryClient.invalidateQueries({ queryKey: ['dashboard'] })
      toast({ title: 'Sincronización completada', description: `${res.saved ?? 0} partidas guardadas` })
    },
    onError: () => {
      toast({ title: 'Error al sincronizar', variant: 'destructive' })
    }
  })

  if (isLoading) return <SettingsSkeleton />

  return (
    <div className="p-6 max-w-2xl space-y-8">
      {/* Cuenta */}
      <motion.section variants={FADE_UP} initial="hidden" animate="visible" custom={0} className="space-y-4">
        <div>
          <h2 className="text-sm font-semibold uppercase tracking-widest text-muted-foreground">Cuenta</h2>
        </div>
        <div className="surface p-5 space-y-4">
          <Row label="Invocador">
            <div className="flex items-center gap-2">
              {data?.riot_id
                ? <span className="font-medium">{data.riot_id}<span className="text-muted-foreground">#{data.tag}</span></span>
                : <Badge variant="warning">No configurado</Badge>
              }
              <Button
                variant="ghost"
                size="sm"
                onClick={handleDetectLcu}
                disabled={detectLcu.isPending}
                title="Detectar cuenta desde el cliente de League"
                className="text-muted-foreground hover:text-emerald-400 h-7 px-2"
              >
                {detectLcu.isPending
                  ? <Loader2 className="h-3.5 w-3.5 animate-spin" />
                  : <Wifi className="h-3.5 w-3.5" />
                }
                Detectar
              </Button>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setAccountModalOpen(true)}
                className="text-muted-foreground hover:text-foreground h-7 px-2"
              >
                <UserCog className="h-3.5 w-3.5" />
                Cambiar
              </Button>
            </div>
          </Row>
          <Separator />
          <Row label="Plataforma">
            <span className="text-sm text-muted-foreground">{data?.platform_name ?? '—'}</span>
          </Row>
          <Separator />
          <Row label="Nivel">
            <span className="text-sm">{data?.level ?? '—'}</span>
          </Row>
          <Separator />
          <Row label="Rango">
            {data?.rank
              ? <Badge variant="secondary">{data.rank} · {data.lp} LP</Badge>
              : <span className="text-sm text-muted-foreground">Sin clasificar</span>
            }
          </Row>
          <Separator />
          <ApiKeySection />
        </div>
      </motion.section>

      {/* Datos */}
      <motion.section variants={FADE_UP} initial="hidden" animate="visible" custom={1} className="space-y-4">
        <h2 className="text-sm font-semibold uppercase tracking-widest text-muted-foreground">Datos</h2>
        <div className="surface p-5">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium">Sincronizar partidas</p>
              <p className="text-xs text-muted-foreground mt-0.5">Descarga las últimas 50 partidas desde Riot API</p>
            </div>
            <Button
              variant="outline"
              size="sm"
              onClick={() => syncMutation.mutate()}
              disabled={syncMutation.isPending || !data?.is_configured}
            >
              {syncMutation.isPending
                ? <Loader2 className="h-4 w-4 animate-spin" />
                : <RefreshCw className="h-4 w-4" />
              }
              Sincronizar
            </Button>
          </div>
        </div>
      </motion.section>

      {/* Apariencia */}
      <motion.section variants={FADE_UP} initial="hidden" animate="visible" custom={2} className="space-y-4">
        <h2 className="text-sm font-semibold uppercase tracking-widest text-muted-foreground">Apariencia</h2>
        <div className="surface p-5">
          <Row label="Tema">
            <div className="flex gap-2">
              {(['dark', 'light'] as const).map((t) => (
                <Button
                  key={t}
                  variant={theme === t ? 'default' : 'outline'}
                  size="sm"
                  onClick={() => setTheme(t)}
                >
                  {t === 'dark' ? 'Oscuro' : 'Claro'}
                </Button>
              ))}
            </div>
          </Row>
        </div>
      </motion.section>

      <AccountChangeModal
        open={accountModalOpen}
        onClose={() => setAccountModalOpen(false)}
        currentPlatform={data?.platform ?? undefined}
      />
    </div>
  )
}

function Row({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex items-center justify-between py-0.5">
      <span className="text-sm text-muted-foreground">{label}</span>
      {children}
    </div>
  )
}

function SettingsSkeleton() {
  return (
    <div className="p-6 max-w-2xl space-y-8">
      {[0,1,2].map((i) => (
        <div key={i} className="space-y-4">
          <Skeleton className="h-3 w-24" />
          <div className="surface p-5 space-y-4">
            {[0,1,2].map(j => <Skeleton key={j} className="h-8" />)}
          </div>
        </div>
      ))}
    </div>
  )
}
