import { useQuery } from '@tanstack/react-query'
import { apiClient } from '@/api/client'
import type { DashboardResponse } from '@/features/shared/types/api'

export function useDashboard() {
  return useQuery<DashboardResponse>({
    queryKey:        ['dashboard'],
    queryFn:         () => apiClient.get<DashboardResponse>('/dashboard').then((r) => r.data),
    refetchInterval: 30_000,
    staleTime:       10_000
  })
}
