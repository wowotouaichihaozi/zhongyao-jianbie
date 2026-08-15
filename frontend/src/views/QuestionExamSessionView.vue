<template>
  <main class="qg-exam-session">
    <div class="qg-session-topbar">
      <strong>考试详情</strong>
      <div class="qg-session-topbar-actions">
        <div v-if="questions.length && !examFinished" class="qg-session-timer" aria-label="考试用时">
          <Clock3 :size="16" aria-hidden="true" />
          <span>{{ formattedElapsedTime }}</span>
        </div>
        <button
          type="button"
          class="qg-session-exit"
          :aria-label="examFinished || !questions.length ? '返回题库' : '退出考试'"
          @click="exitExam"
        >
          <ArrowLeft :size="16" aria-hidden="true" />
          <span>{{ examFinished || !questions.length ? '返回题库' : '退出考试' }}</span>
        </button>
      </div>
    </div>

    <!-- 考试结果面板 -->
    <div v-if="examFinished" class="qg-session-result">
      <div class="qg-result-card">
        <div class="qg-result-icon" :class="resultClass">
          <svg viewBox="0 0 24 24" width="48" height="48" fill="none" stroke="currentColor" stroke-width="2">
            <path v-if="isPassed" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/>
            <path v-else d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4.5c-.77-.833-2.694-.833-3.464 0L3.34 16.5c-.77.833.192 2.5 1.732 2.5z"/>
          </svg>
        </div>
        <h2>{{ isPassed ? '考试通过' : '考试未通过' }}</h2>
        <div class="qg-result-score">
          <span class="qg-score-num">{{ examResult.score }}</span>
          <span class="qg-score-total">/ {{ examResult.total_score }} 分</span>
        </div>
        <div class="qg-result-stats">
          <div class="qg-stat-item">
            <strong>{{ examResult.correct_count }}</strong>
            <span>正确</span>
          </div>
          <div class="qg-stat-item">
            <strong>{{ examResult.question_count - examResult.correct_count }}</strong>
            <span>错误</span>
          </div>
          <div class="qg-stat-item">
            <strong>{{ formattedElapsedTime }}</strong>
            <span>用时</span>
          </div>
          <div class="qg-stat-item">
            <strong>{{ accuracyPercent }}%</strong>
            <span>正确率</span>
          </div>
        </div>

        <div class="qg-ai-rescore-panel" :class="{ active: aiScoreMessage }">
          <div>
            <strong>AI 复核评分</strong>
            <span>{{ aiScoreMessage || '填空题、简答题缺少标准答案时，可交给 AI 根据题干、语义和作答完整度重新评分。' }}</span>
          </div>
          <button type="button" class="qg-btn-ai" :disabled="aiScoring || !examResult.detail?.length" @click="requestAiRescore">
            {{ aiScoring ? 'AI 复核中...' : '申请 AI 复核评分' }}
          </button>
        </div>

        <!-- 错题详情 -->
        <div class="qg-result-wrong" v-if="wrongQuestions.length">
          <h3>错题回顾</h3>
          <div v-for="(item, idx) in wrongQuestions" :key="item.question_id || item.question_number || idx" class="qg-wrong-item">
            <p class="qg-wrong-stem">{{ formatWrongQuestionNo(item) }}. {{ item.stem }}</p>
            <p class="qg-wrong-answer">你的答案：<span class="wrong">{{ item.user_answer || '未作答' }}</span></p>
            <p class="qg-wrong-answer">正确答案：<span class="correct">{{ item.answer }}</span></p>
            <p class="qg-wrong-analysis" v-if="item.analysis">{{ item.analysis }}</p>
            <p class="qg-ai-comment" v-if="item.ai_comment">AI 复核：{{ item.ai_comment }}</p>
          </div>
        </div>

        <div class="qg-result-actions">
          <button type="button" class="qg-btn-primary" @click="backToGenerator">返回题库</button>
          <button type="button" class="qg-btn-secondary" @click="retryExam">重新考试</button>
        </div>
      </div>
    </div>

    <!-- 考试进行中 -->
    <div v-else class="qg-session-shell" :class="{ 'is-empty': !questions.length }">
      <section class="qg-session-paper">
        <div class="qg-session-head">
          <h1>{{ sheet.title || '模拟考试' }}</h1>
          <p>
            <span>题量：{{ questions.length }}</span>
            <span>满分：{{ totalScore }}</span>
          </p>
        </div>

        <div v-if="!questions.length" class="qg-session-empty">
          <strong>暂无可考试题目</strong>
          <span>请从题库生成页面选择一份已生成的题单后开始考试。</span>
          <button type="button" class="qg-empty-return" @click="backToGenerator">
            <ArrowLeft :size="16" aria-hidden="true" />
            返回题库生成
          </button>
        </div>

        <div v-else class="qg-session-question-list">
          <section v-for="group in questionGroups" :key="group.type" class="qg-session-question-group">
            <h2>{{ group.title }}</h2>

            <article
              v-for="item in group.items"
              :key="item.question.id || item.index"
              :id="`exam-question-${item.index}`"
              class="qg-session-question"
            >
              <p class="qg-session-stem">
                <span>{{ item.index + 1 }}. ({{ item.question.type || '题目' }}，{{ scoreForQuestion(item.question) }} 分)</span>
                {{ item.question.stem || item.question.title || item.question.question }}
              </p>

              <div v-if="hasChoiceOptions(item.question)" class="qg-session-options">
                <label v-for="option in item.question.options" :key="option">
                  <input
                    :type="isMultiQuestion(item.question) ? 'checkbox' : 'radio'"
                    :name="`exam-session-${item.index}`"
                    :checked="isChecked(item.index, option, item.question)"
                    @change="updateChoiceAnswer(item.index, option, item.question, $event)"
                  />
                  <span>{{ option }}</span>
                </label>
              </div>

              <textarea
                v-else
                v-model="answers[item.index]"
                rows="4"
                placeholder="在这里输入答案..."
              ></textarea>
            </article>
          </section>
        </div>
      </section>

      <aside v-if="questions.length" class="qg-session-answer-card">
        <div class="qg-session-card-head">
          <strong>答题卡</strong>
          <div>
            <span>{{ answeredCount }} / {{ questions.length }}</span>
          </div>
        </div>

        <div class="qg-session-answer-content">
          <div class="qg-session-progress">
            <div class="qg-progress-bar">
              <div class="qg-progress-fill" :style="{ width: (questions.length ? (answeredCount / questions.length * 100) : 0) + '%' }"></div>
            </div>
            <span class="qg-progress-text">完成 {{ answeredCount }}/{{ questions.length }} 题</span>
          </div>
          <div class="qg-session-answer-body">
            <section v-for="group in questionGroups" :key="group.type" class="qg-session-answer-group">
              <h3>{{ group.answerTitle }}</h3>
              <div class="qg-session-answer-grid">
                <button
                  v-for="item in group.items"
                  :key="item.index"
                  type="button"
                  :class="{ done: hasAnswer(item.index) }"
                  @click="scrollToQuestion(item.index)"
                >
                  {{ item.index + 1 }}
                </button>
              </div>
            </section>
          </div>

          <button type="button" class="qg-session-finish" @click="finishExam">结束考试</button>
        </div>
      </aside>
    </div>
  </main>
</template>

<script setup>
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { ArrowLeft, Clock3 } from 'lucide-vue-next'
import { requestQuestionGeneratorAiScore, saveQuestionGeneratorExamResult } from '../services/api'
import { elapsedSecondsSince, resolveExamQuestions } from '../utils/questionExamSession.js'

const sheet = ref({})
const sessionQuestions = ref([])
const questions = computed(() => resolveExamQuestions({ sheet: sheet.value, questions: sessionQuestions.value }))
const answers = ref([])
const elapsedSeconds = ref(0)
const examFinished = ref(false)
const examResult = ref({ score: 0, total_score: 0, correct_count: 0, question_count: 0, detail: [] })
const aiScoring = ref(false)
const aiScoreMessage = ref('')
let timer = 0
let examStartedAt = 0

const totalScore = computed(() => Number(questions.value.reduce((sum, q) => sum + scoreForQuestion(q), 0).toFixed(1)))
const answeredCount = computed(() => answers.value.filter(a => (Array.isArray(a) ? a.length : String(a || '').trim())).length)
const formattedElapsedTime = computed(() => {
  const mins = String(Math.floor(elapsedSeconds.value / 60)).padStart(2, '0')
  const secs = String(elapsedSeconds.value % 60).padStart(2, '0')
  return `${mins}:${secs}`
})

const accuracyPercent = computed(() => {
  if (!examResult.value.question_count) return 0
  return Math.round((examResult.value.correct_count / examResult.value.question_count) * 100)
})

const isPassed = computed(() => accuracyPercent.value >= 60)

const resultClass = computed(() => isPassed.value ? 'result-pass' : 'result-fail')

const wrongQuestions = computed(() => {
  return examResult.value.detail.filter(item => !item.correct)
})

function formatWrongQuestionNo(item) {
  const questionNo = Number(item.question_number ?? item.original_index)
  if (Number.isFinite(questionNo) && questionNo > 0) return questionNo
  const question = item.question || {}
  const candidate = Number(question.question_number ?? question.number ?? question.no ?? question.index)
  if (Number.isFinite(candidate) && candidate > 0) return candidate
  const idx = Number(question._idx)
  if (Number.isFinite(idx) && idx >= 0) return idx + 1
  return '-'
}

const questionGroups = computed(() => {
  const map = new Map()
  questions.value.forEach((question, index) => {
    const type = normalizeType(question.type)
    if (!map.has(type)) map.set(type, [])
    map.get(type).push({ question, index })
  })
  return Array.from(map.entries()).map(([type, items], groupIndex) => {
    const score = Number(items.reduce((sum, item) => sum + scoreForQuestion(item.question), 0).toFixed(1))
    return {
      type,
      items,
      title: `${chineseNumber(groupIndex + 1)}、${type}（共${items.length}题，${score}分）`,
      answerTitle: `${chineseNumber(groupIndex + 1)}、${type}（${score}分）`,
    }
  })
})

function loadSheet() {
  let examData = {}
  try {
    // 优先从新的 sessionStorage 格式读取
    examData = JSON.parse(sessionStorage.getItem('qgExamSessionData') || '{}')
    if (examData.sheet) {
      sheet.value = examData.sheet
    } else {
      // 兼容旧格式
      sheet.value = JSON.parse(sessionStorage.getItem('qgExamSessionSheet') || localStorage.getItem('qgExamSessionSheet') || '{}')
    }
  } catch {
    sheet.value = {}
  }
  sessionQuestions.value = Array.isArray(examData.questions) ? examData.questions : []
  answers.value = questions.value.map(q => (isMultiQuestion(q) ? [] : ''))
}

function stopTimer({ sync = false } = {}) {
  if (sync && examStartedAt) elapsedSeconds.value = elapsedSecondsSince(examStartedAt)
  if (timer) window.clearInterval(timer)
  timer = 0
}

function startTimer() {
  stopTimer()
  elapsedSeconds.value = 0
  examStartedAt = 0
  if (!questions.value.length) return
  examStartedAt = Date.now()
  timer = window.setInterval(() => {
    elapsedSeconds.value = elapsedSecondsSince(examStartedAt)
  }, 1000)
}

function normalizeType(type) {
  const text = String(type || '其它')
  if (text.includes('单') || /single/i.test(text)) return '单选题'
  if (text.includes('多') || /multi/i.test(text)) return '多选题'
  if (text.includes('判断') || /true|false|judge/i.test(text)) return '判断题'
  if (text.includes('填空') || /blank/i.test(text)) return '填空题'
  if (text.includes('简答') || /short/i.test(text)) return '简答题'
  if (text.includes('计算')) return '计算题'
  if (text.includes('综合')) return '综合应用题'
  return text
}

function chineseNumber(n) {
  return ['零', '一', '二', '三', '四', '五', '六', '七', '八', '九', '十'][n] || String(n)
}

function scoreForQuestion(question) {
  const explicit = Number(question?.score ?? question?.points)
  if (Number.isFinite(explicit) && explicit > 0) return Number(explicit.toFixed(1))
  const type = normalizeType(question?.type)
  if (type.includes('多选')) return 3
  if (type.includes('判断')) return 1
  if (type.includes('填空')) return 2
  if (type.includes('简答')) return 6
  if (type.includes('计算')) return 8
  if (type.includes('综合')) return 10
  return 2
}

function isMultiQuestion(question) {
  return normalizeType(question?.type).includes('多选')
}

function hasChoiceOptions(question) {
  const type = normalizeType(question?.type)
  const isChoiceType = type.includes('单选') || type.includes('多选') || type.includes('判断') || /single|multi|choice|judge|true|false/i.test(type)
  return isChoiceType && Array.isArray(question?.options) && question.options.length > 0
}

function optionKey(option) {
  return String(option).trim().match(/^[A-Z]/i)?.[0]?.toUpperCase() || String(option).trim()
}

function isChecked(index, option, question) {
  const key = optionKey(option)
  const answer = answers.value[index]
  return isMultiQuestion(question) ? Array.isArray(answer) && answer.includes(key) : answer === key
}

function updateChoiceAnswer(index, option, question, event) {
  const key = optionKey(option)
  if (isMultiQuestion(question)) {
    const next = Array.isArray(answers.value[index]) ? [...answers.value[index]] : []
    if (event.target.checked && !next.includes(key)) next.push(key)
    if (!event.target.checked) next.splice(next.indexOf(key), 1)
    answers.value[index] = next.sort()
    return
  }
  answers.value[index] = key
}

function hasAnswer(index) {
  const answer = answers.value[index]
  return Array.isArray(answer) ? answer.length > 0 : Boolean(String(answer || '').trim())
}

function scrollToQuestion(index) {
  document.getElementById(`exam-question-${index}`)?.scrollIntoView({ behavior: 'smooth', block: 'start' })
}

function normalizeAnswer(value) {
  if (Array.isArray(value)) return value.map(item => String(item).trim().toUpperCase()).sort().join('')
  return String(value || '').replace(/\s+/g, '').replace(/[，。；、,.]/g, '').toUpperCase()
}

function isCorrect(question, userAnswer) {
  const type = String(question.type || '')
  const standard = normalizeAnswer(question.answer)
  const user = normalizeAnswer(userAnswer)
  if (!user) return false
  if (type.includes('简答') || type.includes('计算') || type.includes('代码') || type.includes('操作')) {
    return user.length >= 4 && (standard.includes(user) || user.includes(standard.slice(0, Math.min(standard.length, 12))))
  }
  return user === standard || standard.startsWith(user) || user.startsWith(standard)
}

function finishExam() {
  if (!questions.value.length) return
  if (!confirm('确定要结束考试吗？')) return
  stopTimer({ sync: true })
  aiScoreMessage.value = ''
  aiScoring.value = false

  const detail = questions.value.map((question, index) => {
    const userAnswer = answers.value[index]
    const correct = isCorrect(question, userAnswer)
    const questionScore = scoreForQuestion(question)
    return {
      question,
      question_id: question.id || question._id || `Q${index + 1}`,
      question_number: index + 1,
      original_index: index + 1,
      user_answer: userAnswer,
      correct,
      score: correct ? questionScore : 0,
      full_score: questionScore,
      answer: question.answer,
      analysis: question.analysis,
      type: question.type,
      stem: question.stem,
    }
  })

  const correctCount = detail.filter(item => item.correct).length
  const score = Number(detail.reduce((sum, item) => sum + Number(item.score || 0), 0).toFixed(1))
  const totalExamScore = Number(detail.reduce((sum, item) => sum + Number(item.full_score || 0), 0).toFixed(1))

  examResult.value = {
    sheet_id: sheet.value.id,
    title: sheet.value.title,
    score,
    total_score: totalExamScore,
    correct_count: correctCount,
    question_count: questions.value.length,
    duration_seconds: elapsedSeconds.value,
    answers: answers.value,
    detail,
  }

  // 保存到历史记录
  saveToHistory(examResult.value)
  persistExamResult(examResult.value)

  examFinished.value = true
}

function saveToHistory(result) {
  if (!result?.question_count) return
  try {
    let quizHistory = []
    try { quizHistory = JSON.parse(localStorage.getItem('quizHistory') || '[]') } catch {}

    const weakTopics = []
    const kpStats = new Map()
    result.detail.forEach((item) => {
      const kp = item.question?.knowledge_point || item.type || '未知'
      if (!kpStats.has(kp)) kpStats.set(kp, { name: kp, total: 0, wrong: 0 })
      const stat = kpStats.get(kp)
      stat.total++
      if (!item.correct) stat.wrong++
    })
    kpStats.forEach((stat) => {
      if (stat.wrong > 0) weakTopics.push(stat.name)
    })

    const examRecord = {
      score: result.score,
      total: result.total_score,
      correct_count: result.correct_count,
      question_count: result.question_count,
      duration_seconds: result.duration_seconds,
      weakTopics,
      title: result.title || '题库练习',
      sheet_id: result.sheet_id,
      timestamp: new Date().toISOString(),
      time: new Date().toLocaleString(),
      source: 'exam-session',
    }

    quizHistory.unshift(examRecord)
    if (quizHistory.length > 50) quizHistory = quizHistory.slice(0, 50)
    localStorage.setItem('quizHistory', JSON.stringify(quizHistory))

  } catch {}
}

async function persistExamResult(result) {
  if (!result?.question_count) return
  try {
    const saved = await saveQuestionGeneratorExamResult(result)
    examResult.value = { ...examResult.value, id: saved?.id || examResult.value.id }
  } catch (error) {
    console.warn('考试结果暂未同步到学习画像证据库。', error)
  }
}

async function requestAiRescore() {
  if (!examResult.value?.detail?.length || aiScoring.value) return
  aiScoring.value = true
  aiScoreMessage.value = ''
  try {
    const result = await requestQuestionGeneratorAiScore({
      sheet_id: examResult.value.sheet_id,
      title: examResult.value.title,
      score: examResult.value.score,
      total_score: examResult.value.total_score,
      detail: examResult.value.detail,
    })
    examResult.value = {
      ...examResult.value,
      score: result.score,
      total_score: result.total_score || examResult.value.total_score,
      correct_count: result.correct_count,
      question_count: result.question_count || examResult.value.question_count,
      detail: result.detail || examResult.value.detail,
      aiSummary: result.aiSummary,
      aiScoreSource: result.source,
    }
    aiScoreMessage.value = result.aiSummary || 'AI 复核评分已完成，当前分数已更新。'
  } catch (error) {
    aiScoreMessage.value = error.response?.data?.msg || error.response?.data?.message || error.message || 'AI 复核评分失败，请稍后再试。'
  } finally {
    aiScoring.value = false
  }
}

function backToGenerator() {
  // 如果是从新标签页打开的，关闭当前标签页
  if (window.opener) {
    window.close()
  } else {
    // 否则跳转回题库页面
    window.location.href = '/question-generator'
  }
}

function exitExam() {
  if (questions.value.length && !examFinished.value) {
    const confirmed = window.confirm('退出后本次作答不会保存，确定返回题库吗？')
    if (!confirmed) return
  }
  stopTimer({ sync: true })
  backToGenerator()
}

function retryExam() {
  examFinished.value = false
  examResult.value = { score: 0, total_score: 0, correct_count: 0, question_count: 0, detail: [] }
  aiScoreMessage.value = ''
  aiScoring.value = false
  answers.value = questions.value.map(q => (isMultiQuestion(q) ? [] : ''))
  startTimer()
}

onMounted(() => {
  loadSheet()
  startTimer()
})

onUnmounted(() => {
  stopTimer()
})
</script>

<style scoped>
.qg-exam-session {
  min-height: 100vh;
  background: #f3f6f8;
  color: #122b3a;
  font-family: "Microsoft YaHei", "PingFang SC", Arial, sans-serif;
}

.qg-session-topbar {
  min-height: 56px;
  padding: 0 max(24px, calc((100vw - 1450px) / 2));
  background: linear-gradient(135deg, #2f5d8a 0%, #3b7dd8 100%);
  color: var(--surface, rgba(255, 255, 255, 0.94));
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: 18px;
  font-weight: 700;
  gap: 20px;
  box-sizing: border-box;
  box-shadow: 0 2px 8px rgba(47, 93, 138, 0.2);
}

.qg-session-topbar-actions {
  display: flex;
  align-items: center;
  gap: 12px;
}

.qg-session-timer {
  display: flex;
  align-items: center;
  gap: 6px;
  background: rgba(255,255,255,0.15);
  padding: 4px 14px;
  border-radius: 20px;
  font-size: 15px;
  font-weight: 600;
  font-variant-numeric: tabular-nums;
}

.qg-session-exit,
.qg-empty-return {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 7px;
  border: 1px solid rgba(255, 255, 255, 0.32);
  border-radius: 7px;
  background: rgba(255, 255, 255, 0.14);
  color: #ffffff;
  font: inherit;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
}

.qg-session-exit {
  min-height: 36px;
  padding: 0 14px;
}

.qg-session-exit:hover {
  background: rgba(255, 255, 255, 0.24);
}

.qg-session-shell {
  width: min(1450px, calc(100vw - 64px));
  margin: 32px auto;
  display: grid;
  grid-template-columns: minmax(0, 1fr) 300px;
  gap: 24px;
  align-items: start;
}

.qg-session-paper,
.qg-session-answer-card {
  background: var(--surface, rgba(255, 255, 255, 0.94));
  border-radius: 12px;
  border: 1px solid var(--border, rgba(31, 166, 112, 0.1));
  box-shadow: 0 2px 12px rgba(0,0,0,0.04);
}

.qg-session-head {
  padding: 32px 40px 24px;
  border-bottom: 1px solid #edf1f4;
}

.qg-session-head h1 {
  margin: 0 0 12px;
  font-size: 22px;
  color: #1a2b3d;
}

.qg-session-head p {
  margin: 0;
  display: flex;
  gap: 24px;
  color: #8a96a8;
  font-size: 14px;
}

.qg-session-question-list {
  padding: 32px 40px 60px;
}

.qg-session-question-group h2 {
  margin: 0 0 24px;
  font-size: 17px;
  color: #2f5d8a;
  padding-bottom: 8px;
  border-bottom: 2px solid #e8f0f8;
}

.qg-session-question {
  padding: 16px 0 28px;
}

.qg-session-question.weak-point {
  background: linear-gradient(135deg, var(--surface, rgba(255, 255, 255, 0.94))7ed 0%, #fef3c7 100%);
  margin: 0 -16px;
  padding: 16px 16px 28px;
  border-radius: 8px;
  border-left: 3px solid #f59e0b;
}

.qg-weak-badge {
  display: inline-block;
  background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%);
  color: var(--surface, rgba(255, 255, 255, 0.94));
  font-size: 11px;
  font-weight: 600;
  padding: 2px 8px;
  border-radius: 10px;
  margin-left: 8px;
  vertical-align: middle;
}

.qg-session-stem {
  margin: 0 0 14px;
  font-size: 15px;
  line-height: 1.8;
  color: #1a2b3d;
}

.qg-session-stem span {
  font-weight: 700;
  color: #2f5d8a;
}

.qg-session-options {
  display: grid;
  gap: 12px;
  color: #26384d;
  font-size: 15px;
}

.qg-session-options label {
  display: flex;
  gap: 10px;
  align-items: flex-start;
  padding: 10px 14px;
  border-radius: 8px;
  border: 1px solid var(--border, rgba(31, 166, 112, 0.1));
  cursor: pointer;
  transition: all 0.15s;
}

.qg-session-options label:hover {
  background: #f0f5fa;
  border-color: #c5d5e5;
}

.qg-session-options label:has(input:checked) {
  background: #e8f4ff;
  border-color: #3b7dd8;
}

.qg-session-question textarea {
  width: 100%;
  border: 1px solid #dce5ea;
  border-radius: 8px;
  padding: 12px;
  font-size: 14px;
  resize: vertical;
  transition: border-color 0.15s;
}

.qg-session-question textarea:focus {
  outline: none;
  border-color: #3b7dd8;
  box-shadow: 0 0 0 3px rgba(59, 125, 216, 0.1);
}

.qg-session-answer-card {
  position: sticky;
  top: 24px;
  padding: 24px;
  max-height: calc(100vh - 100px);
  overflow-y: auto;
  background: var(--surface, rgba(255, 255, 255, 0.94));
  border-radius: 12px;
  border: 1px solid var(--border, rgba(31, 166, 112, 0.1));
  box-shadow: 0 4px 16px rgba(0,0,0,0.06);
}

.qg-session-card-head {
  display: flex;
  justify-content: space-between;
  gap: 8px;
  align-items: center;
  margin-bottom: 20px;
  padding-bottom: 16px;
  border-bottom: 1px solid #edf1f4;
}

.qg-session-card-head strong {
  font-size: 16px;
  color: #1a2b3d;
  font-weight: 600;
}

.qg-session-card-head span {
  font-size: 14px;
  color: #3b7dd8;
  font-weight: 500;
}

.qg-session-answer-group {
  margin-bottom: 20px;
}

.qg-session-answer-group h3 {
  margin: 0 0 10px;
  color: #2f3542;
  font-size: 13px;
  font-weight: 500;
}

.qg-session-answer-grid {
  display: grid;
  grid-template-columns: repeat(5, 42px);
  gap: 10px;
}

.qg-session-answer-grid button {
  width: 42px;
  height: 42px;
  border: 1px solid rgba(16, 185, 129, 0.32) !important;
  color: #047857 !important;
  background: #ecfdf5 !important;
  border-radius: 50%;
  cursor: pointer;
  font-size: 14px;
  font-weight: 500;
  transition: all 0.2s;
}

.qg-session-answer-grid button:hover {
  border-color: #10b981 !important;
  color: #047857 !important;
  transform: translateY(-1px);
  box-shadow: 0 2px 8px rgba(16, 185, 129, 0.18);
}

.qg-session-answer-grid button.done {
  background: linear-gradient(135deg, #2fd08a 0%, #0f9f6e 100%) !important;
  color: var(--surface, rgba(255, 255, 255, 0.94)) !important;
  border-color: #10b981 !important;
  font-weight: 800;
  box-shadow: 0 8px 18px rgba(16, 185, 129, 0.28);
}

.qg-session-finish {
  width: 100%;
  margin-top: 20px;
  padding: 14px;
  background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%);
  color: var(--surface, rgba(255, 255, 255, 0.94));
  border: none;
  border-radius: 10px;
  font-size: 15px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
  box-shadow: 0 4px 12px rgba(239, 68, 68, 0.3);
}

.qg-session-finish:hover {
  transform: translateY(-1px);
  box-shadow: 0 6px 16px rgba(239, 68, 68, 0.4);
}

.qg-session-progress {
  margin-bottom: 20px;
}

.qg-progress-bar {
  height: 8px;
  background: var(--border, rgba(31, 166, 112, 0.1));
  border-radius: 4px;
  overflow: hidden;
  margin-bottom: 8px;
}

.qg-progress-fill {
  height: 100%;
  background: linear-gradient(90deg, #3b7dd8 0%, #22c55e 100%);
  border-radius: 4px;
  transition: width 0.3s ease;
}

.qg-progress-text {
  font-size: 13px;
  color: #8a96a8;
  text-align: center;
  display: block;
}

.qg-session-empty {
  min-height: 360px;
  display: grid;
  place-content: center;
  text-align: center;
  color: #66798b;
  gap: 10px;
}

.qg-session-shell.is-empty {
  max-width: 900px;
  grid-template-columns: minmax(0, 1fr);
}

.qg-empty-return {
  min-height: 42px;
  margin: 16px auto 0;
  padding: 0 18px;
  border-color: #2f5d8a;
  background: #2f5d8a;
}

.qg-empty-return:hover {
  background: #244c73;
}

/* 考试结果样式 */
.qg-session-result {
  width: min(1120px, calc(100vw - 48px));
  max-width: none;
  margin: 48px auto;
  padding: 0;
}

.qg-result-card {
  background: var(--surface, rgba(255, 255, 255, 0.94));
  border-radius: 16px;
  padding: 48px 56px;
  text-align: center;
  box-shadow: 0 4px 24px rgba(0,0,0,0.06);
}

.qg-result-icon {
  width: 80px;
  height: 80px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  margin: 0 auto 24px;
}

.qg-result-icon.result-pass {
  background: #e6f7ed;
  color: #22c55e;
}

.qg-result-icon.result-fail {
  background: #fef2f2;
  color: #ef4444;
}

.qg-result-card h2 {
  margin: 0 0 20px;
  font-size: 24px;
  color: #1a2b3d;
}

.qg-result-score {
  margin-bottom: 32px;
}

.qg-score-num {
  font-size: 56px;
  font-weight: 700;
  color: #2f5d8a;
}

.qg-score-total {
  font-size: 18px;
  color: #8a96a8;
  margin-left: 8px;
}

.qg-result-stats {
  display: flex;
  justify-content: center;
  gap: 40px;
  margin-bottom: 36px;
  padding: 24px 0;
  border-top: 1px solid #edf1f4;
  border-bottom: 1px solid #edf1f4;
}

.qg-stat-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.qg-stat-item strong {
  font-size: 24px;
  color: #1a2b3d;
}

.qg-stat-item span {
  font-size: 13px;
  color: #8a96a8;
}

.qg-ai-rescore-panel {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 20px;
  margin: -12px 0 34px;
  padding: 18px 20px;
  border: 1px solid rgba(59, 125, 216, 0.22);
  border-radius: 14px;
  background: linear-gradient(135deg, #f4f9ff 0%, #eefdf7 100%);
  text-align: left;
}

.qg-ai-rescore-panel.active {
  border-color: rgba(16, 185, 129, 0.38);
  background: linear-gradient(135deg, #ecfdf5 0%, #eff6ff 100%);
}

.qg-ai-rescore-panel strong {
  display: block;
  margin-bottom: 5px;
  color: #173f36;
  font-size: 16px;
  font-weight: 800;
}

.qg-ai-rescore-panel span {
  display: block;
  color: #5b7a94;
  font-size: 13px;
  line-height: 1.55;
}

.qg-btn-ai {
  flex: 0 0 auto;
  padding: 12px 22px;
  border: none;
  border-radius: 999px;
  background: linear-gradient(135deg, #58d89c 0%, #22c55e 100%);
  color: var(--surface, rgba(255, 255, 255, 0.94));
  box-shadow: 0 10px 22px rgba(20, 184, 166, 0.22);
  cursor: pointer;
  font-size: 14px;
  font-weight: 800;
}

.qg-btn-ai:disabled {
  cursor: not-allowed;
  opacity: 0.58;
  box-shadow: none;
}

.qg-result-wrong {
  text-align: left;
  margin-bottom: 32px;
}

.qg-result-wrong h3 {
  font-size: 16px;
  color: #1a2b3d;
  margin: 0 0 16px;
}

.qg-wrong-item {
  padding: 18px 20px;
  background: #fafbfc;
  border-radius: 8px;
  margin-bottom: 14px;
  border-left: 3px solid #ef4444;
}

.qg-wrong-stem {
  margin: 0 0 8px;
  font-size: 15px;
  color: #1a2b3d;
  line-height: 1.6;
}

.qg-wrong-answer {
  margin: 0 0 4px;
  font-size: 13px;
  color: #5b7a94;
}

.qg-wrong-answer .wrong {
  color: #ef4444;
  font-weight: 600;
}

.qg-wrong-answer .correct {
  color: #22c55e;
  font-weight: 600;
}

.qg-wrong-analysis {
  margin: 6px 0 0;
  font-size: 13px;
  color: #8a96a8;
  font-style: italic;
  line-height: 1.65;
}

.qg-ai-comment {
  margin: 8px 0 0;
  padding: 9px 11px;
  border-radius: 8px;
  background: #ecfdf5;
  color: #047857;
  font-size: 13px;
  line-height: 1.55;
}

.qg-result-actions {
  display: flex;
  gap: 16px;
  justify-content: center;
}

.qg-btn-primary {
  padding: 12px 32px;
  background: linear-gradient(135deg, #3b7dd8 0%, #2f5d8a 100%);
  color: var(--surface, rgba(255, 255, 255, 0.94));
  border: none;
  border-radius: 8px;
  font-size: 15px;
  font-weight: 600;
  cursor: pointer;
  transition: opacity 0.15s;
}

.qg-btn-primary:hover {
  opacity: 0.9;
}

.qg-btn-secondary {
  padding: 12px 32px;
  background: var(--surface, rgba(255, 255, 255, 0.94));
  color: #3b7dd8;
  border: 1px solid #3b7dd8;
  border-radius: 8px;
  font-size: 15px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.15s;
}

.qg-btn-secondary:hover {
  background: #f0f5fa;
}

@media (max-width: 900px) {
  .qg-session-topbar {
    min-height: 64px;
    padding: 10px 16px;
  }

  .qg-session-topbar > strong {
    font-size: 16px;
  }

  .qg-session-topbar-actions {
    gap: 8px;
  }

  .qg-session-timer {
    padding: 4px 10px;
    font-size: 14px;
  }

  .qg-session-exit {
    padding: 0 10px;
  }

  .qg-session-shell {
    width: calc(100vw - 24px);
    margin: 16px auto 28px;
    grid-template-columns: minmax(0, 1fr);
    gap: 14px;
  }

  .qg-session-head {
    padding: 22px 20px 18px;
  }

  .qg-session-head h1 {
    font-size: 19px;
  }

  .qg-session-question-list {
    padding: 22px 20px 36px;
  }

  .qg-session-answer-card {
    position: static;
    max-height: none;
    padding: 20px;
  }

  .qg-session-answer-grid {
    grid-template-columns: repeat(auto-fill, 42px);
  }

  .qg-session-empty {
    min-height: 300px;
    padding: 28px 20px;
  }

  .qg-session-result {
    width: calc(100vw - 24px);
    margin: 20px auto;
  }

  .qg-result-card {
    padding: 28px 20px;
  }

  .qg-result-stats {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 22px 12px;
  }

  .qg-ai-rescore-panel {
    align-items: stretch;
    flex-direction: column;
  }

  .qg-btn-ai {
    width: 100%;
  }
}

@media (max-width: 480px) {
  .qg-session-exit span {
    display: none;
  }

  .qg-session-exit {
    width: 36px;
    padding: 0;
  }

  .qg-session-head p,
  .qg-result-actions {
    flex-direction: column;
    gap: 10px;
  }

  .qg-btn-primary,
  .qg-btn-secondary {
    width: 100%;
  }
}
</style>

<!-- 非 scoped 样式：允许考试页面滚动 -->
<style>
body:has(.qg-exam-session) {
  overflow: auto !important;
  height: auto !important;
}
</style>
