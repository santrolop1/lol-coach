import { Outlet } from 'react-router-dom'
import { useEffect } from 'react'
import { Sidebar } from '@/components/layout/Sidebar'
import { Header }  from '@/components/layout/Header'
import { ErrorBoundary } from '@/components/ErrorBoundary'
import { useAppStore } from '@/store/appStore'
import { useHealth } from '@/api/queries/health'
import { ScrollArea } from '@/components/ui/scroll-area'

export function AppShell() {
  const { setBackendStatus, setLcuConnected } = useAppStore()
  const { data: health, isError } = useHealth({ refetchInterval: 8_000 })

  // Sincronizar estado del backend con el store
  useEffect(() => {
    if (isError) {
      setBackendStatus('error')
    } else if (health) {
      setBackendStatus('connected')
      setLcuConnected(health.lcu === 'connected')
    }
  }, [health, isError, setBackendStatus, setLcuConnected])

  return (
    <div className="flex h-screen overflow-hidden bg-background">
      <Sidebar />

      <div className="flex flex-1 flex-col overflow-hidden min-w-0">
        <Header />

        <ScrollArea className="flex-1">
          <main className="h-full">
            <ErrorBoundary>
              <Outlet />
            </ErrorBoundary>
          </main>
        </ScrollArea>
      </div>
    </div>
  )
}
