<template>
  <div class="ppt-task-page">
    <header ref="toolbarRef" class="task-toolbar" :style="toolbarStyle">
      <div class="task-heading">
        <span class="brand-mark"><Presentation :size="20" aria-hidden="true" /></span>
        <div>
          <span class="eyebrow">OhMyPPT · 岐小智协同任务</span>
          <h1>{{ topic }}</h1>
        </div>
      </div>

      <div class="toolbar-actions">
        <span class="status-chip" :class="statusClass">
          <Loader2 v-if="isRunning" :size="15" class="spin-icon" aria-hidden="true" />
          <CircleCheck v-else-if="taskStatus === 'complete'" :size="15" aria-hidden="true" />
          <CircleAlert v-else :size="15" aria-hidden="true" />
          {{ statusLabel }}
        </span>
        <button type="button" title="PPT 历史记录" @click="openHistory">
          <History :size="18" aria-hidden="true" />
          <span>历史记录</span>
        </button>
        <button v-if="pages.length" type="button" :title="isFullscreen ? '退出全屏' : '全屏展示'" @click="toggleFullscreen">
          <Minimize2 v-if="isFullscreen" :size="18" aria-hidden="true" />
          <Maximize2 v-else :size="18" aria-hidden="true" />
          <span>{{ isFullscreen ? '退出全屏' : '全屏展示' }}</span>
        </button>
        <button type="button" title="关闭任务页" @click="closeTaskPage">
          <X :size="19" aria-hidden="true" />
        </button>
      </div>
    </header>

    <section v-if="isPendingTask" class="center-state">
      <Loader2 :size="34" class="spin-icon" aria-hidden="true" />
      <strong>正在创建 PPT 任务</strong>
      <span>等待主系统返回持久化任务编号</span>
    </section>

    <section v-else-if="isFailed && !pages.length" class="center-state error-state">
      <CircleAlert :size="38" aria-hidden="true" />
      <strong>PPT 生成失败</strong>
      <span>{{ errorMessage }}</span>
      <div class="state-actions">
        <button type="button" class="primary-button" :disabled="retrying" @click="retryGeneration">
          <Loader2 v-if="retrying" :size="17" class="spin-icon" aria-hidden="true" />
          <RotateCcw v-else :size="17" aria-hidden="true" />
          <span>{{ retrying ? '正在重试' : '重新生成' }}</span>
        </button>
        <button type="button" @click="loadTask">
          <RefreshCw :size="17" aria-hidden="true" />
          <span>刷新状态</span>
        </button>
      </div>
    </section>

    <main v-else class="task-workspace">
      <section class="preview-column">
        <div v-if="isRunning" class="progress-band">
          <div class="progress-copy">
            <div>
              <Loader2 :size="18" class="spin-icon" aria-hidden="true" />
              <strong>{{ currentMessage }}</strong>
            </div>
            <span>{{ progress }}%</span>
          </div>
          <div class="progress-track" role="progressbar" :aria-valuenow="progress" aria-valuemin="0" aria-valuemax="100">
            <span :style="{ width: `${progress}%` }"></span>
          </div>
        </div>

        <div
          ref="stageRef"
          class="slide-stage"
          :class="{ 'pseudo-fullscreen': isPseudoFullscreen }"
          tabindex="0"
          @wheel="handleStageWheel"
        >
          <iframe
            v-if="activePage?.html"
            ref="frameRef"
            class="slide-frame"
            title="OhMyPPT 幻灯片预览"
            sandbox="allow-scripts"
            :srcdoc="frameSrcdoc"
          />
          <div v-else class="generation-stage">
            <Loader2 :size="36" class="spin-icon" aria-hidden="true" />
            <strong>{{ currentStageLabel }}</strong>
            <span>{{ currentMessage }}</span>
          </div>

          <div v-if="pages.length" class="stage-overlay">
            <span>{{ activePageIndex + 1 }} / {{ pages.length }}</span>
            <button type="button" :title="isFullscreen ? '退出全屏' : '全屏展示'" @click.stop="toggleFullscreen">
              <Minimize2 v-if="isFullscreen" :size="18" aria-hidden="true" />
              <Maximize2 v-else :size="18" aria-hidden="true" />
            </button>
          </div>
        </div>

        <div v-if="pages.length" class="deck-navigation">
          <button type="button" title="上一页" :disabled="activePageIndex <= 0" @click="goPage(-1)">
            <ChevronLeft :size="19" aria-hidden="true" />
          </button>
          <div class="page-strip" @wheel="handleStripWheel">
            <button
              v-for="(page, index) in pages"
              :key="`${page.pageNumber || index}-${page.title || ''}`"
              type="button"
              :class="{ active: index === activePageIndex }"
              @click="activePageIndex = index"
            >
              <span>{{ index + 1 }}</span>
              <small>{{ page.title || `第 ${index + 1} 页` }}</small>
            </button>
          </div>
          <button type="button" title="下一页" :disabled="activePageIndex >= pages.length - 1" @click="goPage(1)">
            <ChevronRight :size="19" aria-hidden="true" />
          </button>
        </div>
      </section>

      <aside class="detail-panel">
        <header class="detail-heading">
          <div>
            <span>任务追踪</span>
            <h2>详细信息</h2>
          </div>
          <button type="button" title="刷新状态" :disabled="loading" @click="loadTask">
            <RefreshCw :size="17" :class="{ 'spin-icon': loading }" aria-hidden="true" />
          </button>
        </header>

        <dl class="task-facts">
          <div><dt>生成引擎</dt><dd>{{ engineLabel }}</dd></div>
          <div><dt>运行模型</dt><dd>{{ modelLabel }}</dd></div>
          <div><dt>画像版本</dt><dd>{{ profileReportId ? `#${profileReportId}` : '绑定中' }}</dd></div>
          <div><dt>任务编号</dt><dd :title="taskId">{{ compactTaskId }}</dd></div>
        </dl>

        <section v-if="agentRuns.length" class="detail-section">
          <h3>智能体执行</h3>
          <ol class="agent-list">
            <li v-for="agent in agentRuns" :key="agent.id || agent.name" :class="agentStatusClass(agent.status)">
              <span class="agent-dot"></span>
              <div>
                <strong>{{ agent.name || agent.id }}</strong>
                <small>{{ agent.detail || agent.status }}</small>
              </div>
            </li>
          </ol>
        </section>

        <section class="detail-section">
          <h3>执行记录</h3>
          <ol v-if="logs.length" class="log-list">
            <li v-for="(log, index) in logs" :key="`${log.time || ''}-${log.stage || ''}-${index}`">
              <time>{{ formatLogTime(log.time) }}</time>
              <div>
                <strong>{{ stageLabel(log.stage) }}</strong>
                <span>{{ log.message || '状态已更新' }}</span>
              </div>
              <b>{{ Number(log.progress || 0) }}%</b>
            </li>
          </ol>
          <div v-else class="empty-detail">等待首条执行记录</div>
        </section>

        <section v-if="latestRun" class="detail-section review-section">
          <h3>Harness 审核</h3>
          <div class="review-row">
            <span>Root Agent</span>
            <strong>{{ latestRun.rootAgent || '岐小智' }}</strong>
          </div>
          <div class="review-row">
            <span>Skill / MCP</span>
            <strong>{{ latestRun.harness?.skillId || '--' }} · {{ latestRun.harness?.mcpTool || '--' }}</strong>
          </div>
          <div class="review-row">
            <span>质量与安全</span>
            <strong>{{ reviewLabel }}</strong>
          </div>
          <div class="review-row">
            <span>Run ID</span>
            <strong :title="latestRun.runId">{{ compactRunId }}</strong>
          </div>
        </section>

        <p v-if="pollError" class="poll-warning">{{ pollError }}</p>
      </aside>
    </main>
  </div>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  ChevronLeft,
  ChevronRight,
  CircleAlert,
  CircleCheck,
  History,
  Loader2,
  Maximize2,
  Minimize2,
  Presentation,
  RefreshCw,
  RotateCcw,
  X,
} from 'lucide-vue-next'
import { getXiaoZhiTask, startPptH5Generation } from '../services/api.js'

const STAGE_LABELS = {
  start: '任务启动',
  context: '读取学习上下文',
  prepare: '整理生成要求',
  knowledge_retrieval: '检索课程知识库',
  ohmyppt_health: '连接 OhMyPPT',
  ohmyppt_request: '生成 H5 幻灯片',
  ohmyppt_validate: '结构与安全校验',
  ohmyppt_complete: 'OhMyPPT 生成完成',
  quality_review: '质量审核',
  safety_review: '安全审核',
  complete: '任务完成',
  error: '生成异常',
}

const route = useRoute()
const router = useRouter()
const task = ref(null)
const orchestrationRuns = ref([])
const loading = ref(false)
const retrying = ref(false)
const pollError = ref('')
const activePageIndex = ref(0)
const toolbarRef = ref(null)
const stageRef = ref(null)
const frameRef = ref(null)
const isFullscreen = ref(false)
const isPseudoFullscreen = ref(false)
const toolbarSafeInset = ref({ left: 22, right: 22 })
let pollTimer = null
let wheelAccumulator = 0
let lastWheelTurnAt = 0
let assistantLayoutFrame = null
let assistantLayoutObserver = null

const taskId = computed(() => String(route.query.xzTask || route.query.taskId || '').trim())
const rawResult = computed(() => (task.value?.result && typeof task.value.result === 'object' ? task.value.result : {}))
const pptPayload = computed(() => resolvePptPayload(rawResult.value))
const pages = computed(() => (Array.isArray(pptPayload.value?.pages) ? pptPayload.value.pages : []))
const activePage = computed(() => pages.value[activePageIndex.value] || null)
const frameSrcdoc = computed(() => fitSlideHtml(activePage.value?.html || ''))
const taskStatus = computed(() => task.value?.status || (route.query.state === 'error' ? 'failed' : 'pending'))
const isRunning = computed(() => ['queued', 'running'].includes(taskStatus.value))
const isFailed = computed(() => taskStatus.value === 'failed' || route.query.state === 'error')
const isPendingTask = computed(() => !taskId.value && !isFailed.value)
const progress = computed(() => clampProgress(rawResult.value.progress ?? (taskStatus.value === 'complete' ? 100 : 5)))
const topic = computed(() => String(
  pptPayload.value?.title
    || rawResult.value.topic
    || route.query.topic
    || task.value?.title?.replace(/\s*·\s*PPT.*$/i, '')
    || 'PPT 生成任务',
))
const currentStage = computed(() => String(rawResult.value.currentStage || (taskStatus.value === 'complete' ? 'complete' : 'start')))
const currentStageLabel = computed(() => stageLabel(currentStage.value))
const currentMessage = computed(() => String(rawResult.value.message || (isRunning.value ? 'OhMyPPT 正在处理课件' : statusLabel.value)))
const statusLabel = computed(() => {
  if (taskStatus.value === 'complete') return '已完成'
  if (isFailed.value) return '生成失败'
  if (taskStatus.value === 'queued') return '排队中'
  if (taskStatus.value === 'running') return '生成中'
  return '任务创建中'
})
const statusClass = computed(() => ({
  complete: taskStatus.value === 'complete',
  failed: isFailed.value,
  running: isRunning.value || isPendingTask.value,
}))
const logs = computed(() => {
  const direct = Array.isArray(rawResult.value.logs) ? rawResult.value.logs : []
  if (direct.length) return direct.slice(-40)
  const events = pptPayload.value?.orchestration?.events
  return Array.isArray(events) ? events.slice(-40) : []
})
const agentRuns = computed(() => {
  const direct = Array.isArray(rawResult.value.agentRuns) ? rawResult.value.agentRuns : []
  if (direct.length) return direct
  const traced = pptPayload.value?.orchestration?.agentRuns
  return Array.isArray(traced) ? traced : []
})
const latestRun = computed(() => orchestrationRuns.value[0] || null)
const profileReportId = computed(() => Number(
  latestRun.value?.profileReportId
    || pptPayload.value?.harness?.profileReportId
    || pptPayload.value?.orchestration?.profileReportId
    || 0,
))
const engineLabel = computed(() => String(pptPayload.value?.engine?.id || rawResult.value.engine || 'ohmyppt-fastapi'))
const modelLabel = computed(() => String(
  pptPayload.value?.engine?.model
    || pptPayload.value?.harness?.modelRuntime?.model
    || '读取中',
))
const errorMessage = computed(() => String(
  task.value?.error
    || rawResult.value.qualityError
    || rawResult.value.error?.details
    || route.query.message
    || '生成服务未返回可用结果，请查看详细记录后重试。',
))
const compactTaskId = computed(() => compactId(taskId.value))
const compactRunId = computed(() => compactId(latestRun.value?.runId || ''))
const reviewLabel = computed(() => {
  const review = latestRun.value?.review || pptPayload.value?.orchestration?.review || {}
  if (review.passed === true) return '已通过'
  if (review.passed === false) return '未通过'
  return isRunning.value ? '审核中' : '待核验'
})
const toolbarStyle = computed(() => ({
  '--toolbar-safe-left': `${toolbarSafeInset.value.left}px`,
  '--toolbar-safe-right': `${toolbarSafeInset.value.right}px`,
}))

watch(taskId, () => {
  stopPolling()
  task.value = null
  orchestrationRuns.value = []
  if (taskId.value) loadTask()
}, { immediate: true })

watch(() => pages.value.length, (length) => {
  if (!length) activePageIndex.value = 0
  else if (activePageIndex.value >= length) activePageIndex.value = length - 1
})

watch(activePageIndex, () => nextTick(() => stageRef.value?.focus?.({ preventScroll: true })))

onMounted(() => {
  notifyParentWindowReady()
  window.addEventListener('message', handleFrameMessage)
  document.addEventListener('keydown', handleKeydown)
  document.addEventListener('fullscreenchange', handleFullscreenChange)
  window.addEventListener('resize', scheduleAssistantSafeInset)
  assistantLayoutObserver = new MutationObserver(scheduleAssistantSafeInset)
  assistantLayoutObserver.observe(document.body, {
    subtree: true,
    childList: true,
    attributes: true,
    attributeFilter: ['class', 'style'],
  })
  nextTick(scheduleAssistantSafeInset)
})

onBeforeUnmount(() => {
  stopPolling()
  exitPseudoFullscreen()
  window.removeEventListener('message', handleFrameMessage)
  document.removeEventListener('keydown', handleKeydown)
  document.removeEventListener('fullscreenchange', handleFullscreenChange)
  window.removeEventListener('resize', scheduleAssistantSafeInset)
  assistantLayoutObserver?.disconnect()
  assistantLayoutObserver = null
  if (assistantLayoutFrame) window.cancelAnimationFrame(assistantLayoutFrame)
  assistantLayoutFrame = null
})

function resolvePptPayload(result) {
  const topPpt = result?.ppt && typeof result.ppt === 'object' ? result.ppt : {}
  const nestedPpt = topPpt?.ppt && typeof topPpt.ppt === 'object' ? topPpt.ppt : {}
  return [nestedPpt, topPpt, result].find((item) => Array.isArray(item?.pages)) || topPpt || result || {}
}

function notifyParentWindowReady() {
  if (!window.opener || window.opener.closed) return
  try {
    window.opener.postMessage({
      type: 'ppt-generation-window-ready',
      sessionId: String(route.params.sessionId || ''),
    }, window.location.origin)
  } catch {
    // The task page remains fully usable when the opener has already been isolated.
  }
}

async function loadTask() {
  if (!taskId.value || loading.value) return
  loading.value = true
  try {
    const response = await getXiaoZhiTask(taskId.value)
    const nextTask = response?.data?.task
    if (!nextTask) throw new Error('后端未返回任务数据')
    task.value = nextTask
    orchestrationRuns.value = Array.isArray(response?.data?.orchestrationRuns) ? response.data.orchestrationRuns : []
    pollError.value = ''
    if (['queued', 'running'].includes(nextTask.status)) schedulePoll(1200)
    else stopPolling()
  } catch (error) {
    pollError.value = error?.response?.data?.msg || error?.message || '任务状态读取失败'
    schedulePoll(3000)
  } finally {
    loading.value = false
  }
}

function schedulePoll(delay) {
  stopPolling()
  pollTimer = window.setTimeout(loadTask, delay)
}

function stopPolling() {
  if (pollTimer) window.clearTimeout(pollTimer)
  pollTimer = null
}

async function retryGeneration() {
  if (retrying.value) return
  retrying.value = true
  const sessionId = `ppt_${Date.now().toString(36)}_${Math.random().toString(36).slice(2, 8)}`
  try {
    const response = await startPptH5Generation({
      sessionId,
      topic: topic.value,
      userMessage: String(task.value?.prompt || route.query.prompt || `生成一份关于“${topic.value}”的学习 PPT。`),
      pageCount: Math.max(1, Math.min(20, Number(route.query.pageCount || pptPayload.value?.pages?.length || 6))),
      styleName: '岐黄智境浅绿平台风',
      styleDescription: '白底浅绿、干净明亮、模块化教育科技风。',
    })
    const nextTask = response?.data?.task || response?.task
    if (!nextTask?.taskId) throw new Error('后端没有返回新的 PPT 任务编号')
    await router.replace({
      name: 'ppt-generating',
      params: { sessionId: nextTask.result?.sessionId || sessionId },
      query: {
        xzTask: nextTask.taskId,
        topic: topic.value,
        pageCount: route.query.pageCount || pptPayload.value?.pages?.length || 6,
        ...(route.query.cacheKey ? { cacheKey: route.query.cacheKey } : {}),
      },
    })
  } catch (error) {
    pollError.value = error?.response?.data?.msg || error?.response?.data?.error || error?.message || '重试失败'
  } finally {
    retrying.value = false
  }
}

function openHistory() {
  router.push({ name: 'personalized-resource-ppt', query: { tab: 'history' } })
}

function closeTaskPage() {
  window.close()
  window.setTimeout(() => {
    if (!window.closed) router.push('/personalized-resources/ppt?tab=history')
  }, 80)
}

async function toggleFullscreen() {
  const stage = stageRef.value
  if (!stage) return
  if (isPseudoFullscreen.value) {
    exitPseudoFullscreen()
    return
  }
  if (document.fullscreenElement === stage) {
    await document.exitFullscreen?.()
    return
  }
  if (typeof stage.requestFullscreen === 'function') {
    try {
      await stage.requestFullscreen()
      return
    } catch {
      // Embedded browsers may expose the API but reject it; use the page-level fallback.
    }
  }
  enterPseudoFullscreen()
}

function handleFullscreenChange() {
  isFullscreen.value = isPseudoFullscreen.value || document.fullscreenElement === stageRef.value
}

function enterPseudoFullscreen() {
  isPseudoFullscreen.value = true
  isFullscreen.value = true
  document.documentElement.classList.add('ppt-pseudo-fullscreen-active')
  document.body.classList.add('ppt-pseudo-fullscreen-active')
  nextTick(() => stageRef.value?.focus?.({ preventScroll: true }))
}

function exitPseudoFullscreen() {
  if (!isPseudoFullscreen.value && !document.documentElement.classList.contains('ppt-pseudo-fullscreen-active')) return
  isPseudoFullscreen.value = false
  isFullscreen.value = document.fullscreenElement === stageRef.value
  document.documentElement.classList.remove('ppt-pseudo-fullscreen-active')
  document.body.classList.remove('ppt-pseudo-fullscreen-active')
}

function scheduleAssistantSafeInset() {
  if (assistantLayoutFrame) window.cancelAnimationFrame(assistantLayoutFrame)
  assistantLayoutFrame = window.requestAnimationFrame(updateAssistantSafeInset)
}

function updateAssistantSafeInset() {
  assistantLayoutFrame = null
  const toolbar = toolbarRef.value
  const assistant = document.querySelector('.xiaozhi-float')
  const viewportWidth = window.innerWidth
  const baseInset = viewportWidth <= 760 ? 12 : 22
  let left = baseInset
  let right = baseInset

  if (!toolbar || !assistant) {
    if (toolbarSafeInset.value.left !== left || toolbarSafeInset.value.right !== right) {
      toolbarSafeInset.value = { left, right }
    }
    return
  }

  const toolbarRect = toolbar.getBoundingClientRect()
  const obstacles = [assistant, assistant.querySelector('.xiaozhi-window')].filter(Boolean)
  obstacles.forEach((element) => {
    const rect = element.getBoundingClientRect()
    const intersectsToolbar = rect.width > 0
      && rect.height > 0
      && rect.right > 0
      && rect.left < viewportWidth
      && rect.bottom > toolbarRect.top
      && rect.top < toolbarRect.bottom
    if (!intersectsToolbar) return

    const gap = 12
    if (rect.left + (rect.width / 2) <= viewportWidth / 2) {
      left = Math.max(left, Math.ceil(rect.right + gap))
    } else {
      right = Math.max(right, Math.ceil(viewportWidth - rect.left + gap))
    }
  })

  const maxInset = Math.max(baseInset, viewportWidth - 320)
  const nextLeft = Math.min(left, maxInset)
  const nextRight = Math.min(right, maxInset)
  if (toolbarSafeInset.value.left !== nextLeft || toolbarSafeInset.value.right !== nextRight) {
    toolbarSafeInset.value = { left: nextLeft, right: nextRight }
  }
}

function goPage(step) {
  if (!pages.value.length) return
  activePageIndex.value = Math.max(0, Math.min(pages.value.length - 1, activePageIndex.value + step))
}

function turnFromWheel(delta) {
  if (!pages.value.length || Math.abs(delta) < 3) return
  wheelAccumulator += delta
  const now = Date.now()
  if (Math.abs(wheelAccumulator) < 65 || now - lastWheelTurnAt < 260) return
  const direction = wheelAccumulator > 0 ? 1 : -1
  wheelAccumulator = 0
  lastWheelTurnAt = now
  goPage(direction)
}

function handleStageWheel(event) {
  if (!pages.value.length || event.ctrlKey) return
  event.preventDefault()
  turnFromWheel(Number(event.deltaY || event.deltaX || 0))
}

function handleStripWheel(event) {
  const strip = event.currentTarget
  if (!strip || strip.scrollWidth <= strip.clientWidth) return
  event.preventDefault()
  strip.scrollLeft += Number(event.deltaY || event.deltaX || 0)
}

function handleFrameMessage(event) {
  if (event.source !== frameRef.value?.contentWindow || !event.data || typeof event.data !== 'object') return
  if (event.data.type === 'ohmyppt:click') goPage(Number(event.data.direction) < 0 ? -1 : 1)
  if (event.data.type === 'ohmyppt:wheel') turnFromWheel(Number(event.data.deltaY || event.data.deltaX || 0))
  if (event.data.type === 'ohmyppt:key') goPage(Number(event.data.direction) < 0 ? -1 : 1)
  if (event.data.type === 'ohmyppt:exit-fullscreen') {
    if (isPseudoFullscreen.value) exitPseudoFullscreen()
    else if (document.fullscreenElement === stageRef.value) document.exitFullscreen?.()
  }
}

function handleKeydown(event) {
  if (!pages.value.length) return
  if (event.key === 'Escape' && isPseudoFullscreen.value) {
    event.preventDefault()
    exitPseudoFullscreen()
    return
  }
  if (['ArrowRight', 'PageDown', ' ', 'Enter'].includes(event.key)) {
    event.preventDefault()
    goPage(1)
  }
  if (['ArrowLeft', 'PageUp', 'Backspace'].includes(event.key)) {
    event.preventDefault()
    goPage(-1)
  }
}

function fitSlideHtml(html) {
  if (!html) return ''
  const fitStyle = `<style>
html,body{width:100%;height:100%;margin:0;overflow:hidden;background:#f4faf9!important}
body{display:flex!important;align-items:center!important;justify-content:center!important}
.slide.ppt-page-root{flex:0 0 auto!important;transform:scale(var(--ppt-preview-scale,1))!important;transform-origin:center center!important}
</style>`
  const bridgeScript = `<script>(()=>{
const send=(type,payload={})=>parent.postMessage({type,...payload},'*');
const fit=()=>{
  const root=document.querySelector('.slide.ppt-page-root');
  if(!root)return;
  const width=Math.max(1,root.offsetWidth||1600);
  const height=Math.max(1,root.offsetHeight||900);
  const scale=Math.min(window.innerWidth/width,window.innerHeight/height);
  root.style.setProperty('--ppt-preview-scale',String(Math.max(.05,scale)));
};
window.addEventListener('resize',fit);
requestAnimationFrame(fit);
document.addEventListener('wheel',(event)=>send('ohmyppt:wheel',{deltaY:event.deltaY,deltaX:event.deltaX}),{passive:true});
document.addEventListener('click',(event)=>{
  const pending=document.querySelectorAll('[data-anim-trigger="click"]:not(.ppt-anim-in)').length;
  if(pending===0) send('ohmyppt:click',{direction:event.clientX<window.innerWidth*.33?-1:1});
});
document.addEventListener('keydown',(event)=>{
  const forward=['ArrowRight','PageDown',' ','Enter'];
  const backward=['ArrowLeft','PageUp','Backspace'];
  if(event.key==='Escape')send('ohmyppt:exit-fullscreen');
  if(forward.includes(event.key)) send('ohmyppt:key',{direction:1});
  if(backward.includes(event.key)) send('ohmyppt:key',{direction:-1});
});
})()<` + `/script>`
  let output = html.includes('</head>') ? html.replace('</head>', `${fitStyle}</head>`) : `${fitStyle}${html}`
  output = output.includes('</body>') ? output.replace('</body>', `${bridgeScript}</body>`) : `${output}${bridgeScript}`
  return output
}

function clampProgress(value) {
  const number = Number(value)
  return Number.isFinite(number) ? Math.max(0, Math.min(100, Math.round(number))) : 0
}

function stageLabel(stage) {
  const key = String(stage || '').trim()
  return STAGE_LABELS[key] || key || '任务执行'
}

function agentStatusClass(status) {
  const value = String(status || '').toLowerCase()
  if (['complete', 'done'].includes(value)) return 'complete'
  if (['failed', 'error'].includes(value)) return 'failed'
  return value === 'running' ? 'running' : 'queued'
}

function formatLogTime(value) {
  const date = new Date(value || '')
  if (!Number.isFinite(date.getTime())) return '--:--'
  return new Intl.DateTimeFormat('zh-CN', {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: false,
  }).format(date)
}

function compactId(value) {
  const text = String(value || '')
  if (!text) return '--'
  return text.length > 22 ? `${text.slice(0, 10)}...${text.slice(-8)}` : text
}
</script>

<style scoped>
.ppt-task-page {
  min-height: 100vh;
  overflow-x: hidden;
  background: #f5faf7;
  color: #1f2937;
  letter-spacing: 0;
}

.task-toolbar {
  position: sticky;
  top: 0;
  z-index: 30;
  min-height: 72px;
  padding: 12px var(--toolbar-safe-right, 22px) 12px var(--toolbar-safe-left, 22px);
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 20px;
  border-bottom: 1px solid #dcebe3;
  background: rgba(255, 255, 255, 0.96);
  backdrop-filter: blur(14px);
}

.task-heading,
.toolbar-actions,
.progress-copy,
.progress-copy > div,
.detail-heading,
.deck-navigation,
.stage-overlay,
.state-actions {
  display: flex;
  align-items: center;
}

.task-heading {
  min-width: 0;
  gap: 12px;
}

.brand-mark {
  width: 42px;
  height: 42px;
  flex: 0 0 42px;
  display: grid;
  place-items: center;
  border-radius: 8px;
  background: #21b978;
  color: #fff;
}

.task-heading > div {
  min-width: 0;
}

.eyebrow {
  display: block;
  color: #0e9f6e;
  font-size: 12px;
  font-weight: 800;
}

h1,
h2,
h3,
p {
  margin: 0;
}

h1 {
  max-width: min(52vw, 760px);
  margin-top: 3px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 19px;
  line-height: 1.3;
}

.toolbar-actions {
  flex: 0 0 auto;
  gap: 8px;
}

button,
.status-chip {
  min-height: 38px;
  border: 1px solid #d7e8df;
  border-radius: 7px;
  background: #fff;
  color: #33443c;
  font: inherit;
  font-size: 13px;
  font-weight: 750;
}

button {
  padding: 0 12px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 7px;
  cursor: pointer;
}

button:hover:not(:disabled) {
  border-color: #8bd8b5;
  background: #effaf5;
  color: #087a54;
}

button:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}

.status-chip {
  padding: 0 11px;
  display: inline-flex;
  align-items: center;
  gap: 6px;
}

.status-chip.running {
  border-color: #b8e9d2;
  background: #edfaf4;
  color: #087a54;
}

.status-chip.complete {
  border-color: #9ed9ba;
  background: #e6f7ee;
  color: #087244;
}

.status-chip.failed {
  border-color: #f1c4c4;
  background: #fff1f1;
  color: #b42318;
}

.task-workspace {
  width: min(1780px, 100%);
  min-height: calc(100vh - 72px);
  margin: 0 auto;
  padding: 18px 22px 28px;
  display: grid;
  grid-template-columns: minmax(0, 1fr) 350px;
  gap: 18px;
}

.preview-column {
  min-width: 0;
}

.progress-band {
  margin-bottom: 12px;
  padding: 13px 15px;
  border: 1px solid #d9ebe2;
  border-radius: 8px;
  background: #fff;
}

.progress-copy {
  justify-content: space-between;
  gap: 16px;
  font-size: 13px;
}

.progress-copy > div {
  min-width: 0;
  gap: 8px;
}

.progress-copy strong {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.progress-copy > span {
  color: #087a54;
  font-weight: 850;
}

.progress-track {
  height: 6px;
  margin-top: 10px;
  overflow: hidden;
  border-radius: 3px;
  background: #e9f2ed;
}

.progress-track span {
  display: block;
  height: 100%;
  border-radius: inherit;
  background: #21b978;
  transition: width 0.35s ease;
}

.slide-stage {
  position: relative;
  width: 100%;
  aspect-ratio: 16 / 9;
  min-height: 320px;
  overflow: hidden;
  border: 1px solid #cadbd2;
  border-radius: 8px;
  background: #17211d;
  box-shadow: 0 16px 36px rgba(35, 77, 59, 0.12);
  outline: none;
}

.slide-stage:fullscreen {
  width: 100vw;
  height: 100vh;
  aspect-ratio: auto;
  border: 0;
  border-radius: 0;
  background: #101713;
}

.slide-stage.pseudo-fullscreen {
  position: fixed;
  inset: 0;
  z-index: 12000;
  width: 100vw;
  height: 100vh;
  min-height: 0;
  aspect-ratio: auto;
  border: 0;
  border-radius: 0;
  background: #101713;
}

:global(html.ppt-pseudo-fullscreen-active),
:global(body.ppt-pseudo-fullscreen-active) {
  overflow: hidden !important;
}

.slide-frame {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  border: 0;
  background: #f4faf9;
}

.generation-stage,
.center-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  text-align: center;
}

.generation-stage {
  position: absolute;
  inset: 0;
  gap: 12px;
  padding: 28px;
  background: #f4faf7;
  color: #087a54;
}

.generation-stage strong {
  font-size: 18px;
}

.generation-stage span {
  max-width: 620px;
  color: #64736b;
  font-size: 14px;
}

.stage-overlay {
  position: absolute;
  z-index: 8;
  top: 12px;
  right: 12px;
  gap: 7px;
  pointer-events: none;
}

.stage-overlay span,
.stage-overlay button {
  height: 34px;
  min-height: 34px;
  border: 1px solid rgba(255, 255, 255, 0.35);
  background: rgba(15, 31, 24, 0.78);
  color: #fff;
  backdrop-filter: blur(8px);
}

.stage-overlay span {
  padding: 0 10px;
  display: inline-flex;
  align-items: center;
  border-radius: 6px;
  font-size: 12px;
  font-weight: 800;
}

.stage-overlay button {
  width: 34px;
  padding: 0;
  pointer-events: auto;
}

.deck-navigation {
  margin-top: 12px;
  gap: 9px;
}

.deck-navigation > button {
  width: 42px;
  flex: 0 0 42px;
  padding: 0;
}

.page-strip {
  min-width: 0;
  flex: 1;
  display: flex;
  gap: 8px;
  overflow-x: auto;
  scrollbar-width: thin;
  scroll-behavior: smooth;
}

.page-strip button {
  width: 158px;
  min-width: 158px;
  height: 48px;
  padding: 0 10px;
  justify-content: flex-start;
  text-align: left;
}

.page-strip button.active {
  border-color: #21b978;
  background: #eaf8f1;
  color: #087a54;
}

.page-strip span {
  width: 25px;
  height: 25px;
  flex: 0 0 25px;
  display: grid;
  place-items: center;
  border-radius: 5px;
  background: #edf3ef;
  font-size: 11px;
  font-weight: 850;
}

.page-strip small {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.detail-panel {
  min-width: 0;
  max-height: calc(100vh - 112px);
  overflow-y: auto;
  border: 1px solid #d9e7e0;
  border-radius: 8px;
  background: #fff;
  scrollbar-gutter: stable;
}

.detail-heading {
  position: sticky;
  top: 0;
  z-index: 3;
  justify-content: space-between;
  gap: 12px;
  padding: 15px 16px;
  border-bottom: 1px solid #e4eee9;
  background: rgba(255, 255, 255, 0.96);
}

.detail-heading span {
  color: #0e9f6e;
  font-size: 11px;
  font-weight: 850;
}

.detail-heading h2 {
  margin-top: 2px;
  font-size: 17px;
}

.detail-heading button {
  width: 36px;
  min-height: 36px;
  padding: 0;
}

.task-facts {
  margin: 0;
  padding: 6px 16px;
}

.task-facts > div,
.review-row {
  min-height: 42px;
  display: grid;
  grid-template-columns: 92px minmax(0, 1fr);
  align-items: center;
  gap: 10px;
  border-bottom: 1px solid #edf2ef;
}

.task-facts dt,
.review-row span {
  color: #718078;
  font-size: 12px;
}

.task-facts dd,
.review-row strong {
  margin: 0;
  min-width: 0;
  overflow-wrap: anywhere;
  color: #2d3c35;
  font-size: 12px;
  font-weight: 780;
}

.detail-section {
  padding: 15px 16px;
  border-top: 1px solid #e4eee9;
}

.detail-section h3 {
  margin-bottom: 12px;
  font-size: 13px;
}

.agent-list,
.log-list {
  margin: 0;
  padding: 0;
  list-style: none;
}

.agent-list {
  display: grid;
  gap: 11px;
}

.agent-list li {
  display: grid;
  grid-template-columns: 10px minmax(0, 1fr);
  gap: 9px;
}

.agent-dot {
  width: 8px;
  height: 8px;
  margin-top: 5px;
  border-radius: 50%;
  background: #a7b6ae;
}

.agent-list li.running .agent-dot {
  background: #21b978;
  box-shadow: 0 0 0 4px rgba(33, 185, 120, 0.13);
}

.agent-list li.complete .agent-dot {
  background: #087a54;
}

.agent-list li.failed .agent-dot {
  background: #d92d20;
}

.agent-list strong,
.agent-list small {
  display: block;
}

.agent-list strong {
  font-size: 12px;
}

.agent-list small {
  margin-top: 3px;
  color: #718078;
  font-size: 11px;
  line-height: 1.45;
}

.log-list {
  display: grid;
  gap: 0;
}

.log-list li {
  padding: 9px 0;
  display: grid;
  grid-template-columns: 54px minmax(0, 1fr) 34px;
  gap: 8px;
  border-bottom: 1px solid #edf2ef;
}

.log-list time,
.log-list b {
  color: #829088;
  font-size: 10px;
  font-weight: 700;
}

.log-list b {
  text-align: right;
}

.log-list strong,
.log-list span {
  display: block;
}

.log-list strong {
  font-size: 11px;
}

.log-list span {
  margin-top: 2px;
  color: #66756d;
  font-size: 11px;
  line-height: 1.45;
}

.empty-detail {
  padding: 12px 0;
  color: #87958e;
  font-size: 12px;
  text-align: center;
}

.poll-warning {
  margin: 12px 16px 16px;
  padding: 10px 12px;
  border: 1px solid #f2d6a8;
  border-radius: 7px;
  background: #fff8eb;
  color: #8a4b12;
  font-size: 12px;
  line-height: 1.5;
}

.center-state {
  min-height: calc(100vh - 72px);
  gap: 12px;
  padding: 32px;
  color: #0e8a60;
}

.center-state strong {
  font-size: 20px;
}

.center-state > span {
  max-width: 700px;
  color: #64736b;
  line-height: 1.65;
}

.error-state {
  color: #b42318;
}

.state-actions {
  margin-top: 8px;
  gap: 9px;
}

.primary-button {
  border-color: #21b978;
  background: #21b978;
  color: #fff;
}

.spin-icon {
  animation: spin 0.9s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

@media (max-width: 1080px) {
  .task-workspace {
    grid-template-columns: 1fr;
  }

  .detail-panel {
    max-height: none;
  }
}

@media (max-width: 760px) {
  .task-toolbar {
    align-items: flex-start;
    padding: 10px var(--toolbar-safe-right, 12px) 10px var(--toolbar-safe-left, 12px);
  }

  .toolbar-actions {
    flex-wrap: wrap;
    justify-content: flex-end;
  }

  .toolbar-actions button span,
  .toolbar-actions .status-chip {
    display: none;
  }

  .toolbar-actions button {
    width: 38px;
    padding: 0;
  }

  h1 {
    max-width: 46vw;
    font-size: 15px;
  }

  .eyebrow {
    font-size: 10px;
  }

  .task-workspace {
    padding: 12px;
    gap: 12px;
  }

  .slide-stage {
    min-height: 0;
  }

  .page-strip button {
    width: 126px;
    min-width: 126px;
  }
}
</style>
