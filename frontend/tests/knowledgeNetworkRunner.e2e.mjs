import assert from 'node:assert/strict'
import fs from 'node:fs'
import path from 'node:path'
import { chromium } from 'playwright'

const baseUrl = process.env.E2E_BASE_URL || 'http://127.0.0.1:5088'
const outputDirectory = path.resolve('..', 'logs', 'knowledge-network-runner')
const browserCandidates = [
  'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe',
  'C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe',
  'C:\\Program Files\\Microsoft\\Edge\\Application\\msedge.exe',
  'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe',
]
const launchOptions = { headless: true }
if (!fs.existsSync(chromium.executablePath())) {
  launchOptions.executablePath = browserCandidates.find(candidate => fs.existsSync(candidate))
}
assert.ok(launchOptions.executablePath || fs.existsSync(chromium.executablePath()), 'No Chromium browser is available.')
fs.mkdirSync(outputDirectory, { recursive: true })

const browser = await chromium.launch(launchOptions)

async function verifyViewport(name, viewport) {
  const context = await browser.newContext({ viewport })
  const page = await context.newPage()
  const errors = []
  page.on('pageerror', error => errors.push(error.message))
  page.on('console', message => {
    if (message.type() === 'error') errors.push(message.text())
  })

  await page.route('**/api/**', route => route.fulfill({
    status: 200,
    contentType: 'application/json',
    body: JSON.stringify({ code: 0, data: {} }),
  }))

  await page.goto(`${baseUrl}/knowledge-network?codexPreview=1`, { waitUntil: 'domcontentloaded' })
  const frame = page.frameLocator('.knowledge-network-original')
  const canvas = frame.locator('canvas').first()
  await canvas.waitFor({ state: 'visible', timeout: 20_000 })
  await page.waitForFunction(() => {
    const frame = document.querySelector('.knowledge-network-original')
    const canvas = frame?.contentDocument?.querySelector('canvas')
    return Boolean(canvas && canvas.getBoundingClientRect().width > 250 && canvas.getBoundingClientRect().height > 250)
  }, undefined, { timeout: 20_000 })
  const canvasBox = await canvas.boundingBox()
  assert.ok(canvasBox && canvasBox.width > 250 && canvasBox.height > 250, `${name}: canvas is undersized`)
  await page.screenshot({ path: path.join(outputDirectory, `${name}-overview.png`), fullPage: true })
  await page.mouse.move(canvasBox.x + canvasBox.width * 0.6, canvasBox.y + canvasBox.height * 0.5)
  await page.mouse.down()
  await page.mouse.move(canvasBox.x + canvasBox.width * 0.7, canvasBox.y + canvasBox.height * 0.54, { steps: 6 })
  await page.mouse.up()

  if (viewport.width < 768) await frame.getByRole('button', { name: '打开星图导航' }).click()
  await frame.getByRole('button', { name: /基础理论/ }).click()
  await page.waitForTimeout(1200)
  const domainCanvas = frame.locator('[data-active-domain="基础理论"]')
  await domainCanvas.waitFor({ state: 'visible', timeout: 10_000 })
  const domainLabels = frame.locator('[data-active-domain-label="基础理论"]')
  await domainLabels.first().waitFor({ state: 'visible', timeout: 10_000 })
  assert.ok(await domainLabels.count() >= 10, `${name}: domain focus did not expose its topic cluster`)
  const domainCanvasBox = await canvas.boundingBox()
  const domainLabelBoxes = await domainLabels.evaluateAll(elements => elements.map(element => {
    const box = element.getBoundingClientRect()
    return { x: box.x + box.width / 2, y: box.y + box.height / 2 }
  }))
  const domainMean = domainLabelBoxes.reduce((sum, point) => ({ x: sum.x + point.x, y: sum.y + point.y }), { x: 0, y: 0 })
  domainMean.x /= domainLabelBoxes.length
  domainMean.y /= domainLabelBoxes.length
  assert.ok(domainCanvasBox, `${name}: domain focus canvas geometry is unavailable`)
  assert.ok(
    Math.abs(domainMean.x - (domainCanvasBox.x + domainCanvasBox.width / 2)) < 180
      && Math.abs(domainMean.y - (domainCanvasBox.y + domainCanvasBox.height / 2)) < 180,
    `${name}: domain topic cluster did not move near the canvas center`,
  )
  await frame.getByRole('button', { name: '阴阳学说', exact: true }).click()
  await frame.getByRole('button', { name: '概念基础', exact: true }).click()
  await frame.getByRole('button', { name: /定义与边界/ }).first().click()
  await page.waitForTimeout(750)

  if (viewport.width < 768) {
    await frame.getByText('具体知识点', { exact: true }).first().waitFor({ state: 'visible', timeout: 10_000 })
    await frame.getByRole('button', { name: /定义与边界/ }).first().waitFor({ state: 'visible', timeout: 10_000 })
    assert.equal(await frame.getByRole('button', { name: '关闭星图导航' }).count(), 1, `${name}: leaf selection closed the navigation`)
  }

  const detail = frame.locator('[data-knowledge-status="available"]:visible').first()
  await detail.waitFor({ state: 'visible', timeout: 10_000 })
  assert.match(await detail.innerText(), /已收录学习说明/)
  assert.match(await detail.innerText(), /阴阳属性/)

  await frame.getByRole('button', { name: '清空搜索' }).count().then(async count => {
    if (count > 0) await frame.getByRole('button', { name: '清空搜索' }).click()
  })
  const search = frame.getByRole('textbox', { name: '搜索知识点、主题或知识域' })
  await search.fill('阴阳属性')
  await frame.locator('[data-search-result]').first().waitFor({ state: 'visible', timeout: 10_000 })
  await frame.locator('[data-search-result]').first().click()
  await page.waitForTimeout(400)
  assert.match(await frame.locator('[data-knowledge-status="available"]:visible').first().innerText(), /阴阳属性/)
  const selectedLabel = frame.locator('[data-selected-node-label]').first()
  const selectedAnchor = frame.locator('[data-selected-node-anchor]').first()
  await selectedLabel.waitFor({ state: 'visible', timeout: 10_000 })
  await selectedAnchor.waitFor({ state: 'attached', timeout: 10_000 })
  await page.waitForTimeout(700)
  const selectedAnchorBox = await selectedAnchor.boundingBox()
  const focusedCanvasBox = await canvas.boundingBox()
  assert.ok(selectedAnchorBox && focusedCanvasBox, `${name}: selected-node focus geometry is unavailable`)
  assert.ok(
    Math.abs((selectedAnchorBox.x + selectedAnchorBox.width / 2) - (focusedCanvasBox.x + focusedCanvasBox.width / 2)) < 70
      && Math.abs((selectedAnchorBox.y + selectedAnchorBox.height / 2) - (focusedCanvasBox.y + focusedCanvasBox.height / 2)) < 70,
    `${name}: selected node did not move near the canvas center`,
  )
  assert.equal(await page.evaluate(() => document.documentElement.scrollWidth > document.documentElement.clientWidth + 1), false, `${name}: route overflows horizontally`)
  assert.deepEqual(errors, [], `${name}: browser errors: ${errors.join(' | ')}`)
  await page.screenshot({ path: path.join(outputDirectory, `${name}-knowledge-network-runner.png`), fullPage: true })
  await context.close()
}

try {
  await verifyViewport('desktop', { width: 1440, height: 900 })
  await verifyViewport('mobile', { width: 390, height: 844 })
  console.log('knowledge-network runner desktop/mobile navigation and content contract passed')
} finally {
  await browser.close()
}
