import assert from 'node:assert/strict'
import fs from 'node:fs'
import path from 'node:path'

import { chromium } from 'playwright'

const baseUrl = process.env.E2E_BASE_URL || 'http://127.0.0.1:5088'
const screenshotDir = process.env.E2E_SCREENSHOT_DIR?.trim()
const taskId = 'xz_demo_1'
const resourceId = `task:${taskId}:handout`
const mindmapResourceId = `task:${taskId}:mindmap`
const feedbackCacheKey = `resource-detail:${resourceId}`
const rawScript = '<script>globalThis.__resourceDetailInjected = true</script>'
const strategy = '先用可追溯讲义建立概念基础，再通过练习与实验完成学习验证。'

const taskFixture = {
  taskId,
  taskType: 'personalized_resources',
  title: 'GPIO 个性化资源包',
  status: 'complete',
  createdAt: '2026-08-14T02:00:00Z',
  result: {
    orchestrator: 'xiaozhi-companion-agent',
    orchestration: {
      runId: 'run-demo-1',
      profileReportId: 17,
      review: { passed: true, score: 92 },
      agentRuns: [{ id: 'learning_document_agent', name: '讲义智能体', role: 'specialist' }],
    },
    workflow: {
      grounded: true,
      planner: {
        targetWeakPoints: ['GPIO 输入模式'],
        strategy,
      },
      resources: [{
        id: 'handout',
        type: 'document',
        title: 'GPIO 输入模式个性化讲义',
        description: '基于当前画像薄弱点与课程知识库生成的可追溯讲义。',
        matchScore: 94,
        content: `# GPIO 输入模式\n\n课程正文用于验证安全 Markdown 渲染。\n\n${rawScript}`,
        metadata: {
          workflowNode: 'learning_document_agent',
          qualityEvaluation: {
            score: 88,
            passed: true,
            citationCount: 1,
            verificationRequired: false,
            reviewStatus: 'passed',
            criteria: {
              structure: 22,
              relevance: 24,
              knowledgeGrounding: 20,
              usability: 12,
              safety: 10,
            },
          },
          knowledgeSources: [{ id: 'KB-1', title: 'GPIO 课程资料', page: 12 }],
        },
      }, {
        id: 'mindmap',
        type: 'mindmap',
        title: 'GPIO 学习导图',
        description: '以 Markdown 层级展示的个性化导图。',
        content: '# GPIO\n\n## 输入模式\n\n- 上拉输入\n- 下拉输入',
      }],
    },
  },
}

const orchestrationRunFixture = {
  runId: 'run-demo-1',
  rootAgent: 'xiaozhi-companion-agent',
  profileReportId: 17,
  handoffCount: 3,
  review: { passed: true, score: 92 },
  agentRuns: [{ id: 'learning_document_agent', name: '讲义智能体', role: 'specialist' }],
  harness: {
    skillId: 'resource-detail-evidence',
    mcpServer: 'knowledge.retrieve',
    mcpTool: 'gpio-course',
  },
}

const systemChromiumCandidates = [
  'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe',
  'C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe',
  'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe',
  'C:\\Program Files\\Microsoft\\Edge\\Application\\msedge.exe',
]
const launchOptions = { headless: true }
if (!fs.existsSync(chromium.executablePath())) {
  launchOptions.executablePath = systemChromiumCandidates.find(candidate => fs.existsSync(candidate))
}
assert.ok(launchOptions.executablePath || fs.existsSync(chromium.executablePath()), '没有可用的 Chromium 浏览器')
const browser = await chromium.launch(launchOptions)
const unexpectedApiRequests = []
const allowedShellApiRequests = new Set([
  'POST /api/xiaozhi/events',
  'POST /api/learning-activity/pulse',
  'GET /api/xiaozhi/status',
])

function jsonBody(payload) {
  return JSON.stringify(payload)
}

async function installSyntheticApi(page, state) {
  await page.route('**/api/**', async (route) => {
    const request = route.request()
    const url = new URL(request.url())
    const method = request.method()

    if (method === 'GET' && url.pathname === `/api/xiaozhi/tasks/${taskId}`) {
      state.taskRequests += 1
      if (state.taskRequests === 1) {
        await route.fulfill({
          status: 404,
          contentType: 'application/json',
          body: jsonBody({ code: 404, msg: '未找到嵌小智任务' }),
        })
        return
      }
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: jsonBody({
          code: 0,
          data: {
            task: taskFixture,
            orchestrationRuns: [orchestrationRunFixture],
          },
        }),
      })
      return
    }

    if (method === 'GET' && url.pathname === '/api/learning-feedback') {
      state.feedbackQueries.push(Object.fromEntries(url.searchParams))
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: jsonBody({ code: 0, data: { feedbacks: [] } }),
      })
      return
    }

    if (method === 'POST' && url.pathname === '/api/xiaozhi/feedback') {
      const payload = request.postDataJSON()
      state.feedbackPosts.push(payload)
      const needsReview = payload.outcome === 'needs_review'
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: jsonBody({
          code: 0,
          data: {
            message: needsReview
              ? '巩固需求已记录，效果评估会把该主题作为后续调整依据。'
              : '学习反馈已记录，本次任务已计入路径完成与效果评估。',
            route: '/effect-assessment?section=feedback',
            feedback: {
              id: state.feedbackPosts.length,
              taskId,
              cacheKey: feedbackCacheKey,
              outcome: payload.outcome,
              rating: payload.rating,
              note: payload.note || '',
            },
            orchestration: {
              feedback: {
                nextActions: needsReview
                  ? ['回到学习路径调整后续任务', '向智能导师请求针对性辅导']
                  : ['查看本次效果评估', '继续下一项学习任务'],
              },
            },
          },
        }),
      })
      return
    }

    const shellRequest = `${method} ${url.pathname}`
    if (allowedShellApiRequests.has(shellRequest)) {
      state.shellApiRequests.push(shellRequest)
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: jsonBody({ code: 0, data: {} }),
      })
      return
    }

    unexpectedApiRequests.push(`${method} ${url.pathname}${url.search}`)
    await route.fulfill({
      status: 599,
      contentType: 'application/json',
      body: jsonBody({ code: 599, msg: 'Unexpected API request in synthetic UI contract' }),
    })
  })
}

async function openIsolatedContext(viewport) {
  const context = await browser.newContext({ viewport })
  const page = await context.newPage()
  const state = { taskRequests: 0, feedbackQueries: [], feedbackPosts: [], shellApiRequests: [] }

  await page.addInitScript(() => {
    localStorage.setItem('authToken', 'resource-detail-contract-token')
    localStorage.setItem('currentUser', JSON.stringify({
      id: 903,
      username: 'resource-detail-contract',
      displayName: '资源详情合约用户',
      role: 'user',
    }))
    localStorage.setItem('appMode', 'user')
    localStorage.removeItem('currentResourceDetail')
    localStorage.removeItem('resourceEvaluations')
  })
  await installSyntheticApi(page, state)
  return { context, page, state }
}

async function assertRecoveredEvidence(page) {
  await page.getByRole('heading', { name: 'GPIO 输入模式个性化讲义' }).waitFor()
  const pageText = await page.locator('body').innerText()

  for (const evidence of [
    '任务记录',
    '匹配 94%',
    '报告 #17',
    'GPIO 输入模式',
    strategy,
    'xiaozhi-companion-agent',
    '讲义智能体',
    'run-demo-1',
    'resource-detail-evidence',
    'knowledge.retrieve / gpio-course',
    '88',
    '已通过',
    'GPIO 课程资料',
    'KB-1 · 第 12 页',
  ]) {
    assert.equal(pageText.includes(evidence), true, `页面应展示真实证据文本：${evidence}`)
  }

  assert.equal(pageText.includes(rawScript), true, '原始脚本文本应作为安全文本可检查')
  assert.equal(await page.locator('.artifact-surface.markdown-content script').count(), 0, '原始脚本不能成为 DOM 标签')
  assert.equal(await page.evaluate(() => globalThis.__resourceDetailInjected), undefined, '原始脚本不能执行')

  const hasHorizontalOverflow = await page.evaluate(() => (
    document.documentElement.scrollWidth > window.innerWidth + 1
  ))
  assert.equal(hasHorizontalOverflow, false, '资源详情在当前视口不应产生整页横向溢出')
}

async function submitAndAssert(page, state, outcome) {
  if (outcome === 'needs_review') {
    await page.getByRole('button', { name: '需要巩固' }).click()
    await page.getByRole('button', { name: '2 星：初步了解' }).click()
  } else {
    await page.getByRole('button', { name: '完成学习' }).click()
    await page.getByRole('button', { name: '4 星：熟练掌握' }).click()
  }
  await page.getByRole('button', { name: '提交学习反馈' }).click()

  const expectedStatus = outcome === 'needs_review' ? '需巩固' : '已完成'
  await page.locator('.feedback-status', { hasText: expectedStatus }).waitFor()
  const resultText = await page.locator('.feedback-result').innerText()
  assert.equal(
    resultText.includes(outcome === 'needs_review' ? '巩固需求已记录' : '学习反馈已记录'),
    true,
  )

  const assessmentLink = page.getByRole('link', { name: '查看效果评估' })
  assert.equal(await assessmentLink.getAttribute('href'), '/effect-assessment?section=feedback')
  assert.equal(await page.getByRole('link', { name: '返回学习路径' }).isVisible(), true)
  assert.equal(
    await page.getByRole('link', { name: '向智能导师求助' }).count(),
    outcome === 'needs_review' ? 1 : 0,
  )

  const payload = state.feedbackPosts.at(-1)
  const expectedRating = outcome === 'needs_review' ? 2 : 4
  assert.equal(payload.taskId, taskId)
  assert.equal(payload.cacheKey, feedbackCacheKey)
  assert.equal(payload.profileReportId, 17)
  assert.equal(payload.runId, 'run-demo-1')
  assert.equal(payload.topic, 'GPIO 输入模式个性化讲义')
  assert.equal(payload.resourceType, 'document')
  assert.equal(payload.outcome, outcome)
  assert.equal(payload.rating, expectedRating)
  assert.equal(payload.difficulty, outcome === 'needs_review' ? 'hard' : 'easy')
  assert.equal(payload.helpful, outcome === 'completed')
  assert.equal(payload.route.includes(`id=${encodeURIComponent(resourceId)}`), true)
}

async function runViewportContract(viewport) {
  const { context, page, state } = await openIsolatedContext(viewport)
  const query = new URLSearchParams({ id: resourceId, xzEmbed: '1' })

  try {
    await page.goto(`${baseUrl}/resource-detail?${query}`, { waitUntil: 'domcontentloaded' })
    await page.locator('.error-state h2', { hasText: '无法打开该资源' }).waitFor()
    assert.equal((await page.locator('.error-state').innerText()).includes('未找到嵌小智任务'), true)
    assert.equal(state.taskRequests, 1, '首次 URL 恢复应发起一次任务读取')

    await page.getByRole('button', { name: '重试' }).click()
    await assertRecoveredEvidence(page)
    assert.equal(state.taskRequests, 2, '404 后点击重试应重新读取任务')
    assert.deepEqual(state.feedbackQueries.at(-1), { cacheKey: feedbackCacheKey, limit: '1' })

    if (screenshotDir) {
      await page.screenshot({
        path: path.join(screenshotDir, `resource-detail-${viewport.width}x${viewport.height}.png`),
        fullPage: true,
      })
    }

    await submitAndAssert(page, state, 'completed')
    await page.evaluate(() => localStorage.removeItem('resourceEvaluations'))
    await page.reload({ waitUntil: 'domcontentloaded' })
    await assertRecoveredEvidence(page)
    await submitAndAssert(page, state, 'needs_review')

    assert.deepEqual(state.feedbackPosts.map(payload => payload.outcome), ['completed', 'needs_review'])
  } finally {
    await context.close()
  }
}

async function runMarkdownMindmapContract() {
  const { context, page, state } = await openIsolatedContext({ width: 390, height: 844 })
  const query = new URLSearchParams({ id: mindmapResourceId, xzEmbed: '1' })

  try {
    state.taskRequests = 1
    await page.goto(`${baseUrl}/resource-detail?${query}`, { waitUntil: 'domcontentloaded' })
    await page.getByRole('heading', { name: 'GPIO 学习导图' }).waitFor()
    assert.equal(await page.locator('.mindmap-markdown h1', { hasText: 'GPIO' }).count(), 1)
    assert.equal(await page.locator('.mindmap-markdown h2', { hasText: '输入模式' }).count(), 1)
    assert.equal(await page.locator('.render-warning').count(), 0, 'Markdown 导图不应误报 Mermaid 渲染失败')
    assert.equal(await page.locator('.mindmap-render').count(), 0, 'Markdown 导图不应加载 Mermaid 容器')
  } finally {
    await context.close()
  }
}

try {
  await runViewportContract({ width: 1440, height: 900 })
  await runViewportContract({ width: 390, height: 844 })
  await runMarkdownMindmapContract()
  assert.deepEqual(unexpectedApiRequests, [], `发现未预期 API 请求：${unexpectedApiRequests.join(', ')}`)
  console.log('synthetic UI contract fixture; production DB untouched')
} finally {
  await browser.close()
}
