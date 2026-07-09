"use strict";
const electron = require("electron");
const path = require("path");
const is = {
  dev: !electron.app.isPackaged
};
({
  isWindows: process.platform === "win32",
  isMacOS: process.platform === "darwin",
  isLinux: process.platform === "linux"
});
let mainWindow = null;
let overlayWindow = null;
let overlayBounds = { x: 20, y: 20, width: 280, height: 420 };
function createWindow() {
  mainWindow = new electron.BrowserWindow({
    width: 1280,
    height: 820,
    minWidth: 960,
    minHeight: 640,
    show: false,
    frame: false,
    backgroundColor: "#0a0e1a",
    titleBarStyle: "hidden",
    // macOS: posición de los botones de tráfico
    ...process.platform === "darwin" && {
      trafficLightPosition: { x: 14, y: 16 }
    },
    webPreferences: {
      preload: path.join(__dirname, "../preload/index.js"),
      sandbox: false,
      contextIsolation: true,
      nodeIntegration: false
    }
  });
  mainWindow.on("ready-to-show", () => {
    mainWindow?.show();
  });
  mainWindow.webContents.setWindowOpenHandler(({ url }) => {
    electron.shell.openExternal(url);
    return { action: "deny" };
  });
  if (is.dev && process.env["ELECTRON_RENDERER_URL"]) {
    mainWindow.loadURL(process.env["ELECTRON_RENDERER_URL"]);
    mainWindow.webContents.openDevTools({ mode: "detach" });
  } else {
    mainWindow.loadFile(path.join(__dirname, "../renderer/index.html"));
  }
}
function createOverlayWindow() {
  if (overlayWindow && !overlayWindow.isDestroyed()) return;
  overlayWindow = new electron.BrowserWindow({
    x: overlayBounds.x,
    y: overlayBounds.y,
    width: overlayBounds.width,
    height: overlayBounds.height,
    minWidth: 200,
    minHeight: 150,
    show: false,
    frame: false,
    transparent: true,
    alwaysOnTop: true,
    skipTaskbar: true,
    resizable: true,
    movable: true,
    // Permite clickear a través de zonas vacías del overlay
    hasShadow: false,
    backgroundColor: "#00000000",
    webPreferences: {
      preload: path.join(__dirname, "../preload/index.js"),
      sandbox: false,
      contextIsolation: true,
      nodeIntegration: false
    }
  });
  overlayWindow.setAlwaysOnTop(true, "screen-saver");
  overlayWindow.on("ready-to-show", () => overlayWindow?.show());
  overlayWindow.on("moved", () => {
    if (overlayWindow && !overlayWindow.isDestroyed()) {
      const bounds = overlayWindow.getBounds();
      overlayBounds = { x: bounds.x, y: bounds.y, width: bounds.width, height: bounds.height };
    }
  });
  overlayWindow.on("resized", () => {
    if (overlayWindow && !overlayWindow.isDestroyed()) {
      const bounds = overlayWindow.getBounds();
      overlayBounds = { x: bounds.x, y: bounds.y, width: bounds.width, height: bounds.height };
    }
  });
  overlayWindow.on("closed", () => {
    overlayWindow = null;
  });
  const overlayPath = is.dev && process.env["ELECTRON_RENDERER_URL"] ? `${process.env["ELECTRON_RENDERER_URL"]}#/overlay` : `file://${path.join(__dirname, "../renderer/index.html")}#/overlay`;
  overlayWindow.loadURL(overlayPath);
}
electron.ipcMain.on("window:minimize", () => mainWindow?.minimize());
electron.ipcMain.on("window:maximize", () => {
  if (mainWindow?.isMaximized()) {
    mainWindow.unmaximize();
  } else {
    mainWindow?.maximize();
  }
});
electron.ipcMain.on("window:close", () => mainWindow?.close());
electron.ipcMain.handle("window:is-maximized", () => mainWindow?.isMaximized() ?? false);
electron.ipcMain.handle("app:platform", () => process.platform);
electron.ipcMain.handle("app:version", () => electron.app.getVersion());
electron.ipcMain.handle("app:open-external", (_event, url) => electron.shell.openExternal(url));
electron.ipcMain.on("overlay:show", () => {
  if (!overlayWindow || overlayWindow.isDestroyed()) createOverlayWindow();
  else overlayWindow.show();
});
electron.ipcMain.on("overlay:hide", () => overlayWindow?.hide());
electron.ipcMain.on("overlay:toggle", () => {
  if (!overlayWindow || overlayWindow.isDestroyed()) {
    createOverlayWindow();
  } else if (overlayWindow.isVisible()) {
    overlayWindow.hide();
  } else {
    overlayWindow.show();
  }
});
electron.ipcMain.on("overlay:close", () => {
  overlayWindow?.close();
  overlayWindow = null;
});
electron.ipcMain.handle("overlay:bounds", () => {
  if (overlayWindow && !overlayWindow.isDestroyed()) {
    return overlayWindow.getBounds();
  }
  return overlayBounds;
});
electron.ipcMain.on("overlay:set-bounds", (_event, bounds) => {
  if (overlayWindow && !overlayWindow.isDestroyed()) {
    const current = overlayWindow.getBounds();
    overlayWindow.setBounds({ ...current, ...bounds });
  }
  overlayBounds = { ...overlayBounds, ...bounds };
});
electron.ipcMain.on("overlay:set-opacity", (_event, opacity) => {
  overlayWindow?.setOpacity(Math.max(0.1, Math.min(1, opacity)));
});
electron.ipcMain.on("overlay:set-always-on-top", (_event, value) => {
  if (overlayWindow && !overlayWindow.isDestroyed()) {
    overlayWindow.setAlwaysOnTop(value, value ? "screen-saver" : "normal");
  }
});
electron.ipcMain.handle("overlay:is-visible", () => {
  return overlayWindow?.isVisible() ?? false;
});
electron.app.whenReady().then(() => {
  createWindow();
  electron.app.on("activate", () => {
    if (electron.BrowserWindow.getAllWindows().length === 0) {
      createWindow();
    }
  });
});
electron.app.on("window-all-closed", () => {
  if (process.platform !== "darwin") {
    electron.app.quit();
  }
});
