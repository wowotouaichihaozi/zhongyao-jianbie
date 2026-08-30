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

    <section v-if="resultName" class="analysis-panel" aria-live="polite">
      <header class="analysis-header">
        <div>
          <span>大模型药性分析</span>
          <h2>{{ resultName }}学习要点</h2>
        </div>
        <p v-if="analysisResult">知识库引用 {{ analysisCitations.length }} 条</p>
      </header>

      <div v-if="isAnalyzing" class="analysis-status">
        <LoaderCircle :size="20" class="spin" aria-hidden="true" />
        正在检索知识库并分析药物特性
      </div>
      <div v-else-if="analysisError" class="analysis-status analysis-error" role="alert">
        <TriangleAlert :size="19" aria-hidden="true" />
        <span>{{ analysisError }}</span>
        <button type="button" @click="loadHerbAnalysis(resultName)">重新分析</button>
      </div>
      <div v-else-if="analysisResult" class="analysis-content">
        <article class="agent-explanation">
          <div class="agent-explanation-mark" aria-hidden="true"><BookOpenText :size="20" /></div>
          <div>
            <h3>药物讲解</h3>
            <p>{{ analysisResult.agentExplanation }}</p>
          </div>
        </article>
        <dl>
          <div>
            <dt>来源与药用部位</dt>
            <dd>{{ analysisResult.sourceAndPart }}</dd>
          </div>
          <div>
            <dt>性味归经</dt>
            <dd>{{ analysisResult.natureFlavorMeridians }}</dd>
          </div>
          <div>
            <dt>功效主治</dt>
            <dd><ul><li v-for="item in analysisResult.effectsAndIndications" :key="item">{{ item }}</li></ul></dd>
          </div>
          <div>
            <dt>性状鉴别</dt>
            <dd><ul><li v-for="item in analysisResult.identificationPoints" :key="item">{{ item }}</li></ul></dd>
          </div>
          <div>
            <dt>配伍思路</dt>
            <dd>{{ analysisResult.compatibility }}</dd>
          </div>
          <div>
            <dt>用药注意</dt>
            <dd><ul><li v-for="item in analysisResult.cautions" :key="item">{{ item }}</li></ul></dd>
          </div>
        </dl>
        <p class="learning-tip"><BookOpenText :size="18" aria-hidden="true" />{{ analysisResult.learningTip }}</p>
        <p class="analysis-disclaimer">内容用于中药学学习，不替代药材真伪鉴定、临床诊断或处方建议。</p>
      </div>
    </section>
  </main>
</template>

<script setup>
import { nextTick, onActivated, onBeforeUnmount, onDeactivated, ref } from 'vue'
import { BookOpenText, Camera, Crosshair, ImageUp, LoaderCircle, RefreshCw, ScanSearch, TriangleAlert } from 'lucide-vue-next'
import { analyzeRecognizedHerb, calibrateHerbWithAi, recognizeHerb } from '../services/api.js'

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
const isAnalyzing = ref(false)
const analysisError = ref('')
const analysisResult = ref(null)
const analysisCitations = ref([])
let stream = null
let analysisRequestId = 0

function resetRecognition() {
  analysisRequestId += 1
  errorMessage.value = ''
  resultName.value = ''
  isAnalyzing.value = false
  analysisError.value = ''
  analysisResult.value = null
  analysisCitations.value = []
}

async function loadHerbAnalysis(name) {
  const requestId = ++analysisRequestId
  isAnalyzing.value = true
  analysisError.value = ''
  analysisResult.value = null
  analysisCitations.value = []
  try {
    const data = await analyzeRecognizedHerb(name)
    if (requestId !== analysisRequestId) return
    analysisResult.value = data?.analysis || null
    analysisCitations.value = Array.isArray(data?.citations) ? data.citations : []
    if (!analysisResult.value) throw new Error('大模型未返回可用的药性分析。')
  } catch (error) {
    if (requestId !== analysisRequestId) return
    analysisError.value = error?.response?.data?.msg || error?.message || '大模型药性分析不可用，请稍后重试。'
  } finally {
    if (requestId === analysisRequestId) isAnalyzing.value = false
  }
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
    loadHerbAnalysis(resultName.value)
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
  height: calc(100vh - 72px);
  min-height: 0;
  padding: 48px clamp(24px, 6vw, 104px) 72px;
  background: #f6f8f6;
  box-sizing: border-box;
  overflow-x: hidden;
  overflow-y: auto;
  overscroll-behavior: contain;
  scrollbar-gutter: stable;
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

.analysis-panel {
  max-width: 1180px;
  margin: 22px auto 0;
  padding: 28px 30px;
  border: 1px solid #dde5df;
  border-radius: 8px;
  background: #ffffff;
  box-sizing: border-box;
}

.analysis-header {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 20px;
  padding-bottom: 18px;
  border-bottom: 1px solid #e7ece8;
}

.analysis-header span {
  color: #8d4b3d;
  font-size: 13px;
  font-weight: 750;
}

.analysis-header h2 {
  margin: 5px 0 0;
  color: #173d2e;
  font-size: 22px;
}

.analysis-header p {
  margin: 0;
  color: #718078;
  font-size: 13px;
}

.analysis-status {
  min-height: 130px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 9px;
  color: #52655b;
  font-size: 15px;
}

.analysis-error {
  color: #ae3b34;
}

.analysis-error button {
  margin-left: 8px;
  padding: 7px 12px;
  border: 1px solid #cfdbd3;
  border-radius: 6px;
  color: #173d2e;
  background: #ffffff;
  font: inherit;
  font-weight: 700;
  cursor: pointer;
}

.analysis-content dl {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0 36px;
  margin: 0;
}

.agent-explanation {
  display: grid;
  grid-template-columns: 42px minmax(0, 1fr);
  gap: 14px;
  padding: 22px 0 20px;
  border-bottom: 1px solid #dfe8e2;
}

.agent-explanation-mark {
  width: 42px;
  height: 42px;
  display: grid;
  place-items: center;
  border-radius: 50%;
  color: #ffffff;
  background: #1f6a4d;
}

.agent-explanation h3 {
  margin: 0 0 7px;
  color: #173d2e;
  font-size: 16px;
}

.agent-explanation p {
  margin: 0;
  color: #43564d;
  font-size: 15px;
  line-height: 1.85;
}

.analysis-content dl > div {
  padding: 20px 0;
  border-bottom: 1px solid #edf1ee;
}

.analysis-content dt {
  margin-bottom: 8px;
  color: #315847;
  font-size: 14px;
  font-weight: 800;
}

.analysis-content dd,
.analysis-content ul {
  margin: 0;
  color: #4c5c54;
  font-size: 14px;
  line-height: 1.75;
}

.analysis-content ul {
  padding-left: 18px;
}

.learning-tip {
  display: flex;
  align-items: flex-start;
  gap: 9px;
  margin: 22px 0 0;
  padding: 13px 15px;
  color: #315847;
  background: #f3f7f4;
  font-size: 14px;
  line-height: 1.6;
}

.learning-tip svg {
  flex: 0 0 auto;
  margin-top: 2px;
}

.analysis-disclaimer {
  margin: 12px 0 0;
  color: #849089;
  font-size: 12px;
}

.spin {
  animation: spin 0.9s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

@media (max-width: 800px) {
  .herb-recognition-page {
    height: calc(100vh - 88px);
    min-height: 0;
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

  .analysis-panel {
    margin-top: 16px;
    padding: 22px 18px;
  }

  .analysis-header {
    align-items: flex-start;
    flex-direction: column;
    gap: 8px;
  }

  .analysis-content dl {
    grid-template-columns: 1fr;
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
