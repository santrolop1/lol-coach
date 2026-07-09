import { useQuery } from '@tanstack/react-query'
import { apiClient } from '@/api/client'
import type { KnowledgeResponse } from '@/features/knowledge/types'

export function useKnowledge() {
  return useQuery<KnowledgeResponse>({
    queryKey:        ['knowledge'],
    queryFn:         () =>
      apiClient.get<KnowledgeResponse>('/knowledge').then((r) => r.data),
    staleTime:       60_000,
    refetchInterval: 3 * 60_000,
  })
}
