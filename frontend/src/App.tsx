import { Suspense, lazy } from 'react'
import { HashRouter, Routes, Route, Navigate } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { ReactQueryDevtools } from '@tanstack/react-query-devtools'
import { TooltipProvider } from '@/components/ui/tooltip'
import { Toaster }         from '@/components/ui/toaster'
import { ThemeProvider }   from '@/components/ThemeProvider'
import { AppShell }        from '@/components/layout/AppShell'
import { ErrorBoundary }   from '@/components/ErrorBoundary'
import { Skeleton }        from '@/components/ui/skeleton'

// Páginas (lazy para code splitting)
const LoadingPage      = lazy(() => import('@/pages/LoadingPage'))
const DashboardPage    = lazy(() => import('@/features/dashboard'))
const MatchesPage      = lazy(() => import('@/features/matches'))
const MatchReviewPage  = lazy(() => import('@/features/matches/pages/MatchReviewPage'))
const ProgressPage     = lazy(() => import('@/features/progress'))
const KnowledgePage    = lazy(() => import('@/features/knowledge'))
const TrainingPage     = lazy(() => import('@/features/training'))
const CoachingPage     = lazy(() => import('@/features/coaching'))
const DraftPage        = lazy(() => import('@/features/draft'))
const SettingsPage     = lazy(() => import('@/pages/SettingsPage'))
const LiveCoachOverlay = lazy(() =>
  import('@/features/live-coach/LiveCoachOverlay').then(m => ({ default: m.LiveCoachOverlay }))
)
const LiveCoachPage = lazy(() =>
  import('@/features/live-coach/LiveCoachPage').then(m => ({ default: m.LiveCoachPage }))
)

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry:            1,
      refetchOnWindowFocus: false,
      staleTime:        10_000
    }
  }
})

function PageFallback() {
  return (
    <div className="p-6 space-y-4">
      <Skeleton className="h-8 w-48" />
      <Skeleton className="h-4 w-full" />
      <Skeleton className="h-4 w-3/4" />
    </div>
  )
}

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <ThemeProvider>
        <TooltipProvider delayDuration={400}>
          <HashRouter>
            <ErrorBoundary>
              <Suspense fallback={<div className="h-screen bg-background" />}>
                <Routes>
                  {/* Pantalla de carga inicial (sin shell) */}
                  <Route path="/loading" element={<LoadingPage />} />

                  {/* App principal con shell */}
                  <Route element={<AppShell />}>
                    <Route
                      path="/"
                      element={
                        <Suspense fallback={<PageFallback />}>
                          <DashboardPage />
                        </Suspense>
                      }
                    />
                    <Route
                      path="/matches"
                      element={
                        <Suspense fallback={<PageFallback />}>
                          <MatchesPage />
                        </Suspense>
                      }
                    />
                    <Route
                      path="/matches/:matchId"
                      element={
                        <Suspense fallback={<PageFallback />}>
                          <MatchReviewPage />
                        </Suspense>
                      }
                    />
                    <Route
                      path="/progress"
                      element={
                        <Suspense fallback={<PageFallback />}>
                          <ProgressPage />
                        </Suspense>
                      }
                    />
                    <Route
                      path="/knowledge"
                      element={
                        <Suspense fallback={<PageFallback />}>
                          <KnowledgePage />
                        </Suspense>
                      }
                    />
                    <Route
                      path="/training"
                      element={
                        <Suspense fallback={<PageFallback />}>
                          <TrainingPage />
                        </Suspense>
                      }
                    />
                    <Route
                      path="/coaching"
                      element={
                        <Suspense fallback={<PageFallback />}>
                          <CoachingPage />
                        </Suspense>
                      }
                    />
                    <Route
                      path="/draft"
                      element={
                        <Suspense fallback={<PageFallback />}>
                          <DraftPage />
                        </Suspense>
                      }
                    />
                    <Route
                      path="/settings"
                      element={
                        <Suspense fallback={<PageFallback />}>
                          <SettingsPage />
                        </Suspense>
                      }
                    />
                    <Route
                      path="/live-coach"
                      element={
                        <Suspense fallback={<PageFallback />}>
                          <LiveCoachPage />
                        </Suspense>
                      }
                    />
                  </Route>

                  {/* Overlay del Live Coach (ventana transparente independiente) */}
                  <Route
                    path="/overlay"
                    element={
                      <Suspense fallback={<div className="h-screen bg-transparent" />}>
                        <LiveCoachOverlay />
                      </Suspense>
                    }
                  />

                  {/* Redirigir a loading al inicio */}
                  <Route path="*" element={<Navigate to="/loading" replace />} />
                </Routes>
              </Suspense>
            </ErrorBoundary>
          </HashRouter>
          <Toaster />
          {import.meta.env.DEV && <ReactQueryDevtools buttonPosition="bottom-right" />}
        </TooltipProvider>
      </ThemeProvider>
    </QueryClientProvider>
  )
}
