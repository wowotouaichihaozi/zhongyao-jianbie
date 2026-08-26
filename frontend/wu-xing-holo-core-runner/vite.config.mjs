import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { defineConfig } from 'vite'

const runnerDirectory = path.dirname(fileURLToPath(import.meta.url))
const sourceDirectory = path.resolve(runnerDirectory, '../wu-xing-holo-core-original')
const externalDataAdapter = path.resolve(runnerDirectory, 'knowledgeDataAdapter.ts')
const originalDataModule = path.resolve(sourceDirectory, 'src/data')

function suppliedKnowledgeData() {
  return {
    name: 'supplied-knowledge-data',
    enforce: 'pre',
    resolveId(source, importer) {
      if (!importer) return null
      const importerPath = importer.replace(/\?.*$/, '')
      const requestedPath = path.resolve(path.dirname(importerPath), source)
      return requestedPath === originalDataModule ? externalDataAdapter : null
    },
  }
}

export default defineConfig({
  root: sourceDirectory,
  base: '/wu-xing-holo-core-original/',
  envDir: sourceDirectory,
  css: {
    postcss: { plugins: [] },
  },
  plugins: [suppliedKnowledgeData(), react(), tailwindcss()],
  build: {
    outDir: path.resolve(runnerDirectory, '../public/wu-xing-holo-core-original'),
    emptyOutDir: false,
  },
  resolve: {
    alias: {
      '@': sourceDirectory,
    },
  },
})
