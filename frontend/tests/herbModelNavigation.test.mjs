import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import test from 'node:test'

const herbViewPath = new URL('../src/views/HerbModelRecognitionView.vue', import.meta.url)
const learningPathPath = new URL('../src/views/LearningPathView.vue', import.meta.url)
const stageDetailPath = new URL('../src/views/LearningPathStageDetailView.vue', import.meta.url)

test('herb model back button uses history with learning-path and resource fallbacks', async () => {
  const source = await readFile(herbViewPath, 'utf8')
  assert.match(source, /@click="goBack"/)
  assert.match(source, /window\.history\.state\?\.back/)
  assert.match(source, /historyBack\.startsWith\('\/learning-path'\)/)
  assert.match(source, /router\.back\(\)/)
  assert.match(source, /name: 'learning-path-week-detail'/)
  assert.match(source, /router\.push\('\/personalized-resources'\)/)
  assert.doesNotMatch(source, /@click="router\.push\('\/personalized-resources'\)"/)
})

test('both learning-path task views keep herb models in the current tab', async () => {
  const [learningPath, stageDetail] = await Promise.all([
    readFile(learningPathPath, 'utf8'),
    readFile(stageDetailPath, 'utf8'),
  ])
  assert.match(learningPath, /normalizeTaskResourceType\(week\?\.resourceType\) === 'herb-model'/)
  assert.doesNotMatch(learningPath, /normalizeResourceType\(/)
  assert.match(learningPath, /router\.push\(weekActionHref\(week\)\)/)
  assert.match(stageDetail, /node\.resourceType === 'herb-model'/)
  assert.match(stageDetail, /await router\.push\(href\)/)
})
