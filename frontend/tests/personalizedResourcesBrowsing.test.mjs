import assert from 'node:assert/strict'
import fs from 'node:fs'
import test from 'node:test'

const source = fs.readFileSync(new URL('../src/views/PersonalizedResourcesView.vue', import.meta.url), 'utf8')

test('workspace keeps six real tools including the upstream herb model route', () => {
  assert.match(source, /title: '药材模型识别'/)
  assert.match(source, /to: '\/personalized-resources\/herb-model'/)
  assert.match(source, /icon: markRaw\(Box\)/)
  assert.match(source, /grid-template-columns: repeat\(6, minmax\(0, 1fr\)\)/)
  assert.equal((source.match(/class="resource-tool-card"/g) || []).length, 1)
})

test('workspace preserves eight generated TCM topic covers', () => {
  assert.match(source, /v-for="topic in topicCards"/)
  assert.match(source, /class="resource-card topic-card"/)
  assert.match(source, /class="topic-cover-texture"/)
  assert.match(source, /class="topic-cover-icon-image"/)
  assert.match(source, /resource-topic-patterns-v2/)
  assert.match(source, /resource-topic-icons-v2/)
  assert.equal((source.match(/key: '(bagang|herbs|flavor|formula|diagnostics|meridians|wellness|cases)'/g) || []).length, 8)
  assert.doesNotMatch(source, /TopicSolidGlyph/)
})

test('workspace still merges task and generated-video histories into real topics', () => {
  assert.match(source, /getXiaoZhiHistory/)
  assert.match(source, /getXiaoZhiTask/)
  assert.match(source, /getGeneratedVideoTaskHistory\(\{ status: 'complete', limit: 100, offset \}\)/)
  assert.match(source, /const topicCards = computed/)
  assert.match(source, /linkedResource/)
})
