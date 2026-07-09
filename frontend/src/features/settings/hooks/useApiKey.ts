import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { apiClient } from '@/api/client'

export interface ApiKeyStatus {
  configured:   boolean
  status:       'active' | 'expiring_soon' | 'expired' | 'not_configured'
  status_label: string
  masked_key:   string | null
  saved_at:     string | null
  hours_old:    number | null
}

export interface ApiKeySaveResponse {
  success:    boolean
  message:    string
  status:     string
  masked_key: string | null
}

export function useApiKeyStatus() {
  return useQuery<ApiKeyStatus>({
    queryKey:        ['api-key-status'],
    queryFn:         () => apiClient.get<ApiKeyStatus>('/settings/api-key/status').then((r) => r.data),
    refetchInterval: 60_000,   // re-verifica cada minuto para actualizar "horas old"
    staleTime:       30_000,
  })
}

export function useSaveApiKey() {
  const queryClient = useQueryClient()

  return useMutation<ApiKeySaveResponse, Error, string>({
    mutationFn: (api_key: string) =>
      apiClient.post<ApiKeySaveResponse>('/settings/api-key', { api_key }).then((r) => r.data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['api-key-status'] })
      queryClient.invalidateQueries({ queryKey: ['settings'] })
      queryClient.invalidateQueries({ queryKey: ['dashboard'] })
    },
  })
}

export function useDeleteApiKey() {
  const queryClient = useQueryClient()

  return useMutation<unknown, Error, void>({
    mutationFn: () => apiClient.delete('/settings/api-key').then((r) => r.data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['api-key-status'] })
      queryClient.invalidateQueries({ queryKey: ['settings'] })
      queryClient.invalidateQueries({ queryKey: ['dashboard'] })
    },
  })
}

export interface AccountChangeRequest {
  game_name: string
  tag_line:  string
  platform:  string
}

export interface AccountChangeResponse {
  success: boolean
  message: string
  riot_id: string
  tag:     string
  level:   number
  rank:    string
}

export function useDetectFromLcu() {
  const queryClient = useQueryClient()

  return useMutation<{ status: string; message: string; riot_id?: string; tag?: string }, Error, void>({
    mutationFn: () =>
      apiClient.post('/settings/detect-from-lcu').then((r) => r.data),
    onSuccess: (res) => {
      if (res.status === 'updated') {
        queryClient.invalidateQueries({ queryKey: ['settings'] })
        queryClient.invalidateQueries({ queryKey: ['dashboard'] })
      }
    },
  })
}

export function useChangeAccount() {
  const queryClient = useQueryClient()

  return useMutation<AccountChangeResponse, Error, AccountChangeRequest>({
    mutationFn: (body) =>
      apiClient.post<AccountChangeResponse>('/settings/account', body).then((r) => r.data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['settings'] })
      queryClient.invalidateQueries({ queryKey: ['dashboard'] })
    },
  })
}

export function useSyncMatches() {
  const queryClient = useQueryClient()

  return useMutation<unknown, Error, void>({
    mutationFn: () => apiClient.post('/settings/sync').then((r) => r.data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['dashboard'] })
      queryClient.invalidateQueries({ queryKey: ['settings'] })
    },
  })
}
