import assert from 'node:assert/strict'
import fs from 'node:fs'
import test from 'node:test'

const digitalTwinSource = fs.readFileSync(new URL('../../admin/src/views/digital-twin/index.vue', import.meta.url), 'utf8')
const pptWorkbenchSource = fs.readFileSync(new URL('../src/views/PptWorkbenchView.vue', import.meta.url), 'utf8')
const appSource = fs.readFileSync(new URL('../src/App.vue', import.meta.url), 'utf8')
const learnerRouterSource = fs.readFileSync(new URL('../src/router/index.js', import.meta.url), 'utf8')
const learnerNavbarSource = fs.readFileSync(new URL('../src/components/TopNavbar.vue', import.meta.url), 'utf8')
const adminRoutesSource = fs.readFileSync(new URL('../../admin/src/router/routes/index.ts', import.meta.url), 'utf8')

test('digital twin lives in the admin route, scales its scene, and exposes recovery', () => {
  assert.match(digitalTwinSource, /const SCENE_WIDTH = 1920/)
  assert.match(digitalTwinSource, /const SCENE_HEIGHT = 1080/)
  assert.match(digitalTwinSource, /Math\.min\(viewport\.clientWidth \/ SCENE_WIDTH, viewport\.clientHeight \/ SCENE_HEIGHT\)/)
  assert.match(digitalTwinSource, /new ResizeObserver\(fitScene\)/)
  assert.match(digitalTwinSource, /return '\/digital-twin\/index\.html'/)
  assert.match(digitalTwinSource, /v-else-if="loadError"/)
  assert.match(digitalTwinSource, /@click="prepareFrame"/)
  assert.match(digitalTwinSource, /overflow: hidden/)
  assert.match(adminRoutesSource, /name: 'digital-twin'/)
  assert.match(adminRoutesSource, /component: 'layout\.base\$view\.digital-twin'/)
  assert.match(learnerRouterSource, /path: '\/agent-digital-twin',[\s\S]*?redirect: '\/personalized-resources'/)
  assert.doesNotMatch(learnerNavbarSource, /to: '\/agent-digital-twin'/)
})

test('PPT workbench preflights the embedded app and never traps the learner in a blank iframe', () => {
  assert.match(pptWorkbenchSource, /to="\/personalized-resources"/)
  assert.match(pptWorkbenchSource, /const PPT_WEB_BUILD_VERSION = '20260826-ppt-history-v3'/)
  assert.match(pptWorkbenchSource, /const PPT_ENTRY_URL = `\/ppt\/index\.html\?v=/)
  assert.match(pptWorkbenchSource, /fetch\(PPT_ENTRY_URL/)
  assert.match(pptWorkbenchSource, /route\.query\.tab/)
  assert.match(pptWorkbenchSource, /historyRequested \? '\/sessions' : '\/'/)
  assert.match(pptWorkbenchSource, /v-else-if="loadError"/)
  assert.match(pptWorkbenchSource, /@click="prepareWorkbench"/)
  assert.match(pptWorkbenchSource, /v-if="!isNestedFrame && iframeSrc"/)
  assert.match(pptWorkbenchSource, /grid-template-rows: 52px minmax\(0, 1fr\)/)
})

test('PPT wrapper blocks recursive embedding and framed main apps hide duplicate global chrome', () => {
  assert.match(pptWorkbenchSource, /const isNestedFrame = window\.self !== window\.top/)
  assert.match(pptWorkbenchSource, /v-if="isNestedFrame"/)
  assert.match(pptWorkbenchSource, /v-if="!isNestedFrame && iframeSrc"/)
  assert.match(appSource, /const isFramedApp = window\.self !== window\.top/)
  assert.match(appSource, /if \(isFramedApp\) return false/g)
})

test('framed knowledge views hide duplicate global navigation and assistants', () => {
  assert.match(appSource, /const isFramedApp = window\.self !== window\.top/)
  assert.match(appSource, /if \(isFramedApp\) return false/)
  assert.match(appSource, /'life-tree'/)
})
