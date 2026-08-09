<template>
  <main class="document-page">
    <header class="document-toolbar">
      <div class="document-title-block">
        <span><FileText :size="17" />课程讲义生成</span>
        <h1>{{ activeDocument?.title || '个性化课程讲义' }}</h1>
        <p>当前画像与课程知识库共同生成</p>
      </div>
      <div class="document-actions">
        <label v-if="history.length">
          <History :size="16" />
          <select :value="activeRecord?.id || ''" aria-label="历史讲义" @change="openHistory($event.target.value)">
            <option value="">历史讲义</option>
            <option v-for="item in history" :key="item.id" :value="item.id">{{ item.title }}</option>
          </select>
        </label>
        <button type="button" title="导出 Markdown" :disabled="!activeDocument" @click="downloadMarkdown"><Download :size="17" /></button>
        <button type="button" title="打印讲义" :disabled="!activeDocument" @click="printDocument"><Printer :size="17" /></button>
      </div>
    </header>

    <section class="generation-band">
      <div class="field topic-field">
        <label for="document-topic">主题</label>
        <input id="document-topic" v-model.trim="topic" placeholder="例如：STM32 GPIO 与外部中断" />
      </div>
      <div class="field requirement-field">
        <label for="document-requirements">侧重点</label>
        <input id="document-requirements" v-model.trim="requirements" placeholder="课程对象、薄弱点或实践要求" />
      </div>
      <button class="generate-button" type="button" :disabled="generating || !topic" @click="startGeneration">
        <LoaderCircle v-if="generating" :size="18" class="spin" />
        <WandSparkles v-else :size="18" />
        {{ generating ? '生成中' : '生成讲义' }}
      </button>
    </section>

    <section v-if="generating || taskStatus" class="task-progress" :class="taskStatus">
      <div>
        <LoaderCircle v-if="generating" :size="20" class="spin" />
        <CheckCircle2 v-else-if="taskStatus === 'complete'" :size="20" />
        <AlertTriangle v-else-if="taskStatus === 'failed'" :size="20" />
        <FileText v-else :size="20" />
        <span>
          <strong>{{ taskMessage }}</strong>
          <small v-if="taskId">任务 {{ taskId }}</small>
        </span>
      </div>
      <div class="progress-track"><i :style="{ width: `${taskProgress}%` }"></i></div>
      <button v-if="taskStatus === 'failed'" type="button" @click="startGeneration"><RefreshCw :size="16" />重试</button>
    </section>

    <section v-if="error" class="error-band" role="alert"><AlertTriangle :size="18" />{{ error }}</section>

    <template v-if="activeDocument">
      <section class="document-meta-band">
        <div><span>画像版本</span><strong>#{{ activeRecord?.profileReportId || activeDocument.profile?.profileReportId || '--' }}</strong></div>
        <div><span>生成来源</span><strong>{{ sourceLabel(activeRecord?.source || activeDocument.source) }}</strong></div>
        <div><span>知识引用</span><strong>{{ activeQuality.citationCount || activeDocument.references?.length || 0 }} 条</strong></div>
        <div class="quality-score"><span>内容质量</span><strong>{{ activeQuality.score || 0 }}</strong><em>/ 100</em></div>
      </section>

      <LearningFeedbackActions
        v-if="feedbackTask"
        class="document-feedback"
        :task="feedbackTask"
        :cache-key="String(route.query.cacheKey || '')"
        :route-path="route.fullPath"
      />

      <article class="document-sheet">
        <header class="sheet-cover">
          <span>PERSONALIZED COURSE HANDOUT</span>
          <h2>{{ activeDocument.title }}</h2>
          <p>{{ activeDocument.abstract }}</p>
          <div class="objective-row">
            <b v-for="item in activeDocument.learningObjectives || []" :key="item">{{ item }}</b>
          </div>
        </header>

        <section v-for="section in activeDocument.sections || []" :key="`${section.order}-${section.title}`" class="document-section">
          <div class="section-index">{{ String(section.order).padStart(2, '0') }}</div>
          <div>
            <h3>{{ section.title }}</h3>
            <p v-if="section.summary" class="section-summary">{{ section.summary }}</p>
            <p class="section-content">{{ section.content }}</p>
            <ul v-if="section.keyPoints?.length">
              <li v-for="item in section.keyPoints" :key="item">{{ item }}</li>
            </ul>
            <blockquote v-if="section.example">{{ section.example }}</blockquote>
            <pre v-if="section.codeExample"><code>{{ section.codeExample }}</code></pre>
          </div>
        </section>

        <section class="learning-checks">
          <div>
            <span>常见错误</span>
            <ul><li v-for="item in activeDocument.commonMistakes || []" :key="item">{{ item }}</li></ul>
          </div>
          <div>
            <span>巩固任务</span>
            <ol>
              <li v-for="item in activeDocument.practiceTasks || []" :key="item.order">
                <strong>{{ item.task }}</strong>
                <small v-if="item.expectedEvidence">验收证据：{{ item.expectedEvidence }}</small>
              </li>
            </ol>
          </div>
        </section>

        <footer class="document-evidence">
          <div>
            <BookOpen :size="18" />
            <span><strong>课程知识库来源</strong><small>关键事实可追溯</small></span>
          </div>
          <ol v-if="activeDocument.references?.length">
            <li v-for="item in activeDocument.references" :key="item.id"><b>[{{ item.id }}]</b>{{ item.title }} · {{ item.locator }}</li>
          </ol>
          <p v-else>未命中直接来源，文中硬件事实均应按“需进一步核验”处理。</p>
        </footer>
      </article>

      <section class="quality-band">
        <header><ShieldCheck :size="19" /><strong>资源质量评价</strong><span :class="{ passed: activeQuality.passed }">{{ activeQuality.passed ? '通过' : '需核验' }}</span></header>
        <div class="quality-grid">
          <div v-for="item in qualityCriteria" :key="item.label"><span>{{ item.label }}</span><strong>{{ item.value }}</strong></div>
        </div>
        <p v-for="item in activeQuality.issues || []" :key="item"><AlertTriangle :size="14" />{{ item }}</p>
      </section>
    </template>

    <section v-else-if="!generating" class="empty-document">
      <FileText :size="38" />
      <strong>暂无课程讲义</strong>
      <p>输入主题后由课程讲义生成智能体创建。</p>
    </section>
  </main>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { AlertTriangle, BookOpen, CheckCircle2, Download, FileText, History, LoaderCircle, Printer, RefreshCw, ShieldCheck, WandSparkles } from 'lucide-vue-next'
import LearningFeedbackActions from '../components/LearningFeedbackActions.vue'
import { getLearningDocument, getLearningDocuments, getXiaoZhiTask, startPersonalizedResourceAgentTask } from '../services/api.js'

const route = useRoute()
const router = useRouter()
const topic = ref(String(route.query.topic || 'STM32 GPIO 与外部中断'))
const requirements = ref(String(route.query.requirements || '结合当前薄弱点，包含知识依据、常见错误和可验收实践任务'))
const history = ref([])
const activeRecord = ref(null)
const taskId = ref(String(route.query.xzTask || ''))
const taskStatus = ref('')
const taskResult = ref({})
const taskProgress = ref(0)
const generating = ref(false)
const error = ref('')
let pollTimer = null

const activeDocument = computed(() => activeRecord.value?.document || taskResult.value?.document || null)
const activeQuality = computed(() => activeRecord.value?.qualityEvaluation || taskResult.value?.qualityEvaluation || {})
const feedbackTask = computed(() => {
  if (!taskId.value || taskStatus.value !== 'complete') return null
  return {
    taskId: taskId.value,
    taskType: 'document',
    status: taskStatus.value,
    title: activeDocument.value?.title || topic.value || '个性化课程讲义',
    result: taskResult.value,
  }
})
const taskMessage = computed(() => {
  if (taskStatus.value === 'failed') return error.value || '课程讲义生成失败'
  if (taskStatus.value === 'complete') return taskResult.value?.message || '课程讲义已生成并保存'
  return taskResult.value?.message || '嵌小智正在调度课程讲义生成智能体'
})
const qualityCriteria = computed(() => {
  const criteria = activeQuality.value?.criteria || {}
  return [
    { label: '结构完整', value: criteria.structure || 0 },
    { label: '知识依据', value: criteria.knowledgeGrounding || 0 },
    { label: '画像匹配', value: criteria.personalization || 0 },
    { label: '实践可用', value: criteria.practiceReadiness || 0 },
    { label: '内容安全', value: criteria.safety || 0 },
  ]
})

function sourceLabel(source) {
  if (source === 'llm') return '讯飞模型 + RAG'
  if (source === 'llm-schema-repaired') return '讯飞模型修订 + RAG'
  if (source === 'knowledge-template-fallback') return '知识库模板'
  return source || '课程讲义智能体'
}

async function loadHistory() {
  try {
    history.value = await getLearningDocuments(40)
  } catch {
    history.value = []
  }
}

async function openHistory(documentId) {
  if (!documentId) return
  error.value = ''
  try {
    activeRecord.value = await getLearningDocument(documentId)
    topic.value = activeRecord.value?.topic || topic.value
    await router.replace({ query: { ...route.query, documentId, autostart: undefined, xzTask: undefined } })
    stopPolling()
    generating.value = false
    taskStatus.value = 'complete'
  } catch (err) {
    error.value = err?.response?.data?.msg || err?.message || '课程讲义加载失败'
  }
}

async function startGeneration() {
  if (!topic.value || generating.value) return
  stopPolling()
  error.value = ''
  activeRecord.value = null
  taskResult.value = {}
  taskProgress.value = 2
  taskStatus.value = 'queued'
  generating.value = true
  try {
    const response = await startPersonalizedResourceAgentTask({
      resourceType: 'document',
      topic: topic.value,
      prompt: requirements.value || topic.value,
      params: { topic: topic.value, requirements: requirements.value },
    })
    const task = response?.data?.task
    if (!task?.taskId) throw new Error('未获得课程讲义任务 ID')
    taskId.value = task.taskId
    taskResult.value = task.result || {}
    taskStatus.value = task.status || 'queued'
    await router.replace({ query: { ...route.query, topic: topic.value, requirements: requirements.value, autostart: undefined, documentId: undefined, xzTask: taskId.value } })
    startPolling()
    await loadTask()
  } catch (err) {
    generating.value = false
    taskStatus.value = 'failed'
    error.value = err?.response?.data?.msg || err?.message || '课程讲义任务创建失败'
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
    taskProgress.value = Number(task.result?.progress || (task.status === 'complete' ? 100 : 8))
    generating.value = ['queued', 'running'].includes(task.status)
    if (task.status === 'complete') {
      stopPolling()
      generating.value = false
      if (task.result?.documentRecord) activeRecord.value = task.result.documentRecord
      else if (task.result?.documentId) activeRecord.value = await getLearningDocument(task.result.documentId)
      await loadHistory()
    } else if (task.status === 'failed') {
      stopPolling()
      generating.value = false
      error.value = task.error || task.result?.message || '课程讲义生成失败'
    }
  } catch (err) {
    stopPolling()
    generating.value = false
    taskStatus.value = 'failed'
    error.value = err?.response?.data?.msg || err?.message || '课程讲义任务状态读取失败'
  }
}

function startPolling() {
  stopPolling()
  pollTimer = window.setInterval(loadTask, 1800)
}

function stopPolling() {
  if (pollTimer) window.clearInterval(pollTimer)
  pollTimer = null
}

function downloadMarkdown() {
  if (!activeDocument.value) return
  const content = activeDocument.value.markdown || `# ${activeDocument.value.title}\n\n${activeDocument.value.abstract || ''}`
  const blob = new Blob([content], { type: 'text/markdown;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const anchor = document.createElement('a')
  anchor.href = url
  anchor.download = `${String(activeDocument.value.title || '课程讲义').replace(/[\\/:*?"<>|]/g, '_')}.md`
  anchor.click()
  URL.revokeObjectURL(url)
}

function printDocument() {
  window.print()
}

onMounted(async () => {
  await loadHistory()
  const documentId = String(route.query.documentId || '')
  if (taskId.value) {
    generating.value = true
    startPolling()
    await loadTask()
  } else if (documentId) {
    await openHistory(documentId)
  } else if (String(route.query.autostart || '') === '1') {
    await startGeneration()
  } else if (history.value.length) {
    activeRecord.value = history.value[0]
  }
})

onBeforeUnmount(stopPolling)
</script>

<style scoped>
.document-page{height:100vh;overflow-x:hidden;overflow-y:auto;overscroll-behavior:contain;background:#f5f8f6;color:#203630;padding:28px 32px 64px}.document-toolbar{max-width:1240px;margin:0 auto 18px;display:flex;align-items:flex-end;justify-content:space-between;gap:24px}.document-title-block>span{display:flex;align-items:center;gap:7px;color:#177951;font-size:13px;font-weight:800}.document-title-block h1{margin:8px 0 5px;font-size:28px;line-height:1.2;letter-spacing:0}.document-title-block p{margin:0;color:#73827d;font-size:13px}.document-actions{display:flex;align-items:center;gap:8px}.document-actions label{height:38px;display:flex;align-items:center;gap:7px;border:1px solid #d6e2dc;background:#fff;padding:0 10px}.document-actions select{max-width:210px;border:0;background:transparent;color:#314a42;outline:none}.document-actions button{width:38px;height:38px;display:grid;place-items:center;border:1px solid #d6e2dc;background:#fff;color:#315c4c;cursor:pointer}.document-actions button:disabled{opacity:.4;cursor:not-allowed}.generation-band{max-width:1240px;margin:0 auto 14px;display:grid;grid-template-columns:1fr 1.4fr auto;align-items:end;gap:12px;padding:15px 0;border-top:1px solid #dbe5e0;border-bottom:1px solid #dbe5e0}.field{display:grid;gap:6px}.field label{font-size:12px;font-weight:800;color:#536b62}.field input{height:40px;border:1px solid #cedbd5;background:#fff;padding:0 12px;outline:none}.field input:focus{border-color:#2c8b62;box-shadow:0 0 0 3px rgba(44,139,98,.1)}.generate-button{height:40px;display:flex;align-items:center;gap:7px;border:0;background:#176e4a;color:#fff;padding:0 17px;font-weight:800;cursor:pointer}.generate-button:disabled{opacity:.55;cursor:not-allowed}.task-progress,.error-band,.document-meta-band,.document-sheet,.quality-band,.empty-document{max-width:1240px;margin-left:auto;margin-right:auto}.task-progress{display:grid;grid-template-columns:minmax(0,1fr) 220px auto;align-items:center;gap:16px;padding:12px 14px;background:#eaf5ef;border-left:3px solid #27855f}.task-progress>div:first-child{display:flex;align-items:center;gap:10px;color:#246e53}.task-progress span{display:grid;gap:2px}.task-progress small{color:#72847d;font-size:11px}.task-progress.failed{background:#fff0ec;border-color:#c05c3f;color:#9c432e}.task-progress button{display:flex;align-items:center;gap:6px;border:0;background:#fff;padding:8px 11px;color:#8b3d2b;cursor:pointer}.progress-track{height:5px;background:#d0dfd7;overflow:hidden}.progress-track i{display:block;height:100%;background:#26885f;transition:width .35s ease}.error-band{margin-top:12px;padding:11px 13px;display:flex;gap:8px;align-items:center;background:#fff0ec;color:#a44731}.document-meta-band{margin-top:18px;display:grid;grid-template-columns:repeat(4,1fr);background:#273d37;color:#fff}.document-meta-band>div{padding:15px 18px;border-right:1px solid rgba(255,255,255,.14)}.document-meta-band span{display:block;color:#b8cbc4;font-size:11px}.document-meta-band strong{display:inline-block;margin-top:4px;font-size:16px}.document-meta-band em{font-size:11px;color:#b8cbc4;font-style:normal}.quality-score strong{color:#9ee4bd;font-size:22px}.document-feedback{max-width:1240px;margin:12px auto;padding:12px 14px;border:1px solid #dbe4df;background:#fff}.document-sheet{margin-top:0;background:#fff;border:1px solid #dbe4df}.sheet-cover{padding:44px 52px 36px;border-bottom:1px solid #dfe8e3;background:linear-gradient(115deg,#f7fbf8 0 76%,#eef4f0 76%)}.sheet-cover>span{font-size:11px;font-weight:900;color:#9a7129}.sheet-cover h2{max-width:820px;margin:11px 0 13px;font-size:32px;line-height:1.22;letter-spacing:0}.sheet-cover p{max-width:850px;margin:0;color:#5b6f67;line-height:1.8}.objective-row{display:flex;flex-wrap:wrap;gap:7px;margin-top:20px}.objective-row b{padding:6px 9px;background:#e4f3eb;color:#1e7552;font-size:12px;font-weight:700}.document-section{display:grid;grid-template-columns:58px minmax(0,1fr);gap:24px;padding:32px 52px;border-bottom:1px solid #e5ece8}.section-index{font-size:18px;font-weight:900;color:#b58a3e}.document-section h3{margin:0 0 8px;font-size:20px}.section-summary{margin:0 0 12px;color:#247554;font-weight:700}.section-content{white-space:pre-wrap;margin:0;color:#425a52;line-height:1.85}.document-section ul{margin:15px 0 0;padding-left:20px;color:#3f574f}.document-section li{margin:7px 0;line-height:1.65}.document-section blockquote{margin:18px 0 0;padding:14px 16px;border-left:3px solid #b58a3e;background:#fbf7ef;color:#665331}.document-section pre{margin:18px 0 0;padding:17px;background:#1f2e2a;color:#d9f5e7;overflow:auto;line-height:1.65}.learning-checks{display:grid;grid-template-columns:1fr 1fr;gap:0;border-bottom:1px solid #dfe8e3}.learning-checks>div{padding:30px 52px}.learning-checks>div+div{border-left:1px solid #dfe8e3}.learning-checks>div>span{color:#9a7129;font-size:12px;font-weight:900}.learning-checks ul,.learning-checks ol{padding-left:20px;margin:14px 0 0}.learning-checks li{margin:9px 0;line-height:1.6}.learning-checks li strong,.learning-checks li small{display:block}.learning-checks li small{margin-top:4px;color:#6d7e78}.document-evidence{padding:26px 52px;background:#f2f7f4}.document-evidence>div{display:flex;align-items:center;gap:9px;color:#256a4e}.document-evidence span{display:grid}.document-evidence small{color:#778a83}.document-evidence ol{margin:16px 0 0;padding-left:24px}.document-evidence li{margin:7px 0;color:#52675f}.document-evidence b{margin-right:6px;color:#1f7954}.quality-band{margin-top:14px;padding:20px 22px;background:#fff;border:1px solid #dbe4df}.quality-band header{display:flex;align-items:center;gap:8px}.quality-band header span{margin-left:auto;padding:4px 8px;background:#fff0ec;color:#a54b35;font-size:11px;font-weight:800}.quality-band header span.passed{background:#e4f5eb;color:#1e7552}.quality-grid{display:grid;grid-template-columns:repeat(5,1fr);gap:1px;margin-top:16px;background:#dfe8e3}.quality-grid div{display:flex;justify-content:space-between;padding:11px 12px;background:#f7faf8}.quality-grid span{color:#64766f;font-size:12px}.quality-band>p{display:flex;align-items:center;gap:6px;margin:12px 0 0;color:#a04a34;font-size:12px}.empty-document{min-height:360px;display:grid;place-content:center;justify-items:center;gap:8px;color:#779087}.empty-document strong{color:#315148}.empty-document p{margin:0}.spin{animation:spin .8s linear infinite}@keyframes spin{to{transform:rotate(360deg)}}@media(max-width:900px){.document-page{padding:20px 16px 80px}.document-toolbar{align-items:flex-start}.generation-band{grid-template-columns:1fr}.task-progress{grid-template-columns:1fr}.document-meta-band{grid-template-columns:repeat(2,1fr)}.sheet-cover,.document-section,.learning-checks>div,.document-evidence{padding-left:22px;padding-right:22px}.learning-checks{grid-template-columns:1fr}.learning-checks>div+div{border-left:0;border-top:1px solid #dfe8e3}.quality-grid{grid-template-columns:1fr 1fr}.document-section{grid-template-columns:36px minmax(0,1fr)}}@media(max-width:560px){.document-toolbar{display:grid}.document-actions{width:100%}.document-actions label{flex:1}.document-actions select{width:100%}.document-title-block h1{font-size:24px}.document-meta-band{grid-template-columns:1fr 1fr}.sheet-cover h2{font-size:26px}.document-section{display:block}.section-index{margin-bottom:10px}.quality-grid{grid-template-columns:1fr}}@media print{.document-toolbar,.generation-band,.task-progress,.error-band,.quality-band,.document-feedback{display:none!important}.document-page{height:auto;overflow:visible;padding:0;background:#fff}.document-meta-band{background:#fff;color:#222;border:1px solid #ddd}.document-meta-band span,.document-meta-band em{color:#555}.document-sheet{border:0}.sheet-cover{background:#fff}}
@media(max-width:560px){.document-section pre{max-width:100%;min-width:0;white-space:pre-wrap;overflow-wrap:anywhere;word-break:break-word}.document-section code{white-space:inherit;overflow-wrap:anywhere;word-break:break-word}}
.document-sheet,.document-section>div:last-child{min-width:0}.section-content{overflow-wrap:anywhere;word-break:break-word}
</style>
