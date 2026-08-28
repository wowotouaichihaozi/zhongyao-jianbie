import assert from 'node:assert/strict'
import fs from 'node:fs'
import test from 'node:test'

const source = fs.readFileSync(new URL('../src/views/PersonalizedResourcesView.vue', import.meta.url), 'utf8')

test('history resources provide keyword search, type filtering, and pagination', () => {
  assert.match(source, /v-model="searchQuery"/)
  assert.match(source, /placeholder="搜索资源名称或内容"/)
  assert.match(source, /<select v-model="activeCategory" aria-label="按资源类型筛选">/)
  assert.match(source, /const pageSize = 9/)
  assert.match(source, /const paginatedResources = computed/)
  assert.match(source, /v-for="resource in paginatedResources"/)
  assert.match(source, /aria-label="历史资源分页"/)
  assert.match(source, /watch\(\[activeCategory, searchQuery\]/)
})

test('history resources use real-page cover cards', () => {
  assert.match(source, /class="resource-launcher-grid"/)
  assert.match(source, /class="resource-gallery"/)
  assert.match(source, /class="resource-cover-card"/)
  assert.match(source, /class="resource-live-cover"/)
  assert.match(source, /:src="getResourcePreviewUrl\(resource\)"/)
  assert.match(source, /grid-template-columns: repeat\(3, minmax\(0, 1fr\)\)/)
  assert.match(source, /function getResourcePreviewUrl\(resource\)/)
  assert.match(source, /\.history-search:focus-within/)
  assert.doesNotMatch(source, /class="resource-table"/)
  assert.doesNotMatch(source, /class="resource-tool-sidebar"/)
})

test('video histories use static covers and include waiting AI video tasks', () => {
  assert.match(source, /v-if="usesStaticCover\(resource\)"/)
  assert.match(source, /class="resource-static-cover"/)
  assert.match(source, /resource\?\.type === 'video'/)
  assert.match(source, /resource\?\.type === 'generated_video'/)
  assert.match(source, /getGeneratedVideoTaskHistory\(\{ limit: 100, offset \}\)/)
  assert.doesNotMatch(source, /getGeneratedVideoTaskHistory\(\{ status: 'complete'/)
})
