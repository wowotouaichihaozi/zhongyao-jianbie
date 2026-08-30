import assert from 'node:assert/strict'
import fs from 'node:fs'

import { chromium } from 'playwright'

const baseUrl = process.env.E2E_BASE_URL || 'http://127.0.0.1:5088'
const targetPath = '/user-profile?section=security&source=resource#password'
const systemChromiumCandidates = [
  'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe',
  'C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe',
  'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe',
  'C:\\Program Files\\Microsoft\\Edge\\Application\\msedge.exe',
]
const launchOptions = { headless: true }
if (!fs.existsSync(chromium.executablePath())) {
  launchOptions.executablePath = systemChromiumCandidates.find(candidate => fs.existsSync(candidate))
}
assert.ok(launchOptions.executablePath || fs.existsSync(chromium.executablePath()), 'No Chromium browser is available.')

const browser = await chromium.launch(launchOptions)
try {
  const context = await browser.newContext({ viewport: { width: 1280, height: 800 } })
  const page = await context.newPage()

  await page.route('**/api/auth/login', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        id: 901,
        username: 'deep-link-test',
        displayName: 'Deep Link Test',
        role: 'user',
        token: 'deep-link-contract-token',
      }),
    })
  })
  await page.route('**/api/xiaozhi/events', route => route.fulfill({ status: 200, contentType: 'application/json', body: '{}' }))
  await page.route('**/api/xiaozhi/status', route => route.fulfill({ status: 200, contentType: 'application/json', body: '{"data":{"tasks":[],"agents":[]}}' }))
  await page.route('**/api/learning-activity/pulse', route => route.fulfill({ status: 200, contentType: 'application/json', body: '{}' }))

  await page.goto(`${baseUrl}${targetPath}`, { waitUntil: 'domcontentloaded' })
  await page.locator('.auth-modal-panel').waitFor({ state: 'visible' })

  const loginUrl = new URL(page.url())
  assert.equal(loginUrl.pathname, '/login')
  assert.equal(loginUrl.searchParams.get('redirect'), targetPath)

  await page.locator('input[autocomplete="username"]').fill('deep-link-test')
  await page.locator('input[autocomplete="current-password"]').fill('StrongPass123!')
  await page.locator('.auth-modal-panel form').evaluate(form => form.requestSubmit())
  await page.waitForURL(url => `${url.pathname}${url.search}${url.hash}` === targetPath)

  assert.equal(new URL(page.url()).pathname + new URL(page.url()).search + new URL(page.url()).hash, targetPath)
  assert.equal(await page.evaluate(() => localStorage.getItem('authToken')), 'deep-link-contract-token')

  await context.close()

  const expiredContext = await browser.newContext({ viewport: { width: 1280, height: 800 } })
  const expiredPage = await expiredContext.newPage()
  const expiredTarget = '/learning-profile?collect=chat&source=path#dialog'

  await expiredPage.addInitScript(() => {
    if (sessionStorage.getItem('expired-session-seeded') === '1') return
    sessionStorage.setItem('expired-session-seeded', '1')
    localStorage.setItem('authToken', 'expired-contract-token')
    localStorage.setItem('currentUser', JSON.stringify({
      id: 902,
      username: 'expired-user',
      displayName: 'Expired User',
      role: 'user',
    }))
    localStorage.setItem('appMode', 'user')
  })
  await expiredPage.route('**/api/**', async (route) => {
    const url = new URL(route.request().url())
    if (route.request().method() === 'GET' && url.pathname === '/api/learning-profile/profiles') {
      await route.fulfill({
        status: 401,
        contentType: 'application/json',
        body: JSON.stringify({ msg: 'Session expired' }),
      })
      return
    }
    await route.fulfill({ status: 200, contentType: 'application/json', body: '{}' })
  })

  await expiredPage.goto(`${baseUrl}${expiredTarget}`, { waitUntil: 'domcontentloaded' })
  await expiredPage.waitForURL(url => url.pathname === '/login')
  await expiredPage.locator('.auth-modal-panel').waitFor({ state: 'visible' })

  const expiredLoginUrl = new URL(expiredPage.url())
  assert.equal(expiredLoginUrl.searchParams.get('redirect'), expiredTarget)
  assert.equal(await expiredPage.evaluate(() => localStorage.getItem('authToken')), null)

  await expiredContext.close()
  console.log('Desktop auth deep-link restoration contract passed.')
} finally {
  await browser.close()
}
