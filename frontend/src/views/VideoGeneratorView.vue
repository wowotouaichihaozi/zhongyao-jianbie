<script setup>
import '@vue-flow/core/dist/style.css'
import '@vue-flow/core/dist/theme-default.css'
import '@vue-flow/controls/dist/style.css'

import { computed, onBeforeUnmount, onMounted, reactive, ref } from 'vue'
import { Background } from '@vue-flow/background'
import { Controls } from '@vue-flow/controls'
import { VueFlow } from '@vue-flow/core'
import {
  ArrowLeft,
  CircleAlert,
  Clapperboard,
  Download,
  ExternalLink,
  FileText,
  Film,
  Gauge,
  History,
  LoaderCircle,
  Play,
  RotateCcw,
  Server,
  Sparkles,
  Volume2,
} from 'lucide-vue-next'
import { useRoute } from 'vue-router'
import VideoWorkflowNode from '../components/video/VideoWorkflowNode.vue'
import {
  getXiaoZhiTask,
  startGeneratedVideoTask,
  startPersonalizedResourceAgentTask,
} from '../services/api.js'

const route = useRoute()
const WORKFLOW_STEPS = [
  { id: 'request', label: '需求与成本校验', hint: '等待用户确认参数' },
  { id: 'planning', label: '画像与脚本规划', hint: '生成分镜和旁白脚本' },
  { id: 'images', label: '视频首图批处理', hint: '按分镜并行生成首帧' },
  { id: 'tts', label: 'TTS 配音批处理', hint: '生成片段配音素材' },
  { id: 'videos', label: '视频片段批处理', hint: '调用所选视频模型' },
  { id: 'composing', label: '服务端剪辑与字幕', hint: 'FFmpeg 合并并烧录字幕' },
  { id: 'validating', label: '成片质量校验', hint: '检查视频流、音频流与时长' },
  { id: 'complete', label: '成片就绪', hint: '视频已保存到个人资源' },
]
const STAGE_INDEX = Object.fromEntries(WORKFLOW_STEPS.map((step, index) => [step.id, index]))
const VIDEO_ENGINES = [
  { id: 'seedance_1_5_coze', label: 'Seedance 1.5' },
  { id: 'seedance_2_mini', label: 'Seedance 2 Mini' },
  { id: 'seedance_2', label: 'Seedance 2' },
]
const ENGINE_LABELS = Object.fromEntries(VIDEO_ENGINES.map(engine => [engine.id, engine.label]))
const VIDEO_RESOLUTIONS = ['480p', '720p', '1080p']
const ACTIVE_STATUSES = new Set(['queued', 'running'])
const WAITING_STATUSES = new Set(['waiting', 'waiting_for_user'])

const form = reactive({
  prompt: String(route.query.prompt || route.query.topic || ''),
  targetDuration: normalizeNumber(route.query.duration, 30, 20, 60),
  videoEngine: VIDEO_ENGINES.some(engine => engine.id === String(route.query.videoEngine || ''))
    ? String(route.query.videoEngine)
    : VIDEO_ENGINES[0].id,
  resolution: VIDEO_RESOLUTIONS.includes(String(route.query.resolution || ''))
    ? String(route.query.resolution)
    : '720p',
  voice: String(route.query.voice || 'nova'),
  style: String(route.query.style || '二维科普动画'),
})

const task = ref(null)
const busy = ref(false)
const error = ref('')
const selectedNodeId = ref('request')
const localLogs = ref([])
const previewErrors = ref({})
let refreshTimer = 0

const result = computed(() => task.value?.result && typeof task.value.result === 'object' ? task.value.result : {})
const taskStatus = computed(() => String(task.value?.status || ''))
const isActive = computed(() => ACTIVE_STATUSES.has(taskStatus.value))
const isWaiting = computed(() => WAITING_STATUSES.has(taskStatus.value) || result.value.currentStage === 'waiting_for_user')
const isTerminal = computed(() => ['complete', 'failed', 'cancelled'].includes(taskStatus.value))
const progress = computed(() => clamp(Number(result.value.progress || 0), 0, 100))
const currentStage = computed(() => normalizeStage(result.value.currentStage, taskStatus.value))
const segments = computed(() => Array.isArray(result.value.segments) ? result.value.segments : [])
const plan = computed(() => result.value.plan && typeof result.value.plan === 'object' ? result.value.plan : null)
const videoResource = computed(() => result.value.selectedResource || null)
const activeVideoEngine = computed(() => String(result.value.engine || result.value.params?.videoEngine || form.videoEngine))
const engineLabel = computed(() => ENGINE_LABELS[activeVideoEngine.value] || ENGINE_LABELS[form.videoEngine])
const estimatedSegments = computed(() => Math.max(1, Math.round(form.targetDuration / 10)))
const canStart = computed(() => Boolean(form.prompt.trim()) && !busy.value && !isActive.value && (!task.value || isWaiting.value || taskStatus.value === 'failed'))

const workflowState = computed(() => {
  const normalizedStage = currentStage.value
  const activeIndex = STAGE_INDEX[normalizedStage] ?? 0
  const failed = taskStatus.value === 'failed'
  const waiting = isWaiting.value
  return Object.fromEntries(WORKFLOW_STEPS.map((step, index) => {
    let status = 'idle'
    let nodeProgress = 0
    let message = ''
    if (!task.value) {
      status = step.id === 'request' ? 'waiting' : 'idle'
    } else if (waiting) {
      status = step.id === 'request' ? 'waiting' : 'idle'
      message = step.id === 'request' ? '已收到学习路径提示词，等待确认参数' : ''
    } else if (taskStatus.value === 'complete') {
      status = 'completed'
      nodeProgress = 100
    } else if (index < activeIndex) {
      status = 'completed'
      nodeProgress = 100
    } else if (index === activeIndex) {
      status = failed ? 'failed' : 'running'
      nodeProgress = failed ? 100 : Math.max(6, progress.value)
      message = String(task.value?.error || result.value.message || '')
    }
    return [step.id, {
      ...step,
      status,
      progress: nodeProgress,
      message,
      selected: selectedNodeId.value === step.id,
    }]
  }))
})

const flowNodes = computed(() => WORKFLOW_STEPS.map((step, index) => ({
  id: step.id,
  type: 'video-workflow',
  position: { x: 44 + (index % 4) * 236, y: 54 + Math.floor(index / 4) * 174 },
  data: workflowState.value[step.id],
})))

const flowEdges = computed(() => WORKFLOW_STEPS.slice(0, -1).map((step, index) => {
  const next = WORKFLOW_STEPS[index + 1]
  return {
    id: `${step.id}-${next.id}`,
    source: step.id,
    target: next.id,
    type: 'smoothstep',
    animated: workflowState.value[step.id]?.status === 'completed'
      && workflowState.value[next.id]?.status === 'running',
  }
}))

const selectedNode = computed(() => workflowState.value[selectedNodeId.value] || workflowState.value.request)
const selectedFacts = computed(() => {
  const readyCount = field => segments.value.filter(segment => Boolean(segment?.[field])).length
  const facts = {
    request: [
      { label: '创作要求', value: form.prompt || '等待输入' },
      { label: '参考时长', value: `${form.targetDuration} 秒 · 预计 ${estimatedSegments.value} 个镜头` },
      { label: '视频模型', value: ENGINE_LABELS[form.videoEngine] },
      { label: '成片规格', value: `16:9 · ${form.resolution} · ${form.style}` },
      { label: '配音音色', value: form.voice },
    ],
    planning: plan.value ? [
      { label: '成片标题', value: String(plan.value.title || result.value.topic || '') },
      { label: '内容摘要', value: String(plan.value.summary || '') },
      { label: '规划结果', value: `${segments.value.length} 个镜头 · 约 ${segments.value.reduce((sum, item) => sum + Number(item.duration || 0), 0)} 秒` },
    ] : [],
    images: [{ label: '首图进度', value: `${readyCount('imageReady')}/${segments.value.length} 张已就绪` }],
    tts: [{ label: '配音进度', value: `${readyCount('audioReady')}/${segments.value.length} 条已就绪` }],
    videos: [
      { label: '视频进度', value: `${readyCount('videoReady')}/${segments.value.length} 段已就绪` },
      { label: '当前模型', value: engineLabel.value },
    ],
    composing: [
      { label: '剪辑位置', value: '服务端 FFmpeg' },
      { label: '成片处理', value: '统一画幅、混合配音、烧录中文字幕' },
    ],
    validating: [{ label: '校验项目', value: 'H.264 视频流、AAC 音频流、时长与可拖动播放' }],
    complete: videoResource.value ? [
      { label: '成片标题', value: String(videoResource.value.title || '') },
      { label: '成片时长', value: `${Number(videoResource.value.content?.duration || 0)} 秒` },
      { label: '保存状态', value: '已保存到个人视频资源' },
    ] : [],
  }
  return facts[selectedNodeId.value] || []
})

const selectedSegmentDetails = computed(() => {
  if (['request', 'complete'].includes(selectedNodeId.value)) return []
  return segments.value.map((segment, index) => {
    const fields = []
    const media = []
    if (['planning', 'images'].includes(selectedNodeId.value) && segment.image_prompt) {
      fields.push({ label: '首图提示词', value: String(segment.image_prompt) })
    }
    if (['planning', 'tts', 'composing'].includes(selectedNodeId.value) && segment.narration) {
      fields.push({ label: '字幕与配音', value: String(segment.narration) })
    }
    if (['planning', 'videos'].includes(selectedNodeId.value) && segment.video_prompt) {
      fields.push({ label: '视频提示词', value: String(segment.video_prompt) })
    }
    if (selectedNodeId.value === 'images' && segment.imageUrl) {
      media.push(mediaItem(segment, 'image', `第 ${index + 1} 段首图`, segment.imageUrl))
    }
    if (selectedNodeId.value === 'tts' && segment.audioUrl) {
      media.push(mediaItem(segment, 'audio', `第 ${index + 1} 段配音`, segment.audioUrl))
    }
    if (['videos', 'composing'].includes(selectedNodeId.value) && segment.videoUrl) {
      media.push(mediaItem(segment, 'video', `第 ${index + 1} 段视频`, segment.videoUrl))
    }
    return {
      id: String(segment.id || `segment-${index + 1}`),
      title: `${String(index + 1).padStart(2, '0')} · ${segment.title || `镜头 ${index + 1}`}`,
      duration: Number(segment.duration || 0),
      fields,
      media,
    }
  })
})

const eventLogs = computed(() => {
  const backendLogs = Array.isArray(result.value.logs) ? result.value.logs : []
  return [...backendLogs, ...localLogs.value]
    .filter(item => item && (item.message || item.text))
    .slice(-40)
    .reverse()
    .map((item, index) => ({
      id: `${item.time || 'event'}-${index}-${item.stage || ''}`,
      time: formatTime(item.time),
      text: String(item.message || item.text || ''),
    }))
})

function clamp(value, min, max) {
  return Math.max(min, Math.min(max, Number.isFinite(value) ? value : min))
}

function normalizeNumber(value, fallback, min, max) {
  const parsed = Number(value)
  return clamp(Number.isFinite(parsed) ? parsed : fallback, min, max)
}

function normalizeStage(stage, status) {
  const raw = String(stage || '')
  if (raw === 'waiting_for_user' || WAITING_STATUSES.has(status)) return 'request'
  if (raw in STAGE_INDEX) return raw
  if (status === 'complete') return 'complete'
  if (status === 'failed') return raw in STAGE_INDEX ? raw : 'request'
  if (status === 'queued') return 'request'
  return 'request'
}

function mediaItem(segment, kind, label, url) {
  return { id: `${segment.id}-${kind}`, kind, label, url: String(url) }
}

function formatTime(value) {
  const date = value ? new Date(value) : new Date()
  if (Number.isNaN(date.getTime())) return String(value || '')
  return date.toLocaleTimeString('zh-CN', { hour12: false })
}

function addLocalLog(text) {
  localLogs.value.push({ time: new Date().toISOString(), text })
  localLogs.value = localLogs.value.slice(-12)
}

function selectNode({ node }) {
  selectedNodeId.value = String(node.id)
}

function applyTask(updated, { hydrateForm = false } = {}) {
  if (!updated?.taskId) return
  task.value = updated
  const params = updated.result?.params && typeof updated.result.params === 'object' ? updated.result.params : {}
  if (hydrateForm && !isActive.value) {
    form.prompt = String(route.query.prompt || updated.prompt || updated.result?.topic || form.prompt)
    form.targetDuration = normalizeNumber(params.duration, form.targetDuration, 20, 60)
    form.style = String(params.style || form.style)
    form.voice = String(params.voice || form.voice)
    form.resolution = String(params.resolution || form.resolution)
    if (ENGINE_LABELS[params.videoEngine]) form.videoEngine = params.videoEngine
  }
  if (updated.status === 'failed') {
    error.value = String(updated.error || updated.result?.message || '视频生成失败')
  } else if (updated.status === 'complete') {
    error.value = ''
    selectedNodeId.value = 'complete'
  } else if (updated.result?.currentStage && updated.result.currentStage in STAGE_INDEX) {
    selectedNodeId.value = updated.result.currentStage
  }
}

function extractTask(response) {
  return response?.data?.task || response?.task || response?.data?.tasks?.[0] || response?.data || response || null
}

function clearRefreshTimer() {
  if (refreshTimer) window.clearTimeout(refreshTimer)
  refreshTimer = 0
}

function scheduleRefresh() {
  clearRefreshTimer()
  if (isActive.value) refreshTimer = window.setTimeout(refreshTask, 1500)
}

async function refreshTask() {
  if (!task.value?.taskId) return
  try {
    const response = await getXiaoZhiTask(task.value.taskId)
    applyTask(extractTask(response))
  } catch (value) {
    addLocalLog('状态连接暂时中断，稍后自动重试')
    error.value = value?.response?.data?.msg || value?.message || '任务状态读取失败'
  } finally {
    scheduleRefresh()
  }
}

async function startGeneration() {
  if (!canStart.value) return
  busy.value = true
  error.value = ''
  previewErrors.value = {}
  const params = {
    duration: form.targetDuration,
    style: form.style,
    voice: form.voice,
    resolution: form.resolution,
    videoEngine: form.videoEngine,
  }
  try {
    let response
    if (task.value?.taskId && (isWaiting.value || taskStatus.value === 'failed')) {
      response = await startGeneratedVideoTask(task.value.taskId, {
        prompt: form.prompt.trim(),
        params,
      })
      addLocalLog('已确认周任务参数，后台视频工作流开始运行')
    } else {
      const topic = String(route.query.topic || form.prompt).trim().slice(0, 80)
      const createdResponse = await startPersonalizedResourceAgentTask({
        resourceType: 'generated_video',
        topic,
        prompt: form.prompt.trim(),
        params,
      })
      const createdTask = extractTask(createdResponse)
      if (!createdTask?.taskId) throw new Error('未获得 AI 视频任务 ID')
      applyTask(createdTask)
      response = await startGeneratedVideoTask(createdTask.taskId, {
        prompt: form.prompt.trim(),
        params,
      })
      addLocalLog('用户已确认参数，视频工作流开始运行')
    }
    applyTask(extractTask(response))
    await refreshTask()
  } catch (value) {
    error.value = value?.response?.data?.msg || value?.message || '创建视频任务失败'
  } finally {
    busy.value = false
  }
}

function resetWorkspace() {
  clearRefreshTimer()
  task.value = null
  error.value = ''
  localLogs.value = []
  previewErrors.value = {}
  selectedNodeId.value = 'request'
}

function markPreviewError(item) {
  previewErrors.value = { ...previewErrors.value, [item.id]: true }
}

onMounted(async () => {
  const taskId = String(route.query.xzTask || '')
  if (!taskId) return
  task.value = { taskId, status: 'queued', result: {} }
  try {
    const response = await getXiaoZhiTask(taskId)
    applyTask(extractTask(response), { hydrateForm: true })
  } catch (value) {
    error.value = value?.response?.data?.msg || value?.message || '视频任务读取失败'
  } finally {
    scheduleRefresh()
  }
})

onBeforeUnmount(clearRefreshTimer)
</script>

<template>
  <main class="video-studio-page">
    <header class="studio-topbar">
      <RouterLink class="studio-back" to="/personalized-resources" title="返回个性化资源">
        <ArrowLeft :size="18" />
      </RouterLink>
      <div class="studio-brand">
        <span><Clapperboard :size="18" /></span>
        <strong>嵌智 Video Studio</strong>
        <small>AI 课程视频工作台</small>
      </div>
      <RouterLink
        class="studio-history"
        :to="{ path: '/personalized-resources', query: { category: 'generated_video' } }"
        target="_blank"
        rel="noopener noreferrer"
      >
        <History :size="15" />历史记录
      </RouterLink>
      <div class="runtime-state"><i :class="{ active: !error || isActive }" />持久化任务服务</div>
    </header>

    <div class="video-workspace">
      <aside class="studio-input-panel">
        <div class="studio-section-title"><Sparkles :size="16" /><span>创作输入</span></div>
        <label for="video-prompt">视频主题与要求</label>
        <textarea id="video-prompt" v-model="form.prompt" rows="7" maxlength="1200" :disabled="isActive || (task && !isWaiting)" placeholder="输入课程主题、讲解重点和目标受众" />

        <label>视频生成引擎</label>
        <div class="engine-switch" role="radiogroup" aria-label="视频生成引擎">
          <label v-for="engine in VIDEO_ENGINES" :key="engine.id" :class="{ active: form.videoEngine === engine.id }">
            <input v-model="form.videoEngine" type="radio" :value="engine.id" :disabled="isActive || (task && !isWaiting)" />
            <span>{{ engine.label }}</span>
          </label>
        </div>

        <div class="duration-row">
          <div><label for="video-duration">参考时长</label><strong>{{ form.targetDuration }} 秒</strong></div>
          <span>约 {{ estimatedSegments }} 个镜头</span>
        </div>
        <input id="video-duration" v-model.number="form.targetDuration" type="range" min="20" max="60" step="10" :disabled="isActive || (task && !isWaiting)" />

        <div class="input-columns">
          <div><label for="video-resolution">清晰度</label><select id="video-resolution" v-model="form.resolution" :disabled="isActive || (task && !isWaiting)"><option v-for="resolution in VIDEO_RESOLUTIONS" :key="resolution" :value="resolution">{{ resolution }}</option></select></div>
          <div><label for="video-voice">配音音色</label><select id="video-voice" v-model="form.voice" :disabled="isActive || (task && !isWaiting)"><option value="nova">Nova 女声</option><option value="shimmer">Shimmer 女声</option><option value="alloy">Alloy 中性</option><option value="onyx">Onyx 男声</option></select></div>
        </div>

        <label for="video-style">视觉风格</label>
        <select id="video-style" v-model="form.style" :disabled="isActive || (task && !isWaiting)">
          <option>二维科普动画</option><option>简洁教学插画</option><option>实验室纪实</option><option>科技信息图</option><option>电影感纪实短片</option>
        </select>

        <div class="cost-guard">
          <Gauge :size="17" />
          <div><strong>用户确认后才调用模型</strong><span>当前设置：{{ engineLabel }} · {{ form.targetDuration }} 秒 · {{ form.resolution }}</span></div>
        </div>

        <button v-if="!task || isWaiting || taskStatus === 'failed'" class="studio-primary" type="button" :disabled="!canStart" @click="startGeneration">
          <LoaderCircle v-if="busy || isActive" :size="17" class="spin" />
          <Play v-else :size="17" fill="currentColor" />
          {{ busy ? '正在提交' : isActive ? '后台生成中' : taskStatus === 'failed' ? '重试视频工作流' : '运行视频工作流' }}
        </button>
        <button v-else-if="isTerminal" class="studio-secondary" type="button" @click="resetWorkspace"><RotateCcw :size="16" />新建任务</button>
      </aside>

      <section class="studio-canvas-panel">
        <div class="canvas-heading">
          <div><h1>视频生成工作流</h1><p>{{ task ? `任务 ${task.taskId.slice(0, 12)} · ${taskStatus}` : '等待用户确认创作输入' }}</p></div>
          <div class="model-strip"><span><Server :size="14" />Agent Workflow</span><span><Film :size="14" />{{ engineLabel }}</span><span><Volume2 :size="14" />TTS + FFmpeg</span></div>
        </div>
        <div class="flow-canvas">
          <VueFlow :nodes="flowNodes" :edges="flowEdges" fit-view-on-init :min-zoom="0.55" :max-zoom="1.25" :nodes-draggable="false" @node-click="selectNode">
            <template #node-video-workflow="props"><VideoWorkflowNode v-bind="props" /></template>
            <Background :gap="22" color="#d7dce0" />
            <Controls position="bottom-right" />
          </VueFlow>
        </div>

        <div v-if="error" class="studio-error-bar"><CircleAlert :size="16" />{{ error }}</div>
        <div v-if="videoResource" class="output-bar">
          <div><strong>{{ videoResource.title }}</strong><span>{{ videoResource.description }}</span></div>
          <a :href="videoResource.content?.videoUrl" target="_blank" rel="noreferrer"><ExternalLink :size="15" />播放</a>
          <a :href="videoResource.content?.videoUrl" download><Download :size="15" />下载</a>
        </div>
      </section>

      <aside class="studio-detail-panel">
        <section class="node-inspector">
          <div class="studio-section-title"><FileText :size="16" /><span>节点详情</span></div>
          <div class="inspector-head"><strong>{{ selectedNode.label }}</strong><span :class="`status-${selectedNode.status}`">{{ selectedNode.status }}</span></div>
          <div class="inspector-meta"><span>进度 {{ selectedNode.progress }}%</span><span>总任务 {{ progress }}%</span></div>
          <p v-if="selectedNode.message" class="node-message">{{ selectedNode.message }}</p>

          <dl v-if="selectedFacts.length" class="node-facts">
            <div v-for="fact in selectedFacts" :key="fact.label"><dt>{{ fact.label }}</dt><dd>{{ fact.value }}</dd></div>
          </dl>

          <div v-if="selectedSegmentDetails.length" class="node-segments">
            <article v-for="detail in selectedSegmentDetails" :key="detail.id">
              <header><strong>{{ detail.title }}</strong><span v-if="detail.duration">{{ detail.duration }}s</span></header>
              <div v-for="field in detail.fields" :key="field.label" class="detail-field"><b>{{ field.label }}</b><p>{{ field.value }}</p></div>
              <div v-if="detail.media.length" class="media-previews">
                <figure v-for="item in detail.media" :key="item.id">
                  <div v-if="previewErrors[item.id]" class="preview-error">该素材暂时无法预览</div>
                  <img v-else-if="item.kind === 'image'" :src="item.url" :alt="item.label" loading="lazy" @error="markPreviewError(item)" />
                  <video v-else-if="item.kind === 'video'" :src="item.url" controls playsinline preload="metadata" @error="markPreviewError(item)" />
                  <audio v-else :src="item.url" controls preload="metadata" @error="markPreviewError(item)" />
                  <figcaption><span>{{ item.label }}</span><a :href="item.url" target="_blank" rel="noreferrer" title="打开媒体文件"><ExternalLink :size="12" /></a></figcaption>
                </figure>
              </div>
            </article>
          </div>
          <div v-else-if="!selectedFacts.length" class="studio-empty">该节点尚未产生内容</div>
        </section>

        <div class="panel-divider" />
        <div class="studio-section-title"><Film :size="16" /><span>片段批次</span><b>{{ segments.length }}</b></div>
        <div v-if="plan" class="plan-summary"><strong>{{ plan.title }}</strong><span>{{ plan.summary }}</span></div>
        <div class="segment-list">
          <article v-for="(segment, index) in segments" :key="segment.id">
            <div class="segment-index">{{ String(index + 1).padStart(2, '0') }}</div>
            <div><header><strong>{{ segment.title }}</strong><span>{{ segment.duration }}s</span></header><p>{{ segment.narration }}</p><footer><i :class="{ ready: segment.imageReady }">首图</i><i :class="{ ready: segment.audioReady }">配音</i><i :class="{ ready: segment.videoReady }">视频</i></footer></div>
          </article>
          <div v-if="!segments.length" class="studio-empty">运行后显示分镜、字幕与媒体状态</div>
        </div>

        <section class="event-log"><div class="studio-section-title"><span>运行记录</span></div><ol><li v-for="item in eventLogs" :key="item.id"><time>{{ item.time }}</time><span>{{ item.text }}</span></li></ol><div v-if="!eventLogs.length" class="studio-empty compact">暂无运行记录</div></section>
      </aside>
    </div>
  </main>
</template>

<style scoped>
.video-studio-page { --accent:#147d83; --accent-dark:#0f676d; --ink:#20282c; --muted:#6d7b80; min-height:calc(100vh - 72px); color:var(--ink); background:#eef2f3; }
.studio-topbar { height:56px; display:flex; align-items:center; gap:12px; padding:0 18px; background:#20282c; color:#fff; border-bottom:1px solid #384246; }
.studio-back { width:34px; height:34px; display:grid; place-items:center; color:#dbe4e6; border-radius:6px; }.studio-back:hover { background:#344044; }
.studio-brand { display:flex; align-items:center; gap:9px; min-width:0; }.studio-brand>span { width:32px; height:32px; display:grid; place-items:center; background:var(--accent); border-radius:6px; }.studio-topbar .studio-brand strong { font-size:15px; }.studio-brand small { padding-left:10px; color:#acb9bd; border-left:1px solid #4a5559; font-size:11px; }
:global(#app .studio-topbar .studio-brand strong) { color:#fff !important; }
.studio-history { margin-left:auto; display:flex; align-items:center; gap:6px; padding:7px 9px; border-radius:5px; color:#d8e3e5; background:#303b3f; text-decoration:none; font-size:10px; font-weight:700; }.studio-history:hover { color:#fff; background:#3b484c; }
.runtime-state { display:flex; align-items:center; gap:8px; color:#c5d0d3; font-size:11px; }.runtime-state i { width:7px; height:7px; border-radius:50%; background:#d75b55; }.runtime-state i.active { background:#46b879; }
.video-workspace { height:calc(100vh - 128px); min-height:620px; display:grid; grid-template-columns:292px minmax(600px,1fr) 352px; overflow:hidden; }
.studio-input-panel,.studio-detail-panel { min-width:0; padding:18px; overflow-y:auto; background:#fff; }.studio-input-panel { border-right:1px solid #dce2e4; }.studio-detail-panel { border-left:1px solid #dce2e4; }
.studio-section-title { min-height:26px; display:flex; align-items:center; gap:8px; margin-bottom:13px; font-size:12px; font-weight:750; }.studio-section-title b { margin-left:auto; min-width:25px; height:20px; display:grid; place-items:center; border-radius:4px; background:#e5f3f2; color:var(--accent); font-size:10px; }
.studio-input-panel>label,.studio-input-panel .input-columns label,.duration-row label { display:block; margin:13px 0 6px; color:#627177; font-size:11px; font-weight:700; }
textarea,select { width:100%; border:1px solid #d2dadd; border-radius:6px; background:#fff; color:#293438; outline:none; font:inherit; letter-spacing:0; } textarea { min-height:128px; padding:10px; resize:vertical; line-height:1.6; font-size:12px; } select { height:36px; padding:0 9px; font-size:11px; } textarea:focus,select:focus { border-color:var(--accent); box-shadow:0 0 0 2px #dff1ef; } textarea:disabled,select:disabled { background:#f4f6f7; color:#7b878b; }
.engine-switch { display:grid; grid-template-columns:repeat(3,minmax(0,1fr)); min-height:40px; padding:3px; border:1px solid #d2dadd; border-radius:6px; background:#eef2f3; }.engine-switch label { min-width:0; display:grid; place-items:center; margin:0; padding:3px; border-radius:4px; color:#67757a; cursor:pointer; text-align:center; font-size:9px; line-height:1.2; }.engine-switch label.active { background:#fff; color:var(--accent-dark); box-shadow:0 1px 4px rgba(31,47,52,.14); }.engine-switch input { position:absolute; opacity:0; pointer-events:none; }.engine-switch label:has(input:disabled) { opacity:.62; cursor:not-allowed; }
.duration-row { display:flex; align-items:end; justify-content:space-between; margin-top:4px; }.duration-row>div { display:flex; align-items:baseline; gap:8px; }.duration-row strong { font-size:15px; }.duration-row span { color:#8a969a; font-size:9px; } input[type='range'] { width:100%; accent-color:var(--accent); }
.input-columns { display:grid; grid-template-columns:1fr 1fr; gap:10px; }
.cost-guard { display:flex; gap:10px; align-items:flex-start; margin:18px 0; padding:10px; border:1px solid #cfe5d6; border-radius:6px; background:#f0f7f2; color:#276344; }.cost-guard div { display:flex; flex-direction:column; gap:3px; }.cost-guard strong { font-size:11px; }.cost-guard span { color:#61806d; font-size:9px; line-height:1.45; }
.studio-primary,.studio-secondary { width:100%; min-height:39px; display:flex; align-items:center; justify-content:center; gap:8px; border:0; border-radius:6px; cursor:pointer; font-weight:700; font-size:12px; }.studio-primary { color:#fff; background:var(--accent); }.studio-primary:hover:not(:disabled) { background:var(--accent-dark); }.studio-primary:disabled { opacity:.5; cursor:not-allowed; }.studio-secondary { color:#3d4a4f; background:#edf1f2; }.studio-secondary:hover { background:#e2e8e9; }
:global(#app .video-studio-page .studio-primary) { border-color:var(--accent) !important; background:var(--accent) !important; color:#fff !important; }
:global(#app .video-studio-page .studio-primary:hover:not(:disabled)) { border-color:var(--accent-dark) !important; background:var(--accent-dark) !important; color:#fff !important; }
.studio-canvas-panel { min-width:0; display:grid; grid-template-rows:66px minmax(340px,1fr) auto auto; overflow:hidden; background:#f4f6f7; }.canvas-heading { display:flex; align-items:center; justify-content:space-between; gap:16px; padding:0 18px; border-bottom:1px solid #dce2e4; background:#fff; }.canvas-heading h1 { margin:0 0 4px; font-size:15px; }.canvas-heading p { margin:0; color:#8a9599; font-size:10px; }.model-strip { display:flex; gap:6px; }.model-strip span { display:flex; align-items:center; gap:5px; padding:5px 7px; border:1px solid #dfe5e7; border-radius:5px; color:#5d6a6f; background:#f2f5f5; font-size:9px; }
.flow-canvas { min-height:0; }.studio-error-bar { display:flex; align-items:center; gap:8px; padding:10px 16px; border-top:1px solid #ecc8c4; color:#a23d36; background:#fff1f0; font-size:11px; }.output-bar { display:grid; grid-template-columns:minmax(0,1fr) auto auto; align-items:center; gap:10px; padding:10px 16px; border-top:1px solid #dce2e4; background:#fff; }.output-bar>div { min-width:0; display:flex; flex-direction:column; gap:3px; }.output-bar strong,.output-bar span { overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }.output-bar strong { font-size:12px; }.output-bar span { color:#77858a; font-size:9px; }.output-bar a { display:flex; align-items:center; gap:5px; padding:7px 9px; border-radius:5px; color:var(--accent-dark); background:#e7f4f3; text-decoration:none; font-size:10px; font-weight:700; }
:deep(.video-workflow-node) { width:202px; min-height:98px; padding:12px; border:1px solid #d4dcdf; border-radius:7px; background:#fff; box-shadow:0 4px 12px rgba(35,48,52,.06); cursor:pointer; }.spin { animation:spin 1s linear infinite; } @keyframes spin { to { transform:rotate(360deg) } }
:deep(.video-workflow-node.is-selected) { border-color:var(--accent); box-shadow:0 0 0 2px #dcefed,0 5px 14px rgba(35,48,52,.08); }:deep(.video-workflow-node.is-running) { border-color:#2b9ea1; }:deep(.video-workflow-node.is-completed) { border-color:#70ba88; }:deep(.video-workflow-node.is-failed) { border-color:#dc746d; }:deep(.video-workflow-node.is-waiting) { border-color:#d7a34a; }
:deep(.video-node-head) { display:grid; grid-template-columns:18px minmax(0,1fr) auto; align-items:center; gap:7px; font-size:10px; font-weight:750; }:deep(.video-node-head b) { color:#737f84; font-size:9px; }:deep(.video-node-track) { height:3px; overflow:hidden; margin:10px 0; background:#e9edef; }:deep(.video-node-track span) { display:block; height:100%; background:var(--accent); transition:width .25s; }:deep(.is-completed .video-node-track span) { background:#42a967; }:deep(.is-failed .video-node-track span) { background:#d24f4f; }:deep(.is-waiting .video-node-track span) { background:#cf9634; }:deep(.video-workflow-node p) { height:28px; margin:0; overflow:hidden; color:#818c90; font-size:9px; line-height:1.5; }
:deep(.vue-flow__edge-path) { stroke:#a9b3b6; stroke-width:1.5; }:deep(.vue-flow__handle) { width:7px; height:7px; border:2px solid #fff; background:#7c898e; }
.inspector-head { display:flex; align-items:center; justify-content:space-between; gap:8px; }.inspector-head strong { min-width:0; font-size:12px; }.inspector-head>span { flex:0 0 auto; padding:3px 6px; border-radius:4px; color:#68757a; background:#edf1f2; font-size:8px; font-weight:750; text-transform:uppercase; }.inspector-head>span.status-running { color:#0f6e73; background:#dff2f1; }.inspector-head>span.status-completed { color:#277447; background:#e1f1e6; }.inspector-head>span.status-failed { color:#a23e38; background:#f8e4e2; }.inspector-head>span.status-waiting { color:#865d1d; background:#fff0d7; }
.inspector-meta { display:flex; gap:12px; margin:7px 0 10px; color:#899599; font-size:9px; }.node-message { margin:0 0 10px; padding:8px 9px; border-left:3px solid var(--accent); color:#566368; background:#edf6f5; font-size:9px; line-height:1.55; }
.node-facts { margin:0 0 12px; border-top:1px solid #e1e6e8; }.node-facts div { display:grid; grid-template-columns:72px minmax(0,1fr); gap:8px; padding:8px 0; border-bottom:1px solid #e9edef; }.node-facts dt { color:#859196; font-size:9px; font-weight:700; }.node-facts dd { min-width:0; margin:0; color:#3d494e; font-size:9px; line-height:1.55; overflow-wrap:anywhere; }
.node-segments { border-top:1px solid #dfe5e7; }.node-segments>article { padding:12px 0 14px; border-bottom:1px solid #dfe5e7; }.node-segments>article>header { display:flex; align-items:center; justify-content:space-between; gap:8px; margin-bottom:9px; }.node-segments>article>header strong { min-width:0; font-size:11px; }.node-segments>article>header span { color:var(--accent); font-size:9px; font-weight:700; }.detail-field { margin-top:8px; }.detail-field b { display:block; margin-bottom:3px; color:#78858a; font-size:8px; }.detail-field p { margin:0; color:#404c50; font-size:9px; line-height:1.6; overflow-wrap:anywhere; }
.media-previews { margin-top:10px; }.media-previews figure { margin:0 0 10px; overflow:hidden; border:1px solid #d9e0e2; border-radius:6px; background:#182125; }.media-previews img,.media-previews video { display:block; width:100%; aspect-ratio:16/9; object-fit:contain; background:#182125; }.media-previews audio { display:block; width:100%; min-height:42px; background:#f3f5f6; }.media-previews figcaption { min-height:30px; display:flex; align-items:center; justify-content:space-between; padding:6px 8px; color:#657277; background:#fff; font-size:9px; }.media-previews figcaption a { width:24px; height:24px; display:grid; place-items:center; color:var(--accent); border-radius:4px; }.preview-error { min-height:88px; display:grid; place-items:center; color:#a23d36; background:#fff1f0; font-size:9px; }
.panel-divider { height:1px; margin:18px 0; background:#e0e6e8; }.plan-summary { display:flex; flex-direction:column; gap:4px; padding:10px; margin-bottom:12px; border-left:3px solid var(--accent); background:#eef6f5; }.plan-summary strong { font-size:11px; }.plan-summary span { color:#718085; font-size:9px; line-height:1.5; }
.segment-list { display:flex; flex-direction:column; gap:8px; }.segment-list article { display:grid; grid-template-columns:30px minmax(0,1fr); gap:9px; padding:10px; border:1px solid #dde3e5; border-radius:6px; }.segment-index { width:28px; height:28px; display:grid; place-items:center; border-radius:5px; color:#fff; background:#253034; font-size:10px; }.segment-list header { display:flex; justify-content:space-between; gap:8px; }.segment-list header strong { min-width:0; font-size:10px; }.segment-list header span { color:var(--accent); font-size:9px; font-weight:700; }.segment-list p { margin:7px 0; color:#6c797e; font-size:9px; line-height:1.55; }.segment-list footer { display:flex; gap:5px; }.segment-list i { padding:2px 5px; border-radius:3px; color:#969fa3; background:#edf0f1; font-size:8px; font-style:normal; }.segment-list i.ready { color:#267445; background:#e0f1e6; }
.studio-empty { padding:30px 12px; border:1px dashed #d4dcdf; color:#97a1a5; text-align:center; font-size:9px; line-height:1.7; }.studio-empty.compact { padding:14px 8px; }.event-log { margin-top:20px; padding-top:14px; border-top:1px solid #e0e6e8; }.event-log ol { margin:0; padding:0; list-style:none; }.event-log li { display:grid; grid-template-columns:54px minmax(0,1fr); gap:7px; padding:5px 0; border-bottom:1px solid #eef1f2; font-size:9px; }.event-log time { color:#9aa4a8; }.event-log span { color:#58666b; line-height:1.45; }
@media (max-width:1280px) { .video-workspace { grid-template-columns:270px minmax(560px,1fr) 318px; }.studio-input-panel,.studio-detail-panel { padding:15px; }.model-strip span:first-child { display:none; } }
@media (max-width:1050px) { .video-workspace { height:auto; min-height:calc(100vh - 128px); grid-template-columns:280px minmax(0,1fr); overflow:visible; }.studio-canvas-panel { min-height:620px; }.studio-detail-panel { grid-column:1/-1; border:0; border-top:1px solid #dce2e4; }.node-inspector { max-width:none; }.model-strip { display:none; } }
@media (max-width:720px) { .video-studio-page { min-height:100vh; }.studio-topbar { padding:0 10px; }.studio-brand small,.runtime-state { display:none; }.studio-history { padding:7px; font-size:0; }.video-workspace { display:block; min-height:0; }.studio-input-panel,.studio-detail-panel { overflow:visible; }.studio-canvas-panel { min-height:560px; grid-template-rows:62px 430px auto auto; }.input-columns { grid-template-columns:1fr; }.output-bar { grid-template-columns:1fr 1fr; }.output-bar>div { grid-column:1/-1; } }
</style>
