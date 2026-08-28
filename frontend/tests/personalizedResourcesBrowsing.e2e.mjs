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
  await page.locator('.archive-result-line').waitFor({ state: 'visible' })

  const cards = page.locator('.resource-cover-card')
  const visibleCardCount = await cards.count()
  assert.ok(visibleCardCount > 0 && visibleCardCount <= 9, `expected 1-9 cards, received ${visibleCardCount}`)
  assert.equal(await page.locator('.history-search').count(), 1)
  assert.equal(await page.locator('.history-pagination').count(), 1)
  assert.equal(await page.locator('.resource-launcher-grid').count(), 1)
  assert.equal(await page.locator('.resource-gallery').count(), 1)
  const liveCoverCount = await page.locator('.resource-live-cover').count()
  const staticCoverCount = await page.locator('.resource-static-cover').count()
  assert.equal(liveCoverCount + staticCoverCount, visibleCardCount)
  assert.ok(staticCoverCount > 0, 'video resources did not use static covers')
  assert.equal(await page.locator('.resource-tool-sidebar').count(), 0)
  assert.equal(await page.locator('.resource-table-head').count(), 0)
  assert.equal(await page.locator('.resource-card').count(), 0)
  assert.equal(await page.locator('.resource-tool-card').count(), 0)
  assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth), true)
  await page.locator('.resource-live-cover.loaded').first().waitFor({ state: 'visible', timeout: 15_000 })
  assert.ok(await page.locator('.resource-live-cover.loaded').count() > 0, 'no real page cover finished loading')
  const assistantBox = await page.locator('.xiaozhi-float').boundingBox()
  assert.ok(assistantBox && assistantBox.x > 1000 && assistantBox.y > 500, 'floating assistant overlaps the page header')
  const firstCardStyle = await cards.first().evaluate(element => {
    const style = getComputedStyle(element)
    return { borderRadius: style.borderRadius, boxShadow: style.boxShadow }
  })
  assert.equal(firstCardStyle.borderRadius, '6px')

  const embeddedControlStyles = await page.evaluate(() => {
    const searchInput = document.querySelector('.archive-toolbar .history-search input')
    const typeSelect = document.querySelector('.type-filter select')
    return {
      searchBorder: searchInput ? getComputedStyle(searchInput).borderTopWidth : null,
      searchShadow: searchInput ? getComputedStyle(searchInput).boxShadow : null,
      selectBorder: typeSelect ? getComputedStyle(typeSelect).borderTopWidth : null,
      selectShadow: typeSelect ? getComputedStyle(typeSelect).boxShadow : null,
    }
  })
  assert.deepEqual(embeddedControlStyles, {
    searchBorder: '0px',
    searchShadow: 'none',
    selectBorder: '0px',
    selectShadow: 'none',
  })

  const firstTitle = (await cards.first().locator('.resource-cover-copy h3').textContent())?.trim() || ''
  assert.ok(firstTitle, 'first history resource has no title')
  await page.locator('.history-search input').fill(firstTitle.slice(0, Math.min(firstTitle.length, 8)))
  await page.waitForTimeout(150)
  assert.ok(await cards.count() >= 1, 'search removed the matching resource')

  await page.locator('.history-search button').click()
  await page.waitForTimeout(100)
  assert.equal(await page.locator('.history-search input').inputValue(), '')

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
