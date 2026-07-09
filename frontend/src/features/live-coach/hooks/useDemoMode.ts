/**
 * useDemoMode — controla el Demo Mode del Live Coach.
 * Llama a los endpoints /live-coach/demo/* del backend.
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { apiClient } from '@/api/client'
import type { DemoState } from '../types'

const DEMO_KEY = ['live-coach', 'demo']

export function useDemoMode() {
  const qc = useQueryClient()

  const { data: demo, isLoading } = useQuery<DemoState>({
    queryKey: DEMO_KEY,
    queryFn: () => apiClient.get('/live-coach/demo').then(r => r.data),
    refetchInterval: 3_000,
  })

  const activate = useMutation({
    mutationFn: (params: { champion: string; scenario: string }) =>
      apiClient.post('/live-coach/demo/activate', params).then(r => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: DEMO_KEY }),
  })

  const deactivate = useMutation({
    mutationFn: () =>
      apiClient.post('/live-coach/demo/deactivate').then(r => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: DEMO_KEY }),
  })

  const setScenario = useMutation({
    mutationFn: (params: { scenario: string; champion?: string }) =>
      apiClient.post('/live-coach/demo/scenario', params).then(r => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: DEMO_KEY }),
  })

  const fireEvent = useMutation({
    mutationFn: (params: { event_type: string; data?: Record<string, unknown> }) =>
      apiClient.post('/live-coach/demo/event', params).then(r => r.data),
  })

  return {
    demo,
    isLoading,
    isActive: demo?.active ?? false,
    currentScenario: demo?.current_scenario ?? '',
    scenarios: demo?.scenarios ?? [],
    activate: activate.mutate,
    deactivate: deactivate.mutate,
    setScenario: setScenario.mutate,
    fireEvent: fireEvent.mutate,
    isPending: activate.isPending || deactivate.isPending || setScenario.isPending,
  }
}
