const { spawn } = require('node:child_process')
const path = require('node:path')

const args = process.argv.slice(2)
const env = { ...process.env }
const cli = path.resolve(__dirname, '..', 'node_modules', 'electron-vite', 'bin', 'electron-vite.js')

delete env.ELECTRON_RUN_AS_NODE

const child = spawn(process.execPath, [cli, ...args], {
  stdio: 'inherit',
  env
})

child.on('exit', (code, signal) => {
  if (signal) {
    process.kill(process.pid, signal)
    return
  }
  process.exit(code ?? 0)
})
