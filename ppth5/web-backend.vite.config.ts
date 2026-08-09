import { resolve } from 'node:path'
import { defineConfig } from 'vite'

export default defineConfig({
  resolve: {
    alias: {
      '@shared': resolve(__dirname, 'src/shared')
    }
  },
  build: {
    ssr: resolve(__dirname, 'src/web-backend/index.ts'),
    outDir: resolve(__dirname, 'out-web-backend'),
    emptyOutDir: true,
    target: 'node22',
    rollupOptions: {
      output: {
        entryFileNames: 'index.js',
        format: 'es'
      },
      external: ['electron', 'better-sqlite3']
    }
  }
})
