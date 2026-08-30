import assert from 'node:assert/strict'

import { chromium } from 'playwright'

const baseUrl = process.env.E2E_BASE_URL || 'http://127.0.0.1:3000'
const browser = await chromium.launch({ headless: true })

try {
  const context = await browser.newContext({ viewport: { width: 1440, height: 900 } })
  const page = await context.newPage()

  await page.addInitScript(() => {
    localStorage.setItem('authToken', 'interview-fail-open-test-token')
    localStorage.setItem('currentUser', JSON.stringify({
      id: 901,
      username: 'interview-test',
      displayName: '面试测试用户',
      role: 'user',
    }))
    localStorage.setItem('appMode', 'user')
  })

  await page.route('**/api/avatar/config', (route) => route.abort('failed'))
  await page.route('**/api/interview/session/start', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        sessionId: 'interview-fail-open-session',
        status: 'asking',
        round: 1,
        content: '请解释 GPIO 推挽输出与开漏输出的区别。',
        source: 'model',
        usedAI: true,
      }),
    })
  })
  await page.route('**/api/interview/session/message', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        status: 'asking',
        round: 2,
        content: '请继续说明 EXTI 中断的排查步骤。',
        source: 'model',
        usedAI: true,
      }),
    })
  })
  await page.route('**/api/interview/session/end', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        status: 'ended',
        summary: '回答覆盖了关键配置与调试步骤。',
        score: 88,
        textScore: 88,
        advantages: ['概念区分清晰'],
        weaknesses: ['可补充波形验证'],
        suggestions: ['增加示波器验证过程'],
      }),
    })
  })

  await page.goto(`${baseUrl}/digital-human-interview?codexPreview=1`, { waitUntil: 'domcontentloaded' })
  await page.getByText('数字人连接失败', { exact: true }).last().waitFor()
  assert.equal(await page.locator('.avatar-standby').count(), 0, '数字人连接失败时不应渲染人物占位图')
  const startButton = page.getByRole('button', { name: '开始访谈' })
  try {
    await startButton.waitFor({ timeout: 15000 })
  } catch (error) {
    console.error('Current URL:', page.url())
    console.error('Page text:', (await page.locator('body').innerText()).slice(0, 1200))
    throw error
  }
  await startButton.click()

  await page.getByText('请解释 GPIO 推挽输出与开漏输出的区别。').waitFor()
  await page.getByText('数字人连接失败', { exact: true }).last().waitFor()
  assert.equal(await page.locator('.avatar-standby').count(), 0, '访谈进行中连接失败也不应回退到人物海报')
  const answerInput = page.getByPlaceholder('请输入你的回答，或点击语音回答')
  await answerInput.waitFor()
  assert.equal(await answerInput.isDisabled(), false, '首题出现后文字输入应立即可用')
  assert.equal(await page.getByRole('button', { name: '结束面试' }).isDisabled(), false)

  await answerInput.fill('推挽可主动输出高低电平，开漏输出高电平需要外部上拉。')
  await page.getByRole('button', { name: '发送回答' }).click()
  await page.getByText('请继续说明 EXTI 中断的排查步骤。').waitFor()
  assert.equal(await answerInput.isDisabled(), false, '下一题出现后不应等待数字人播报')

  await page.getByRole('button', { name: '结束面试' }).click()
  await page.getByText('回答覆盖了关键配置与调试步骤。', { exact: false }).waitFor()
  await page.getByText('综合评分：88 分', { exact: false }).waitFor()
  assert.equal((await page.locator('.status-strip > span').textContent())?.trim(), '已结束')
  assert.equal(await page.getByRole('button', { name: '重新开始' }).isDisabled(), false)

  await context.close()
  console.log('AI interview fail-open flow passed without a placeholder avatar image.')
} finally {
  await browser.close()
}
