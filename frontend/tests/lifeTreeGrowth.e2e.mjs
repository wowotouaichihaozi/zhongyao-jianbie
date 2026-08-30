import assert from 'node:assert/strict'
import fs from 'node:fs'
import path from 'node:path'

import { chromium } from 'playwright'

const baseUrl = process.env.E2E_BASE_URL || 'http://127.0.0.1:5088'
const outputDirectory = path.resolve('..', 'logs', 'life-tree-growth')
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

const assessmentFixture = {
  profile: { id: 29, profileName: '本草辨识进阶画像', isActive: true },
  evidence: {
    pathProgress: { trackedNodes: 18, completedNodes: 7, updatedAt: '2026-08-29T12:00:00Z' },
    examResults: [{ accuracy: 82, createdAt: '2026-08-29T11:00:00Z' }],
  },
  assessment: {
    labels: ['基础知识', '辨证思维', '方药应用', '医案实践', '学习投入', '综合素养'],
    radarScores: [3.8, 3.2, 4.1, 2.9, 3.5, 4.4],
    masteryRate: 68.4,
    achievementRate: 61.2,
    evidenceCount: 26,
    confidenceLevel: 'high',
    knowledgeHeatmap: [{ knowledgePoint: '八纲辨证', attempts: 5, masteryRate: 80, status: 'mastered' }],
  },
}

const weekTitles = ['中医基础理论', '四诊信息归纳', '八纲辨证', '中药性味归经', '方剂组成与配伍', '综合医案辨析']
const weekStatuses = ['completed', 'current', 'locked', 'locked', 'locked', 'locked']
const stageNodeStatuses = [
  ['done', 'done', 'done', 'done'],
  ['done', 'current', 'current', 'locked'],
  ['locked', 'locked', 'locked'],
  ['locked', 'locked', 'locked'],
  ['locked', 'locked', 'locked'],
  ['locked', 'locked', 'locked'],
]
const pathFixture = {
  meta: { profileReportId: 29, savedAt: '2026-08-29T12:00:00Z' },
  weeks: weekTitles.map((title, index) => ({
    id: `week-${index + 1}`,
    order: index + 1,
    weekLabel: `第${['一', '二', '三', '四', '五', '六'][index]}周`,
    title,
    description: `${title}的画像驱动学习目标`,
    status: weekStatuses[index],
    enabled: true,
  })),
  stages: Object.fromEntries(stageNodeStatuses.map((statuses, index) => [
    `week-${index + 1}`,
    { nodes: statuses.map((status, nodeIndex) => ({
      id: `${index + 1}-${nodeIndex + 1}`,
      cacheKey: `week-${index + 1}-node-${nodeIndex + 1}`,
      status,
    })) },
  ])),
}

const initialNodeCaches = {
  'week-2-node-2': {
    cacheKey: 'week-2-node-2',
    stageId: 'week-2',
    nodeId: '2-2',
    status: 'complete',
    completionSource: 'resource-generation',
    lastOpenedAt: 1788074521000,
    updatedAt: '2026-08-30T09:00:00Z',
  },
}

function jsonResponse(data, status = 200) {
  return { status, contentType: 'application/json', body: JSON.stringify(status === 200 ? { data } : { msg: data }) }
}

async function canvasHasRenderedPixels(canvas) {
  return canvas.evaluate(async (element) => {
    await new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)))
    const gl = element.getContext('webgl2') || element.getContext('webgl')
    if (!gl) return false
    const width = Math.min(96, element.width)
    const height = Math.min(96, element.height)
    const pixels = new Uint8Array(width * height * 4)
    gl.readPixels(
      Math.max(0, Math.floor((element.width - width) / 2)),
      Math.max(0, Math.floor((element.height - height) / 2)),
      width,
      height,
      gl.RGBA,
      gl.UNSIGNED_BYTE,
      pixels,
    )
    let minimum = 255
    let maximum = 0
    for (let index = 0; index < pixels.length; index += 4) {
      const brightness = pixels[index] + pixels[index + 1] + pixels[index + 2]
      minimum = Math.min(minimum, brightness)
      maximum = Math.max(maximum, brightness)
    }
    return maximum - minimum > 24
  })
}

async function verifyViewport(browser, name, viewport) {
  const context = await browser.newContext({ viewport })
  const page = await context.newPage()
  const errors = []
  const fruitResponses = []
  let scenario = 'populated'
  page.on('pageerror', error => errors.push(error.message))
  page.on('console', message => {
    const isExpectedApiFailure = ['partial', 'error'].includes(scenario)
      && message.text().startsWith('Failed to load resource: the server responded with a status of 503')
    if (message.type() === 'error' && !isExpectedApiFailure) errors.push(message.text())
  })
  page.on('response', response => {
    if (response.url().endsWith('/models/life-tree/apple08.fbx')) fruitResponses.push(response.status())
  })

  await page.route('**/api/effect-assessment**', async route => {
    if (scenario === 'loading') await new Promise(resolve => setTimeout(resolve, 1_200))
    if (scenario === 'error') return route.fulfill(jsonResponse('效果评估加载失败', 503))
    return route.fulfill(jsonResponse(scenario === 'empty' ? { profile: {}, evidence: {}, assessment: {} } : assessmentFixture))
  })
  await page.route('**/api/learning-path/config**', async route => {
    if (scenario === 'loading') await new Promise(resolve => setTimeout(resolve, 1_200))
    if (scenario === 'error' || scenario === 'partial') return route.fulfill(jsonResponse('学习路径加载失败', 503))
    return route.fulfill(jsonResponse(scenario === 'empty' ? {} : pathFixture))
  })
  await page.route('**/api/learning-path/node-caches**', async route => {
    return route.fulfill(jsonResponse(scenario === 'empty' ? { caches: {} } : { caches: initialNodeCaches }))
  })

  const openScenario = async nextScenario => {
    scenario = nextScenario
    await page.goto(`${baseUrl}/life-tree?codexPreview=1&state=${nextScenario}&t=${Date.now()}`, { waitUntil: 'domcontentloaded' })
  }

  await openScenario('populated')
  const canvas = page.locator('.life-tree-growth-scene canvas').first()
  await canvas.waitFor({ state: 'visible', timeout: 20_000 })
  await page.getByLabel('当前学习画像').waitFor({ state: 'visible' })
  await page.waitForTimeout(650)
  const canvasBox = await canvas.boundingBox()
  assert.ok(canvasBox?.width > 250 && canvasBox?.height > 250, `${name}: growth-tree canvas is not sized`)
  assert.equal(await page.locator('.life-tree-growth-scene').getAttribute('data-fruit-count'), '6', `${name}: six fruits are not bound`)
  assert.equal(await page.locator('.profile-dimension-list > div').count(), 6, `${name}: persistent learning profile does not show six dimensions`)
  assert.deepEqual(
    await page.locator('.profile-dimension-list span').allTextContents(),
    ['基础知识', '辨证思维', '方药应用', '医案实践', '学习投入', '综合素养'],
  )
  assert.deepEqual(await page.locator('.profile-dimension-list small').allTextContents(), ['3.8', '3.2', '4.1', '2.9', '3.5', '4.4'])
  assert.ok(await page.locator('.profile-radar-value').getAttribute('points'), `${name}: profile radar has no score outline`)
  assert.equal(await page.getByRole('link', { name: /完整画像/ }).count(), 1, `${name}: full profile route is missing`)
  const profileBox = await page.locator('.tree-status').boundingBox()
  const weekPathBox = await page.locator('.week-path').boundingBox()
  assert.ok(profileBox && weekPathBox && profileBox.y + profileBox.height <= weekPathBox.y, `${name}: learning profile overlaps the week path`)
  assert.equal(await page.locator('.week-path button').count(), 6, `${name}: six week fruits are not present`)
  assert.deepEqual(await page.locator('.week-path button em').allTextContents(), ['100%', '50%', '0%', '0%', '0%', '0%'])
  assert.equal(await page.getByRole('button', { name: /自动旋转/ }).count(), 0, `${name}: automatic rotation control still exists`)
  assert.ok(await canvasHasRenderedPixels(canvas), `${name}: WebGL canvas is blank`)
  assert.equal(await page.locator('.topnavbar').count(), 1, `${name}: duplicate navigation`)
  assert.equal(await page.evaluate(() => document.documentElement.scrollWidth > document.documentElement.clientWidth + 1), false, `${name}: populated route overflows horizontally`)
  await page.screenshot({ path: path.join(outputDirectory, `${name}-populated.png`), fullPage: true })
  await page.locator('.profile-link').click()
  assert.equal(await page.locator('.profile-root-list > div').count(), 6, `${name}: six profile dimensions are not available`)
  await page.getByRole('button', { name: '关闭节点详情' }).click()
  await page.locator('.week-path button').nth(1).evaluate(element => element.click())
  await page.getByRole('heading', { name: '四诊信息归纳' }).waitFor({ state: 'visible' })
  await page.getByText('查看成熟依据', { exact: true }).click()
  await page.getByText('本周共 4 个可学习任务，已有 2 个学习完成记录，其中 1 个已有学习者实际操作记录。每个路径节点只计一次。').waitFor({ state: 'visible' })
  await page.screenshot({ path: path.join(outputDirectory, `${name}-interaction.png`), fullPage: true })

  await page.evaluate((storageKey) => {
    const caches = JSON.parse(localStorage.getItem(storageKey) || '{}')
    caches['week-2-node-3'] = {
      cacheKey: 'week-2-node-3',
      stageId: 'week-2',
      nodeId: '2-3',
      status: 'complete',
      completionSource: 'learning-feedback',
      learningFeedback: { outcome: 'completed' },
      updatedAt: Date.now(),
    }
    localStorage.setItem(storageKey, JSON.stringify(caches))
    window.dispatchEvent(new CustomEvent('learning-path-node-cache-updated', {
      detail: { cacheKey: 'week-2-node-3', entry: caches['week-2-node-3'] },
    }))
  }, 'qianzhi-learning-path-node-results:v1')
  await page.getByText('第二周果实成熟度提升：50% → 75%', { exact: true }).waitFor({ state: 'visible', timeout: 8_000 })
  assert.equal(await page.locator('.week-path button').nth(1).locator('em').textContent(), '75%', `${name}: feedback did not grow week two fruit`)
  await page.getByText(/其中 1 个已提交完成学习反馈/).waitFor({ state: 'visible' })
  await page.waitForTimeout(1_200)
  await page.screenshot({ path: path.join(outputDirectory, `${name}-feedback-growth.png`), fullPage: true })

  await page.evaluate((storageKey) => {
    const caches = JSON.parse(localStorage.getItem(storageKey) || '{}')
    caches['week-2-node-4'] = {
      cacheKey: 'week-2-node-4',
      stageId: 'week-2',
      nodeId: '2-4',
      status: 'complete',
      completionSource: 'learning-feedback',
      learningFeedback: { outcome: 'completed' },
      updatedAt: Date.now(),
    }
    localStorage.setItem(storageKey, JSON.stringify(caches))
  }, 'qianzhi-learning-path-node-results:v1')
  await page.reload({ waitUntil: 'domcontentloaded' })
  await page.getByText('第二周果实成熟度提升：75% → 100%', { exact: true }).waitFor({ state: 'visible', timeout: 12_000 })
  assert.equal(await page.locator('.sync-note em').textContent(), '第二周 75→100%', `${name}: compact growth summary is incorrect`)
  assert.equal(await page.locator('.week-path button').nth(1).locator('em').textContent(), '100%', `${name}: route return did not preserve growth comparison`)
  await page.waitForTimeout(1_200)
  await page.screenshot({ path: path.join(outputDirectory, `${name}-return-growth.png`), fullPage: true })

  await openScenario('empty')
  await page.getByText('六个果位已经建立，等待画像路径').waitFor({ state: 'visible', timeout: 20_000 })
  assert.equal(await page.locator('.life-tree-growth-scene').getAttribute('data-fruit-count'), '6', `${name}: empty route lost fruit positions`)
  assert.equal(await page.evaluate(() => document.documentElement.scrollWidth > document.documentElement.clientWidth + 1), false, `${name}: empty route overflows horizontally`)

  await openScenario('partial')
  await page.getByText(/学习路径加载失败；当前仅显示画像与评估证据/).waitFor({ state: 'visible', timeout: 20_000 })
  assert.equal(await page.locator('.life-tree-growth-scene').getAttribute('data-fruit-count'), '6', `${name}: partial route lost fruit positions`)

  await openScenario('error')
  await page.getByText('学习成长树暂时无法加载').waitFor({ state: 'visible', timeout: 20_000 })
  assert.equal(await page.getByRole('button', { name: /重新加载/ }).count(), 1, `${name}: error retry is missing`)

  scenario = 'loading'
  const navigation = page.goto(`${baseUrl}/life-tree?codexPreview=1&state=loading&t=${Date.now()}`, { waitUntil: 'domcontentloaded' })
  await page.getByText('正在读取画像与六周路径').waitFor({ state: 'visible', timeout: 3_000 })
  await navigation
  await page.locator('.life-tree-growth-scene canvas').waitFor({ state: 'visible', timeout: 20_000 })
  await page.getByLabel('当前学习画像').waitFor({ state: 'visible' })

  assert.ok(fruitResponses.some(status => status === 200), `${name}: FBX model did not return HTTP 200`)
  assert.deepEqual(errors, [], `${name}: browser errors: ${errors.join(' | ')}`)
  await context.close()
}

const browser = await chromium.launch(launchOptions)
try {
  await verifyViewport(browser, 'desktop', { width: 1440, height: 900 })
  await verifyViewport(browser, 'mobile', { width: 390, height: 844 })
  console.log('Life Tree six-fruit browser verification passed.')
} finally {
  await browser.close()
}
