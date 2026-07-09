import { useQuery } from '@tanstack/react-query'
import { apiClient } from '@/api/client'
import type { DraftResponse } from '../types'

export function useDraft() {
  return useQuery<DraftResponse>({
    queryKey:        ['draft'],
    queryFn:         () =>
      apiClient.get<DraftResponse>('/draft').then((r) => r.data),
    refetchInterval: 3_000,   // polling cada 3 s — el draft cambia rápido
    staleTime:       1_000,
  })
}
