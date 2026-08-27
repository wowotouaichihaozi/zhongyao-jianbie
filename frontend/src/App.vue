<template>
  <div id="app" :class="{ 'xiaozhi-embed-app': isXiaoZhiEmbed || isFramedApp }">
    <TopNavbar v-if="showNavbar" />
    <RouterView v-slot="{ Component, route }">
      <component :is="Component" :key="route.fullPath" />
    </RouterView>
    <ResourceTaskStatusBanner v-if="showFloatingAssistant && route.query.xzTask" />
    <FloatingLogoLauncher v-if="showFloatingAssistant" />
    <GlobalDebugPanel v-if="showFloatingAssistant" />
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, watch } from 'vue'
import { RouterView, useRoute } from 'vue-router'
import FloatingLogoLauncher from './components/FloatingLogoLauncher.vue'
import GlobalDebugPanel from './components/GlobalDebugPanel.vue'
import ResourceTaskStatusBanner from './components/ResourceTaskStatusBanner.vue'
import TopNavbar from './components/TopNavbar.vue'
import { logXiaoZhiEvent, pulseLearningActivity } from './services/api.js'

const route = useRoute()
const isFramedApp = window.self !== window.top
const isXiaoZhiEmbed = computed(() => route.query.xzEmbed === '1' || route.query.embed === 'xiaozhi')

const routesWithoutNavbar = new Set([
  'login',
  'learning-profile-submit',
  'learning-profile-upload',
  'learning-profile-chat',
  'question-generator-exam-session',
  'digital-human-interview',
  'ppt-generating',
])

const showNavbar = computed(() => {
  if (isFramedApp) return false
  if (isXiaoZhiEmbed.value) return false
  if (route.meta?.noNavbar) return false
  if (routesWithoutNavbar.has(route.name)) return false
  if (route.name === 'mcu-simulator' && route.params.board) return false
  return true
})

const routesWithoutFloatingAssistant = new Set([
  'login',
  'agent-digital-twin',
  'knowledge-network',
  'life-tree',
  'ai-coding',
  'herb-recognition',
  'personalized-resource-video-generator',
  'personalized-resource-herb-model',
])

const showFloatingAssistant = computed(() => {
  if (isFramedApp) return false
  if (isXiaoZhiEmbed.value) return false
  if (routesWithoutFloatingAssistant.has(route.name)) return false
  if (route.path.startsWith('/admin')) return false
  return true
})

let activitySessionId = ''
let activityRoute = ''
let activityRouteName = ''
let activityTimer = 0

function createActivitySessionId() {
  if (globalThis.crypto?.randomUUID) {
    return `web_${globalThis.crypto.randomUUID().replaceAll('-', '')}`
  }
  return `web_${Date.now()}_${Math.random().toString(36).slice(2, 12)}`
}

function clearActivityTimer() {
  if (activityTimer) window.clearInterval(activityTimer)
  activityTimer = 0
}

function sendActivityPulse(action, keepalive = false) {
  if (!activitySessionId) return Promise.resolve()
  return pulseLearningActivity({
    sessionId: activitySessionId,
    action,
    route: activityRoute,
    routeName: activityRouteName,
  }, { keepalive }).catch(() => {})
}

function stopLearningActivity(keepalive = false) {
  clearActivityTimer()
  if (!activitySessionId) return
  const endingSessionId = activitySessionId
  const endingRoute = activityRoute
  const endingRouteName = activityRouteName
  activitySessionId = ''
  activityRoute = ''
  activityRouteName = ''
  pulseLearningActivity({
    sessionId: endingSessionId,
    action: 'end',
    route: endingRoute,
    routeName: endingRouteName,
  }, { keepalive }).catch(() => {})
}

function startLearningActivity() {
  if (!showFloatingAssistant.value || document.hidden || activitySessionId) return
  activitySessionId = createActivitySessionId()
  activityRoute = route.fullPath
  activityRouteName = String(route.name || '')
  void sendActivityPulse('start')
  activityTimer = window.setInterval(() => {
    if (!document.hidden) void sendActivityPulse('heartbeat')
  }, 15000)
}

function handleVisibilityChange() {
  if (document.hidden) stopLearningActivity(true)
  else startLearningActivity()
}

function handlePageHide() {
  stopLearningActivity(true)
}

watch(
  () => route.fullPath,
  (path) => {
    stopLearningActivity()
    if (!showFloatingAssistant.value) return
    logXiaoZhiEvent({
      eventType: 'page_view',
      route: path,
      title: document.title || '',
      payload: {
        name: route.name || '',
        params: route.params || {},
        query: route.query || {},
      },
    }).catch(() => {})
    startLearningActivity()
  },
  { immediate: true },
)

onMounted(() => {
  document.addEventListener('visibilitychange', handleVisibilityChange)
  window.addEventListener('pagehide', handlePageHide)
  startLearningActivity()
})

onBeforeUnmount(() => {
  document.removeEventListener('visibilitychange', handleVisibilityChange)
  window.removeEventListener('pagehide', handlePageHide)
  stopLearningActivity(true)
})
</script>

<style>
@media (max-width: 768px) and (orientation: portrait) {
  #app:not(.xiaozhi-embed-app) {
    min-height: 100vh;
    padding-bottom: 88px;
    box-sizing: border-box;
  }
}

#app.xiaozhi-embed-app {
  min-height: 100vh;
  padding-bottom: 0;
}

#app:has(.mcu-app) .xiaozhi-float {
  right: 20px !important;
  bottom: 20px !important;
  left: auto !important;
  top: auto !important;
}

#app:has(.mcu-app) .xiaozhi-window {
  right: 84px !important;
  bottom: 0 !important;
  left: auto !important;
  top: auto !important;
}

@media (max-width: 768px) and (orientation: portrait) {
  #app:has(.mcu-app) .xiaozhi-float {
    display: none;
  }
}
</style>
