import { resolve } from 'path'
import { defineConfig, externalizeDepsPlugin } from 'electron-vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  main: {
    plugins: [externalizeDepsPlugin()],
    build: {
      outDir: 'out/main',
      rollupOptions: {
        input: { index: resolve(__dirname, 'electron/main.ts') }
      }
    }
  },
  preload: {
    plugins: [externalizeDepsPlugin()],
    build: {
      outDir: 'out/preload',
      rollupOptions: {
        input: { index: resolve(__dirname, 'electron/preload.ts') }
      }
    }
  },
  renderer: {
    root: 'src',
    build: {
      outDir: 'out/renderer',
      rollupOptions: {
        input: { index: resolve(__dirname, 'src/index.html') }
      }
    },
    resolve: {
      alias: {
        '@': resolve('src')
      }
    },
    plugins: [react()],
    server: {
      port: 5173,
      host: '127.0.0.1'
    }
  }
})
