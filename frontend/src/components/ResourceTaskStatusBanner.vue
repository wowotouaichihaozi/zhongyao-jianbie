<template>
  <aside v-if="showTaskBanner" class="xz-task-banner" :class="task.status">
    <span class="state-dot"></span>
    <div>
      <strong>{{ task.title }}</strong>
      <p>{{ taskMessage }}</p>
      <p v-if="taskResultSummary" class="result-summary">{{ taskResultSummary }}</p>
    </div>
    <button v-if="task.route" type="button" class="view-button" @click="goTaskRoute">
      查看
      <ArrowRight :size="15" />
    </button>
    <div v-if="showFeedbackActions" class="feedback-slot">
      <LearningFeedbackActions
        :task="task"
        :cache-key="String(route.query.cacheKey || '')"
        :route-path="route.fullPath"
        compact
      />
    </div>
  </aside>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ArrowRight } from 'lucide-vue-next'
import LearningFeedbackActions from './LearningFeedbackActions.vue'
import { getXiaoZhiStatus, getXiaoZhiTask } from '../services/api.js'

const route = useRoute()
const router = useRouter()
const task = ref(null)
let timer = null

const taskId = computed(() => String(route.query.xzTask || ''))
const isImmersiveWorkbench = computed(() => String(route.path || '').startsWith('/personalized-resources/mcu-simulator/'))
const showTaskBanner = computed(() => (
  Boolean(task.value)
  && !isImmersiveWorkbench.value
  && !['/mind-map', '/document'].some(suffix => String(route.path || '').endsWith(suffix))
))
const feedbackTaskTypes = new Set(['personalized_resources', 'question_bank', 'ppt', 'video', 'animation', 'mcu', 'smart_tutor'])
const showFeedbackActions = computed(() => (
  task.value?.status === 'complete'
  && feedbackTaskTypes.has(String(task.value?.taskType || task.value?.type || ''))
))
const taskMessage = computed(() => {
  const status = task.value?.status
  if (status === 'running') return '岐小智正在后台生成，切换页面后状态会继续保留。'
  if (status === 'queued') return '任务已进入队列，岐小智会持续跟进。'
  if (status === 'complete') return task.value?.result?.message || '任务已完成，可以继续查看或编辑对应资源。'
  if (status === 'failed') return task.value?.error || '任务生成失败，请稍后重试。'
  return '正在同步岐小智后台任务状态。'
})
const taskResultSummary = computed(() => {
  if (!task.value) return ''
  if (['queued', 'running'].includes(task.value.status)) return 'Harness 执行与审核中'
  if (task.value.status === 'failed') return 'Harness 审核未通过或资源生成失败'
  const result = task.value?.result || {}
  const selected = result.selectedResource && typeof result.selectedResource === 'object' ? result.selectedResource : {}
  const metadata = selected.metadata && typeof selected.metadata === 'object' ? selected.metadata : {}
  const quality = result.qualityEvaluation || selected.qualityEvaluation || metadata.qualityEvaluation || {}
  const sources = result.knowledgeSources || selected.knowledgeSources || metadata.knowledgeSources || []
  const review = result.orchestration?.review || {}
  const parts = []
  if (result.topic) parts.push(`主题：${result.topic}`)
  if (Number(quality.score || 0)) parts.push(`质量 ${Number(quality.score)} / 100`)
  const citationCount = Math.max(Number(quality.citationCount || 0), Array.isArray(sources) ? sources.length : 0)
  if (citationCount) parts.push(`知识引用 ${citationCount} 条`)
  parts.push(review.passed ? 'Harness 已通过' : 'Harness 待核验')
  return parts.join(' · ')
})

watch(taskId, () => {
  task.value = null
  loadTask()
  startPolling()
})

async function loadTask() {
  if (!taskId.value) return
  try {
    const response = await getXiaoZhiTask(taskId.value)
    task.value = response?.data?.task || null
    if (task.value && !['queued', 'running'].includes(task.value.status)) {
      stopPolling()
    }
  } catch {
    await loadTaskFromStatus()
  }
}

async function loadTaskFromStatus() {
  try {
    const response = await getXiaoZhiStatus()
    const tasks = response?.data?.tasks || []
    task.value = tasks.find(item => item.taskId === taskId.value) || null
    if (task.value && !['queued', 'running'].includes(task.value.status)) {
      stopPolling()
    }
  } catch {
    // Keep the banner quiet if the assistant status endpoint is unavailable.
  }
}

function startPolling() {
  stopPolling()
  if (!taskId.value) return
  timer = window.setInterval(loadTask, 3000)
}

function stopPolling() {
  if (timer) {
    window.clearInterval(timer)
    timer = null
  }
}

function goTaskRoute() {
  if (!task.value?.route) return
  router.push(task.value.route)
}

onMounted(() => {
  loadTask()
  startPolling()
})

onBeforeUnmount(stopPolling)
</script>

<style scoped>
.xz-task-banner {
  position: fixed;
  top: 86px;
  right: 24px;
  z-index: 9997;
  width: min(380px, calc(100vw - 32px));
  display: grid;
  grid-template-columns: auto minmax(0, 1fr) auto;
  align-items: center;
  gap: 12px;
  padding: 12px 14px;
  border: 1px solid rgba(205, 239, 227, 0.95);
  border-radius: 18px;
  background: rgba(255, 255, 255, 0.95);
  box-shadow: 0 18px 44px rgba(31, 72, 66, 0.14);
  backdrop-filter: blur(16px);
}

.state-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: #94a3b8;
}

.xz-task-banner > div {
  min-width: 0;
}

.xz-task-banner.queued .state-dot,
.xz-task-banner.running .state-dot {
  background: #3b82f6;
  box-shadow: 0 0 0 5px rgba(59, 130, 246, 0.12);
}

.xz-task-banner.complete .state-dot {
  background: #10b981;
  box-shadow: 0 0 0 5px rgba(16, 185, 129, 0.12);
}

.xz-task-banner.failed .state-dot {
  background: #ef4444;
  box-shadow: 0 0 0 5px rgba(239, 68, 68, 0.12);
}

.xz-task-banner strong {
  display: block;
  overflow: hidden;
  color: #1f3433;
  font-size: 14px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.xz-task-banner p {
  margin: 3px 0 0;
  color: #667a77;
  font-size: 12px;
  line-height: 1.45;
}

.xz-task-banner .result-summary {
  color: #0f766e;
  font-weight: 700;
}

.xz-task-banner .view-button {
  min-height: 34px;
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 0 12px;
  border: 0;
  border-radius: 999px;
  background: #e8f8ef;
  color: #0e9f6e;
  font-weight: 800;
  cursor: pointer;
}

.feedback-slot {
  grid-column: 2 / 4;
  padding-top: 4px;
}

@media (max-width: 768px) {
  .xz-task-banner {
    top: auto;
    right: 12px;
    bottom: calc(166px + env(safe-area-inset-bottom));
    left: 12px;
    width: auto;
    grid-template-columns: auto minmax(0, 1fr);
  }

  .xz-task-banner .view-button {
    grid-column: 2;
    justify-self: start;
  }

  .feedback-slot {
    grid-column: 1 / 3;
  }
}
</style>
