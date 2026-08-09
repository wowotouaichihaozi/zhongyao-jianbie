import { dirname, resolve } from 'node:path'
import { existsSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

const configDir = dirname(fileURLToPath(import.meta.url))
const projectDir = existsSync(resolve(process.cwd(), 'resources', 'styles.json'))
  ? process.cwd()
  : configDir

export default defineConfig({
  root: 'src/renderer',
  base: '/ppt/',
  publicDir: resolve(projectDir, 'public'),
  resolve: {
    alias: {
      '@renderer': resolve(projectDir, 'src/renderer/src'),
      '@shared': resolve(projectDir, 'src/shared')
    }
  },
  server: {
    port: 5188,
    strictPort: false,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8765',
        changeOrigin: true,
        configure: (proxy) => {
          proxy.on('proxyReq', () => {
            // Bypass system proxy for local backend
          })
        }
      }
    }
  },
  preview: {
    port: 5188,
    strictPort: false
  },
  plugins: [react()],
  build: {
    outDir: resolve(projectDir, 'dist-web'),
    emptyOutDir: true
  }
})
