/**
 * useLiveCoach — hook principal del Live Coach.
 *
 * Estrategia de conexión:
 *   1. Intenta WebSocket (/ws/live-coach) — actualizaciones push cada 2s
 *   2. Si WebSocket falla → polling REST cada 3s como fallback
 *
 * El componente overlay no sabe de dónde vienen los datos.
 */

import { useState, useEffect, useRef, useCallback } from 'react'
import { API_BASE } from '../../api/client'
import { LiveCoachState, DEFAULT_STATE } from './types'

const WS_URL = API_BASE.replace('http', 'ws') + '/ws/live-coach'
const POLL_URL = API_BASE + '/api/v1/live-coach'
const POLL_INTERVAL = 3_000
const WS_RECONNECT_DELAY = 4_000

interface UseLiveCoachReturn {
  state: LiveCoachState
  connected: boolean
  connectionMode: 'ws' | 'poll' | 'offline'
  setChampion: (champion: string, role: string) => void
  reset: () => void
}

export function useLiveCoach(): UseLiveCoachReturn {
  const [state, setState] = useState<LiveCoachState>(DEFAULT_STATE)
  const [connected, setConnected] = useState(false)
  const [connectionMode, setConnectionMode] = useState<'ws' | 'poll' | 'offline'>('offline')

  const wsRef = useRef<WebSocket | null>(null)
  const pollTimerRef = useRef<ReturnType<typeof setInterval> | null>(null)
  const reconnectTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const usingWsRef = useRef(false)

  const stopPolling = useCallback(() => {
    if (pollTimerRef.current) {
      clearInterval(pollTimerRef.current)
      pollTimerRef.current = null
    }
  }, [])

  const startPolling = useCallback(() => {
    stopPolling()
    setConnectionMode('poll')

    const poll = async () => {
      try {
        const res = await fetch(POLL_URL)
        if (res.ok) {
          const data = await res.json()
          setState(data)
          setConnected(true)
        }
      } catch {
        setConnected(false)
        setConnectionMode('offline')
      }
    }

    poll()
    pollTimerRef.current = setInterval(poll, POLL_INTERVAL)
  }, [stopPolling])

  const connectWs = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) return

    const ws = new WebSocket(WS_URL)
    wsRef.current = ws
    usingWsRef.current = false

    ws.onopen = () => {
      usingWsRef.current = true
      setConnected(true)
      setConnectionMode('ws')
      stopPolling()
    }

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)
        if (data.pong) return
        setState(data as LiveCoachState)
      } catch {}
    }

    ws.onclose = () => {
      setConnected(false)
      usingWsRef.current = false
      // Fallback a polling mientras el WS no esté disponible
      startPolling()
      reconnectTimerRef.current = setTimeout(connectWs, WS_RECONNECT_DELAY)
    }

    ws.onerror = () => {
      ws.close()
    }
  }, [startPolling, stopPolling])

  useEffect(() => {
    connectWs()
    return () => {
      wsRef.current?.close()
      stopPolling()
      if (reconnectTimerRef.current) clearTimeout(reconnectTimerRef.current)
    }
  }, [connectWs, stopPolling])

  const setChampion = useCallback((champion: string, role: string) => {
    const ws = wsRef.current
    if (ws?.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({ action: 'set_champion', champion, role }))
    } else {
      fetch(`${API_BASE}/api/v1/live-coach/champion`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ champion, role }),
      }).catch(() => {})
    }
  }, [])

  const reset = useCallback(() => {
    const ws = wsRef.current
    if (ws?.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({ action: 'reset' }))
    } else {
      fetch(`${API_BASE}/api/v1/live-coach/reset`, { method: 'POST' }).catch(() => {})
    }
    setState(DEFAULT_STATE)
  }, [])

  return { state, connected, connectionMode, setChampion, reset }
}
