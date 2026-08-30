import assert from 'node:assert/strict'
import fs from 'node:fs'
import test from 'node:test'

const resourceSource = fs.readFileSync(new URL('../src/views/PersonalizedResourcesView.vue', import.meta.url), 'utf8')
const weekSource = fs.readFileSync(new URL('../src/views/LearningPathView.vue', import.meta.url), 'utf8')
const questionSource = fs.readFileSync(new URL('../src/views/QuestionGeneratorView.vue', import.meta.url), 'utf8')
const appSource = fs.readFileSync(new URL('../src/App.vue', import.meta.url), 'utf8')
const routerSource = fs.readFileSync(new URL('../src/router/index.js', import.meta.url), 'utf8')
test('resource history and weekly tasks use live page previews except for generated-video posters', () => {
  assert.match(resourceSource, /class="resource-live-cover"/)
  assert.match(resourceSource, /return String\(resource\?\.type \|\| ''\) === 'generated_video'/)
  assert.match(resourceSource, /generated-videos\/\$\{encodeURIComponent\(taskId\)\}\/poster/)
  assert.match(weekSource, /class="task-resource-live-cover"/)
  assert.match(weekSource, /String\(task\?\.resourceType \|\| ''\) === 'generated_video'/)
  assert.match(weekSource, /generated-videos\/\$\{encodeURIComponent\(taskId\)\}\/poster/)
  assert.doesNotMatch(resourceSource, /captureResourcePageCover|readResourcePageCover|writeResourcePageCover/)
  assert.doesNotMatch(weekSource, /captureResourcePageCover|readResourcePageCover|writeResourcePageCover/)
})

test('exam preview includes a data-driven paper overview sidebar', () => {
  assert.match(questionSource, /class="qg-exam-overview-sidebar"/)
  assert.match(questionSource, /selectedExamTypeDistribution/)
  assert.match(questionSource, /selectedExamKnowledgeFocus/)
  assert.match(questionSource, /selectedExamMinutes/)
  assert.match(questionSource, /grid-template-columns: 15% minmax\(0, 85%\)/)
  assert.match(questionSource, /grid-template-columns: minmax\(0, 67%\) minmax\(0, 31%\)/)
})

test('primary navigation pages retain their component state between route switches', () => {
  assert.match(appSource, /<KeepAlive[^>]+:max="10"/)
  assert.match(appSource, /v-if="route\.meta\?\.keepAlive"/)
  assert.match(appSource, /navigationCacheEpoch\.value \+= 1/)
  for (const routeName of [
    'learning-profile',
    'effect-assessment',
    'learning-path-stage-detail',
    'personalized-resources',
    'herb-recognition',
    'knowledge-network',
    'life-tree',
  ]) {
    const routeBlock = new RegExp(`name: '${routeName}'[\\s\\S]{0,900}?keepAlive: true`)
    assert.match(routerSource, routeBlock)
  }
  assert.doesNotMatch(routerSource, /name: 'digital-human-interview'[\s\S]{0,300}?keepAlive: true/)
})
