<template>
  <div class="speech-answer">
    <textarea
      :value="modelValue"
      rows="3"
      placeholder="请输入你的回答，或点击语音回答"
      :disabled="disabled"
      @input="handleInput"
      @keydown.enter.exact.prevent="emitSend"
      @keydown.shift.enter.stop
    ></textarea>

    <div class="speech-row">
      <button
        type="button"
        class="speech-button"
        :disabled="disabled || !supported || listening"
        @click="startRecognition"
      >
        开始语音回答
      </button>
      <button
        type="button"
        class="speech-button secondary"
        :disabled="!listening"
        @click="stopRecognition"
      >
        停止识别
      </button>
      <span class="speech-status" :class="{ error: statusKind === 'error' }">{{ statusLabel }}</span>
    </div>

    <p v-if="interimText" class="interim-text">{{ interimText }}</p>
    <p v-if="!supported" class="speech-hint">当前浏览器不支持语音转文字，请使用 Chrome 或 Edge，或手动输入回答。</p>
    <p v-if="permissionHint" class="speech-hint">{{ permissionHint }}</p>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, ref } from 'vue'

const props = defineProps({
  modelValue: {
    type: String,
    default: '',
  },
  disabled: {
    type: Boolean,
    default: false,
  },
})

const emit = defineEmits(['update:modelValue', 'send', 'status-change'])

const SpeechRecognition = typeof window !== 'undefined'
  ? (window.SpeechRecognition || window.webkitSpeechRecognition)
  : null
const supported = Boolean(SpeechRecognition)
const listening = ref(false)
const status = ref(supported ? 'idle' : 'unsupported')
const interimText = ref('')
const permissionHint = ref('')
let recognition = null

const statusKind = computed(() => (['unsupported', 'denied', 'error'].includes(status.value) ? 'error' : 'normal'))
const statusLabel = computed(() => {
  const labels = {
    idle: '未开启',
    listening: '正在聆听',
    recognizing: '识别中',
    stopped: '已停止',
    unsupported: '浏览器不支持',
    denied: '麦克风权限被拒绝',
    error: '识别失败',
  }
  return labels[status.value] || '未开启'
})

function setStatus(nextStatus, detail = '') {
  status.value = nextStatus
  emit('status-change', { code: nextStatus, label: statusLabel.value, detail })
}

function handleInput(event) {
  emit('update:modelValue', event.target.value)
}

function emitSend() {
  if (props.disabled) return
  emit('send')
}

function appendFinalText(text) {
  const value = String(props.modelValue || '').trim()
  const next = value ? `${value}${/[，。！？,.!?]$/.test(value) ? '' : ' '}${text}` : text
  emit('update:modelValue', next.trim())
}

function ensureRecognition() {
  if (!supported) {
    setStatus('unsupported')
    return null
  }
  if (recognition) return recognition
  recognition = new SpeechRecognition()
  recognition.lang = 'zh-CN'
  recognition.continuous = true
  recognition.interimResults = true

  recognition.onstart = () => {
    listening.value = true
    permissionHint.value = ''
    setStatus('listening')
  }

  recognition.onresult = (event) => {
    let finalText = ''
    let interim = ''
    for (let index = event.resultIndex; index < event.results.length; index += 1) {
      const transcript = event.results[index][0]?.transcript || ''
      if (event.results[index].isFinal) {
        finalText += transcript
      } else {
        interim += transcript
      }
    }
    if (finalText.trim()) {
      appendFinalText(finalText.trim())
    }
    interimText.value = interim.trim()
    setStatus(interimText.value ? 'recognizing' : 'listening')
  }

  recognition.onerror = (event) => {
    listening.value = false
    interimText.value = ''
    if (event.error === 'not-allowed' || event.error === 'service-not-allowed') {
      permissionHint.value = '麦克风权限被拒绝，仍可手动输入回答。'
      setStatus('denied', event.error)
      return
    }
    permissionHint.value = '语音识别失败，仍可手动输入回答。'
    setStatus('error', event.error || '')
  }

  recognition.onend = () => {
    listening.value = false
    interimText.value = ''
    if (!['denied', 'unsupported', 'error'].includes(status.value)) {
      setStatus('stopped')
    }
  }

  return recognition
}

function startRecognition() {
  if (props.disabled || listening.value) return
  const instance = ensureRecognition()
  if (!instance) return
  try {
    interimText.value = ''
    instance.start()
  } catch (error) {
    permissionHint.value = '语音识别暂时无法启动，仍可手动输入回答。'
    setStatus('error', error?.message || '')
  }
}

function stopRecognition() {
  if (!recognition) return
  try {
    recognition.stop()
  } catch {
    // Ignore browser-specific stop errors.
  }
  listening.value = false
  interimText.value = ''
  setStatus('stopped')
}

onBeforeUnmount(() => {
  stopRecognition()
  recognition = null
})

defineExpose({
  stopRecognition,
})
</script>

<style scoped>
.speech-answer {
  display: grid;
  gap: 8px;
}

textarea {
  width: 100%;
  box-sizing: border-box;
  min-height: 76px;
  resize: vertical;
  padding: 10px;
  border: 1px solid rgba(148, 163, 184, 0.32);
  border-radius: 6px;
  background: #f8fafc;
  color: #334155;
  line-height: 1.5;
  outline: none;
}

.speech-row {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
}

.speech-button {
  border: 0;
  border-radius: 6px;
  padding: 8px 10px;
  background: #e0f7f8;
  color: #117a51;
  cursor: pointer;
  font-weight: 700;
}

.speech-button.secondary {
  background: #e2e8f0;
  color: #334155;
}

.speech-button:disabled {
  cursor: not-allowed;
  opacity: 0.48;
}

.speech-status {
  color: #475569;
  font-size: 12px;
}

.speech-status.error,
.speech-hint {
  color: #b91c1c;
}

.interim-text,
.speech-hint {
  margin: 0;
  font-size: 12px;
  line-height: 1.5;
}

.interim-text {
  color: #64748b;
}
</style>
