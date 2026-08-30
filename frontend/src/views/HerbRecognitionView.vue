<template>
  <main class="herb-recognition-page">
    <header class="page-header">
      <div>
        <p>药材图像识别</p>
        <h1>药材识别</h1>
      </div>
    </header>

    <section class="recognition-workspace" aria-label="药材图片识别">
      <div class="input-panel">
        <div class="mode-switch" role="group" aria-label="图片来源与识别方式">
          <button
            type="button"
            :class="{ active: mode === 'upload' }"
            :aria-pressed="mode === 'upload'"
            @click="selectMode('upload')"
          >
            <ImageUp :size="18" aria-hidden="true" />
            导入图片
          </button>
          <button
            type="button"
            :class="{ active: mode === 'camera' }"
            :aria-pressed="mode === 'camera'"
            @click="selectMode('camera')"
          >
            <Camera :size="18" aria-hidden="true" />
            打开摄像头
          </button>
          <button
            type="button"
            :class="{ active: recognitionProvider === 'deepseek' }"
            :aria-pressed="recognitionProvider === 'deepseek'"
            @click="toggleAiCalibration"
          >
            <Crosshair :size="18" aria-hidden="true" />
            AI 校准
          </button>
        </div>

        <div v-if="mode === 'upload'" class="image-stage upload-stage">
          <img v-if="previewUrl" :src="previewUrl" alt="待识别药材图片预览" />
          <label v-else class="upload-placeholder" for="herb-image-input">
            <ImageUp :size="42" stroke-width="1.6" aria-hidden="true" />
            <span>选择药材图片</span>
            <small>JPG、PNG 或 WebP，最大 10 MB</small>
          </label>
          <input
            id="herb-image-input"
            ref="fileInput"
            class="file-input overlay-input"
            type="file"
            accept="image/jpeg,image/png,image/webp"
            aria-label="选择药材图片"
            @change="onFileSelected"
          />
          <button v-if="previewUrl" class="change-image" type="button" @click="openFilePicker">
            <ImageUp :size="16" aria-hidden="true" />
            更换图片
          </button>
        </div>

        <div v-else class="image-stage camera-stage">
          <video v-show="cameraActive && !previewUrl" ref="video" autoplay playsinline muted></video>
          <img v-if="previewUrl" :src="previewUrl" alt="摄像头锁定的药材画面" />
          <div v-if="!cameraActive && !previewUrl" class="camera-placeholder">
            <Camera :size="42" stroke-width="1.6" aria-hidden="true" />
            <span>正在准备摄像头</span>
          </div>
          <button v-if="cameraActive && !previewUrl" class="capture-button" type="button" @click="captureFrame">
            锁定画面
          </button>
          <button v-if="previewUrl" class="change-image" type="button" @click="restartCamera">
            <RefreshCw :size="16" aria-hidden="true" />
            重新拍摄
          </button>
        </div>

        <p v-if="errorMessage" class="inline-message error" role="alert">
          <TriangleAlert :size="17" aria-hidden="true" />
          {{ errorMessage }}
        </p>
        <button class="recognize-button" type="button" :disabled="!selectedFile || isRecognizing" @click="recognize">
          <LoaderCircle v-if="isRecognizing" :size="19" class="spin" aria-hidden="true" />
          <ScanSearch v-else :size="19" aria-hidden="true" />
          {{ isRecognizing ? '识别中' : recognitionProvider === 'deepseek' ? 'AI 校准识别' : '开始识别' }}
        </button>
      </div>

      <aside class="result-panel" aria-live="polite">
        <div class="result-icon">
          <ScanSearch :size="28" stroke-width="1.8" aria-hidden="true" />
        </div>
        <template v-if="resultName">
          <span class="result-label">识别结果</span>
          <strong>{{ resultName }}</strong>
        </template>
        <template v-else-if="isRecognizing">
          <span class="result-label">正在识别</span>
          <strong class="pending-copy">请稍候</strong>
        </template>
        <template v-else>
          <span class="result-label">识别结果</span>
          <strong class="pending-copy">等待图片</strong>
        </template>
      </aside>
    </section>
  </main>
</template>

<script setup>
import { nextTick, onActivated, onBeforeUnmount, onDeactivated, ref } from 'vue'
import { Camera, Crosshair, ImageUp, LoaderCircle, RefreshCw, ScanSearch, TriangleAlert } from 'lucide-vue-next'
import { calibrateHerbWithAi, recognizeHerb } from '../services/api.js'

const ACCEPTED_TYPES = new Set(['image/jpeg', 'image/png', 'image/webp'])
const MAX_FILE_SIZE = 10 * 1024 * 1024

const mode = ref('upload')
const recognitionProvider = ref('local')
const fileInput = ref(null)
const video = ref(null)
const selectedFile = ref(null)
const previewUrl = ref('')
const cameraActive = ref(false)
const isRecognizing = ref(false)
const errorMessage = ref('')
const resultName = ref('')
let stream = null

function resetRecognition() {
  errorMessage.value = ''
  resultName.value = ''
}

function clearPreview() {
  if (previewUrl.value) URL.revokeObjectURL(previewUrl.value)
  previewUrl.value = ''
  selectedFile.value = null
}

function stopCamera() {
  stream?.getTracks().forEach(track => track.stop())
  stream = null
  cameraActive.value = false
}

function openFilePicker() {
  fileInput.value?.click()
}

function validateFile(file) {
  if (!file) return '请选择一张药材图片。'
  if (!ACCEPTED_TYPES.has(file.type)) return '仅支持 JPG、PNG 或 WebP 格式的图片。'
  if (file.size > MAX_FILE_SIZE) return '图片不能超过 10 MB。'
  return ''
}

function setSelectedFile(file) {
  const validationMessage = validateFile(file)
  if (validationMessage) {
    errorMessage.value = validationMessage
    return
  }
  clearPreview()
  selectedFile.value = file
  previewUrl.value = URL.createObjectURL(file)
  resetRecognition()
}

function onFileSelected(event) {
  setSelectedFile(event.target.files?.[0])
  event.target.value = ''
}

async function selectMode(nextMode) {
  if (mode.value === nextMode) return
  mode.value = nextMode
  clearPreview()
  resetRecognition()
  stopCamera()
  if (nextMode === 'camera') await startCamera()
}

function toggleAiCalibration() {
  recognitionProvider.value = recognitionProvider.value === 'deepseek' ? 'local' : 'deepseek'
  resetRecognition()
}

async function startCamera() {
  errorMessage.value = ''
  try {
    stream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: 'environment' }, audio: false })
    await nextTick()
    if (!video.value) return
    video.value.srcObject = stream
    cameraActive.value = true
  } catch {
    stopCamera()
    errorMessage.value = '无法打开摄像头，请检查浏览器权限后重试。'
  }
}

async function restartCamera() {
  clearPreview()
  stopCamera()
  await startCamera()
}

function captureFrame() {
  if (!video.value || !video.value.videoWidth || !video.value.videoHeight) {
    errorMessage.value = '摄像头画面尚未准备好，请稍后再试。'
    return
  }
  const canvas = document.createElement('canvas')
  canvas.width = video.value.videoWidth
  canvas.height = video.value.videoHeight
  canvas.getContext('2d').drawImage(video.value, 0, 0, canvas.width, canvas.height)
  canvas.toBlob((blob) => {
    if (!blob) {
      errorMessage.value = '画面截取失败，请重新拍摄。'
      return
    }
    setSelectedFile(new File([blob], `herb-camera-${Date.now()}.jpg`, { type: 'image/jpeg' }))
    stopCamera()
  }, 'image/jpeg', 0.92)
}

async function recognize() {
  if (!selectedFile.value || isRecognizing.value) return
  isRecognizing.value = true
  resetRecognition()
  try {
    const result = recognitionProvider.value === 'deepseek'
      ? await calibrateHerbWithAi(selectedFile.value)
      : await recognizeHerb(selectedFile.value)
    resultName.value = result?.name || ''
    if (!resultName.value) throw new Error('识别服务没有返回药材名称。')
  } catch (error) {
    errorMessage.value = error?.response?.data?.msg || error?.message || '药材识别失败，请稍后重试。'
  } finally {
    isRecognizing.value = false
  }
}

onBeforeUnmount(() => {
  clearPreview()
  stopCamera()
})

onDeactivated(stopCamera)

onActivated(() => {
  if (mode.value === 'camera' && !previewUrl.value && !cameraActive.value) {
    startCamera()
  }
})
</script>

<style scoped>
.herb-recognition-page {
  min-height: calc(100vh - 72px);
  padding: 48px clamp(24px, 6vw, 104px) 72px;
  background: #f6f8f6;
  box-sizing: border-box;
}

.page-header {
  max-width: 1180px;
  margin: 0 auto 28px;
}

.page-header p,
.result-label {
  margin: 0;
  color: #8d4b3d;
  font-size: 13px;
  font-weight: 750;
  letter-spacing: 0;
}

.page-header h1 {
  margin: 7px 0 0;
  color: #173d2e;
  font-size: 30px;
  line-height: 1.2;
  letter-spacing: 0;
}

.recognition-workspace {
  max-width: 1180px;
  display: grid;
  grid-template-columns: minmax(0, 1.4fr) minmax(280px, 0.6fr);
  gap: 22px;
  margin: 0 auto;
}

.input-panel,
.result-panel {
  border: 1px solid #dde5df;
  border-radius: 8px;
  background: #ffffff;
}

.input-panel {
  padding: 24px;
}

.mode-switch {
  display: inline-grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 4px;
  padding: 4px;
  border: 1px solid #dce5df;
  border-radius: 7px;
  background: #f5f8f6;
}

.mode-switch button,
.change-image,
.capture-button,
.recognize-button {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  border: 0;
  border-radius: 6px;
  font: inherit;
  font-weight: 700;
  cursor: pointer;
}

.mode-switch button {
  min-width: 128px;
  height: 38px;
  padding: 0 12px;
  color: #66736d;
  background: transparent;
}

.mode-switch button.active {
  color: #173d2e;
  background: #ffffff;
  box-shadow: 0 1px 3px rgba(32, 55, 43, 0.14);
}

.image-stage {
  position: relative;
  min-height: 390px;
  display: grid;
  place-items: center;
  margin-top: 20px;
  overflow: hidden;
  border: 1px dashed #b8c8bc;
  border-radius: 7px;
  background: #f8faf8;
}

.image-stage img,
.image-stage video {
  width: 100%;
  height: 390px;
  object-fit: contain;
  background: #17221c;
}

.upload-placeholder,
.camera-placeholder {
  display: grid;
  justify-items: center;
  gap: 12px;
  color: #507065;
  font-weight: 750;
}

.upload-placeholder small {
  color: #7a8580;
  font-size: 13px;
  font-weight: 600;
}

.file-input {
  position: absolute;
  width: 1px;
  height: 1px;
  opacity: 0;
  pointer-events: none;
}

.overlay-input {
  inset: 0;
  width: 100%;
  height: 100%;
  cursor: pointer;
  pointer-events: auto;
}

.change-image,
.capture-button {
  position: absolute;
  bottom: 16px;
  min-height: 38px;
  padding: 0 14px;
  color: #ffffff;
  background: rgba(17, 39, 29, 0.9);
}

.change-image:hover,
.capture-button:hover {
  background: #173d2e;
}

.inline-message {
  display: flex;
  align-items: flex-start;
  gap: 7px;
  min-height: 20px;
  margin: 14px 0 0;
  color: #ae3b34;
  font-size: 14px;
  line-height: 1.45;
}

.recognize-button {
  width: 100%;
  min-height: 46px;
  margin-top: 18px;
  color: #ffffff;
  background: #1f6a4d;
}

.recognize-button:hover:not(:disabled) {
  background: #15563d;
}

.recognize-button:disabled {
  cursor: not-allowed;
  opacity: 0.55;
}

.result-panel {
  min-height: 270px;
  display: grid;
  align-content: center;
  justify-items: center;
  gap: 11px;
  padding: 32px 24px;
  text-align: center;
  box-sizing: border-box;
}

.result-icon {
  width: 62px;
  height: 62px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  color: #1f6a4d;
  background: #e5f0e9;
}

.result-panel strong {
  max-width: 100%;
  overflow-wrap: anywhere;
  color: #173d2e;
  font-size: 32px;
  line-height: 1.25;
}

.result-panel .pending-copy {
  color: #849089;
  font-size: 20px;
  font-weight: 650;
}

.spin {
  animation: spin 0.9s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

@media (max-width: 800px) {
  .herb-recognition-page {
    min-height: 100vh;
    padding: 30px 18px 100px;
  }

  .page-header {
    margin-bottom: 20px;
  }

  .page-header h1 {
    font-size: 26px;
  }

  .recognition-workspace {
    grid-template-columns: 1fr;
    gap: 16px;
  }

  .input-panel {
    padding: 16px;
  }

  .mode-switch {
    width: 100%;
    box-sizing: border-box;
  }

  .mode-switch button {
    min-width: 0;
    padding: 0 3px;
    gap: 4px;
    font-size: 12px;
    white-space: nowrap;
  }

  .image-stage {
    min-height: 280px;
  }

  .image-stage img,
  .image-stage video {
    height: 280px;
  }

  .result-panel {
    min-height: 168px;
    padding: 24px;
  }
}

@media (max-width: 370px) {
  .mode-switch {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .mode-switch button:nth-child(3) {
    grid-column: 1 / -1;
  }
}
</style>
