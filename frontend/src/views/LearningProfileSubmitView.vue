<template>
  <div class="questionnaire-page">
    <Transition name="toast">
      <div v-if="toastMsg" class="toast-bar">{{ toastMsg }}</div>
    </Transition>

    <header class="questionnaire-header">
      <div>
        <h1>嵌入式大学生学习画像量表问卷</h1>
      </div>
      <button class="ghost-btn" type="button" @click="router.push('/learning-profile')">返回学习画像</button>
    </header>

    <main class="questionnaire-shell">
      <aside class="section-rail" aria-label="问卷部分">
        <button
          v-for="(section, index) in questionnaireSections"
          :key="section.key"
          :class="['rail-item', { active: index === currentIndex, complete: getSectionComplete(section) }]"
          type="button"
          @click="currentIndex = index"
        >
          <span class="rail-index">{{ index + 1 }}</span>
          <span class="rail-label">{{ section.title }}</span>
        </button>
      </aside>

      <section v-if="!resultVisible" class="questionnaire-card">
        <div class="card-head">
          <div>
            <p class="section-kicker">第 {{ currentIndex + 1 }} / {{ questionnaireSections.length }} 部分</p>
            <h2>{{ currentSection.title }}</h2>
          </div>
        </div>

        <p v-if="currentSection.hint" class="section-hint">{{ currentSection.hint }}</p>

        <div v-if="currentSection.type === 'basic'" class="question-list">
          <div v-for="question in currentSection.questions" :key="question.key" class="choice-block">
            <p class="question-title">{{ question.text }}</p>
            <div class="choice-grid">
              <label v-for="option in question.options" :key="option.value" class="choice-item">
                <input
                  v-if="question.mode === 'multiple'"
                  v-model="answers.basic[question.key]"
                  type="checkbox"
                  :value="option.value"
                />
                <input
                  v-else
                  v-model="answers.basic[question.key]"
                  type="radio"
                  :name="question.key"
                  :value="option.value"
                />
                <span>{{ option.label }}</span>
              </label>
            </div>
          </div>
        </div>

        <div v-else-if="currentSection.type === 'rating'" class="rating-table-wrap">
          <table class="rating-table">
            <thead>
              <tr>
                <th>题目</th>
                <th v-for="n in 5" :key="n">{{ n }}</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="item in currentSection.items" :key="item.key">
                <td>{{ item.text }}</td>
                <td v-for="n in 5" :key="n">
                  <label class="rating-cell">
                    <input
                      v-model="answers.ratings[currentSection.key][item.key]"
                      type="radio"
                      :name="item.key"
                      :value="n"
                    />
                    <span></span>
                  </label>
                </td>
              </tr>
            </tbody>
          </table>
        </div>

        <div v-else-if="currentSection.type === 'difficulties'" class="question-list">
          <div v-for="question in currentSection.questions" :key="question.key" class="choice-block">
            <p class="question-title">{{ question.text }}</p>
            <div class="choice-grid">
              <label v-for="option in question.options" :key="option.value" class="choice-item">
                <input v-model="answers.difficulties[question.key]" type="checkbox" :value="option.value" />
                <span>{{ option.label }}</span>
              </label>
            </div>
            <input
              v-if="question.extraKey"
              v-model="answers.difficulties[question.extraKey]"
              class="text-input"
              type="text"
              placeholder="其他内容"
            />
          </div>
        </div>

        <div v-else class="open-list">
          <label v-for="question in currentSection.questions" :key="question.key" class="open-item">
            <span>{{ question.text }}</span>
            <textarea v-model="answers.open[question.key]" rows="4" placeholder="答："></textarea>
          </label>
        </div>

        <footer class="step-actions">
          <button class="ghost-btn" type="button" :disabled="currentIndex === 0" @click="goPrevious">上一部分</button>
          <button v-if="!isLastSection" class="primary-btn" type="button" @click="goNext">下一部分</button>
          <button v-else class="primary-btn" type="button" @click="submitQuestionnaire">保存并返回采集进度</button>
        </footer>
      </section>

      <section v-else class="result-card">
        <div class="card-head">
          <div>
            <p class="section-kicker">问卷结果</p>
            <h2>学习画像量表已保存</h2>
          </div>
          <span class="status-pill">{{ completedSections.length }} / {{ questionnaireSections.length }} 部分已填写</span>
        </div>

        <div class="result-grid">
          <div v-for="section in questionnaireSections" :key="section.key" class="result-item">
            <span class="result-title">{{ section.title }}</span>
            <span :class="['result-status', sectionStatuses[section.key].completed ? 'ok' : 'missing']">
              {{ sectionStatuses[section.key].completed ? '已保存' : sectionStatuses[section.key].message }}
            </span>
          </div>
        </div>

        <div class="score-summary">
          <h3>能力维度均分</h3>
          <div class="score-row" v-for="item in scoreSummary" :key="item.key">
            <span>{{ item.title }}</span>
            <strong>{{ item.score ? `${item.score}/5` : '暂时缺失' }}</strong>
          </div>
        </div>

        <div class="step-actions">
          <button class="ghost-btn" type="button" @click="resultVisible = false">继续修改</button>
          <button class="primary-btn" type="button" @click="router.push('/learning-profile')">返回画像页</button>
        </div>
      </section>
    </main>
  </div>
</template>

<script setup>
import { computed, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { saveLearningProfileQuestionnaire } from '../services/api.js'

const LS_KEY = 'learningProfileData'
const MISSING_MESSAGE = '暂时缺失该部分的数据'
const router = useRouter()

function returnToCollectProgress() {
  router.push({ path: '/learning-profile', query: { collect: 'progress' } })
}

const ratingGuide = '请根据自己的真实情况打分：1 分 = 完全不了解，2 分 = 了解较少，3 分 = 基本了解，4 分 = 掌握较好，5 分 = 非常熟练。'

const questionnaireSections = [
  {
    key: 'basic',
    title: '一、基本信息',
    type: 'basic',
    questions: [
      {
        key: 'grade',
        text: '你的年级是？',
        options: ['大一', '大二', '大三', '大四', '研究生'].map((label, index) => ({ value: String.fromCharCode(65 + index), label: `${String.fromCharCode(65 + index)}. ${label}` })),
      },
      {
        key: 'major',
        text: '你的专业方向是？',
        options: ['电子信息类', '计算机类', '自动化类', '物联网工程', '其他'].map((label, index) => ({ value: String.fromCharCode(65 + index), label: `${String.fromCharCode(65 + index)}. ${label}` })),
      },
      {
        key: 'learningTime',
        text: '你目前接触嵌入式学习的时间是？',
        options: ['还没有系统学习', '1 个月以内', '1～6 个月', '6～12 个月', '1 年以上'].map((label, index) => ({ value: String.fromCharCode(65 + index), label: `${String.fromCharCode(65 + index)}. ${label}` })),
      },
      {
        key: 'platforms',
        mode: 'multiple',
        text: '你主要使用过哪些开发板或平台？可多选：',
        options: ['51 单片机', 'STM32', 'Arduino', 'ESP32', '树莓派', 'RDK / Jetson 等 AI 开发板', '暂时没有使用过'].map((label, index) => ({ value: String.fromCharCode(65 + index), label: `${String.fromCharCode(65 + index)}. ${label}` })),
      },
    ],
  },
  {
    key: 'embeddedBasics',
    title: '二、嵌入式基础知识掌握情况',
    type: 'rating',
    hint: ratingGuide,
    items: [
      '我了解嵌入式系统的基本概念和应用场景',
      '我理解单片机、微处理器、开发板之间的区别',
      '我掌握 C 语言的基本语法和指针使用',
      '我能理解 GPIO、定时器、中断等基础外设',
      '我了解串口通信、I2C、SPI 等通信方式',
      '我能看懂简单的电路原理图',
      '我能根据实验要求连接基础硬件模块',
    ].map((text, index) => ({ key: `embeddedBasics_${index}`, text })),
  },
  {
    key: 'programmingDebug',
    title: '三、编程与调试能力',
    type: 'rating',
    items: [
      '我能独立编写简单的嵌入式程序',
      '我能根据报错信息定位代码问题',
      '我会使用 Keil、STM32CubeIDE、VS Code 等开发工具',
      '我能使用串口打印、断点调试等方式排查问题',
      '我能读懂示例工程并进行修改',
      '我能将多个功能模块组合成一个完整程序',
    ].map((text, index) => ({ key: `programmingDebug_${index}`, text })),
  },
  {
    key: 'experimentPractice',
    title: '四、实验与动手能力',
    type: 'rating',
    items: [
      '我能独立完成基础实验，如 LED、按键、蜂鸣器实验',
      '我能完成传感器数据采集实验',
      '我能完成串口通信或模块通信实验',
      '我能在实验失败时主动分析原因',
      '我能记录实验过程、问题和解决方法',
      '我能把实验结果整理成报告或项目展示',
    ].map((text, index) => ({ key: `experimentPractice_${index}`, text })),
  },
  {
    key: 'projectPractice',
    title: '五、项目实践能力',
    type: 'rating',
    items: [
      '我参与过嵌入式相关课程设计或比赛项目',
      '我能根据需求设计简单的嵌入式系统方案',
      '我能进行模块划分，如输入、处理、输出、通信等',
      '我能将硬件、软件和传感器模块结合起来完成任务',
      '我了解项目开发的基本流程，如需求分析、设计、实现、测试',
      '我能对项目进行功能测试和问题修复',
    ].map((text, index) => ({ key: `projectPractice_${index}`, text })),
  },
  {
    key: 'learningHabits',
    title: '六、学习习惯与学习投入',
    type: 'rating',
    items: [
      '我会定期复习嵌入式相关知识',
      '我会主动查阅资料解决学习中的问题',
      '我会整理错题、错误代码或实验问题',
      '我每周愿意投入时间进行嵌入式学习和实验',
      '我遇到困难时不会轻易放弃',
      '我愿意通过刷题、实验、项目等方式提升能力',
    ].map((text, index) => ({ key: `learningHabits_${index}`, text })),
  },
  {
    key: 'innovationEngineering',
    title: '七、创新能力与工程意识',
    type: 'rating',
    items: [
      '我能提出嵌入式项目的创新想法',
      '我会考虑项目的稳定性、可靠性和可扩展性',
      '我了解低功耗、实时性、资源限制等嵌入式特点',
      '我愿意尝试 AI、物联网、视觉识别等嵌入式拓展方向',
      '我能从实际生活中发现可用嵌入式解决的问题',
    ].map((text, index) => ({ key: `innovationEngineering_${index}`, text })),
  },
  {
    key: 'difficulties',
    title: '八、学习困难自评',
    type: 'difficulties',
    questions: [
      {
        key: 'currentDifficulties',
        extraKey: 'currentDifficultiesOther',
        text: '你目前学习嵌入式最大的困难是什么？可多选：',
        options: ['C 语言基础薄弱', '电路基础薄弱', '看不懂代码', '看不懂原理图', '不会调试', '实验容易失败', '缺少项目经验', '不知道学习路线', '缺少学习兴趣', '其他：______'].map((label, index) => ({ value: String.fromCharCode(65 + index), label: `${String.fromCharCode(65 + index)}. ${label}` })),
      },
      {
        key: 'platformHelps',
        text: '你最希望平台提供哪些帮助？可多选：',
        options: ['自动生成学习画像', '推荐学习路线', '自动生成题目', '错题分析', '实验指导', '项目案例推荐', 'AI 问答辅导', '成绩单分析', '能力雷达图', '学习报告导出'].map((label, index) => ({ value: String.fromCharCode(65 + index), label: `${String.fromCharCode(65 + index)}. ${label}` })),
      },
    ],
  },
  {
    key: 'openQuestions',
    title: '九、开放性问题',
    type: 'open',
    questions: [
      { key: 'projectDescription', text: '请简单描述你做过的一个嵌入式实验或项目。' },
      { key: 'bestSkill', text: '你认为自己在嵌入式学习中最擅长的方面是什么？' },
      { key: 'targetSkill', text: '你最想提升的嵌入式能力是什么？' },
      { key: 'adviceType', text: '你希望系统给你生成什么类型的学习建议？' },
    ],
  },
]

const currentIndex = ref(0)
const resultVisible = ref(false)
const toastMsg = ref('')
let toastTimer = null

const answers = reactive({
  basic: { platforms: [] },
  ratings: {},
  difficulties: { currentDifficulties: [], platformHelps: [], currentDifficultiesOther: '' },
  open: {},
})

questionnaireSections
  .filter(section => section.type === 'rating')
  .forEach(section => {
    answers.ratings[section.key] = {}
  })

const currentSection = computed(() => questionnaireSections[currentIndex.value])
const isLastSection = computed(() => currentIndex.value === questionnaireSections.length - 1)
const completedSections = computed(() => questionnaireSections.filter(section => getSectionComplete(section)))
const sectionStatuses = computed(() => {
  return questionnaireSections.reduce((acc, section) => {
    const completed = getSectionComplete(section)
    acc[section.key] = {
      completed,
      message: completed ? '已保存' : MISSING_MESSAGE,
    }
    return acc
  }, {})
})

const ratingSections = computed(() => questionnaireSections.filter(section => section.type === 'rating'))
const scoreSummary = computed(() => {
  return ratingSections.value.map(section => ({
    key: section.key,
    title: section.title.replace(/^[一二三四五六七八九]、/, ''),
    score: getRatingAverage(section),
  }))
})

function showToast(msg) {
  toastMsg.value = msg
  clearTimeout(toastTimer)
  toastTimer = setTimeout(() => { toastMsg.value = '' }, 2200)
}

function goPrevious() {
  currentIndex.value = Math.max(0, currentIndex.value - 1)
}

function goNext() {
  currentIndex.value = Math.min(questionnaireSections.length - 1, currentIndex.value + 1)
}

function hasValue(value) {
  if (Array.isArray(value)) return value.length > 0
  return value !== undefined && value !== null && String(value).trim() !== ''
}

function getSectionComplete(section) {
  if (section.type === 'basic') {
    return section.questions.some(question => hasValue(answers.basic[question.key]))
  }
  if (section.type === 'rating') {
    return section.items.some(item => hasValue(answers.ratings[section.key][item.key]))
  }
  if (section.type === 'difficulties') {
    return section.questions.some(question => hasValue(answers.difficulties[question.key]) || hasValue(answers.difficulties[question.extraKey]))
  }
  return section.questions.some(question => hasValue(answers.open[question.key]))
}

function getRatingAverage(section) {
  const values = section.items
    .map(item => Number(answers.ratings[section.key][item.key]))
    .filter(value => Number.isFinite(value) && value > 0)
  if (!values.length) return null
  return Number((values.reduce((sum, value) => sum + value, 0) / values.length).toFixed(1))
}

function loadProfile() {
  try {
    const raw = localStorage.getItem(LS_KEY)
    return raw ? JSON.parse(raw) : {}
  } catch {
    return {}
  }
}

function saveProfile(patch) {
  const merged = { ...loadProfile(), ...patch }
  localStorage.setItem(LS_KEY, JSON.stringify(merged))
}

function buildPayload() {
  const sectionData = {}
  questionnaireSections.forEach(section => {
    const status = sectionStatuses.value[section.key]
    if (section.type === 'basic') sectionData[section.key] = { status, answers: { ...answers.basic } }
    if (section.type === 'rating') sectionData[section.key] = { status, answers: { ...answers.ratings[section.key] } }
    if (section.type === 'difficulties') sectionData[section.key] = { status, answers: { ...answers.difficulties } }
    if (section.type === 'open') sectionData[section.key] = { status, answers: { ...answers.open } }
  })

  return {
    title: '嵌入式大学生学习画像量表问卷',
    submittedAt: Date.now(),
    sectionStatuses: sectionStatuses.value,
    sections: sectionData,
    dimensionScores: scoreSummary.value,
    missingMessage: MISSING_MESSAGE,
  }
}

async function submitQuestionnaire() {
  const payload = buildPayload()
  const scaleScores = scoreSummary.value.map(item => item.score ? Math.round(item.score) : 3)
  saveProfile({
    questionnaire: payload,
    scaleScores,
    scaleTimestamp: payload.submittedAt,
    aiAnalysis: null,
  })
  resultVisible.value = false
  showToast('问卷已保存，正在返回采集进度')

  saveLearningProfileQuestionnaire(payload)
    .catch(() => showToast('问卷已本地保存，数据库保存失败'))

  setTimeout(returnToCollectProgress, 600)
}
</script>

<style scoped>
.questionnaire-page {
  height: 100vh;
  min-height: 0;
  padding: 20px 28px 32px;
  overflow-y: auto;
  overflow-x: hidden;
  background: #f4faf9;
  box-sizing: border-box;
  scrollbar-gutter: stable;
}

.questionnaire-page::-webkit-scrollbar {
  width: 10px;
}

.questionnaire-page::-webkit-scrollbar-track {
  background: #e8f1f3;
}

.questionnaire-page::-webkit-scrollbar-thumb {
  background: #9cc9c5;
  border: 2px solid #e8f1f3;
  border-radius: 999px;
}

.questionnaire-page::-webkit-scrollbar-thumb:hover {
  background: #68aaa4;
}

.toast-bar {
  position: fixed;
  top: 20px;
  left: 50%;
  transform: translateX(-50%);
  z-index: 1000;
  padding: 12px 22px;
  border-radius: 8px;
  background: #117a51;
  color: var(--surface, rgba(255, 255, 255, 0.94));
  font-size: 14px;
  font-weight: 700;
  box-shadow: 0 8px 24px rgba(15, 118, 110, 0.24);
}

.toast-enter-active,
.toast-leave-active {
  transition: opacity 0.2s, transform 0.2s;
}

.toast-enter-from,
.toast-leave-to {
  opacity: 0;
  transform: translateX(-50%) translateY(-8px);
}

.questionnaire-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 20px;
  margin-bottom: 14px;
}

.section-kicker {
  margin: 0 0 6px;
  color: #117a51;
  font-size: 13px;
  font-weight: 800;
}

h1,
h2,
h3 {
  margin: 0;
  color: #1f3f3b;
}

h1 {
  font-size: 24px;
  line-height: 1.25;
}

h2 {
  font-size: 22px;
}

.questionnaire-shell {
  display: grid;
  grid-template-columns: 220px minmax(0, 1fr);
  gap: 18px;
  align-items: start;
}

.section-rail,
.questionnaire-card,
.result-card {
  background: var(--surface, rgba(255, 255, 255, 0.94));
  border: 1px solid var(--border, rgba(31, 166, 112, 0.1));
  border-radius: 8px;
  box-shadow: 0 2px 12px rgba(15, 23, 42, 0.04);
}

.section-rail {
  position: sticky;
  top: 84px;
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding: 10px;
}

.rail-item {
  display: flex;
  align-items: center;
  gap: 10px;
  min-height: 38px;
  padding: 0 10px;
  border: 1px solid transparent;
  border-radius: 6px;
  background: transparent;
  color: #475569;
  font: inherit;
  font-size: 13px;
  font-weight: 700;
  cursor: pointer;
  text-align: left;
}

.rail-item.active,
.rail-item:hover {
  border-color: rgba(31, 188, 191, 0.24);
  background: rgba(31, 188, 191, 0.1);
  color: #117a51;
}

.rail-item.complete .rail-index {
  background: #10b981;
  color: var(--surface, rgba(255, 255, 255, 0.94));
}

.rail-index {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 24px;
  height: 24px;
  border-radius: 50%;
  background: #e2e8f0;
  color: #334155;
  font-size: 12px;
}

.rail-label {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.questionnaire-card,
.result-card {
  padding: 24px 30px;
}

.card-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 20px;
}

.status-pill {
  padding: 5px 10px;
  border-radius: 999px;
  background: rgba(31, 188, 191, 0.1);
  color: #117a51;
  font-size: 12px;
  font-weight: 800;
}

.section-hint {
  margin: -4px 0 22px;
  color: #64748b;
  line-height: 1.7;
}

.question-list,
.open-list {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.choice-block {
  padding-bottom: 20px;
  border-bottom: 1px solid #eef2f6;
}

.choice-block:last-child {
  border-bottom: none;
}

.question-title {
  margin: 0 0 12px;
  color: #334155;
  font-size: 15px;
  font-weight: 800;
}

.choice-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
}

.choice-item {
  display: flex;
  align-items: center;
  gap: 10px;
  min-height: 42px;
  padding: 0 12px;
  border: 1px solid #dbe5ea;
  border-radius: 6px;
  color: #334155;
  cursor: pointer;
}

.choice-item input {
  width: 16px;
  height: 16px;
  accent-color: #117a51;
}

.text-input {
  width: 100%;
  min-height: 40px;
  margin-top: 12px;
  padding: 0 12px;
  border: 1px solid #dbe5ea;
  border-radius: 6px;
  color: #334155;
  font: inherit;
  box-sizing: border-box;
}

.rating-table-wrap {
  overflow-x: auto;
}

.rating-table {
  width: 100%;
  border-collapse: collapse;
  min-width: 720px;
}

.rating-table th,
.rating-table td {
  border-bottom: 1px solid var(--border, rgba(31, 166, 112, 0.1));
  padding: 14px 10px;
  color: #334155;
  text-align: center;
}

.rating-table th:first-child,
.rating-table td:first-child {
  width: 58%;
  text-align: left;
}

.rating-table th {
  color: #117a51;
  font-size: 13px;
  font-weight: 800;
}

.rating-cell {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 30px;
  height: 30px;
  cursor: pointer;
}

.rating-cell input {
  display: none;
}

.rating-cell span {
  width: 18px;
  height: 18px;
  border: 2px solid #cbd5e1;
  border-radius: 50%;
}

.rating-cell input:checked + span {
  border-color: #117a51;
  box-shadow: inset 0 0 0 4px var(--surface, rgba(255, 255, 255, 0.94));
  background: #117a51;
}

.open-item {
  display: flex;
  flex-direction: column;
  gap: 10px;
  color: #334155;
  font-weight: 800;
}

.open-item textarea {
  width: 100%;
  resize: vertical;
  padding: 12px;
  border: 1px solid #dbe5ea;
  border-radius: 6px;
  color: #334155;
  font: inherit;
  line-height: 1.6;
  box-sizing: border-box;
}

.step-actions {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  margin-top: 28px;
}

.ghost-btn,
.primary-btn {
  min-height: 40px;
  padding: 0 18px;
  border-radius: 6px;
  font: inherit;
  font-weight: 800;
  cursor: pointer;
}

.ghost-btn {
  border: 1px solid #cbd5e1;
  background: var(--surface, rgba(255, 255, 255, 0.94));
  color: #475569;
}

.ghost-btn:disabled {
  opacity: 0.48;
  cursor: not-allowed;
}

.primary-btn {
  border: 1px solid #117a51;
  background: #117a51;
  color: var(--surface, rgba(255, 255, 255, 0.94));
}

.result-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.result-item,
.score-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 12px 14px;
  border: 1px solid var(--border, rgba(31, 166, 112, 0.1));
  border-radius: 6px;
  color: #334155;
}

.result-title {
  font-weight: 800;
}

.result-status {
  font-size: 13px;
  font-weight: 800;
}

.result-status.ok {
  color: #117a51;
}

.result-status.missing {
  color: #b45309;
}

.score-summary {
  margin-top: 24px;
}

.score-summary h3 {
  margin-bottom: 12px;
  font-size: 18px;
}

.score-row + .score-row {
  margin-top: 8px;
}

@media (max-width: 900px) {
  .questionnaire-page {
    padding: 20px 16px 32px;
  }

  .questionnaire-header {
    align-items: flex-start;
    flex-direction: column;
  }

  .questionnaire-shell {
    grid-template-columns: 1fr;
  }

  .section-rail {
    position: static;
  }

  .choice-grid,
  .result-grid {
    grid-template-columns: 1fr;
  }
}
</style>
