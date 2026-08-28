import assert from 'node:assert/strict'
import fs from 'node:fs'
import path from 'node:path'

import { chromium } from 'playwright'

const baseUrl = process.env.E2E_BASE_URL || 'http://127.0.0.1:3000'
const outputDir = process.env.E2E_SCREENSHOT_DIR || path.resolve('../logs/xiaozhi-workflow-card')
const systemChromiumCandidates = [
  'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe',
  'C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe',
  'C:\\Program Files\\Microsoft\\Edge\\Application\\msedge.exe',
]
const launchOptions = { headless: true }
if (!fs.existsSync(chromium.executablePath())) {
  launchOptions.executablePath = systemChromiumCandidates.find(candidate => fs.existsSync(candidate))
}
assert.ok(launchOptions.executablePath || fs.existsSync(chromium.executablePath()), '没有可用的 Chromium 浏览器')
fs.mkdirSync(outputDir, { recursive: true })

const browser = await chromium.launch(launchOptions)

async function verifyViewport(viewport) {
  const context = await browser.newContext({ viewport })
  const page = await context.newPage()
  await page.addInitScript(() => {
    localStorage.setItem('authToken', 'workflow-card-contract-token')
    localStorage.setItem('currentUser', JSON.stringify({ id: 903, username: 'workflow-card-contract', role: 'user' }))
    localStorage.setItem('appMode', 'user')
  })
  await page.route('**/api/**', route => route.fulfill({
    status: 200,
    contentType: 'application/json',
    body: JSON.stringify({ code: 0, data: { messages: [], tasks: [], agents: [], architecture: null } }),
  }))

  try {
    await page.goto(`${baseUrl}/personalized-resources`, { waitUntil: 'domcontentloaded' })
    await page.evaluate(() => {
      const detail = {
        workflowId: 'profile-contract-1',
        workflow: 'learning-profile',
        stage: 'quality_review',
        status: 'running',
        progress: 68,
        message: '领域专家与审核 Agent 正在交叉验证画像证据',
        route: '/learning-profile',
      }
      sessionStorage.setItem('qihuang:xiaozhi-workflow-state:v1', JSON.stringify(detail))
      window.dispatchEvent(new CustomEvent('xiaozhi-workflow-progress', { detail }))
    })

    const assistant = page.locator('.xiaozhi-window')
    const chat = page.locator('.chat-scroll-area')
    const card = chat.locator('.xz-workflow-card.embedded')
    await assistant.waitFor({ state: 'visible' })
    await card.waitFor({ state: 'visible' })
    await page.waitForTimeout(500)

    assert.equal(await page.locator('body > .xz-workflow-card, #app > .xz-workflow-card').count(), 0)
    assert.equal(await page.locator('.xz-workflow-card').count(), 1)
    assert.equal((await card.innerText()).includes('多智能体协同'), true)
    assert.equal((await card.innerText()).includes('交叉审核'), true)
    assert.equal((await card.innerText()).includes('68%'), true)

    const bounds = await page.evaluate(() => {
      const windowRect = document.querySelector('.xiaozhi-window').getBoundingClientRect()
      const cardRect = document.querySelector('.chat-scroll-area .xz-workflow-card.embedded').getBoundingClientRect()
      return {
        inside: cardRect.left >= windowRect.left - 1
          && cardRect.right <= windowRect.right + 1
          && cardRect.top >= windowRect.top - 1
          && cardRect.bottom <= windowRect.bottom + 1,
        overflow: document.documentElement.scrollWidth > window.innerWidth + 1,
      }
    })
    assert.equal(bounds.inside, true, '协同卡必须位于悬浮助手窗口内部')
    assert.equal(bounds.overflow, false, '页面不应出现横向溢出')

    await page.screenshot({
      path: path.join(outputDir, `assistant-workflow-${viewport.width}x${viewport.height}.png`),
      fullPage: true,
    })
  } finally {
    await context.close()
  }
}

try {
  await verifyViewport({ width: 1440, height: 900 })
  console.log('assistant workflow card rendered inside the desktop companion chat')
} finally {
  await browser.close()
}
