import assert from 'node:assert/strict'
import fs from 'node:fs'
import path from 'node:path'
import test from 'node:test'
import { fileURLToPath } from 'node:url'

const testDirectory = path.dirname(fileURLToPath(import.meta.url))
const frontendDirectory = path.resolve(testDirectory, '..')
const knowledgePath = path.join(frontendDirectory, 'src/data/tcm-knowledge-network.v1.2-substantive.json')
const adapterPath = path.join(frontendDirectory, 'wu-xing-holo-core-runner/knowledgeDataAdapter.ts')
const spherePath = path.join(frontendDirectory, 'wu-xing-holo-core-runner/components/HoloSphere.tsx')
const originalSpherePath = path.join(frontendDirectory, 'wu-xing-holo-core-original/src/components/HoloSphere.tsx')
const runnerAppPath = path.join(frontendDirectory, 'wu-xing-holo-core-runner/App.tsx')

function flatten(entry, result = []) {
  if (!entry || typeof entry !== 'object') return result
  result.push(entry)
  for (const child of Array.isArray(entry.children) ? entry.children : []) flatten(child, result)
  return result
}

test('every supplied knowledge node has a displayable learning explanation', () => {
  const knowledge = JSON.parse(fs.readFileSync(knowledgePath, 'utf8'))
  const entries = flatten(knowledge.root)
  const learningNodes = entries.filter(entry => entry.id !== 'TCM_ROOT')

  assert.equal(entries.length, 1601)
  assert.equal(learningNodes.length, 1600)
  assert.equal(
    learningNodes.filter(entry => !String(entry.explanation || entry.summary || '').trim()).length,
    0,
  )
})

test('runner uses stable evenly spaced siblings inside compact domain clusters', () => {
  const adapter = fs.readFileSync(adapterPath, 'utf8')

  assert.match(adapter, /function getFibonacciSpherePoints/)
  assert.match(adapter, /function nodeExplanation/)
  assert.match(adapter, /下设\$\{childTitles\.length\}个子主题/)
  assert.match(adapter, /function getStableSiblingOffsets/)
  assert.match(adapter, /function rotatePoint/)
  assert.match(adapter, /const entriesByDomain = new Map/)
  assert.match(adapter, /const domainCenters = getFibonacciSpherePoints\(orderedDomains\.length, 9\.5/)
  assert.match(adapter, /const topicOffsets = getFibonacciSpherePoints\(domainEntries\.length, 5, 0\.4/)
  assert.match(adapter, /const subOffsets = getStableSiblingOffsets\(mainNode\.id, subEntries\.length, 2\.2, 0\.3\)/)
  assert.match(adapter, /const pointOffsets = getStableSiblingOffsets\(subNode\.id, pointEntries\.length, 1\.2, 0\.16\)/)
  assert.match(adapter, /const minimumDistance = Math\.max\(0\.7, baseRadius \* 0\.72\)/)
  assert.doesNotMatch(adapter, /getStableOffset/)
  assert.doesNotMatch(adapter, /Math\.random\(\)/)
})

test('runner keeps navigation and classifications outside the original sphere', () => {
  const sphere = fs.readFileSync(spherePath, 'utf8')
  const originalSphere = fs.readFileSync(originalSpherePath, 'utf8')
  const app = fs.readFileSync(runnerAppPath, 'utf8')

  assert.match(sphere, /import OriginalHoloSphere/)
  assert.match(sphere, /<OriginalHoloSphere selectedId=\{selectedId\} activeDomain=\{activeDomain\} onSelect=\{onSelect\} focusToken=\{focusToken\} \/>/)
  assert.match(sphere, /activeDomain\?: string/)
  assert.match(originalSphere, /autoRotate=\{true\}/)
  assert.match(originalSphere, /minDistance=\{2\}/)
  assert.match(originalSphere, /function FocusCamera/)
  assert.match(originalSphere, /startCamera = useRef\(new THREE\.Vector3\(\)\)/)
  assert.match(originalSphere, /progress\.current = Math\.min\(1, progress\.current \+ delta \/ 0\.7\)/)
  assert.match(originalSphere, /camera\.position\.lerpVectors\(startCamera\.current, destination\.current, eased\)/)
  assert.doesNotMatch(originalSphere, /camera\.position\.distanceTo\(destination\.current\) < 0\.03/)
  assert.match(originalSphere, /function focusedNodeIds/)
  assert.match(originalSphere, /selected\.level === 'knowledge_point'/)
  assert.match(originalSphere, /pointerEvents="none"/)
  assert.match(originalSphere, /depthWrite=\{false\}/)
  assert.match(originalSphere, /-translate-y-1\/2 translate-x-5 whitespace-nowrap/)
  assert.match(originalSphere, /const appendEdge = \(target: number\[\], source: GraphNode, destination: GraphNode\)/)
  assert.match(originalSphere, /function domainTint/)
  assert.match(originalSphere, /const groups = new Map<string, \{ normal: number\[\]; active: number\[\] \}>\(\)/)
  assert.match(originalSphere, /blending=\{THREE\.NormalBlending\}/)
  assert.match(originalSphere, /key=\{`active-edges-\$\{selectedId\}/)
  assert.match(originalSphere, /key=\{`active-geometry-\$\{selectedId\}/)
  assert.doesNotMatch(originalSphere, /QuadraticBezierCurve3/)
  assert.doesNotMatch(originalSphere, /dimEdgePositions\.length > 0/)
  assert.match(originalSphere, /desiredDistance = isOverview \? 22\.45 : isDomainFocus \? 13\.5 : 9\.5/)
  assert.match(originalSphere, /target\.current\.set\(selected\?\.x \|\| 0, selected\?\.y \|\| 0, selected\?\.z \|\| 0\)/)
  assert.match(originalSphere, /data-active-domain=\{activeDomain \|\| undefined\}/)
  assert.match(app, /星图导航/)
  assert.match(app, /搜索知识点、主题或知识域/)
  assert.match(app, /data-search-result=/)
  assert.match(app, /searchResults = useMemo/)
  assert.match(app, /selectDomain\(domain: string\)/)
  assert.match(app, /具体知识点/)
  assert.match(app, /max-h-\[calc\(100dvh-6rem\)\]/)
  assert.doesNotMatch(app, /if \(showPanel\) setNavigationOpen\(false\)/)
  assert.match(app, /if \(openPanel\) setNavigationOpen\(true\)/)
  assert.match(app, /selectedNode\?\.level === 'knowledge_point'[\s\S]*nodeById\.get\(selectedNode\.parent\)/)
  assert.match(app, /<InfoPanel selected=\{selectedNode\}[\s\S]*embedded \/>/)
  assert.match(app, /selectFromNavigation\(topic\.id, true\)/)
  assert.match(app, /selectFromNavigation\(subtopic\.id, true\)/)
})
