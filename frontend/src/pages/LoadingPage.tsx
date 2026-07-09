import { useEffect, useState, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import { CheckCircle2, XCircle, Loader2, RefreshCw } from 'lucide-react'
import { apiClient, isNetworkError } from '@/api/client'
import type { HealthResponse } from '@/api/types'
import { useAppStore } from '@/store/appStore'
import { Button } from '@/components/ui/button'

type CheckStatus = 'pending' | 'ok' | 'error'

interface StatusCheck {
  id:     string
  label:  string
  status: CheckStatus
}

const POLL_INTERVAL = 1500
const MAX_RETRIES   = 20

export default function LoadingPage() {
  const navigate = useNavigate()
  const { setBackendStatus, setLcuConnected } = useAppStore()
  const [checks, setChecks] = useState<StatusCheck[]>([
    { id: 'backend', label: 'Backend FastAPI',      status: 'pending' },
    { id: 'db',      label: 'Base de datos SQLite', status: 'pending' },
    { id: 'riot',    label: 'Riot API configurada', status: 'pending' }
  ])
  const [failed,  setFailed]  = useState(false)
  const retriesRef = useRef(0)
  // timer almacenado en un objeto para evitar el readonly de React.RefObject
  const timer = useRef<{ id: ReturnType<typeof setTimeout> | null }>({ id: null })

  function setCheck(id: string, status: CheckStatus) {
    setChecks((prev) => prev.map((c) => c.id === id ? { ...c, status } : c))
  }

  function schedule(fn: () => void, ms: number) {
    if (timer.current.id) clearTimeout(timer.current.id)
    timer.current.id = setTimeout(fn, ms)
  }

  async function runHealthCheck() {
    try {
      const res = await apiClient.get<HealthResponse>('/health')
      const h   = res.data

      setCheck('backend', h.status === 'ok' ? 'ok' : 'error')
      setCheck('db',      h.db      === 'ok' ? 'ok' : 'error')
      setCheck('riot',    'ok')  // no bloqueante

      setBackendStatus('connected')
      setLcuConnected(h.lcu === 'connected')

      // Auto-detect de cuenta si el cliente está conectado (silencioso)
      if (h.lcu === 'connected') {
        apiClient.post('/settings/detect-from-lcu').catch(() => {})
      }

      await new Promise((r) => setTimeout(r, 600))
      navigate('/', { replace: true })
    } catch (err) {
      retriesRef.current += 1
      if (retriesRef.current >= MAX_RETRIES || !isNetworkError(err)) {
        setFailed(true)
        setCheck('backend', 'error')
        setBackendStatus('error')
      } else {
        schedule(runHealthCheck, POLL_INTERVAL)
      }
    }
  }

  useEffect(() => {
    schedule(runHealthCheck, 600)
    return () => { if (timer.current.id) clearTimeout(timer.current.id) }
  }, [])

  function retry() {
    setFailed(false)
    retriesRef.current = 0
    setChecks((prev) => prev.map((c) => ({ ...c, status: 'pending' })))
    schedule(runHealthCheck, 200)
  }

  return (
    <div className="flex h-screen flex-col items-center justify-center bg-background gap-8">
      {/* Branding */}
      <motion.div
        initial={{ opacity: 0, y: -16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4 }}
        className="flex flex-col items-center gap-3"
      >
        <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-primary/20 border border-primary/30 shadow-lg shadow-primary/10">
          <span className="text-2xl font-bold text-primary">LC</span>
        </div>
        <div className="text-center">
          <h1 className="text-xl font-bold tracking-tight">LoL Coach</h1>
          <p className="text-sm text-muted-foreground mt-0.5">Análisis inteligente de partidas</p>
        </div>
      </motion.div>

      {/* Status checks */}
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.2 }}
        className="flex flex-col gap-2.5 min-w-[240px]"
      >
        {checks.map((check, i) => (
          <motion.div
            key={check.id}
            initial={{ opacity: 0, x: -12 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: 0.3 + i * 0.1 }}
            className="flex items-center gap-3"
          >
            <StatusIcon status={check.status} />
            <span className={
              check.status === 'pending' ? 'text-sm text-muted-foreground'
              : check.status === 'ok'    ? 'text-sm text-foreground'
              :                            'text-sm text-destructive'
            }>
              {check.label}
            </span>
          </motion.div>
        ))}
      </motion.div>

      {/* Error state */}
      <AnimatePresence>
        {failed && (
          <motion.div
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0 }}
            className="flex flex-col items-center gap-3 text-center"
          >
            <p className="text-sm text-muted-foreground max-w-xs">
              No se pudo conectar al backend.<br />
              ¿Está FastAPI corriendo en el puerto 8765?
            </p>
            <Button variant="outline" size="sm" onClick={retry}>
              <RefreshCw className="h-4 w-4" />
              Reintentar
            </Button>
            <code className="text-xs text-muted-foreground/50 font-mono">
              uvicorn backend.api.main:app --port 8765
            </code>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Pulse loader */}
      {!failed && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.5 }}
          className="text-xs text-muted-foreground/40 flex items-center gap-1.5"
        >
          <Loader2 className="h-3 w-3 animate-spin" />
          Conectando…
        </motion.div>
      )}
    </div>
  )
}

function StatusIcon({ status }: { status: CheckStatus }) {
  if (status === 'ok')    return <CheckCircle2 className="h-4 w-4 text-emerald-400 shrink-0" />
  if (status === 'error') return <XCircle      className="h-4 w-4 text-destructive  shrink-0" />
  return <Loader2 className="h-4 w-4 animate-spin text-muted-foreground/50 shrink-0" />
}
