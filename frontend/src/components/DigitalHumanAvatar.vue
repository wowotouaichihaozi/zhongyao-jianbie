<template>
  <section
    class="avatar-panel"
    @click="resumeFromGesture"
  >
    <div ref="wrapperRef" class="avatar-stage" aria-label="数字人渲染容器"></div>

    <div v-if="showStatus" class="avatar-status" :class="{ error: statusCode === 'error' }">
      {{ status }}
    </div>

    <button v-if="showResume && resumeRequired" class="resume-button" type="button" @click.stop="resumeAvatar">
      点击开启声音
    </button>

    <p v-if="showError && errorMessage" class="avatar-error">{{ errorMessage }}</p>
  </section>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { getAvatarConfig } from '../services/api.js'
import { clearAvatarStage, createAvatarService, normalizeAvatarDom, validateAvatarConfig } from '../services/avatarService.js'
import { createAvatarSessionController } from '../services/avatarSessionManager.js'
import { useAvatarDebug } from '../stores/avatarDebug.js'

defineProps({
  showStatus: {
    type: Boolean,
    default: true,
  },
  showError: {
    type: Boolean,
    default: true,
  },
  showResume: {
    type: Boolean,
    default: true,
  },
})

const emit = defineEmits(['status-change', 'error'])

const wrapperRef = ref(null)
const statusCode = ref('idle')
const errorMessage = ref('')
const resumeRequired = ref(false)
const hasStarted = ref(false)
const audioEnabledByUser = ref(false)
let avatarService = null
let startPromise = null
let pendingSpeechText = ''
let avatarMutationObserver = null
let avatarSessionController = null
let lifecycleVersion = 0

const avatarInstanceId = `avatar-${Date.now()}-${Math.random().toString(16).slice(2)}`

function waitForPreviousSessionRelease() {
  return new Promise(resolve => window.setTimeout(resolve, 180))
}

function invalidateAvatarLifecycle() {
  lifecycleVersion += 1
  return lifecycleVersion
}

function isLifecycleCurrent(version) {
  return lifecycleVersion === version
}

const statusLabels = {
  idle: '未连接',
  'loading-config': '读取配置中',
  ready: '准备连接',
  connecting: '连接中',
  connected: '已连接',
  speaking: '数字人讲话中',
  waiting: '等待用户回答',
  disconnected: '已断开',
  'resume-required': '需要恢复播放',
  destroyed: '已销毁',
  error: '连接错误',
}

const status = computed(() => statusLabels[statusCode.value] || statusCode.value)

function setStatus(code, payload) {
  statusCode.value = code
  resumeRequired.value = code === 'resume-required'
  if (code !== 'error') {
    errorMessage.value = ''
  }
  emit('status-change', { code, label: status.value, payload })
}

function normalizeErrorMessage(error) {
  const raw = error?.message || String(error || '数字人连接失败')
  if (/play\(\) failed|NotAllowedError|not-allowed|autoplay/i.test(raw)) {
    return '浏览器阻止自动播放，请点击恢复播放'
  }
  if (/authentication|auth|1120\d|1006/i.test(raw)) {
    return '数字人服务鉴权或场景授权失败，请检查 API Key、Secret、AppId、接口服务 ID 与形象 ID 是否属于同一服务'
  }
  return raw
}

function handleAvatarError(error) {
  const message = normalizeErrorMessage(error)
  if (isAutoplayError(error)) {
    resumeRequired.value = true
    errorMessage.value = ''
    return
  }
  errorMessage.value = message
  emit('error', message)
}

function isAutoplayError(error) {
  const raw = error?.message || String(error || '')
  return /play\(\) failed|NotAllowedError|not-allowed|autoplay|阻止.*播放|播放.*不允许/i.test(raw)
}

async function startAvatar() {
  if (hasStarted.value && avatarService) {
    return true
  }
  if (startPromise) {
    return startPromise
  }
  if (!wrapperRef.value) {
    throw new Error('数字人渲染容器尚未就绪')
  }

  const version = invalidateAvatarLifecycle()
  avatarSessionController?.claim()

  startPromise = (async () => {
    errorMessage.value = ''
    resumeRequired.value = false
    await waitForPreviousSessionRelease()
    if (!isLifecycleCurrent(version)) return false

    setStatus('loading-config')

    const config = await getAvatarConfig()
    if (!isLifecycleCurrent(version)) return false
    const missing = validateAvatarConfig(config)
    if (missing.length) {
      throw new Error(`数字人配置不完整：缺少 ${missing.join(', ')}`)
    }

    if (!avatarService) {
      avatarService = createAvatarService({
        onStatus: setStatus,
        onError: handleAvatarError,
      })
      await avatarService.init(config)
    }
    if (!isLifecycleCurrent(version)) {
      await avatarService?.destroy()
      avatarService = null
      return false
    }

    wrapperRef.value.replaceChildren()
    await avatarService.start(wrapperRef.value)
    if (!isLifecycleCurrent(version)) {
      await avatarService?.destroy()
      avatarService = null
      return false
    }
    normalizeAvatarDom(wrapperRef.value)
    hasStarted.value = true
    if (audioEnabledByUser.value) {
      await resumeAvatar()
    }
    return true
  })()
  startPromise.catch(() => {})

  try {
    return await startPromise
  } catch (error) {
    if (isAutoplayError(error)) {
      setStatus('resume-required')
      handleAvatarError(error)
      return false
    }
    if (avatarService) {
      try {
        await avatarService.destroy()
      } catch {
        // Keep the original SDK error visible to the caller.
      }
      avatarService = null
      hasStarted.value = false
    }
    clearAvatarStage(wrapperRef.value)
    setStatus('error')
    handleAvatarError(error)
    throw error
  } finally {
    startPromise = null
  }
}

async function speak(text) {
  if (!avatarService || !hasStarted.value) {
    await startAvatar()
  }
  try {
    errorMessage.value = ''
    setStatus('speaking')
    return await avatarService.writeText(text)
  } catch (error) {
    if (isAutoplayError(error)) {
      pendingSpeechText = String(text || '').trim()
      setStatus('resume-required')
      handleAvatarError(error)
      return false
    } else {
      setStatus('error')
    }
    handleAvatarError(error)
    throw error
  }
}

async function interruptAvatar() {
  if (!avatarService) return
  try {
    await avatarService.interrupt()
    setStatus('waiting')
  } catch (error) {
    setStatus('error')
    handleAvatarError(error)
  }
}

async function resumeAvatar() {
  audioEnabledByUser.value = true
  if (!avatarService) return false
  try {
    await avatarService.resumePlayer()
    resumeRequired.value = false
    errorMessage.value = ''
    if (pendingSpeechText) {
      const text = pendingSpeechText
      pendingSpeechText = ''
      setStatus('speaking')
      await avatarService.writeText(text)
    }
    return true
  } catch (error) {
    if (isAutoplayError(error)) {
      setStatus('resume-required')
      handleAvatarError(error)
      return false
    } else {
      setStatus('error')
    }
    handleAvatarError(error)
    return false
  }
}

function resumeFromGesture() {
  resumeAvatar()
}

function stopAvatar() {
  if (!avatarService) return
  avatarService.stop()
}

async function destroyAvatar(options = {}) {
  const { releaseSession = true } = options
  invalidateAvatarLifecycle()
  startPromise = null
  if (!avatarService) {
    hasStarted.value = false
    resumeRequired.value = false
    pendingSpeechText = ''
    clearAvatarStage(wrapperRef.value)
    if (releaseSession) avatarSessionController?.release()
    return
  }
  const currentService = avatarService
  avatarService = null
  hasStarted.value = false
  resumeRequired.value = false
  pendingSpeechText = ''
  if (releaseSession) avatarSessionController?.release()
  await currentService.destroy()
  clearAvatarStage(wrapperRef.value)
}

const { registerAvatarController, unregisterAvatarController } = useAvatarDebug()
const debugController = {
  status,
  resumeRequired,
  actions: {
    start: startAvatar,
    resume: resumeAvatar,
    interrupt: interruptAvatar,
    stop: stopAvatar,
    destroy: destroyAvatar,
  },
}

onMounted(() => {
  avatarSessionController = createAvatarSessionController(avatarInstanceId, () => {
    destroyAvatar({ releaseSession: false }).catch(() => {})
  })
  registerAvatarController(debugController)
  if (wrapperRef.value) {
    avatarMutationObserver = new MutationObserver(() => {
      normalizeAvatarDom(wrapperRef.value)
      if (audioEnabledByUser.value) {
        void avatarService?.resumeRenderedMedia?.()
      }
    })
    avatarMutationObserver.observe(wrapperRef.value, {
      childList: true,
      subtree: true,
      attributes: true,
      attributeFilter: ['style', 'class', 'id'],
    })
  }
})

onBeforeUnmount(() => {
  unregisterAvatarController(debugController)
  avatarMutationObserver?.disconnect()
  avatarMutationObserver = null
  destroyAvatar().finally(() => {
    avatarSessionController?.dispose()
    avatarSessionController = null
  })
})

defineExpose({
  startAvatar,
  speak,
  interruptAvatar,
  destroyAvatar,
  resumeAvatar,
  status,
  statusCode,
  errorMessage,
  resumeRequired,
})
</script>

<style scoped>
.avatar-panel {
  position: relative;
  display: block;
  width: 100%;
  height: 100%;
  min-height: 0;
  overflow: hidden;
  border: 0;
  border-radius: 0;
  background: transparent;
}

.avatar-stage {
  position: absolute;
  inset: 0;
  z-index: 2;
  width: 100%;
  height: 100%;
  overflow: hidden;
  background: transparent;
}

.avatar-stage :deep(> #xvideo),
.avatar-stage :deep(> [id*="xvideo"]),
.avatar-stage :deep(> iframe) {
  display: block !important;
  width: 100% !important;
  height: 100% !important;
  max-width: 100% !important;
  max-height: 100% !important;
  background: transparent !important;
  border: 0 !important;
  overflow: hidden !important;
}

.avatar-stage :deep(> iframe) {
  background: #ffffff !important;
}

.avatar-status {
  position: absolute;
  top: 14px;
  left: 14px;
  z-index: 2;
  padding: 7px 10px;
  border-radius: 6px;
  background: rgba(255, 255, 255, 0.9);
  color: #334155;
  font-size: 13px;
  border: 1px solid rgba(148, 163, 184, 0.32);
}

.avatar-status.error {
  color: #b91c1c;
  border-color: rgba(248, 113, 113, 0.42);
}

.resume-button {
  position: absolute;
  right: 14px;
  top: 14px;
  z-index: 2;
  border: 0;
  border-radius: 6px;
  padding: 8px 12px;
  color: #ffffff;
  background: #0ea5a8;
  cursor: pointer;
  font-weight: 700;
}

.avatar-error {
  position: absolute;
  left: 14px;
  right: 14px;
  bottom: 24px;
  z-index: 2;
  margin: 0;
  padding: 10px 12px;
  border-radius: 6px;
  color: #991b1b;
  background: rgba(254, 242, 242, 0.94);
  border: 1px solid rgba(248, 113, 113, 0.34);
  font-size: 13px;
}

</style>
