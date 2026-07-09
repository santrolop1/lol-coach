/// <reference types="vite/client" />

interface Window {
  electron: import('@electron-toolkit/preload').ElectronAPI
  api: {
    window: {
      minimize: () => void
      maximize: () => void
      close: () => void
      isMaximized: () => Promise<boolean>
    }
    app: {
      platform:     () => Promise<NodeJS.Platform>
      version:      () => Promise<string>
      openExternal: (url: string) => Promise<void>
    }
    overlay: {
      show:          () => void
      hide:          () => void
      toggle:        () => void
      close:         () => void
      getBounds:     () => Promise<{ x: number; y: number; width: number; height: number }>
      setBounds:     (bounds: Partial<{ x: number; y: number; width: number; height: number }>) => void
      setOpacity:    (opacity: number) => void
      setAlwaysOnTop: (value: boolean) => void
      isVisible:     () => Promise<boolean>
    }
  }
}
