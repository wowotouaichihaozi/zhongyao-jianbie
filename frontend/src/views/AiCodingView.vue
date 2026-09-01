<template>
  <main class="ai-coding-page">
    <section class="workspace-body">
      <iframe
        v-if="runtimeReady"
        :key="frameKey"
        class="runtime-frame"
        src="/ai-coding-runtime/"
        title="DeepSeek Harness AI 编程工作区"
        allow="microphone; clipboard-read; clipboard-write"
        @load="handleFrameLoad"
      />

      <div v-if="loading" class="workspace-state" role="status" aria-live="polite">
        <LoaderCircle class="spin" :size="30" aria-hidden="true" />
        <strong>正在连接 AI 编程工作区</strong>
        <span>共享会话与文件正在加载...</span>
      </div>

      <div v-else-if="loadError" class="workspace-state workspace-error" role="alert">
        <TriangleAlert :size="30" aria-hidden="true" />
        <strong>AI 编程工作区暂时无法连接</strong>
        <span>{{ loadError }}</span>
        <button type="button" @click="prepareRuntime">
          <RefreshCw :size="16" aria-hidden="true" />
          重试连接
        </button>
      </div>
    </section>
  </main>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { LoaderCircle, RefreshCw, TriangleAlert } from 'lucide-vue-next'

const runtimeReady = ref(false)
const loading = ref(true)
const loadError = ref('')
const frameKey = ref(0)
let loadTimer = 0

function clearLoadTimer() {
  if (loadTimer) window.clearTimeout(loadTimer)
  loadTimer = 0
}

async function prepareRuntime() {
  clearLoadTimer()
  runtimeReady.value = false
  loading.value = true
  loadError.value = ''

  try {
    const response = await fetch('/ai-coding-runtime/', {
      method: 'GET',
      cache: 'no-store',
      credentials: 'same-origin',
      headers: { Accept: 'text/html' },
    })
    if (!response.ok) throw new Error(`服务返回 HTTP ${response.status}`)

    const html = await response.text()
    const isPlatformFallback = html.includes('<title>嵌智学航</title>')
      || html.includes('src="/src/main.js"')
    if (isPlatformFallback) {
      throw new Error('AI 编程运行时尚未启动或反向代理未配置')
    }

    frameKey.value += 1
    runtimeReady.value = true
    loadTimer = window.setTimeout(() => {
      loading.value = false
      runtimeReady.value = false
      loadError.value = '工作区页面加载超时，请稍后重试。'
    }, 20000)
  } catch (error) {
    loading.value = false
    const reason = error instanceof Error ? error.message : '未知错误'
    loadError.value = `${reason}。`
  }
}

function handleFrameLoad() {
  clearLoadTimer()
  loading.value = false
}

onMounted(() => {
  void prepareRuntime()
})
</script>

<style scoped>
.ai-coding-page {
  height: calc(100vh - 72px);
  height: calc(100dvh - 72px);
  min-height: 0;
  overflow: hidden;
}

.workspace-body {
  position: relative;
  height: 100%;
  min-height: 0;
  overflow: hidden;
  background: #ffffff;
}

.runtime-frame {
  display: block;
  width: 100%;
  height: 100%;
  border: 0;
  background: #ffffff;
}

.workspace-state {
  position: absolute;
  inset: 0;
  z-index: 2;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 10px;
  padding: 24px;
  background: #f7f9fa;
  color: #253135;
  text-align: center;
  box-sizing: border-box;
}

.workspace-state strong {
  font-size: 15px;
}

.workspace-state span {
  color: #697579;
  font-size: 13px;
}

.workspace-error svg {
  color: #b45309;
}

.workspace-error button {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  min-height: 38px;
  margin-top: 4px;
  padding: 0 14px;
  border: 1px solid #b9c3c7;
  border-radius: 4px;
  background: #ffffff;
  color: #20292c;
  font: inherit;
  font-size: 13px;
  font-weight: 700;
  cursor: pointer;
}

.workspace-error button:hover {
  border-color: #2563eb;
  color: #1d4ed8;
}

.spin {
  color: #2563eb;
  animation: spin 0.9s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

@media (max-width: 768px) and (orientation: portrait) {
  .ai-coding-page {
    height: calc(100vh - 88px);
    height: calc(100dvh - 88px);
  }

}
</style>

<style>
body:has(.ai-coding-page) {
  overflow: hidden;
}
</style>
