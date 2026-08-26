<template>
  <div class="ppt-native-page" :class="{ standalone: isResourceToolPage }">
    <button v-if="isResourceToolPage" type="button" class="resource-back-button" @click="goBackToResources">
      <ArrowLeft :size="18" :stroke-width="2.2" aria-hidden="true" />
      <span>返回个性化资源</span>
    </button>

    <header class="ppt-header">
      <div>
        <div class="ppt-kicker">
          <Sparkles :size="16" aria-hidden="true" />
          <span>岐黄智境 PPT</span>
        </div>
        <h1>快速创建演示文稿</h1>
      </div>
      <div class="ppt-header-metrics" aria-label="PPT 会话概览">
        <div class="metric">
          <strong>{{ sessions.length }}</strong>
          <span>历史会话</span>
        </div>
        <div class="metric">
          <strong>{{ latestPageCount }}</strong>
          <span>最近页数</span>
        </div>
      </div>
    </header>

    <main class="ppt-workspace">
      <nav class="ppt-tabs" aria-label="PPT 功能">
        <button
          type="button"
          :class="{ active: activeTab === 'quick' }"
          :aria-pressed="activeTab === 'quick'"
          aria-controls="ppt-quick-create"
          :title="activeTab === 'quick' && form.topic.trim() ? '使用当前设置生成 PPT' : '打开快速创建表单'"
          @click="activateQuickCreate"
        >
          <Play :size="17" aria-hidden="true" />
          <span>快速创建</span>
        </button>
        <button
          type="button"
          :class="{ active: activeTab === 'history' }"
          :aria-pressed="activeTab === 'history'"
          aria-controls="ppt-history"
          @click="activateHistory"
        >
          <History :size="17" aria-hidden="true" />
          <span>历史会话</span>
        </button>
      </nav>

      <section class="content-grid" :class="{ 'history-mode': activeTab === 'history' }">
        <form v-if="activeTab === 'quick'" id="ppt-quick-create" class="tool-panel creator-tool" @submit.prevent="submitQuickCreate">
          <div class="panel-title">
            <FileText :size="20" aria-hidden="true" />
            <h2>快速创建</h2>
          </div>

          <label class="field">
            <span>主题</span>
            <input ref="topicInputRef" v-model.trim="form.topic" type="text" placeholder="例如：八纲辨证与典型医案" maxlength="80" autofocus />
          </label>

          <label class="field">
            <span>页数</span>
            <input v-model.number="form.pageCount" type="number" min="1" max="12" step="1" @blur="normalizePageCount" />
          </label>

          <label class="field">
            <span>补充要求</span>
            <textarea
              v-model.trim="form.userMessage"
              rows="7"
              placeholder="可填写课程对象、章节重点、汇报场景或内容侧重点"
              maxlength="600"
            />
          </label>

          <div class="creator-actions">
            <button type="submit" class="primary-action" :disabled="!canGenerate">
              <Loader2 v-if="generating" :size="18" class="spin-icon" aria-hidden="true" />
              <Sparkles v-else :size="18" aria-hidden="true" />
              <span>{{ generating ? '生成中' : '生成 PPT' }}</span>
            </button>
            <button type="button" class="secondary-action" :disabled="generating" @click="resetForm">
              <RotateCcw :size="17" aria-hidden="true" />
              <span>重置</span>
            </button>
          </div>
        </form>

        <section v-else id="ppt-history" class="tool-panel history-tool">
          <div class="panel-title history-title">
            <History :size="20" aria-hidden="true" />
            <h2>历史会话</h2>
            <button v-if="sessions.length" type="button" class="ghost-action" :disabled="historyLoading" @click="refreshPersistedHistory">
              <RotateCcw :size="16" :class="{ 'spin-icon': historyLoading }" aria-hidden="true" />
              <span>刷新</span>
            </button>
          </div>

          <div v-if="sortedSessions.length" class="history-list">
            <button
              v-for="session in sortedSessions"
              :key="session.id"
              type="button"
              class="session-row"
              :class="{ active: currentSession?.id === session.id }"
              @click="selectSession(session)"
            >
              <span class="session-icon">
                <FileText :size="18" aria-hidden="true" />
              </span>
              <span class="session-main">
                <strong>{{ session.title || session.topic }}</strong>
                <small>{{ formatDate(session.updatedAt || session.createdAt) }}</small>
              </span>
              <span class="session-meta">{{ sessionStatusText(session) }} · {{ getSessionPageCount(session) }} 页</span>
            </button>
          </div>

          <div v-else class="empty-state compact">
            <Clock :size="28" aria-hidden="true" />
            <strong>暂无历史会话</strong>
          </div>
        </section>

        <section class="tool-panel preview-tool">
          <div class="preview-head">
            <div>
              <div class="preview-status">
                <Layers :size="16" aria-hidden="true" />
                <span>{{ previewStatus }}</span>
              </div>
              <h2>{{ previewTitle }}</h2>
            </div>
            <div v-if="pages.length" class="page-actions">
              <button type="button" :disabled="exporting" title="导出为独立 H5 文件" @click="exportPptFile">
                <Download :size="18" aria-hidden="true" />
                <span>{{ exporting ? '导出中' : '导出文件' }}</span>
              </button>
              <button type="button" :title="isPreviewFullscreen ? '退出全屏' : '全屏展示'" @click="togglePreviewFullscreen">
                <Minimize2 v-if="isPreviewFullscreen" :size="18" aria-hidden="true" />
                <Maximize2 v-else :size="18" aria-hidden="true" />
                <span>{{ isPreviewFullscreen ? '退出全屏' : '全屏展示' }}</span>
              </button>
              <button type="button" :disabled="activePageIndex === 0" @click="goPage(-1)">
                <ChevronLeft :size="18" aria-hidden="true" />
                <span>上一页</span>
              </button>
              <button type="button" :disabled="activePageIndex >= pages.length - 1" @click="goPage(1)">
                <span>下一页</span>
                <ChevronRight :size="18" aria-hidden="true" />
              </button>
            </div>
          </div>

          <div
            ref="previewStageRef"
            class="preview-stage"
            :class="{ 'fallback-fullscreen': isPreviewFullscreenFallback }"
            tabindex="-1"
            @wheel="handlePreviewWheel"
          >
            <div
              v-if="isCurrentGenerating"
              class="generation-panel"
              :class="{ 'without-agents': !generationAgentRuns.length }"
            >
              <div class="generation-hero">
                <div class="generation-badge">
                  <Loader2 :size="16" class="spin-icon" aria-hidden="true" />
                  <span>生成中</span>
                </div>
                <strong>{{ generationStageLabel }}</strong>
                <p>{{ generationMessage }}</p>
              </div>

              <div class="generation-progress" aria-label="PPT 生成进度">
                <span :style="{ width: `${generationProgress}%` }"></span>
              </div>
              <div class="generation-meta">
                <span>{{ generationProgress }}%</span>
                <span>{{ generationPageCount }} 页课件</span>
              </div>

              <div v-if="generationAgentRuns.length" class="generation-agents">
                <article
                  v-for="agent in generationAgentRuns"
                  :key="agent.name"
                  class="generation-agent"
                  :class="agentStatusClass(agent.status)"
                >
                  <span class="agent-dot"></span>
                  <div>
                    <strong>{{ agent.name }}</strong>
                    <small>{{ agent.detail || agentStatusText(agent.status) }}</small>
                  </div>
                </article>
              </div>

              <div v-if="generationLogs.length" class="generation-log">
                <header>
                  <span>实时过程</span>
                  <small>{{ generationLogs.length }} 条</small>
                </header>
                <ol>
                  <li v-for="log in generationLogs" :key="`${log.time || ''}-${log.stage || ''}-${log.message || ''}`">
                    <time>{{ formatLogTime(log.time) }}</time>
                    <span>{{ log.message || stageLabel(log.stage) }}</span>
                  </li>
                </ol>
              </div>
            </div>
            <div v-else-if="currentSession?.status === 'error'" class="empty-state error">
              <FileText :size="34" aria-hidden="true" />
              <strong>生成失败</strong>
              <span>{{ currentSession.error || '请稍后重试' }}</span>
            </div>
            <div v-else-if="activePage?.html" class="preview-frame-shell">
              <iframe
                class="preview-frame"
                title="PPT 页面预览"
                sandbox="allow-scripts"
                :srcdoc="previewSrcdoc"
                :style="previewFrameStyle"
              />
            </div>
            <div v-else class="empty-state">
              <FileText :size="34" aria-hidden="true" />
              <strong>等待创建</strong>
              <span>生成后的页面会显示在这里。</span>
            </div>
            <button
              v-if="isPreviewFullscreen && pages.length"
              type="button"
              class="fullscreen-hit-zone prev"
              aria-label="上一页"
              :disabled="activePageIndex === 0"
              @click.stop="goPage(-1)"
            />
            <button
              v-if="isPreviewFullscreen && pages.length"
              type="button"
              class="fullscreen-hit-zone next"
              aria-label="下一页"
              :disabled="activePageIndex >= pages.length - 1"
              @click.stop="goPage(1)"
            />
          </div>

          <div v-if="pages.length" class="slide-strip" aria-label="页面列表" @wheel="handleSlideStripWheel">
            <button
              v-for="(page, index) in pages"
              :key="page.pageNumber || index"
              type="button"
              class="slide-chip"
              :class="{ active: activePageIndex === index }"
              @click="activePageIndex = index"
            >
              <span>{{ index + 1 }}</span>
              <small>{{ page.title || `第 ${index + 1} 页` }}</small>
            </button>
          </div>
        </section>
      </section>
    </main>
  </div>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  ArrowLeft,
  ChevronLeft,
  ChevronRight,
  Clock,
  Download,
  FileText,
  History,
  Layers,
  Loader2,
  Maximize2,
  Minimize2,
  Play,
  RotateCcw,
  Sparkles,
} from 'lucide-vue-next'
import { getPptTaskHistory, getXiaoZhiTask, startPptH5Generation } from '../services/api.js'
import {
  getNodeCache,
  hydrateNodeCachesFromServer,
  markNodeCacheComplete,
  markNodeCacheError,
  markNodeCacheStarted,
  setNodeCache,
} from '../services/learningPathNodeCache.js'

const STORAGE_KEY = 'qianzhi-ppt-sessions:v1'
const MAX_HISTORY = 12
const GENERATION_STAGE_LABELS = {
  start: '任务启动',
  prepare: '整理课件需求',
  model_config: '读取模型配置',
  prompt_ready: '构建生成提示词',
  llm_request: '大模型生成内容',
  llm_retry: '模型请求重试',
  llm_response: '解析模型输出',
  parse_success: '内容结构解析完成',
  parse_retry: '重新解析结构',
  ohmyppt_health: '连接 OhMyPPT',
  ohmyppt_request: 'OhMyPPT 生成页面',
  ohmyppt_validate: '页面结构与安全校验',
  ohmyppt_complete: 'OhMyPPT 生成完成',
  rendering: '渲染 H5 幻灯片',
  render_page: '写入幻灯片页面',
  render_fallback_page: '模板补齐页面',
  assemble: '组装预览数据',
  complete: '生成完成',
  error: '生成异常',
}
const PLATFORM_STYLE_SKILL = [
  '使用岐黄智境平台同款画风。',
  '白底或极浅薄荷绿背景，深灰文字，绿色 #21B978 / #58D89C 作为强调色。',
  '模块化分区、充足留白、轻量卡片、清晰教育科技感。',
  '避免深色主题、蓝紫主色、高饱和颜色和复杂动效。',
].join('\n')

const route = useRoute()
const router = useRouter()

const activeTab = ref(route.query.tab === 'history' ? 'history' : 'quick')
const sessions = ref(loadSessions())
const currentSessionId = ref('')
const activePageIndex = ref(0)
const generatingSessionId = ref('')
const xiaozhiTaskId = ref('')
const topicInputRef = ref(null)
const previewStageRef = ref(null)
const previewScale = ref(1)
const isPreviewFullscreen = ref(false)
const isPreviewFullscreenFallback = ref(false)
const exporting = ref(false)
const historyLoading = ref(false)
let xiaozhiTaskTimer = null
let previewResizeObserver = null
let previewWheelDelta = 0
let previewWheelLastTurnAt = 0
const readyGenerationSessions = new Set()

const form = reactive({
  topic: '',
  pageCount: 6,
  userMessage: '',
})

const isResourceToolPage = computed(() => route.meta?.resourceTool === true || route.path.startsWith('/personalized-resources/'))
const generating = computed(() => Boolean(generatingSessionId.value))
const canGenerate = computed(() => Boolean(form.topic.trim()) && !generating.value)
const sortedSessions = computed(() => [...sessions.value].sort((a, b) => Number(b.updatedAt || 0) - Number(a.updatedAt || 0)))
const currentSession = computed(() => {
  if (!currentSessionId.value) return null
  return sessions.value.find((session) => session.id === currentSessionId.value) || null
})
const pages = computed(() => (Array.isArray(currentSession.value?.pages) ? currentSession.value.pages : []))
const activePage = computed(() => pages.value[Math.min(activePageIndex.value, Math.max(pages.value.length - 1, 0))] || null)
const previewSrcdoc = computed(() => fitSlideHtml(activePage.value?.html || ''))
const previewFrameStyle = computed(() => ({
  transform: `translate(-50%, -50%) scale(${previewScale.value})`,
}))
const isCurrentGenerating = computed(() => Boolean(currentSession.value?.id && currentSession.value.id === generatingSessionId.value))
const previewTitle = computed(() => currentSession.value?.title || currentSession.value?.topic || 'PPT 预览')
const latestPageCount = computed(() => getSessionPageCount(sortedSessions.value[0]) || form.pageCount)
const generationState = computed(() => currentSession.value?.generation || {})
const generationProgress = computed(() => clampProgress(generationState.value.progress ?? (isCurrentGenerating.value ? 5 : 0)))
const generationMessage = computed(() => {
  const message = String(generationState.value.message || '').trim()
  if (message) return message
  return isCurrentGenerating.value ? '正在启动 PPT 生成任务' : '等待任务更新'
})
const generationStageLabel = computed(() => stageLabel(generationState.value.currentStage || generationState.value.stage))
const generationLogs = computed(() => {
  const logs = Array.isArray(generationState.value.logs) ? generationState.value.logs : []
  return logs.slice(-6).reverse()
})
const generationAgentRuns = computed(() => (Array.isArray(generationState.value.agentRuns) ? generationState.value.agentRuns : []))
const generationPageCount = computed(() => Number(generationState.value.pageCount || currentSession.value?.pageCount || form.pageCount || 0))
const previewStatus = computed(() => {
  if (isCurrentGenerating.value) return '生成中'
  if (currentSession.value?.status === 'error') return '生成失败'
  if (pages.value.length) return `${activePageIndex.value + 1} / ${pages.value.length}`
  return '未生成'
})

watch(
  () => [route.query.session, route.query.tab],
  () => syncRouteSession(),
  { immediate: true },
)

watch(
  () => route.query.xzTask,
  (taskId) => {
    syncXiaoZhiTask(String(taskId || ''))
  },
  { immediate: true },
)

watch(
  () => pages.value.length,
  (length) => {
    if (!length) {
      activePageIndex.value = 0
      nextTick(updatePreviewScale)
      return
    }
    if (activePageIndex.value > length - 1) {
      activePageIndex.value = length - 1
    }
    nextTick(updatePreviewScale)
  },
)

watch(
  () => [activePage.value?.html, isPreviewFullscreen.value],
  () => nextTick(updatePreviewScale),
)

onMounted(async () => {
  document.addEventListener('fullscreenchange', handleFullscreenChange)
  document.addEventListener('keydown', handleFullscreenKeydown)
  window.addEventListener('message', handleGenerationWindowReady)
  if (typeof ResizeObserver !== 'undefined') {
    previewResizeObserver = new ResizeObserver(updatePreviewScale)
    nextTick(() => {
      if (previewStageRef.value) {
        previewResizeObserver.observe(previewStageRef.value)
      }
      updatePreviewScale()
    })
  } else {
    window.addEventListener('resize', updatePreviewScale)
    nextTick(updatePreviewScale)
  }
  applyRoutePrefill()
  await refreshPersistedHistory()
  syncRouteSession()
  await hydrateNodeCachesFromServer()
  const restoredFromCache = restoreLearningNodeSession()
  const restoredFromTask = restoredFromCache ? false : await restoreLearningNodeTaskFromCache()
  if (!restoredFromCache && !restoredFromTask && route.query.autostart === '1') {
    nextTick(() => {
      submitQuickCreate()
    })
  }
})

onBeforeUnmount(() => {
  stopXiaoZhiTaskPolling()
  closePreviewFallbackFullscreen()
  previewResizeObserver?.disconnect?.()
  previewResizeObserver = null
  window.removeEventListener('resize', updatePreviewScale)
  window.removeEventListener('message', handleGenerationWindowReady)
  document.removeEventListener('fullscreenchange', handleFullscreenChange)
  document.removeEventListener('keydown', handleFullscreenKeydown)
})

function goBackToResources() {
  router.push('/personalized-resources')
}

async function activateQuickCreate() {
  if (activeTab.value === 'quick' && form.topic.trim() && !generating.value) {
    await submitQuickCreate()
    return
  }
  activeTab.value = 'quick'
  const query = { ...route.query }
  delete query.tab
  delete query.session
  await router.replace({ query }).catch(() => {})
  await nextTick()
  topicInputRef.value?.focus?.({ preventScroll: true })
}

function activateHistory() {
  activeTab.value = 'history'
  router.replace({ query: { ...route.query, tab: 'history' } }).catch(() => {})
}

async function togglePreviewFullscreen() {
  const stage = previewStageRef.value
  if (!stage) return
  if (document.fullscreenElement === stage || isPreviewFullscreenFallback.value) {
    if (isPreviewFullscreenFallback.value) {
      closePreviewFallbackFullscreen()
      return
    }
    await document.exitFullscreen?.()
    return
  }
  if (stage.requestFullscreen) {
    try {
      await stage.requestFullscreen()
    } catch {
      openPreviewFallbackFullscreen()
    }
  } else {
    openPreviewFallbackFullscreen()
  }
  stage.focus?.({ preventScroll: true })
}

function handleFullscreenChange() {
  const isNativeFullscreen = document.fullscreenElement === previewStageRef.value
  isPreviewFullscreen.value = isNativeFullscreen || isPreviewFullscreenFallback.value
  if (isNativeFullscreen) {
    isPreviewFullscreenFallback.value = false
  }
  if (isPreviewFullscreen.value) {
    previewStageRef.value?.focus?.({ preventScroll: true })
  }
  nextTick(updatePreviewScale)
}

function handleFullscreenKeydown(event) {
  if (!isPreviewFullscreen.value || !pages.value.length) return
  if (event.key === 'Escape' && isPreviewFullscreenFallback.value) {
    event.preventDefault()
    closePreviewFallbackFullscreen()
    return
  }
  const forwardKeys = new Set(['ArrowRight', 'PageDown', ' ', 'Enter'])
  const backwardKeys = new Set(['ArrowLeft', 'PageUp', 'Backspace'])
  if (forwardKeys.has(event.key)) {
    event.preventDefault()
    goPage(1)
    return
  }
  if (backwardKeys.has(event.key)) {
    event.preventDefault()
    goPage(-1)
  }
}

function openPreviewFallbackFullscreen() {
  isPreviewFullscreenFallback.value = true
  isPreviewFullscreen.value = true
  document.body.classList.add('ppt-preview-fallback-fullscreen')
  nextTick(() => {
    previewStageRef.value?.focus?.({ preventScroll: true })
    updatePreviewScale()
  })
}

function closePreviewFallbackFullscreen() {
  isPreviewFullscreenFallback.value = false
  if (document.fullscreenElement !== previewStageRef.value) {
    isPreviewFullscreen.value = false
  }
  document.body.classList.remove('ppt-preview-fallback-fullscreen')
  nextTick(updatePreviewScale)
}

function learningNodeCacheKey() {
  return String(route.query.cacheKey || '').trim()
}

function pptGenerationLocation(sessionId, taskId = '', extraQuery = {}) {
  const query = {
    ...(taskId ? { xzTask: taskId } : {}),
    ...(learningNodeCacheKey() ? { cacheKey: learningNodeCacheKey() } : {}),
    ...(route.query.source ? { source: route.query.source } : {}),
    ...(route.query.stageId ? { stageId: route.query.stageId } : {}),
    ...(route.query.nodeId ? { nodeId: route.query.nodeId } : {}),
    ...extraQuery,
  }
  Object.keys(query).forEach((key) => {
    if (query[key] === undefined || query[key] === null || String(query[key]).trim() === '') delete query[key]
  })
  return router.resolve({
    name: 'ppt-generating',
    params: { sessionId: String(sessionId || 'pending') },
    query,
  })
}

function handleGenerationWindowReady(event) {
  if (event.origin !== window.location.origin || event.data?.type !== 'ppt-generation-window-ready') return
  const sessionId = String(event.data.sessionId || '').trim()
  if (sessionId) readyGenerationSessions.add(sessionId)
}

async function waitForGenerationWindow(sessionId, timeout = 900) {
  const normalizedId = String(sessionId || '').trim()
  if (!normalizedId) return false
  const deadline = Date.now() + timeout
  while (Date.now() < deadline) {
    if (readyGenerationSessions.has(normalizedId)) return true
    await new Promise((resolve) => window.setTimeout(resolve, 75))
  }
  return readyGenerationSessions.has(normalizedId)
}

async function navigateGenerationWindow(targetWindow, location, sessionId) {
  if (targetWindow && !targetWindow.closed) {
    try {
      targetWindow.location.replace(location.href)
    } catch {
      // Fall through to the current-tab task page when the popup proxy is unusable.
    }
    const ready = await waitForGenerationWindow(sessionId)
    if (ready) {
      readyGenerationSessions.delete(String(sessionId || '').trim())
      try {
        targetWindow.opener = null
      } catch {
        // The task window is already usable when opener isolation is unavailable.
      }
      targetWindow.focus?.()
      return
    }
  }
  await router.push(location.fullPath)
}

function restoreLearningNodeSession() {
  const cacheKey = learningNodeCacheKey()
  if (!cacheKey) return false
  const cache = getNodeCache(cacheKey)
  const sessionId = String(route.query.session || cache?.sessionId || '').trim()
  const session = sessions.value.find((item) => item.id === sessionId)
    || sessions.value.find((item) => item.sourceCacheKey === cacheKey)
    || restoreCachedLearningNodePptSession(cache, cacheKey, sessionId)
  if (!session) return false
  currentSessionId.value = session.id
  activePageIndex.value = 0
  activeTab.value = session.status === 'done' || session.status === 'generating' ? 'quick' : 'history'
  setNodeCache(cacheKey, buildLearningNodePptCachePatch(session, { lastOpenedAt: Date.now() }))
  return true
}

function restoreCachedLearningNodePptSession(cache, cacheKey, preferredSessionId = '') {
  if (!cache || typeof cache !== 'object') return null
  const cachedSession = cache.pptSession && typeof cache.pptSession === 'object' ? cache.pptSession : {}
  const cachedPages = Array.isArray(cachedSession.pages)
    ? cachedSession.pages
    : (Array.isArray(cache.pages) ? cache.pages : [])
  if (!cachedPages.length) return null

  const session = {
    id: String(preferredSessionId || cachedSession.id || cache.sessionId || createSessionId(cacheKey)),
    sourceCacheKey: cacheKey,
    sourceTaskId: cachedSession.sourceTaskId || cache.taskId || '',
    title: cachedSession.title || cache.title || '中医基础理论 PPT',
    topic: cachedSession.topic || cache.topic || cache.title || '中医基础理论 PPT',
    pageCount: Number(cachedSession.pageCount || cache.pageCount || cachedPages.length || 6),
    userMessage: cachedSession.userMessage || cache.userMessage || '',
    status: cachedSession.status || (cache.status === 'complete' ? 'done' : (cache.status === 'error' ? 'error' : 'generating')),
    pages: cachedPages,
    generation: cachedSession.generation || cache.generation || {},
    createdAt: toTimestamp(cachedSession.createdAt || cache.createdAt),
    updatedAt: toTimestamp(cachedSession.updatedAt || cache.updatedAt),
  }
  upsertSession(session)
  return session
}

function buildLearningNodePptCachePatch(session, extra = {}) {
  const cacheKey = learningNodeCacheKey() || session?.sourceCacheKey || ''
  const sessionId = session?.id || createSessionId(cacheKey)
  const status = session?.status === 'done'
    ? 'complete'
    : (session?.status === 'error' ? 'error' : 'running')
  const pages = Array.isArray(session?.pages) ? session.pages : []
  return {
    status,
    resourceType: 'ppt',
    title: session?.title || session?.topic || '中医基础理论 PPT',
    sessionId,
    taskId: session?.sourceTaskId || '',
    pageCount: Number(session?.pageCount || pages.length || 0),
    route: pptGenerationLocation(sessionId, session?.sourceTaskId || '').fullPath,
    pages,
    generation: session?.generation || {},
    pptSession: {
      id: sessionId,
      sourceCacheKey: cacheKey,
      sourceTaskId: session?.sourceTaskId || '',
      title: session?.title || session?.topic || '中医基础理论 PPT',
      topic: session?.topic || session?.title || '中医基础理论 PPT',
      pageCount: Number(session?.pageCount || pages.length || 0),
      userMessage: session?.userMessage || '',
      status: session?.status || 'done',
      pages,
      generation: session?.generation || {},
      createdAt: session?.createdAt || Date.now(),
      updatedAt: session?.updatedAt || Date.now(),
    },
    ...extra,
  }
}

async function restoreLearningNodeTaskFromCache() {
  const cacheKey = learningNodeCacheKey()
  if (!cacheKey) return false
  const cache = getNodeCache(cacheKey)
  const taskId = String(route.query.xzTask || cache?.taskId || cache?.sourceTaskId || '').trim()
  if (!taskId) return false
  const task = await loadXiaoZhiTask(taskId)
  if (!task) return false
  return Boolean(
    currentSessionId.value
    || sessions.value.some((session) => session?.sourceTaskId === taskId || session?.sourceCacheKey === cacheKey),
  )
}

function applyRoutePrefill() {
  const topic = String(route.query.topic || '').trim()
  const prompt = String(route.query.prompt || '').trim()
  const pageCount = Number(route.query.pageCount || route.query.pages)
  if (topic) {
    form.topic = topic
    activeTab.value = 'quick'
  }
  if (prompt) form.userMessage = prompt
  if (Number.isFinite(pageCount) && pageCount > 0) {
    form.pageCount = Math.min(12, Math.max(1, Math.round(pageCount)))
  }
}

function syncRouteSession() {
  const sessionId = String(route.query.session || '')
  if (sessionId && sessions.value.some((session) => session.id === sessionId)) {
    currentSessionId.value = sessionId
    activePageIndex.value = 0
    activeTab.value = 'history'
    return
  }
  if (route.query.tab === 'history') {
    activeTab.value = 'history'
  }
}

function stopXiaoZhiTaskPolling() {
  if (xiaozhiTaskTimer) {
    window.clearInterval(xiaozhiTaskTimer)
    xiaozhiTaskTimer = null
  }
}

function startXiaoZhiTaskPolling(taskId) {
  stopXiaoZhiTaskPolling()
  if (!taskId) return
  xiaozhiTaskTimer = window.setInterval(() => {
    loadXiaoZhiTask(taskId)
  }, 1200)
}

async function syncXiaoZhiTask(taskId) {
  if (!taskId) {
    xiaozhiTaskId.value = ''
    stopXiaoZhiTaskPolling()
    return
  }
  xiaozhiTaskId.value = taskId
  await loadXiaoZhiTask(taskId)
}

async function loadXiaoZhiTask(taskId) {
  if (!taskId) return null
  try {
    const response = await getXiaoZhiTask(taskId)
    const task = response?.data?.task
    if (!task) return null
    applyXiaoZhiTask(task)
    if (['queued', 'running'].includes(task.status)) {
      startXiaoZhiTaskPolling(taskId)
    } else {
      stopXiaoZhiTaskPolling()
    }
    return task
  } catch {
    stopXiaoZhiTaskPolling()
    return null
  }
}

function applyXiaoZhiTask(task) {
  const result = task.result || {}
  const ppt = result.ppt || {}
  const topic = ppt.title || result.topic || extractTopicFromTask(task) || '中医学习课件'
  const sessionId = result.sessionId || ppt.sessionId || `xiaozhi_${task.taskId}`
  const timestamp = toTimestamp(task.updatedAt || task.createdAt)
  const generation = normalizeGeneration(task)
  const cacheKey = learningNodeCacheKey()
    || sessions.value.find((item) => item.id === sessionId)?.sourceCacheKey
    || ''

  if (!form.topic.trim()) {
    form.topic = topic
  }
  if (!form.userMessage.trim()) {
    form.userMessage = task.prompt || result.topic || topic
  }

  const baseSession = {
    id: sessionId,
    sourceCacheKey: cacheKey,
    sourceTaskId: task.taskId,
    title: topic,
    topic,
    pageCount: Number(result.pageCount || ppt.pages?.length || 5),
    userMessage: task.prompt || result.topic || topic,
    pages: Array.isArray(ppt.pages) ? ppt.pages : [],
    generation,
    createdAt: toTimestamp(task.createdAt) || timestamp,
    updatedAt: timestamp,
  }

  if (task.status === 'complete') {
    if (Array.isArray(ppt.pages) && ppt.pages.length) {
      const completedSession = {
        ...baseSession,
        title: ppt.title || topic,
        pageCount: ppt.pages.length,
        status: 'done',
        updatedAt: Date.now(),
      }
      upsertSession(completedSession)
      if (cacheKey) {
        markNodeCacheComplete(cacheKey, buildLearningNodePptCachePatch(completedSession, {
          taskId: task.taskId,
        }))
      }
    } else {
      upsertSession({
        ...baseSession,
        status: 'error',
        error: '岐小智任务已完成，但后端没有返回可预览的 PPT 页面',
      })
      if (cacheKey) {
        markNodeCacheError(cacheKey, {
          resourceType: 'ppt',
          title: topic,
          sessionId,
          taskId: task.taskId,
          error: '岐小智任务已完成，但后端没有返回可预览的 PPT 页面',
        })
      }
    }
    currentSessionId.value = sessionId
    activePageIndex.value = 0
    activeTab.value = 'quick'
    if (generatingSessionId.value === sessionId) {
      generatingSessionId.value = ''
    }
    return
  }

  if (task.status === 'failed') {
    upsertSession({
      ...baseSession,
      status: 'error',
      error: task.error || '岐小智 PPT 任务生成失败',
      generation,
    })
    if (cacheKey) {
      markNodeCacheError(cacheKey, {
        resourceType: 'ppt',
        title: topic,
        sessionId,
        taskId: task.taskId,
        error: task.error || '岐小智 PPT 任务生成失败',
      })
    }
    currentSessionId.value = sessionId
    activePageIndex.value = 0
    if (generatingSessionId.value === sessionId) {
      generatingSessionId.value = ''
    }
    return
  }

  upsertSession({
    ...baseSession,
    status: 'generating',
    generation,
  })
  currentSessionId.value = sessionId
  activePageIndex.value = 0
  activeTab.value = 'quick'
  generatingSessionId.value = sessionId
}

function extractTopicFromTask(task) {
  const title = String(task?.title || '')
  return title.replace(/\s*·\s*PPT.*$/i, '').trim()
}

function normalizeGeneration(task) {
  const result = task?.result && typeof task.result === 'object' ? task.result : {}
  const ppt = result.ppt && typeof result.ppt === 'object' ? result.ppt : {}
  const logs = Array.isArray(result.logs) ? result.logs : []
  const agentRuns = Array.isArray(result.agentRuns) ? result.agentRuns : []
  const status = task?.status || result.status || 'running'
  const currentStage = result.currentStage || (status === 'complete' ? 'complete' : '')
  return {
    taskId: task?.taskId || '',
    status,
    progress: clampProgress(result.progress ?? (status === 'complete' ? 100 : 5)),
    currentStage,
    message: result.message || stageLabel(currentStage),
    logs,
    agentRuns,
    pageCount: Number(result.pageCount || ppt.pages?.length || 0),
    updatedAt: toTimestamp(task?.updatedAt || task?.createdAt),
  }
}

function createInitialGeneration(sessionId, pageCount) {
  return {
    taskId: '',
    status: 'running',
    progress: 3,
    currentStage: 'start',
    message: 'PPT 后台生成任务已启动',
    logs: [
      {
        time: new Date().toISOString(),
        stage: 'start',
        message: 'PPT 后台生成任务已启动',
        progress: 3,
      },
    ],
    agentRuns: [
      { name: 'PPT任务规划智能体', status: 'running', detail: '解析主题、页数和风格约束' },
      { name: 'OhMyPPT生成智能体', status: 'queued', detail: '等待独立 FastAPI 引擎生成页面' },
      { name: '页面审核智能体', status: 'queued', detail: '等待页面结构与安全校验' },
    ],
    pageCount,
    sessionId,
    updatedAt: Date.now(),
  }
}

function clampProgress(value) {
  const progress = Number(value)
  if (!Number.isFinite(progress)) return 0
  return Math.min(100, Math.max(0, Math.round(progress)))
}

function stageLabel(stage) {
  const key = String(stage || '').trim()
  return GENERATION_STAGE_LABELS[key] || '生成任务进行中'
}

function agentStatusClass(status) {
  const value = String(status || 'queued').toLowerCase()
  if (value === 'complete' || value === 'done') return 'is-complete'
  if (value === 'running') return 'is-running'
  if (value === 'failed' || value === 'error') return 'is-error'
  return 'is-queued'
}

function agentStatusText(status) {
  const value = String(status || 'queued').toLowerCase()
  if (value === 'complete' || value === 'done') return '已完成'
  if (value === 'running') return '运行中'
  if (value === 'failed' || value === 'error') return '异常'
  return '等待中'
}

function formatLogTime(value) {
  const time = Date.parse(value || '')
  if (!Number.isFinite(time)) return '--:--'
  return new Intl.DateTimeFormat('zh-CN', {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: false,
  }).format(new Date(time))
}

function toTimestamp(value) {
  const time = Date.parse(value || '')
  return Number.isFinite(time) ? time : Date.now()
}

function loadSessions() {
  try {
    const parsed = JSON.parse(localStorage.getItem(STORAGE_KEY) || '[]')
    return Array.isArray(parsed) ? parsed.filter((item) => item && item.id).slice(0, MAX_HISTORY) : []
  } catch {
    return []
  }
}

function resolveTaskPptPayload(task) {
  const result = task?.result && typeof task.result === 'object' ? task.result : {}
  const topPpt = result.ppt && typeof result.ppt === 'object' ? result.ppt : {}
  const nestedPpt = topPpt.ppt && typeof topPpt.ppt === 'object' ? topPpt.ppt : {}
  return [nestedPpt, topPpt, result].find((item) => Array.isArray(item?.pages)) || topPpt || result
}

function taskRouteParams(task) {
  try {
    const url = new URL(String(task?.route || ''), window.location.origin)
    return Object.fromEntries(url.searchParams.entries())
  } catch {
    return {}
  }
}

function sessionFromPersistedTask(task) {
  if (!task?.taskId) return null
  const result = task.result && typeof task.result === 'object' ? task.result : {}
  const ppt = resolveTaskPptPayload(task)
  const params = result.params && typeof result.params === 'object' ? result.params : {}
  const routeParams = taskRouteParams(task)
  const sessionId = String(
    ppt.sessionId
      || result.sessionId
      || result.ohmyPptSessionId
      || params.sessionId
      || routeParams.sessionId
      || `xiaozhi_${task.taskId}`,
  )
  const pages = Array.isArray(ppt.pages) ? ppt.pages : []
  const status = task.status === 'complete' && pages.length
    ? 'done'
    : (task.status === 'failed' ? 'error' : 'generating')
  const topic = String(ppt.title || result.topic || extractTopicFromTask(task) || '中医学习课件')
  return {
    id: sessionId,
    sourceTaskId: task.taskId,
    sourceCacheKey: String(params.cacheKey || routeParams.cacheKey || ''),
    title: topic,
    topic,
    pageCount: Number(result.pageCount || params.pageCount || pages.length || 6),
    userMessage: task.prompt || params.prompt || topic,
    status,
    pages,
    generation: normalizeGeneration(task),
    error: task.error || result.qualityError || '',
    profileReportId: Number(
      ppt?.harness?.profileReportId
        || ppt?.orchestration?.profileReportId
        || result?.orchestration?.profileReportId
        || params.profileReportId
        || 0,
    ),
    createdAt: toTimestamp(task.createdAt),
    updatedAt: toTimestamp(task.updatedAt || task.createdAt),
  }
}

async function refreshPersistedHistory() {
  if (historyLoading.value) return
  historyLoading.value = true
  try {
    const snapshot = await getPptTaskHistory({ limit: MAX_HISTORY })
    const persisted = (Array.isArray(snapshot?.tasks) ? snapshot.tasks : [])
      .map(sessionFromPersistedTask)
      .filter(Boolean)
    saveSessions([...persisted, ...sessions.value])
  } catch {
    // Local history remains available while the API is temporarily unavailable.
  } finally {
    historyLoading.value = false
  }
}

function saveSessions(nextSessions) {
  const seen = new Set()
  const normalizedSessions = nextSessions
    .filter((session) => {
      if (!session?.id || seen.has(session.id)) return false
      seen.add(session.id)
      return true
    })
    .sort((a, b) => Number(b.updatedAt || 0) - Number(a.updatedAt || 0))
    .slice(0, MAX_HISTORY)
  sessions.value = normalizedSessions
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(normalizedSessions))
  } catch {
    const compactSessions = normalizedSessions.slice(0, 3)
    sessions.value = compactSessions
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(compactSessions))
    } catch {
      localStorage.removeItem(STORAGE_KEY)
    }
  }
}

function upsertSession(session) {
  saveSessions([session, ...sessions.value.filter((item) => item.id !== session.id)])
}

function createSessionId(seed = '') {
  const normalizedSeed = String(seed || '').trim().replace(/[^a-zA-Z0-9_-]/g, '_')
  if (normalizedSeed) return `ppt_${normalizedSeed}`
  return `ppt_${Date.now().toString(36)}_${Math.random().toString(36).slice(2, 8)}`
}

function normalizePageCount() {
  const pageCount = Number(form.pageCount)
  form.pageCount = Number.isFinite(pageCount) ? Math.min(12, Math.max(1, Math.round(pageCount))) : 6
}

function resetForm() {
  form.topic = ''
  form.pageCount = 6
  form.userMessage = ''
}

async function submitQuickCreate() {
  normalizePageCount()
  const topic = form.topic.trim()
  if (!topic || generating.value) return
  if (restoreLearningNodeSession()) return

  const now = Date.now()
  const cacheKey = learningNodeCacheKey()
  const sessionId = createSessionId(cacheKey)
  const pendingLocation = pptGenerationLocation(sessionId, '', {
    pending: '1',
    topic,
    pageCount: form.pageCount,
  })
  const generationWindow = window.open(pendingLocation.href, '_blank')
  generationWindow?.focus?.()
  const draftSession = {
    id: sessionId,
    sourceCacheKey: cacheKey,
    title: topic,
    topic,
    pageCount: form.pageCount,
    userMessage: form.userMessage.trim(),
    status: 'generating',
    pages: [],
    generation: createInitialGeneration(sessionId, form.pageCount),
    createdAt: now,
    updatedAt: now,
  }

  generatingSessionId.value = sessionId
  currentSessionId.value = sessionId
  activePageIndex.value = 0
  activeTab.value = 'quick'
  upsertSession(draftSession)
  if (cacheKey) {
    markNodeCacheStarted(cacheKey, {
      resourceType: 'ppt',
      title: topic,
      sessionId,
      route: pendingLocation.fullPath,
    })
  }

  try {
    const response = await startPptH5Generation({
      sessionId,
      topic,
      userMessage: form.userMessage.trim() || `生成一份关于“${topic}”的岐黄智境平台风格 PPT。`,
      pageCount: form.pageCount,
      styleName: '岐黄智境平台',
      styleDescription: '白底浅绿、干净明亮、留白充足、模块化教育科技风。',
      styleSkill: PLATFORM_STYLE_SKILL,
    })
    const task = response?.data?.task || response?.task || null
    const taskId = task?.taskId || response?.taskId || response?.data?.pptTask?.taskId || ''
    if (!taskId) throw new Error('后端没有返回 PPT 任务编号')
    const effectiveSessionId = String(task?.result?.sessionId || task?.result?.ohmyPptSessionId || sessionId)
    generatingSessionId.value = effectiveSessionId
    currentSessionId.value = effectiveSessionId
    const generationLocation = pptGenerationLocation(effectiveSessionId, taskId, {
      topic,
      pageCount: form.pageCount,
    })
    const generation = task ? normalizeGeneration(task) : { ...draftSession.generation, taskId, updatedAt: Date.now() }
    upsertSession({
      ...draftSession,
      id: effectiveSessionId,
      sourceTaskId: taskId,
      status: 'generating',
      generation,
      updatedAt: Date.now(),
    })
    if (cacheKey) {
      setNodeCache(cacheKey, {
        status: 'running',
        resourceType: 'ppt',
        title: topic,
        sessionId: effectiveSessionId,
        taskId,
        route: generationLocation.fullPath,
      })
    }
    await navigateGenerationWindow(generationWindow, generationLocation, effectiveSessionId)
    if (taskId) {
      xiaozhiTaskId.value = taskId
      window.dispatchEvent(new CustomEvent('xiaozhi-task-updated', { detail: { taskId, taskType: 'ppt' } }))
      startXiaoZhiTaskPolling(taskId)
      await loadXiaoZhiTask(taskId)
    }
  } catch (error) {
    const errorMessage = error?.response?.data?.msg || error?.response?.data?.error || error?.message || '生成失败'
    upsertSession({
      ...draftSession,
      status: 'error',
      error: errorMessage,
      updatedAt: Date.now(),
    })
    if (cacheKey) {
      markNodeCacheError(cacheKey, {
        resourceType: 'ppt',
        title: topic,
        sessionId,
        error: errorMessage,
      })
    }
    await navigateGenerationWindow(generationWindow, pptGenerationLocation(sessionId, '', {
      state: 'error',
      message: errorMessage.slice(0, 300),
      topic,
      pageCount: form.pageCount,
    }), sessionId)
    if (generatingSessionId.value === sessionId) {
      generatingSessionId.value = ''
    }
  }
}

function selectSession(session) {
  if (session?.sourceTaskId) {
    const location = pptGenerationLocation(session.id, session.sourceTaskId, {
      topic: session.topic || session.title,
      pageCount: session.pageCount || getSessionPageCount(session),
    })
    const targetWindow = window.open(location.href, '_blank')
    if (targetWindow) {
      try {
        targetWindow.opener = null
      } catch {
        // Ignore opener isolation failures; the task page is still usable.
      }
      targetWindow.focus?.()
    } else {
      router.push(location.fullPath)
    }
    return
  }
  currentSessionId.value = session.id
  activePageIndex.value = 0
}

function sessionStatusText(session) {
  if (session?.status === 'done') return '已完成'
  if (session?.status === 'error') return '失败'
  return '生成中'
}

function goPage(step) {
  activePageIndex.value = clampPageIndex(activePageIndex.value + step)
  nextTick(updatePreviewScale)
}

function clampPageIndex(index) {
  return Math.min(Math.max(index, 0), Math.max(pages.value.length - 1, 0))
}

function normalizeWheelDelta(event) {
  const delta = Math.abs(event.deltaY) >= Math.abs(event.deltaX) ? event.deltaY : event.deltaX
  if (event.deltaMode === 1) return delta * 16
  if (event.deltaMode === 2) return delta * 120
  return delta
}

function handlePreviewWheel(event) {
  if (!pages.value.length || isCurrentGenerating.value || event.ctrlKey) return
  const delta = normalizeWheelDelta(event)
  if (Math.abs(delta) < 4) return
  const direction = delta > 0 ? 1 : -1
  const targetIndex = clampPageIndex(activePageIndex.value + direction)
  if (targetIndex === activePageIndex.value && !isPreviewFullscreen.value) return

  event.preventDefault()
  event.stopPropagation()
  previewWheelDelta += delta

  const now = Date.now()
  if (Math.abs(previewWheelDelta) < 70 || now - previewWheelLastTurnAt < 260) return
  previewWheelDelta = 0
  previewWheelLastTurnAt = now
  if (targetIndex !== activePageIndex.value) {
    activePageIndex.value = targetIndex
    nextTick(updatePreviewScale)
  }
}

function handleSlideStripWheel(event) {
  const strip = event.currentTarget
  if (!strip) return
  const maxScrollLeft = strip.scrollWidth - strip.clientWidth
  if (maxScrollLeft <= 0) return
  const delta = normalizeWheelDelta(event)
  if (Math.abs(delta) < 2) return
  const nextScrollLeft = Math.min(Math.max(strip.scrollLeft + delta, 0), maxScrollLeft)
  if (nextScrollLeft === strip.scrollLeft) return
  event.preventDefault()
  event.stopPropagation()
  strip.scrollLeft = nextScrollLeft
}

function updatePreviewScale() {
  const stage = previewStageRef.value
  if (!stage) return
  const rect = stage.getBoundingClientRect()
  const scale = Math.min(rect.width / 1600, rect.height / 900)
  previewScale.value = Number.isFinite(scale) && scale > 0 ? Math.round(scale * 10000) / 10000 : 1
}

function getSessionPageCount(session) {
  if (!session) return 0
  if (Array.isArray(session.pages) && session.pages.length) return session.pages.length
  return Number(session.pageCount || 0)
}

function exportPptFile() {
  if (!pages.value.length || exporting.value) return
  exporting.value = true
  try {
    const session = currentSession.value || {}
    const title = session.title || session.topic || form.topic || '岐黄智境PPT'
    const html = buildStandalonePptHtml(title, pages.value)
    downloadBlob(html, `${sanitizeFilename(title)}.html`, 'text/html;charset=utf-8')
  } finally {
    exporting.value = false
  }
}

function buildStandalonePptHtml(title, slidePages) {
  const slides = slidePages.map((page, index) => ({
    title: String(page.title || `第 ${index + 1} 页`),
    html: String(page.html || ''),
  }))
  const slidesJson = JSON.stringify(slides)
    .replace(/</g, '\\u003c')
    .replace(/\u2028/g, '\\u2028')
    .replace(/\u2029/g, '\\u2029')
  const safeTitle = escapeHtmlText(title)
  const titleJson = JSON.stringify(String(title || '岐黄智境PPT'))
    .replace(/</g, '\\u003c')
    .replace(/\u2028/g, '\\u2028')
    .replace(/\u2029/g, '\\u2029')
  return `<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>${safeTitle}</title>
<style>
*{box-sizing:border-box}
html,body{margin:0;width:100%;height:100%;overflow:hidden;background:#eef9f4;color:#172033;font-family:"Inter","Segoe UI","PingFang SC","Microsoft YaHei",system-ui,sans-serif}
body{display:grid;place-items:center}
.deck-shell{width:100vw;height:100vh;display:grid;grid-template-rows:auto minmax(0,1fr) auto;background:linear-gradient(180deg,#ffffff 0%,#eef9f4 100%)}
.deck-head,.deck-foot{display:flex;align-items:center;justify-content:space-between;gap:14px;padding:14px 18px;background:rgba(255,255,255,.94);border-color:rgba(33,185,120,.16);z-index:10}
.deck-head{border-bottom:1px solid rgba(33,185,120,.16)}
.deck-foot{border-top:1px solid rgba(33,185,120,.16)}
.deck-title{min-width:0}
.deck-title strong{display:block;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;font-size:16px}
.deck-title span{display:block;margin-top:3px;color:#0e9f6e;font-size:12px;font-weight:800}
.deck-actions{display:flex;gap:8px;align-items:center}
button{height:36px;padding:0 12px;border:1px solid #cdefe3;border-radius:8px;background:#fff;color:#25342f;font:inherit;font-size:13px;font-weight:800;cursor:pointer}
button:hover{background:#f1fbf7}
button:disabled{opacity:.45;cursor:not-allowed}
.stage{position:relative;min-width:0;min-height:0;background:#0b1713;overflow:hidden}
.stage iframe{position:absolute;inset:0;width:100%;height:100%;border:0;background:#f4faf9}
.hit-zone{position:absolute;top:0;bottom:0;z-index:5;border:0;border-radius:0;background:transparent;color:transparent}
.hit-zone.prev{left:0;width:34%}
.hit-zone.next{right:0;width:66%}
.hit-zone:hover{background:rgba(33,185,120,.05)}
.dots{display:flex;gap:6px;align-items:center;overflow:auto}
.dots button{width:34px;height:28px;padding:0;border-radius:999px;color:#64748b}
.dots button.active{background:#21b978;color:#fff;border-color:#21b978}
.counter{color:#64748b;font-size:13px;font-weight:800}
@media (max-width:720px){.deck-head,.deck-foot{padding:10px}.deck-actions button span{display:none}.dots button{width:28px}}
</style>
</head>
<body>
<div class="deck-shell">
  <header class="deck-head">
    <div class="deck-title"><strong id="deckTitle"></strong><span>岐黄智境 H5 演示文稿</span></div>
    <div class="deck-actions">
      <span class="counter" id="counter"></span>
      <button id="prevBtn" type="button">上一页</button>
      <button id="nextBtn" type="button">下一页</button>
      <button id="fullBtn" type="button">全屏</button>
    </div>
  </header>
  <main class="stage" id="stage">
    <iframe id="slideFrame" title="PPT 页面" sandbox="allow-scripts"></iframe>
    <button id="leftHit" class="hit-zone prev" type="button" aria-label="上一页">上一页</button>
    <button id="rightHit" class="hit-zone next" type="button" aria-label="下一页">下一页</button>
  </main>
  <footer class="deck-foot">
    <div class="dots" id="dots"></div>
    <span class="counter" id="slideName"></span>
  </footer>
</div>
<script>
const slides = ${slidesJson};
let activeIndex = 0;
const frame = document.getElementById('slideFrame');
const title = document.getElementById('deckTitle');
const counter = document.getElementById('counter');
const slideName = document.getElementById('slideName');
const prevBtn = document.getElementById('prevBtn');
const nextBtn = document.getElementById('nextBtn');
const dots = document.getElementById('dots');
const stage = document.getElementById('stage');
title.textContent = ${titleJson};
function fitSlideHtml(html) {
  const fitStyle = '<style>html,body{width:100%;height:100%;margin:0;overflow:hidden;background:#f4faf9!important}body{display:flex!important;align-items:center!important;justify-content:center!important}.slide.ppt-page-root{flex:0 0 auto!important;transform:scale(min(calc(100vw / 1600),calc(100vh / 900)))!important;transform-origin:center center!important}</style>';
  return html.includes('</head>') ? html.replace('</head>', fitStyle + '</head>') : fitStyle + html;
}
function renderDots() {
  dots.innerHTML = '';
  slides.forEach((_, index) => {
    const btn = document.createElement('button');
    btn.type = 'button';
    btn.textContent = String(index + 1);
    btn.className = index === activeIndex ? 'active' : '';
    btn.addEventListener('click', () => goTo(index));
    dots.appendChild(btn);
  });
}
function render() {
  const slide = slides[activeIndex] || { title: '', html: '' };
  frame.srcdoc = fitSlideHtml(slide.html || '');
  counter.textContent = (activeIndex + 1) + ' / ' + slides.length;
  slideName.textContent = slide.title || '';
  prevBtn.disabled = activeIndex <= 0;
  nextBtn.disabled = activeIndex >= slides.length - 1;
  document.querySelectorAll('.dots button').forEach((btn, index) => btn.classList.toggle('active', index === activeIndex));
}
function goTo(index) {
  activeIndex = Math.max(0, Math.min(slides.length - 1, index));
  render();
}
function go(step) {
  goTo(activeIndex + step);
}
prevBtn.addEventListener('click', () => go(-1));
nextBtn.addEventListener('click', () => go(1));
document.getElementById('leftHit').addEventListener('click', () => go(-1));
document.getElementById('rightHit').addEventListener('click', () => go(1));
document.getElementById('fullBtn').addEventListener('click', () => {
  if (document.fullscreenElement) document.exitFullscreen?.();
  else stage.requestFullscreen?.();
});
document.addEventListener('keydown', (event) => {
  if (['ArrowRight','PageDown',' ','Enter'].includes(event.key)) { event.preventDefault(); go(1); }
  if (['ArrowLeft','PageUp','Backspace'].includes(event.key)) { event.preventDefault(); go(-1); }
});
renderDots();
render();
<\/script>
</body>
</html>`
}

function sanitizeFilename(value) {
  const name = String(value || '岐黄智境PPT').replace(/[\\/:*?"<>|]+/g, '_').replace(/\s+/g, ' ').trim()
  return name.slice(0, 80) || '岐黄智境PPT'
}

function escapeHtmlText(value) {
  return String(value || '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;')
}

function downloadBlob(content, filename, type) {
  const blob = new Blob([content], { type })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  document.body.appendChild(link)
  link.click()
  link.remove()
  window.setTimeout(() => URL.revokeObjectURL(url), 800)
}

function formatDate(timestamp) {
  if (!timestamp) return '刚刚'
  return new Intl.DateTimeFormat('zh-CN', {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  }).format(new Date(timestamp))
}

function fitSlideHtml(html) {
  if (!html) return ''
  const fitStyle = `
<style>
html,body{width:100%;height:100%;margin:0;overflow:hidden;background:#f4faf9!important}
body{display:flex!important;align-items:center!important;justify-content:center!important}
.slide.ppt-page-root{flex:0 0 auto!important;transform:scale(min(calc(100vw / 1600),calc(100vh / 900)))!important;transform-origin:center center!important}
</style>`
  if (html.includes('</head>')) {
    return html.replace('</head>', `${fitStyle}</head>`)
  }
  return `${fitStyle}${html}`
}
</script>

<style scoped>
.ppt-native-page {
  height: calc(100vh - 72px);
  min-height: calc(100vh - 72px);
  overflow-x: hidden;
  overflow-y: auto;
  overscroll-behavior: contain;
  scrollbar-gutter: stable;
  padding: 20px clamp(18px, 2.2vw, 34px) 28px;
  box-sizing: border-box;
  background:
    linear-gradient(90deg, rgba(232, 249, 241, 0.82) 0, rgba(232, 249, 241, 0.34) 18%, transparent 36%),
    linear-gradient(180deg, #ffffff 0%, #f7fbf9 100%);
  color: #1f2937;
}

.ppt-native-page.standalone {
  min-height: calc(100vh - 72px);
  padding-top: 20px;
}

:global(#app.xiaozhi-embed-app) .ppt-native-page {
  height: 100vh;
  min-height: 100vh;
}

.resource-back-button {
  position: static;
  width: fit-content;
  height: 42px;
  margin: 0 0 14px;
  padding: 0 18px;
  display: inline-flex;
  align-items: center;
  gap: 8px;
  border: 1px solid #cdefe3;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.96);
  color: #0e9f6e;
  font-size: 14px;
  font-weight: 700;
  box-shadow: 0 10px 26px rgba(31, 72, 66, 0.1);
  cursor: pointer;
}

.ppt-header,
.ppt-workspace {
  width: min(1680px, 100%);
  margin: 0 auto;
}

.ppt-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 24px;
  padding: 16px 18px;
  border: 1px solid rgba(33, 185, 120, 0.12);
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.78);
  box-shadow: 0 16px 38px rgba(18, 84, 68, 0.06);
}

.ppt-kicker {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  height: 32px;
  padding: 0 12px;
  border: 1px solid rgba(33, 185, 120, 0.16);
  border-radius: 999px;
  background: #f1fbf7;
  color: #0e9f6e;
  font-size: 13px;
  font-weight: 800;
}

.ppt-header h1 {
  margin: 10px 0 0;
  color: #172033;
  font-size: clamp(26px, 2.5vw, 34px);
  line-height: 1.18;
  font-weight: 850;
  letter-spacing: 0;
}

.ppt-header-metrics {
  display: flex;
  gap: 12px;
}

.metric {
  min-width: 96px;
  padding: 12px 14px;
  border: 1px solid rgba(33, 185, 120, 0.14);
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.92);
  box-shadow: 0 12px 28px rgba(18, 84, 68, 0.06);
}

.metric strong,
.metric span {
  display: block;
}

.metric strong {
  color: #0e9f6e;
  font-size: 22px;
  line-height: 1;
}

.metric span {
  margin-top: 6px;
  color: #64748b;
  font-size: 12px;
}

.ppt-tabs {
  display: inline-flex;
  gap: 6px;
  padding: 4px;
  margin-top: 14px;
  border: 1px solid #dcece5;
  border-radius: 8px;
  background: #ffffff;
  box-shadow: 0 10px 28px rgba(15, 23, 42, 0.04);
}

.ppt-tabs button {
  height: 38px;
  padding: 0 16px;
  display: inline-flex;
  align-items: center;
  gap: 8px;
  border: 0;
  border-radius: 6px;
  background: transparent;
  color: #64748b;
  font-size: 14px;
  font-weight: 800;
  cursor: pointer;
}

.ppt-tabs button.active {
  background: #21b978;
  color: #ffffff;
}

.content-grid {
  display: grid;
  grid-template-columns: minmax(300px, 430px) minmax(720px, 1fr);
  gap: 18px;
  margin-top: 14px;
  align-items: start;
}

.content-grid.history-mode {
  grid-template-columns: minmax(300px, 440px) minmax(720px, 1fr);
}

.tool-panel {
  min-width: 0;
  border: 1px solid rgba(33, 185, 120, 0.13);
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.96);
  box-shadow: 0 18px 46px rgba(18, 84, 68, 0.07);
}

.creator-tool,
.history-tool,
.preview-tool {
  padding: 18px;
}

.panel-title,
.preview-status,
.creator-actions,
.page-actions,
.history-title {
  display: flex;
  align-items: center;
}

.panel-title {
  gap: 10px;
  margin-bottom: 18px;
  color: #0e9f6e;
}

.panel-title h2,
.preview-head h2 {
  margin: 0;
  color: #172033;
  font-size: 20px;
  line-height: 1.25;
  font-weight: 850;
  letter-spacing: 0;
}

.field {
  display: block;
  margin-bottom: 14px;
}

.field span {
  display: block;
  margin-bottom: 8px;
  color: #25342f;
  font-size: 14px;
  font-weight: 800;
}

.field input,
.field textarea {
  width: 100%;
  border: 1px solid #dce8e3;
  border-radius: 8px;
  background: #ffffff;
  color: #1f2937;
  font: inherit;
  font-size: 15px;
  line-height: 1.6;
  outline: none;
  transition: border-color 0.2s ease, box-shadow 0.2s ease;
}

.field input {
  height: 44px;
  padding: 0 14px;
}

.field textarea {
  resize: vertical;
  min-height: 132px;
  padding: 12px 14px;
}

.field input:focus,
.field textarea:focus {
  border-color: #58d89c;
  box-shadow: 0 0 0 3px rgba(33, 185, 120, 0.12);
}

.creator-actions {
  gap: 10px;
  margin-top: 18px;
}

.primary-action,
.secondary-action,
.ghost-action,
.page-actions button {
  height: 42px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 800;
  cursor: pointer;
  transition: transform 0.2s ease, background 0.2s ease, border-color 0.2s ease;
}

.primary-action {
  flex: 1;
  border: 0;
  background: linear-gradient(135deg, #21b978, #58d89c);
  color: #ffffff;
}

.secondary-action,
.page-actions button {
  border: 1px solid #dce8e3;
  background: #ffffff;
  color: #53656a;
}

.secondary-action {
  padding: 0 16px;
}

.primary-action:not(:disabled):hover,
.secondary-action:not(:disabled):hover,
.page-actions button:not(:disabled):hover,
.ghost-action:not(:disabled):hover {
  transform: translateY(-1px);
}

button:disabled {
  cursor: not-allowed;
  opacity: 0.56;
}

.history-title {
  justify-content: space-between;
}

.history-title h2 {
  flex: 1;
}

.ghost-action {
  height: 34px;
  padding: 0 10px;
  border: 1px solid #e5ece9;
  background: #f8fbfa;
  color: #64748b;
}

.history-list {
  display: grid;
  gap: 10px;
  max-height: 610px;
  overflow: auto;
  padding-right: 4px;
}

.session-row {
  width: 100%;
  min-height: 74px;
  display: grid;
  grid-template-columns: 40px minmax(0, 1fr) auto;
  align-items: center;
  gap: 12px;
  padding: 12px;
  border: 1px solid #e2ece7;
  border-radius: 8px;
  background: #ffffff;
  text-align: left;
  cursor: pointer;
}

.session-row.active {
  border-color: rgba(33, 185, 120, 0.44);
  background: #f4fcf8;
}

.session-icon {
  width: 40px;
  height: 40px;
  display: grid;
  place-items: center;
  border-radius: 8px;
  background: #e9f8f1;
  color: #0e9f6e;
}

.session-main {
  min-width: 0;
}

.session-main strong,
.session-main small {
  display: block;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.session-main strong {
  color: #172033;
  font-size: 14px;
  line-height: 1.35;
}

.session-main small,
.session-meta {
  color: #64748b;
  font-size: 12px;
}

.session-meta {
  padding: 5px 8px;
  border-radius: 999px;
  background: #f1f5f9;
}

.preview-tool {
  display: flex;
  flex-direction: column;
  min-height: min(720px, calc(100vh - 190px));
}

.preview-head {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 12px;
}

.preview-status {
  gap: 7px;
  margin-bottom: 7px;
  color: #0e9f6e;
  font-size: 13px;
  font-weight: 800;
}

.page-actions {
  align-self: start;
  display: flex;
  flex-wrap: wrap;
  justify-content: flex-end;
  gap: 8px;
}

.page-actions button {
  padding: 0 12px;
}

.preview-stage {
  position: relative;
  width: 100%;
  aspect-ratio: 16 / 9;
  min-height: 420px;
  flex: 1;
  overflow: hidden;
  overscroll-behavior: contain;
  border: 1px solid #dce8e3;
  border-radius: 8px;
  background: #eef7f3;
}

.preview-stage:focus {
  outline: none;
}

.preview-stage:fullscreen,
.preview-stage.fallback-fullscreen {
  width: 100vw;
  height: 100vh;
  min-height: 100vh;
  aspect-ratio: auto;
  border: 0;
  border-radius: 0;
  background: #000;
}

.preview-stage.fallback-fullscreen {
  position: fixed;
  inset: 0;
  z-index: 1000;
}

:global(body.ppt-preview-fallback-fullscreen) {
  overflow: hidden;
}

.fullscreen-hit-zone {
  display: none;
}

.preview-stage:fullscreen .fullscreen-hit-zone,
.preview-stage.fallback-fullscreen .fullscreen-hit-zone {
  position: absolute;
  top: 0;
  bottom: 0;
  z-index: 20;
  display: block;
  border: 0;
  background: transparent;
  cursor: pointer;
}

.preview-stage:fullscreen .fullscreen-hit-zone.prev,
.preview-stage.fallback-fullscreen .fullscreen-hit-zone.prev {
  left: 0;
  width: 35%;
}

.preview-stage:fullscreen .fullscreen-hit-zone.next,
.preview-stage.fallback-fullscreen .fullscreen-hit-zone.next {
  right: 0;
  width: 65%;
}

.preview-stage:fullscreen .fullscreen-hit-zone:disabled,
.preview-stage.fallback-fullscreen .fullscreen-hit-zone:disabled {
  pointer-events: none;
}

.preview-frame-shell {
  position: absolute;
  inset: 0;
  overflow: hidden;
  background:
    linear-gradient(135deg, rgba(244, 250, 249, 0.96), rgba(230, 248, 239, 0.88));
}

.preview-frame {
  position: absolute;
  left: 50%;
  top: 50%;
  width: 1600px;
  height: 900px;
  border: 0;
  display: block;
  pointer-events: none;
  background: #ffffff;
  transform-origin: center center;
}

.generation-panel {
  height: 100%;
  min-height: 360px;
  display: grid;
  grid-template-columns: minmax(0, 1.25fr) minmax(250px, 0.75fr);
  grid-template-rows: auto 10px auto minmax(100px, 1fr);
  gap: 12px 18px;
  padding: clamp(20px, 2.4vw, 34px);
  overflow: auto;
  box-sizing: border-box;
  background:
    linear-gradient(135deg, rgba(255, 255, 255, 0.88), rgba(233, 249, 241, 0.94)),
    #eefcf6;
}

.generation-panel.without-agents {
  grid-template-columns: minmax(0, 1fr);
}

.generation-panel.without-agents > * {
  grid-column: 1 / -1;
}

.generation-hero {
  grid-column: 1 / 2;
  grid-row: 1;
  align-self: start;
}

.generation-badge {
  width: fit-content;
  height: 30px;
  padding: 0 10px;
  display: inline-flex;
  align-items: center;
  gap: 7px;
  border: 1px solid rgba(33, 185, 120, 0.22);
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.88);
  color: #0e9f6e;
  font-size: 12px;
  font-weight: 850;
}

.generation-hero strong {
  display: block;
  margin-top: 14px;
  color: #172033;
  font-size: 24px;
  line-height: 1.25;
  font-weight: 850;
  letter-spacing: 0;
}

.generation-hero p {
  max-width: 620px;
  margin: 9px 0 0;
  color: #53656a;
  font-size: 14px;
  line-height: 1.6;
}

.generation-progress {
  grid-column: 1 / 2;
  grid-row: 2;
  height: 10px;
  overflow: hidden;
  border-radius: 999px;
  background: #dce8e3;
}

.generation-progress span {
  display: block;
  width: 0;
  height: 100%;
  border-radius: inherit;
  background: linear-gradient(90deg, #21b978, #82e5b7);
  box-shadow: 0 0 18px rgba(33, 185, 120, 0.36);
  transition: width 0.45s ease;
}

.generation-meta {
  grid-column: 1 / 2;
  grid-row: 3;
  display: flex;
  justify-content: space-between;
  color: #64748b;
  font-size: 12px;
  font-weight: 800;
}

.generation-meta span:first-child {
  color: #0e9f6e;
}

.generation-agents {
  grid-column: 2 / 3;
  grid-row: 1 / 5;
  display: grid;
  align-content: center;
  gap: 10px;
  min-height: 0;
  overflow: auto;
}

.generation-agent {
  min-height: 72px;
  display: grid;
  grid-template-columns: 12px minmax(0, 1fr);
  gap: 10px;
  align-items: start;
  padding: 12px;
  border: 1px solid #dce8e3;
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.82);
}

.agent-dot {
  width: 9px;
  height: 9px;
  margin-top: 5px;
  border-radius: 50%;
  background: #cbd5e1;
}

.generation-agent strong,
.generation-agent small {
  display: block;
}

.generation-agent strong {
  overflow: hidden;
  color: #172033;
  font-size: 13px;
  line-height: 1.35;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.generation-agent small {
  margin-top: 4px;
  color: #64748b;
  font-size: 12px;
  line-height: 1.45;
}

.generation-agent.is-running {
  border-color: rgba(33, 185, 120, 0.28);
  background: rgba(241, 251, 247, 0.9);
}

.generation-agent.is-running .agent-dot {
  background: #21b978;
  box-shadow: 0 0 0 5px rgba(33, 185, 120, 0.13);
}

.generation-agent.is-complete .agent-dot {
  background: #0e9f6e;
}

.generation-agent.is-error {
  border-color: rgba(180, 35, 24, 0.22);
  background: #fff7f6;
}

.generation-agent.is-error .agent-dot {
  background: #b42318;
}

.generation-log {
  grid-column: 1 / 2;
  grid-row: 4;
  min-height: 0;
  align-self: stretch;
  border: 1px solid #dce8e3;
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.74);
  overflow: hidden;
}

.generation-log header {
  height: 40px;
  padding: 0 14px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  border-bottom: 1px solid #e5ece9;
  color: #172033;
  font-size: 13px;
  font-weight: 850;
}

.generation-log header small {
  color: #94a3b8;
  font-weight: 800;
}

.generation-log ol {
  height: calc(100% - 40px);
  max-height: 156px;
  margin: 0;
  padding: 8px 14px 10px;
  display: grid;
  gap: 7px;
  overflow: auto;
  list-style: none;
}

.generation-log li {
  display: grid;
  grid-template-columns: 72px minmax(0, 1fr);
  gap: 10px;
  align-items: start;
  color: #53656a;
  font-size: 12px;
  line-height: 1.5;
}

.generation-log time {
  color: #0e9f6e;
  font-weight: 800;
}

.empty-state {
  height: 100%;
  min-height: 220px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 10px;
  padding: 28px;
  color: #64748b;
  text-align: center;
}

.empty-state strong {
  color: #172033;
  font-size: 18px;
}

.empty-state span {
  max-width: 360px;
  font-size: 14px;
  line-height: 1.6;
}

.empty-state.error {
  color: #b42318;
  background: #fff7f6;
}

.empty-state.compact {
  min-height: 360px;
  border: 1px dashed #d6e6df;
  border-radius: 8px;
  background: #fbfefd;
}

.slide-strip {
  display: flex;
  gap: 8px;
  overflow-x: auto;
  overscroll-behavior-inline: contain;
  padding: 12px 2px 2px;
}

.slide-chip {
  width: 92px;
  min-width: 92px;
  height: 58px;
  padding: 8px;
  border: 1px solid #e2ece7;
  border-radius: 8px;
  background: #ffffff;
  color: #53656a;
  text-align: left;
  cursor: pointer;
}

.slide-chip.active {
  border-color: rgba(33, 185, 120, 0.52);
  background: #f1fbf7;
  color: #0e9f6e;
}

.slide-chip span,
.slide-chip small {
  display: block;
}

.slide-chip span {
  font-size: 13px;
  font-weight: 850;
}

.slide-chip small {
  margin-top: 4px;
  overflow: hidden;
  color: inherit;
  font-size: 11px;
  line-height: 1.25;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.spin-icon {
  animation: spin 0.9s linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

@media (max-width: 980px) {
  .ppt-native-page {
    padding: 20px;
  }

  .ppt-header,
  .content-grid,
  .content-grid.history-mode {
    grid-template-columns: 1fr;
  }

  .ppt-header {
    display: block;
  }

  .ppt-header-metrics {
    margin-top: 16px;
  }

  .preview-tool {
    min-height: 0;
  }
}

@media (max-width: 640px) {
  .ppt-native-page {
    padding: 16px;
  }

  .ppt-native-page.standalone {
    padding-top: 72px;
  }

  .ppt-header h1 {
    font-size: 26px;
  }

  .ppt-tabs,
  .ppt-tabs button,
  .creator-actions,
  .preview-head,
  .page-actions {
    width: 100%;
  }

  .ppt-tabs button,
  .creator-actions,
  .preview-head,
  .page-actions {
    flex: 1;
  }

  .preview-head,
  .creator-actions {
    flex-direction: column;
    align-items: stretch;
  }

  .preview-stage {
    min-height: 240px;
  }

  .generation-panel {
    min-height: 240px;
    display: flex;
    flex-direction: column;
    gap: 12px;
    padding: 18px;
    overflow: auto;
  }

  .generation-agents {
    display: grid;
    grid-template-columns: 1fr;
  }

  .generation-hero strong {
    font-size: 20px;
  }

  .generation-log ol {
    max-height: 150px;
  }
}
</style>
