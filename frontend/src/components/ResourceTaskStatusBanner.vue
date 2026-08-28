<template>
  <Transition name="motion-toast">
    <aside
      v-if="showTaskBanner"
      class="xz-workflow-card"
      :class="[status, { embedded }]"
      role="status"
      aria-live="polite"
    >
      <header class="card-head">
        <div class="brand-mark" aria-hidden="true">
          <Network :size="17" />
        </div>
        <div class="head-copy">
          <span>岐小智 · 多智能体协同</span>
          <strong>{{ cardTitle }}</strong>
        </div>
        <span class="status-label"><i></i>{{ statusLabel }}</span>
        <button type="button" class="icon-button" title="收起进度" aria-label="收起进度" @click="dismissCard">
          <X :size="16" />
        </button>
      </header>

      <div class="current-run">
        <div class="agent-icon" aria-hidden="true">
          <LoaderCircle v-if="isActive" :size="17" class="spin" />
          <CircleCheck v-else-if="status === 'complete'" :size="17" />
          <CircleAlert v-else :size="17" />
        </div>
        <div>
          <span>{{ currentAgent }}</span>
          <p>{{ taskMessage }}</p>
        </div>
      </div>

      <ol class="stage-list" aria-label="多智能体协同阶段">
        <li v-for="(stage, index) in workflowStages" :key="stage.id" :class="stageState(index)">
          <span class="stage-node">
            <Check v-if="stageState(index) === 'done'" :size="12" />
            <span v-else>{{ index + 1 }}</span>
          </span>
          <small>{{ stage.label }}</small>
        </li>
      </ol>

      <div class="progress-row">
        <div class="progress-track" aria-hidden="true">
          <i :style="{ width: `${progress}%` }"></i>
        </div>
        <strong>{{ progress }}%</strong>
      </div>

      <footer v-if="weekSummary || canOpenTask || taskResultSummary || hasTaskAudit" class="card-foot">
        <span class="result-summary">{{ weekSummary || taskResultSummary }}</span>
        <div class="foot-actions">
          <button v-if="hasTaskAudit" type="button" class="view-button" :aria-expanded="auditExpanded" @click="auditExpanded = !auditExpanded">
            生成依据
            <ChevronUp v-if="auditExpanded" :size="15" />
            <ChevronDown v-else :size="15" />
          </button>
          <button v-if="canOpenTask" type="button" class="view-button" @click="goTaskRoute">
            {{ isLearningPath ? '查看学习路径' : '查看结果' }}
            <ArrowRight :size="15" />
          </button>
        </div>
      </footer>

      <section v-if="hasTaskAudit && auditExpanded" class="audit-drawer" aria-label="生成依据与审核信息">
        <dl>
          <div v-if="taskAudit.profile"><dt>画像</dt><dd>#{{ taskAudit.profile }}<template v-if="taskAudit.match !== null"> · 匹配 {{ taskAudit.match }}%</template></dd></div>
          <div v-if="taskAudit.agent"><dt>智能体</dt><dd>{{ taskAudit.agent }}</dd></div>
          <div v-if="taskAudit.skill"><dt>Skill</dt><dd>{{ taskAudit.skill }}</dd></div>
          <div v-if="taskAudit.quality"><dt>质量审核</dt><dd>{{ taskAudit.quality }}</dd></div>
          <div v-if="taskAudit.citations"><dt>知识依据</dt><dd>{{ taskAudit.citations }} 条</dd></div>
          <div v-if="taskAudit.strategy"><dt>生成策略</dt><dd>{{ taskAudit.strategy }}</dd></div>
        </dl>
        <p v-if="taskAudit.sourcePreview">来源：{{ taskAudit.sourcePreview }}</p>
      </section>

      <div v-if="showFeedbackActions" class="feedback-slot">
        <LearningFeedbackActions
          :task="task"
          :cache-key="String(route.query.cacheKey || '')"
          :route-path="route.fullPath"
          compact
        />
      </div>
    </aside>
  </Transition>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  ArrowRight,
  Check,
  ChevronDown,
  ChevronUp,
  CircleAlert,
  CircleCheck,
  LoaderCircle,
  Network,
  X,
} from 'lucide-vue-next'
import LearningFeedbackActions from './LearningFeedbackActions.vue'
import { getXiaoZhiStatus, getXiaoZhiTask } from '../services/api.js'
import {
  PROFILE_WORKFLOW_STAGES,
  XIAOZHI_ACTIVE_TASK_KEY,
  XIAOZHI_WORKFLOW_STATE_KEY,
  XIAOZHI_WORKFLOW_EVENT,
  learningPathProgress,
  profileProgress,
  profileStageIndex,
  workflowStatus,
} from '../utils/xiaozhiWorkflowProgress.js'

const props = defineProps({
  embedded: {
    type: Boolean,
    default: false,
  },
})

const embedded = props.embedded

const route = useRoute()
const router = useRouter()
const task = ref(null)
const trackedTaskId = ref('')
const streamState = ref(null)
const dismissedKey = ref('')
const auditExpanded = ref(false)
let pollingTimer = 0
let completeTimer = 0
const dismissedStorageKey = 'qihuang:xiaozhi-dismissed-workflow:v1'

const feedbackTaskTypes = new Set(['personalized_resources', 'question_bank', 'ppt', 'video', 'animation', 'mcu', 'smart_tutor'])
const routesWithInlineFeedback = new Set([
  'resource-detail',
  'mind-map',
  'personalized-resource-mind-map',
  'video-search',
  'personalized-resource-video-search',
  'personalized-resource-document',
  'smart-tutor',
])
const workflowStages = PROFILE_WORKFLOW_STAGES
const status = computed(() => workflowStatus(task.value?.status || streamState.value?.status))
const isActive = computed(() => ['queued', 'running'].includes(status.value))
const isLearningPath = computed(() => (
  String(task.value?.taskType || '') === 'learning_path'
  || String(streamState.value?.workflow || '') === 'learning-path'
))
const cardKey = computed(() => String(task.value?.taskId || streamState.value?.workflowId || ''))
const isImmersiveWorkbench = computed(() => String(route.path || '').startsWith('/personalized-resources/mcu-simulator/'))
const showTaskBanner = computed(() => (
  Boolean(task.value || streamState.value)
  && Boolean(cardKey.value)
  && dismissedKey.value !== cardKey.value
  && !isImmersiveWorkbench.value
  && !['/mind-map', '/document'].some(suffix => String(route.path || '').endsWith(suffix))
))
const showFeedbackActions = computed(() => (
  task.value?.status === 'complete'
  && feedbackTaskTypes.has(String(task.value?.taskType || task.value?.type || ''))
  && !routesWithInlineFeedback.has(String(route.name || ''))
))
const progress = computed(() => (
  task.value ? learningPathProgress(task.value) : profileProgress(streamState.value || {})
))
const activeStageIndex = computed(() => {
  if (isLearningPath.value) return 3
  if (task.value) return isLearningPath.value ? 3 : Math.min(3, Math.floor(progress.value / 26))
  return profileStageIndex(streamState.value?.stage, false)
})
const cardTitle = computed(() => {
  if (isLearningPath.value) return status.value === 'complete' ? '个性化学习路径已生成' : '正在生成个性化学习路径'
  if (task.value) return task.value.title || '正在生成个性化资源'
  return status.value === 'complete' ? '学习画像已完成' : '正在构建学习画像'
})
const currentAgent = computed(() => {
  if (status.value === 'failed') return '协同任务异常'
  if (isLearningPath.value) return status.value === 'complete' ? '学习路径 Agent · 已交付' : '学习路径 Agent · 逐周规划'
  if (task.value) return '资源生成 Agent · 协同执行'
  return [
    '学情诊断 Agent · 证据归纳',
    '知识检索 Agent · 依据匹配',
    '领域专家与审核 Agent · 交叉验证',
    '学习路径 Agent · 个性化规划',
  ][activeStageIndex.value]
})
const statusLabel = computed(() => ({
  queued: '排队中',
  running: '协同中',
  complete: '已完成',
  failed: '需处理',
})[status.value])
const taskMessage = computed(() => {
  if (task.value) {
    if (status.value === 'failed') return task.value.error || task.value.result?.message || '任务执行失败，请稍后重试。'
    return task.value.result?.message
      || (status.value === 'queued' ? '任务已进入队列，后台会持续跟进。' : '多个智能体正在协同处理当前任务。')
  }
  return streamState.value?.message || '正在汇总画像证据并进行多智能体分析。'
})
const weekSummary = computed(() => {
  if (!isLearningPath.value) return ''
  const result = task.value?.result || streamState.value || {}
  const completed = Math.max(0, Number(result.completedWeeks) || 0)
  const total = Math.max(1, Number(result.totalWeeks) || 6)
  return `路径进度 ${completed} / ${total} 周`
})
const canOpenTask = computed(() => (
  Boolean(task.value?.route || streamState.value?.route)
  && ['complete', 'failed'].includes(status.value)
  && route.name !== 'resource-detail'
))
const taskResultSummary = computed(() => {
  if (!task.value || isLearningPath.value) return ''
  if (status.value === 'failed') return '审核未通过或资源生成失败'
  if (isActive.value) return '生成与质量审核进行中'
  const result = task.value.result || {}
  const quality = result.qualityEvaluation || result.orchestration?.review || {}
  const sources = Array.isArray(result.knowledgeSources) ? result.knowledgeSources : []
  const parts = []
  if (Number(quality.score || 0)) parts.push(`质量 ${Number(quality.score)} / 100`)
  if (sources.length) parts.push(`知识引用 ${sources.length} 条`)
  return parts.join(' · ') || '任务已完成'
})
const taskAudit = computed(() => {
  const currentTask = task.value || {}
  const result = currentTask.result && typeof currentTask.result === 'object' ? currentTask.result : {}
  const focused = currentTask.focusedResource && typeof currentTask.focusedResource === 'object'
    ? currentTask.focusedResource
    : {}
  const selected = Object.keys(focused).length
    ? focused
    : (result.selectedResource && typeof result.selectedResource === 'object'
        ? result.selectedResource
        : (Array.isArray(result.workflow?.resources) ? result.workflow.resources[0] || {} : {}))
  const metadata = selected.metadata && typeof selected.metadata === 'object' ? selected.metadata : {}
  const runs = Array.isArray(currentTask.orchestrationRuns) ? currentTask.orchestrationRuns : []
  const orchestration = result.orchestration && typeof result.orchestration === 'object' ? result.orchestration : {}
  const run = runs.find(item => String(item?.runId || '') === String(metadata.runId || '')) || runs[0] || orchestration
  const agentRuns = Array.isArray(run.agentRuns) ? run.agentRuns : (Array.isArray(metadata.agentRuns) ? metadata.agentRuns : [])
  const specialist = agentRuns.find(item => String(item?.role || '') === 'specialist') || agentRuns.at(-1) || {}
  const quality = result.qualityEvaluation || selected.qualityEvaluation || metadata.qualityEvaluation || orchestration.review || {}
  const sources = result.knowledgeSources || selected.knowledgeSources || metadata.knowledgeSources || []
  const planner = metadata.planner && typeof metadata.planner === 'object' ? metadata.planner : {}
  const score = Number(quality.score)
  return {
    profile: metadata.profileReportId || orchestration.profileReportId || result.profileReportId || '',
    match: Number.isFinite(Number(selected.matchScore)) ? Number(selected.matchScore) : null,
    agent: specialist.name || specialist.id || metadata.workflowNode || result.agent || '',
    skill: run.harness?.skillId || metadata.skillId || '',
    quality: Number.isFinite(score) ? `${score} / 100` : (quality.passed === true ? '已通过' : quality.passed === false ? '未通过' : ''),
    citations: Array.isArray(sources) ? sources.length : 0,
    sourcePreview: Array.isArray(sources)
      ? sources.slice(0, 2).map(source => source.title || source.name || source.source).filter(Boolean).join('、')
      : '',
    strategy: planner.strategy || '',
  }
})
const hasTaskAudit = computed(() => Boolean(
  task.value
  && !isLearningPath.value
  && Object.values(taskAudit.value).some(value => value !== '' && value !== null && value !== 0),
))

watch(() => route.query.xzTask, (value) => {
  const id = String(value || '')
  if (id && id !== trackedTaskId.value) trackTaskId(id)
}, { immediate: true })

function stageState(index) {
  if (status.value === 'failed' && index === activeStageIndex.value) return 'failed'
  if (status.value === 'complete' || index < activeStageIndex.value) return 'done'
  if (index === activeStageIndex.value) return 'active'
  return 'waiting'
}

function rememberTaskId(taskId) {
  try {
    if (taskId) sessionStorage.setItem(XIAOZHI_ACTIVE_TASK_KEY, taskId)
    else sessionStorage.removeItem(XIAOZHI_ACTIVE_TASK_KEY)
  } catch {
    // Storage can be unavailable in privacy-restricted webviews.
  }
}

function restoredTaskId() {
  try {
    return String(sessionStorage.getItem(XIAOZHI_ACTIVE_TASK_KEY) || '')
  } catch {
    return ''
  }
}

function restoredWorkflowState() {
  try {
    const raw = sessionStorage.getItem(XIAOZHI_WORKFLOW_STATE_KEY)
    return raw ? JSON.parse(raw) : null
  } catch {
    return null
  }
}

function rememberDismissedKey(value) {
  try {
    if (value) sessionStorage.setItem(dismissedStorageKey, value)
    else sessionStorage.removeItem(dismissedStorageKey)
  } catch {
    // Storage can be unavailable in privacy-restricted webviews.
  }
}

function restoredDismissedKey() {
  try {
    return String(sessionStorage.getItem(dismissedStorageKey) || '')
  } catch {
    return ''
  }
}

function resetDismissalFor(nextKey, previousKey) {
  if (previousKey === nextKey || dismissedKey.value === nextKey) return
  dismissedKey.value = ''
  rememberDismissedKey('')
}

function trackTaskId(taskId, initialTask = null) {
  const normalized = String(taskId || '')
  if (!normalized) return
  const previousKey = cardKey.value
  trackedTaskId.value = normalized
  task.value = initialTask
  streamState.value = null
  if (previousKey !== normalized) {
    resetDismissalFor(normalized, previousKey)
    auditExpanded.value = false
  }
  rememberTaskId(normalized)
  loadTask()
  startPolling()
}

function applyTask(nextTask) {
  if (!nextTask?.taskId) return
  const nextKey = String(nextTask.taskId)
  const previousKey = cardKey.value
  trackedTaskId.value = nextKey
  task.value = nextTask
  streamState.value = null
  if (previousKey !== nextKey) {
    resetDismissalFor(nextKey, previousKey)
    auditExpanded.value = false
  }
  if (['queued', 'running'].includes(String(nextTask.status))) {
    rememberTaskId(nextKey)
    startPolling()
  } else {
    rememberTaskId('')
    stopPolling()
    scheduleCompleteDismiss()
  }
}

function handleWorkflowProgress(event) {
  const detail = event?.detail && typeof event.detail === 'object' ? event.detail : {}
  if (detail.task?.taskId) {
    applyTask(detail.task)
    return
  }
  const workflowId = String(detail.workflowId || '')
  if (!workflowId) return
  const previousKey = cardKey.value
  task.value = null
  trackedTaskId.value = ''
  streamState.value = {
    workflowId,
    workflow: detail.workflow || '',
    stage: detail.stage || '',
    status: workflowStatus(detail.status),
    progress: detail.progress,
    message: detail.message || '',
    completedWeeks: detail.completedWeeks,
    totalWeeks: detail.totalWeeks,
    route: detail.route || '',
  }
  if (previousKey !== workflowId) {
    resetDismissalFor(workflowId, previousKey)
    auditExpanded.value = false
  }
  stopPolling()
  if (['complete', 'failed'].includes(streamState.value.status)) scheduleCompleteDismiss()
}

async function loadTask() {
  if (!trackedTaskId.value) return
  try {
    const response = await getXiaoZhiTask(trackedTaskId.value)
    const nextTask = response?.data?.task || null
    if (nextTask && Array.isArray(response?.data?.orchestrationRuns)) {
      nextTask.orchestrationRuns = response.data.orchestrationRuns
    }
    if (nextTask) applyTask(nextTask)
  } catch (error) {
    if (Number(error?.response?.status) === 404) {
      trackedTaskId.value = ''
      task.value = null
      rememberTaskId('')
      stopPolling()
      return
    }
    await loadTaskFromStatus(trackedTaskId.value)
  }
}

async function loadTaskFromStatus(targetId = '') {
  try {
    const response = await getXiaoZhiStatus()
    const tasks = Array.isArray(response?.data?.tasks) ? response.data.tasks : []
    const nextTask = targetId
      ? tasks.find(item => String(item.taskId) === String(targetId))
      : tasks.find(item => item.taskType === 'learning_path' && ['queued', 'running'].includes(String(item.status)))
    if (nextTask) applyTask(nextTask)
  } catch {
    // The assistant stays quiet when no authenticated status can be loaded.
  }
}

function startPolling() {
  stopPolling()
  if (!trackedTaskId.value || !['queued', 'running'].includes(String(task.value?.status || 'queued'))) return
  pollingTimer = window.setInterval(loadTask, 3000)
}

function stopPolling() {
  if (pollingTimer) window.clearInterval(pollingTimer)
  pollingTimer = 0
}

function scheduleCompleteDismiss() {
  if (completeTimer) window.clearTimeout(completeTimer)
  completeTimer = 0
  if (status.value === 'failed') return
  if (embedded) return
  if (route.name === 'resource-detail') return
  completeTimer = window.setTimeout(() => {
    dismissedKey.value = cardKey.value
  }, 15000)
}

function dismissCard() {
  dismissedKey.value = cardKey.value
  rememberDismissedKey(dismissedKey.value)
}

function goTaskRoute() {
  const targetRoute = task.value?.route || streamState.value?.route
  if (!targetRoute) return
  router.push(targetRoute)
}

onMounted(() => {
  window.addEventListener(XIAOZHI_WORKFLOW_EVENT, handleWorkflowProgress)
  dismissedKey.value = restoredDismissedKey()
  const initialTaskId = String(route.query.xzTask || restoredTaskId())
  if (initialTaskId) trackTaskId(initialTaskId)
  else {
    const restored = restoredWorkflowState()
    if (restored?.taskId) trackTaskId(restored.taskId)
    else if (restored?.workflowId) handleWorkflowProgress({ detail: restored })
    else loadTaskFromStatus()
  }
})

onBeforeUnmount(() => {
  window.removeEventListener(XIAOZHI_WORKFLOW_EVENT, handleWorkflowProgress)
  stopPolling()
  if (completeTimer) window.clearTimeout(completeTimer)
})
</script>

<style scoped>
.xz-workflow-card {
  position: fixed;
  top: 86px;
  right: 24px;
  z-index: 9997;
  width: min(420px, calc(100vw - 32px));
  padding: 16px;
  box-sizing: border-box;
  border: 1px solid rgba(202, 216, 211, 0.92);
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.97);
  box-shadow: 0 16px 42px rgba(28, 55, 49, 0.14);
  color: #1f3430;
  backdrop-filter: blur(14px);
}

.xz-workflow-card.embedded {
  position: relative;
  inset: auto;
  z-index: auto;
  width: 100%;
  margin: 10px 0;
  padding: 14px;
  border-color: #dce5e1;
  background: #fff;
  box-shadow: none;
  backdrop-filter: none;
}

.card-head {
  display: grid;
  grid-template-columns: 34px minmax(0, 1fr) auto 30px;
  align-items: center;
  gap: 10px;
}

.brand-mark,
.agent-icon {
  display: grid;
  place-items: center;
  flex: 0 0 auto;
  color: #176b52;
  background: #edf7f2;
}

.brand-mark {
  width: 34px;
  height: 34px;
  border-radius: 7px;
}

.head-copy {
  min-width: 0;
}

.head-copy > span {
  display: block;
  margin-bottom: 2px;
  color: #5d716b;
  font-size: 10px;
  font-weight: 800;
}

.head-copy strong {
  display: block;
  overflow: hidden;
  font-size: 14px;
  line-height: 1.35;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.status-label {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  min-width: max-content;
  color: #176b52;
  font-size: 11px;
  font-weight: 800;
}

.status-label i {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: currentColor;
}

.running .status-label i,
.queued .status-label i {
  box-shadow: 0 0 0 4px rgba(23, 107, 82, 0.12);
}

.failed .status-label,
.failed .agent-icon {
  color: #b83b34;
}

.failed .status-label i {
  box-shadow: 0 0 0 4px rgba(184, 59, 52, 0.1);
}

.icon-button {
  width: 30px;
  height: 30px;
  display: grid;
  place-items: center;
  padding: 0;
  border: 1px solid #dce5e1;
  border-radius: 6px;
  background: #fff;
  color: #61736e;
  cursor: pointer;
}

.icon-button:hover {
  border-color: #afc9bf;
  color: #1d5f4b;
}

.current-run {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  margin: 14px 0;
  padding: 11px 12px;
  border-left: 3px solid #2f8b6c;
  background: #f5f8f6;
}

.agent-icon {
  width: 28px;
  height: 28px;
  margin-top: 1px;
  border-radius: 50%;
}

.current-run > div:last-child {
  min-width: 0;
}

.current-run span {
  display: block;
  color: #254a3f;
  font-size: 12px;
  font-weight: 800;
}

.current-run p {
  margin: 3px 0 0;
  overflow: hidden;
  color: #63736e;
  font-size: 12px;
  line-height: 1.5;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.stage-list {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  margin: 0;
  padding: 0;
  list-style: none;
}

.stage-list li {
  position: relative;
  display: grid;
  justify-items: center;
  gap: 5px;
  color: #8b9894;
}

.stage-list li:not(:last-child)::after {
  content: '';
  position: absolute;
  top: 10px;
  left: calc(50% + 12px);
  right: calc(-50% + 12px);
  height: 1px;
  background: #dce5e1;
}

.stage-list li.done:not(:last-child)::after {
  background: #65a991;
}

.stage-node {
  position: relative;
  z-index: 1;
  width: 22px;
  height: 22px;
  display: grid;
  place-items: center;
  border: 1px solid #d6dfdc;
  border-radius: 50%;
  background: #fff;
  font-size: 10px;
  font-weight: 800;
}

.stage-list li.active,
.stage-list li.done {
  color: #176b52;
}

.stage-list li.active .stage-node {
  border-color: #2f8b6c;
  box-shadow: 0 0 0 4px rgba(47, 139, 108, 0.1);
}

.stage-list li.done .stage-node {
  border-color: #2f8b6c;
  background: #2f8b6c;
  color: #fff;
}

.stage-list li.failed,
.stage-list li.failed .stage-node {
  border-color: #c9574f;
  color: #b83b34;
}

.stage-list small {
  max-width: 100%;
  overflow: hidden;
  font-size: 10px;
  font-weight: 700;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.progress-row {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 38px;
  align-items: center;
  gap: 10px;
  margin-top: 13px;
}

.progress-track {
  height: 5px;
  border-radius: 5px;
  background: #e7eeeb;
  overflow: hidden;
}

.progress-track i {
  display: block;
  height: 100%;
  border-radius: inherit;
  background: #2f8b6c;
  transition: width 320ms ease;
}

.failed .progress-track i {
  background: #c9574f;
}

.progress-row strong {
  color: #34564c;
  font-size: 12px;
  text-align: right;
}

.card-foot {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-top: 11px;
  padding-top: 10px;
  border-top: 1px solid #edf1ef;
}

.foot-actions {
  display: inline-flex;
  align-items: center;
  gap: 12px;
  flex: 0 0 auto;
}

.result-summary {
  min-width: 0;
  overflow: hidden;
  color: #64756f;
  font-size: 11px;
  font-weight: 700;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.view-button {
  min-height: 30px;
  display: inline-flex;
  align-items: center;
  gap: 5px;
  flex: 0 0 auto;
  padding: 0;
  border: 0;
  background: transparent;
  color: #176b52;
  font-size: 12px;
  font-weight: 800;
  cursor: pointer;
}

.feedback-slot {
  margin-top: 10px;
}

.audit-drawer {
  margin-top: 10px;
  padding: 10px 11px;
  border: 1px solid #e2e9e6;
  background: #f8faf9;
}

.audit-drawer dl {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 8px 14px;
  margin: 0;
}

.audit-drawer dl > div {
  min-width: 0;
}

.audit-drawer dt {
  color: #7b8b85;
  font-size: 9px;
  font-weight: 700;
}

.audit-drawer dd {
  margin: 2px 0 0;
  overflow: hidden;
  color: #304f45;
  font-size: 11px;
  font-weight: 750;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.audit-drawer p {
  margin: 9px 0 0;
  padding-top: 8px;
  border-top: 1px solid #e4ebe8;
  overflow: hidden;
  color: #64756f;
  font-size: 10px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.spin {
  animation: xzWorkflowSpin 1.2s linear infinite;
}

@keyframes xzWorkflowSpin {
  to { transform: rotate(360deg); }
}

@media (max-width: 768px) {
  .xz-workflow-card {
    top: auto;
    right: 12px;
    bottom: calc(166px + env(safe-area-inset-bottom));
    left: 12px;
    width: auto;
    padding: 14px;
  }

  .xz-workflow-card.embedded {
    position: relative;
    inset: auto;
    width: 100%;
    padding: 12px;
  }

  .card-head {
    grid-template-columns: 32px minmax(0, 1fr) 30px;
  }

  .brand-mark {
    width: 32px;
    height: 32px;
  }

  .status-label {
    display: none;
  }

  .current-run {
    margin: 12px 0;
  }

  .stage-list small {
    font-size: 9px;
  }
}

@media (prefers-reduced-motion: reduce) {
  .spin {
    animation: none;
  }

  .progress-track i {
    transition: none;
  }
}
</style>
