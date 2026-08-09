const fs = require('node:fs')
const path = require('node:path')
const { spawnSync } = require('node:child_process')

const projectDir = path.resolve(__dirname, '..')
const viteBin = path.join(projectDir, 'node_modules', 'vite', 'bin', 'vite.js')

if (!fs.existsSync(viteBin)) {
  console.error(`[build-web] Missing local Vite binary: ${viteBin}`)
  process.exit(1)
}

const result = spawnSync(process.execPath, [viteBin, 'build'], {
  cwd: projectDir,
  stdio: 'inherit',
  shell: false
})

const indexHtml = path.join(projectDir, 'dist-web', 'index.html')
if (!fs.existsSync(indexHtml)) {
  process.exit(typeof result.status === 'number' ? result.status : 1)
}

require('./copy-web-resources.cjs')
