import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import test from 'node:test'

const viewSource = readFileSync(new URL('../src/views/LearningProfileView.vue', import.meta.url), 'utf8')
const apiSource = readFileSync(new URL('../src/services/api.js', import.meta.url), 'utf8')

test('profile history exposes a confirmed persistent delete action', () => {
  assert.match(viewSource, /@click\.stop="deleteProfileVersion\(report\)"/)
  assert.match(viewSource, /window\.confirm\(/)
  assert.match(viewSource, /await deleteLearningProfile\(report\.id\)/)
  assert.match(viewSource, /class="history-delete-button"/)
  assert.match(apiSource, /apiClient\.delete\(`\/api\/learning-profile\/profiles\/\$\{reportId\}`\)/)
})
