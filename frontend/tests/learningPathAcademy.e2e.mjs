import assert from 'node:assert/strict'
import fs from 'node:fs'
import path from 'node:path'

import { chromium } from 'playwright'

const baseUrl = process.env.E2E_BASE_URL || 'http://127.0.0.1:5088'
const screenshotDir = path.resolve('../logs/learning-path-academy')
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

const completedPath = {
  version: 2,
  meta: {
    activeProfileReportId: 909,
    profileReportId: 909,
    totalWeeks: 6,
    generationState: 'complete',
    canGeneratePersonalized: true,
    activeProfileSummary: {
      id: 909,
      profileName: '中医基础进阶画像',
      version: 2,
      isActive: true,
    },
  },
  weeks: [
    { id: 'week-1', order: 1, title: '四诊与八纲辨证基础', status: 'completed' },
    { id: 'week-2', order: 2, title: '寒热真假辨析', status: 'current' },
    { id: 'week-3', order: 3, title: '脉象鉴别专项', status: 'locked' },
    { id: 'week-4', order: 4, title: '方剂配伍与医案推演', status: 'locked' },
    { id: 'week-5', order: 5, title: '综合辨证实践', status: 'locked' },
    { id: 'week-6', order: 6, title: '中医智慧综合实践', status: 'locked' },
  ],
  stages: {},
}

const browser = await chromium.launch(launchOptions)

async function newPage(viewport, configResponse = completedPath, delay = 0, contextOptions = {}) {
  const context = await browser.newContext({ viewport, ...contextOptions })
  const page = await context.newPage()
  const pageErrors = []
  page.on('pageerror', error => pageErrors.push(error.message))
  await page.route('**/api/learning-path/config*', async (route) => {
    if (delay) await new Promise(resolve => setTimeout(resolve, delay))
    if (configResponse instanceof Error) {
      await route.fulfill({ status: 500, contentType: 'application/json', body: JSON.stringify({ msg: configResponse.message }) })
      return
    }
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ code: 0, data: configResponse }) })
  })
  return { context, page, pageErrors }
}

async function verifyPopulated(name, viewport) {
  const { context, page, pageErrors } = await newPage(viewport)
  try {
    await page.goto(`${baseUrl}/learning-path/stage/overview?codexPreview=1`, { waitUntil: 'domcontentloaded' })
    await page.locator('.academy-node').first().waitFor()
    assert.equal(await page.locator('.academy-node').count(), 6)
    const entranceMotion = await page.locator('.academy-node').evaluateAll(nodes => nodes.map((node) => {
      const style = getComputedStyle(node)
      return {
        name: style.animationName,
        duration: Number.parseFloat(style.animationDuration) * 1000,
        delay: Number.parseFloat(style.animationDelay) * 1000,
      }
    }))
    assert.ok(entranceMotion.every(item => item.name.includes('academy-route-node-enter')), `${name} should apply the academy entrance animation`)
    assert.ok(entranceMotion.every((item, index) => index === 0 || item.delay > entranceMotion[index - 1].delay), `${name} academy delays should increase from left to right`)
    assert.ok(entranceMotion.at(-1).duration + entranceMotion.at(-1).delay <= 500, `${name} academy entrance should complete within 0.5 seconds`)
    const panelMotion = await page.locator('.stage-overview, .current-profile-path-switcher').evaluateAll(nodes => nodes.map((node) => {
      const style = getComputedStyle(node)
      return {
        name: style.animationName,
        duration: Number.parseFloat(style.animationDuration) * 1000,
        delay: Number.parseFloat(style.animationDelay) * 1000,
      }
    }))
    assert.equal(panelMotion.length, 2)
    assert.ok(panelMotion.every(item => item.name.includes('academy-path-card-') && item.duration + item.delay <= 500), `${name} overview cards should enter within 0.5 seconds`)
    const landmarks = ['study-hut', 'herb-garden', 'diagnosis-court', 'lecture-academy', 'archive-pagoda', 'knowledge-palace']
    const mapTitles = [
      '本草基原与药用部位',
      '药材性状观察与记录',
      '真伪药材对比鉴别',
      '显微与理化鉴别进阶',
      '炮制品与易混品辨析',
      '综合中药鉴别实践',
    ]
    for (let stage = 1; stage <= 6; stage += 1) {
      assert.equal(await page.locator(`.academy-node.stage-${stage}`).count(), 1)
      assert.equal(await page.locator(`.academy-node[data-landmark="${landmarks[stage - 1]}"]`).count(), 1)
    }
    assert.equal(await page.locator('.academy-node img').count(), 0)
    assert.equal(await page.locator('.academy-node svg .landmark').count(), 6)
    assert.deepEqual(await page.locator('.map-dot .dot-title').allTextContents(), mapTitles)
    const firstNodeLabel = await page.locator('.map-dot').first().getAttribute('aria-label')
    assert.ok(firstNodeLabel?.includes(mapTitles[0]) && firstNodeLabel.length > mapTitles[0].length, `${name} should retain the generated week title alongside the map caption`)
    await page.waitForTimeout(520)
    const firstBox = await page.locator('.academy-node').first().boundingBox()
    const lastBox = await page.locator('.academy-node').last().boundingBox()
    assert.ok(lastBox.width > firstBox.width * 1.05, `${name} academy milestones should grow gradually`)
    assert.ok(lastBox.width < firstBox.width * 1.15, `${name} academy milestone growth should remain restrained`)
    assert.equal(await page.evaluate(async () => (await fetch('/learning-path-academy-background-v1.png')).status), 200)
    await page.locator('.map-dot').last().hover()
    await page.waitForTimeout(420)
    const liftedBox = await page.locator('.academy-node').last().boundingBox()
    const liftTransforms = await page.locator('.academy-node').last().evaluate(node => ({
      node: getComputedStyle(node).transform,
      parentHover: node.parentElement.matches(':hover'),
    }))
    if (name === 'desktop') {
      assert.ok(liftedBox.y < lastBox.y - 12, `${name} academy milestone should visibly lift on hover (${lastBox.y} -> ${liftedBox.y}; ${JSON.stringify(liftTransforms)})`)
    }
    const overflow = await page.evaluate(() => document.documentElement.scrollWidth > window.innerWidth + 1)
    assert.equal(overflow, false, `${name} should not create horizontal overflow`)
    assert.deepEqual(pageErrors, [], `${name} page errors: ${pageErrors.join('; ')}`)
    await page.screenshot({ path: path.join(screenshotDir, `${name}-populated.png`), fullPage: true })
  } finally {
    await context.close()
  }
}

async function verifyReducedMotion() {
  const { context, page, pageErrors } = await newPage(
    { width: 1440, height: 900 },
    completedPath,
    0,
    { reducedMotion: 'reduce' },
  )
  try {
    await page.goto(`${baseUrl}/learning-path/stage/overview?codexPreview=1`, { waitUntil: 'domcontentloaded' })
    await page.locator('.academy-node').first().waitFor()
    assert.deepEqual(await page.locator('.academy-node').evaluateAll(nodes => nodes.map(node => getComputedStyle(node).animationName)), Array(6).fill('none'))
    assert.deepEqual(await page.locator('.stage-overview, .current-profile-path-switcher').evaluateAll(nodes => nodes.map(node => getComputedStyle(node).animationName)), ['none', 'none'])
    assert.deepEqual(pageErrors, [], `reduced-motion page errors: ${pageErrors.join('; ')}`)
  } finally {
    await context.close()
  }
}

async function verifyStates() {
  const loading = await newPage({ width: 1440, height: 900 }, completedPath, 900)
  try {
    await loading.page.goto(`${baseUrl}/learning-path/stage/overview?codexPreview=1`, { waitUntil: 'domcontentloaded' })
    await loading.page.locator('.map-loading').waitFor()
    await loading.page.screenshot({ path: path.join(screenshotDir, 'desktop-loading.png'), fullPage: true })
  } finally {
    await loading.context.close()
  }

  const empty = await newPage({ width: 390, height: 844 }, {
    version: 2,
    meta: { activeProfileReportId: null, canGeneratePersonalized: false },
    weeks: [],
    stages: {},
  })
  try {
    await empty.page.goto(`${baseUrl}/learning-path/stage/overview?codexPreview=1`, { waitUntil: 'domcontentloaded' })
    await empty.page.locator('.empty-path-state').waitFor()
    await empty.page.screenshot({ path: path.join(screenshotDir, 'mobile-empty.png'), fullPage: true })
  } finally {
    await empty.context.close()
  }

  const failed = await newPage({ width: 1440, height: 900 }, new Error('测试路径读取失败'))
  try {
    await failed.page.goto(`${baseUrl}/learning-path/stage/overview?codexPreview=1`, { waitUntil: 'domcontentloaded' })
    await failed.page.locator('.path-load-error').waitFor()
    assert.equal(await failed.page.getByRole('button', { name: /重新加载/ }).count(), 1)
    await failed.page.screenshot({ path: path.join(screenshotDir, 'desktop-error.png'), fullPage: true })
  } finally {
    await failed.context.close()
  }
}

try {
  await verifyPopulated('desktop', { width: 1440, height: 900 })
  await verifyPopulated('mobile', { width: 390, height: 844 })
  await verifyStates()
  await verifyReducedMotion()
  console.log('learning-path academy map verified at desktop/mobile widths, reduced motion, and across loading, empty, and error states')
} finally {
  await browser.close()
}
