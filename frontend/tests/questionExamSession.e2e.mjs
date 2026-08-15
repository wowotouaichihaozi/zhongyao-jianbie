import assert from 'node:assert/strict'
import fs from 'node:fs'

import { chromium } from 'playwright'

const baseUrl = process.env.E2E_BASE_URL || 'http://127.0.0.1:5088'
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

async function openExam(viewport, examData) {
  const context = await browser.newContext({ viewport })
  const page = await context.newPage()
  const examWrites = []
  const unexpectedRequests = []

  await page.addInitScript((payload) => {
    localStorage.setItem('codexPreviewAuth', '1')
    localStorage.setItem('authToken', 'codex-preview-token')
    localStorage.setItem('currentUser', JSON.stringify({ id: 'exam-contract', username: 'exam-contract' }))
    localStorage.setItem('quizHistory', JSON.stringify([{ id: 'existing-history' }]))
    sessionStorage.setItem('qgExamSessionData', JSON.stringify(payload))
  }, examData)

  await page.route('**/api/**', async (route) => {
    const request = route.request()
    const url = new URL(request.url())
    if (request.method() === 'POST' && url.pathname === '/api/question-generator/exam-results') {
      examWrites.push(request.postDataJSON())
      await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ id: 91 }) })
      return
    }
    unexpectedRequests.push(`${request.method()} ${url.pathname}`)
    await route.fulfill({ status: 599, contentType: 'application/json', body: '{}' })
  })

  await page.goto(`${baseUrl}/question-generator/exam-session`, { waitUntil: 'domcontentloaded' })
  return { context, page, examWrites, unexpectedRequests }
}

async function assertNoHorizontalOverflow(page) {
  assert.equal(await page.evaluate(() => document.documentElement.scrollWidth > window.innerWidth + 1), false)
}

async function runEmptyContract() {
  const state = await openExam({ width: 1440, height: 900 }, {
    sheet: { id: 'empty-sheet', title: '空题单', question_bank: { questions: [] } },
    questions: [],
  })

  try {
    await state.page.getByText('暂无可考试题目', { exact: true }).waitFor()
    assert.equal(await state.page.locator('.qg-session-timer').count(), 0)
    assert.equal(await state.page.locator('.qg-session-answer-card').count(), 0)
    assert.equal(await state.page.getByRole('button', { name: '结束考试' }).count(), 0)
    assert.equal(await state.page.getByRole('button', { name: '返回题库生成' }).isVisible(), true)

    await state.page.waitForTimeout(1200)
    assert.deepEqual(state.examWrites, [])
    assert.deepEqual(await state.page.evaluate(() => JSON.parse(localStorage.getItem('quizHistory') || '[]')), [{ id: 'existing-history' }])
    await assertNoHorizontalOverflow(state.page)
  } finally {
    await state.context.close()
  }
}

async function runPopulatedContract(viewport) {
  const question = {
    id: 'q-top-level',
    type: '单选题',
    stem: 'GPIO 输入电平应读取哪个寄存器？',
    options: ['A. IDR', 'B. ODR'],
    answer: 'A',
    score: 2,
  }
  const state = await openExam(viewport, {
    sheet: { id: 'compat-sheet', title: '顶层题目兼容试卷', question_bank: { questions: [] } },
    questions: [question],
  })

  try {
    await state.page.locator('.qg-session-stem', { hasText: question.stem }).waitFor()
    assert.equal(await state.page.locator('.qg-session-timer').isVisible(), true)
    assert.equal(await state.page.locator('.qg-session-answer-card').isVisible(), true)
    assert.equal(await state.page.getByRole('button', { name: '结束考试' }).isVisible(), true)

    const timerBefore = await state.page.locator('.qg-session-timer span').innerText()
    await state.page.waitForTimeout(1200)
    const timerAfter = await state.page.locator('.qg-session-timer span').innerText()
    assert.equal(timerBefore, '00:00')
    assert.notEqual(timerAfter, '00:00')

    state.page.once('dialog', async (dialog) => {
      assert.equal(dialog.message(), '退出后本次作答不会保存，确定返回题库吗？')
      await dialog.dismiss()
    })
    await state.page.getByRole('button', { name: '退出考试' }).click()
    assert.equal(state.page.url().includes('/question-generator/exam-session'), true)
    assert.deepEqual(state.examWrites, [])
    await assertNoHorizontalOverflow(state.page)

    if (viewport.width <= 900) {
      const paper = await state.page.locator('.qg-session-paper').boundingBox()
      const answerCard = await state.page.locator('.qg-session-answer-card').boundingBox()
      assert.ok(paper && answerCard && answerCard.y >= paper.y + paper.height - 1, '移动端答题卡应排在试卷下方')
    }
  } finally {
    await state.context.close()
  }
}

async function runGeneratorLaunchGuardContract() {
  const context = await browser.newContext({ viewport: { width: 1440, height: 900 } })
  const page = await context.newPage()
  const openedPages = []

  context.on('page', openedPage => openedPages.push(openedPage))
  await page.addInitScript(() => {
    localStorage.setItem('codexPreviewAuth', '1')
    localStorage.setItem('authToken', 'codex-preview-token')
    localStorage.setItem('currentUser', JSON.stringify({ id: 'exam-contract', username: 'exam-contract' }))
  })
  await page.route('**/api/**', async (route) => {
    const request = route.request()
    const url = new URL(request.url())
    let body = {}
    if (request.method() === 'GET' && url.pathname === '/api/question-generator/history') {
      body = {
        question_sheets: [{ id: 'empty-sheet', title: '空题单', question_count: 0, question_bank: { questions: [] } }],
        exam_results: [],
      }
    } else if (request.method() === 'GET' && url.pathname === '/api/question-generator/status') {
      body = { status: 'idle' }
    } else if (request.method() === 'GET' && url.pathname === '/api/question-generator/config') {
      body = { config: {} }
    }
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(body) })
  })

  try {
    await page.goto(`${baseUrl}/question-generator`, { waitUntil: 'domcontentloaded' })
    await page.locator('.qg-module-nav-item', { hasText: '考试' }).click()
    await page.getByText('当前题单没有可用题目，请重新选择或生成题单。', { exact: true }).waitFor()
    const launchButton = page.getByRole('button', { name: '开始考试' })
    assert.equal(await launchButton.isDisabled(), true)
    await launchButton.evaluate(button => button.click())
    await page.waitForTimeout(100)
    assert.deepEqual(openedPages, [])
    assert.equal(await page.evaluate(() => sessionStorage.getItem('qgExamSessionData')), null)
  } finally {
    await context.close()
  }
}

try {
  await runEmptyContract()
  await runPopulatedContract({ width: 1440, height: 900 })
  await runPopulatedContract({ width: 390, height: 844 })
  await runGeneratorLaunchGuardContract()
  console.log('exam session UI contract fixture; production DB untouched')
} finally {
  await browser.close()
}
