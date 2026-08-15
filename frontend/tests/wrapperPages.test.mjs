import assert from 'node:assert/strict'
import fs from 'node:fs'
import test from 'node:test'

const digitalTwinSource = fs.readFileSync(new URL('../src/views/AgentDigitalTwinView.vue', import.meta.url), 'utf8')
const pptWorkbenchSource = fs.readFileSync(new URL('../src/views/PptWorkbenchView.vue', import.meta.url), 'utf8')

test('digital twin scales the fixed scene into the available viewport and exposes recovery', () => {
  assert.match(digitalTwinSource, /const SCENE_WIDTH = 1920/)
  assert.match(digitalTwinSource, /const SCENE_HEIGHT = 1080/)
  assert.match(digitalTwinSource, /Math\.min\(page\.clientWidth \/ SCENE_WIDTH, page\.clientHeight \/ SCENE_HEIGHT\)/)
  assert.match(digitalTwinSource, /new ResizeObserver\(fitScene\)/)
  assert.match(digitalTwinSource, /fetch\('\/digital-twin\/index\.html'/)
  assert.match(digitalTwinSource, /v-else-if="loadError"/)
  assert.match(digitalTwinSource, /@click="prepareFrame"/)
  assert.match(digitalTwinSource, /overflow: hidden/)
})

test('PPT workbench preflights the embedded app and never traps the learner in a blank iframe', () => {
  assert.match(pptWorkbenchSource, /to="\/personalized-resources"/)
  assert.match(pptWorkbenchSource, /fetch\('\/ppt\/'/)
  assert.match(pptWorkbenchSource, /v-else-if="loadError"/)
  assert.match(pptWorkbenchSource, /@click="prepareWorkbench"/)
  assert.match(pptWorkbenchSource, /v-if="iframeSrc"/)
  assert.match(pptWorkbenchSource, /grid-template-rows: 52px minmax\(0, 1fr\)/)
})
