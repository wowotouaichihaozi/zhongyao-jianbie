import assert from 'node:assert/strict'
import fs from 'node:fs'
import test from 'node:test'

const source = fs.readFileSync(new URL('../src/views/PersonalizedResourcesView.vue', import.meta.url), 'utf8')

test('history resources provide keyword search, type filtering, and pagination', () => {
  assert.match(source, /v-model="searchQuery"/)
  assert.match(source, /placeholder="搜索资源"/)
  assert.match(source, /<select v-model="activeCategory" aria-label="按资源类型筛选">/)
  assert.match(source, /const pageSize = 12/)
  assert.match(source, /const paginatedResources = computed/)
  assert.match(source, /v-for="resource in paginatedResources"/)
  assert.match(source, /aria-label="历史资源分页"/)
  assert.match(source, /watch\(\[activeCategory, searchQuery\]/)
})

test('history resources use real-page cover cards', () => {
  assert.match(source, /class="resource-launcher-grid"/)
  assert.doesNotMatch(source, /tool\.description/)
  assert.doesNotMatch(source, /按学习画像生成讲解视频/)
  assert.match(source, /class="resource-gallery"/)
  assert.match(source, /class="resource-cover-card"/)
  assert.match(source, /class="resource-live-cover"/)
  assert.match(source, /:src="getResourcePreviewUrl\(resource\)"/)
  assert.match(source, /grid-template-columns: repeat\(6, minmax\(0, 1fr\)\)/)
  assert.match(source, /aspect-ratio: 16 \/ 9/)
  assert.match(source, /function getResourcePreviewUrl\(resource\)/)
  assert.match(source, /\.history-search:focus-within/)
  assert.doesNotMatch(source, /class="resource-table"/)
  assert.doesNotMatch(source, /class="resource-tool-sidebar"/)
})

test('only AI-generated videos use static posters and waiting tasks remain visible', () => {
  assert.match(source, /v-if="usesStaticCover\(resource\)"/)
  assert.match(source, /class="resource-static-cover"/)
  assert.match(source, /String\(resource\?\.type \|\| ''\) === 'generated_video'/)
  assert.match(source, /getGeneratedVideoTaskHistory\(\{ limit: 100, offset \}\)/)
  assert.doesNotMatch(source, /getGeneratedVideoTaskHistory\(\{ status: 'complete'/)
})
