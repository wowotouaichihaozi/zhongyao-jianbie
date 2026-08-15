import assert from 'node:assert/strict'
import test from 'node:test'

import { elapsedSecondsSince, resolveExamQuestions } from '../src/utils/questionExamSession.js'

test('resolves nested sheet questions before the session-level compatibility payload', () => {
  const nested = [{ id: 'nested' }]
  const topLevel = [{ id: 'top-level' }]

  assert.equal(resolveExamQuestions({
    sheet: { question_bank: { questions: nested } },
    questions: topLevel,
  }), nested)
})

test('falls back to top-level session questions when the sheet has no populated question list', () => {
  const topLevel = [{ id: 'top-level' }]

  assert.equal(resolveExamQuestions({
    sheet: { question_bank: { questions: [] } },
    questions: topLevel,
  }), topLevel)
  assert.deepEqual(resolveExamQuestions({ sheet: { questions: null }, questions: null }), [])
})

test('uses direct sheet questions when an empty question bank is present', () => {
  const directQuestions = [{ id: 'direct', score: 4 }]

  assert.equal(resolveExamQuestions({
    sheet: { question_bank: { questions: [] }, questions: directQuestions },
  }), directQuestions)
})

test('derives elapsed time from wall-clock timestamps', () => {
  assert.equal(elapsedSecondsSince(10_000, 13_999), 3)
  assert.equal(elapsedSecondsSince(10_000, 70_250), 60)
  assert.equal(elapsedSecondsSince(10_000, 9_000), 0)
  assert.equal(elapsedSecondsSince(0, 20_000), 0)
})
