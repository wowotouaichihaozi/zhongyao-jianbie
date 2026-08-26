<template>
  <main
    class="ppt-workbench-page"
    :class="{ 'ppt-workbench-page--nested': isNestedFrame }"
    aria-label="OhMyPPT 演示文稿工作台"
  >
    <header v-if="!isNestedFrame" class="ppt-workbench-toolbar">
      <RouterLink
        class="ppt-workbench-return"
        to="/personalized-resources"
        aria-label="返回个性化资源"
        title="返回个性化资源"
      >
        <ArrowLeft :size="18" aria-hidden="true" />
        <span>返回个性化资源</span>
      </RouterLink>
      <strong>OhMyPPT</strong>
    </header>

    <section class="ppt-workbench-surface">
      <div v-if="isNestedFrame" class="ppt-workbench-state ppt-workbench-error" role="alert">
        <TriangleAlert :size="28" aria-hidden="true" />
        <strong>已阻止重复嵌入</strong>
        <span>请返回上一层后重新打开 OhMyPPT，页面不会继续创建嵌套工作台。</span>
      </div>

      <div v-else-if="loading" class="ppt-workbench-state" role="status" aria-live="polite">
        <LoaderCircle class="spin" :size="24" aria-hidden="true" />
        <span>正在检查并打开 OhMyPPT...</span>
      </div>

      <div v-else-if="loadError" class="ppt-workbench-state ppt-workbench-error" role="alert">
        <TriangleAlert :size="28" aria-hidden="true" />
        <strong>OhMyPPT 暂时不可用</strong>
        <span>{{ loadError }}</span>
        <button type="button" @click="prepareWorkbench">
          <RefreshCw :size="16" aria-hidden="true" />
          重试
        </button>
      </div>

      <iframe
        v-if="!isNestedFrame && iframeSrc"
        :key="iframeSrc"
        :src="iframeSrc"
        title="OhMyPPT 演示文稿工作台"
        allow="fullscreen; clipboard-read; clipboard-write"
        @load="handleFrameLoad"
      />
    </section>
  </main>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { ArrowLeft, LoaderCircle, RefreshCw, TriangleAlert } from 'lucide-vue-next'
import { RouterLink, useRoute } from 'vue-router'

const route = useRoute()
const loading = ref(true)
const loadError = ref('')
const iframeSrc = ref('')
let prepareSequence = 0
const isNestedFrame = window.self !== window.top
const PPT_WEB_BUILD_VERSION = '20260826-ppt-history-v3'
const PPT_ENTRY_URL = `/ppt/index.html?v=${encodeURIComponent(PPT_WEB_BUILD_VERSION)}`

const FORWARDED_QUERY_KEYS = [
  'topic',
  'prompt',
  'userMessage',
  'pageCount',
  'pages',
  'styleId',
  'modelConfigId',
  'autostart',
]

function queryValue(value) {
  return Array.isArray(value) ? String(value[0] || '') : String(value || '')
}

function stableHash(value) {
  let hash = 2166136261
  for (let index = 0; index < value.length; index += 1) {
    hash ^= value.charCodeAt(index)
    hash = Math.imul(hash, 16777619)
  }
  return (hash >>> 0).toString(36)
}

function pptWorkbenchLocation(hashPath = '/') {
  const normalizedHashPath = hashPath.startsWith('/') ? hashPath : `/${hashPath}`
  return `${PPT_ENTRY_URL}#${normalizedHashPath}`
}

const workbenchUrl = computed(() => {
  const params = new URLSearchParams()
  FORWARDED_QUERY_KEYS.forEach((key) => {
    const value = queryValue(route.query[key]).trim()
    if (value) params.set(key, value)
  })

  const hasGenerationInput = ['topic', 'prompt', 'userMessage', 'pageCount', 'pages', 'autostart']
    .some((key) => params.has(key))
  if (!hasGenerationInput) {
    const historyRequested = queryValue(route.query.tab).trim().toLowerCase() === 'history'
    return pptWorkbenchLocation(historyRequested ? '/sessions' : '/')
  }

  if (!params.has('pageCount') && !params.has('pages')) params.set('pageCount', '6')
  params.set('autostart', '1')

  const taskIdentity =
    queryValue(route.query.xzTask) ||
    queryValue(route.query.cacheKey) ||
    route.fullPath
  const sessionId = `embedded_${stableHash(taskIdentity)}`
  return pptWorkbenchLocation(`/sessions/${encodeURIComponent(sessionId)}/generating?${params.toString()}`)
})

async function prepareWorkbench() {
  const sequence = ++prepareSequence
  loading.value = true
  loadError.value = ''
  iframeSrc.value = ''
  if (isNestedFrame) {
    loading.value = false
    return
  }
  try {
    const response = await fetch(PPT_ENTRY_URL, { cache: 'no-store', credentials: 'same-origin' })
    if (!response.ok) throw new Error(`HTTP ${response.status}`)
    if (sequence !== prepareSequence) return
    iframeSrc.value = workbenchUrl.value
  } catch (error) {
    if (sequence !== prepareSequence) return
    loading.value = false
    const reason = error instanceof Error ? error.message : '未知错误'
    loadError.value = `无法访问同源工作台 /ppt/（${reason}）`
  }
}

function handleFrameLoad() {
  loading.value = false
}

watch(workbenchUrl, () => {
  void prepareWorkbench()
}, { immediate: true })
</script>

<style scoped>
.ppt-workbench-page {
  position: relative;
  width: 100%;
  height: 100vh;
  height: 100dvh;
  display: grid;
  grid-template-rows: 52px minmax(0, 1fr);
  overflow: hidden;
  background: #f7f9f8;
  box-sizing: border-box;
}

.ppt-workbench-page--nested {
  grid-template-rows: minmax(0, 1fr);
}

.ppt-workbench-toolbar {
  position: relative;
  z-index: 3;
  min-width: 0;
  padding: 0 16px;
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto minmax(0, 1fr);
  align-items: center;
  border-bottom: 1px solid #dfe5e2;
  background: #ffffff;
  box-sizing: border-box;
}

.ppt-workbench-toolbar > strong {
  grid-column: 2;
  color: #26332f;
  font-size: 15px;
  letter-spacing: 0;
}

.ppt-workbench-return {
  grid-column: 1;
  justify-self: start;
  min-width: 0;
  min-height: 36px;
  padding: 0 10px;
  display: inline-flex;
  align-items: center;
  gap: 7px;
  border-radius: 4px;
  color: #235f4b;
  font-size: 14px;
  font-weight: 700;
  text-decoration: none;
}

.ppt-workbench-return:hover {
  background: #eef6f2;
}

.ppt-workbench-surface {
  position: relative;
  min-width: 0;
  min-height: 0;
  overflow: hidden;
  background: #f4faf8;
}

.ppt-workbench-surface iframe {
  display: block;
  width: 100%;
  height: 100%;
  border: 0;
  background: #f4faf8;
}

.ppt-workbench-state {
  position: absolute;
  inset: 0;
  z-index: 2;
  display: grid;
  place-content: center;
  justify-items: center;
  gap: 10px;
  color: #39705b;
  background: #f4faf8;
  font-size: 13px;
  font-weight: 700;
  text-align: center;
}

.ppt-workbench-error {
  padding: 24px;
  color: #3f514b;
}

.ppt-workbench-error > span {
  max-width: 560px;
  color: #687b75;
  font-weight: 500;
  line-height: 1.6;
}

.ppt-workbench-error button {
  min-height: 38px;
  margin-top: 4px;
  padding: 0 16px;
  display: inline-flex;
  align-items: center;
  gap: 7px;
  border: 1px solid #98bcae;
  border-radius: 4px;
  background: #ffffff;
  color: #235f4b;
  font: inherit;
  cursor: pointer;
}

.ppt-workbench-state .spin {
  animation: ppt-workbench-spin 0.8s linear infinite;
}

@media (max-width: 600px) {
  .ppt-workbench-page {
    grid-template-rows: 48px minmax(0, 1fr);
  }

  .ppt-workbench-toolbar {
    padding: 0 10px;
  }

  .ppt-workbench-return {
    width: 36px;
    padding: 0;
    justify-content: center;
  }

  .ppt-workbench-return span {
    display: none;
  }
}

@keyframes ppt-workbench-spin {
  to {
    transform: rotate(360deg);
  }
}
</style>

<style>
body:has(.ppt-workbench-page),
#app:has(.ppt-workbench-page) {
  overflow: hidden !important;
}

#app:has(.ppt-workbench-page) {
  padding-bottom: 0 !important;
  box-sizing: border-box;
}
</style>
