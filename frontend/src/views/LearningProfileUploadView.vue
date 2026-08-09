<template>
  <div class="upload-page">
    <Transition name="toast">
      <div v-if="toastMsg" class="toast-bar" aria-live="polite">{{ toastMsg }}</div>
    </Transition>

    <header class="page-header">
      <div>
        <p class="eyebrow">学习画像数据采集</p>
        <h1>上传成绩单</h1>
      </div>
      <button class="back-btn" type="button" @click="router.push('/learning-profile')">返回学习画像</button>
    </header>

    <main class="material-layout">
      <section class="material-upload-panel" aria-label="上传材料">
        <div class="panel-title">
          <h2>上传材料</h2>
          <span>{{ uploadItems.length }} 份</span>
        </div>

        <button
          class="material-dropzone"
          type="button"
          :class="{ active: isDragging, 'has-files': uploadItems.length }"
          @dragover.prevent="isDragging = true"
          @dragleave.prevent="isDragging = false"
          @drop.prevent="onDrop"
          @click="triggerUpload"
        >
          <input ref="fileInput" type="file" accept="image/*,.pdf" multiple hidden @change="onFileSelect" />
          <svg viewBox="0 0 24 24" aria-hidden="true">
            <path d="M12 16V4m0 0 4 4m-4-4-4 4M4 16v3a1 1 0 0 0 1 1h14a1 1 0 0 0 1-1v-3" />
          </svg>
          <strong>{{ uploadItems.length ? '继续选择成绩单文件' : '拖拽成绩单到这里，或点击选择文件' }}</strong>
          <span>支持 JPG / PNG / PDF，可一次选择多份文件</span>
        </button>

        <div class="material-file-list" :class="{ empty: !uploadItems.length }">
          <button
            v-for="(item, index) in uploadItems"
            :key="item.id"
            type="button"
            class="file-chip"
            :class="{ active: selectedIndex === index }"
            @click="selectedIndex = index"
          >
            <span class="file-kind">{{ item.kind }}</span>
            <strong>{{ item.file.name }}</strong>
            <em>{{ formatSize(item.file.size) }}</em>
            <i type="button" aria-hidden="true" @click.stop="removeFile(index)">×</i>
          </button>
          <p v-if="!uploadItems.length">上传后，右侧会显示材料预览。</p>
        </div>
      </section>

      <section class="material-preview-panel" aria-label="预览材料">
        <div class="preview-head">
          <h2>预览材料</h2>
          <button class="clear-btn" type="button" :disabled="!uploadItems.length" @click="clearFiles">清空</button>
        </div>

        <div class="material-preview-stage" :class="{ 'has-preview': selectedItem }">
          <template v-if="selectedItem?.previewUrl">
            <img :src="selectedItem.previewUrl" :alt="selectedItem.file.name" />
          </template>
          <template v-else-if="selectedItem">
            <div class="pdf-preview">
              <svg viewBox="0 0 24 24" aria-hidden="true">
                <path d="M7 3h7l5 5v13H7z" />
                <path d="M14 3v5h5" />
                <path d="M10 13h6M10 17h4" />
              </svg>
              <strong>{{ selectedItem.file.name }}</strong>
              <span>{{ selectedItem.kind }} · {{ formatSize(selectedItem.file.size) }}</span>
            </div>
          </template>
          <template v-else>
            <svg viewBox="0 0 24 24" aria-hidden="true">
              <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20M4 19.5A2.5 2.5 0 0 0 6.5 22H20V4H6.5A2.5 2.5 0 0 0 4 6.5v13ZM8 8h8M8 12h7M8 16h5" />
            </svg>
            <strong>材料预览区</strong>
            <span>选择成绩单后，图片将在这里直接预览，PDF 会显示文件信息。</span>
          </template>
        </div>

        <div class="preview-footer">
          <span>{{ uploadItems.length ? '材料已选择，可保存到学习画像' : '尚未选择文件' }}</span>
          <button class="save-btn" type="button" :disabled="!uploadItems.length" @click="submitUpload">保存成绩单</button>
        </div>
      </section>
    </main>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, ref } from 'vue'
import { useRouter } from 'vue-router'

const LS_KEY = 'learningProfileData'
const router = useRouter()
const fileInput = ref(null)
const uploadItems = ref([])
const selectedIndex = ref(0)
const isDragging = ref(false)
const toastMsg = ref('')
let toastTimer = null

const selectedItem = computed(() => uploadItems.value[selectedIndex.value] || null)

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

function triggerUpload() {
  fileInput.value?.click()
}

function onFileSelect(event) {
  addFiles(Array.from(event.target.files || []))
  event.target.value = ''
}

function onDrop(event) {
  isDragging.value = false
  addFiles(Array.from(event.dataTransfer.files || []))
}

function addFiles(files) {
  const accepted = files.filter(file => file.type.startsWith('image/') || file.type === 'application/pdf' || /\.pdf$/i.test(file.name))
  const items = accepted.map(file => ({
    id: `${file.name}-${file.size}-${file.lastModified}-${Math.random().toString(16).slice(2)}`,
    file,
    kind: file.type.startsWith('image/') ? 'IMG' : 'PDF',
    previewUrl: file.type.startsWith('image/') ? URL.createObjectURL(file) : '',
  }))
  uploadItems.value.push(...items)
  if (items.length && uploadItems.value.length === items.length) selectedIndex.value = 0
  if (files.length && !accepted.length) showToast('请选择图片或 PDF 文件')
}

function removeFile(index) {
  const [item] = uploadItems.value.splice(index, 1)
  if (item?.previewUrl) URL.revokeObjectURL(item.previewUrl)
  selectedIndex.value = Math.min(selectedIndex.value, Math.max(uploadItems.value.length - 1, 0))
}

function clearFiles() {
  uploadItems.value.forEach(item => {
    if (item.previewUrl) URL.revokeObjectURL(item.previewUrl)
  })
  uploadItems.value = []
  selectedIndex.value = 0
}

function formatSize(bytes) {
  if (!bytes) return '0 B'
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1048576) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / 1048576).toFixed(1)} MB`
}

function submitUpload() {
  if (!uploadItems.value.length) return
  const fileRecords = uploadItems.value.map(item => ({
    name: item.file.name,
    size: item.file.size,
    type: item.file.type || item.kind,
  }))
  saveProfile({ uploadFiles: fileRecords, uploadTimestamp: Date.now(), aiAnalysis: null })
  showToast('成绩单已保存')
}

onBeforeUnmount(() => {
  clearTimeout(toastTimer)
  uploadItems.value.forEach(item => {
    if (item.previewUrl) URL.revokeObjectURL(item.previewUrl)
  })
})
</script>

<style scoped>
.upload-page {
  min-height: 100vh;
  padding: 28px 36px 40px;
  background:
    linear-gradient(rgba(15, 118, 110, 0.025) 1px, transparent 1px),
    linear-gradient(90deg, rgba(15, 118, 110, 0.025) 1px, transparent 1px),
    #f4faf9;
  background-size: 42px 42px;
  box-sizing: border-box;
  overflow-x: hidden;
}

.toast-bar {
  position: fixed;
  top: 20px;
  left: 50%;
  z-index: 20;
  padding: 12px 22px;
  border-radius: 8px;
  background: #117a51;
  color: var(--surface, rgba(255, 255, 255, 0.94));
  font-weight: 800;
  box-shadow: 0 8px 24px rgba(15, 118, 110, 0.24);
  transform: translateX(-50%);
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

.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 20px;
  margin-bottom: 22px;
}

.eyebrow,
h1,
h2,
p {
  margin: 0;
}

.eyebrow {
  margin-bottom: 8px;
  color: #117a51;
  font-size: 13px;
  font-weight: 800;
}

h1 {
  color: #1f3f3b;
  font-size: 30px;
  line-height: 1.15;
}

h2 {
  color: #1f3f3b;
  font-size: 18px;
  line-height: 1.25;
}

button {
  font: inherit;
  touch-action: manipulation;
}

button:focus-visible {
  outline: 3px solid rgba(31, 188, 191, 0.28);
  outline-offset: 2px;
}

.back-btn,
.clear-btn,
.save-btn,
.material-dropzone,
.file-chip {
  cursor: pointer;
}

.back-btn {
  min-height: 42px;
  padding: 0 18px;
  border: 1px solid #b8eadf;
  border-radius: 999px;
  background: #eafff8;
  color: #117a51;
  font-weight: 800;
}

.upload-page .material-layout {
  display: grid;
  grid-template-columns: minmax(320px, 430px) minmax(0, 1fr);
  gap: 20px;
  height: 690px;
  min-height: 690px;
}

.upload-page .material-upload-panel,
.upload-page .material-preview-panel {
  min-width: 0;
  height: 100%;
  border: 1px solid #b8eadf;
  background: rgba(255, 255, 255, 0.72);
  box-shadow: 0 14px 34px rgba(15, 118, 110, 0.08);
  box-sizing: border-box;
}

.upload-page .material-upload-panel {
  display: flex;
  flex-direction: column;
  gap: 18px;
  padding: 28px;
}

.upload-page .material-preview-panel {
  display: grid;
  grid-template-rows: 78px 1fr 92px;
  overflow: hidden;
}

.panel-title,
.preview-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.panel-title span {
  color: #117a51;
  font-size: 22px;
  font-weight: 900;
}

.upload-page .material-dropzone {
  display: flex;
  min-height: 280px;
  width: 100%;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
  border: 1px dashed #7bd4c5;
  border-radius: 0 !important;
  background:
    linear-gradient(rgba(31, 188, 191, 0.045) 1px, transparent 1px),
    linear-gradient(90deg, rgba(31, 188, 191, 0.045) 1px, transparent 1px),
    linear-gradient(135deg, rgba(234, 255, 248, 0.76), rgba(255, 255, 255, 0.82));
  background-size: 44px 44px, 44px 44px, auto;
  color: #117a51;
  text-align: center;
  transition: border-color 0.18s, background-color 0.18s, transform 0.18s;
}

.upload-page .material-dropzone:hover,
.upload-page .material-dropzone.active {
  border-color: #0f9f9b;
  background-color: #eafff8;
  transform: translateY(-1px);
}

.upload-page .material-dropzone svg {
  width: 44px;
  height: 44px;
  fill: none;
  stroke: currentColor;
  stroke-linecap: round;
  stroke-linejoin: round;
  stroke-width: 1.9;
}

.upload-page .material-dropzone strong {
  color: #123b37;
  font-size: 17px;
  line-height: 1.45;
}

.upload-page .material-dropzone span {
  color: #64748b;
  font-size: 14px;
}

.material-file-list {
  display: grid;
  gap: 10px;
  min-height: 186px;
  align-content: start;
}

.material-file-list.empty {
  align-content: center;
}

.material-file-list p {
  color: #94a3b8;
  text-align: center;
}

.file-chip {
  position: relative;
  display: grid;
  grid-template-columns: 46px minmax(0, 1fr) auto;
  align-items: center;
  gap: 10px;
  min-height: 58px;
  padding: 10px 38px 10px 10px;
  border: 1px solid #d8e8ea;
  border-radius: 0;
  background: var(--surface, rgba(255, 255, 255, 0.94));
  text-align: left;
  transition: border-color 0.18s, background-color 0.18s;
}

.file-chip.active,
.file-chip:hover {
  border-color: #10a99f;
  background: #effff9;
}

.file-kind {
  display: inline-flex;
  width: 40px;
  height: 36px;
  align-items: center;
  justify-content: center;
  background: #dcf8ed;
  color: #117a51;
  font-size: 12px;
  font-weight: 900;
}

.file-chip strong {
  overflow: hidden;
  color: #123b37;
  font-size: 14px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.file-chip em {
  color: #94a3b8;
  font-size: 12px;
  font-style: normal;
  font-variant-numeric: tabular-nums;
}

.file-chip i {
  position: absolute;
  top: 8px;
  right: 10px;
  color: #64748b;
  font-style: normal;
  font-weight: 900;
}

.preview-head {
  padding: 28px 30px 16px;
}

.clear-btn {
  min-height: 34px;
  padding: 0 14px;
  border: 1px solid #cfe3e5;
  border-radius: 999px;
  background: var(--surface, rgba(255, 255, 255, 0.94));
  color: #64748b;
  font-weight: 800;
}

.clear-btn:disabled {
  opacity: 0.42;
  cursor: not-allowed;
}

.material-preview-stage {
  display: flex;
  height: 100%;
  min-height: 0;
  align-items: center;
  justify-content: center;
  margin: 0 30px;
  border: 1px solid #b8eadf;
  background:
    linear-gradient(rgba(31, 188, 191, 0.04) 1px, transparent 1px),
    linear-gradient(90deg, rgba(31, 188, 191, 0.04) 1px, transparent 1px),
    linear-gradient(135deg, rgba(239, 255, 249, 0.9), rgba(255, 255, 255, 0.74));
  background-size: 48px 48px, 48px 48px, auto;
  color: #117a51;
  overflow: hidden;
}

.material-preview-stage > svg {
  width: 58px;
  height: 58px;
  margin-bottom: 14px;
  fill: none;
  stroke: currentColor;
  stroke-linecap: round;
  stroke-linejoin: round;
  stroke-width: 1.7;
}

.material-preview-stage:not(.has-preview) {
  flex-direction: column;
  text-align: center;
}

.material-preview-stage strong {
  color: #123b37;
  font-size: 18px;
}

.material-preview-stage span {
  margin-top: 12px;
  color: #64748b;
  font-size: 14px;
}

.material-preview-stage img {
  display: block;
  width: 100%;
  height: 100%;
  object-fit: contain;
  background: var(--surface, rgba(255, 255, 255, 0.94));
}

.pdf-preview {
  display: flex;
  width: 100%;
  height: 100%;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 10px;
  padding: 30px;
  text-align: center;
}

.pdf-preview svg {
  width: 76px;
  height: 76px;
  fill: none;
  stroke: #8aa1b5;
  stroke-linecap: round;
  stroke-linejoin: round;
  stroke-width: 1.7;
}

.preview-footer {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 190px;
  align-items: center;
  gap: 18px;
  padding: 18px 30px 28px;
}

.preview-footer span {
  color: #64748b;
  font-size: 13px;
  font-weight: 800;
}

.save-btn {
  min-height: 46px;
  border: 1px solid #117a51;
  border-radius: 999px;
  background: #117a51;
  color: var(--surface, rgba(255, 255, 255, 0.94));
  font-weight: 900;
}

.save-btn:disabled {
  border-color: #cbd5e1;
  background: #dce5e5;
  color: #94a3b8;
  cursor: not-allowed;
}

@media (prefers-reduced-motion: reduce) {
  .toast-enter-active,
  .toast-leave-active,
  .material-dropzone,
  .file-chip {
    transition: none;
  }
}

@media (max-width: 980px) {
  .upload-page {
    padding: 20px 16px 32px;
  }

  .page-header {
    align-items: flex-start;
    flex-direction: column;
  }

  .material-layout {
    grid-template-columns: 1fr;
    height: auto;
    min-height: 0;
  }

  .material-preview-panel {
    height: 560px;
    min-height: 560px;
  }

  .preview-footer {
    grid-template-columns: 1fr;
  }
}
</style>
