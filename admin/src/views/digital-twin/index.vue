<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue';

defineOptions({
  name: 'DigitalTwin'
});

const SCENE_WIDTH = 1920;
const SCENE_HEIGHT = 1080;

const pageRef = ref<HTMLElement | null>(null);
const viewportRef = ref<HTMLElement | null>(null);
const iframeSrc = ref('');
const loading = ref(true);
const loadError = ref('');
const sceneScale = ref(1);
let resizeObserver: ResizeObserver | null = null;

const stageStyle = computed(() => ({
  width: `${SCENE_WIDTH * sceneScale.value}px`,
  height: `${SCENE_HEIGHT * sceneScale.value}px`
}));

const frameStyle = computed(() => ({
  width: `${SCENE_WIDTH}px`,
  height: `${SCENE_HEIGHT}px`,
  transform: `scale(${sceneScale.value})`
}));

function sceneEntry() {
  if (!import.meta.env.DEV) return '/digital-twin/index.html';
  const host = window.location.hostname || '127.0.0.1';
  return `http://${host}:5088/digital-twin/index.html`;
}

function fitScene() {
  const viewport = viewportRef.value;
  if (!viewport?.clientWidth || !viewport?.clientHeight) return;
  sceneScale.value = Math.min(viewport.clientWidth / SCENE_WIDTH, viewport.clientHeight / SCENE_HEIGHT);
}

async function prepareFrame() {
  loading.value = true;
  loadError.value = '';
  iframeSrc.value = '';
  const entry = sceneEntry();
  try {
    const response = await fetch(entry, { cache: 'no-store', credentials: 'same-origin' });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    iframeSrc.value = `${entry}?v=${Date.now()}`;
  } catch (error) {
    loading.value = false;
    const reason = error instanceof Error ? error.message : '未知错误';
    loadError.value = `无法读取数字孪生场景（${reason}）`;
  }
}

function handleFrameLoad() {
  loading.value = false;
}

async function openFullscreen() {
  if (!pageRef.value?.requestFullscreen) return;
  await pageRef.value.requestFullscreen();
}

onMounted(() => {
  fitScene();
  resizeObserver = new ResizeObserver(fitScene);
  if (viewportRef.value) resizeObserver.observe(viewportRef.value);
  void prepareFrame();
});

onBeforeUnmount(() => {
  resizeObserver?.disconnect();
  resizeObserver = null;
});
</script>

<template>
  <main ref="pageRef" class="digital-twin-admin-page">
    <header class="scene-toolbar">
      <div>
        <span>智能体架构展示</span>
        <h1>数字孪生</h1>
      </div>
      <div class="scene-status">
        <i aria-hidden="true"></i>
        架构展示 · 非实时运行
      </div>
      <div class="scene-actions">
        <NButton secondary @click="prepareFrame">
          <template #icon><SvgIcon icon="lucide:refresh-cw" /></template>
          刷新场景
        </NButton>
        <NButton type="primary" @click="openFullscreen">
          <template #icon><SvgIcon icon="lucide:maximize-2" /></template>
          全屏查看
        </NButton>
      </div>
    </header>

    <section ref="viewportRef" class="digital-twin-viewport" aria-label="中药鉴别智能体数字孪生场景">
      <div v-if="iframeSrc" class="digital-twin-stage" :style="stageStyle">
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

      <div v-if="loading" class="page-state" role="status">
        <SvgIcon class="spin" icon="lucide:loader-circle" />
        <span>正在加载数字孪生场景...</span>
      </div>

      <div v-else-if="loadError" class="page-state page-error" role="alert">
        <SvgIcon icon="lucide:triangle-alert" />
        <strong>数字孪生资源加载失败</strong>
        <span>{{ loadError }}</span>
        <NButton type="primary" secondary @click="prepareFrame">重试</NButton>
      </div>
    </section>
  </main>
</template>

<style scoped>
.digital-twin-admin-page {
  height: calc(100vh - 132px);
  min-height: 580px;
  display: grid;
  grid-template-rows: 64px minmax(0, 1fr);
  overflow: hidden;
  border: 1px solid #dbe4e0;
  background: #02060d;
  color: #eef7f4;
}

.digital-twin-admin-page:fullscreen {
  width: 100vw;
  height: 100vh;
  min-height: 0;
}

.scene-toolbar {
  display: grid;
  grid-template-columns: minmax(220px, 1fr) auto minmax(220px, 1fr);
  align-items: center;
  gap: 18px;
  padding: 0 18px;
  border-bottom: 1px solid rgba(154, 188, 177, 0.2);
  background: #0b1715;
}

.scene-toolbar > div:first-child {
  min-width: 0;
}

.scene-toolbar span {
  display: block;
  color: #91aaa2;
  font-size: 10px;
  font-weight: 700;
}

.scene-toolbar h1 {
  margin: 2px 0 0;
  font-size: 18px;
  line-height: 1.2;
  letter-spacing: 0;
}

.scene-status {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  color: #b8ccc5;
  font-size: 12px;
  white-space: nowrap;
}

.scene-status i {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: #5bc69d;
  box-shadow: 0 0 0 4px rgba(91, 198, 157, 0.12);
}

.scene-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}

.digital-twin-viewport {
  position: relative;
  min-height: 0;
  display: grid;
  place-items: center;
  overflow: hidden;
  background: #02060d;
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
  gap: 11px;
  color: #ccecff;
  background: #02060d;
  font-size: 14px;
}

.page-state :deep(svg) {
  font-size: 28px;
}

.page-error span {
  color: #85a7bb;
}

.spin {
  animation: spin 0.9s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

@media (max-width: 900px) {
  .digital-twin-admin-page {
    height: calc(100vh - 116px);
    min-height: 520px;
    grid-template-rows: auto minmax(0, 1fr);
  }

  .scene-toolbar {
    grid-template-columns: minmax(0, 1fr) auto;
    min-height: 68px;
    padding: 8px 12px;
  }

  .scene-status {
    display: none;
  }

  .scene-actions {
    flex-wrap: wrap;
  }
}

@media (prefers-reduced-motion: reduce) {
  .spin { animation: none; }
}
</style>
