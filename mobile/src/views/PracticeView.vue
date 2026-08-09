<template>
  <AppShell>
    <AsyncState :loading="loading" :error="error" :empty="!sheet" empty-text="未找到该题单" @retry="load">
      <header class="page-head practice-head">
        <span class="eyebrow"><BookOpenCheck :size="15" />PRACTICE</span>
        <h1>{{ sheet?.title || '个性化练习' }}</h1>
        <p>共 {{ questions.length }} 题，作答后可请求 AI 评分。</p>
        <div class="question-progress">
          <span>第 {{ currentIndex + 1 }} / {{ questions.length }} 题</span>
          <div><i :style="{ width: `${progress}%` }"></i></div>
          <b>{{ progress }}%</b>
        </div>
      </header>

      <form v-if="currentQuestion" class="question-list" @submit.prevent="nextOrSubmit">
        <article>
          <span>Q{{ currentIndex + 1 }}</span>
          <h2>{{ currentQuestion.question || currentQuestion.title || currentQuestion.stem }}</h2>
          <div v-if="currentQuestion.options" class="option-list">
            <label
              v-for="(option, key) in normalizedOptions(currentQuestion.options)"
              :key="key"
              :class="{ selected: answers[currentIndex] === key }"
            >
              <input v-model="answers[currentIndex]" type="radio" :value="key" />
              <span>{{ key }}. {{ option }}</span>
            </label>
          </div>
          <textarea v-else v-model.trim="answers[currentIndex]" rows="4" placeholder="输入答案"></textarea>
        </article>
        <p v-if="error" class="form-error">{{ error }}</p>
        <div class="question-actions">
          <button class="secondary-btn" type="button" :disabled="currentIndex === 0 || saving" @click="currentIndex--">
            <ChevronLeft :size="18" />上一题
          </button>
          <button class="primary-btn" :disabled="saving">
            <span v-if="saving" class="spinner light"></span>
            <CheckCircle2 v-else-if="isLast" :size="18" />
            <ChevronRight v-else :size="18" />
            {{ saving ? '正在评分' : isLast ? '提交并评分' : '下一题' }}
          </button>
        </div>
      </form>

      <section v-if="result" class="result-band">
        <strong>{{ result.score ?? result.scores?.score ?? '--' }}</strong>
        <div><h2>评分完成</h2><p>{{ result.aiSummary || result.summary || result.comment || '结果已保存到学习证据。' }}</p></div>
      </section>
    </AsyncState>
  </AppShell>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute } from 'vue-router'
import { BookOpenCheck, CheckCircle2, ChevronLeft, ChevronRight } from 'lucide-vue-next'
import AppShell from '../components/AppShell.vue'
import AsyncState from '../components/AsyncState.vue'
import { getQuestionHistory, saveExamResult, scoreExam } from '../services/api.js'

const route = useRoute()
const sheet = ref(null)
const questions = ref([])
const answers = reactive({})
const currentIndex = ref(0)
const loading = ref(true)
const error = ref('')
const saving = ref(false)
const result = ref(null)
const currentQuestion = computed(() => questions.value[currentIndex.value])
const isLast = computed(() => currentIndex.value === questions.value.length - 1)
const progress = computed(() => questions.value.length ? Math.round(((currentIndex.value + 1) / questions.value.length) * 100) : 0)

async function load() {
  loading.value = true
  error.value = ''
  try {
    const body = await getQuestionHistory()
    const sheets = body.question_sheets || body.questionSheets || body.data?.question_sheets || []
    sheet.value = sheets.find(x => String(x.id || x.sheetId) === String(route.params.sheetId)) || null
    questions.value = sheet.value?.questions || sheet.value?.items || sheet.value?.question_bank?.questions || []
    currentIndex.value = 0
  } catch (e) {
    error.value = e.message
  } finally {
    loading.value = false
  }
}

function normalizedOptions(options) {
  if (Array.isArray(options)) return Object.fromEntries(options.map((x, i) => [String.fromCharCode(65 + i), typeof x === 'string' ? x : x.text]))
  return options || {}
}

function nextOrSubmit() {
  if (!isLast.value) {
    currentIndex.value++
    return
  }
  submit()
}

async function submit() {
  saving.value = true
  error.value = ''
  try {
    const detail = questions.value.map((q, i) => ({ question: q, user_answer: answers[i] || '', answer: q.answer, full_score: q.score || q.points || 10 }))
    const sheetId = sheet.value.id || sheet.value.sheetId
    const scored = await scoreExam({
      sheet_id: sheetId,
      title: sheet.value.title || '个性化练习',
      total_score: detail.reduce((total, item) => total + Number(item.full_score || 0), 0),
      detail,
    })
    result.value = scored.data || scored
    await saveExamResult({
      sheet_id: sheetId,
      title: sheet.value.title || '个性化练习',
      answers: { ...answers },
      score: result.value.score ?? result.value.scores?.score ?? 0,
      total_score: result.value.total_score ?? result.value.scores?.totalScore ?? 0,
      correct_count: result.value.correct_count ?? result.value.scores?.correctCount ?? 0,
      question_count: result.value.question_count ?? result.value.scores?.questionCount ?? questions.value.length,
      detail: result.value.detail || detail,
      ai_score: result.value,
    })
  } catch (e) {
    error.value = e.message
  } finally {
    saving.value = false
  }
}

onMounted(load)
</script>

<style scoped>
.practice-head{padding-bottom:14px}.question-progress{display:grid;grid-template-columns:auto minmax(80px,1fr) auto;align-items:center;gap:9px;margin-top:14px;color:#66766d;font-size:10px}.question-progress>div{height:6px;border-radius:3px;background:#dce5e0;overflow:hidden}.question-progress i{height:100%;display:block;background:#176f4b;transition:width .2s}.question-progress b{color:#176f4b}.question-list{display:grid;gap:12px}.question-list article{min-height:340px;padding:20px 17px;border:1px solid #dce5e0;border-top:3px solid #176f4b;border-radius:7px;background:white}.question-list article>span{color:#176f4b;font-size:9px;font-weight:850}.question-list h2{margin:10px 0 18px;font-size:15px;line-height:1.65}.option-list{display:grid;gap:8px}.option-list label{min-height:48px;display:flex;align-items:center;gap:9px;padding:9px 11px;border:1px solid #dce5e0;border-radius:6px;color:#465a50;font-size:11px;transition:.15s}.option-list label.selected{border-color:#176f4b;background:#edf5f1;color:#176f4b}.question-list textarea{width:100%;padding:12px;border:1px solid #cfdad4;border-radius:6px}.question-actions{display:grid;grid-template-columns:1fr 1.35fr;gap:8px}.question-actions button{min-height:48px}.form-error{padding:10px;background:#fff0ec;color:#a04435;font-size:11px}.spinner.light{border-color:rgba(255,255,255,.45);border-top-color:white}.result-band{display:grid;grid-template-columns:70px minmax(0,1fr);align-items:center;gap:14px;margin-top:18px;padding:18px;border-radius:7px;background:#176f4b;color:white}.result-band>strong{font-size:36px}.result-band h2{margin:0;font-size:15px}.result-band p{margin:5px 0 0;color:#dbeae3;font-size:10px}
</style>
