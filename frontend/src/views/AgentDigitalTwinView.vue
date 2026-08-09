<template>
  <main class="digital-twin-page">
    <iframe
      v-if="iframeSrc"
      :key="iframeSrc"
      class="digital-twin-frame"
      :src="iframeSrc"
      title="嵌智学航智能体数字孪生架构展示"
      allow="fullscreen"
      @load="handleFrameLoad"
    />

    <div v-if="loading" class="page-state" role="status">
      <LoaderCircle class="spin" :size="28" />
      <span>正在加载数字孪生场景...</span>
    </div>

    <div v-else-if="loadError" class="page-state page-error" role="alert">
      <TriangleAlert :size="30" />
      <strong>数字孪生资源加载失败</strong>
      <span>{{ loadError }}</span>
      <button type="button" @click="prepareFrame">重试</button>
    </div>
  </main>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { LoaderCircle, TriangleAlert } from 'lucide-vue-next'

const iframeSrc = ref('')
const loading = ref(true)
const loadError = ref('')

async function prepareFrame() {
  loading.value = true
  loadError.value = ''
  iframeSrc.value = ''
  try {
    const response = await fetch('/digital-twin/index.html', { cache: 'no-store' })
    if (!response.ok) throw new Error(`HTTP ${response.status}`)
    iframeSrc.value = `/digital-twin/index.html?v=${Date.now()}`
  } catch (error) {
    loading.value = false
    loadError.value = error instanceof Error ? error.message : '无法读取同源静态资源'
  }
}

function handleFrameLoad() {
  loading.value = false
}

onMounted(() => {
  void prepareFrame()
})
</script>

<style scoped>
.digital-twin-page {
  position: relative;
  width: 100%;
  height: calc(100vh - 72px);
  min-height: 560px;
  overflow: auto;
  overscroll-behavior: contain;
  background: #02060d;
  scrollbar-color: #17628a #02060d;
  scrollbar-width: thin;
}

.digital-twin-frame {
  display: block;
  width: 1920px;
  height: 1080px;
  max-width: none;
  margin: 0 auto;
  border: 0;
  background: #02060d;
}

.digital-twin-page::-webkit-scrollbar {
  width: 9px;
  height: 9px;
}

.digital-twin-page::-webkit-scrollbar-track {
  background: #02060d;
}

.digital-twin-page::-webkit-scrollbar-thumb {
  border: 2px solid #02060d;
  border-radius: 5px;
  background: #17628a;
}

.digital-twin-page::-webkit-scrollbar-thumb:hover {
  background: #2185b7;
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
  padding: 8px 18px;
  border: 1px solid #3e9dd5;
  border-radius: 4px;
  background: #0a3652;
  color: #ffffff;
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
    min-height: 480px;
  }
}
</style>
