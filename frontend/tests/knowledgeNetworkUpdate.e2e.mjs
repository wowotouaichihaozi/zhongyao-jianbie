import assert from 'node:assert/strict'
import fs from 'node:fs'
import path from 'node:path'

import { chromium } from 'playwright'

const baseUrl = process.env.E2E_BASE_URL || 'http://127.0.0.1:5088'
const outputDirectory = path.resolve('..', 'logs', 'knowledge-network-update')
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

  await page.route('**/api/effect-assessment**', route => route.fulfill({
    status: 200,
    contentType: 'application/json',
    body: JSON.stringify({ data: { profile: { id: 1, profileName: '中医学习画像' }, evidence: {}, assessment: {} } }),
  }))
  await page.route('**/api/learning-path/config**', route => route.fulfill({
    status: 200,
    contentType: 'application/json',
    body: JSON.stringify({ data: { weeks: [{ id: 'week-1', title: '中医基础', status: 'current', enabled: true }] } }),
  }))

  await page.goto(`${baseUrl}/knowledge-network?codexPreview=1`, { waitUntil: 'domcontentloaded' })
  const frame = page.frameLocator('.knowledge-network-original')
  const knowledgeCanvases = frame.locator('canvas')
  await knowledgeCanvases.first().waitFor({ state: 'visible', timeout: 20_000 })
  await page.waitForTimeout(1_500)
  const knowledgeBoxes = await knowledgeCanvases.evaluateAll(canvases => canvases.map((canvas, index) => ({
    index,
    width: canvas.getBoundingClientRect().width,
    height: canvas.getBoundingClientRect().height,
  })))
  const largestKnowledgeCanvas = knowledgeBoxes.sort((left, right) => (right.width * right.height) - (left.width * left.height))[0]
  const knowledgeCanvas = knowledgeCanvases.nth(largestKnowledgeCanvas.index)
  const knowledgeBox = await knowledgeCanvas.boundingBox()
  const knowledgeLayout = await knowledgeCanvas.evaluate(canvas => {
    const details = []
    let element = canvas
    while (element && details.length < 6) {
      const box = element.getBoundingClientRect()
      const style = getComputedStyle(element)
      details.push({ tag: element.tagName, className: element.className, width: box.width, height: box.height, display: style.display, position: style.position })
      element = element.parentElement
    }
    return details
  })
  assert.ok(
    knowledgeBox?.width > 250 && knowledgeBox?.height > 250,
    `${name}: knowledge canvas is not sized (${JSON.stringify({ knowledgeBox, knowledgeBoxes, knowledgeLayout, errors })})`,
  )
  assert.equal(await page.locator('.topnavbar').count(), 1, `${name}: duplicate knowledge navigation`)
  assert.equal(await page.evaluate(() => document.documentElement.scrollWidth > document.documentElement.clientWidth + 1), false, `${name}: knowledge page overflows horizontally`)
  await page.screenshot({ path: path.join(outputDirectory, `${name}-knowledge-network.png`), fullPage: true })

  await page.goto(`${baseUrl}/life-tree?codexPreview=1`, { waitUntil: 'domcontentloaded' })
  const lifeCanvas = page.locator('.life-tree-scene canvas').first()
  await lifeCanvas.waitFor({ state: 'visible', timeout: 20_000 })
  const lifeBox = await lifeCanvas.boundingBox()
  assert.ok(lifeBox?.width > 250 && lifeBox?.height > 250, `${name}: life-tree canvas is not sized`)
  assert.equal(await page.locator('.topnavbar').count(), 1, `${name}: duplicate life-tree navigation`)
  assert.equal(await page.evaluate(() => document.documentElement.scrollWidth > document.documentElement.clientWidth + 1), false, `${name}: life-tree page overflows horizontally`)
  await page.screenshot({ path: path.join(outputDirectory, `${name}-life-tree.png`), fullPage: true })

  assert.deepEqual(errors, [], `${name}: browser errors: ${errors.join(' | ')}`)
  await context.close()
}

try {
  await verifyViewport('desktop', { width: 1440, height: 900 })
  await verifyViewport('mobile', { width: 390, height: 844 })
  console.log('Knowledge network and Life Tree browser verification passed.')
} finally {
  await browser.close()
}
