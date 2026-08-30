import assert from 'node:assert/strict'
import fs from 'node:fs'
import test from 'node:test'

const mapSource = fs.readFileSync(new URL('../src/views/LearningPathStageDetailView.vue', import.meta.url), 'utf8')
const weekSource = fs.readFileSync(new URL('../src/views/LearningPathView.vue', import.meta.url), 'utf8')
const apiSource = fs.readFileSync(new URL('../src/services/api.js', import.meta.url), 'utf8')

test('week map never starts an automatic remaining-weeks loop', () => {
  assert.doesNotMatch(mapSource, /generateRemainingLearningPath/)
  assert.doesNotMatch(mapSource, /generateRemainingWeeks\(/)
  assert.match(mapSource, /getLearningPathConfig\(\{ summary: true \}\)/)
})

test('opening a weekly task records explicit view evidence', () => {
  assert.match(weekSource, /markNodeCacheViewed\(week\.cacheKey/)
  assert.match(weekSource, /viewedAt: Date\.now\(\)/)
  assert.match(weekSource, /allWeekTaskNodes\.value\.filter\(isWeekTaskViewed\)/)
  assert.match(weekSource, /cache\?\.viewSource !== 'learning-path-task-open'/)
  assert.match(weekSource, /profileReportId: Number\(pathConfig\.value\?\.meta/)
  assert.match(apiSource, /keepalive: true/)
  assert.match(weekSource, /getLearningPathConfig\(\{ summary: true \}\)/)
})

test('weekly progress labels distinguish not started, in progress, and complete', () => {
  assert.match(weekSource, /progressPercent\.value <= 0[^]*未开始/)
  assert.match(weekSource, /progressPercent\.value >= 100[^]*已完成/)
  assert.match(weekSource, /return `\$\{currentWeekLabel\.value\}进行中`/)
  assert.match(mapSource, /progressPercent >= 100 \? 'done' : progressPercent > 0 \? 'current' : 'available'/)
  assert.match(mapSource, /state === 'done' \? '已完成' : state === 'current' \? '进行中' : '未开始'/)
  assert.match(mapSource, /optionalProgressPercent\(week\.progressPercent\)/)
  assert.match(mapSource, /totalProgress \/ sortedNodes\.value\.length/)
})

test('learning path config supports a lightweight summary request', () => {
  assert.match(apiSource, /params: \{ summary: options\.summary === true \? 1 : 0 \}/)
})

test('empty learning path distinguishes active background generation from a missing path', () => {
  assert.match(mapSource, /generationIsRunning \? '正在生成学习路径' :/)
  assert.match(mapSource, /generationStatusMessage/)
  assert.match(mapSource, /v-if="generationIsRunning" class="empty-path-progress"/)
  assert.match(mapSource, /<button v-else type="button" @click="handlePersonalizationAction">/)
})
