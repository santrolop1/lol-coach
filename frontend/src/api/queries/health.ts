import { useQuery } from '@tanstack/react-query'
import { apiClient } from '@/api/client'
import type { HealthResponse } from '@/api/types'

export const healthKeys = {
  all: ['health'] as const
}

export function useHealth(options?: { enabled?: boolean; refetchInterval?: number }) {
  return useQuery<HealthResponse>({
    queryKey:        healthKeys.all,
    queryFn:         () => apiClient.get<HealthResponse>('/health').then((r) => r.data),
    refetchInterval: options?.refetchInterval ?? 5_000,
    retry:           false,
    staleTime:       0,
    enabled:         options?.enabled ?? true
  })
}
