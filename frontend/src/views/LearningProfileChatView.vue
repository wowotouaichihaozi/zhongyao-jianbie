<template>
  <div class="chat-page">
    <Transition name="toast">
      <div v-if="toastMsg" class="toast-bar" aria-live="polite">{{ toastMsg }}</div>
    </Transition>

    <header class="chat-header">
      <div>
        <p class="eyebrow">学习画像数据采集</p>
        <h1>学习背景对话</h1>
      </div>
      <button class="ghost-btn" type="button" @click="router.push('/learning-profile')">返回学习画像</button>
    </header>

    <main class="chat-layout">
      <section class="avatar-panel-card" aria-label="数字人导师">
        <DigitalHumanAvatar
          ref="avatarRef"
          class="chat-avatar"
          @error="handleAvatarError"
        />
      </section>

      <section class="conversation-panel">
        <div class="panel-head">
          <div class="head-icon">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" aria-hidden="true">
              <path d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.86 9.86 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" stroke-linecap="round" stroke-linejoin="round"/>
            </svg>
          </div>
          <div>
            <h2>对话采集</h2>
            <p>围绕专业方向、学习目标、基础水平和薄弱环节补充背景。</p>
          </div>
        </div>

        <div ref="messageListRef" class="message-list" aria-live="polite">
          <div class="message bot">
            <span class="avatar">岐</span>
            <p>请描述你的中医学习背景，比如专业方向、已学课程、当前目标和最想提升的能力。</p>
          </div>
          <div v-for="(message, index) in messages" :key="index" :class="['message', message.role]">
            <span class="avatar">{{ message.role === 'user' ? '你' : '岐' }}</span>
            <p>{{ message.text }}</p>
          </div>
          <div v-if="chatLoading && !streamingReply" class="message bot">
            <span class="avatar">岐</span>
            <p>正在整理...</p>
          </div>
        </div>

        <form class="composer" @submit.prevent="sendChat">
          <label class="sr-only" for="chat-input">输入学习背景</label>
          <textarea
            id="chat-input"
            v-model="chatInput"
            name="chatInput"
            autocomplete="off"
            rows="3"
            placeholder="例如：我是中医学专业大二学生，学过中医基础理论，但八纲辨证和脉诊还不熟..."
            :disabled="chatLoading"
          ></textarea>
          <button class="send-btn" type="submit" :disabled="chatLoading || !chatInput.trim()">发送</button>
        </form>
      </section>
    </main>
  </div>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import DigitalHumanAvatar from '../components/DigitalHumanAvatar.vue'
import { streamLearningProfileBackgroundChat } from '../services/api.js'

const LS_KEY = 'learningProfileData'
const router = useRouter()

const messages = ref([])
const chatInput = ref('')
const chatLoading = ref(false)
const streamingReply = ref(false)
const summaryText = ref('')
const toastMsg = ref('')
const messageListRef = ref(null)
const avatarRef = ref(null)
let toastTimer = null

const userMessages = computed(() => messages.value.filter(message => message.role === 'user'))

function loadProfile() {
  try {
    const raw = localStorage.getItem(LS_KEY)
    return raw ? JSON.parse(raw) : {}
  } catch {
    return {}
  }
}

function saveProfile(patch) {
  localStorage.setItem(LS_KEY, JSON.stringify({ ...loadProfile(), ...patch }))
}

function showToast(msg) {
  toastMsg.value = msg
  clearTimeout(toastTimer)
  toastTimer = setTimeout(() => { toastMsg.value = '' }, 2200)
}

function scrollMessages() {
  nextTick(() => {
    if (messageListRef.value) messageListRef.value.scrollTop = messageListRef.value.scrollHeight
  })
}

function buildLocalSummary() {
  return userMessages.value.map(message => message.text).join('；')
}

function saveSummary(showSavedToast = false) {
  const summary = summaryText.value.trim() || buildLocalSummary()
  if (!summary) return
  saveProfile({ chatBackground: summary, chatTimestamp: Date.now(), aiAnalysis: null })
  if (showSavedToast) showToast('学习背景已保存')
}

async function speakWithAvatar(text) {
  try {
    await avatarRef.value?.speak?.(text)
  } catch {
    // 数字人失败不阻塞文字对话。
  }
}

function handleAvatarError(message) {
  if (message) showToast(message)
}

async function requestAiReply(messageHistory, onDelta) {
  let reply = ''
  let agentResult = null
  await streamLearningProfileBackgroundChat({
    messages: messageHistory,
    currentSummary: summaryText.value,
  }, async ({ event, data }) => {
    if (event === 'delta' && data?.text) {
      reply += String(data.text)
      onDelta(reply)
      scrollMessages()
      return
    }
    if (event === 'result') {
      agentResult = data?.data || data || {}
      const resultReply = String(agentResult.reply || agentResult.question || '').trim()
      if (resultReply && !reply.trim()) {
        reply = resultReply
        onDelta(reply)
        scrollMessages()
      }
      return
    }
    if (event === 'error') {
      throw new Error(data?.message || data?.error || '调用学习背景对话智能体失败')
    }
  })
  if (!reply.trim()) throw new Error('学习背景对话流未返回可显示内容')
  return { ...(agentResult || {}), reply }
}

async function sendChat() {
  const text = chatInput.value.trim()
  if (!text || chatLoading.value) return
  messages.value.push({ role: 'user', text })
  const messageHistory = messages.value.slice()
  const botMessage = { role: 'bot', text: '' }
  messages.value.push(botMessage)
  chatInput.value = ''
  summaryText.value = buildLocalSummary()
  saveSummary(false)
  chatLoading.value = true
  streamingReply.value = true
  scrollMessages()

  try {
    const agentResult = await requestAiReply(messageHistory, (reply) => {
      botMessage.text = reply
    })
    summaryText.value = agentResult.summary || buildLocalSummary()
    saveSummary(false)
    const reply = agentResult.reply || agentResult.question
    speakWithAvatar(reply)
  } catch (error) {
    botMessage.text = error?.message || '调用学习背景对话智能体失败'
  } finally {
    chatLoading.value = false
    streamingReply.value = false
    scrollMessages()
  }
}

onMounted(() => {
  nextTick(async () => {
    try {
      await avatarRef.value?.startAvatar?.()
      await speakWithAvatar('你好，我是你的学习画像数字导师。请在右侧对话框中告诉我你的专业方向、学习目标和薄弱环节。')
    } catch {
      // 页面仍可使用文字对话。
    }
  })
})

onBeforeUnmount(() => {
  avatarRef.value?.destroyAvatar?.()
})
</script>

<style scoped>
.chat-page {
  min-height: 100vh;
  padding: 28px 36px 40px;
  background: #f4faf9;
  box-sizing: border-box;
}

.toast-bar {
  position: fixed;
  top: 20px;
  left: 50%;
  transform: translateX(-50%);
  z-index: 20;
  padding: 12px 22px;
  border-radius: 8px;
  background: #117a51;
  color: #ffffff;
  font-weight: 800;
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

.chat-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 20px;
  margin-bottom: 22px;
}

.eyebrow {
  margin: 0 0 8px;
  color: #117a51;
  font-size: 13px;
  font-weight: 800;
}

h1,
h2,
p {
  margin: 0;
}

h1 {
  color: #1f3f3b;
  font-size: 28px;
  line-height: 1.2;
}

h2 {
  color: #1f3f3b;
  font-size: 20px;
}

.chat-layout {
  display: grid;
  grid-template-columns: minmax(320px, 28%) minmax(0, 1fr);
  gap: 22px;
  align-items: stretch;
  min-height: calc(100vh - 150px);
}

.avatar-panel-card,
.conversation-panel {
  min-height: 620px;
  border: 1px solid #e3edf0;
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.94);
  box-shadow: 0 8px 24px rgba(15, 23, 42, 0.05);
  overflow: hidden;
}

.avatar-panel-card {
  position: relative;
  background:
    linear-gradient(rgba(31, 188, 191, 0.035) 1px, transparent 1px),
    linear-gradient(90deg, rgba(31, 188, 191, 0.035) 1px, transparent 1px),
    #effdfa;
  background-size: 44px 44px;
}

.chat-avatar {
  width: 100%;
  height: 100%;
}

.avatar-panel-card :deep(.avatar-panel) {
  min-height: 620px;
  height: 100%;
  border: none;
  background: transparent;
}

.avatar-panel-card :deep(.avatar-status) {
  top: 16px;
  left: 16px;
}

.conversation-panel {
  display: flex;
  flex-direction: column;
  padding: 28px;
}

.panel-head {
  display: flex;
  align-items: center;
  gap: 14px;
  margin-bottom: 20px;
}

.panel-head p {
  margin-top: 6px;
  color: #64748b;
}

.head-icon {
  display: inline-flex;
  width: 50px;
  height: 50px;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  border-radius: 8px;
  background: #eafff8;
  color: #0f9f9b;
}

.head-icon svg {
  width: 26px;
  height: 26px;
}

.message-list {
  display: flex;
  flex: 1;
  flex-direction: column;
  gap: 12px;
  overflow-y: auto;
  padding: 18px;
  border: 1px solid #e3edf0;
  border-radius: 8px;
  background:
    linear-gradient(rgba(31, 188, 191, 0.035) 1px, transparent 1px),
    linear-gradient(90deg, rgba(31, 188, 191, 0.035) 1px, transparent 1px),
    #f8fffd;
  background-size: 40px 40px;
}

.message {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  max-width: 78%;
}

.message.user {
  align-self: flex-end;
  flex-direction: row-reverse;
}

.avatar {
  display: inline-flex;
  flex-shrink: 0;
  width: 34px;
  height: 34px;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  background: #117a51;
  color: #ffffff;
  font-size: 12px;
  font-weight: 800;
}

.message p {
  padding: 12px 14px;
  border: 1px solid #dbe9eb;
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.94);
  color: #334155;
  line-height: 1.65;
  overflow-wrap: anywhere;
}

.message.user p {
  border-color: #0f9f9b;
  background: #eafff8;
}

.composer {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 96px;
  gap: 12px;
  margin-top: 16px;
}

textarea {
  width: 100%;
  border: 1px solid #d5e4e7;
  border-radius: 8px;
  color: #334155;
  font: inherit;
  line-height: 1.6;
  resize: vertical;
  box-sizing: border-box;
}

textarea:focus-visible,
button:focus-visible {
  outline: 3px solid rgba(31, 188, 191, 0.28);
  outline-offset: 2px;
}

.composer textarea {
  min-height: 76px;
  padding: 12px;
}

.send-btn,
.ghost-btn {
  border-radius: 8px;
  font: inherit;
  font-weight: 800;
  cursor: pointer;
  touch-action: manipulation;
}

.send-btn {
  border: 1px solid #117a51;
  background: #117a51;
  color: #ffffff;
}

.send-btn:disabled {
  border-color: #cbd5e1;
  background: #cbd5e1;
  cursor: not-allowed;
}

.ghost-btn {
  min-height: 42px;
  padding: 0 18px;
  border: 1px solid #b8eadf;
  border-radius: 999px;
  background: #eafff8;
  color: #117a51;
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

@media (prefers-reduced-motion: reduce) {
  .toast-enter-active,
  .toast-leave-active {
    transition: none;
  }
}

@media (max-width: 980px) {
  .chat-page {
    padding: 20px 16px 32px;
  }

  .chat-header {
    align-items: flex-start;
    flex-direction: column;
  }

  .chat-layout {
    grid-template-columns: 1fr;
  }

  .avatar-panel-card,
  .conversation-panel {
    min-height: auto;
  }

  .avatar-panel-card :deep(.avatar-panel) {
    min-height: 520px;
  }

  .composer {
    grid-template-columns: 1fr;
  }

  .send-btn {
    min-height: 44px;
  }
}
</style>
