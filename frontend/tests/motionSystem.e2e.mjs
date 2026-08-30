import assert from 'node:assert/strict'
import fs from 'node:fs'
import path from 'node:path'

import { chromium } from 'playwright'

const baseUrl = process.env.E2E_BASE_URL || 'http://127.0.0.1:5088'
const screenshotDir = path.resolve('../logs/motion-system')
const systemChromiumCandidates = [
  'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe',
  'C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe',
  'C:\\Program Files\\Microsoft\\Edge\\Application\\msedge.exe',
  'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe',
]
const launchOptions = { headless: true }

if (!fs.existsSync(chromium.executablePath())) {
  launchOptions.executablePath = systemChromiumCandidates.find(candidate => fs.existsSync(candidate))
}

assert.ok(launchOptions.executablePath || fs.existsSync(chromium.executablePath()), 'Chromium is required')
fs.mkdirSync(screenshotDir, { recursive: true })

const browser = await chromium.launch(launchOptions)

async function openRoute(viewport, reducedMotion = 'no-preference') {
  const context = await browser.newContext({ viewport, reducedMotion })
  const page = await context.newPage()
  const pageErrors = []
  page.on('pageerror', error => pageErrors.push(error.message))

  await page.goto(`${baseUrl}/learning-profile?codexPreview=1`, { waitUntil: 'domcontentloaded' })
  await page.locator('body > #app').waitFor()
  await page.waitForTimeout(650)
  return { context, page, pageErrors }
}

async function assertNoPageOverflow(page, label) {
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth > window.innerWidth + 1)
  assert.equal(overflow, false, `${label} should not create horizontal page overflow`)
}

async function verifyDesktop() {
  const { context, page, pageErrors } = await openRoute({ width: 1440, height: 900 })

  try {
    await page.locator('.nav-links a[href="/personalized-resources"]').click()
    await page.waitForURL('**/personalized-resources')
    await page.locator('.resources-page').waitFor()
    const cardAnimation = await page.locator('.resource-tool-card').first().evaluate(element => (
      getComputedStyle(element).animationName
    ))
    assert.equal(cardAnimation, 'motion-surface-enter', 'resource cards should use the shared insertion motion')

    await page.locator('.xiaozhi-orb').click()
    await page.waitForFunction(() => Boolean(document.querySelector('.motion-pop-enter-active')))
    await page.locator('.xiaozhi-window').waitFor()
    const popDuration = await page.locator('.xiaozhi-window').evaluate(element => (
      getComputedStyle(element).transitionDuration
    ))
    assert.notEqual(popDuration, '0s', 'assistant window should have a visible transition')

    await page.locator('.mode-tabs button').nth(1).click()
    await page.waitForFunction(() => Boolean(document.querySelector('.motion-panel-enter-active')))
    await page.waitForTimeout(320)
    assert.equal(await page.locator('.status-panel').isVisible(), true, 'assistant status panel should settle after switching')

    await page.locator('.window-head-actions .icon-btn').last().click()
    await page.waitForFunction(() => Boolean(document.querySelector('.motion-pop-leave-active')))
    await page.locator('.xiaozhi-window').waitFor({ state: 'detached' })

    await assertNoPageOverflow(page, 'desktop motion pass')
    await page.screenshot({ path: path.join(screenshotDir, 'desktop-resources.png'), fullPage: true })
    assert.deepEqual(pageErrors, [], `desktop page errors: ${pageErrors.join('; ')}`)
  } finally {
    await context.close()
  }
}

async function verifyMobile() {
  const { context, page, pageErrors } = await openRoute({ width: 390, height: 844 })

  try {
    await page.locator('.mobile-bottom-nav a[href="/personalized-resources"]').click()
    await page.waitForURL('**/personalized-resources')
    await page.locator('.resources-page').waitFor()
    await assertNoPageOverflow(page, 'mobile motion pass')
    await page.screenshot({ path: path.join(screenshotDir, 'mobile-resources.png'), fullPage: true })
    assert.deepEqual(pageErrors, [], `mobile page errors: ${pageErrors.join('; ')}`)
  } finally {
    await context.close()
  }
}

async function verifyRepeatedNavigationNeverBlanks() {
  const { context, page, pageErrors } = await openRoute({ width: 1280, height: 800 })
  const destinations = [
    ['/personalized-resources', '.resources-page'],
    ['/effect-assessment', '.assessment-page'],
    ['/learning-profile', '.lp-page'],
    ['/personalized-resources', '.resources-page'],
  ]

  try {
    for (const [href, rootSelector] of destinations) {
      await page.locator(`.nav-links a[href="${href}"]`).click()
      await page.waitForURL(`**${href}`)
      const root = page.locator(rootSelector)
      await root.waitFor()
      assert.equal(await root.isVisible(), true, `${href} should keep a visible route root`)
      assert.ok((await root.innerText()).trim().length > 0, `${href} should not render a blank content area`)
    }
    assert.deepEqual(pageErrors, [], `repeated navigation page errors: ${pageErrors.join('; ')}`)
  } finally {
    await context.close()
  }
}

async function verifyReducedMotion() {
  const { context, page } = await openRoute({ width: 1024, height: 768 }, 'reduce')

  try {
    await page.locator('.xiaozhi-orb').click()
    await page.locator('.xiaozhi-window').waitFor()
    const durations = await page.locator('.xiaozhi-window').evaluate(element => ({
      animation: getComputedStyle(element).animationDuration,
      transition: getComputedStyle(element).transitionDuration,
    }))
    assert.match(durations.animation, /0\.0*1ms|0\.00001s|1e-05s/)
    assert.match(durations.transition, /0\.0*1ms|0\.00001s|1e-05s/)
  } finally {
    await context.close()
  }
}

try {
  await verifyDesktop()
  await verifyMobile()
  await verifyReducedMotion()
  await verifyRepeatedNavigationNeverBlanks()
  console.log('motion system verified at desktop/mobile widths with reduced-motion fallback')
} finally {
  await browser.close()
}
