import { useQuery } from '@tanstack/react-query'
import { apiClient } from '@/api/client'
import type { DashboardResponse } from '@/api/types'

export const dashboardKeys = {
  all: ['dashboard'] as const
}

export function useDashboard() {
  return useQuery<DashboardResponse>({
    queryKey:        dashboardKeys.all,
    queryFn:         () => apiClient.get<DashboardResponse>('/dashboard').then((r) => r.data),
    refetchInterval: 30_000,
    staleTime:       15_000
  })
}
