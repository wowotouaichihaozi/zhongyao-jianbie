import assert from 'node:assert/strict'
import fs from 'node:fs'
import path from 'node:path'
import test from 'node:test'
import { fileURLToPath } from 'node:url'

const frontendDir = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..')
const imageDir = path.resolve(frontendDir, '../img')

const optimizedLandingImages = [
  'auth-hero-embedded-collage.webp',
  'auth-capability-profile.webp',
  'auth-capability-path.webp',
  'auth-capability-resources.webp',
  'auth-capability-assessment.webp',
]

test('keeps optimized landing media within the initial-load budget', () => {
  const optimizedBytes = optimizedLandingImages.reduce((total, filename) => {
    return total + fs.statSync(path.join(imageDir, filename)).size
  }, 0)

  assert.ok(optimizedBytes < 700_000, `optimized landing media is ${optimizedBytes} bytes`)
  assert.ok(fs.statSync(path.join(imageDir, 'logogif-128.webp')).size < 300_000)
  assert.ok(fs.existsSync(path.join(imageDir, 'logogif.gif')), 'the original GIF fallback must remain available')
})

test('prefers WebP while retaining original media fallbacks', () => {
  const authSource = fs.readFileSync(path.join(frontendDir, 'src/views/AuthPage.vue'), 'utf8')
  const launcherSource = fs.readFileSync(path.join(frontendDir, 'src/components/FloatingLogoLauncher.vue'), 'utf8')

  optimizedLandingImages.forEach((filename) => {
    assert.match(authSource, new RegExp(`srcset="/${filename}"`))
  })
  assert.equal((authSource.match(/loading="lazy" decoding="async"/g) || []).length, 5)
  assert.match(launcherSource, /srcset="\/logogif-128\.webp"/)
  assert.match(launcherSource, /src="\/logogif\.gif"/)
})
