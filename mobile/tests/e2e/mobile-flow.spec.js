import { expect, test } from '@playwright/test'

const user = { id: 7, username: 'mobile-test', displayName: '移动测试用户', token: 'test-token' }
const profile = { id: 11, isActive: true, profileName: 'STM32 学习画像', version: 3 }
const pathConfig = { config: { weeks: [
  { id: 'week-1', order: 1, title: 'GPIO 与时钟基础', status: 'done' },
  { id: 'week-2', order: 2, title: '定时器与 PWM', status: 'current' },
  { id: 'week-3', order: 3, title: '串口通信', status: 'available' },
] } }

async function mockApi(page) {
  await page.route('**/api/**', async route => {
    const url = new URL(route.request().url())
    let body = { code: 0 }
    if (url.pathname.endsWith('/auth/login')) body = user
    else if (url.pathname.endsWith('/learning-profile/profiles')) body = { profiles: [profile], activeReportId: 11 }
    else if (url.pathname.endsWith('/learning-path/config')) body = pathConfig
    else if (url.pathname.endsWith('/xiaozhi/history')) body = { code: 0, data: { tasks: [] } }
    else if (url.pathname.endsWith('/learning-feedback')) body = { code: 0, data: { feedbacks: [] } }
    else if (url.pathname.endsWith('/effect-assessment')) body = { code: 0, data: { assessment: { overallScore: 82, summary: '进展稳定' } } }
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(body) })
  })
}

test('logs in and shows the five mobile destinations', async ({ page }) => {
  await mockApi(page)
  await page.goto('login')
  await page.getByPlaceholder('用户名或邮箱').fill('mobile-test')
  await page.getByPlaceholder('输入密码').fill('password123')
  await page.getByRole('button', { name: '进入学习空间', exact: true }).click()
  await expect(page.getByRole('heading', { name: /移动测试用户/ })).toBeVisible()
  const nav = page.getByRole('navigation', { name: '主导航' })
  for (const label of ['首页', '路径', '资源', '辅导', '我的']) await expect(nav.getByRole('link', { name: label, exact: true })).toBeVisible()
  const layout = await page.evaluate(() => {
    const navLinks = [...document.querySelectorAll('.bottom-nav a')]
    const navBox = document.querySelector('.bottom-nav')?.getBoundingClientRect()
    return {
      hasHorizontalOverflow: document.documentElement.scrollWidth > document.documentElement.clientWidth,
      minNavTarget: Math.min(...navLinks.map(link => link.getBoundingClientRect().height)),
      navInsideViewport: Boolean(navBox && navBox.left >= 0 && navBox.right <= innerWidth),
    }
  })
  expect(layout.hasHorizontalOverflow).toBe(false)
  expect(layout.minNavTarget).toBeGreaterThanOrEqual(44)
  expect(layout.navInsideViewport).toBe(true)
})

test('renders the learning map as an ordered vertical path', async ({ page }) => {
  await mockApi(page)
  await page.addInitScript(value => { localStorage.setItem('authToken', value.token); localStorage.setItem('currentUser', JSON.stringify(value)) }, user)
  await page.goto('path')
  await expect(page.getByRole('heading', { name: '纵向学习路径' })).toBeVisible()
  const titles = page.locator('.path-node .node-copy strong')
  await expect(titles).toHaveText(['GPIO 与时钟基础', '定时器与 PWM', '串口通信'])
  await expect(page.locator('.vertical-path > li.current .node-detail')).toBeVisible()
  await expect(page.locator('body')).not.toHaveCSS('overflow-x', 'scroll')
})

test('creates a resource task with the mobile form contract', async ({ page }) => {
  let submitted
  await page.route('**/api/**', async route => {
    const url = new URL(route.request().url())
    if (url.pathname.endsWith('/personalized-resources/agent-task')) {
      submitted = route.request().postDataJSON()
      return route.fulfill({ status: 202, contentType: 'application/json', body: JSON.stringify({ code: 0, data: { task: { taskId: 'task-mobile-1', taskType: submitted.resourceType, status: 'queued', title: submitted.topic } } }) })
    }
    if (url.pathname.endsWith('/xiaozhi/tasks/task-mobile-1')) return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ code: 0, data: { task: { taskId: 'task-mobile-1', taskType: 'document', status: 'queued', title: 'GPIO 调试笔记' } } }) })
    if (url.pathname.endsWith('/learning-feedback')) return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ code: 0, data: { feedbacks: [] } }) })
    return route.fulfill({ status: 200, contentType: 'application/json', body: '{}' })
  })
  await page.addInitScript(value => { localStorage.setItem('authToken', value.token); localStorage.setItem('currentUser', JSON.stringify(value)) }, user)
  await page.goto('resources/new')
  await page.getByRole('button', { name: '文档', exact: true }).click()
  await page.getByPlaceholder('例如：STM32 定时器与 PWM').fill('GPIO 调试笔记')
  await page.getByPlaceholder('难度、重点、呈现方式等').fill('突出排错步骤')
  await page.getByRole('button', { name: '创建后台生成任务' }).click()
  await expect(page).toHaveURL(/resources\/task\/task-mobile-1/)
  expect(submitted).toMatchObject({ resourceType: 'document', topic: 'GPIO 调试笔记', prompt: '突出排错步骤' })
})

test('submits practice detail for AI scoring and stores the result', async ({ page }) => {
  const requests = []
  await page.route('**/api/**', async route => {
    const url = new URL(route.request().url())
    if (url.pathname.endsWith('/question-generator/history')) return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ question_sheets: [{ id: 21, title: 'GPIO 小测', question_bank: { questions: [{ question: 'GPIO 输出高电平对应哪个值？', options: ['0', '1'], answer: 'B', score: 10 }] } }] }) })
    if (url.pathname.endsWith('/question-generator/ai-score')) {
      requests.push({ kind: 'score', body: route.request().postDataJSON() })
      return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ score: 10, total_score: 10, correct_count: 1, question_count: 1, detail: [], aiSummary: '掌握良好' }) })
    }
    if (url.pathname.endsWith('/question-generator/exam-results')) {
      requests.push({ kind: 'save', body: route.request().postDataJSON() })
      return route.fulfill({ status: 201, contentType: 'application/json', body: JSON.stringify({ id: 88 }) })
    }
    return route.fulfill({ status: 200, contentType: 'application/json', body: '{}' })
  })
  await page.addInitScript(value => { localStorage.setItem('authToken', value.token); localStorage.setItem('currentUser', JSON.stringify(value)) }, user)
  await page.goto('practice/21')
  await page.getByText('B. 1', { exact: true }).click()
  await page.getByRole('button', { name: '提交并评分' }).click()
  await expect(page.getByRole('heading', { name: '评分完成' })).toBeVisible()
  expect(requests[0].body.detail).toHaveLength(1)
  expect(requests[0].body).not.toHaveProperty('items')
  expect(requests[1].body).toMatchObject({ sheet_id: 21, score: 10, total_score: 10, correct_count: 1, question_count: 1 })
})

test('renders tutor evidence and supports a follow-up', async ({ page }) => {
  const questions = []
  await page.route('**/api/**', async route => {
    const url = new URL(route.request().url())
    if (url.pathname.endsWith('/xiaozhi/tutor')) {
      const payload = route.request().postDataJSON()
      questions.push(payload)
      return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ code: 0, data: { question: payload.question, answer: payload.followUp ? '因为输出寄存器控制引脚电平。' : '先配置 GPIO 输出模式。', references: [{ title: 'STM32 GPIO 课程知识库' }], qualityEvaluation: { score: 92 } } }) })
    }
    return route.fulfill({ status: 200, contentType: 'application/json', body: '{}' })
  })
  await page.addInitScript(value => { localStorage.setItem('authToken', value.token); localStorage.setItem('currentUser', JSON.stringify(value)) }, user)
  await page.goto('tutor')
  await page.getByPlaceholder('输入你卡住的知识点或调试问题…').fill('GPIO 如何配置？')
  await page.getByRole('button', { name: '开始辅导' }).click()
  await expect.poll(() => questions.length).toBe(1)
  await expect(page.getByText('STM32 GPIO 课程知识库')).toBeVisible()
  await page.getByLabel('继续追问').fill('为什么？')
  await page.getByLabel('发送追问').click()
  await expect(page.getByText('因为输出寄存器控制引脚电平。')).toBeVisible()
  expect(questions[1]).toMatchObject({ question: '为什么？', followUp: true, previousAnswer: '先配置 GPIO 输出模式。' })
})

test('clears an expired session and redirects to login on 401', async ({ page }) => {
  await page.route('**/api/**', route => {
    const url = new URL(route.request().url())
    if (url.pathname.endsWith('/learning-profile/profiles')) return route.fulfill({ status: 401, contentType: 'application/json', body: JSON.stringify({ msg: '登录已过期' }) })
    return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ code: 0, data: { tasks: [] } }) })
  })
  await page.goto('login')
  await page.evaluate(value => { localStorage.setItem('authToken', value.token); localStorage.setItem('currentUser', JSON.stringify(value)) }, user)
  await page.goto('home')
  await expect(page).toHaveURL(/\/m\/login$/)
  await page.waitForLoadState('domcontentloaded')
  await page.waitForTimeout(500)
  await expect(page.getByRole('button', { name: '进入学习空间' })).toBeVisible()
  expect(await page.evaluate(() => localStorage.getItem('authToken'))).toBeNull()
})

test('guides users without a profile and logs out cleanly', async ({ page }) => {
  await page.route('**/api/**', async route => {
    const url = new URL(route.request().url())
    if (url.pathname.endsWith('/learning-profile/profiles')) return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ code: 0, data: { profiles: [], activeReportId: null } }) })
    if (url.pathname.endsWith('/auth/logout')) return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ code: 0 }) })
    return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ code: 0, data: { tasks: [] } }) })
  })
  await page.addInitScript(value => { localStorage.setItem('authToken', value.token); localStorage.setItem('currentUser', JSON.stringify(value)) }, user)
  await page.goto('path')
  await expect(page.getByText('请先完成学习画像')).toBeVisible()
  await expect(page.getByRole('link', { name: '完成画像' })).toHaveAttribute('href', '/m/profile/collect')
  await page.goto('me')
  await page.getByRole('button', { name: '退出登录' }).click()
  await expect(page).toHaveURL(/\/m\/login$/)
  expect(await page.evaluate(() => localStorage.getItem('authToken'))).toBeNull()
})
