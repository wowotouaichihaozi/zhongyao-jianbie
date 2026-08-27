import assert from 'node:assert/strict'
import fs from 'node:fs'
import path from 'node:path'

import { chromium } from 'playwright'

const baseUrl = process.env.E2E_BASE_URL || 'http://127.0.0.1:5088'
const screenshotDir = path.resolve('../logs/learning-profile-developer-tools')
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

async function verifyViewport(name, viewport) {
  const context = await browser.newContext({ viewport })
  const page = await context.newPage()
  const pageErrors = []
  page.on('pageerror', error => pageErrors.push(error.message))
  await page.route('**/api/learning-profile/analyze-stream', async (route) => {
    const payload = route.request().postDataJSON()
    const report = {
      id: 909,
      version: 1,
      profileName: '开发测试画像',
      isActive: true,
      timestamp: '2026-08-27T18:00:00+08:00',
      scaleScores: payload.scaleScores,
      scaleTimestamp: payload.scaleTimestamp,
      chatBackground: payload.chatBackground,
      chatTimestamp: payload.chatTimestamp,
      chatStudentProfile: payload.chatStudentProfile,
      completedProfileDimensions: payload.completedProfileDimensions,
      missingProfileDimensions: payload.missingProfileDimensions,
      uploadFiles: [],
      aiAnalysis: {
        source: 'llm',
        learningStyle: '案例与图示驱动型',
        overallScore: 78,
        radarScores: [4, 4, 3, 3, 4, 3],
        dimensionScores: [
          { name: '中医基础知识', score: 4 },
          { name: '辨证与临床思维能力', score: 4 },
          { name: '中药与方剂应用能力', score: 3 },
          { name: '医案实践能力', score: 3 },
          { name: '学习习惯与投入', score: 4 },
          { name: '综合应用与人文素养', score: 3 },
        ],
        strengths: ['基础概念较完整'],
        weaknesses: ['脉象鉴别'],
        recommendations: ['完成一次病例辨证练习'],
        summary: payload.chatBackground,
      },
    }
    const result = {
      report,
      reportId: report.id,
      status: 'complete',
      progress: 100,
      message: '画像已保存，学习路径任务已创建',
      learningPathTask: { taskId: 'fixture-path-task', status: 'queued' },
    }
    await route.fulfill({
      status: 200,
      contentType: 'text/event-stream; charset=utf-8',
      body: `event: result\ndata: ${JSON.stringify(result)}\n\nevent: done\ndata: ${JSON.stringify({ status: 'complete' })}\n\n`,
    })
  })

  try {
    await page.goto(`${baseUrl}/learning-profile?codexPreview=1`, { waitUntil: 'domcontentloaded' })
    await page.locator('.lp-page').waitFor()
    await page.keyboard.press('F4')

    const panel = page.locator('.profile-developer-panel')
    await panel.waitFor()
    assert.equal(await panel.getAttribute('role'), 'dialog')
    assert.equal(await page.locator('.profile-developer-action').count(), 2)
    await page.screenshot({ path: path.join(screenshotDir, `${name}-empty.png`), fullPage: true })

    await page.getByRole('button', { name: /一键完成学习画像/ }).click()
    await panel.waitFor({ state: 'detached' })
    assert.equal(await page.evaluate(() => JSON.parse(localStorage.getItem('learningProfileData') || '{}').id), 909)
    assert.equal(await page.evaluate(() => JSON.parse(localStorage.getItem('learningProfileData') || '{}').isActive), true)
    await page.keyboard.press('F4')
    await panel.waitFor()
    assert.equal((await page.locator('.profile-developer-status strong').innerText()).trim(), '10/10')

    await page.getByRole('button', { name: /清除当前画像信息/ }).click()
    assert.match(await page.locator('.profile-developer-action.clear strong').innerText(), /再次点击确认清除/)
    const overflow = await page.evaluate(() => document.documentElement.scrollWidth > window.innerWidth + 1)
    assert.equal(overflow, false, `${name} should not create horizontal overflow`)
    await page.screenshot({ path: path.join(screenshotDir, `${name}-filled.png`), fullPage: true })
    assert.deepEqual(pageErrors, [], `${name} page errors: ${pageErrors.join('; ')}`)
  } finally {
    await context.close()
  }
}

try {
  await verifyViewport('desktop', { width: 1440, height: 900 })
  await verifyViewport('mobile', { width: 390, height: 844 })
  console.log('learning-profile developer panel verified at desktop and mobile widths')
} finally {
  await browser.close()
}
