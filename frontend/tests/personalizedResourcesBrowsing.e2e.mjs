import assert from 'node:assert/strict'
import fs from 'node:fs'
import path from 'node:path'
import { chromium } from 'playwright'

const baseUrl = process.env.RESOURCE_E2E_BASE_URL || 'http://127.0.0.1:3000'
const outputDir = path.resolve('test-output', 'personalized-resources')
fs.mkdirSync(outputDir, { recursive: true })

const browserCandidates = [
  process.env.PLAYWRIGHT_BROWSER_PATH,
  'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe',
  'C:\\Program Files\\Microsoft\\Edge\\Application\\msedge.exe',
  'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe',
].filter(Boolean)
const executablePath = browserCandidates.find(candidate => fs.existsSync(candidate))
const browser = await chromium.launch({ headless: true, ...(executablePath ? { executablePath } : {}) })
const page = await browser.newPage({ viewport: { width: 1440, height: 900 }, deviceScaleFactor: 1 })

try {
  const loginResponse = await page.request.post(`${baseUrl}/api/auth/login`, {
    data: { username: 'admin123', password: 'admin123' },
  })
  assert.equal(loginResponse.ok(), true, `login failed with HTTP ${loginResponse.status()}`)
  const session = await loginResponse.json()
  assert.ok(session.token, 'login response did not include a token')

  await page.addInitScript(payload => {
    localStorage.setItem('authToken', payload.token)
    localStorage.setItem('currentUser', JSON.stringify(payload.user))
    localStorage.setItem('appMode', 'user')
  }, {
    token: session.token,
    user: {
      id: session.id,
      username: session.username,
      displayName: session.displayName,
      role: session.role,
      avatarUrl: session.avatarUrl,
    },
  })

  await page.goto(`${baseUrl}/personalized-resources`, { waitUntil: 'networkidle' })
  await page.locator('.resource-card').first().waitFor({ state: 'visible' })

  const cards = page.locator('.resource-card.topic-card')
  const visibleCardCount = await cards.count()
  assert.equal(visibleCardCount, 8, `expected eight topic cards, received ${visibleCardCount}`)
  assert.equal(await page.locator('.resource-tool-card').count(), 6)
  assert.equal(await page.getByRole('link', { name: '药材模型识别' }).getAttribute('href'), '/personalized-resources/herb-model')
  assert.equal(await page.locator('.history-search').count(), 0)
  assert.equal(await page.locator('.history-pagination').count(), 0)
  assert.equal(await page.locator('.topic-cover-texture').count(), 8)
  assert.equal(await page.locator('.topic-cover-icon-image').count(), 8)
  await page.waitForFunction(() => [...document.querySelectorAll('.topic-cover-texture, .topic-cover-icon-image')]
    .every(image => image.complete && image.naturalWidth > 0))
  assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth), true)
  const assistantBox = await page.locator('.xiaozhi-float').boundingBox()
  assert.ok(assistantBox && assistantBox.x > 1000 && assistantBox.y > 500, 'floating assistant overlaps the page header')
  const firstCardStyle = await cards.first().evaluate(element => {
    const style = getComputedStyle(element)
    return { borderRadius: style.borderRadius, boxShadow: style.boxShadow }
  })
  assert.equal(firstCardStyle.borderRadius, '8px')

  await page.screenshot({
    path: path.join(outputDir, 'personalized-resources-desktop.png'),
    fullPage: true,
  })

  await page.locator('.resources-page').evaluate(element => {
    element.scrollTop = Math.max(0, element.scrollHeight - element.clientHeight)
  })
  await page.waitForTimeout(200)
  await page.screenshot({
    path: path.join(outputDir, 'personalized-resources-lower-cards.png'),
  })

  console.log(`PASS cards=${visibleCardCount} screenshot=${path.join(outputDir, 'personalized-resources-desktop.png')}`)
} finally {
  await browser.close()
}
