import { useQuery } from '@tanstack/react-query'
import { apiClient } from '@/api/client'
import type { MatchReviewResponse } from '@/features/matches/types'

export function useMatchReview(matchId: string | undefined) {
  return useQuery<MatchReviewResponse>({
    queryKey:  ['match-review', matchId],
    queryFn:   () =>
      apiClient
        .get<MatchReviewResponse>(`/matches/${matchId}/review`)
        .then((r) => r.data),
    enabled:   !!matchId,
    staleTime: 5 * 60_000,
    retry:     1,
  })
}
