import assert from 'node:assert/strict'
import fs from 'node:fs'
import test from 'node:test'

const source = fs.readFileSync(new URL('../src/views/HerbWiseLoginPage.vue', import.meta.url), 'utf8')
const routerSource = fs.readFileSync(new URL('../src/router/index.js', import.meta.url), 'utf8')

test('login route uses the latest HerbWise one-screen composition', () => {
  assert.match(routerSource, /import\('\.\.\/views\/HerbWiseLoginPage\.vue'\)/)
  assert.match(source, /class="herbwise-login-page"/)
  assert.match(source, /url\('\/images\/herbwise-login-scene\.jpg'\)/)
  assert.match(source, /class="hero-panel"/)
  assert.match(source, /class="login-console auth-modal-panel"/)
  assert.match(source, /grid-template-columns: repeat\(4, minmax\(0, 1fr\)\)/)
})

test('new skin keeps real project authentication contracts', () => {
  assert.match(source, /loginUser\(/)
  assert.match(source, /loginAdminUser\(/)
  assert.match(source, /registerUser\(/)
  assert.match(source, /getLoginCaptcha\(/)
  assert.match(source, /safeInternalRedirect\(route\.query\.redirect\)/)
  assert.doesNotMatch(source, /HerbWise@2026/)
  assert.doesNotMatch(source, /captchaCode = ref/)
})
