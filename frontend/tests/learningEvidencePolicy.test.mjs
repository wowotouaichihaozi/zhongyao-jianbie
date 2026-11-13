import assert from 'node:assert/strict'
import test from 'node:test'
import { examStats, learningResourceCompleted } from '../local-exam-evidence.mjs'
import { loadVideoPages } from '../local-resource-history.mjs'

test('unanswered is not wrong, including a legacy false flag', () => {
  const detail = [...Array.from({ length: 8 }, () => ({ user_answer:'A',correct:false })), ...Array.from({ length:32 }, () => ({ user_answer:'',correct:false }))]
  assert.equal(examStats({ detail }).incorrect, 8)
  assert.equal(examStats({ detail }).unanswered, 32)
  assert.equal(examStats({ detail:[{ user_answer:'' }] }).accuracy, null)
})
test('generation and quiz opening are not learning completion', () => {
  assert.equal(learningResourceCompleted('ppt', { status:'complete',result:{ completedAt:'generation' } }), false)
  assert.equal(learningResourceCompleted('ppt', { viewedAt:'now',viewSource:'learning-path-task-open' }), true)
  assert.equal(learningResourceCompleted('quiz', { viewedAt:'now',viewSource:'learning-path-task-open' }), false)
})
test('video pagination cannot loop over the same page forever', async () => {
  let reads=0
  await assert.rejects(() => loadVideoPages(async () => { reads++; return { tasks:[{ taskId:'same' }],hasMore:true } }, () => true))
  assert.equal(reads, 2)
})
