<template>
  <main ref="pageRef" class="digital-twin-page">
    <div v-if="iframeSrc" class="digital-twin-viewport">
      <div class="digital-twin-stage" :style="stageStyle">
        <iframe
          :key="iframeSrc"
          class="digital-twin-frame"
          :src="iframeSrc"
          :style="frameStyle"
          title="中药鉴别智能体数字孪生架构展示"
          allow="fullscreen"
          @load="handleFrameLoad"
        />
      </div>
    </div>

    <div v-if="loading" class="page-state" role="status">
      <LoaderCircle class="spin" :size="28" aria-hidden="true" />
      <span>正在加载数字孪生场景...</span>
    </div>

    <div v-else-if="loadError" class="page-state page-error" role="alert">
      <TriangleAlert :size="30" aria-hidden="true" />
      <strong>数字孪生资源加载失败</strong>
      <span>{{ loadError }}</span>
      <button type="button" @click="prepareFrame">
        <RefreshCw :size="16" aria-hidden="true" />
        重试
      </button>
    </div>
  </main>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { LoaderCircle, RefreshCw, TriangleAlert } from 'lucide-vue-next'

const SCENE_WIDTH = 1920
const SCENE_HEIGHT = 1080

const pageRef = ref(null)
const iframeSrc = ref('')
const loading = ref(true)
const loadError = ref('')
const sceneScale = ref(1)
let resizeObserver = null

const stageStyle = computed(() => ({
  width: `${SCENE_WIDTH * sceneScale.value}px`,
  height: `${SCENE_HEIGHT * sceneScale.value}px`,
}))

const frameStyle = computed(() => ({
  width: `${SCENE_WIDTH}px`,
  height: `${SCENE_HEIGHT}px`,
  transform: `scale(${sceneScale.value})`,
}))

function fitScene() {
  const page = pageRef.value
  if (!page?.clientWidth || !page?.clientHeight) return
  sceneScale.value = Math.min(page.clientWidth / SCENE_WIDTH, page.clientHeight / SCENE_HEIGHT)
}

async function prepareFrame() {
  loading.value = true
  loadError.value = ''
  iframeSrc.value = ''
  try {
    const response = await fetch('/digital-twin/index.html', { cache: 'no-store', credentials: 'same-origin' })
    if (!response.ok) throw new Error(`HTTP ${response.status}`)
    iframeSrc.value = `/digital-twin/index.html?v=${Date.now()}`
  } catch (error) {
    loading.value = false
    const reason = error instanceof Error ? error.message : '未知错误'
    loadError.value = `无法读取同源资源 /digital-twin/index.html（${reason}）`
  }
}

function handleFrameLoad() {
  loading.value = false
}

onMounted(() => {
  fitScene()
  resizeObserver = new ResizeObserver(fitScene)
  if (pageRef.value) resizeObserver.observe(pageRef.value)
  void prepareFrame()
})

onBeforeUnmount(() => {
  resizeObserver?.disconnect()
  resizeObserver = null
})
</script>

<style scoped>
.digital-twin-page {
  position: relative;
  width: 100%;
  height: calc(100vh - 72px);
  height: calc(100dvh - 72px);
  min-height: 0;
  overflow: hidden;
  overscroll-behavior: contain;
  background: #02060d;
  box-sizing: border-box;
}

.digital-twin-viewport {
  position: absolute;
  inset: 0;
  display: grid;
  place-items: center;
  overflow: hidden;
}

.digital-twin-stage {
  position: relative;
  flex: 0 0 auto;
}

.digital-twin-frame {
  position: absolute;
  inset: 0 auto auto 0;
  display: block;
  max-width: none;
  border: 0;
  background: #02060d;
  transform-origin: top left;
}

.page-state {
  position: absolute;
  inset: 0;
  z-index: 2;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
  color: #ccecff;
  background: #02060d;
  font-size: 14px;
}

.page-error span {
  color: #85a7bb;
}

.page-error button {
  margin-top: 4px;
  min-height: 38px;
  padding: 0 16px;
  border: 1px solid #3e9dd5;
  border-radius: 4px;
  background: #0a3652;
  color: #ffffff;
  display: inline-flex;
  align-items: center;
  gap: 7px;
  font: inherit;
  font-weight: 700;
  cursor: pointer;
}

.spin {
  animation: spin 0.9s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

@media (max-width: 640px) {
  .digital-twin-page {
    height: calc(100vh - 88px);
    height: calc(100dvh - 88px);
  }
}
</style>

<style>
body:has(.digital-twin-page) {
  overflow: hidden;
}

#app:has(.digital-twin-page) {
  box-sizing: border-box;
}
</style>
