import axios, { type AxiosError } from 'axios'

// Puerto configurable — por defecto 8766 (8765 suele estar ocupado en Windows)
const PORT     = import.meta.env.VITE_API_PORT ?? '8766'
export const API_BASE = `http://127.0.0.1:${PORT}`
export const API_V1   = `${API_BASE}/api/v1`

export const apiClient = axios.create({
  baseURL: API_V1,
  timeout: 15_000,
  headers: { 'Content-Type': 'application/json' }
})

// Interceptor: loguea errores en dev
apiClient.interceptors.response.use(
  (res) => res,
  (error: AxiosError) => {
    if (import.meta.env.DEV) {
      console.error('[api]', error.config?.url, error.response?.status ?? 'network error')
    }
    return Promise.reject(error)
  }
)

export function isNetworkError(error: unknown): boolean {
  if (!axios.isAxiosError(error)) return false
  return !error.response
}
