import { useQuery } from '@tanstack/react-query'
import { apiClient } from '@/api/client'
import type { TrainingResponse } from '../types'

async function fetchTraining(): Promise<TrainingResponse> {
  const r = await apiClient.get<TrainingResponse>('/training')
  return r.data
}

export function useTraining() {
  return useQuery<TrainingResponse>({
    queryKey:      ['training'],
    queryFn:       fetchTraining,
    refetchInterval: 5 * 60 * 1000,   // 5 min
    staleTime:     2 * 60 * 1000,
  })
}
