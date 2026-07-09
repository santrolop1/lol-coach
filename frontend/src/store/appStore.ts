import { create } from 'zustand'
import { persist } from 'zustand/middleware'

type BackendStatus = 'connecting' | 'connected' | 'error'
type Theme = 'dark' | 'light'

interface AppState {
  // ── Backend ────────────────────────────────────────────────────────────────
  backendStatus: BackendStatus
  setBackendStatus: (status: BackendStatus) => void

  // ── Jugador ────────────────────────────────────────────────────────────────
  playerName:  string | null
  playerRank:  string | null
  playerLp:    number | null
  lcuConnected: boolean
  setPlayerInfo:   (name: string, rank: string | null, lp: number | null) => void
  setLcuConnected: (connected: boolean) => void

  // ── UI ─────────────────────────────────────────────────────────────────────
  theme:           Theme
  sidebarPinned:   boolean
  setTheme:        (theme: Theme) => void
  toggleSidebar:   () => void
}

export const useAppStore = create<AppState>()(
  persist(
    (set) => ({
      // Backend
      backendStatus:    'connecting',
      setBackendStatus: (status) => set({ backendStatus: status }),

      // Jugador
      playerName:      null,
      playerRank:      null,
      playerLp:        null,
      lcuConnected:    false,
      setPlayerInfo:   (name, rank, lp) => set({ playerName: name, playerRank: rank, playerLp: lp }),
      setLcuConnected: (connected) => set({ lcuConnected: connected }),

      // UI
      theme:         'dark',
      sidebarPinned: true,
      setTheme:      (theme) => set({ theme }),
      toggleSidebar: () => set((s) => ({ sidebarPinned: !s.sidebarPinned }))
    }),
    {
      name:    'lol-coach-settings',
      partialize: (state) => ({
        theme:        state.theme,
        sidebarPinned: state.sidebarPinned
      })
    }
  )
)
