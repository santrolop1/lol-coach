import { useEffect } from 'react'
import { useQuery } from '@tanstack/react-query'
import { apiClient } from '@/api/client'
import { useAppStore } from '@/store/appStore'
import type { HealthResponse } from '@/features/shared/types/api'

export function useHealthPolling(intervalMs = 8_000) {
  const { setBackendStatus, setLcuConnected } = useAppStore()

  const query = useQuery<HealthResponse>({
    queryKey:        ['health'],
    queryFn:         () => apiClient.get<HealthResponse>('/health').then((r) => r.data),
    refetchInterval: intervalMs,
    retry:           false,
    staleTime:       0
  })

  useEffect(() => {
    if (query.isError) {
      setBackendStatus('error')
    } else if (query.data) {
      setBackendStatus('connected')
      setLcuConnected(query.data.lcu === 'connected')
    }
  }, [query.data, query.isError, setBackendStatus, setLcuConnected])

  return query
}
