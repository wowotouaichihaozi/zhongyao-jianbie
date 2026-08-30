import assert from 'node:assert/strict'
import fs from 'node:fs'
import path from 'node:path'

import { chromium } from 'playwright'

const baseUrl = process.env.E2E_BASE_URL || 'http://127.0.0.1:5088'
const screenshotDir = path.resolve('../logs/personalized-resource-workspace')
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

const task = {
  taskId: 'workspace-review-1',
  taskType: 'personalized_resources',
  title: '第六周综合资源包',
  status: 'complete',
  createdAt: '2026-08-28T06:38:00.000Z',
  result: {
    workflow: {
      grounded: true,
      knowledgeSources: [
        { title: '中药鉴定学课程知识库' },
        { title: '中国药典学习资料' },
      ],
      resources: [
        {
          id: 'ppt-1',
          type: 'ppt',
          title: '第一周 · 中药性味归经与相似药物功效对比',
          description: '围绕本周薄弱点整理的六页复习课件。',
          matchScore: 95,
          qualityEvaluation: { score: 100 },
          metadata: { weekLabel: '第一周' },
        },
        {
          id: 'mindmap-1',
          type: 'mindmap',
          title: '第二周：麻黄、桂枝与石膏的功效和配伍关系',
          description: '按药性、归经、功效、主治和配伍禁忌组织知识结构。',
          matchScore: 92,
          qualityEvaluation: { score: 98 },
          metadata: { weekNumber: 2 },
        },
        {
          id: 'quiz-1',
          type: 'quiz',
          title: '第 2 周 · 医案辨析：五则基础证候判断与鉴别',
          description: '根据近期错题生成的辨证训练题。',
          matchScore: 89,
          qualityEvaluation: { score: 96 },
        },
        {
          id: 'video-1',
          type: 'video',
          title: '第3周 - 相似药材鉴别与医案辨证综合提升',
          description: '从来源、性状到临床辨证的阶段复习视频。',
          matchScore: 87,
          qualityEvaluation: { score: 94 },
        },
      ],
    },
    orchestration: { review: { score: 96 } },
  },
}

async function installFixtures(page, mode = 'populated') {
  await page.route('**/api/learning-profile/profiles', route => route.fulfill({
    status: 200,
    contentType: 'application/json',
    body: JSON.stringify({
      data: {
        activeReportId: mode === 'no-profile' ? 0 : 12,
        profiles: mode === 'no-profile' ? [] : [{ id: 12, aiAnalysis: { weaknesses: ['相似药材鉴别'] } }],
      },
    }),
  }))

  if (mode === 'loading') {
    await page.route('**/api/xiaozhi/history**', () => new Promise(() => {}))
    await page.route('**/api/personalized-resources/generated-videos**', () => new Promise(() => {}))
    return
  }

  const historyStatus = mode === 'error' ? 503 : 200
  const videoStatus = mode === 'error' || mode === 'partial' ? 503 : 200
  await page.route('**/api/xiaozhi/history**', route => route.fulfill({
    status: historyStatus,
    contentType: 'application/json',
    body: JSON.stringify(mode === 'error' ? { msg: '暂时不可用' } : { data: { tasks: mode === 'empty' ? [] : [task] } }),
  }))
  await page.route('**/api/personalized-resources/generated-videos**', route => route.fulfill({
    status: videoStatus,
    contentType: 'application/json',
    body: JSON.stringify(mode === 'error' ? { msg: '暂时不可用' } : { data: { tasks: [], hasMore: false } }),
  }))
}

async function openPage(browser, viewport, mode = 'populated') {
  const context = await browser.newContext({ viewport })
  const page = await context.newPage()
  const pageErrors = []
  page.on('pageerror', error => pageErrors.push(error.message))
  await installFixtures(page, mode)
  await page.goto(`${baseUrl}/personalized-resources?codexPreview=1`, { waitUntil: 'domcontentloaded' })
  await page.locator('.resources-page').waitFor()
  return { context, page, pageErrors }
}

async function assertNoOverflow(page, label) {
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth > window.innerWidth + 1)
  assert.equal(overflow, false, `${label} should not create horizontal page overflow`)
}

async function assertAssistantDoesNotCoverRecordAction(page, label) {
  const orb = await page.locator('.xiaozhi-orb').boundingBox()
  const action = await page.locator('.topic-card-body > svg').last().boundingBox()
  if (!orb || !action) return
  const overlaps = !(
    action.x + action.width <= orb.x
    || orb.x + orb.width <= action.x
    || action.y + action.height <= orb.y
    || orb.y + orb.height <= action.y
  )
  assert.equal(overlaps, false, `${label} assistant launcher should not cover the record action`)
}

const browser = await chromium.launch(launchOptions)

try {
  const desktop = await openPage(browser, { width: 1440, height: 900 })
  try {
    await desktop.page.locator('.resource-card').first().waitFor()
    await desktop.page.waitForTimeout(700)
    assert.equal(await desktop.page.locator('.resource-tool-card').count(), 6)
    const herbModelTool = desktop.page.getByRole('link', { name: '药材模型识别' })
    assert.equal(await herbModelTool.count(), 1, 'the upstream herb-model tool should be retained as the sixth command')
    assert.equal(await herbModelTool.getAttribute('href'), '/personalized-resources/herb-model')
    assert.equal(await desktop.page.locator('.resource-card').count(), 8)
    assert.equal(await desktop.page.locator('.resources-grid').evaluate(element => getComputedStyle(element).gridTemplateColumns.split(' ').length), 4)
    const desktopStyles = await desktop.page.evaluate(() => ({
      toolBorder: getComputedStyle(document.querySelector('.resource-tool-card')).borderTopWidth,
      toolDivider: getComputedStyle(document.querySelector('.resource-tool-card')).borderRightWidth,
      toolRadius: getComputedStyle(document.querySelector('.resource-tool-card')).borderRadius,
      cardBorder: getComputedStyle(document.querySelector('.resource-card')).borderTopWidth,
      cardRadius: getComputedStyle(document.querySelector('.resource-card')).borderRadius,
    }))
    assert.deepEqual(desktopStyles, { toolBorder: '0px', toolDivider: '1px', toolRadius: '0px', cardBorder: '1px', cardRadius: '8px' })
    assert.match(await desktop.page.locator('.profile-state').innerText(), /已关联学习画像/)
    assert.deepEqual(
      await desktop.page.locator('.resource-card h3').allTextContents(),
      ['八纲辨证', '药材识别', '性味归经', '方剂配伍', '四诊合参', '经络腧穴', '养生健康', '医案研习'],
    )
    assert.equal(await desktop.page.locator('.history-filter-row').count(), 0, 'week and resource-type filters should be removed')
    assert.equal(await desktop.page.getByText('学习时间', { exact: true }).count(), 0)
    const textureImages = desktop.page.locator('.topic-cover-texture')
    assert.equal(await textureImages.count(), 8, 'every topic cover should load one generated texture overlay')
    await desktop.page.waitForFunction(() => [...document.querySelectorAll('.topic-cover-texture')].every(image => image.complete && image.naturalWidth > 0))
    assert.equal(await desktop.page.locator('.topic-cover-icon').count(), 8, 'every topic cover should use one filled topic symbol')
    const iconImages = desktop.page.locator('.topic-cover-icon-image')
    assert.equal(await iconImages.count(), 8, 'every topic cover should use one complete raster pictogram')
    await desktop.page.waitForFunction(() => [...document.querySelectorAll('.topic-cover-icon-image')].every(image => image.complete && image.naturalWidth > 0))
    assert.equal(await desktop.page.locator('.topic-cover-label').count(), 8, 'every topic cover should expose a short series label')
    const coverLabelStyle = await desktop.page.locator('.topic-cover-label').first().evaluate(element => ({
      background: getComputedStyle(element).backgroundColor,
      borderRadius: getComputedStyle(element).borderRadius,
    }))
    assert.deepEqual(coverLabelStyle, { background: 'rgba(0, 0, 0, 0)', borderRadius: '0px' }, 'cover labels should remain direct white text rather than pills')
    const coverTreatment = await desktop.page.locator('.topic-card-media').evaluateAll(elements => ({
      colors: [...new Set(elements.map(element => getComputedStyle(element).backgroundColor))],
      baseLayers: elements.map(element => (getComputedStyle(element).backgroundImage.match(/gradient/g) || []).length),
      pseudoDisplays: elements.map(element => [getComputedStyle(element, '::before').display, getComputedStyle(element, '::after').display]),
    }))
    const textureTreatment = await textureImages.evaluateAll(images => images.map(image => ({
      src: new URL(image.currentSrc || image.src).pathname,
      width: image.naturalWidth,
      height: image.naturalHeight,
      opacity: Number(getComputedStyle(image).opacity),
      style: image.dataset.textureStyle,
      alt: image.getAttribute('alt'),
      ariaHidden: image.getAttribute('aria-hidden'),
    })))
    const iconTreatment = await desktop.page.locator('.topic-cover-icon').evaluateAll(elements => elements.map(element => ({
      glyph: element.dataset.glyph,
      src: new URL(element.querySelector('.topic-cover-icon-image').currentSrc || element.querySelector('.topic-cover-icon-image').src).pathname,
      width: element.querySelector('.topic-cover-icon-image').naturalWidth,
      height: element.querySelector('.topic-cover-icon-image').naturalHeight,
      imageCount: element.querySelectorAll('.topic-cover-icon-image').length,
      svgCount: element.querySelectorAll('svg').length,
      background: getComputedStyle(element).backgroundColor,
      ariaHidden: element.getAttribute('aria-hidden'),
      imageAlt: element.querySelector('.topic-cover-icon-image').getAttribute('alt'),
      imageAriaHidden: element.querySelector('.topic-cover-icon-image').getAttribute('aria-hidden'),
    })))
    assert.ok(coverTreatment.colors.length >= 6, 'topic covers should use a varied but controlled course palette')
    assert.ok(coverTreatment.baseLayers.every(layerCount => layerCount === 1), 'cover colors should remain independently adjustable beneath the bitmap texture')
    assert.ok(coverTreatment.pseudoDisplays.every(displays => displays.every(display => display === 'none')), 'legacy CSS texture shapes should stay disabled')
    assert.equal(new Set(textureTreatment.map(texture => texture.src)).size, 8, 'every topic cover should use a distinct generated texture')
    assert.ok(textureTreatment.every(texture => texture.src.includes('/resource-topic-patterns-v2/')), 'topic covers should use the simplified v2 texture family')
    assert.equal(new Set(textureTreatment.map(texture => texture.style)).size, 8, 'every cover should declare a structurally distinct texture style')
    assert.ok(textureTreatment.every(texture => texture.width === 768 && texture.height === 432), 'web textures should use the optimized 16:9 dimensions')
    assert.ok(textureTreatment.every(texture => texture.opacity >= 0.18 && texture.opacity <= 0.3), 'texture overlays should remain visibly subordinate to labels and icons')
    assert.ok(textureTreatment.every(texture => texture.alt === '' && texture.ariaHidden === 'true'), 'decorative textures should stay hidden from assistive technology')
    assert.equal(new Set(iconTreatment.map(icon => icon.glyph)).size, 8, 'every topic should use a distinct custom TCM pictogram')
    assert.equal(new Set(iconTreatment.map(icon => icon.src)).size, 8, 'every topic should use a distinct raster pictogram asset')
    assert.ok(iconTreatment.every(icon => icon.src.includes('/resource-topic-icons-v2/')), 'topic symbols should use the generated v2 raster family')
    assert.ok(iconTreatment.every(icon => icon.width === 256 && icon.height === 256), 'web pictograms should use stable optimized square dimensions')
    assert.ok(iconTreatment.every(icon => icon.imageCount === 1 && icon.svgCount === 0), 'each topic symbol should be one complete image with no SVG assembly')
    assert.ok(iconTreatment.every(icon => icon.background === 'rgba(0, 0, 0, 0)'), 'global resource-card span styles must not add a repeated circular icon backing')
    assert.ok(iconTreatment.every(icon => icon.ariaHidden === 'true' && icon.imageAlt === '' && icon.imageAriaHidden === 'true'), 'decorative topic symbols should stay hidden from assistive technology')
    await desktop.page.waitForTimeout(450)
    await desktop.page.locator('.resource-card').first().hover()
    const hoveredShadow = await desktop.page.locator('.resource-card').first().evaluate(element => getComputedStyle(element).boxShadow)
    assert.notEqual(hoveredShadow, 'none', 'card hover should use restrained elevation feedback')
    await assertNoOverflow(desktop.page, 'desktop workspace')
    await assertAssistantDoesNotCoverRecordAction(desktop.page, 'desktop workspace')
    await desktop.page.screenshot({ path: path.join(screenshotDir, 'desktop-populated.png'), fullPage: true })
    await desktop.page.getByRole('button', { name: '进入药材识别专题' }).click()
    await desktop.page.waitForURL(/\/resource-detail\?id=/)
    assert.deepEqual(desktop.pageErrors, [])
  } finally {
    await desktop.context.close()
  }

  const mobile = await openPage(browser, { width: 390, height: 844 })
  try {
    await mobile.page.locator('.resource-card').first().waitFor()
    await mobile.page.waitForTimeout(700)
    const columns = await mobile.page.locator('.resource-tools-grid').evaluate(element => getComputedStyle(element).gridTemplateColumns)
    assert.equal(columns.split(' ').length, 2, 'mobile tools should use two compact columns')
    const resourceColumns = await mobile.page.locator('.resources-grid').evaluate(element => getComputedStyle(element).gridTemplateColumns)
    assert.equal(resourceColumns.split(' ').length, 1, 'mobile resource cards should use one column')
    assert.equal(await mobile.page.locator('.topic-cover-texture').count(), 8)
    assert.equal(await mobile.page.locator('.topic-cover-icon').count(), 8)
    await mobile.page.waitForFunction(() => [...document.querySelectorAll('.topic-cover-icon-image')].every(image => image.complete && image.naturalWidth > 0))
    await assertNoOverflow(mobile.page, 'mobile workspace')
    await assertAssistantDoesNotCoverRecordAction(mobile.page, 'mobile workspace')
    await mobile.page.screenshot({ path: path.join(screenshotDir, 'mobile-populated.png'), fullPage: true })
    await mobile.page.locator('.resource-card').last().scrollIntoViewIfNeeded()
    await mobile.page.waitForTimeout(250)
    await mobile.page.screenshot({ path: path.join(screenshotDir, 'mobile-populated-bottom.png') })
    assert.deepEqual(mobile.pageErrors, [])
  } finally {
    await mobile.context.close()
  }

  const empty = await openPage(browser, { width: 1280, height: 800 }, 'empty')
  try {
    await empty.page.locator('.compact-empty-state').waitFor()
    assert.match(await empty.page.locator('.compact-empty-state').innerText(), /暂时没有已生成记录/)
    assert.equal(await empty.page.locator('.resource-card').count(), 8, 'empty records should retain useful topic entries')
  } finally {
    await empty.context.close()
  }

  const failed = await openPage(browser, { width: 1280, height: 800 }, 'error')
  try {
    await failed.page.locator('.history-error').waitFor()
    assert.match(await failed.page.locator('.history-error').innerText(), /暂时无法加载/)
    assert.deepEqual(failed.pageErrors, [])
  } finally {
    await failed.context.close()
  }

  const partial = await openPage(browser, { width: 1280, height: 800 }, 'partial')
  try {
    await partial.page.locator('.history-status.warning').waitFor()
    assert.equal(await partial.page.locator('.resource-card').count(), 8)
    assert.match(await partial.page.locator('.history-status.warning').innerText(), /列表可能不完整/)
  } finally {
    await partial.context.close()
  }

  const noProfile = await openPage(browser, { width: 390, height: 844 }, 'no-profile')
  try {
    await noProfile.page.locator('.no-profile-banner').waitFor()
    assert.equal(await noProfile.page.locator('.generate-btn').isDisabled(), true)
    assert.equal(await noProfile.page.locator('.resource-card').count(), 8)
  } finally {
    await noProfile.context.close()
  }

  const loading = await openPage(browser, { width: 390, height: 844 }, 'loading')
  try {
    await loading.page.locator('.history-loading').waitFor()
    assert.match(await loading.page.locator('.history-loading').innerText(), /正在同步真实资源记录/)
  } finally {
    await loading.context.close()
  }

  console.log('Generated transparent personalized-resource textures verified in populated, interactive, empty, warning, error, no-profile, and loading states')
} finally {
  await browser.close()
}
