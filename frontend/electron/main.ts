import { app, BrowserWindow, ipcMain, shell } from 'electron'
import { join } from 'path'
import { is } from '@electron-toolkit/utils'

let mainWindow: BrowserWindow | null = null
let overlayWindow: BrowserWindow | null = null

// Posición y tamaño persistidos en memoria (hasta que tengamos DB access desde main)
let overlayBounds = { x: 20, y: 20, width: 280, height: 420 }

function createWindow(): void {
  mainWindow = new BrowserWindow({
    width:          1280,
    height:         820,
    minWidth:       960,
    minHeight:      640,
    show:           false,
    frame:          false,
    backgroundColor: '#0a0e1a',
    titleBarStyle:  'hidden',
    // macOS: posición de los botones de tráfico
    ...(process.platform === 'darwin' && {
      trafficLightPosition: { x: 14, y: 16 }
    }),
    webPreferences: {
      preload:         join(__dirname, '../preload/index.js'),
      sandbox:         false,
      contextIsolation: true,
      nodeIntegration: false
    }
  })

  // Mostrar solo cuando el contenido esté listo (evita flash blanco)
  mainWindow.on('ready-to-show', () => {
    mainWindow?.show()
  })

  // Abrir links externos en el navegador del sistema
  mainWindow.webContents.setWindowOpenHandler(({ url }) => {
    shell.openExternal(url)
    return { action: 'deny' }
  })

  if (is.dev && process.env['ELECTRON_RENDERER_URL']) {
    mainWindow.loadURL(process.env['ELECTRON_RENDERER_URL'])
    mainWindow.webContents.openDevTools({ mode: 'detach' })
  } else {
    mainWindow.loadFile(join(__dirname, '../renderer/index.html'))
  }
}

function createOverlayWindow(): void {
  if (overlayWindow && !overlayWindow.isDestroyed()) return

  overlayWindow = new BrowserWindow({
    x:           overlayBounds.x,
    y:           overlayBounds.y,
    width:       overlayBounds.width,
    height:      overlayBounds.height,
    minWidth:    200,
    minHeight:   150,
    show:        false,
    frame:       false,
    transparent: true,
    alwaysOnTop: true,
    skipTaskbar: true,
    resizable:   true,
    movable:     true,
    // Permite clickear a través de zonas vacías del overlay
    hasShadow:   false,
    backgroundColor: '#00000000',
    webPreferences: {
      preload:          join(__dirname, '../preload/index.js'),
      sandbox:          false,
      contextIsolation: true,
      nodeIntegration:  false,
    }
  })

  overlayWindow.setAlwaysOnTop(true, 'screen-saver')

  overlayWindow.on('ready-to-show', () => overlayWindow?.show())

  overlayWindow.on('moved', () => {
    if (overlayWindow && !overlayWindow.isDestroyed()) {
      const bounds = overlayWindow.getBounds()
      overlayBounds = { x: bounds.x, y: bounds.y, width: bounds.width, height: bounds.height }
    }
  })

  overlayWindow.on('resized', () => {
    if (overlayWindow && !overlayWindow.isDestroyed()) {
      const bounds = overlayWindow.getBounds()
      overlayBounds = { x: bounds.x, y: bounds.y, width: bounds.width, height: bounds.height }
    }
  })

  overlayWindow.on('closed', () => { overlayWindow = null })

  const overlayPath = is.dev && process.env['ELECTRON_RENDERER_URL']
    ? `${process.env['ELECTRON_RENDERER_URL']}#/overlay`
    : `file://${join(__dirname, '../renderer/index.html')}#/overlay`

  overlayWindow.loadURL(overlayPath)
}

// ── IPC: controles de ventana ──────────────────────────────────────────────────

ipcMain.on('window:minimize', () => mainWindow?.minimize())

ipcMain.on('window:maximize', () => {
  if (mainWindow?.isMaximized()) {
    mainWindow.unmaximize()
  } else {
    mainWindow?.maximize()
  }
})

ipcMain.on('window:close', () => mainWindow?.close())

ipcMain.handle('window:is-maximized', () => mainWindow?.isMaximized() ?? false)

ipcMain.handle('app:platform', () => process.platform)

ipcMain.handle('app:version', () => app.getVersion())

ipcMain.handle('app:open-external', (_event, url: string) => shell.openExternal(url))

// ── IPC: overlay ───────────────────────────────────────────────────────────────

ipcMain.on('overlay:show', () => {
  if (!overlayWindow || overlayWindow.isDestroyed()) createOverlayWindow()
  else overlayWindow.show()
})

ipcMain.on('overlay:hide', () => overlayWindow?.hide())

ipcMain.on('overlay:toggle', () => {
  if (!overlayWindow || overlayWindow.isDestroyed()) {
    createOverlayWindow()
  } else if (overlayWindow.isVisible()) {
    overlayWindow.hide()
  } else {
    overlayWindow.show()
  }
})

ipcMain.on('overlay:close', () => {
  overlayWindow?.close()
  overlayWindow = null
})

ipcMain.handle('overlay:bounds', () => {
  if (overlayWindow && !overlayWindow.isDestroyed()) {
    return overlayWindow.getBounds()
  }
  return overlayBounds
})

ipcMain.on('overlay:set-bounds', (_event, bounds: Partial<typeof overlayBounds>) => {
  if (overlayWindow && !overlayWindow.isDestroyed()) {
    const current = overlayWindow.getBounds()
    overlayWindow.setBounds({ ...current, ...bounds })
  }
  overlayBounds = { ...overlayBounds, ...bounds }
})

ipcMain.on('overlay:set-opacity', (_event, opacity: number) => {
  overlayWindow?.setOpacity(Math.max(0.1, Math.min(1.0, opacity)))
})

ipcMain.on('overlay:set-always-on-top', (_event, value: boolean) => {
  if (overlayWindow && !overlayWindow.isDestroyed()) {
    overlayWindow.setAlwaysOnTop(value, value ? 'screen-saver' : 'normal')
  }
})

ipcMain.handle('overlay:is-visible', () => {
  return overlayWindow?.isVisible() ?? false
})

// ── Ciclo de vida ──────────────────────────────────────────────────────────────

app.whenReady().then(() => {
  createWindow()

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createWindow()
    }
  })
})

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit()
  }
})
