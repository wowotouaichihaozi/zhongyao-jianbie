import assert from 'node:assert/strict'
import fs from 'node:fs'
import test from 'node:test'

const viewSource = fs.readFileSync(new URL('../src/views/HerbRecognitionView.vue', import.meta.url), 'utf8')
const apiSource = fs.readFileSync(new URL('../src/services/api.js', import.meta.url), 'utf8')

test('successful herb recognition automatically starts grounded model analysis', () => {
  assert.match(viewSource, /loadHerbAnalysis\(resultName\.value\)/)
  assert.match(apiSource, /post\('\/api\/herb-recognition\/analyze', \{ name \}/)
  assert.match(viewSource, /正在检索知识库并分析药物特性/)
})

test('analysis UI exposes structured learning fields and an explicit failure state', () => {
  for (const label of ['来源与药用部位', '性味归经', '功效主治', '性状鉴别', '配伍思路', '用药注意']) {
    assert.match(viewSource, new RegExp(label))
  }
  assert.match(viewSource, /<h3>药物讲解<\/h3>/)
  assert.match(viewSource, /analysisResult\.agentExplanation/)
  assert.match(viewSource, /analysisError/)
  assert.match(viewSource, /重新分析/)
  assert.match(viewSource, /不替代药材真伪鉴定、临床诊断或处方建议/)
})

test('the recognition page owns a viewport-height vertical scroll container', () => {
  assert.match(viewSource, /\.herb-recognition-page\s*\{[\s\S]*?height:\s*calc\(100vh - 72px\)/)
  assert.match(viewSource, /\.herb-recognition-page\s*\{[\s\S]*?overflow-y:\s*auto/)
  assert.doesNotMatch(viewSource, /\.herb-recognition-page\s*\{[\s\S]{0,240}?overflow-y:\s*hidden/)
})
