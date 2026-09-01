<template>
  <main class="mind-map-page" :class="{ standalone: isResourceToolPage, 'task-backed': isTaskBackedMap }">
    <button v-if="isResourceToolPage" type="button" class="resource-back-button" @click="goBackToResources">
      <ArrowLeft :size="18" :stroke-width="2.2" aria-hidden="true" />
      <span>返回个性化资源</span>
    </button>

    <section v-if="isTaskBackedMap" class="task-map-shell" aria-live="polite">
      <header class="task-map-header">
        <div>
          <span class="task-map-kicker">
            <Network :size="16" stroke-width="2.2" aria-hidden="true" />
            嵌小智思维导图
          </span>
          <h1>{{ mapTitle }}</h1>
          <p>{{ mapDescription }}</p>
          <div v-if="!isTaskPending && !taskError" class="map-evidence-strip">
            <span>质量 <strong>{{ mapQuality.score || 0 }} / 100</strong></span>
            <span>知识引用 <strong>{{ mapCitationCount }} 条</strong></span>
            <span :class="{ passed: mapQuality.passed }">{{ mapQuality.passed ? '质量评价通过' : '需要进一步核验' }}</span>
          </div>
        </div>
        <div class="task-header-actions">
          <button type="button" class="history-nav-button" @click="openHistory">
            <History :size="16" stroke-width="2.2" aria-hidden="true" />
            历史记录
          </button>
          <span class="task-state" :class="taskStateClass">
            <LoaderCircle v-if="isTaskPending" :size="16" class="spin" aria-hidden="true" />
            <CircleAlert v-else-if="taskError" :size="16" aria-hidden="true" />
            <CheckCircle2 v-else :size="16" aria-hidden="true" />
            {{ taskStatusText }}
          </span>
        </div>
      </header>

      <LearningFeedbackActions
        v-if="!isTaskPending && !taskError"
        class="task-map-feedback"
        :task="task"
        :cache-key="String(route.query.cacheKey || '')"
        :route-path="route.fullPath"
      />

      <div v-if="isTaskPending" class="task-map-loading">
        <span class="loading-rings" aria-hidden="true"><i></i><i></i><i></i></span>
        <strong>{{ taskStatusText }}</strong>
        <p>页面会持续同步后台任务，导图生成完成后自动显示。</p>
        <div class="loading-track"><span :style="{ width: `${taskProgress}%` }"></span></div>
        <small>{{ taskProgress }}%</small>
      </div>

      <div v-else-if="taskError" class="task-map-error">
        <CircleAlert :size="34" stroke-width="1.9" aria-hidden="true" />
        <strong>思维导图暂时无法显示</strong>
        <p>{{ taskError }}</p>
        <button type="button" @click="startGeneration">重新生成</button>
      </div>

      <div v-else-if="mindMapMarkdown" class="mind-map-canvas">
        <MindMapWizardCanvas :content="mindMapMarkdown" :title="mapTitle" />
      </div>
    </section>

    <section v-else class="mind-map-create-shell">
      <div class="wizard-hero">
        <span class="wizard-product-mark">
          <Sparkles :size="17" stroke-width="2.2" aria-hidden="true" />
          Mind Map Wizard · 嵌小智
        </span>
        <h1>把学习主题变成一张清晰的思维导图</h1>
        <p>围绕当前学习画像梳理核心概念、前置知识、易错点和实践关系。</p>

        <form class="wizard-composer" @submit.prevent="startGeneration">
          <label class="sr-only" for="mind-map-topic">学习主题</label>
          <div class="wizard-input-shell">
            <textarea
              id="mind-map-topic"
              v-model.trim="topic"
              rows="2"
              maxlength="100"
              placeholder="输入学习主题，例如：STM32 GPIO 工作模式"
              :disabled="creatingTask"
              @keydown.enter.exact.prevent="startGeneration"
            ></textarea>
            <button
              type="submit"
              title="生成思维导图"
              aria-label="生成思维导图"
              :disabled="!topic || creatingTask"
            >
              <LoaderCircle v-if="creatingTask" :size="21" class="spin" aria-hidden="true" />
              <Send v-else :size="21" stroke-width="2.2" aria-hidden="true" />
            </button>
          </div>
          <div class="wizard-suggestions" aria-label="推荐学习主题">
            <span>试试这些主题</span>
            <button
              v-for="suggestion in suggestedTopics"
              :key="suggestion"
              type="button"
              :disabled="creatingTask"
              @click="useSuggestedTopic(suggestion)"
            >
              {{ suggestion }}
            </button>
          </div>
        </form>

        <p v-if="taskError" class="create-error" role="alert">{{ taskError }}</p>

        <div class="wizard-capabilities" aria-label="导图生成能力">
          <div>
            <UserRoundCheck :size="20" stroke-width="2" aria-hidden="true" />
            <span><strong>画像适配</strong><small>结合目标与薄弱点</small></span>
          </div>
          <div>
            <BookOpenCheck :size="20" stroke-width="2" aria-hidden="true" />
            <span><strong>知识引用</strong><small>关联课程知识依据</small></span>
          </div>
          <div>
            <ShieldCheck :size="20" stroke-width="2" aria-hidden="true" />
            <span><strong>质量审校</strong><small>结构与安全双重检查</small></span>
          </div>
        </div>
      </div>

      <div class="mind-map-history-band">
        <MindMapTaskHistory
          :tasks="historyTasks"
          :loading="historyLoading"
          :error="historyError"
          @open="openHistoryTask"
          @refresh="loadMindMapHistory"
          @retry="retryHistoryTask"
        />
      </div>
    </section>
  </main>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  ArrowLeft,
  BookOpenCheck,
  CheckCircle2,
  CircleAlert,
  History,
  LoaderCircle,
  Network,
  Send,
  ShieldCheck,
  Sparkles,
  UserRoundCheck,
} from 'lucide-vue-next'
import LearningFeedbackActions from '../components/LearningFeedbackActions.vue'
import MindMapTaskHistory from '../components/MindMapTaskHistory.vue'
import MindMapWizardCanvas from '../components/MindMapWizardCanvas.vue'
import { getMindMapTaskHistory, getXiaoZhiTask, startPersonalizedResourceAgentTask } from '../services/api.js'
import {
  markNodeCacheComplete,
  markNodeCacheError,
  markNodeCacheStarted,
} from '../services/learningPathNodeCache.js'

const route = useRoute()
const router = useRouter()
const task = ref(null)
const taskError = ref('')
const mindMapMarkdown = ref('')
const selectedResource = ref(null)
const topic = ref(String(route.query.topic || route.query.keyword || '').trim())
const creatingTask = ref(false)
const historyTasks = ref([])
const historyLoading = ref(false)
const historyError = ref('')
let taskPollTimer = null
let historyPollTimer = null
let historyRequestInFlight = false
let autostartConsumed = false
const suggestedTopics = [
  'STM32 中断系统',
  'FreeRTOS 任务调度',
  '串口通信与 DMA',
]

const isResourceToolPage = computed(() => route.meta?.resourceTool === true || route.path.startsWith('/personalized-resources/'))
const taskId = computed(() => String(route.query.xzTask || '').trim())
const isTaskBackedMap = computed(() => Boolean(taskId.value))
const taskRuntimeStatus = computed(() => String(task.value?.status || (taskId.value ? 'loading' : 'complete')))
const isTaskPending = computed(() => ['loading', 'queued', 'running'].includes(taskRuntimeStatus.value) && !taskError.value)
const taskProgress = computed(() => {
  if (taskRuntimeStatus.value === 'loading') return 8
  const progress = Number(task.value?.result?.progress || 0)
  if (taskRuntimeStatus.value === 'queued') return Math.max(6, Math.min(18, progress || 8))
  return Math.max(18, Math.min(96, progress || 36))
})
const taskStateClass = computed(() => (taskError.value ? 'failed' : (isTaskPending.value ? 'running' : 'complete')))
const taskStatusText = computed(() => {
  if (taskError.value) return '同步失败'
  if (taskRuntimeStatus.value === 'loading') return '正在读取后台任务'
  if (taskRuntimeStatus.value === 'queued') return '等待后台生成'
  if (taskRuntimeStatus.value === 'running') return '后台生成中'
  return '导图已生成'
})
const mapTitle = computed(() => String(
  selectedResource.value?.title
  || task.value?.result?.topic
  || task.value?.title
  || route.query.topic
  || route.query.keyword
  || '个性化学习思维导图',
).trim())
const mapDescription = computed(() => String(
  selectedResource.value?.description
  || (isTaskPending.value ? '正在根据当前学习画像和本周任务整理知识结构。' : '已根据本周任务目标整理核心概念、易错点与实践验证关系。'),
).trim())
const mapQuality = computed(() => (
  selectedResource.value?.qualityEvaluation
  || selectedResource.value?.metadata?.qualityEvaluation
  || task.value?.result?.qualityEvaluation
  || {}
))
const mapCitationCount = computed(() => Math.max(
  Number(mapQuality.value?.citationCount || 0),
  Array.isArray(task.value?.result?.knowledgeSources) ? task.value.result.knowledgeSources.length : 0,
  Array.isArray(selectedResource.value?.metadata?.knowledgeSources) ? selectedResource.value.metadata.knowledgeSources.length : 0,
))

watch(taskId, () => {
  stopTaskPolling()
  task.value = null
  taskError.value = ''
  mindMapMarkdown.value = ''
  selectedResource.value = null
  if (taskId.value) void loadTask()
}, { immediate: true })

onMounted(() => {
  void loadMindMapHistory()
  if (!taskId.value && route.query.autostart === '1' && topic.value && !autostartConsumed) {
    autostartConsumed = true
    void startGeneration()
  }
})

onBeforeUnmount(() => {
  stopTaskPolling()
  stopHistoryPolling()
})

function goBackToResources() {
  router.push('/personalized-resources')
}

function useSuggestedTopic(value) {
  topic.value = value
  document.querySelector('#mind-map-topic')?.focus()
}

async function startGeneration() {
  if (!topic.value || creatingTask.value || isTaskPending.value) return
  stopTaskPolling()
  creatingTask.value = true
  taskError.value = ''
  mindMapMarkdown.value = ''
  selectedResource.value = null
  try {
    const response = await startPersonalizedResourceAgentTask({
      resourceType: 'mindmap',
      topic: topic.value,
      prompt: `围绕 ${topic.value} 生成结构清晰、带知识依据的学习思维导图`,
      params: {
        topic: topic.value,
        keyword: topic.value,
        source: route.query.source,
        stageId: route.query.stageId,
        nodeId: route.query.nodeId,
        cacheKey: route.query.cacheKey,
      },
    })
    const nextTask = response?.data?.task
    if (!nextTask?.taskId) throw new Error('未获得思维导图任务 ID')
    task.value = nextTask
    historyTasks.value = [nextTask, ...historyTasks.value.filter(item => item.taskId !== nextTask.taskId)]
    startHistoryPolling()
    markTaskCacheStarted(nextTask)
    await router.replace({
      query: {
        ...route.query,
        topic: topic.value,
        keyword: topic.value,
        autostart: undefined,
        xzTask: nextTask.taskId,
      },
    })
    startTaskPolling()
    await loadTask()
  } catch (error) {
    taskError.value = error?.response?.data?.msg || error?.message || '思维导图任务创建失败'
    markTaskCacheError(taskError.value)
  } finally {
    creatingTask.value = false
  }
}

async function loadTask() {
  if (!taskId.value) return
  taskError.value = ''
  try {
    const response = await getXiaoZhiTask(taskId.value)
    const nextTask = response?.data?.task
    if (!nextTask) throw new Error('未找到对应的嵌小智后台任务。')
    task.value = nextTask
    if (['queued', 'running'].includes(nextTask.status)) {
      markTaskCacheStarted(nextTask)
      startTaskPolling()
      return
    }
    stopTaskPolling()
    if (nextTask.status === 'failed') {
      throw new Error(nextTask.error || '后台思维导图任务生成失败。')
    }
    const resource = resolveMindMapResource(nextTask.result)
    const markdown = normalizeMindMapContent(resource?.content, mapTitle.value)
    if (!markdown) throw new Error('后台任务已完成，但没有返回有效的思维导图内容。')
    selectedResource.value = resource
    mindMapMarkdown.value = markdown
    markTaskCacheComplete(nextTask, resource)
    void loadMindMapHistory({ silent: true })
  } catch (error) {
    stopTaskPolling()
    taskError.value = error?.response?.data?.msg || error?.message || '同步思维导图任务时发生错误。'
    markTaskCacheError(taskError.value)
  }
}

function startTaskPolling() {
  if (taskPollTimer || !taskId.value) return
  taskPollTimer = window.setInterval(loadTask, 1600)
}

function stopTaskPolling() {
  if (!taskPollTimer) return
  window.clearInterval(taskPollTimer)
  taskPollTimer = null
}

async function loadMindMapHistory(options = {}) {
  if (historyRequestInFlight) return
  historyRequestInFlight = true
  if (!options.silent) historyLoading.value = true
  historyError.value = ''
  try {
    const data = await getMindMapTaskHistory({ limit: 40 })
    historyTasks.value = Array.isArray(data?.tasks) ? data.tasks : []
    if (historyTasks.value.some(item => ['queued', 'running'].includes(item.status))) {
      startHistoryPolling()
    } else {
      stopHistoryPolling()
    }
  } catch (error) {
    historyError.value = error?.response?.data?.msg || error?.message || '读取思维导图历史记录失败'
    stopHistoryPolling()
  } finally {
    historyRequestInFlight = false
    historyLoading.value = false
  }
}

function startHistoryPolling() {
  if (historyPollTimer) return
  historyPollTimer = window.setInterval(() => loadMindMapHistory({ silent: true }), 2400)
}

function stopHistoryPolling() {
  if (!historyPollTimer) return
  window.clearInterval(historyPollTimer)
  historyPollTimer = null
}

function openHistory() {
  router.push({ path: '/personalized-resources/mind-map', query: { history: '1' } })
}

function openHistoryTask(historyTask) {
  const savedRoute = String(historyTask?.route || '').trim()
  if (/^\/(?:personalized-resources\/mind-map|mind-map)(?:\?|$)/.test(savedRoute)) {
    router.push(savedRoute)
    return
  }
  router.push({
    path: '/personalized-resources/mind-map',
    query: {
      topic: historyTask?.result?.topic || historyTask?.result?.params?.topic || historyTask?.title || '',
      xzTask: historyTask?.taskId,
    },
  })
}

async function retryHistoryTask(historyTask) {
  topic.value = String(
    historyTask?.result?.topic
    || historyTask?.result?.params?.topic
    || historyTask?.prompt
    || historyTask?.title
    || '',
  ).trim()
  if (!topic.value) return
  await router.replace({
    path: '/personalized-resources/mind-map',
    query: { topic: topic.value, keyword: topic.value },
  })
  await startGeneration()
}

function resolveMindMapResource(result) {
  const payload = result && typeof result === 'object' ? result : {}
  if (payload.selectedResource && typeof payload.selectedResource === 'object') {
    return payload.selectedResource
  }
  const resources = Array.isArray(payload.workflow?.resources) ? payload.workflow.resources : []
  const resource = resources.find(item => ['mindmap', 'mind-map'].includes(String(item?.type || '').toLowerCase()))
  if (resource) return resource
  if (typeof payload.content === 'string') {
    return { title: payload.topic || mapTitle.value, content: payload.content }
  }
  return null
}

function normalizeMindMapContent(content, fallbackTitle) {
  let source = String(content || '').replace(/\r/g, '').trim()
  if (source.startsWith('{')) {
    try {
      const parsed = JSON.parse(source)
      if (typeof parsed?.markdown === 'string') source = parsed.markdown.trim()
      else if (parsed?.['mm-node']) return source
    } catch {
      // Continue with the raw model output so fenced Markdown can still be recovered.
    }
  }
  const fenced = source.match(/```(?:mermaid|markdown|md)?\s*([\s\S]*?)```/i)
  if (fenced) source = fenced[1].trim()
  if (!source) return ''

  const lines = source.split('\n')
  const startIndex = lines.findIndex(line => /^\s*mindmap\s*$/i.test(line))
  if (startIndex < 0) {
    const hasRoot = lines.some(line => /^#\s+\S/.test(line.trim()))
    const hasBranch = lines.some(line => /^##\s+\S/.test(line.trim()))
    if (hasRoot && hasBranch) return source
    const plainLines = lines.map(line => cleanMindMapLabel(line)).filter(Boolean)
    if (!plainLines.length) return ''
    return [`# ${fallbackTitle || plainLines[0]}`, ...plainLines.map(line => `## ${line}`)].join('\n')
  }

  const mapLines = lines.slice(startIndex + 1)
    .filter(line => line.trim() && !/^\s*(?:---|```)/.test(line))
  if (!mapLines.length) return ''

  const root = { label: cleanMindMapLabel(mapLines[0].trim()) || fallbackTitle, children: [] }
  const rootIndent = indentationOf(mapLines[0])
  const stack = [{ indent: rootIndent, node: root }]
  for (const line of mapLines.slice(1)) {
    const label = cleanMindMapLabel(line.trim())
    if (!label) continue
    const indent = indentationOf(line)
    const node = { label, children: [] }
    while (stack.length > 1 && indent <= stack[stack.length - 1].indent) stack.pop()
    stack[stack.length - 1].node.children.push(node)
    stack.push({ indent, node })
  }
  return mindMapTreeToMarkdown(root)
}

function indentationOf(line) {
  const prefix = String(line || '').match(/^\s*/)?.[0] || ''
  return prefix.replace(/\t/g, '  ').length
}

function cleanMindMapLabel(value) {
  let label = String(value || '').trim()
  label = label.replace(/^root\s*/i, '')
  label = label.replace(/^[a-zA-Z0-9_-]+(?=\(\(|\[|\(|\{)/, '')
  const wrappers = [
    [/^\(\((.*)\)\)$/s, '$1'],
    [/^\((.*)\)$/s, '$1'],
    [/^\[(.*)\]$/s, '$1'],
    [/^\{(.*)\}$/s, '$1'],
  ]
  for (const [pattern, replacement] of wrappers) label = label.replace(pattern, replacement)
  return label.replace(/^['"]|['"]$/g, '').trim()
}

function mindMapTreeToMarkdown(root) {
  const lines = [`# ${root.label}`]
  const visit = (nodes, depth) => {
    for (const node of nodes || []) {
      lines.push(`${'#'.repeat(Math.min(depth + 1, 6))} ${node.label}`)
      visit(node.children, depth + 1)
    }
  }
  visit(root.children, 1)
  return lines.join('\n')
}

function taskCacheKey() {
  return String(route.query.cacheKey || '').trim()
}

function markTaskCacheStarted(nextTask) {
  const cacheKey = taskCacheKey()
  if (!cacheKey) return
  markNodeCacheStarted(cacheKey, {
    resourceType: 'mindmap',
    title: mapTitle.value,
    route: route.fullPath,
    taskId: nextTask.taskId,
    agentTaskId: nextTask.taskId,
    progress: taskProgress.value,
  })
}

function markTaskCacheComplete(nextTask, resource) {
  const cacheKey = taskCacheKey()
  if (!cacheKey) return
  markNodeCacheComplete(cacheKey, {
    resourceType: 'mindmap',
    title: resource?.title || mapTitle.value,
    route: route.fullPath,
    taskId: nextTask.taskId,
    agentTaskId: nextTask.taskId,
    progress: 100,
  })
}

function markTaskCacheError(error) {
  const cacheKey = taskCacheKey()
  if (!cacheKey) return
  markNodeCacheError(cacheKey, {
    resourceType: 'mindmap',
    title: mapTitle.value,
    route: route.fullPath,
    taskId: taskId.value,
    agentTaskId: taskId.value,
    error,
  })
}

</script>

<style scoped>
.mind-map-page {
  width: 100%;
  height: calc(100vh - 64px);
  min-height: 560px;
  background: #f4f8f6;
}

.mind-map-page.standalone {
  height: 100vh;
  min-height: 100vh;
  padding: 72px 16px 16px;
  box-sizing: border-box;
}

.mind-map-page.task-backed {
  height: calc(100vh - 64px);
  min-height: 560px;
  overflow-x: hidden;
  overflow-y: scroll;
  overscroll-behavior-y: contain;
  scrollbar-color: #8bb6a6 #e7f1ed;
  scrollbar-gutter: stable;
  scrollbar-width: thin;
}

.mind-map-page.standalone.task-backed {
  height: 100vh;
  min-height: 100vh;
}

.mind-map-page.task-backed::-webkit-scrollbar {
  width: 10px;
}

.mind-map-page.task-backed::-webkit-scrollbar-track {
  background: #e7f1ed;
}

.mind-map-page.task-backed::-webkit-scrollbar-thumb {
  border: 2px solid #e7f1ed;
  border-radius: 5px;
  background: #8bb6a6;
}

.mind-map-page.task-backed::-webkit-scrollbar-thumb:hover {
  background: #669a87;
}

.mind-map-create-shell {
  width: 100%;
  margin: 0 auto;
  padding: 36px 0 64px;
}

.wizard-hero {
  width: min(900px, calc(100% - 40px));
  min-height: 480px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  margin: 0 auto;
  padding: 38px 0 30px;
  text-align: center;
}

.wizard-product-mark {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  color: #0b8f65;
  font-size: 13px;
  font-weight: 800;
}

.wizard-product-mark svg { color: #e0a51a; }

.wizard-hero h1 {
  max-width: 760px;
  margin: 20px 0 12px;
  color: #163a31;
  font-size: 42px;
  line-height: 1.18;
  letter-spacing: 0;
}

.wizard-hero > p:not(.create-error) {
  max-width: 640px;
  margin: 0;
  color: #61766f;
  font-size: 15px;
  line-height: 1.7;
}

.wizard-composer {
  width: min(700px, 100%);
  margin-top: 34px;
}

.wizard-input-shell {
  position: relative;
  display: flex;
  align-items: flex-end;
  min-height: 76px;
  padding: 8px 68px 8px 20px;
  border: 1px solid #c9ddd5;
  border-radius: 28px;
  background: #fff;
  box-shadow: 0 16px 40px rgba(30, 83, 68, 0.1);
  transition: border-color 160ms ease, box-shadow 160ms ease;
}

.wizard-input-shell:focus-within {
  border-color: #18a575;
  box-shadow: 0 0 0 4px rgba(24, 165, 117, 0.1), 0 18px 44px rgba(30, 83, 68, 0.12);
}

.wizard-input-shell textarea {
  width: 100%;
  min-height: 52px;
  max-height: 130px;
  padding: 13px 0 8px;
  border: 0;
  resize: none;
  background: transparent;
  color: #17352d;
  font: inherit;
  font-size: 16px;
  line-height: 1.55;
  outline: none;
}

.wizard-input-shell textarea::placeholder { color: #8a9c96; }

.wizard-input-shell > button {
  position: absolute;
  right: 10px;
  bottom: 10px;
  width: 54px;
  height: 54px;
  display: grid;
  place-items: center;
  padding: 0;
  border: 0;
  border-radius: 50%;
  background: #0e9f6e;
  color: #fff;
  cursor: pointer;
  transition: background 160ms ease, transform 160ms ease;
}

.wizard-input-shell > button:hover:not(:disabled) {
  background: #087f59;
  transform: translateY(-1px);
}

.wizard-input-shell > button:disabled { opacity: 0.42; cursor: not-allowed; }

.wizard-suggestions {
  display: inline-flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: center;
  gap: 8px;
  margin-top: 16px;
}

.wizard-suggestions > span {
  margin-right: 2px;
  color: #83948e;
  font-size: 12px;
}

.wizard-suggestions button {
  min-height: 32px;
  padding: 0 12px;
  border: 1px solid #d7e5df;
  border-radius: 16px;
  background: rgba(255, 255, 255, 0.72);
  color: #45635a;
  font: inherit;
  font-size: 12px;
  cursor: pointer;
}

.wizard-suggestions button:hover:not(:disabled) {
  border-color: #9fd5c0;
  background: #eef9f4;
  color: #087b55;
}

.wizard-suggestions button:disabled { opacity: 0.55; cursor: not-allowed; }

.wizard-capabilities {
  width: min(700px, 100%);
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  margin-top: 32px;
  border-top: 1px solid #dce8e2;
  border-bottom: 1px solid #dce8e2;
}

.wizard-capabilities > div {
  min-width: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  padding: 17px 14px;
  color: #0b8f65;
}

.wizard-capabilities > div + div { border-left: 1px solid #dce8e2; }
.wizard-capabilities span { min-width: 0; text-align: left; }
.wizard-capabilities strong,
.wizard-capabilities small { display: block; }
.wizard-capabilities strong { color: #2d5046; font-size: 12px; }
.wizard-capabilities small { margin-top: 2px; color: #7a8c86; font-size: 10px; }

.mind-map-history-band {
  width: min(1200px, calc(100% - 40px));
  margin: 4px auto 0;
  padding-top: 30px;
  border-top: 1px solid #d9e6e1;
}

.sr-only {
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  margin: -1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  white-space: nowrap;
  border: 0;
}

.create-error {
  width: min(700px, 100%);
  box-sizing: border-box;
  margin: 14px 0 0;
  padding: 12px 14px;
  border: 1px solid #edc7c3;
  border-radius: 6px;
  background: #fff5f4;
  color: #a83e37;
  font-size: 13px;
}

.task-map-shell {
  width: min(1240px, calc(100% - 40px));
  min-height: calc(100vh - 104px);
  margin: 0 auto;
  padding: 24px 0 40px;
  box-sizing: border-box;
}

.standalone .task-map-shell {
  min-height: calc(100vh - 104px);
  padding-top: 4px;
}

.task-map-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 28px;
  padding: 4px 2px 24px;
  border-bottom: 1px solid #dce8e2;
}

.task-map-kicker,
.task-state {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  color: #0b8f65;
  font-size: 13px;
  font-weight: 750;
}

.task-header-actions {
  flex: 0 0 auto;
  display: flex;
  align-items: center;
  gap: 8px;
}

.history-nav-button {
  min-height: 36px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 7px;
  padding: 0 12px;
  border: 1px solid #d3e4dc;
  border-radius: 6px;
  background: #fff;
  color: #416259;
  font: inherit;
  font-size: 12px;
  font-weight: 700;
  cursor: pointer;
}

.history-nav-button:hover {
  border-color: #b9ddce;
  background: #edf8f3;
  color: #087b55;
}

.task-map-header h1 {
  margin: 9px 0 7px;
  color: #17352d;
  font-size: 28px;
  line-height: 1.28;
  letter-spacing: 0;
}

.task-map-header p {
  max-width: 760px;
  margin: 0;
  color: #667b74;
  font-size: 14px;
  line-height: 1.7;
}

.map-evidence-strip {
  display: flex;
  flex-wrap: wrap;
  gap: 8px 16px;
  margin-top: 13px;
  color: #6b7f78;
  font-size: 12px;
}

.map-evidence-strip span {
  display: inline-flex;
  align-items: center;
  gap: 4px;
}

.map-evidence-strip strong,
.map-evidence-strip .passed { color: #087b55; }

.task-state {
  flex: 0 0 auto;
  min-height: 36px;
  padding: 0 13px;
  border: 1px solid #bfe4d5;
  border-radius: 6px;
  background: #edf9f4;
}

.task-state.failed {
  color: #b4443c;
  border-color: #edc7c3;
  background: #fff5f4;
}

.task-map-loading,
.task-map-error {
  min-height: 420px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  text-align: center;
  color: #5d756d;
}

.task-map-loading strong,
.task-map-error strong {
  margin-top: 18px;
  color: #193a31;
  font-size: 19px;
}

.task-map-loading p,
.task-map-error p {
  max-width: 520px;
  margin: 8px 0 0;
  font-size: 14px;
  line-height: 1.65;
}

.loading-rings {
  position: relative;
  width: 80px;
  height: 80px;
}

.loading-rings i {
  position: absolute;
  inset: 0;
  border: 2px solid rgba(14, 159, 110, 0.28);
  border-radius: 50%;
  animation: map-pulse 1.8s ease-out infinite;
}

.loading-rings i:nth-child(2) { animation-delay: 0.45s; }
.loading-rings i:nth-child(3) { animation-delay: 0.9s; }

.loading-track {
  width: min(360px, 80vw);
  height: 6px;
  margin-top: 24px;
  overflow: hidden;
  border-radius: 3px;
  background: #dceae4;
}

.loading-track span {
  display: block;
  height: 100%;
  border-radius: inherit;
  background: #0e9f6e;
  transition: width 400ms ease;
}

.task-map-loading small {
  margin-top: 8px;
  color: #0b8f65;
  font-weight: 700;
}

.task-map-error svg { color: #c44b42; }

.task-map-error button {
  min-height: 40px;
  margin-top: 20px;
  padding: 0 18px;
  border: 0;
  border-radius: 6px;
  background: #0e9f6e;
  color: #fff;
  font-weight: 700;
  cursor: pointer;
}

.mind-map-canvas {
  min-height: 620px;
  padding: 24px 0 0;
}

.resource-back-button {
  position: fixed;
  top: 18px;
  left: 96px;
  z-index: 20;
  height: 42px;
  padding: 0 18px;
  display: inline-flex;
  align-items: center;
  gap: 8px;
  border: 1px solid #cdefe3;
  border-radius: 6px;
  background: rgba(255, 255, 255, 0.96);
  color: #0e9f6e;
  font-size: 14px;
  font-weight: 700;
  box-shadow: 0 10px 26px rgba(31, 72, 66, 0.1);
  cursor: pointer;
}

.resource-back-button:hover {
  background: #f1fbf7;
  transform: translateY(-1px);
}

.spin { animation: map-spin 900ms linear infinite; }

@keyframes map-spin { to { transform: rotate(360deg); } }
@keyframes map-pulse {
  0% { opacity: 0.8; transform: scale(0.35); }
  100% { opacity: 0; transform: scale(1); }
}

@media (max-width: 860px) {
  .wizard-hero { min-height: 440px; }
  .wizard-hero h1 { font-size: 36px; }
}

@media (max-width: 640px) {
  .mind-map-page {
    height: calc(100vh - 58px);
    min-height: 520px;
  }

  .mind-map-page.standalone {
    height: 100vh;
    min-height: 100vh;
    padding: 68px 10px 10px;
  }

  .task-map-shell { width: calc(100% - 20px); padding-bottom: 24px; }
  .mind-map-create-shell { padding: 20px 0 40px; }
  .wizard-hero {
    width: calc(100% - 24px);
    min-height: 440px;
    padding: 18px 0 28px;
  }
  .wizard-hero h1 { margin-top: 16px; font-size: 29px; }
  .wizard-hero > p:not(.create-error) { font-size: 13px; }
  .wizard-composer { margin-top: 26px; }
  .wizard-input-shell { min-height: 70px; padding-left: 16px; border-radius: 24px; }
  .wizard-input-shell > button { width: 50px; height: 50px; }
  .wizard-suggestions > span { width: 100%; }
  .wizard-capabilities { grid-template-columns: 1fr; margin-top: 26px; }
  .wizard-capabilities > div { justify-content: flex-start; padding: 12px 18px; }
  .wizard-capabilities > div + div { border-top: 1px solid #dce8e2; border-left: 0; }
  .mind-map-history-band { width: calc(100% - 24px); padding-top: 24px; }
  .task-map-header { display: block; }
  .task-map-header h1 { font-size: 22px; }
  .task-header-actions { justify-content: space-between; margin-top: 16px; }

  .mind-map-canvas {
    min-height: 520px;
    padding: 24px 0 0;
  }
  .resource-back-button { left: 92px; }
}

@media (prefers-reduced-motion: reduce) {
  .spin,
  .loading-rings i { animation: none; }
}
</style>
