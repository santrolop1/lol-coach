import { useQuery } from '@tanstack/react-query'
import { apiClient } from '@/api/client'
import type { MatchesResponse } from '@/features/matches/types'

export function useMatches(role?: string | null) {
  return useQuery<MatchesResponse>({
    queryKey:  ['matches', role ?? null],
    queryFn:   () =>
      apiClient
        .get<MatchesResponse>('/matches', { params: role ? { role } : {} })
        .then((r) => r.data),
    staleTime: 60_000,
  })
}
