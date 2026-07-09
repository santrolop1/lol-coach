import { useQuery } from '@tanstack/react-query'
import { apiClient } from '@/api/client'
import type { CoachingResponse } from '../types'

export function useCoaching(role: 'ADC' | 'TOP' = 'ADC', limit = 20) {
  return useQuery<CoachingResponse>({
    queryKey:        ['coaching', role, limit],
    queryFn:         () =>
      apiClient.get<CoachingResponse>('/coaching', { params: { role, limit } }).then((r) => r.data),
    staleTime:       60_000,
    refetchInterval: 3 * 60_000,
  })
}
