const fs = require('node:fs')
const path = require('node:path')

const projectDir = path.resolve(__dirname, '..')
const source = path.join(projectDir, 'resources')
const target = path.join(projectDir, 'dist-web', 'resources')

function copyDir(sourceDir, targetDir) {
  fs.mkdirSync(targetDir, { recursive: true })
  for (const entry of fs.readdirSync(sourceDir, { withFileTypes: true })) {
    const sourcePath = path.join(sourceDir, entry.name)
    const targetPath = path.join(targetDir, entry.name)
    if (entry.isDirectory()) {
      copyDir(sourcePath, targetPath)
    } else if (entry.isFile()) {
      fs.copyFileSync(sourcePath, targetPath)
    }
  }
}

if (!fs.existsSync(source)) {
  console.error(`[copy-web-resources] Missing resources directory: ${source}`)
  process.exit(1)
}

try {
  console.log(`[copy-web-resources] Source: ${source}`)
  console.log(`[copy-web-resources] Target: ${target}`)
  fs.rmSync(target, { recursive: true, force: true })
  fs.mkdirSync(path.dirname(target), { recursive: true })
  copyDir(source, target)

  const styleHtmlDir = path.join(target, 'styleHtml')
  const styleHtmlCount = fs.existsSync(styleHtmlDir)
    ? fs.readdirSync(styleHtmlDir).filter((name) => name.endsWith('.html')).length
    : 0

  console.log(`[copy-web-resources] Copied PPT resources to ${target}`)
  console.log(`[copy-web-resources] styleHtml files: ${styleHtmlCount}`)
} catch (error) {
  console.error('[copy-web-resources] Failed to copy PPT resources')
  console.error(error && error.stack ? error.stack : error)
  process.exit(1)
}
