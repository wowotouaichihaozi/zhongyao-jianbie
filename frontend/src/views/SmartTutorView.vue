<template>
  <main class="tutor-page" :class="{ embedded: isEmbedded }">
    <header class="tutor-head">
      <div>
        <span><BrainCircuit :size="18" />SMART TUTOR</span>
        <h1>{{ tutor.question || task?.title || '个性化智能辅导' }}</h1>
      </div>
    </header>

    <section v-if="isRunning && isEmbedded" class="progress-band" role="status">
      <div>
        <strong>{{ result.message || '岐小智正在编排智能辅导任务' }}</strong>
        <span>{{ result.currentStage || 'supervisor_dispatch' }}</span>
      </div>
      <div class="progress-track"><i :style="{ width: `${taskProgress}%` }"></i></div>
      <em>{{ taskProgress }}%</em>
    </section>

    <section v-else-if="error" class="error-band" role="alert">
      <AlertTriangle :size="18" />
      <span>{{ error }}</span>
      <button type="button" @click="loadTask"><RefreshCw :size="16" />重试</button>
    </section>

    <template v-if="tutor.answer">
      <form class="follow-up-band" @submit.prevent="submitFollowUp">
        <div>
          <MessagesSquare :size="18" />
          <span><strong>继续辅导</strong><small>{{ tutor.followUp || '岐小智会结合本轮回答继续追问。' }}</small></span>
        </div>
        <textarea v-model.trim="followUpDraft" rows="2" placeholder="输入回答或追问" :disabled="followUpSending"></textarea>
        <button type="button" :disabled="followUpSending || !followUpDraft" @click="submitFollowUp">
          <LoaderCircle v-if="followUpSending" :size="17" class="spin" />
          <Send v-else :size="17" />
          {{ followUpSending ? '正在交给岐小智' : '提交' }}
        </button>
        <p v-if="followUpError">{{ followUpError }}</p>
      </form>

      <div class="tutor-workspace">
        <div class="lesson-column">
          <section class="answer-band">
            <span>核心回答</span>
            <p>{{ tutor.answer }}</p>
          </section>

          <section class="lesson-section explanation-section">
            <header><BookOpenCheck :size="19" /><h2>机制讲解</h2></header>
            <p>{{ tutor.explanation?.concept }}</p>
            <blockquote v-if="tutor.explanation?.analogy">{{ tutor.explanation.analogy }}</blockquote>
            <ol>
              <li v-for="step in tutor.explanation?.steps || []" :key="step">{{ step }}</li>
            </ol>
          </section>

          <section class="lesson-section">
            <header><MessagesSquare :size="19" /><h2>苏格拉底式追问</h2><em>{{ tutor.socraticQuestions?.length || 0 }} 题</em></header>
            <article v-for="item in tutor.socraticQuestions || []" :key="item.id" class="question-row">
              <b>{{ item.id }}</b>
              <div>
                <h3>{{ item.question }}</h3>
                <p v-if="revealedSocratic.has(item.id)"><strong>判断要点：</strong>{{ item.expectedKeyPoints }}</p>
                <button type="button" @click="toggleSet(revealedSocratic, item.id)">
                  <EyeOff v-if="revealedSocratic.has(item.id)" :size="15" />
                  <Eye v-else :size="15" />
                  {{ revealedSocratic.has(item.id) ? '收起判断要点' : '查看判断要点' }}
                </button>
              </div>
            </article>
          </section>

          <section class="lesson-section feynman-section">
            <header><Mic2 :size="19" /><h2>费曼复述任务</h2></header>
            <p>{{ tutor.feynmanTask?.prompt }}</p>
            <div class="check-list">
              <span v-for="item in tutor.feynmanTask?.checklist || []" :key="item"><Check :size="14" />{{ item }}</span>
            </div>
          </section>

          <section class="lesson-section hint-section">
            <header><Lightbulb :size="19" /><h2>三级提示</h2><em>{{ revealedHintLevel }}/3 已揭示</em></header>
            <article v-for="hint in tutor.hintLadder || []" :key="hint.level" :class="['hint-row', { locked: revealedHintLevel < hint.level }]">
              <b>LEVEL {{ hint.level }}</b>
              <div v-if="revealedHintLevel >= hint.level">
                <strong>{{ hint.label }}</strong>
                <p>{{ hint.hint }}</p>
              </div>
              <button v-else type="button" @click="revealHint(hint.level)"><Unlock :size="15" />显示第 {{ hint.level }} 级提示</button>
            </article>
          </section>

          <section class="lesson-section practice-section">
            <header><ListChecks :size="19" /><h2>巩固练习</h2><em>{{ tutor.practiceTasks?.length || 0 }} 题</em></header>
            <article v-for="item in tutor.practiceTasks || []" :key="item.id" class="practice-row">
              <div class="practice-title"><b>{{ item.id }}</b><span>{{ item.type }}</span><em>{{ item.difficulty }}</em></div>
              <h3>{{ item.question }}</h3>
              <div v-if="revealedPractice.has(item.id)" class="practice-answer">
                <p><strong>答案：</strong>{{ item.answer }}</p>
                <p><strong>解析：</strong>{{ item.explanation }}</p>
                <p><strong>验收：</strong>{{ item.acceptanceCriteria }}</p>
              </div>
              <button type="button" @click="toggleSet(revealedPractice, item.id)">
                <EyeOff v-if="revealedPractice.has(item.id)" :size="15" />
                <Eye v-else :size="15" />
                {{ revealedPractice.has(item.id) ? '收起答案' : '查看答案与解析' }}
              </button>
            </article>
          </section>
        </div>

        <aside class="support-column">
          <section class="support-section diagram-section">
            <header><Workflow :size="18" /><h2>学习流程</h2></header>
            <div v-if="diagramLoading" class="diagram-loading"><LoaderCircle :size="26" class="spin" /></div>
            <div v-else-if="diagramSvg" class="mermaid-output" v-html="diagramSvg"></div>
            <pre v-else><code>{{ tutor.multimodal?.mermaid?.code }}</code></pre>
          </section>

          <section class="support-section learning-card-section">
            <header><Layers3 :size="18" /><h2>学习卡</h2></header>
            <button class="flip-card" type="button" @click="cardFlipped = !cardFlipped">
              <span>{{ cardFlipped ? 'BACK' : 'FRONT' }}</span>
              <strong>{{ cardFlipped ? tutor.multimodal?.learningCard?.back : tutor.multimodal?.learningCard?.front }}</strong>
              <small><RotateCcw :size="14" />切换卡面</small>
            </button>
            <div class="key-points">
              <span v-for="item in tutor.multimodal?.learningCard?.keyPoints || []" :key="item">{{ item }}</span>
            </div>
          </section>

          <section class="support-section">
            <header><Volume2 :size="18" /><h2>讲解脚本</h2></header>
            <ol class="narration-list"><li v-for="item in tutor.multimodal?.narrationScript || []" :key="item">{{ item }}</li></ol>
          </section>

          <section class="support-section references-section">
            <header><Library :size="18" /><h2>知识依据</h2><em>{{ tutor.references?.length || 0 }}</em></header>
            <ol v-if="tutor.references?.length">
              <li v-for="item in tutor.references" :key="item.id"><b>[{{ item.id }}]</b><span>{{ item.title }}</span><small>{{ referenceLocator(item) }}</small></li>
            </ol>
            <p v-for="item in tutor.uncertainties || []" :key="item" class="uncertainty"><AlertTriangle :size="14" />{{ item }}</p>
          </section>

          <section class="support-section harness-section">
            <header><Network :size="18" /><h2>总控执行轨迹</h2></header>
            <dl>
              <div><dt>Root Agent</dt><dd>{{ orchestration.rootAgentName || orchestration.rootAgent || '岐小智' }}</dd></div>
              <div><dt>Skill</dt><dd>{{ harness.skill?.id || 'learning.tutor.answer' }}</dd></div>
              <div><dt>MCP Tool</dt><dd>{{ harness.mcp?.toolCalls?.[0]?.tool || 'learning.tutor.answer' }}</dd></div>
              <div><dt>Run ID</dt><dd>{{ orchestration.runId || harness.runId || '--' }}</dd></div>
            </dl>
          </section>
        </aside>
      </div>
    </template>

    <section v-else-if="!isRunning && !error" class="empty-state">
      <BrainCircuit :size="38" />
      <strong>暂无辅导任务</strong>
    </section>
  </main>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  AlertTriangle,
  BookOpenCheck,
  BrainCircuit,
  Check,
  CheckCircle2,
  Eye,
  EyeOff,
  Layers3,
  Library,
  Lightbulb,
  ListChecks,
  LoaderCircle,
  MessagesSquare,
  Mic2,
  Network,
  RefreshCw,
  RotateCcw,
  Send,
  Unlock,
  Volume2,
  Workflow,
} from 'lucide-vue-next'
import { chatWithXiaoZhi, getXiaoZhiTask } from '../services/api.js'

const route = useRoute()
const router = useRouter()
const taskId = ref(String(route.query.xzTask || ''))
const task = ref(null)
const error = ref('')
const diagramSvg = ref('')
const diagramLoading = ref(false)
const cardFlipped = ref(false)
const revealedHintLevel = ref(0)
const revealedSocratic = reactive(new Set())
const revealedPractice = reactive(new Set())
const followUpDraft = ref('')
const followUpSending = ref(false)
const followUpError = ref('')
let pollTimer = null
let renderSequence = 0

const isEmbedded = computed(() => route.query.xzEmbed === '1' || route.query.embed === 'xiaozhi')
const result = computed(() => task.value?.result || {})
const tutor = computed(() => result.value?.tutor || {})
const harness = computed(() => result.value?.harness || {})
const orchestration = computed(() => result.value?.orchestration || {})
const review = computed(() => orchestration.value?.review || result.value?.review || {})
const isRunning = computed(() => ['queued', 'running'].includes(task.value?.status))
const taskProgress = computed(() => Math.max(0, Math.min(100, Number(result.value?.progress || (task.value?.status === 'complete' ? 100 : 8)))))
const taskStateText = computed(() => {
  if (task.value?.status === 'complete') return '辅导完成'
  if (task.value?.status === 'failed') return '生成失败'
  return '生成中'
})
const profileReportId = computed(() => harness.value?.profileReportId || orchestration.value?.profileReportId || 0)
const modelName = computed(() => harness.value?.modelRuntime?.model || '')

function toggleSet(target, key) {
  if (target.has(key)) target.delete(key)
  else target.add(key)
}

function revealHint(level) {
  if (Number(level) <= revealedHintLevel.value + 1) revealedHintLevel.value = Number(level)
}

function referenceLocator(item) {
  if (item?.page) return `第 ${item.page} 页`
  if (item?.section) return `第 ${item.section} 节`
  return item?.source || '课程知识库'
}

async function submitFollowUp() {
  const learnerReply = followUpDraft.value.trim()
  if (!learnerReply || followUpSending.value) return
  followUpSending.value = true
  followUpError.value = ''
  try {
    const firstQuestion = tutor.value?.socraticQuestions?.[0]?.question || ''
    const message = [
      '继续智能辅导，请基于上一轮内容判断我的理解并继续苏格拉底式追问。',
      `上一轮主题：${tutor.value?.question || task.value?.title || '当前学习主题'}`,
      firstQuestion ? `当前追问：${firstQuestion}` : '',
      `我的回答或追问：${learnerReply}`,
    ].filter(Boolean).join('\n')
    const response = await chatWithXiaoZhi({ message, route: route.fullPath })
    const cards = response?.data?.cards || []
    const nextTask = cards.find(item => String(item?.type || item?.taskType || '') === 'smart_tutor')
    if (!nextTask?.taskId) {
      throw new Error(response?.data?.reply || '岐小智没有创建下一轮辅导任务')
    }
    followUpDraft.value = ''
    await router.push({
      path: '/smart-tutor',
      query: { ...route.query, xzTask: nextTask.taskId },
    })
  } catch (err) {
    followUpError.value = err?.response?.data?.msg || err?.message || '下一轮辅导启动失败'
  } finally {
    followUpSending.value = false
  }
}

async function renderDiagram(code) {
  const source = String(code || '').trim()
  const sequence = ++renderSequence
  diagramSvg.value = ''
  if (!source) return
  diagramLoading.value = true
  try {
    const { default: mermaid } = await import('mermaid')
    mermaid.initialize({
      startOnLoad: false,
      securityLevel: 'strict',
      theme: 'base',
      themeVariables: {
        primaryColor: '#e8f4ed',
        primaryTextColor: '#203a31',
        primaryBorderColor: '#4c9272',
        lineColor: '#61766e',
        secondaryColor: '#f5efe2',
        tertiaryColor: '#f7faf8',
        fontFamily: 'Inter, Microsoft YaHei, sans-serif',
      },
    })
    const rendered = await mermaid.render(`smart-tutor-${Date.now()}-${sequence}`, source)
    if (sequence === renderSequence) diagramSvg.value = rendered.svg
  } catch (err) {
    if (sequence === renderSequence) diagramSvg.value = ''
  } finally {
    if (sequence === renderSequence) diagramLoading.value = false
  }
}

async function loadTask() {
  if (!taskId.value) return
  error.value = ''
  try {
    const response = await getXiaoZhiTask(taskId.value)
    task.value = response?.data?.task || null
    if (!task.value) throw new Error('未找到辅导任务')
    if (task.value.status === 'failed') {
      stopPolling()
      error.value = task.value.error || task.value.result?.message || '智能辅导生成失败'
    } else if (task.value.status === 'complete') {
      stopPolling()
    } else {
      startPolling()
    }
  } catch (err) {
    stopPolling()
    error.value = err?.response?.data?.msg || err?.message || '辅导任务读取失败'
  }
}

function startPolling() {
  if (pollTimer) return
  pollTimer = window.setInterval(loadTask, 1800)
}

function stopPolling() {
  if (pollTimer) window.clearInterval(pollTimer)
  pollTimer = null
}

watch(
  () => tutor.value?.multimodal?.mermaid?.code,
  async code => {
    await nextTick()
    renderDiagram(code)
  },
  { immediate: true },
)

onMounted(loadTask)
onBeforeUnmount(() => {
  stopPolling()
  renderSequence += 1
})
</script>

<style scoped>
.tutor-page{min-height:100vh;padding:28px 32px 72px;background:#f4f7f5;color:#21372f;letter-spacing:0}.tutor-page.embedded{padding:18px 16px 40px}.tutor-head{max-width:1380px;margin:0 auto 18px;display:flex;align-items:flex-end;justify-content:space-between;gap:24px}.tutor-head>div:first-child>span{display:flex;align-items:center;gap:7px;color:#237451;font-size:12px;font-weight:900}.tutor-head h1{max-width:980px;margin:8px 0 4px;font-size:27px;line-height:1.3;letter-spacing:0}.tutor-head p{margin:0;color:#778780;font-size:11px}.task-state{display:flex;align-items:center;gap:7px;padding:9px 12px;border:1px solid #bcd9cb;background:#e9f5ee;color:#236f50;font-size:12px;font-weight:800}.task-state.failed{border-color:#e3c1b7;background:#fff1ed;color:#9d462f}.progress-band,.error-band,.evidence-strip,.tutor-workspace,.empty-state{max-width:1380px;margin-left:auto;margin-right:auto}.progress-band{display:grid;grid-template-columns:minmax(0,1fr) 280px 44px;align-items:center;gap:16px;padding:13px 16px;background:#e7f2ec;border-left:3px solid #2d835f}.progress-band>div:first-child{display:grid;gap:3px}.progress-band span{color:#6f827a;font-size:11px}.progress-band em{font-style:normal;font-size:12px;font-weight:900;color:#286d50}.progress-track{height:6px;background:#cadbd2;overflow:hidden}.progress-track i{display:block;height:100%;background:#2d835f;transition:width .35s ease}.error-band{display:flex;align-items:center;gap:9px;padding:13px 15px;background:#fff0ec;color:#9f442e}.error-band button{margin-left:auto;display:flex;align-items:center;gap:6px;border:1px solid #d8a99b;background:#fff;padding:7px 10px;color:inherit;cursor:pointer}.evidence-strip{display:grid;grid-template-columns:repeat(5,minmax(0,1fr));margin-top:16px;background:#263b34;color:#fff}.evidence-strip>div{padding:14px 17px;border-right:1px solid rgba(255,255,255,.13)}.evidence-strip span{display:block;color:#aec4bb;font-size:10px}.evidence-strip strong{display:block;margin-top:4px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;font-size:14px}.tutor-workspace{display:grid;grid-template-columns:minmax(0,1.65fr) minmax(320px,.78fr);gap:18px;margin-top:18px}.lesson-column,.support-column{min-width:0;display:grid;align-content:start;gap:14px}.answer-band{padding:24px 28px;background:#fff;border-top:3px solid #27805c}.answer-band>span,.lesson-section>header em,.support-section>header em{color:#9b742d;font-size:11px;font-weight:900;font-style:normal}.answer-band p{margin:9px 0 0;color:#314b42;font-size:15px;line-height:1.85}.lesson-section,.support-section{background:#fff;border:1px solid #dce5e0}.lesson-section{padding:22px 26px}.lesson-section>header,.support-section>header{display:flex;align-items:center;gap:8px;margin-bottom:15px;color:#245c47}.lesson-section>header h2,.support-section>header h2{margin:0;font-size:17px;letter-spacing:0}.lesson-section>header em,.support-section>header em{margin-left:auto}.explanation-section>p{margin:0;color:#40584f;line-height:1.8}.explanation-section blockquote{margin:16px 0 0;padding:12px 14px;border-left:3px solid #b18a46;background:#fbf8f1;color:#66583e}.explanation-section ol{margin:16px 0 0;padding-left:22px}.explanation-section li{margin:8px 0;color:#3e554d;line-height:1.65}.question-row{display:grid;grid-template-columns:42px minmax(0,1fr);gap:14px;padding:16px 0;border-top:1px solid #e5ece8}.question-row>b{display:grid;width:38px;height:30px;place-items:center;background:#e7f2ec;color:#267353;font-size:11px}.question-row h3,.practice-row h3{margin:0;color:#2f463e;font-size:14px;line-height:1.65;letter-spacing:0}.question-row p{margin:10px 0 0;padding:10px 12px;background:#f6f8f7;color:#536860;font-size:12px;line-height:1.65}.question-row button,.practice-row button,.hint-row button{display:flex;align-items:center;gap:6px;margin-top:10px;border:0;background:transparent;padding:0;color:#277555;font-size:12px;font-weight:800;cursor:pointer}.feynman-section>p{margin:0;color:#364f46;line-height:1.8}.check-list{display:flex;flex-wrap:wrap;gap:7px;margin-top:14px}.check-list span{display:flex;align-items:center;gap:5px;padding:6px 8px;background:#f2f6f4;color:#53675f;font-size:11px}.hint-row{display:grid;grid-template-columns:74px minmax(0,1fr);gap:14px;padding:15px 0;border-top:1px solid #e5ece8}.hint-row>b{color:#9a712d;font-size:10px}.hint-row strong{font-size:13px}.hint-row p{margin:6px 0 0;color:#4e645c;font-size:13px;line-height:1.65}.hint-row.locked{min-height:46px;align-items:center}.hint-row.locked button{margin:0}.practice-row{padding:17px 0;border-top:1px solid #e5ece8}.practice-title{display:flex;align-items:center;gap:7px;margin-bottom:8px}.practice-title b{color:#286f52}.practice-title span,.practice-title em{padding:3px 6px;background:#eef3f0;color:#64766f;font-size:10px;font-style:normal}.practice-answer{margin-top:12px;padding:12px 14px;background:#f5f8f6}.practice-answer p{margin:5px 0;color:#4c625a;font-size:12px;line-height:1.65}.support-section{padding:18px}.diagram-loading{min-height:220px;display:grid;place-items:center;color:#2d805d}.mermaid-output{overflow:auto}.mermaid-output :deep(svg){display:block;max-width:100%;height:auto;margin:auto}.diagram-section pre{max-height:280px;margin:0;padding:13px;overflow:auto;background:#263934;color:#d8f0e4;font-size:11px;white-space:pre-wrap}.flip-card{width:100%;min-height:150px;display:grid;align-content:space-between;gap:12px;border:1px solid #cdded5;background:#edf5f0;padding:16px;text-align:left;color:#28463a;cursor:pointer}.flip-card>span{color:#9b742d;font-size:10px;font-weight:900}.flip-card>strong{font-size:14px;line-height:1.65}.flip-card>small{display:flex;align-items:center;gap:5px;color:#637970}.key-points{display:flex;flex-wrap:wrap;gap:6px;margin-top:10px}.key-points span{padding:5px 7px;background:#f1ece1;color:#745d31;font-size:10px}.narration-list{margin:0;padding-left:21px}.narration-list li{margin:8px 0;color:#4d635b;font-size:12px;line-height:1.6}.references-section ol{margin:0;padding:0;list-style:none}.references-section li{display:grid;grid-template-columns:36px minmax(0,1fr);gap:4px 7px;padding:10px 0;border-top:1px solid #e5ece8}.references-section li b{grid-row:1/3;color:#287153;font-size:11px}.references-section li span{font-size:12px;color:#334b42}.references-section li small{color:#7c8c85;font-size:10px}.uncertainty{display:flex;align-items:flex-start;gap:6px;margin:10px 0 0;padding:9px 10px;background:#fff7eb;color:#806535;font-size:11px;line-height:1.5}.harness-section dl{margin:0}.harness-section dl>div{display:grid;grid-template-columns:82px minmax(0,1fr);gap:8px;padding:8px 0;border-top:1px solid #e5ece8}.harness-section dt{color:#72837c;font-size:10px}.harness-section dd{margin:0;overflow-wrap:anywhere;color:#385048;font-size:11px;font-weight:700}.empty-state{min-height:420px;display:grid;place-content:center;justify-items:center;gap:10px;color:#789088}.empty-state strong{color:#36574b}.spin{animation:tutor-spin .8s linear infinite}@keyframes tutor-spin{to{transform:rotate(360deg)}}@media(max-width:1050px){.tutor-workspace{grid-template-columns:1fr}.support-column{grid-template-columns:repeat(2,minmax(0,1fr))}.evidence-strip{grid-template-columns:repeat(3,minmax(0,1fr))}}@media(max-width:720px){.tutor-page{padding:20px 14px 82px}.tutor-head{align-items:flex-start}.tutor-head h1{font-size:22px}.task-state{flex:none}.progress-band{grid-template-columns:1fr 40px}.progress-track{grid-column:1/3;grid-row:2}.evidence-strip{grid-template-columns:repeat(2,minmax(0,1fr))}.tutor-workspace{gap:12px}.lesson-section{padding:18px}.answer-band{padding:20px}.support-column{grid-template-columns:1fr}.question-row{grid-template-columns:34px minmax(0,1fr)}.hint-row{grid-template-columns:64px minmax(0,1fr)}}
.follow-up-band {
  position: relative;
  max-width: 1380px;
  display: grid;
  grid-template-columns: minmax(220px, 0.75fr) minmax(280px, 1.5fr) auto;
  align-items: center;
  gap: 12px;
  margin: 14px auto 0;
  padding: 14px 16px;
  border: 1px solid #d9e5df;
  background: #fff;
}

.follow-up-band > div {
  display: flex;
  align-items: center;
  gap: 9px;
  color: #276f52;
}

.follow-up-band > div span {
  min-width: 0;
  display: grid;
  gap: 2px;
}

.follow-up-band > div strong { font-size: 13px; }

.follow-up-band > div small {
  overflow: hidden;
  color: #75867f;
  font-size: 10px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.follow-up-band textarea {
  width: 100%;
  min-height: 48px;
  max-height: 120px;
  resize: vertical;
  box-sizing: border-box;
  border: 1px solid #cddbd4;
  background: #f8faf9;
  padding: 10px 12px;
  color: #2d453c;
  font: inherit;
  font-size: 13px;
  line-height: 1.45;
}

.follow-up-band > button {
  min-height: 42px;
  display: flex;
  align-items: center;
  gap: 7px;
  border: 0;
  background: #287b59;
  padding: 0 15px;
  color: #fff;
  font-weight: 800;
  cursor: pointer;
}

.follow-up-band > button:disabled { cursor: not-allowed; opacity: 0.55; }
.follow-up-band > p { grid-column: 2 / 4; margin: 0; color: #a44731; font-size: 11px; }

@media (max-width: 1050px) {
  .follow-up-band { grid-template-columns: 1fr auto; }
  .follow-up-band > div { grid-column: 1 / 3; }
  .follow-up-band > p { grid-column: 1 / 3; }
}

@media (max-width: 720px) {
  .follow-up-band { grid-template-columns: 1fr; }
  .follow-up-band > div,
  .follow-up-band textarea,
  .follow-up-band > button,
  .follow-up-band > p { grid-column: 1; }
  .follow-up-band > button { justify-content: center; }
}
</style>
