<template>
  <main class="ppt-workbench-page" aria-label="OhMyPPT 演示文稿工作台">
    <div v-if="loading" class="ppt-workbench-loading" role="status" aria-live="polite">
      <LoaderCircle :size="24" aria-hidden="true" />
      <span>正在打开 OhMyPPT...</span>
    </div>
    <iframe
      :key="workbenchUrl"
      :src="workbenchUrl"
      title="OhMyPPT 演示文稿工作台"
      allow="fullscreen; clipboard-read; clipboard-write"
      @load="loading = false"
    />
  </main>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { LoaderCircle } from 'lucide-vue-next'
import { useRoute } from 'vue-router'

const route = useRoute()
const loading = ref(true)

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

const workbenchUrl = computed(() => {
  const params = new URLSearchParams()
  FORWARDED_QUERY_KEYS.forEach((key) => {
    const value = queryValue(route.query[key]).trim()
    if (value) params.set(key, value)
  })

  const hasGenerationInput = ['topic', 'prompt', 'userMessage', 'pageCount', 'pages', 'autostart']
    .some((key) => params.has(key))
  if (!hasGenerationInput) return '/ppt/#/'

  if (!params.has('pageCount') && !params.has('pages')) params.set('pageCount', '6')
  params.set('autostart', '1')

  const taskIdentity =
    queryValue(route.query.xzTask) ||
    queryValue(route.query.cacheKey) ||
    route.fullPath
  const sessionId = `embedded_${stableHash(taskIdentity)}`
  return `/ppt/#/sessions/${encodeURIComponent(sessionId)}/generating?${params.toString()}`
})

watch(workbenchUrl, () => {
  loading.value = true
})
</script>

<style scoped>
.ppt-workbench-page {
  position: relative;
  width: 100%;
  height: 100vh;
  overflow: hidden;
  background: #f4faf8;
}

.ppt-workbench-page iframe {
  display: block;
  width: 100%;
  height: 100%;
  border: 0;
  background: #f4faf8;
}

.ppt-workbench-loading {
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
}

.ppt-workbench-loading svg {
  animation: ppt-workbench-spin 0.8s linear infinite;
}

@keyframes ppt-workbench-spin {
  to {
    transform: rotate(360deg);
  }
}
</style>
