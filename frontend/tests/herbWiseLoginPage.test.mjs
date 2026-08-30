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

test('role and authentication choices use a strong shared selected state', () => {
  assert.match(source, /label: '用户端'/)
  assert.match(source, /role="tab" :aria-selected="activeTab === 'login'"/)
  assert.match(source, /:global\(#app \.herbwise-login-page \.role-tabs button\.active\)/)
  assert.match(source, /:global\(#app \.herbwise-login-page \.auth-tabs button\.active\)/)
  assert.match(source, /background: #174c3c !important;/)
  assert.match(source, /color: #fff !important;/)
})

test('password visibility controls stay inside the input without floating button chrome', () => {
  assert.match(source, /\.password-field input\) \{\s*padding-right: 48px !important;/)
  assert.match(source, /\.password-visibility-toggle\).*position: absolute !important;/s)
  assert.match(source, /right: 11px !important;/)
  assert.match(source, /width: 30px !important;/)
  assert.match(source, /background: transparent !important;/)
  assert.match(source, /transform: translateY\(-50%\) !important;/)
})

test('login card omits redundant explanatory and footer copy', () => {
  assert.doesNotMatch(source, /登录后继续当前画像与学习路径/)
  assert.doesNotMatch(source, /注册后开始建立你的中医学习画像/)
  assert.doesNotMatch(source, /数据按账户隔离/)
  assert.doesNotMatch(source, /进入学习工作台/)
  assert.doesNotMatch(source, /class="console-meta"/)
})
