<template>
  <section class="camera-analyzer">
    <div class="preview-wrap">
      <video ref="videoRef" autoplay muted playsinline></video>
      <div v-if="!cameraActive" class="preview-placeholder">
        {{ cameraStatusLabel }}
      </div>
    </div>
    <div class="camera-info">
      <div class="camera-status">
        <span class="status-dot" :class="statusClass"></span>
        <strong>{{ cameraStatusLabel }}</strong>
        <span v-if="analysisStatus !== 'idle'" class="analysis-status">{{ analysisStatusLabel }}</span>
      </div>
      <div class="camera-actions">
        <button
          v-if="!cameraActive"
          type="button"
          class="camera-button"
          :disabled="cameraStatus === 'requesting'"
          @click="startCamera"
        >
          {{ cameraOpenButtonLabel }}
        </button>
        <button
          v-else
          type="button"
          class="camera-button secondary"
          :disabled="locked"
          @click="stopCamera"
        >
          关闭摄像头
        </button>
        <button
          type="button"
          class="camera-button test"
          :disabled="!cameraActive || analysisStatus === 'analyzing'"
          @click="testAnalysis"
        >
          测试分析
        </button>
      </div>
      <p v-if="locked" class="camera-lock">
        {{ cameraActive ? '面试进行中，摄像头已开启，暂不能关闭' : '面试进行中，仍可开启摄像头' }}
      </p>
      <p v-if="lastAnalyzedAt">最近分析：{{ lastAnalyzedAt }}</p>
      <p v-if="errorMessage" class="camera-error">{{ errorMessage }}</p>
    </div>
    <canvas ref="canvasRef" width="480" height="360" aria-hidden="true"></canvas>
  </section>
</template>

<script setup>
import { computed, onBeforeUnmount, ref } from 'vue'
import { analyzeInterviewFrame } from '../services/api.js'

const props = defineProps({
  locked: {
    type: Boolean,
    default: false,
  },
})

const emit = defineEmits(['analysis', 'status-change', 'analysis-status-change', 'error'])

const videoRef = ref(null)
const canvasRef = ref(null)
const stream = ref(null)
const cameraStatus = ref('idle')
const analysisStatus = ref('idle')
const errorMessage = ref('')
const lastAnalyzedAt = ref('')
const currentSessionId = ref('')
const currentRound = ref(0)
const isAnalyzing = ref(false)
const isVideoReady = ref(false)
const analyzedRoundKeys = new Set()
let timerId = null

const cameraActive = computed(() => {
  // Keep reactive dependencies while validating the actual browser media state.
  void stream.value
  void isVideoReady.value
  void cameraStatus.value
  return isCameraActuallyActive()
})
const cameraStatusLabel = computed(() => {
  const labels = {
    idle: '未开启',
    requesting: '正在请求权限',
    active: '已开启',
    denied: '权限被拒绝',
    unsupported: '浏览器不支持',
    insecure: '当前环境不支持',
    unavailable: '摄像头不可用',
    stopped: '已关闭',
    error: '摄像头错误',
  }
  return labels[cameraStatus.value] || '未开启'
})
const analysisStatusLabel = computed(() => {
  const labels = {
    idle: '',
    capturing: '正在截图',
    analyzing: '正在分析',
    success: '分析成功',
    failed: '分析失败',
  }
  return labels[analysisStatus.value] || ''
})
const cameraOpenButtonLabel = computed(() => {
  if (cameraStatus.value === 'requesting') return '正在开启...'
  if (cameraStatus.value === 'denied') return '重新授权摄像头'
  return '开启摄像头'
})
function cameraStartErrorMessage(error) {
  const name = error?.name || ''
  const message = error?.message || ''
  if (name === 'NotAllowedError' || name === 'PermissionDeniedError') {
    return {
      status: 'denied',
      message: '摄像头权限被拒绝，请在浏览器地址栏左侧权限设置中允许摄像头访问。',
    }
  }
  if (name === 'NotFoundError' || name === 'DevicesNotFoundError') {
    return {
      status: 'unavailable',
      message: '未检测到可用摄像头，请确认电脑已连接摄像头，并在系统设置中启用。',
    }
  }
  if (name === 'NotReadableError' || name === 'TrackStartError') {
    return {
      status: 'unavailable',
      message: '摄像头被其他应用占用或系统禁止访问，请关闭占用摄像头的软件后重试。',
    }
  }
  if (name === 'OverconstrainedError' || name === 'ConstraintNotSatisfiedError') {
    return {
      status: 'unavailable',
      message: '当前摄像头不支持请求的视频参数，系统已改用默认参数，请稍后重试。',
    }
  }
  if (name === 'SecurityError') {
    return {
      status: 'unavailable',
      message: '浏览器安全策略阻止了摄像头访问，请使用 localhost 或 HTTPS 打开页面。',
    }
  }
  if (message === 'video_not_ready') {
    return {
      status: 'unavailable',
      message: '摄像头已授权但画面未就绪，请稍等片刻后重新开启。',
    }
  }
  return {
    status: 'unavailable',
    message: `摄像头不可用，面试可继续，但不会启用关键帧分析。${name ? `（${name}）` : ''}`,
  }
}
const statusClass = computed(() => {
  if (cameraActive.value) return 'is-ok'
  if (cameraStatus.value === 'requesting') return 'is-busy'
  if (['denied', 'unsupported', 'insecure', 'unavailable', 'error'].includes(cameraStatus.value)) return 'is-error'
  return ''
})

function setCameraStatus(nextStatus, detail = '') {
  cameraStatus.value = nextStatus
  emit('status-change', {
    code: nextStatus,
    label: cameraStatusLabel.value,
    detail,
    enabled: isCameraActuallyActive(),
    videoReady: isVideoReady.value,
  })
}

function setAnalysisStatus(nextStatus, detail = '') {
  analysisStatus.value = nextStatus
  emit('analysis-status-change', {
    code: nextStatus,
    label: analysisStatusLabel.value,
    detail,
  })
}

function formatTime() {
  return new Date().toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit', second: '2-digit' })
}

function stopTimer() {
  if (timerId) {
    clearInterval(timerId)
    timerId = null
  }
}

function releaseCameraStream() {
  stopTimer()
  stopMediaStream(stream.value)
  stream.value = null
  isVideoReady.value = false
  if (videoRef.value) {
    videoRef.value.pause()
    videoRef.value.srcObject = null
    videoRef.value.removeAttribute('src')
    videoRef.value.load()
  }
}

function wait(ms = 0) {
  return new Promise((resolve) => {
    window.setTimeout(resolve, ms)
  })
}

function isDeviceBusyError(error) {
  return error?.name === 'NotReadableError' || error?.name === 'TrackStartError'
}

function stopMediaStream(mediaStream) {
  mediaStream?.getTracks?.().forEach((track) => track.stop())
}

function baseVideoConstraints(extra = {}) {
  return {
    width: { ideal: 640 },
    height: { ideal: 480 },
    frameRate: { ideal: 15, max: 30 },
    ...extra,
  }
}

async function getVideoDevices() {
  if (!navigator.mediaDevices?.enumerateDevices) return []
  const devices = await navigator.mediaDevices.enumerateDevices()
  return devices.filter((device) => device.kind === 'videoinput')
}

async function tryGetUserMedia(constraints, label = 'camera') {
  try {
    const mediaStream = await navigator.mediaDevices.getUserMedia(constraints)
    const [track] = mediaStream.getVideoTracks()
    console.info('[Camera] Opened', {
      label,
      trackLabel: track?.label || '',
      settings: track?.getSettings?.() || {},
    })
    return mediaStream
  } catch (error) {
    console.warn('[Camera] Open failed', {
      label,
      name: error?.name,
      message: error?.message,
    })
    throw error
  }
}

async function requestCameraStream() {
  const attempts = [
    {
      label: 'default',
      constraints: { video: baseVideoConstraints(), audio: false },
    },
    {
      label: 'default-low-resolution',
      constraints: {
        video: baseVideoConstraints({
          width: { ideal: 320 },
          height: { ideal: 240 },
          frameRate: { ideal: 10, max: 15 },
        }),
        audio: false,
      },
    },
  ]
  let lastError = null

  try {
    return await tryGetUserMedia(attempts[0].constraints, attempts[0].label)
  } catch (error) {
    lastError = error
    if (!isDeviceBusyError(error)) {
      throw error
    }
    console.warn('[Camera] Device busy, releasing stale stream and retrying once', {
      name: error?.name,
      message: error?.message,
    })
    releaseCameraStream()
    await wait(600)
  }

  for (const attempt of attempts.slice(1)) {
    try {
      return await tryGetUserMedia(attempt.constraints, attempt.label)
    } catch (error) {
      lastError = error
      if (!isDeviceBusyError(error) && error?.name !== 'OverconstrainedError') {
        throw error
      }
      await wait(250)
    }
  }

  const devices = await getVideoDevices()
  console.info('[Camera] Video devices', devices.map((device) => ({
    label: device.label || '(no label)',
    deviceId: device.deviceId ? `${device.deviceId.slice(0, 6)}...` : '',
  })))

  for (const device of devices) {
    if (!device.deviceId) continue
    try {
      const mediaStream = await tryGetUserMedia({
        video: baseVideoConstraints({
          deviceId: { exact: device.deviceId },
        }),
        audio: false,
      }, device.label || 'video-input')
      return mediaStream
    } catch (error) {
      lastError = error
      if (!isDeviceBusyError(error) && error?.name !== 'OverconstrainedError') {
        throw error
      }
      await wait(250)
    }
  }

  throw lastError || new Error('camera_not_available')
}

function setSessionId(sessionId = '') {
  currentSessionId.value = sessionId || ''
  analyzedRoundKeys.clear()
  if (!currentSessionId.value) {
    stopTimer()
    return
  }
  if (stream.value && currentSessionId.value) {
    startTimer()
  }
}

function isCameraActuallyActive() {
  const mediaStream = stream.value
  const video = videoRef.value
  if (!mediaStream || !video || !video.srcObject) return false
  const liveVideoTrack = mediaStream.getVideoTracks().some((track) => track.readyState === 'live')
  return Boolean(
    liveVideoTrack &&
    video.readyState >= 2 &&
    video.videoWidth > 0 &&
    video.videoHeight > 0 &&
    !video.paused
  )
}

function setCurrentRound(round = 0) {
  const parsed = Number(round)
  currentRound.value = Number.isFinite(parsed) && parsed > 0 ? parsed : currentRound.value
}

function isSecureCameraContext() {
  if (typeof window === 'undefined') return false
  const { protocol, hostname } = window.location
  return protocol === 'https:' || hostname === 'localhost' || hostname === '127.0.0.1' || hostname === '[::1]'
}

async function startCamera(sessionId = '') {
  const nextSessionId = typeof sessionId === 'string' ? sessionId : ''
  currentSessionId.value = nextSessionId || currentSessionId.value
  errorMessage.value = ''
  if (!isSecureCameraContext()) {
    errorMessage.value = '浏览器摄像头需要在 localhost 或 HTTPS 环境下使用。'
    setCameraStatus('unavailable', errorMessage.value)
    emit('error', errorMessage.value)
    return false
  }
  if (!navigator.mediaDevices?.getUserMedia) {
    errorMessage.value = '当前浏览器不支持摄像头调用，请使用 Chrome 或 Edge。'
    setCameraStatus('unavailable', errorMessage.value)
    emit('error', errorMessage.value)
    return false
  }
  if (isCameraActuallyActive()) {
    setCameraStatus('active')
    startTimer()
    return true
  }
  releaseCameraStream()
  setCameraStatus('requesting')
  try {
    stream.value = await requestCameraStream()
    stream.value.getTracks().forEach((track) => {
      track.addEventListener('ended', () => {
        isVideoReady.value = false
        stopTimer()
        setCameraStatus('stopped')
      }, { once: true })
    })
    if (videoRef.value) {
      videoRef.value.srcObject = stream.value
      await videoRef.value.play()
      isVideoReady.value = await waitForVideoReady(2500)
    }
    if (!isCameraActuallyActive()) {
      throw new Error('video_not_ready')
    }
    setCameraStatus('active')
    setAnalysisStatus('idle')
    startTimer()
    return true
  } catch (error) {
    const normalizedError = cameraStartErrorMessage(error)
    errorMessage.value = normalizedError.message
    setCameraStatus(normalizedError.status, errorMessage.value)
    emit('error', errorMessage.value)
    return false
  }
}

function startTimer() {
  stopTimer()
  if (!currentSessionId.value || !isCameraActuallyActive()) return
  timerId = setInterval(() => {
    captureAndAnalyze('timer')
  }, 20000)
}

function stopCamera(force = false) {
  if (props.locked && force !== true) {
    errorMessage.value = '面试进行中，摄像头状态已锁定'
    return
  }
  releaseCameraStream()
  analyzedRoundKeys.clear()
  isAnalyzing.value = false
  setAnalysisStatus('idle')
  setCameraStatus('stopped')
}

function waitForVideoReady(timeoutMs = 1200) {
  return new Promise((resolve) => {
    const video = videoRef.value
    if (!video || !stream.value) {
      resolve(false)
      return
    }
    if (video.readyState >= 2 && video.videoWidth > 0 && video.videoHeight > 0 && !video.paused) {
      isVideoReady.value = true
      resolve(true)
      return
    }
    const cleanup = () => {
      video.removeEventListener('loadedmetadata', onReady)
      video.removeEventListener('canplay', onReady)
      window.clearTimeout(timer)
    }
    const onReady = () => {
      if (video.readyState >= 2 && video.videoWidth > 0 && video.videoHeight > 0) {
        cleanup()
        isVideoReady.value = true
        resolve(true)
      }
    }
    const timer = window.setTimeout(() => {
      cleanup()
      resolve(false)
    }, timeoutMs)
    video.addEventListener('loadedmetadata', onReady)
    video.addEventListener('canplay', onReady)
  })
}

function captureFrame() {
  const video = videoRef.value
  const canvas = canvasRef.value
  if (
    !video ||
    !canvas ||
    !stream.value ||
    !isVideoReady.value ||
    video.readyState < 2 ||
    video.paused ||
    video.videoWidth <= 0 ||
    video.videoHeight <= 0
  ) {
    return ''
  }
  const width = 320
  const ratio = video.videoWidth && video.videoHeight ? video.videoHeight / video.videoWidth : 0.75
  const height = Math.max(180, Math.min(240, Math.round(width * ratio)))
  canvas.width = width
  canvas.height = height
  const ctx = canvas.getContext('2d')
  if (!ctx) return ''
  ctx.drawImage(video, 0, 0, width, height)
  return canvas.toDataURL('image/jpeg', 0.7)
}

function errorPayload(code, message) {
  return { success: false, errorCode: code, error: message, timestamp: new Date().toISOString() }
}

function normalizeFailureMessage(error) {
  const code = error?.response?.data?.errorCode || error?.errorCode || ''
  const raw = error?.response?.data?.error || error?.message || ''
  const map = {
    EMPTY_IMAGE: '关键帧未准备好，请稍后重试。',
    INVALID_IMAGE_BASE64: '关键帧图片格式不正确，请重新采集。',
    IMAGE_TOO_LARGE: '截图过大，已自动降低分辨率后重试。',
    MODEL_CONFIG_MISSING: '讯飞多模态配置缺失，请检查嵌小智模型设置或平台凭据。',
    MODEL_TIMEOUT: 'AI 分析超时，将在下一轮重试。',
    MODEL_PARSE_ERROR: '讯飞模型返回内容解析失败，但面试可以继续。',
    MODEL_AUTH_FAILED: '讯飞模型鉴权失败，请检查嵌小智模型设置或平台凭据。',
    MODEL_ERROR: 'AI 分析暂时不可用，将在下一轮重试。',
    CAMERA_NOT_ENABLED: '摄像头未准备好，请重新开启摄像头。',
    VIDEO_NOT_READY: '关键帧未准备好，请稍后重试。',
    SESSION_NOT_FOUND: '面试会话不存在或已过期，请重新开始面试。',
    API_NOT_FOUND: '关键帧分析接口不存在，请检查后端部署版本。',
    AUTH_EXPIRED: '登录态已失效，请重新登录。',
    NETWORK_ERROR: '网络连接失败，关键帧分析未完成。',
    video_not_ready: '关键帧未准备好，请稍后重试',
    camera_not_enabled: '摄像头未开启，无法进行关键帧分析',
    image_too_large: '图片过大，已自动降低截图质量',
    model_timeout: 'AI 分析超时，将在下一轮重试',
    model_error: 'AI 分析暂时不可用，将在下一轮重试',
    invalid_response: 'AI 分析结果异常，将在下一轮重试',
  }
  return map[code] || raw || '关键帧分析失败，但面试可以继续。'
}

async function captureAndAnalyze(reason = 'manual', options = {}) {
  const round = Number(options.round || currentRound.value || 0)
  const roundKey = round > 0 ? `${currentSessionId.value}:${round}` : ''
  const allowRepeat = Boolean(options.allowRepeat || reason === 'manual-test')
  if (!allowRepeat && roundKey && analyzedRoundKeys.has(roundKey)) return null
  if (!currentSessionId.value && reason !== 'manual-test') return null
  if (!isCameraActuallyActive()) {
    const payload = errorPayload('CAMERA_NOT_ENABLED', '摄像头未准备好，请重新开启摄像头。')
    emit('error', payload)
    return null
  }
  if (isAnalyzing.value) return null
  setAnalysisStatus('capturing', reason)
  const ready = await waitForVideoReady()
  if (!ready) {
    const payload = errorPayload('VIDEO_NOT_READY', '关键帧未准备好，请稍后重试')
    errorMessage.value = payload.error
    emit('error', payload)
    setAnalysisStatus('failed', payload.error)
    return null
  }
  const imageBase64 = captureFrame()
  if (!imageBase64 || !imageBase64.startsWith('data:image/jpeg;base64,') || imageBase64.length < 500) {
    const payload = errorPayload('VIDEO_NOT_READY', '关键帧未准备好，请稍后重试')
    errorMessage.value = payload.error
    emit('error', payload)
    setAnalysisStatus('failed', payload.error)
    return null
  }
  console.log('[FrameCapture]', {
    videoWidth: videoRef.value?.videoWidth || 0,
    videoHeight: videoRef.value?.videoHeight || 0,
    base64Length: imageBase64.length,
    cameraStatus: cameraStatus.value,
    analysisStatus: analysisStatus.value,
  })
  isAnalyzing.value = true
  errorMessage.value = ''
  setAnalysisStatus('analyzing', reason)
  try {
    const result = await analyzeInterviewFrame({
      sessionId: currentSessionId.value,
      round,
      reason,
      imageBase64,
    })
    if (!result?.success) {
      const error = new Error(result?.error || '关键帧分析失败，可继续面试')
      error.errorCode = result?.errorCode || 'MODEL_ERROR'
      throw error
    }
    const payload = {
      success: true,
      analysis: result.analysis || '',
      suggestions: Array.isArray(result.suggestions) ? result.suggestions : [],
      confidence: result.confidence || 'medium',
      presentationScore: result.presentationScore ?? null,
      confidenceSignal: result.confidenceSignal || 'neutral',
      scoreDelta: Number(result.scoreDelta || 0),
      debugOnly: reason === 'manual-test',
      round,
      timestamp: new Date().toISOString(),
    }
    if (!allowRepeat && roundKey) analyzedRoundKeys.add(roundKey)
    lastAnalyzedAt.value = formatTime()
    emit('analysis', payload)
    setAnalysisStatus('success')
    setCameraStatus('active')
    return payload
  } catch (error) {
    console.warn('[AnalyzeFrame Request Failed]', {
      status: error?.response?.status || null,
      errorCode: error?.response?.data?.errorCode || error?.errorCode || 'UNKNOWN',
      error: error?.response?.data?.error || error?.message || '',
    })
    errorMessage.value = normalizeFailureMessage(error)
    emit('error', {
      success: false,
      errorCode: error?.response?.data?.errorCode || error?.errorCode || 'MODEL_ERROR',
      error: errorMessage.value,
      round,
      timestamp: new Date().toISOString(),
    })
    setAnalysisStatus('failed', errorMessage.value)
    if (isCameraActuallyActive()) setCameraStatus('active')
    return null
  } finally {
    isAnalyzing.value = false
  }
}

async function testAnalysis() {
  return captureAndAnalyze('manual-test', {
    round: currentRound.value,
    allowRepeat: true,
  })
}

onBeforeUnmount(() => {
  stopCamera(true)
})

defineExpose({
  setSessionId,
  setCurrentRound,
  startCamera,
  stopCamera,
  captureAndAnalyze,
  testAnalysis,
  isCameraEnabled: () => isCameraActuallyActive(),
  isCameraActuallyActive,
})
</script>

<style scoped>
.camera-analyzer {
  display: grid;
  gap: 8px;
  width: 190px;
  padding: 8px;
  border: 1px solid rgba(148, 163, 184, 0.28);
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.94);
  box-shadow: 0 10px 28px rgba(15, 23, 42, 0.12);
}

.preview-wrap {
  position: relative;
  overflow: hidden;
  aspect-ratio: 4 / 3;
  border-radius: 6px;
  background: #e2e8f0;
}

video {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}

.preview-placeholder {
  position: absolute;
  inset: 0;
  display: grid;
  place-items: center;
  padding: 8px;
  color: #64748b;
  font-size: 12px;
  text-align: center;
  background: #f1f5f9;
}

.camera-info {
  display: grid;
  gap: 4px;
  color: #475569;
  font-size: 12px;
}

.camera-info p {
  margin: 0;
}

.camera-status {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  align-items: center;
}

.analysis-status {
  color: #64748b;
}

.camera-actions {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 6px;
}

.camera-button {
  border: 0;
  border-radius: 6px;
  padding: 7px 6px;
  background: #0ea5a8;
  color: #ffffff;
  cursor: pointer;
  font-size: 12px;
  font-weight: 700;
}

.camera-button.secondary {
  background: #e2e8f0;
  color: #334155;
}

.camera-button:disabled {
  cursor: not-allowed;
  opacity: 0.48;
}

.camera-lock {
  color: #117a51;
}

.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 999px;
  background: #94a3b8;
}

.status-dot.is-ok {
  background: #10b981;
}

.status-dot.is-busy {
  background: #0ea5a8;
}

.status-dot.is-error {
  background: #ef4444;
}

.camera-error {
  color: #b91c1c;
}

canvas {
  display: none;
}
</style>
