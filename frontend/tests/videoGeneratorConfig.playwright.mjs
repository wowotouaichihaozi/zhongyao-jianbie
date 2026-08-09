import assert from 'node:assert/strict'

import { chromium } from 'playwright'

const baseUrl = process.env.E2E_BASE_URL || 'http://127.0.0.1:3000'
const taskId = 'video-prompt-prefill-task'
const generatedPrompt = '用分镜讲解 STM32 定时器输入捕获，并突出频率测量步骤。'
const browser = await chromium.launch({ headless: true })

try {
  const context = await browser.newContext({ viewport: { width: 1440, height: 900 } })
  const page = await context.newPage()
  const generationRequests = []
  let workflowStarted = false
  let submittedPayload = null

  await page.addInitScript(() => {
    localStorage.setItem('authToken', 'video-generator-config-test-token')
    localStorage.setItem('currentUser', JSON.stringify({
      id: 902,
      username: 'video-generator-test',
      displayName: '视频生成测试用户',
      role: 'user',
    }))
    localStorage.setItem('appMode', 'user')
  })

  await page.route('**/api/**', async (route) => {
    const request = route.request()
    const pathname = new URL(request.url()).pathname

    if (request.method() === 'POST' && (
      pathname === '/api/personalized-resources/agent-task'
      || pathname === `/api/personalized-resources/generated-videos/${taskId}/start`
    )) {
      generationRequests.push(pathname)
    }

    if (request.method() === 'GET' && pathname === `/api/xiaozhi/tasks/${taskId}`) {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          task: {
            taskId,
            status: workflowStarted ? 'running' : 'waiting_for_user',
            prompt: generatedPrompt,
            result: {
              currentStage: workflowStarted ? 'planning' : 'waiting_for_user',
              progress: workflowStarted ? 8 : 0,
              params: submittedPayload?.params || {},
            },
          },
        }),
      })
      return
    }

    if (request.method() === 'POST' && pathname === `/api/personalized-resources/generated-videos/${taskId}/start`) {
      submittedPayload = request.postDataJSON()
      workflowStarted = true
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          task: {
            taskId,
            status: 'running',
            result: { currentStage: 'planning', progress: 5, params: submittedPayload.params },
          },
        }),
      })
      return
    }

    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({}),
    })
  })

  const query = new URLSearchParams({ xzTask: taskId, topic: generatedPrompt })
  await page.goto(`${baseUrl}/personalized-resources/video-generator?${query}`, { waitUntil: 'domcontentloaded' })
  await page.waitForFunction(
    expected => document.querySelector('#video-prompt')?.value === expected,
    generatedPrompt,
  )
  await page.waitForTimeout(200)

  assert.deepEqual(generationRequests, [], '进入生成器和预填提示词不得自动启动视频工作流')

  const engines = await page.locator('.engine-switch input[type="radio"]').evaluateAll(inputs => (
    inputs.map(input => ({ id: input.value, checked: input.checked }))
  ))
  assert.deepEqual(engines, [
    { id: 'seedance_1_5_coze', checked: true },
    { id: 'seedance_2_mini', checked: false },
    { id: 'seedance_2', checked: false },
  ])

  const resolutions = await page.locator('#video-resolution option').evaluateAll(options => (
    options.map(option => option.value)
  ))
  assert.deepEqual(resolutions, ['480p', '720p', '1080p'])
  assert.equal(await page.locator('#video-resolution').inputValue(), '720p')

  await page.getByText('Seedance 2', { exact: true }).click()
  await page.locator('#video-resolution').selectOption('1080p')
  await page.getByRole('button', { name: '运行视频工作流' }).click()
  await page.waitForFunction(() => document.querySelector('.runtime-state i')?.classList.contains('active'))

  assert.deepEqual(generationRequests, [
    `/api/personalized-resources/generated-videos/${taskId}/start`,
  ])
  assert.equal(submittedPayload.prompt, generatedPrompt)
  assert.equal(submittedPayload.params.videoEngine, 'seedance_2')
  assert.equal(submittedPayload.params.resolution, '1080p')

  await context.close()
  console.log('Video generator options and explicit-start flow passed.')
} finally {
  await browser.close()
}
