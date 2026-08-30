import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { defineConfig } from 'vite'

const runnerDirectory = path.dirname(fileURLToPath(import.meta.url))
const sourceDirectory = path.resolve(runnerDirectory, '../wu-xing-holo-core-original')
const externalDataAdapter = path.resolve(runnerDirectory, 'knowledgeDataAdapter.ts')
const originalDataModule = path.resolve(sourceDirectory, 'src/data')
const originalAppModule = path.resolve(sourceDirectory, 'src/App.tsx')
const runnerAppModule = path.resolve(runnerDirectory, 'App.tsx')

function suppliedKnowledgeData() {
  return {
    name: 'supplied-knowledge-data',
    enforce: 'pre',
    resolveId(source, importer) {
      if (!importer) return null
      const importerPath = importer.replace(/\?.*$/, '')
      const requestedPath = path.resolve(path.dirname(importerPath), source)
      if (requestedPath === originalAppModule) return runnerAppModule
      return requestedPath === originalDataModule ? externalDataAdapter : null
    },
  }
}

function runnerTailwindSource() {
  return {
    name: 'runner-tailwind-source',
    enforce: 'pre',
    transform(code, id) {
      const stylesheet = path.resolve(sourceDirectory, 'src/index.css')
      if (path.resolve(id.replace(/\?.*$/, '')) !== stylesheet) return null
      return `@source "../../wu-xing-holo-core-runner";\n${code}`
    },
  }
}

function runnerFavicon() {
  return {
    name: 'runner-favicon',
    transformIndexHtml(html) {
      return html.replace('</head>', '    <link rel="icon" href="/favicon.svg" type="image/svg+xml" />\n  </head>')
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
  plugins: [suppliedKnowledgeData(), runnerTailwindSource(), runnerFavicon(), react(), tailwindcss()],
  build: {
    outDir: path.resolve(runnerDirectory, '../public/wu-xing-holo-core-original'),
    emptyOutDir: false,
  },
  resolve: {
    alias: {
      '@': sourceDirectory,
      react: path.resolve(sourceDirectory, 'node_modules/react'),
      'react-dom': path.resolve(sourceDirectory, 'node_modules/react-dom'),
      motion: path.resolve(sourceDirectory, 'node_modules/motion'),
      'lucide-react': path.resolve(sourceDirectory, 'node_modules/lucide-react'),
      '@react-three/fiber': path.resolve(sourceDirectory, 'node_modules/@react-three/fiber'),
      '@react-three/drei': path.resolve(sourceDirectory, 'node_modules/@react-three/drei'),
      three: path.resolve(sourceDirectory, 'node_modules/three'),
    },
  },
})
