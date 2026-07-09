import { contextBridge, ipcRenderer } from 'electron'
import { electronAPI } from '@electron-toolkit/preload'

// API expuesta al renderer a través de contextBridge
const api = {
  // Controles de ventana
  window: {
    minimize:    () => ipcRenderer.send('window:minimize'),
    maximize:    () => ipcRenderer.send('window:maximize'),
    close:       () => ipcRenderer.send('window:close'),
    isMaximized: () => ipcRenderer.invoke('window:is-maximized') as Promise<boolean>
  },
  // Info de la app
  app: {
    platform:     () => ipcRenderer.invoke('app:platform') as Promise<NodeJS.Platform>,
    version:      () => ipcRenderer.invoke('app:version') as Promise<string>,
    openExternal: (url: string) => ipcRenderer.invoke('app:open-external', url) as Promise<void>
  },
  // Controles del overlay
  overlay: {
    show:          () => ipcRenderer.send('overlay:show'),
    hide:          () => ipcRenderer.send('overlay:hide'),
    toggle:        () => ipcRenderer.send('overlay:toggle'),
    close:         () => ipcRenderer.send('overlay:close'),
    getBounds:     () => ipcRenderer.invoke('overlay:bounds') as Promise<{ x: number; y: number; width: number; height: number }>,
    setBounds:     (bounds: Partial<{ x: number; y: number; width: number; height: number }>) =>
                     ipcRenderer.send('overlay:set-bounds', bounds),
    setOpacity:    (opacity: number) => ipcRenderer.send('overlay:set-opacity', opacity),
    setAlwaysOnTop: (value: boolean) => ipcRenderer.send('overlay:set-always-on-top', value),
    isVisible:     () => ipcRenderer.invoke('overlay:is-visible') as Promise<boolean>,
  }
}

if (process.contextIsolated) {
  try {
    contextBridge.exposeInMainWorld('electron', electronAPI)
    contextBridge.exposeInMainWorld('api', api)
  } catch (error) {
    console.error('[preload] contextBridge error:', error)
  }
} else {
  // @ts-ignore (entorno sin aislamiento — solo dev/test)
  window.electron = electronAPI
  // @ts-ignore
  window.api = api
}
