const { spawn } = require('node:child_process')
const path = require('node:path')

const env = { ...process.env }
delete env.ELECTRON_RUN_AS_NODE

const electron = require('electron')
const entry = path.resolve(__dirname, '..', 'out-web-backend', 'index.js')
const child = spawn(electron, [entry], {
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
