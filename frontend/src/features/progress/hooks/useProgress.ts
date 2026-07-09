import { useQuery } from '@tanstack/react-query'
import { apiClient } from '@/api/client'
import type { ProgressResponse } from '@/features/progress/types'

export function useProgress() {
  return useQuery<ProgressResponse>({
    queryKey:  ['progress'],
    queryFn:   () =>
      apiClient.get<ProgressResponse>('/progress').then((r) => r.data),
    staleTime: 2 * 60_000,
    refetchInterval: 5 * 60_000,
  })
}
