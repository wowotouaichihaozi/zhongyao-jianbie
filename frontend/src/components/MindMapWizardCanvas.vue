<template>
  <section ref="shell" class="mindmap-wizard-shell" :class="{ fullscreen: isFullscreen }">
    <header class="mindmap-toolbar">
      <span class="engine-label">
        <Network :size="16" stroke-width="2.2" aria-hidden="true" />
        <span>交互式导图</span>
      </span>
      <div class="mindmap-controls" role="toolbar" aria-label="思维导图工具栏">
        <button type="button" title="缩小" aria-label="缩小" :disabled="!ready" @click="control('zoom-out')">
          <ZoomOut :size="18" aria-hidden="true" />
        </button>
        <button type="button" title="放大" aria-label="放大" :disabled="!ready" @click="control('zoom-in')">
          <ZoomIn :size="18" aria-hidden="true" />
        </button>
        <button type="button" title="适应屏幕" aria-label="适应屏幕" :disabled="!ready" @click="control('fit')">
          <Scan :size="18" aria-hidden="true" />
        </button>
        <button type="button" title="下载 SVG" aria-label="下载 SVG" :disabled="!rendered" @click="control('export')">
          <Download :size="18" aria-hidden="true" />
        </button>
        <button type="button" :title="isFullscreen ? '退出全屏' : '全屏'" :aria-label="isFullscreen ? '退出全屏' : '全屏'" @click="toggleFullscreen">
          <Minimize2 v-if="isFullscreen" :size="18" aria-hidden="true" />
          <Maximize2 v-else :size="18" aria-hidden="true" />
        </button>
      </div>
    </header>

    <div class="mindmap-viewport">
      <iframe
        ref="frame"
        class="mindmap-frame"
        src="/mind-map-wizard/embedded/index.html"
        :title="`${title || '学习'}思维导图`"
      ></iframe>
      <div v-if="!ready && !error" class="mindmap-overlay" role="status">
        <LoaderCircle :size="24" class="spin" aria-hidden="true" />
        <span>正在加载导图引擎</span>
      </div>
      <div v-else-if="error" class="mindmap-overlay error" role="alert">
        <CircleAlert :size="24" aria-hidden="true" />
        <strong>导图渲染失败</strong>
        <span>{{ error }}</span>
        <button type="button" @click="reloadFrame">重试</button>
      </div>
    </div>
  </section>
</template>

<script setup>
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'
import {
  CircleAlert,
  Download,
  LoaderCircle,
  Maximize2,
  Minimize2,
  Network,
  Scan,
  ZoomIn,
  ZoomOut,
} from 'lucide-vue-next'

const props = defineProps({
  content: { type: String, required: true },
  title: { type: String, default: '思维导图' },
})

const MESSAGE_SCOPE = 'xz-mindmap-wizard'
const frame = ref(null)
const shell = ref(null)
const ready = ref(false)
const rendered = ref(false)
const error = ref('')
const isFullscreen = ref(false)
const fallbackFullscreen = ref(false)
let previousBodyOverflow = ''
let bodyOverflowLocked = false

watch(() => [props.content, props.title], () => {
  if (ready.value) render()
})

onMounted(() => {
  window.addEventListener('message', handleMessage)
  document.addEventListener('fullscreenchange', handleFullscreenChange)
})

onBeforeUnmount(() => {
  window.removeEventListener('message', handleMessage)
  document.removeEventListener('fullscreenchange', handleFullscreenChange)
  restoreBodyOverflow()
})

function handleMessage(event) {
  if (event.origin !== window.location.origin || event.source !== frame.value?.contentWindow) return
  const message = event.data || {}
  if (message.scope !== MESSAGE_SCOPE) return
  if (message.type === 'ready') {
    ready.value = true
    error.value = ''
    render()
  } else if (message.type === 'rendered') {
    rendered.value = Number(message.nodeCount || 0) > 0
    error.value = ''
  } else if (message.type === 'error') {
    rendered.value = false
    error.value = String(message.message || '思维导图渲染失败')
  } else if (message.type === 'export') {
    downloadSvg(message.content, message.filename)
  }
}

function post(message) {
  frame.value?.contentWindow?.postMessage({ scope: MESSAGE_SCOPE, ...message }, window.location.origin)
}

function render() {
  rendered.value = false
  error.value = ''
  post({ type: 'render', content: props.content, title: props.title })
}

function control(action) {
  post({ type: 'control', action })
}

function reloadFrame() {
  ready.value = false
  rendered.value = false
  error.value = ''
  frame.value?.contentWindow?.location.reload()
}

async function toggleFullscreen() {
  if (!shell.value) return
  if (fallbackFullscreen.value) {
    fallbackFullscreen.value = false
    isFullscreen.value = false
    restoreBodyOverflow()
    window.setTimeout(() => control('fit'), 120)
    return
  }
  if (document.fullscreenElement === shell.value) {
    await document.exitFullscreen()
  } else {
    try {
      await shell.value.requestFullscreen()
    } catch {
      previousBodyOverflow = document.body.style.overflow
      document.body.style.overflow = 'hidden'
      bodyOverflowLocked = true
      fallbackFullscreen.value = true
      isFullscreen.value = true
      window.setTimeout(() => control('fit'), 120)
    }
  }
}

function handleFullscreenChange() {
  if (!fallbackFullscreen.value) isFullscreen.value = document.fullscreenElement === shell.value
  if (isFullscreen.value) window.setTimeout(() => control('fit'), 120)
}

function restoreBodyOverflow() {
  if (!bodyOverflowLocked) return
  document.body.style.overflow = previousBodyOverflow
  previousBodyOverflow = ''
  bodyOverflowLocked = false
}

function downloadSvg(content, filename) {
  if (!content) return
  const blob = new Blob([content], { type: 'image/svg+xml;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const anchor = document.createElement('a')
  anchor.href = url
  anchor.download = String(filename || `${props.title || '思维导图'}.svg`).replace(/[\\/:*?"<>|]/g, '-')
  document.body.appendChild(anchor)
  anchor.click()
  anchor.remove()
  URL.revokeObjectURL(url)
}
</script>

<style scoped>
.mindmap-wizard-shell {
  min-height: 620px;
  display: grid;
  grid-template-rows: 48px minmax(0, 1fr);
  overflow: hidden;
  border: 1px solid #d6e5de;
  border-radius: 8px;
  background: #f8fbf9;
  box-shadow: 0 14px 38px rgba(34, 71, 59, 0.08);
}

.mindmap-wizard-shell:fullscreen,
.mindmap-wizard-shell.fullscreen {
  width: 100vw;
  height: 100vh;
  min-height: 100vh;
  border: 0;
  border-radius: 0;
}

.mindmap-wizard-shell.fullscreen {
  position: fixed;
  inset: 0;
  z-index: 5000;
}

.mindmap-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 0 10px 0 16px;
  border-bottom: 1px solid #dbe8e2;
  background: #fff;
}

.engine-label {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  color: #31574b;
  font-size: 13px;
  font-weight: 750;
}

.engine-label svg { color: #0e9f6e; }

.mindmap-controls {
  display: flex;
  align-items: center;
  gap: 4px;
}

.mindmap-controls button {
  width: 34px;
  height: 34px;
  display: grid;
  place-items: center;
  padding: 0;
  border: 0;
  border-radius: 6px;
  background: transparent;
  color: #42645a;
  cursor: pointer;
}

.mindmap-controls button:hover:not(:disabled) {
  background: #eaf6f0;
  color: #087b55;
}

.mindmap-controls button:disabled {
  opacity: 0.35;
  cursor: not-allowed;
}

.mindmap-viewport {
  position: relative;
  min-height: 570px;
  overflow: hidden;
}

.mindmap-frame {
  display: block;
  width: 100%;
  height: 100%;
  min-height: 570px;
  border: 0;
  background: #f8fbf9;
}

.mindmap-overlay {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 10px;
  padding: 24px;
  background: rgba(248, 251, 249, 0.94);
  color: #587168;
  font-size: 13px;
  text-align: center;
}

.mindmap-overlay.error { color: #a83e37; }
.mindmap-overlay.error strong { font-size: 16px; }

.mindmap-overlay.error button {
  min-height: 36px;
  margin-top: 4px;
  padding: 0 16px;
  border: 0;
  border-radius: 6px;
  background: #0e9f6e;
  color: #fff;
  font-weight: 700;
  cursor: pointer;
}

.spin { animation: mindmap-spin 900ms linear infinite; }
@keyframes mindmap-spin { to { transform: rotate(360deg); } }

@media (max-width: 640px) {
  .mindmap-wizard-shell { min-height: 520px; }
  .mindmap-viewport,
  .mindmap-frame { min-height: 472px; }
  .engine-label > span { display: none; }
}

@media (prefers-reduced-motion: reduce) {
  .spin { animation: none; }
}
</style>
