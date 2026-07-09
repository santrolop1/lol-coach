"use strict";
const electron = require("electron");
const electronAPI = {
  ipcRenderer: {
    send(channel, ...args) {
      electron.ipcRenderer.send(channel, ...args);
    },
    sendTo(webContentsId, channel, ...args) {
      const electronVer = process.versions.electron;
      const electronMajorVer = electronVer ? parseInt(electronVer.split(".")[0]) : 0;
      if (electronMajorVer >= 28) {
        throw new Error('"sendTo" method has been removed since Electron 28.');
      } else {
        electron.ipcRenderer.sendTo(webContentsId, channel, ...args);
      }
    },
    sendSync(channel, ...args) {
      return electron.ipcRenderer.sendSync(channel, ...args);
    },
    sendToHost(channel, ...args) {
      electron.ipcRenderer.sendToHost(channel, ...args);
    },
    postMessage(channel, message, transfer) {
      electron.ipcRenderer.postMessage(channel, message, transfer);
    },
    invoke(channel, ...args) {
      return electron.ipcRenderer.invoke(channel, ...args);
    },
    on(channel, listener) {
      electron.ipcRenderer.on(channel, listener);
      return () => {
        electron.ipcRenderer.removeListener(channel, listener);
      };
    },
    once(channel, listener) {
      electron.ipcRenderer.once(channel, listener);
      return () => {
        electron.ipcRenderer.removeListener(channel, listener);
      };
    },
    removeListener(channel, listener) {
      electron.ipcRenderer.removeListener(channel, listener);
      return this;
    },
    removeAllListeners(channel) {
      electron.ipcRenderer.removeAllListeners(channel);
    }
  },
  webFrame: {
    insertCSS(css) {
      return electron.webFrame.insertCSS(css);
    },
    setZoomFactor(factor) {
      if (typeof factor === "number" && factor > 0) {
        electron.webFrame.setZoomFactor(factor);
      }
    },
    setZoomLevel(level) {
      if (typeof level === "number") {
        electron.webFrame.setZoomLevel(level);
      }
    }
  },
  webUtils: {
    getPathForFile(file) {
      return electron.webUtils.getPathForFile(file);
    }
  },
  process: {
    get platform() {
      return process.platform;
    },
    get versions() {
      return process.versions;
    },
    get env() {
      return { ...process.env };
    }
  }
};
const api = {
  // Controles de ventana
  window: {
    minimize: () => electron.ipcRenderer.send("window:minimize"),
    maximize: () => electron.ipcRenderer.send("window:maximize"),
    close: () => electron.ipcRenderer.send("window:close"),
    isMaximized: () => electron.ipcRenderer.invoke("window:is-maximized")
  },
  // Info de la app
  app: {
    platform: () => electron.ipcRenderer.invoke("app:platform"),
    version: () => electron.ipcRenderer.invoke("app:version"),
    openExternal: (url) => electron.ipcRenderer.invoke("app:open-external", url)
  },
  // Controles del overlay
  overlay: {
    show: () => electron.ipcRenderer.send("overlay:show"),
    hide: () => electron.ipcRenderer.send("overlay:hide"),
    toggle: () => electron.ipcRenderer.send("overlay:toggle"),
    close: () => electron.ipcRenderer.send("overlay:close"),
    getBounds: () => electron.ipcRenderer.invoke("overlay:bounds"),
    setBounds: (bounds) => electron.ipcRenderer.send("overlay:set-bounds", bounds),
    setOpacity: (opacity) => electron.ipcRenderer.send("overlay:set-opacity", opacity),
    setAlwaysOnTop: (value) => electron.ipcRenderer.send("overlay:set-always-on-top", value),
    isVisible: () => electron.ipcRenderer.invoke("overlay:is-visible")
  }
};
if (process.contextIsolated) {
  try {
    electron.contextBridge.exposeInMainWorld("electron", electronAPI);
    electron.contextBridge.exposeInMainWorld("api", api);
  } catch (error) {
    console.error("[preload] contextBridge error:", error);
  }
} else {
  window.electron = electronAPI;
  window.api = api;
}
