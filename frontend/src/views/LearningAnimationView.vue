<template>
  <main class="animation-page">
    <header class="animation-toolbar">
      <button type="button" class="icon-button" title="返回个性化资源" aria-label="返回个性化资源" @click="router.push('/personalized-resources')">
        <ArrowLeft :size="19" />
      </button>
      <div class="animation-title">
        <span>H5 动画讲解</span>
        <h1>{{ animation?.title || '动画微课工作台' }}</h1>
      </div>
      <div class="toolbar-actions">
        <label class="history-select">
          <History :size="17" />
          <select :value="taskId" aria-label="历史动画任务" @change="openHistory($event.target.value)">
            <option value="">历史任务</option>
            <option v-for="item in history" :key="item.taskId" :value="item.taskId">{{ item.title }}</option>
          </select>
        </label>
        <button class="icon-button" type="button" :title="fullscreenLabel" :aria-label="fullscreenLabel" :disabled="!animation" @click="toggleFullscreen">
          <Minimize2 v-if="fullscreenActive" :size="19" />
          <Maximize2 v-else :size="19" />
        </button>
      </div>
    </header>

    <section class="generation-band" aria-label="动画生成参数">
      <label>
        <span>主题</span>
        <input v-model.trim="topic" placeholder="例如：风寒感冒辨证论治流程" />
      </label>
      <label>
        <span>侧重点</span>
        <input v-model.trim="requirements" placeholder="例如：用信号流解释触发、挂起与清除" />
      </label>
      <button type="button" :disabled="generating || !topic" @click="startGeneration">
        <LoaderCircle v-if="generating" :size="18" class="spin" />
        <WandSparkles v-else :size="18" />
        {{ generating ? '生成中' : '生成动画' }}
      </button>
    </section>

    <section v-if="error" class="error-band" role="alert">
      <AlertTriangle :size="18" />
      <span>{{ error }}</span>
      <button type="button" @click="startGeneration"><RotateCcw :size="16" />重试</button>
    </section>

    <template v-if="animation">
      <section class="animation-meta" aria-label="动画内容信息">
        <div><span>场景</span><strong>{{ animation.scenes?.length || 0 }}</strong></div>
        <div><span>时长</span><strong>{{ durationLabel(animation.totalDurationSeconds) }}</strong></div>
      </section>

      <section ref="player" :class="['animation-player', { 'is-fallback-fullscreen': fallbackFullscreen }]" aria-label="H5 动画播放器">
        <div class="player-progress"><i :style="{ width: `${sceneProgress}%` }"></i></div>
        <div class="scene-shell" @click="nextScene">
          <div class="scene-visual" :class="`visual-${currentScene.visualType || 'concept'}`">
            <div class="scene-kicker">
              <span>{{ String(sceneIndex + 1).padStart(2, '0') }} / {{ animation.scenes.length }}</span>
              <em>{{ visualLabel(currentScene.visualType) }}</em>
            </div>

            <div v-if="currentScene.visualType === 'code' && currentScene.codeSnippet" class="code-visual">
              <div class="code-heading"><Code2 :size="18" />{{ currentScene.headline }}</div>
              <pre><code>{{ currentScene.codeSnippet }}</code></pre>
            </div>

            <div v-else-if="currentScene.visualType === 'comparison'" class="comparison-visual">
              <article><span>对照 A</span><strong>{{ currentScene.primaryLabel }}</strong><p>{{ displaySceneItem(currentScene.keyPoints?.[0]) || currentScene.narration }}</p></article>
              <div>VS</div>
              <article><span>对照 B</span><strong>{{ currentScene.secondaryLabel || currentScene.headline }}</strong><p>{{ displaySceneItem(currentScene.keyPoints?.[1]) || currentScene.narration }}</p></article>
            </div>

            <div v-else-if="currentScene.visualType === 'experiment'" class="experiment-visual">
              <div class="board-panel">
                <span>岐黄</span><strong>{{ currentScene.primaryLabel }}</strong>
                <i v-for="pin in 6" :key="pin" :style="{ top: `${14 + pin * 11}%` }"></i>
              </div>
              <div class="wire-line"><b></b></div>
              <div class="output-panel"><span>OBSERVE</span><strong>{{ currentScene.secondaryLabel || '运行现象' }}</strong><i></i></div>
            </div>

            <div v-else-if="['flow', 'signal', 'register'].includes(currentScene.visualType)" class="flow-visual">
              <article><span>INPUT</span><strong>{{ currentScene.signal?.input || currentScene.primaryLabel || '输入' }}</strong></article>
              <div class="flow-link"><i></i></div>
              <article><span>PROCESS</span><strong>{{ currentScene.signal?.process || currentScene.headline }}</strong></article>
              <div class="flow-link"><i></i></div>
              <article><span>OUTPUT</span><strong>{{ currentScene.signal?.output || currentScene.secondaryLabel || '输出' }}</strong></article>
            </div>

            <div v-else class="concept-visual">
              <div class="concept-core"><span>CORE</span><strong>{{ currentScene.primaryLabel || currentScene.headline }}</strong></div>
              <div class="concept-steps">
                <article v-for="(step, index) in visibleSteps" :key="`${index}-${step}`"><b>{{ String(index + 1).padStart(2, '0') }}</b><span>{{ step }}</span></article>
              </div>
            </div>
          </div>

          <div class="scene-copy">
            <span>{{ currentScene.headline }}</span>
            <h2>{{ currentScene.title }}</h2>
            <p>{{ currentScene.narration }}</p>
            <ul><li v-for="(item, index) in currentScene.keyPoints || []" :key="index">{{ displaySceneItem(item) }}</li></ul>
          </div>
        </div>

        <footer class="player-controls" @click.stop>
          <button type="button" title="上一场景" aria-label="上一场景" :disabled="sceneIndex === 0" @click="previousScene"><SkipBack :size="20" /></button>
          <button type="button" class="play-button" :title="playing ? '暂停' : '播放'" :aria-label="playing ? '暂停' : '播放'" @click="togglePlay">
            <Pause v-if="playing" :size="22" fill="currentColor" />
            <Play v-else :size="22" fill="currentColor" />
          </button>
          <button type="button" title="下一场景" aria-label="下一场景" :disabled="sceneIndex >= animation.scenes.length - 1" @click="nextScene"><SkipForward :size="20" /></button>
          <button type="button" :title="voiceEnabled ? '关闭语音' : '开启语音'" :aria-label="voiceEnabled ? '关闭语音' : '开启语音'" @click="toggleVoice">
            <Volume2 v-if="voiceEnabled" :size="20" />
            <VolumeX v-else :size="20" />
          </button>
          <div class="scene-timeline" aria-label="场景导航">
            <button
              v-for="(scene, index) in animation.scenes"
              :key="scene.id"
              type="button"
              :class="{ active: sceneIndex === index, visited: sceneIndex > index }"
              :title="scene.title"
              :aria-label="`场景 ${index + 1}：${scene.title}`"
              @click="selectScene(index)"
            >{{ index + 1 }}</button>
          </div>
          <button type="button" :title="fullscreenLabel" :aria-label="fullscreenLabel" @click="toggleFullscreen">
            <Minimize2 v-if="fullscreenActive" :size="20" />
            <Maximize2 v-else :size="20" />
          </button>
        </footer>
      </section>

      <section class="animation-details" aria-label="动画学习检查">
        <article class="detail-panel">
          <header><BadgeCheck :size="18" /><h2>学习检查</h2><span>{{ animation.knowledgeChecks?.length || 0 }}</span></header>
          <details v-for="item in animation.knowledgeChecks || []" :key="item.id">
            <summary>{{ item.question }}</summary>
            <strong>{{ item.answer }}</strong>
            <p>{{ item.explanation }}</p>
          </details>
        </article>
      </section>
    </template>

    <section v-else-if="!generating" class="empty-animation">
      <Film :size="38" />
      <strong>暂无动画微课</strong>
    </section>
  </main>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  AlertTriangle,
  ArrowLeft,
  BadgeCheck,
  Code2,
  Film,
  History,
  LoaderCircle,
  Maximize2,
  Minimize2,
  Pause,
  Play,
  RotateCcw,
  SkipBack,
  SkipForward,
  Volume2,
  VolumeX,
  WandSparkles,
} from 'lucide-vue-next'
import { getXiaoZhiHistory, getXiaoZhiTask, startPersonalizedResourceAgentTask } from '../services/api.js'
import { dispatchXiaoZhiWorkflowProgress } from '../utils/xiaozhiWorkflowProgress.js'

const route = useRoute()
const router = useRouter()
const topic = ref(String(route.query.topic || '风寒感冒辨证论治流程'))
const requirements = ref(String(route.query.requirements || '用信号流解释触发、挂起、服务与清除过程'))
const history = ref([])
const taskId = ref(String(route.query.xzTask || ''))
const taskStatus = ref('')
const taskResult = ref({})
const generating = ref(false)
const error = ref('')
const sceneIndex = ref(0)
const playing = ref(false)
const voiceEnabled = ref(false)
const player = ref(null)
const nativeFullscreen = ref(false)
const fallbackFullscreen = ref(false)
let pollTimer = null
let sceneTimer = null

const animation = computed(() => taskResult.value?.animation || null)
const currentScene = computed(() => animation.value?.scenes?.[sceneIndex.value] || {})
const visibleSteps = computed(() => {
  const items = currentScene.value?.steps?.length
    ? currentScene.value.steps.slice(0, 4)
    : currentScene.value?.keyPoints?.slice(0, 4) || []
  return items.map(displaySceneItem).filter(Boolean)
})
const sceneProgress = computed(() => animation.value?.scenes?.length ? ((sceneIndex.value + 1) / animation.value.scenes.length) * 100 : 0)
const fullscreenActive = computed(() => nativeFullscreen.value || fallbackFullscreen.value)
const fullscreenLabel = computed(() => fullscreenActive.value ? '退出全屏' : '全屏播放')
function displaySceneItem(value) {
  if (value == null) return ''
  if (typeof value === 'object') {
    const label = value.title || value.label || value.name || value.heading || ''
    const content = value.content || value.description || value.text || value.detail || value.narration || ''
    if (label && content && label !== content) return `${label}：${content}`
    if (label || content) return String(label || content).trim()
    return [...new Set(Object.values(value).filter(item => ['string', 'number', 'boolean'].includes(typeof item)).map(String))].join('：')
  }

  const text = String(value).trim()
  if (!text.startsWith('{') || !text.endsWith('}')) return text

  const fields = {}
  const pairPattern = /['"](title|label|name|heading|content|description|text|detail|narration)['"]\s*:\s*(['"])(.*?)\2(?=\s*[,}])/g
  let match
  while ((match = pairPattern.exec(text)) !== null) fields[match[1]] = match[3]
  const label = fields.title || fields.label || fields.name || fields.heading || ''
  const content = fields.content || fields.description || fields.text || fields.detail || fields.narration || ''
  if (label && content && label !== content) return `${label}：${content}`
  if (label || content) return label || content

  const scalarValues = [...text.matchAll(/:\s*(['"])(.*?)\1(?=\s*[,}])/g)].map(item => item[2]).filter(Boolean)
  return scalarValues.length ? [...new Set(scalarValues)].join('：') : text
}

function durationLabel(value) {
  const seconds = Math.max(0, Number(value || 0))
  const minutes = Math.floor(seconds / 60)
  return `${minutes}:${String(Math.floor(seconds % 60)).padStart(2, '0')}`
}

function visualLabel(value) {
  return ({ concept: '概念', flow: '流程', signal: '信号', register: '寄存器', code: '代码', comparison: '对照', experiment: '实验' })[value] || '概念'
}

async function loadHistory() {
  try {
    const response = await getXiaoZhiHistory()
    history.value = (response?.data?.tasks || []).filter(item => item.taskType === 'animation')
  } catch {
    history.value = []
  }
}

async function startGeneration() {
  if (!topic.value || generating.value) return
  stopPolling()
  stopPlayback()
  error.value = ''
  taskResult.value = {}
  taskStatus.value = 'queued'
  sceneIndex.value = 0
  generating.value = true
  try {
    const response = await startPersonalizedResourceAgentTask({
      resourceType: 'animation',
      topic: topic.value,
      prompt: requirements.value || topic.value,
      params: { topic: topic.value, requirements: requirements.value },
    })
    const task = response?.data?.task
    if (!task?.taskId) throw new Error('未获得动画任务 ID')
    taskId.value = task.taskId
    taskResult.value = task.result || {}
    taskStatus.value = task.status || 'queued'
    dispatchXiaoZhiWorkflowProgress({ task })
    await router.replace({ query: { ...route.query, topic: topic.value, requirements: requirements.value, autostart: undefined, xzTask: taskId.value } })
    startPolling()
    await loadTask()
  } catch (err) {
    generating.value = false
    taskStatus.value = 'failed'
    error.value = err?.response?.data?.msg || err?.message || '动画任务创建失败'
  }
}

async function loadTask() {
  if (!taskId.value) return
  try {
    const response = await getXiaoZhiTask(taskId.value)
    const task = response?.data?.task
    if (!task) return
    taskStatus.value = task.status || ''
    taskResult.value = task.result || {}
    if (Array.isArray(response?.data?.orchestrationRuns)) task.orchestrationRuns = response.data.orchestrationRuns
    dispatchXiaoZhiWorkflowProgress({ task })
    generating.value = ['queued', 'running'].includes(task.status)
    if (task.status === 'complete') {
      stopPolling()
      generating.value = false
      sceneIndex.value = Math.min(sceneIndex.value, Math.max(0, (task.result?.animation?.scenes?.length || 1) - 1))
      await loadHistory()
    } else if (task.status === 'failed') {
      stopPolling()
      generating.value = false
      error.value = task.error || task.result?.message || '动画生成失败'
    }
  } catch (err) {
    stopPolling()
    generating.value = false
    taskStatus.value = 'failed'
    error.value = err?.response?.data?.msg || err?.message || '动画任务状态读取失败'
  }
}

async function openHistory(nextTaskId) {
  if (!nextTaskId) return
  stopPlayback()
  taskId.value = String(nextTaskId)
  taskResult.value = {}
  sceneIndex.value = 0
  await router.replace({ query: { xzTask: taskId.value } })
  await loadTask()
  if (['queued', 'running'].includes(taskStatus.value)) startPolling()
}

function startPolling() {
  stopPolling()
  pollTimer = window.setInterval(loadTask, 1800)
}

function stopPolling() {
  if (pollTimer) window.clearInterval(pollTimer)
  pollTimer = null
}

function clearSceneTimer() {
  if (sceneTimer) window.clearTimeout(sceneTimer)
  sceneTimer = null
}

function scheduleScene() {
  clearSceneTimer()
  if (!playing.value || !animation.value) return
  const duration = Math.max(3, Number(currentScene.value?.durationSeconds || 12)) * 1000
  sceneTimer = window.setTimeout(() => {
    if (sceneIndex.value >= animation.value.scenes.length - 1) {
      playing.value = false
      return
    }
    sceneIndex.value += 1
  }, duration)
}

function stopPlayback() {
  playing.value = false
  clearSceneTimer()
  window.speechSynthesis?.cancel()
}

function togglePlay() {
  if (!animation.value) return
  if (!playing.value && sceneIndex.value >= animation.value.scenes.length - 1) sceneIndex.value = 0
  playing.value = !playing.value
}

function selectScene(index) {
  sceneIndex.value = Math.max(0, Math.min(animation.value.scenes.length - 1, index))
}

function previousScene() {
  if (sceneIndex.value > 0) sceneIndex.value -= 1
}

function nextScene() {
  if (!animation.value) return
  if (sceneIndex.value < animation.value.scenes.length - 1) sceneIndex.value += 1
  else playing.value = false
}

function speakCurrentScene() {
  if (!voiceEnabled.value || !currentScene.value?.narration || !window.speechSynthesis) return
  window.speechSynthesis.cancel()
  const utterance = new SpeechSynthesisUtterance(currentScene.value.narration)
  utterance.lang = 'zh-CN'
  utterance.rate = 0.95
  window.speechSynthesis.speak(utterance)
}

function toggleVoice() {
  voiceEnabled.value = !voiceEnabled.value
  if (voiceEnabled.value) speakCurrentScene()
  else window.speechSynthesis?.cancel()
}

function syncFullscreenState() {
  nativeFullscreen.value = document.fullscreenElement === player.value
}

async function toggleFullscreen() {
  if (!player.value) return
  if (fallbackFullscreen.value) {
    fallbackFullscreen.value = false
    return
  }
  if (document.fullscreenElement) {
    await document.exitFullscreen()
    return
  }
  try {
    await player.value.requestFullscreen()
    syncFullscreenState()
    if (!nativeFullscreen.value) fallbackFullscreen.value = true
  } catch {
    fallbackFullscreen.value = true
  }
}

function handleKeydown(event) {
  if (['INPUT', 'TEXTAREA', 'SELECT'].includes(event.target?.tagName)) return
  if (event.key === 'Escape' && fallbackFullscreen.value) {
    fallbackFullscreen.value = false
    return
  }
  if (event.key === 'ArrowLeft') previousScene()
  else if (event.key === 'ArrowRight') nextScene()
  else if (event.key === ' ') {
    event.preventDefault()
    togglePlay()
  }
}

watch([playing, sceneIndex], scheduleScene)
watch(currentScene, speakCurrentScene)

onMounted(async () => {
  window.addEventListener('keydown', handleKeydown)
  document.addEventListener('fullscreenchange', syncFullscreenState)
  await loadHistory()
  if (taskId.value) {
    generating.value = true
    startPolling()
    await loadTask()
  } else if (String(route.query.autostart || '') === '1') {
    await startGeneration()
  } else if (history.value.length) {
    await openHistory(history.value[0].taskId)
  }
})

onBeforeUnmount(() => {
  stopPolling()
  stopPlayback()
  fallbackFullscreen.value = false
  window.removeEventListener('keydown', handleKeydown)
  document.removeEventListener('fullscreenchange', syncFullscreenState)
})
</script>

<style scoped>
.animation-page{min-height:100vh;background:#f3f6f4;color:#20352f;padding:24px 30px 64px;letter-spacing:0}.animation-toolbar{max-width:1320px;margin:0 auto 16px;display:grid;grid-template-columns:42px minmax(0,1fr) auto;align-items:center;gap:14px}.icon-button,.player-controls>button{width:40px;height:40px;display:grid;place-items:center;border:1px solid #d4dfda;border-radius:6px;background:#fff;color:#315b4d;cursor:pointer}.icon-button:disabled,.player-controls>button:disabled{opacity:.4;cursor:not-allowed}.animation-title span{color:#1c8159;font-size:12px;font-weight:800}.animation-title h1{margin:4px 0 0;font-size:25px;line-height:1.25;letter-spacing:0}.toolbar-actions{display:flex;gap:8px}.history-select{height:40px;display:flex;align-items:center;gap:7px;border:1px solid #d4dfda;border-radius:6px;background:#fff;padding:0 9px;color:#315b4d}.history-select select{max-width:220px;border:0;outline:0;background:transparent;color:#29463c}.generation-band{max-width:1320px;margin:0 auto 14px;display:grid;grid-template-columns:1fr 1.35fr auto;align-items:end;gap:12px;padding:14px 0;border-top:1px solid #dae3df;border-bottom:1px solid #dae3df}.generation-band label{display:grid;gap:6px}.generation-band label span{color:#526a61;font-size:12px;font-weight:800}.generation-band input{height:40px;border:1px solid #ccd9d3;border-radius:4px;background:#fff;padding:0 12px;outline:0}.generation-band input:focus{border-color:#23855f;box-shadow:0 0 0 3px rgba(35,133,95,.1)}.generation-band>button{height:40px;display:flex;align-items:center;gap:7px;border:0;border-radius:6px;background:#176f4b;color:#fff;padding:0 17px;font-weight:800;cursor:pointer}.generation-band>button:disabled{opacity:.55;cursor:not-allowed}.task-progress,.error-band,.animation-meta,.animation-player,.animation-details,.empty-animation{max-width:1320px;margin-left:auto;margin-right:auto}.task-progress{display:grid;grid-template-columns:minmax(0,1fr) 240px auto;align-items:center;gap:16px;padding:12px 14px;background:#e8f4ed;border-left:3px solid #23855f}.task-progress>div:first-child{display:flex;align-items:center;gap:9px}.task-progress span{display:grid;gap:2px}.task-progress small{color:#71837c;font-size:10px}.task-progress>button{display:flex;align-items:center;gap:6px;border:1px solid #d7b1a5;background:#fff;padding:7px 10px;color:#9c442f;cursor:pointer}.progress-track{height:5px;overflow:hidden;background:#ccdbd4}.progress-track i{display:block;height:100%;background:#23855f;transition:width .35s}.error-band{margin-top:12px;display:flex;align-items:center;gap:8px;padding:11px 13px;background:#fff0ec;color:#a44832}.animation-meta{margin-top:16px;display:grid;grid-template-columns:repeat(5,1fr);background:#263b34;color:#fff}.animation-meta>div{padding:13px 16px;border-right:1px solid rgba(255,255,255,.14)}.animation-meta span{display:block;color:#b8c9c2;font-size:10px}.animation-meta strong{display:block;margin-top:4px;font-size:16px}.animation-player{position:relative;overflow:hidden;background:#172720;color:#fff;aspect-ratio:16/9;min-height:520px;display:grid;grid-template-rows:5px minmax(0,1fr) 64px}.player-progress{background:#415149}.player-progress i{display:block;height:100%;background:#62c890;transition:width .35s}.scene-shell{min-height:0;display:grid;grid-template-columns:minmax(0,1.4fr) minmax(320px,.72fr);cursor:pointer}.scene-visual{position:relative;min-width:0;padding:38px 42px;display:grid;align-content:center;background:#eff4f1;color:#1d342b;overflow:hidden}.scene-kicker{position:absolute;top:18px;left:22px;right:22px;display:flex;justify-content:space-between;align-items:center}.scene-kicker span,.scene-kicker em{font-size:10px;font-weight:900;font-style:normal}.scene-kicker em{padding:5px 7px;border:1px solid #c8d9d1;border-radius:4px;color:#236e50;background:#fff}.scene-copy{min-width:0;padding:46px 38px 32px;display:grid;align-content:center;background:#22362e}.scene-copy>span{color:#76d7a1;font-size:11px;font-weight:900}.scene-copy h2{margin:9px 0 14px;font-size:25px;line-height:1.3;letter-spacing:0}.scene-copy p{margin:0;color:#d0ddd7;line-height:1.75;font-size:14px}.scene-copy ul{margin:18px 0 0;padding-left:18px;color:#a9c0b6}.scene-copy li{margin:7px 0;line-height:1.5}.concept-visual{display:grid;grid-template-columns:minmax(180px,.65fr) minmax(0,1fr);align-items:center;gap:34px}.concept-core{min-height:180px;display:grid;place-content:center;gap:8px;border:2px solid #27855e;border-radius:6px;background:#fff;padding:20px;text-align:center}.concept-core span,.comparison-visual article span,.flow-visual article span,.board-panel span,.output-panel span{color:#9a732d;font-size:10px;font-weight:900}.concept-core strong{font-size:20px;line-height:1.4}.concept-steps{display:grid;gap:10px}.concept-steps article{display:grid;grid-template-columns:34px minmax(0,1fr);align-items:center;gap:10px;padding:12px;border-left:3px solid #2c8b63;background:#fff;animation:scene-in .45s both}.concept-steps article:nth-child(2){animation-delay:.1s}.concept-steps article:nth-child(3){animation-delay:.2s}.concept-steps article:nth-child(4){animation-delay:.3s}.concept-steps b{color:#247756;font-size:11px}.flow-visual{display:grid;grid-template-columns:minmax(0,1fr) 54px minmax(0,1fr) 54px minmax(0,1fr);align-items:center}.flow-visual article{min-height:150px;display:grid;place-content:center;gap:9px;border:1px solid #bfcfc7;border-radius:6px;background:#fff;padding:18px;text-align:center}.flow-visual article strong{font-size:16px;line-height:1.45}.flow-link{height:4px;background:#b9cac2;position:relative}.flow-link i{position:absolute;width:16px;height:16px;top:-6px;border:4px solid #2e966a;background:#eff4f1;animation:signal-pulse 1.8s linear infinite}.code-visual{max-height:390px;display:grid;grid-template-rows:auto minmax(0,1fr);border-radius:6px;overflow:hidden;background:#172620;color:#d8efe4}.code-heading{display:flex;align-items:center;gap:8px;padding:12px 16px;background:#2d443a;color:#b7dfca;font-size:12px;font-weight:800}.code-visual pre{min-height:0;margin:0;padding:20px;overflow:auto;font-size:12px;line-height:1.65;white-space:pre-wrap}.comparison-visual{display:grid;grid-template-columns:1fr 48px 1fr;align-items:center;gap:12px}.comparison-visual>div{font-size:13px;font-weight:900;text-align:center;color:#956f2c}.comparison-visual article{min-height:230px;display:grid;align-content:center;gap:12px;border:1px solid #c8d5cf;border-radius:6px;background:#fff;padding:24px}.comparison-visual article strong{font-size:19px}.comparison-visual article p{margin:0;color:#5a6f66;line-height:1.6}.experiment-visual{display:grid;grid-template-columns:minmax(190px,.7fr) minmax(80px,.4fr) minmax(170px,.6fr);align-items:center}.board-panel,.output-panel{position:relative;min-height:220px;display:grid;place-content:center;gap:8px;border-radius:6px;padding:24px;text-align:center}.board-panel{border:4px solid #2d7a5b;background:#d9efe3}.board-panel strong,.output-panel strong{font-size:17px;line-height:1.5}.board-panel>i{position:absolute;right:-10px;width:18px;height:6px;background:#b89045}.wire-line{height:5px;background:#b89045;position:relative}.wire-line b{position:absolute;width:18px;height:18px;top:-7px;border-radius:50%;background:#e7b44f;animation:signal-pulse 1.5s linear infinite}.output-panel{border:2px solid #48675a;background:#fff}.output-panel>i{width:32px;height:32px;margin:12px auto 0;border-radius:50%;background:#db6244;box-shadow:0 0 18px rgba(219,98,68,.6);animation:led-blink 1.3s ease-in-out infinite}.player-controls{display:flex;align-items:center;gap:8px;padding:11px 16px;background:#101d18}.player-controls>button{flex:0 0 40px;border-color:#41524a;background:#24362e;color:#e4eee9}.player-controls .play-button{background:#5bc286;color:#102018;border-color:#5bc286}.scene-timeline{min-width:0;flex:1;display:grid;grid-template-columns:repeat(8,minmax(28px,1fr));gap:5px}.scene-timeline button{height:30px;border:1px solid #41524a;border-radius:4px;background:#24362e;color:#a9bbb3;cursor:pointer}.scene-timeline button.active{border-color:#69d092;background:#69d092;color:#13221b;font-weight:900}.scene-timeline button.visited{border-color:#4c8067;color:#cde4d8}.animation-player:fullscreen{width:100vw;height:100vh;max-width:none;aspect-ratio:auto;min-height:0}.animation-details{display:grid;grid-template-columns:1.1fr 1fr .78fr;gap:14px;margin-top:14px}.detail-panel{min-width:0;border:1px solid #d7e1dc;border-radius:6px;background:#fff;padding:18px}.detail-panel header{display:flex;align-items:center;gap:7px;margin-bottom:12px;color:#286b50}.detail-panel h2{margin:0;font-size:16px;letter-spacing:0}.detail-panel header span{margin-left:auto;padding:4px 7px;border-radius:4px;background:#edf3f0;color:#61746c;font-size:10px;font-weight:800}.detail-panel header span.passed{background:#dff3e7;color:#1e7550}.detail-panel details{border-top:1px solid #e5ece8;padding:11px 0}.detail-panel summary{cursor:pointer;color:#314c42;font-size:13px;font-weight:700;line-height:1.5}.detail-panel details strong,.detail-panel details p{display:block;margin-top:8px;color:#536960;font-size:12px;line-height:1.55}.detail-panel ol{margin:0;padding:0;list-style:none}.detail-panel li{display:grid;grid-template-columns:40px minmax(0,1fr);gap:3px 7px;padding:9px 0;border-top:1px solid #e5ece8}.detail-panel li b{grid-row:1/3;color:#1d7b55}.detail-panel li small{color:#7b8c85}.verification-copy{display:flex;align-items:flex-start;gap:6px;color:#866936;font-size:11px;line-height:1.5}.quality-panel>div{display:flex;justify-content:space-between;padding:9px 0;border-top:1px solid #e5ece8}.quality-panel>div span{color:#667a72;font-size:12px}.empty-animation{min-height:360px;display:grid;place-content:center;justify-items:center;gap:8px;color:#789087}.empty-animation strong{color:#315047}.spin{animation:spin .8s linear infinite}@keyframes spin{to{transform:rotate(360deg)}}@keyframes scene-in{from{opacity:0;transform:translateX(18px)}to{opacity:1;transform:translateX(0)}}@keyframes signal-pulse{from{left:0}to{left:calc(100% - 18px)}}@keyframes led-blink{0%,100%{opacity:.35}50%{opacity:1}}@media(max-width:980px){.scene-shell{grid-template-columns:1fr}.animation-player{aspect-ratio:auto;min-height:720px}.scene-copy{padding:28px}.animation-details{grid-template-columns:1fr 1fr}.quality-panel{grid-column:1/3}.generation-band{grid-template-columns:1fr}.task-progress{grid-template-columns:1fr}.animation-meta{grid-template-columns:repeat(3,1fr)}}@media(max-width:680px){.animation-page{padding:18px 14px 86px}.animation-toolbar{grid-template-columns:40px minmax(0,1fr)}.toolbar-actions{grid-column:1/3;justify-content:flex-end}.history-select{flex:1}.history-select select{width:100%;max-width:none}.animation-meta{grid-template-columns:1fr 1fr}.animation-player{min-height:660px}.scene-visual{padding:46px 18px 24px}.scene-copy{padding:24px 20px}.scene-copy h2{font-size:21px}.concept-visual,.comparison-visual,.experiment-visual{grid-template-columns:1fr}.concept-core{min-height:110px}.comparison-visual>div{padding:4px}.board-panel,.output-panel{min-height:120px}.wire-line{width:5px;height:45px;margin:auto}.wire-line b{left:-7px;animation:signal-pulse-vertical 1.5s linear infinite}.flow-visual{grid-template-columns:1fr;gap:8px}.flow-link{width:4px;height:34px;margin:auto}.flow-link i{left:-6px;animation:signal-pulse-vertical 1.8s linear infinite}.flow-visual article{min-height:90px}.scene-timeline{display:none}.animation-details{grid-template-columns:1fr}.quality-panel{grid-column:auto}.player-controls{justify-content:center}.player-controls>button:nth-last-child(1){margin-left:auto}}@keyframes signal-pulse-vertical{from{top:0}to{top:calc(100% - 18px)}}
.animation-meta{grid-template-columns:repeat(2,minmax(0,1fr))}.animation-details{grid-template-columns:minmax(0,1fr)}.error-band span{min-width:0;flex:1}.error-band button{display:flex;align-items:center;gap:6px;border:1px solid #d7b1a5;background:#fff;padding:7px 10px;color:#9c442f;cursor:pointer}
.animation-player.is-fallback-fullscreen{position:fixed;inset:0;z-index:2200;width:100vw;height:100vh;max-width:none;min-height:0;margin:0;aspect-ratio:auto}
</style>
