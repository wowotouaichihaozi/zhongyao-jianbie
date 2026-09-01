<template>
  <div class="interview-page">
    <TopNavbar />

    <main class="interview-main">
      <header class="interview-header">
        <div>
          <p class="eyebrow">Digital Human Interview</p>
          <h1>数字人 AI 面试</h1>
        </div>
        <div class="status-strip">
          <i :class="{ active: interviewInProgress }" aria-hidden="true"></i>
          <span>{{ interviewStatus }}</span>
          <strong>{{ avatarStatus }}</strong>
        </div>
      </header>

      <section class="interview-layout">
        <div class="visual-panel">
          <DigitalHumanAvatar
            v-if="avatarVisible"
            ref="avatarRef"
            class="avatar-area"
            @status-change="handleAvatarStatus"
            @error="handleAvatarError"
          />
          <img
            v-show="!avatarConnected"
            class="avatar-standby"
            src="/avatar-interview-standby.png"
            alt=""
            aria-hidden="true"
          />
          <div
            v-if="avatarConnectionFailed"
            class="avatar-fallback-notice"
            role="status"
            :title="avatarErrorMessage"
          >
            <MessageSquareText :size="18" aria-hidden="true" />
            <span>数字人暂不可用，文字面试正常进行</span>
          </div>
          <div v-if="!avatarVisible" class="avatar-idle-card">
            <strong>数字人待启动</strong>
            <span>点击“开始面试”后连接数字人面试官</span>
          </div>
        </div>

        <aside class="chat-panel">
          <div class="interview-options">
            <label>
              岗位大类
              <select v-model="interviewForm.categoryKey" :disabled="optionsLocked" @change="handleCategoryChange">
                <option v-for="category in INTERVIEW_CATEGORIES" :key="category.value" :value="category.value">
                  {{ category.label }}
                </option>
              </select>
            </label>
            <label>
              具体岗位
              <select v-model="interviewForm.positionKey" :disabled="optionsLocked" @change="handlePositionChange">
                <option v-for="position in positionOptions" :key="position.value" :value="position.value">
                  {{ position.label }}
                </option>
              </select>
            </label>
            <label>
              面试方向
              <select v-model="interviewForm.directionKey" :disabled="optionsLocked" @change="syncFormLabels">
                <option v-for="direction in directionOptions" :key="direction.value" :value="direction.value">
                  {{ direction.label }}
                </option>
              </select>
            </label>
            <label>
              难度
              <select v-model="interviewForm.difficulty" :disabled="optionsLocked">
                <option v-for="difficulty in DIFFICULTY_OPTIONS" :key="difficulty.value" :value="difficulty.value">
                  {{ difficulty.label }}
                </option>
              </select>
            </label>
          </div>

          <div ref="chatLogRef" class="chat-log">
            <div v-if="!messages.length" class="empty-chat">
              <span class="empty-chat-icon"><MessageSquareText :size="24" stroke-width="1.9" /></span>
              <strong>面试准备就绪</strong>
              <p>{{ interviewForm.position }}</p>
              <div class="empty-chat-meta">
                <span>{{ interviewForm.direction }}</span>
                <span>{{ selectedDifficulty?.label || interviewForm.difficulty }}</span>
              </div>
            </div>
            <article
              v-for="message in messages"
              :key="message.id"
              class="chat-message"
              :class="`role-${message.role}`"
            >
              <div class="message-meta">
                <strong>{{ roleLabel(message.role) }}</strong>
                <span>{{ message.time }}</span>
              </div>
              <p>{{ message.content }}</p>
              <ul v-if="message.advantages?.length" class="suggestion-list">
                <li v-for="item in message.advantages" :key="`adv-${item}`">优点：{{ item }}</li>
              </ul>
              <ul v-if="message.weaknesses?.length" class="suggestion-list">
                <li v-for="item in message.weaknesses" :key="`weak-${item}`">不足：{{ item }}</li>
              </ul>
              <ul v-if="message.suggestions?.length" class="suggestion-list">
                <li v-for="item in message.suggestions" :key="`sug-${item}`">建议：{{ item }}</li>
              </ul>
            </article>
          </div>

          <footer class="answer-bar">
            <SpeechAnswerInput
              ref="speechInputRef"
              v-model="answerText"
              :disabled="!sessionId || interviewEnded || isBusy"
              @send="sendAnswer"
            />
            <div class="button-row">
              <button
                type="button"
                class="primary-button"
                :disabled="Boolean(sessionId && !interviewEnded) || isStartingInterview || isBusy"
                @click="startInterview"
              >
                <LoaderCircle v-if="isStartingInterview" class="button-spinner" :size="17" aria-hidden="true" />
                <PlayCircle v-else :size="17" aria-hidden="true" />
                {{ isStartingInterview ? '正在开始...' : (interviewEnded ? '重新开始' : '开始面试') }}
              </button>
              <button type="button" class="primary-button" :disabled="!canSend" @click="sendAnswer">
                <SendHorizontal :size="17" aria-hidden="true" />
                发送回答
              </button>
              <button type="button" class="secondary-button" :disabled="!sessionId || interviewEnded || isBusy" @click="endInterview">
                <CircleStop :size="17" aria-hidden="true" />
                {{ interviewEnded ? '已结束' : '结束面试' }}
              </button>
            </div>
            <p v-if="errorMessage" class="error-text">{{ errorMessage }}</p>
          </footer>
        </aside>
      </section>
    </main>
  </div>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, reactive, ref } from 'vue'
import { CircleStop, LoaderCircle, MessageSquareText, PlayCircle, SendHorizontal } from 'lucide-vue-next'
import TopNavbar from '../components/TopNavbar.vue'
import DigitalHumanAvatar from '../components/DigitalHumanAvatar.vue'
import SpeechAnswerInput from '../components/SpeechAnswerInput.vue'
import { DIFFICULTY_OPTIONS, INTERVIEW_CATEGORIES, findOption } from '../config/interviewOptions.js'
import { endInterviewSession, sendInterviewMessage, startInterviewSession } from '../services/api.js'

const avatarRef = ref(null)
const speechInputRef = ref(null)
const chatLogRef = ref(null)
const sessionId = ref('')
const messages = ref([])
const answerText = ref('')
const interviewStatus = ref('未开始')
const avatarStatus = ref('数字人未连接')
const avatarErrorMessage = ref('')
const errorMessage = ref('')
const isBusy = ref(false)
const isStartingInterview = ref(false)
const interviewEnded = ref(false)
const avatarVisible = ref(true)
const avatarConnected = ref(false)
const avatarConnectionFailed = ref(false)
const AVATAR_START_TIMEOUT_MS = 15000
const AVATAR_SPEAK_TIMEOUT_MS = 10000
const AVATAR_DESTROY_TIMEOUT_MS = 5000
let avatarOperationVersion = 0

const interviewForm = reactive({
  categoryKey: 'mcu_development',
  category: '单片机与 MCU 开发',
  positionKey: 'stm32_developer',
  position: 'STM32 开发工程师',
  directionKey: 'gpio_interrupt_uart',
  direction: 'GPIO / 中断 / UART',
  topic: 'GPIO / 中断 / UART',
  difficulty: 'medium',
})

const selectedCategory = computed(() => findOption(INTERVIEW_CATEGORIES, interviewForm.categoryKey))
const positionOptions = computed(() => selectedCategory.value?.positions || [])
const selectedPosition = computed(() => findOption(positionOptions.value, interviewForm.positionKey))
const directionOptions = computed(() => selectedPosition.value?.directions || [])
const selectedDirection = computed(() => findOption(directionOptions.value, interviewForm.directionKey))
const selectedDifficulty = computed(() => findOption(DIFFICULTY_OPTIONS, interviewForm.difficulty))
const optionsLocked = computed(() => Boolean((sessionId.value && !interviewEnded.value) || isStartingInterview.value || isBusy.value))
const interviewInProgress = computed(() => Boolean(sessionId.value && !interviewEnded.value))

const canSend = computed(() => {
  return Boolean(sessionId.value && answerText.value.trim() && !interviewEnded.value && !isBusy.value)
})

function syncFormLabels() {
  interviewForm.category = selectedCategory.value?.label || ''
  interviewForm.position = selectedPosition.value?.label || ''
  interviewForm.direction = selectedDirection.value?.label || ''
  interviewForm.topic = interviewForm.direction
}

function handleCategoryChange() {
  const firstPosition = positionOptions.value[0]
  interviewForm.positionKey = firstPosition?.value || ''
  interviewForm.directionKey = firstPosition?.directions?.[0]?.value || ''
  syncFormLabels()
}

function handlePositionChange() {
  interviewForm.directionKey = directionOptions.value[0]?.value || ''
  syncFormLabels()
}

syncFormLabels()

function nowText() {
  return new Date().toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
}

function isChatNearBottom() {
  const el = chatLogRef.value
  if (!el) return true
  return el.scrollHeight - el.scrollTop - el.clientHeight < 72
}

function appendMessage(role, content, extra = {}) {
  const shouldStickToBottom = isChatNearBottom()
  messages.value.push({
    id: `${Date.now()}-${Math.random().toString(16).slice(2)}`,
    role,
    content,
    time: nowText(),
    ...extra,
  })
  nextTick(() => {
    if (chatLogRef.value && shouldStickToBottom) {
      chatLogRef.value.scrollTop = chatLogRef.value.scrollHeight
    }
  })
}

function roleLabel(role) {
  if (role === 'user') return '候选人'
  if (role === 'summary') return '面试总结'
  return '数字人面试官'
}

function isTimeoutError(error) {
  const message = `${error?.message || ''} ${error?.response?.data?.error || ''} ${error?.response?.data?.msg || ''}`
    .toLowerCase()
  return error?.code === 'ECONNABORTED' || message.includes('timeout') || message.includes('timed out')
}

function getErrorMessage(error, fallback) {
  if (isTimeoutError(error)) {
    return 'AI 面试官正在生成问题，响应时间较长，请稍后重试。'
  }
  return error?.response?.data?.msg || error?.response?.data?.error || error?.message || fallback
}

function getDisplayText(response) {
  if (typeof response === 'string') return response
  if (!response || typeof response !== 'object') return ''

  const value = response.content ?? response.message ?? response.reply ?? response.summary ?? ''
  if (typeof value === 'string') return value
  if (value && typeof value === 'object') {
    return value.content || value.message || value.reply || value.summary || ''
  }
  return ''
}

function cleanSummaryScoreLines(text) {
  return String(text || '')
    .split('\n')
    .filter((line) => !/(综合)?评分|得分|\d{1,3}\s*\/\s*100/.test(line))
    .join('\n')
    .replace(/\n{3,}/g, '\n\n')
    .trim()
}

function buildSummaryDisplay(result) {
  const summary = cleanSummaryScoreLines(getDisplayText({ summary: result?.summary || result?.content || '' }))
  const endReason = result?.autoEnded && result?.endReason ? `自动结束原因：${result.endReason}` : ''
  const hasScore = result?.score !== null && result?.score !== undefined && result?.score !== '' && Number.isFinite(Number(result.score))
  const scoreText = hasScore ? `综合评分：${Number(result.score)} 分` : '综合评分：暂无评分'
  const textScoreText = hasScore && Number.isFinite(Number(result?.textScore)) ? `文字回答评分：${Number(result.textScore)} 分` : ''
  return [endReason, summary, scoreText, textScoreText].filter(Boolean).join('\n')
}

function isModelAuthError(reason = '') {
  return /401|invalid api key|invalid_key|auth|unauthorized|鉴权|api key|token/i.test(String(reason))
}

function applySourceNotice(result) {
  console.log(
    '[Interview Source]',
    result?.source,
    result?.usedAI,
    result?.fallbackReason || '',
    result?.answerType || '',
    result?.answerScore ?? '',
    result?.shouldEnd || false,
    result?.autoEnded || false,
    result?.endType || '',
    result?.endReason || '',
    result?.round || '',
  )
  if (result?.source === 'local-fallback') {
    errorMessage.value = isModelAuthError(result?.fallbackReason)
      ? 'AI 面试模型鉴权失败，已先使用本地面试题继续。请检查嵌小智模型设置或平台凭据。'
      : 'AI 面试模型响应较慢，已先使用本地面试题继续。'
  }
}

function handleAvatarStatus(event) {
  const code = String(event?.code || '')
  if (['connected', 'speaking', 'waiting', 'resume-required'].includes(code)) {
    avatarConnected.value = true
    avatarConnectionFailed.value = false
    avatarErrorMessage.value = ''
  } else if (['idle', 'loading-config', 'ready', 'connecting', 'error', 'disconnected', 'destroyed'].includes(code)) {
    avatarConnected.value = false
  }
  if (['error', 'disconnected'].includes(code)) {
    avatarConnectionFailed.value = true
  }
  avatarStatus.value = event?.label || '数字人状态更新'
}

function handleAvatarError(message) {
  avatarConnected.value = false
  avatarConnectionFailed.value = true
  avatarErrorMessage.value = String(message || '数字人连接失败')
  avatarStatus.value = '文字模式可用'
}

function stopSpeechRecognition() {
  speechInputRef.value?.stopRecognition?.()
}

async function safeSpeak(text) {
  const avatar = avatarRef.value
  const statusCode = avatar?.statusCode?.value ?? avatar?.statusCode ?? ''
  if (!avatar || avatarConnectionFailed.value || ['error', 'disconnected', 'destroyed'].includes(statusCode)) {
    return false
  }

  try {
    await withTimeout(
      Promise.resolve(avatar.speak(text)),
      AVATAR_SPEAK_TIMEOUT_MS,
      '数字人播报超时',
    )
    return true
  } catch (error) {
    handleAvatarError(getErrorMessage(error, '数字人暂时无法朗读，文字面试仍可继续'))
    return false
  }
}

function withTimeout(promise, timeoutMs, message) {
  let timer = 0
  return Promise.race([
    promise,
    new Promise((_, reject) => {
      timer = window.setTimeout(() => reject(new Error(message)), timeoutMs)
    }),
  ]).finally(() => {
    if (timer) window.clearTimeout(timer)
  })
}

function runAvatarInBackground(task) {
  Promise.resolve()
    .then(task)
    .catch((error) => {
      handleAvatarError(getErrorMessage(error, '数字人暂不可用，文字面试仍可继续'))
    })
}

async function startInterviewAvatar(options = {}) {
  const keepInterviewStatus = Boolean(options.keepInterviewStatus)
  const resetBeforeStart = options.resetBeforeStart !== false
  const operationVersion = ++avatarOperationVersion

  try {
    if (resetBeforeStart && avatarRef.value) {
      await withTimeout(
        Promise.resolve(avatarRef.value.destroyAvatar?.()),
        AVATAR_DESTROY_TIMEOUT_MS,
        '数字人释放超时',
      )
      if (operationVersion !== avatarOperationVersion) return false
      avatarVisible.value = false
      await nextTick()
    }

    avatarConnectionFailed.value = false
    avatarErrorMessage.value = ''
    avatarVisible.value = true
    avatarStatus.value = '数字人连接中'
    await nextTick()
    if (operationVersion !== avatarOperationVersion) return false

    const avatar = avatarRef.value
    if (!avatar) return false
    const started = await withTimeout(
      Promise.resolve(avatar.startAvatar()),
      AVATAR_START_TIMEOUT_MS,
      '数字人连接超时',
    )
    if (operationVersion !== avatarOperationVersion) return false
    if (started !== true) {
      const statusCode = avatar?.statusCode?.value ?? avatar?.statusCode ?? ''
      if (statusCode === 'resume-required') {
        avatarStatus.value = '点击数字人开启声音'
        return false
      }
      throw new Error('数字人未能建立连接')
    }
    avatarConnectionFailed.value = false
    avatarErrorMessage.value = ''
    avatarStatus.value = keepInterviewStatus ? '数字人已连接' : '数字人就绪'
    return true
  } catch (error) {
    if (operationVersion !== avatarOperationVersion) return false
    handleAvatarError(getErrorMessage(error, '数字人连接失败，文字面试仍可继续'))
    Promise.resolve(avatarRef.value?.destroyAvatar?.()).catch(() => {})
    return false
  }
}

function startAvatarNarration(text, options = {}) {
  runAvatarInBackground(async () => {
    if (options.connect) {
      const started = await startInterviewAvatar({
        keepInterviewStatus: true,
        resetBeforeStart: options.resetBeforeStart !== false,
      })
      if (!started) return
    }
    await safeSpeak(text)
  })
}

function handleEndedInterviewResult(result) {
  interviewEnded.value = true
  interviewStatus.value = '已结束'
  stopSpeechRecognition()
  const summaryDisplay = buildSummaryDisplay(result)
  const hasScore = result?.score !== null && result?.score !== undefined && result?.score !== '' && Number.isFinite(Number(result.score))
  appendMessage('summary', summaryDisplay || '本次面试已结束。', {
    advantages: hasScore ? (result.advantages || []) : [],
    weaknesses: hasScore ? (result.weaknesses || []) : [],
    suggestions: hasScore ? (result.suggestions || []) : [],
  })
  applySourceNotice(result)
  startAvatarNarration(`本次面试已结束。${summaryDisplay}`)
}

async function startInterview() {
  if (isStartingInterview.value || isBusy.value || (sessionId.value && !interviewEnded.value)) return

  Promise.resolve(avatarRef.value?.resumeAvatar?.()).catch(() => {})
  isBusy.value = true
  isStartingInterview.value = true
  errorMessage.value = ''
  interviewEnded.value = false
  sessionId.value = ''
  messages.value = []
  answerText.value = ''
  avatarConnectionFailed.value = false
  stopSpeechRecognition()
  interviewStatus.value = '正在连接 AI 面试官，请稍候...'
  avatarVisible.value = true

  try {
    syncFormLabels()
    const result = await startInterviewSession({
      categoryKey: interviewForm.categoryKey,
      category: interviewForm.category,
      positionKey: interviewForm.positionKey,
      position: interviewForm.position,
      directionKey: interviewForm.directionKey,
      direction: interviewForm.direction,
      topic: interviewForm.topic,
      difficulty: interviewForm.difficulty,
      difficultyLabel: selectedDifficulty.value?.label || interviewForm.difficulty,
      cameraEnabled: false,
      videoAnalysisEnabled: false,
    })
    const displayText = getDisplayText(result)
    const questionText = displayText || '面试已开始，请准备回答。'
    sessionId.value = result.sessionId
    appendMessage('interviewer', questionText)
    applySourceNotice(result)
    interviewStatus.value = '等待回答'
    startAvatarNarration(questionText, { connect: true, resetBeforeStart: false })
  } catch (error) {
    interviewStatus.value = '错误'
    errorMessage.value = getErrorMessage(error, '创建面试会话失败')
  } finally {
    isStartingInterview.value = false
    isBusy.value = false
  }
}

async function sendAnswer() {
  const answer = answerText.value.trim()
  if (!canSend.value || !answer) return

  stopSpeechRecognition()
  appendMessage('user', answer)
  answerText.value = ''
  isBusy.value = true
  errorMessage.value = ''
  interviewStatus.value = '发送中'

  try {
    const result = await sendInterviewMessage({
      sessionId: sessionId.value,
      answer,
    })
    if (result.status === 'ended' || result.autoEnded) {
      await handleEndedInterviewResult(result)
      return
    }
    const displayText = getDisplayText(result)
    const questionText = displayText || '我们继续下一个问题。'
    appendMessage('interviewer', questionText)
    applySourceNotice(result)
    interviewStatus.value = '等待回答'
    startAvatarNarration(questionText)
  } catch (error) {
    interviewStatus.value = '错误'
    errorMessage.value = getErrorMessage(error, '发送回答失败')
  } finally {
    isBusy.value = false
  }
}

async function endInterview() {
  if (!sessionId.value || interviewEnded.value) return

  stopSpeechRecognition()
  isBusy.value = true
  errorMessage.value = ''
  interviewStatus.value = '生成总结中'

  try {
    const result = await endInterviewSession({ sessionId: sessionId.value })
    await handleEndedInterviewResult(result)
  } catch (error) {
    interviewStatus.value = '错误'
    errorMessage.value = getErrorMessage(error, '结束面试失败')
  } finally {
    isBusy.value = false
  }
}

onBeforeUnmount(() => {
  avatarOperationVersion += 1
  stopSpeechRecognition()
  avatarRef.value?.destroyAvatar?.()
})

onMounted(() => {
  startInterviewAvatar({ keepInterviewStatus: false, resetBeforeStart: false }).catch(() => {})
})
</script>

<style scoped>
.interview-page {
  display: flex;
  flex-direction: column;
  height: 100vh;
  min-height: 100vh;
  overflow: hidden;
  color: #0b0e0d;
  background: #ffffff;
}

.interview-main {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
  width: 100%;
  max-width: 1600px;
  margin: 0 auto;
  padding: 16px 24px 20px;
  box-sizing: border-box;
}

.interview-header {
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 18px;
  margin-bottom: 12px;
}

.eyebrow {
  margin: 0 0 4px;
  color: #176f4b;
  font-size: 11px;
  font-weight: 800;
  text-transform: uppercase;
}

h1 {
  margin: 0;
  color: #080b0a;
  font-size: 28px;
  line-height: 1.2;
}

.status-strip {
  display: flex;
  gap: 10px;
  align-items: center;
  min-height: 36px;
  padding: 0 12px;
  border-radius: 6px;
  border: 1px solid #cdd5d1;
  background: #ffffff;
  color: #303834;
  font-size: 13px;
}

.status-strip i {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #a8b1ad;
}

.status-strip i.active {
  background: #0b9965;
  box-shadow: 0 0 0 4px rgba(11, 153, 101, 0.12);
}

.status-strip strong {
  color: #075c3e;
}

.interview-layout {
  flex: 1;
  min-height: 0;
  display: grid;
  grid-template-columns: minmax(380px, 0.86fr) minmax(560px, 1.14fr);
  gap: 16px;
}

.visual-panel {
  position: relative;
  min-height: 0;
  height: 100%;
  overflow: hidden;
  border-radius: 8px;
  background: #f8faf9 url("/shuzirenbg.png") center bottom / cover no-repeat;
  box-shadow: none;
  border: 1px solid #d2d9d6;
}

.visual-panel :deep(.avatar-panel) {
  position: absolute;
  left: 50%;
  bottom: 0;
  z-index: 2;
  width: min(720px, calc(100% - 32px));
  height: min(680px, calc(100% - 36px));
  min-height: 520px;
  transform: translateX(-50%);
  overflow: hidden;
  background: transparent;
  border: 0;
  border-radius: 0;
  box-shadow: none;
}

.visual-panel :deep(.avatar-stage) {
  inset: 0;
  width: 100%;
  height: 100%;
  background: transparent !important;
  overflow: hidden;
}

.visual-panel :deep(> .avatar-panel > .avatar-stage > #xvideo),
.visual-panel :deep(> .avatar-panel > .avatar-stage > [id*="xvideo"]),
.visual-panel :deep(> .avatar-panel > .avatar-stage > iframe),
.visual-panel :deep(> .avatar-panel > .avatar-stage > video),
.visual-panel :deep(> .avatar-panel > .avatar-stage > canvas) {
  display: block !important;
  width: 100% !important;
  height: 100% !important;
  max-width: 100% !important;
  max-height: 100% !important;
  object-fit: contain !important;
  object-position: center bottom !important;
  background: transparent !important;
  border: 0 !important;
  overflow: hidden !important;
}

.visual-panel :deep(> .avatar-panel > .avatar-stage > iframe) {
  background: #ffffff !important;
}

.avatar-standby {
  position: absolute;
  left: 50%;
  bottom: 0;
  z-index: 3;
  width: min(54%, 360px);
  height: 88%;
  object-fit: contain;
  object-position: center bottom;
  pointer-events: none;
  filter: drop-shadow(0 16px 28px rgba(24, 77, 59, 0.12));
  transform: translateX(-50%);
  animation: avatarStandbyBreath 2.4s ease-in-out infinite;
}

@keyframes avatarStandbyBreath {
  0%, 100% {
    opacity: 0.9;
    transform: translateX(-50%) translateY(0);
  }
  50% {
    opacity: 1;
    transform: translateX(-50%) translateY(-3px);
  }
}

.avatar-idle-card {
  position: absolute;
  left: 50%;
  top: 50%;
  z-index: 2;
  display: grid;
  gap: 10px;
  min-width: 260px;
  padding: 26px 30px;
  border: 1px solid #d2d9d6;
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.94);
  color: #151a18;
  text-align: center;
  box-shadow: 0 12px 30px rgba(16, 32, 25, 0.08);
  transform: translate(-50%, -50%);
  backdrop-filter: blur(14px);
}

.avatar-idle-card strong {
  font-size: 24px;
  font-weight: 700;
}

.avatar-idle-card span {
  color: #46504c;
  font-size: 14px;
}

.avatar-fallback-notice {
  position: absolute;
  left: 50%;
  bottom: 18px;
  z-index: 8;
  display: inline-flex;
  width: max-content;
  max-width: calc(100% - 32px);
  min-height: 40px;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 9px 13px;
  border: 1px solid #d8e4e1;
  border-radius: 7px;
  background: rgba(255, 255, 255, 0.94);
  color: #30544c;
  font-size: 13px;
  font-weight: 700;
  line-height: 1.4;
  text-align: center;
  transform: translateX(-50%);
  box-sizing: border-box;
  backdrop-filter: blur(8px);
}

.visual-panel :deep(.avatar-error) {
  display: none;
}

.visual-panel,
.avatar-area,
.chat-panel {
  min-height: 0;
  height: 100%;
}

.chat-panel {
  display: flex;
  flex-direction: column;
  overflow: hidden;
  border-radius: 8px;
  border: 1px solid #cfd7d3;
  background: #ffffff;
}

.interview-options {
  flex-shrink: 0;
  display: grid;
  grid-template-columns: 1fr 1.1fr 1.35fr 96px;
  gap: 10px;
  padding: 12px 14px;
  border-bottom: 1px solid #d7ddda;
  background: #ffffff;
}

.interview-options label {
  display: grid;
  gap: 6px;
  color: #313936;
  font-size: 12px;
  font-weight: 700;
}

.interview-options input,
.interview-options select {
  width: 100%;
  box-sizing: border-box;
  border: 1px solid #c3ccc7;
  border-radius: 6px;
  background: #ffffff;
  color: #0d1210;
  outline: none;
}

.interview-options input,
.interview-options select {
  height: 38px;
  padding: 0 10px;
}

.chat-log {
  flex: 1 1 160px;
  min-height: 120px;
  overflow-y: auto;
  padding: 18px;
  background: #ffffff;
  scrollbar-gutter: stable;
}

.empty-chat {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  height: 100%;
  justify-content: center;
  color: #303834;
  font-size: 14px;
  text-align: center;
}

.empty-chat-icon {
  display: grid;
  place-items: center;
  width: 46px;
  height: 46px;
  border: 1px solid #bcd4c8;
  border-radius: 8px;
  background: #eef8f3;
  color: #0b7f55;
}

.empty-chat > strong {
  color: #0a0d0c;
  font-size: 18px;
}

.empty-chat > p {
  margin: 0;
  color: #252c29;
  font-size: 15px;
  font-weight: 700;
}

.empty-chat-meta {
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
  gap: 6px;
}

.empty-chat-meta span {
  padding: 4px 8px;
  border: 1px solid #d2d9d6;
  border-radius: 4px;
  background: #ffffff;
  color: #48514d;
  font-size: 12px;
}

.chat-message {
  max-width: 86%;
  margin-bottom: 14px;
  padding: 12px 14px;
  border-radius: 8px;
  border: 1px solid #d4dbd7;
  background: #f7f9f8;
}

.chat-message.role-user {
  margin-left: auto;
  background: #eaf7f0;
  border-color: #b7daca;
}

.chat-message.role-summary {
  max-width: 100%;
  background: #edf8f2;
  border-color: #afd5c2;
}

.message-meta {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 8px;
  color: #075c3e;
  font-size: 12px;
}

.chat-message.role-user .message-meta {
  color: #0369a1;
}

.message-meta span {
  color: #5f6965;
}

.chat-message p {
  margin: 0;
  white-space: pre-wrap;
  color: #171d1a;
  line-height: 1.65;
}

.suggestion-list {
  margin: 10px 0 0;
  padding-left: 18px;
  color: #15803d;
  line-height: 1.6;
}

.answer-bar {
  flex-shrink: 0;
  padding: 10px 12px;
  border-top: 1px solid #d7ddda;
  background: #ffffff;
}

.answer-bar :deep(textarea) {
  resize: none;
  min-height: 64px;
  max-height: 84px;
  padding: 10px;
  line-height: 1.5;
}

.button-row {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin-top: 10px;
}

.primary-button,
.secondary-button {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 7px;
  min-height: 38px;
  border: 1px solid transparent;
  border-radius: 6px;
  padding: 0 14px;
  cursor: pointer;
  font-weight: 700;
}

.primary-button {
  border-color: #176f4b;
  background: #176f4b;
  color: #ffffff;
}

.secondary-button {
  border-color: #cbd3cf;
  background: #ffffff;
  color: #202724;
}

.primary-button:disabled,
.secondary-button:disabled {
  cursor: not-allowed;
  opacity: 0.48;
}

.error-text {
  margin: 10px 0 0;
  max-height: 38px;
  overflow-y: auto;
  color: #b91c1c;
  font-size: 13px;
  line-height: 1.4;
}

.button-spinner {
  animation: interviewSpin 0.8s linear infinite;
}

@keyframes interviewSpin {
  to { transform: rotate(360deg); }
}

@media (max-width: 980px) {
  .interview-main {
    padding: 18px 14px calc(118px + env(safe-area-inset-bottom));
  }

  .interview-page {
    height: auto;
    overflow: auto;
  }

  .interview-header {
    align-items: stretch;
    flex-direction: column;
  }

  .interview-layout {
    grid-template-columns: 1fr;
    min-height: 0;
  }

  .visual-panel {
    overflow: visible;
    min-height: 500px;
  }

  .avatar-area {
    min-height: 460px;
  }

  .chat-panel {
    min-height: 560px;
  }

  .interview-options {
    grid-template-columns: 1fr;
  }

  .interview-options input,
  .interview-options select {
    min-height: 46px;
    border-radius: 12px;
    font-size: 15px;
  }

  .primary-button,
  .secondary-button {
    min-height: 48px;
    border-radius: 6px;
  }

  .button-row .primary-button,
  .button-row .secondary-button,
  .answer-bar .primary-button,
  .answer-bar .secondary-button {
    height: 48px !important;
    min-height: 48px !important;
    padding: 0 18px !important;
  }

  .button-row {
    gap: 12px;
  }

  .chat-panel,
  .visual-panel {
    scroll-margin-bottom: calc(118px + env(safe-area-inset-bottom));
  }
}

@media (max-width: 640px) {
  .interview-main {
    padding-inline: 10px;
  }

  .visual-panel {
    min-height: 420px;
  }

  .button-row > button {
    flex: 1 1 calc(50% - 6px);
  }
}

@media (prefers-reduced-motion: reduce) {
  .button-spinner {
    animation: none;
  }
}
</style>
