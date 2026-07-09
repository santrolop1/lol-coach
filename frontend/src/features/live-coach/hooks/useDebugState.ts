/**
 * useDebugState — obtiene el dump completo del estado interno del Live Coach.
 */

import { useQuery } from '@tanstack/react-query'
import { apiClient } from '@/api/client'

export interface DebugState {
  session: Record<string, unknown>
  player: Record<string, unknown>
  intelligence: Record<string, unknown>
  decision: Record<string, unknown> | null
  widgets: Record<string, unknown>[]
  recent_events: { type: string; timestamp: number; data: Record<string, unknown> }[]
  decision_history: Record<string, unknown>[]
  demo: Record<string, unknown>
}

export function useDebugState(enabled = true) {
  return useQuery<DebugState>({
    queryKey: ['live-coach', 'debug'],
    queryFn: () => apiClient.get('/live-coach/debug').then(r => r.data),
    refetchInterval: enabled ? 2_000 : false,
    enabled,
  })
}
