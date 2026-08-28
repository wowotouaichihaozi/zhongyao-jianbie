<template>
  <main class="video-search-page" :class="{ standalone: isResourceToolPage }">
    <button v-if="isResourceToolPage" type="button" class="resource-back-button" @click="goBackToResources">
      <ArrowLeft :size="18" :stroke-width="2.2" aria-hidden="true" />
      <span>返回个性化资源</span>
    </button>

    <section class="video-search-shell" aria-live="polite">
      <header class="video-search-header">
        <div>
          <span class="video-search-kicker">
            <Clapperboard :size="17" stroke-width="2.2" aria-hidden="true" />
            岐小智视频查找智能体
          </span>
          <h1>学习视频</h1>
          <p>结合当前学习画像、任务主题和联网检索结果筛选课程视频。</p>
        </div>
      </header>

      <form class="video-search-form" @submit.prevent="startSearch">
        <label for="video-search-topic">学习主题</label>
        <div>
          <input
            id="video-search-topic"
            v-model.trim="topic"
            type="search"
            maxlength="100"
            placeholder="例如：四诊合参与舌脉辨析"
            :disabled="isPending"
          />
          <button type="submit" :disabled="!topic || isPending">
            <Search :size="18" stroke-width="2.2" aria-hidden="true" />
            <span>{{ isPending ? '检索中' : '开始检索' }}</span>
          </button>
        </div>
      </form>

      <LearningFeedbackActions
        v-if="feedbackTask"
        class="video-feedback"
        :task="feedbackTask"
        :cache-key="String(route.query.cacheKey || '')"
        :route-path="route.fullPath"
      />

      <div v-if="isPending" class="video-loading">
        <span class="loading-rings" aria-hidden="true"><i></i><i></i><i></i></span>
        <strong>正在筛选学习视频</strong>
        <p>检索完成后将在这里直接显示结果。</p>
      </div>

      <div v-else-if="taskError" class="video-error" role="alert">
        <CircleAlert :size="36" stroke-width="1.9" aria-hidden="true" />
        <strong>视频检索未完成</strong>
        <p>{{ taskError }}</p>
        <button type="button" @click="startSearch">重新检索</button>
      </div>

      <section v-else-if="videos.length" class="video-results">
        <header>
          <div>
            <span>检索结果</span>
            <h2>{{ selectedResource?.title || topic }}</h2>
          </div>
          <span class="result-count">{{ videos.length }} 个视频</span>
        </header>

        <div class="video-grid">
          <article v-for="video in videos" :key="video.bvid || video.url" class="video-card">
            <a :href="video.url" target="_blank" rel="noopener noreferrer" class="video-cover">
              <img
                v-if="video.cover"
                :src="videoCoverUrl(video.cover)"
                :alt="video.title"
                loading="lazy"
                @error="hideBrokenCover"
              />
              <span class="cover-fallback" aria-hidden="true">
                <PlayCircle :size="38" stroke-width="1.7" />
              </span>
              <em v-if="video.duration">{{ video.duration }}</em>
            </a>
            <div class="video-card-body">
              <a :href="video.url" target="_blank" rel="noopener noreferrer">{{ video.title }}</a>
              <p v-if="video.snippet">{{ video.snippet }}</p>
              <div>
                <span v-if="video.author"><UserRound :size="14" aria-hidden="true" />{{ video.author }}</span>
                <span v-if="video.bvid">{{ video.bvid }}</span>
              </div>
            </div>
          </article>
        </div>
      </section>

      <div v-else class="video-empty">
        <Clapperboard :size="42" stroke-width="1.6" aria-hidden="true" />
        <strong>等待检索主题</strong>
      </div>
    </section>
  </main>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  ArrowLeft,
  CheckCircle2,
  CircleAlert,
  Clapperboard,
  LoaderCircle,
  PlayCircle,
  Search,
  UserRound,
} from 'lucide-vue-next'
import LearningFeedbackActions from '../components/LearningFeedbackActions.vue'
import { getXiaoZhiTask, startPersonalizedResourceAgentTask } from '../services/api.js'
import {
  markNodeCacheComplete,
  markNodeCacheError,
  markNodeCacheStarted,
} from '../services/learningPathNodeCache.js'

const route = useRoute()
const router = useRouter()
const topic = ref(String(route.query.keyword || route.query.topic || '').trim())
const taskId = ref(String(route.query.xzTask || '').trim())
const task = ref(null)
const selectedResource = ref(null)
const taskError = ref('')
let pollTimer = null
let autostartConsumed = false

const isResourceToolPage = computed(() => route.meta?.resourceTool === true || route.path.startsWith('/personalized-resources/'))
const taskStatus = computed(() => String(task.value?.status || (taskId.value ? 'loading' : 'idle')))
const isPending = computed(() => ['loading', 'queued', 'running'].includes(taskStatus.value) && !taskError.value)
const taskProgress = computed(() => {
  if (taskStatus.value === 'loading') return 8
  const progress = Number(task.value?.result?.progress || 0)
  if (taskStatus.value === 'queued') return Math.max(8, Math.min(18, progress || 8))
  return Math.max(20, Math.min(96, progress || 38))
})
const taskStateClass = computed(() => (taskError.value ? 'failed' : (isPending.value ? 'running' : 'complete')))
const taskStatusText = computed(() => {
  if (taskError.value) return '检索失败'
  if (taskStatus.value === 'loading') return '正在读取任务'
  if (taskStatus.value === 'queued') return '等待后台检索'
  if (taskStatus.value === 'running') return '后台检索中'
  return '检索完成'
})
const taskMessage = computed(() => String(
  task.value?.result?.message
  || '岐小智正在读取学习画像、检索课程视频并校验结果。',
))
const videos = computed(() => {
  const result = task.value?.result || {}
  const candidates = [
    selectedResource.value?.metadata?.results,
    selectedResource.value?.results,
    result.videos,
    result.searchResults,
  ]
  return candidates.find(Array.isArray) || []
})
const quality = computed(() => (
  selectedResource.value?.qualityEvaluation
  || selectedResource.value?.metadata?.qualityEvaluation
  || task.value?.result?.qualityEvaluation
  || {}
))
const citationCount = computed(() => Math.max(
  Number(quality.value?.citationCount || 0),
  Array.isArray(task.value?.result?.knowledgeSources) ? task.value.result.knowledgeSources.length : 0,
  Array.isArray(selectedResource.value?.metadata?.knowledgeSources) ? selectedResource.value.metadata.knowledgeSources.length : 0,
))
const feedbackTask = computed(() => (taskStatus.value === 'complete' ? task.value : null))

watch(
  () => route.query.xzTask,
  (value) => {
    const nextTaskId = String(value || '').trim()
    if (nextTaskId === taskId.value && task.value) return
    stopPolling()
    taskId.value = nextTaskId
    task.value = null
    selectedResource.value = null
    taskError.value = ''
    if (nextTaskId) void loadTask()
  },
  { immediate: true },
)

onMounted(() => {
  if (!taskId.value && route.query.autostart === '1' && topic.value && !autostartConsumed) {
    autostartConsumed = true
    void startSearch()
  }
})

onBeforeUnmount(stopPolling)

async function startSearch() {
  if (!topic.value || isPending.value) return
  stopPolling()
  taskError.value = ''
  task.value = null
  selectedResource.value = null
  try {
    const response = await startPersonalizedResourceAgentTask({
      resourceType: 'video',
      topic: topic.value,
      prompt: `检索并筛选适合当前学习画像的 ${topic.value} 课程视频`,
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
    if (!nextTask?.taskId) throw new Error('未获得视频检索任务 ID')
    taskId.value = nextTask.taskId
    task.value = nextTask
    markTaskStarted(nextTask)
    await router.replace({
      query: {
        ...route.query,
        topic: topic.value,
        keyword: topic.value,
        autostart: undefined,
        xzTask: nextTask.taskId,
      },
    })
    startPolling()
    await loadTask()
  } catch (error) {
    taskError.value = error?.response?.data?.msg || error?.message || '视频检索任务创建失败'
    markTaskFailed(taskError.value)
  }
}

async function loadTask() {
  if (!taskId.value) return
  try {
    const response = await getXiaoZhiTask(taskId.value)
    const nextTask = response?.data?.task
    if (!nextTask) throw new Error('未找到对应的视频检索任务')
    task.value = nextTask
    if (['queued', 'running'].includes(nextTask.status)) {
      markTaskStarted(nextTask)
      startPolling()
      return
    }
    stopPolling()
    if (nextTask.status === 'failed') {
      throw new Error(nextTask.error || nextTask.result?.message || '视频检索任务失败')
    }
    selectedResource.value = resolveVideoResource(nextTask.result)
    if (!selectedResource.value) throw new Error('任务已完成，但没有返回有效的视频检索结果')
    topic.value = String(selectedResource.value?.metadata?.query || nextTask.result?.topic || topic.value).replace(/\s+教程\s+视频$/u, '').trim()
    markTaskComplete(nextTask)
  } catch (error) {
    stopPolling()
    taskError.value = error?.response?.data?.msg || error?.message || '读取视频检索任务失败'
    markTaskFailed(taskError.value)
  }
}

function resolveVideoResource(result) {
  const payload = result && typeof result === 'object' ? result : {}
  if (payload.selectedResource && typeof payload.selectedResource === 'object') return payload.selectedResource
  const resources = Array.isArray(payload.workflow?.resources) ? payload.workflow.resources : []
  return resources.find(item => String(item?.type || '').toLowerCase() === 'video') || null
}

function videoCoverUrl(value) {
  let cover = String(value || '').trim()
  if (cover.startsWith('//')) cover = `https:${cover}`
  if (!/^https?:\/\//i.test(cover)) return cover
  return `/api-cover?url=${encodeURIComponent(cover)}`
}

function hideBrokenCover(event) {
  event.currentTarget.style.display = 'none'
}

function startPolling() {
  if (pollTimer || !taskId.value) return
  pollTimer = window.setInterval(loadTask, 1800)
}

function stopPolling() {
  if (!pollTimer) return
  window.clearInterval(pollTimer)
  pollTimer = null
}

function cacheKey() {
  return String(route.query.cacheKey || '').trim()
}

function markTaskStarted(nextTask) {
  if (!cacheKey()) return
  markNodeCacheStarted(cacheKey(), {
    resourceType: 'video',
    title: topic.value || '学习视频',
    taskId: nextTask.taskId,
    agentTaskId: nextTask.taskId,
    route: route.fullPath,
    progress: taskProgress.value,
  })
}

function markTaskComplete(nextTask) {
  if (!cacheKey()) return
  markNodeCacheComplete(cacheKey(), {
    resourceType: 'video',
    title: selectedResource.value?.title || topic.value || '学习视频',
    taskId: nextTask.taskId,
    agentTaskId: nextTask.taskId,
    route: route.fullPath,
    progress: 100,
    resultCount: videos.value.length,
  })
}

function markTaskFailed(error) {
  if (!cacheKey()) return
  markNodeCacheError(cacheKey(), {
    resourceType: 'video',
    title: topic.value || '学习视频',
    taskId: taskId.value,
    agentTaskId: taskId.value,
    route: route.fullPath,
    error,
  })
}

function goBackToResources() {
  router.push('/personalized-resources')
}
</script>

<style scoped>
.video-search-page {
  width: 100%;
  min-height: calc(100vh - 64px);
  background: #f4f8f6;
  color: #17352d;
}

.video-search-page.standalone {
  min-height: 100vh;
  padding: 72px 16px 40px;
  box-sizing: border-box;
}

.video-search-shell {
  width: min(1240px, calc(100% - 40px));
  margin: 0 auto;
  padding: 24px 0 40px;
}

.standalone .video-search-shell { padding-top: 4px; }

.video-search-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 28px;
  padding: 4px 2px 24px;
  border-bottom: 1px solid #dce8e2;
}

.video-search-kicker,
.task-state {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  color: #0b8f65;
  font-size: 13px;
  font-weight: 750;
}

.video-search-header h1 {
  margin: 9px 0 7px;
  font-size: 28px;
  line-height: 1.28;
  letter-spacing: 0;
}

.video-search-header p {
  margin: 0;
  color: #667b74;
  font-size: 14px;
  line-height: 1.7;
}

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

.video-search-form {
  display: grid;
  gap: 8px;
  padding: 22px 2px 18px;
}

.video-search-form label {
  color: #48645a;
  font-size: 13px;
  font-weight: 700;
}

.video-search-form > div {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 10px;
}

.video-search-form input {
  min-width: 0;
  height: 46px;
  padding: 0 14px;
  border: 1px solid #cadbd4;
  border-radius: 6px;
  background: #fff;
  color: #17352d;
  font: inherit;
  outline: none;
}

.video-search-form input:focus {
  border-color: #0e9f6e;
  box-shadow: 0 0 0 3px rgba(14, 159, 110, 0.12);
}

.video-search-form button,
.video-error button {
  min-height: 42px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 7px;
  padding: 0 18px;
  border: 0;
  border-radius: 6px;
  background: #0e9f6e;
  color: #fff;
  font: inherit;
  font-weight: 700;
  cursor: pointer;
}

.video-search-form button:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}

.video-feedback { margin: 0 2px 12px; }

.video-loading,
.video-error,
.video-empty {
  min-height: 390px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  text-align: center;
  color: #647a72;
}

.video-loading strong,
.video-error strong,
.video-empty strong {
  margin-top: 16px;
  color: #193a31;
  font-size: 19px;
}

.video-loading p,
.video-error p {
  max-width: 560px;
  margin: 8px 0 0;
  font-size: 14px;
  line-height: 1.65;
}

.video-error svg { color: #c44b42; }
.video-error button { margin-top: 20px; }

.loading-rings {
  position: relative;
  width: 78px;
  height: 78px;
}

.loading-rings i {
  position: absolute;
  inset: 0;
  border: 2px solid rgba(14, 159, 110, 0.28);
  border-radius: 50%;
  animation: video-pulse 1.8s ease-out infinite;
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

.video-loading small {
  margin-top: 8px;
  color: #0b8f65;
  font-weight: 700;
}

.video-results { padding: 10px 2px 0; }

.video-results > header {
  display: flex;
  align-items: end;
  justify-content: space-between;
  gap: 24px;
  margin-bottom: 16px;
}

.video-results > header span {
  color: #6a8078;
  font-size: 12px;
}

.video-results h2 {
  margin: 5px 0 0;
  font-size: 20px;
  line-height: 1.4;
  letter-spacing: 0;
}

.quality-summary {
  display: flex;
  flex-wrap: wrap;
  justify-content: flex-end;
  gap: 8px 14px;
}

.video-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 16px;
}

.video-card {
  min-width: 0;
  overflow: hidden;
  border: 1px solid #d6e3dd;
  border-radius: 8px;
  background: #fff;
  box-shadow: 0 8px 22px rgba(36, 73, 62, 0.06);
}

.video-cover {
  position: relative;
  display: block;
  aspect-ratio: 16 / 9;
  overflow: hidden;
  background: #dfeae5;
  color: #0e9f6e;
}

.video-cover img {
  position: relative;
  z-index: 2;
  width: 100%;
  height: 100%;
  display: block;
  object-fit: cover;
  transition: transform 220ms ease;
}

.video-cover:hover img { transform: scale(1.025); }

.cover-fallback {
  position: absolute;
  inset: 0;
  display: grid;
  place-items: center;
}

.video-cover em {
  position: absolute;
  z-index: 3;
  right: 8px;
  bottom: 8px;
  padding: 3px 6px;
  border-radius: 4px;
  background: rgba(17, 35, 30, 0.82);
  color: #fff;
  font-size: 11px;
  font-style: normal;
}

.video-card-body { padding: 14px; }

.video-card-body > a {
  display: -webkit-box;
  min-height: 44px;
  overflow: hidden;
  color: #1c3c33;
  font-size: 15px;
  font-weight: 750;
  line-height: 1.45;
  text-decoration: none;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
}

.video-card-body > a:hover { color: #07865e; }

.video-card-body p {
  min-height: 38px;
  margin: 8px 0 0;
  color: #687d76;
  font-size: 12px;
  line-height: 1.55;
}

.video-card-body > div {
  min-height: 20px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  margin-top: 10px;
  color: #7a8d86;
  font-size: 11px;
}

.video-card-body span {
  min-width: 0;
  display: inline-flex;
  align-items: center;
  gap: 5px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.resource-back-button {
  position: fixed;
  top: 18px;
  left: 24px;
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

.resource-back-button:hover { background: #f1fbf7; }
.spin { animation: video-spin 900ms linear infinite; }

@keyframes video-spin { to { transform: rotate(360deg); } }
@keyframes video-pulse {
  0% { opacity: 0.8; transform: scale(0.35); }
  100% { opacity: 0; transform: scale(1); }
}

@media (max-width: 980px) {
  .video-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
}

@media (max-width: 640px) {
  .video-search-page.standalone { padding: 68px 10px 24px; }
  .video-search-shell { width: calc(100% - 20px); padding-bottom: 24px; }
  .video-search-header { display: block; }
  .video-search-header h1 { font-size: 22px; }
  .task-state { margin-top: 16px; }
  .video-search-form > div { grid-template-columns: 1fr; }
  .video-search-form button { width: 100%; }
  .video-results > header { display: block; }
  .quality-summary { justify-content: flex-start; margin-top: 10px; }
  .video-grid { grid-template-columns: 1fr; }
  .resource-back-button { left: 14px; }
}

@media (prefers-reduced-motion: reduce) {
  .spin,
  .loading-rings i { animation: none; }
  .video-cover img { transition: none; }
}
</style>
