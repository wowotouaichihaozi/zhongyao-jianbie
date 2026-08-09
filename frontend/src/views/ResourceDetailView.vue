<template>
  <div class="resource-detail-page">
    <div class="detail-header">
      <button class="back-btn" @click="goBack">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M10 19l-7-7m0 0l7-7m-7 7h18" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>
        返回
      </button>
      <div class="header-info">
        <span class="type-tag">{{ getTypeName(resource.type) }}</span>
        <h1>{{ resource.title }}</h1>
      </div>
    </div>

    <!-- 思维导图 -->
    <div v-if="resource.type === 'mindmap'" class="mindmap-container">
      <div class="mindmap-tree">
        <div ref="mindmapRef" class="mindmap-render"></div>
      </div>
    </div>

    <!-- PPT -->
    <div v-else-if="resource.type === 'ppt'" class="ppt-container">
      <div v-if="isHtmlPpt" class="html-ppt-render" v-html="resource.content"></div>
      <template v-else>
      <div class="slides-wrapper">
        <div class="slide" v-for="(slide, index) in slides" :key="index" v-show="currentSlide === index">
          <h2>{{ slide.title }}</h2>
          <ul>
            <li v-for="(point, i) in slide.points" :key="i">{{ point }}</li>
          </ul>
        </div>
      </div>
      <div class="slide-controls">
        <button class="slide-btn" @click="prevSlide" :disabled="currentSlide === 0">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M15 19l-7-7 7-7" stroke-linecap="round" stroke-linejoin="round"/>
          </svg>
        </button>
        <span class="slide-num">{{ currentSlide + 1 }} / {{ slides.length }}</span>
        <button class="slide-btn" @click="nextSlide" :disabled="currentSlide === slides.length - 1">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M9 5l7 7-7 7" stroke-linecap="round" stroke-linejoin="round"/>
          </svg>
        </button>
      </div>
      </template>
    </div>

    <!-- 视频 -->
    <div v-else-if="resource.type === 'video'" class="video-container">
      <div class="video-layout">
        <div class="video-main">
          <div class="video-iframe-wrap" v-if="currentVideo">
            <iframe
              :src="currentVideo.embedUrl || currentVideo.url"
              scrolling="no"
              frameborder="0"
              allowfullscreen="true"
              class="video-iframe"
            ></iframe>
          </div>
          <div class="video-iframe-wrap video-empty" v-else>
            <div class="empty-placeholder">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                <path d="M15.91 11.672a.375.375 0 010 .656l-5.603 3.113a.375.375 0 01-.557-.328V8.887c0-.286.307-.466.557-.327l5.603 3.112z"/>
                <path d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/>
              </svg>
              <p>请选择一个视频开始播放</p>
            </div>
          </div>
          <div class="video-info" v-if="currentVideo">
            <h3>{{ currentVideo.title }}</h3>
            <span class="video-meta" v-if="currentVideo.author">UP主：{{ currentVideo.author }}</span>
            <span class="video-meta" v-if="currentVideo.duration">　时长：{{ currentVideo.duration }}</span>
          </div>
        </div>
        <div class="video-playlist">
          <h3 class="playlist-heading">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M12 6v6l4 2M22 12a10 10 0 11-20 0 10 10 0 0120 0z"/>
            </svg>
            播放列表
          </h3>
          <ul>
            <li
              v-for="(v, idx) in videoList"
              :key="v.bvid || v.url"
              :class="{ active: currentVideoIndex === idx }"
              @click="playVideo(idx)"
            >
              <span class="pl-index">{{ idx + 1 }}</span>
              <div class="pl-info">
                <span class="pl-title">{{ v.title }}</span>
                <span class="pl-meta" v-if="v.author || v.duration">{{ v.author }}{{ v.author && v.duration ? ' · ' : '' }}{{ v.duration }}</span>
              </div>
            </li>
          </ul>
          <div class="playlist-empty" v-if="!videoList.length">
            <p>暂未搜索到相关视频</p>
          </div>
        </div>
      </div>
      <div class="video-links markdown-content" v-html="renderedContent"></div>
    </div>

    <!-- 代码/练习题 -->
    <div v-else class="content-container">
      <div class="markdown-content" v-html="renderedContent"></div>
    </div>

    <!-- 学习效果评价 -->
    <div class="evaluation-section" v-if="resource.id">
      <div class="evaluation-card">
        <div class="eval-header">
          <h3>学习效果评价</h3>
          <span v-if="isCompleted" class="completed-badge">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
              <path d="M5 13l4 4L19 7" stroke-linecap="round" stroke-linejoin="round"/>
            </svg>
            已学习
          </span>
        </div>

        <div class="eval-body">
          <label class="eval-label">掌握程度</label>
          <div class="star-rating">
            <button
              v-for="star in 5"
              :key="star"
              class="star-btn"
              :class="{ active: rating >= star }"
              @click="!isCompleted && (rating = star)"
              :disabled="isCompleted"
            >
              <svg viewBox="0 0 24 24" :fill="rating >= star ? '#f59e0b' : 'none'" :stroke="rating >= star ? '#f59e0b' : '#cbd5e1'" stroke-width="2">
                <path d="M11.049 2.927c.3-.921 1.603-.921 1.902 0l1.519 4.674a1 1 0 00.95.69h4.915c.969 0 1.371 1.24.588 1.81l-3.976 2.888a1 1 0 00-.363 1.118l1.518 4.674c.3.922-.755 1.688-1.538 1.118l-3.976-2.888a1 1 0 00-1.176 0l-3.976 2.888c-.783.57-1.838-.197-1.538-1.118l1.518-4.674a1 1 0 00-.363-1.118l-3.976-2.888c-.784-.57-.38-1.81.588-1.81h4.914a1 1 0 00.951-.69l1.519-4.674z"/>
              </svg>
            </button>
            <span class="rating-text">{{ ratingLabels[rating - 1] }}</span>
          </div>

          <label class="eval-label">学习心得 <span class="optional">（选填）</span></label>
          <textarea
            v-model="note"
            class="note-input"
            placeholder="记录学习中的收获和疑问..."
            :disabled="isCompleted"
            rows="3"
          ></textarea>
        </div>

        <div class="eval-footer">
          <button
            class="submit-btn"
            :class="{ done: isCompleted }"
            :disabled="isCompleted || evaluationSaving || rating === 0"
            @click="submitEvaluation"
          >
            {{ isCompleted ? '已完成学习' : (evaluationSaving ? '正在记录' : '完成学习') }}
          </button>
          <small v-if="evaluationError" class="evaluation-error">{{ evaluationError }}</small>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, nextTick, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { getLearningFeedback, submitLearningFeedback } from '../services/api.js'

const router = useRouter()
const route = useRoute()
const currentSlide = ref(0)
const mindmapRef = ref(null)

// 视频播放器状态
const currentVideoIndex = ref(0)

const videoList = computed(() => {
  if (resource.value.type !== 'video') return []
  const meta = resource.value.metadata || {}
  const results = meta.results || []
  // 优先使用 metadata 中的结构化数据（只保留有 bvid 的）
  if (results.length) {
    return results
      .filter(item => item.bvid)
      .map(item => ({
        title: item.title || '未知视频',
        url: item.url || '',
        bvid: item.bvid || '',
        embedUrl: item.embedUrl || (item.bvid ? `https://player.bilibili.com/player.html?bvid=${item.bvid}&high_quality=1` : ''),
        snippet: item.snippet || '',
        cover: item.cover || '',
        duration: item.duration || '',
        author: item.author || '',
      }))
  }
  // fallback: 从 markdown content 中解析带 BV 号的链接
  const lines = resource.value.content.split('\n')
  const parsed = []
  for (const line of lines) {
    const m = line.match(/\[([^\]]+)\]\((https?:\/\/[^)]+)\)/)
    if (m) {
      const url = m[2]
      const bvidMatch = url.match(/(BV[\w]{10})/)
      const bvid = bvidMatch ? bvidMatch[1] : ''
      if (!bvid) continue  // 跳过没有 BV 号的链接
      parsed.push({
        title: m[1],
        url,
        bvid,
        embedUrl: `https://player.bilibili.com/player.html?bvid=${bvid}&high_quality=1`,
        snippet: '',
        cover: '',
        duration: '',
        author: '',
      })
    }
  }
  return parsed
})

const currentVideo = computed(() => videoList.value[currentVideoIndex.value] || null)

function playVideo(idx) {
  currentVideoIndex.value = idx
}

const resource = ref({
  id: null,
  title: '',
  description: '',
  type: 'mindmap',
  content: '',
})

// 学习效果评价状态
const rating = ref(0)
const note = ref('')
const isCompleted = ref(false)
const evaluationSaving = ref(false)
const evaluationError = ref('')
const ratingLabels = ['完全不会', '初步了解', '基本掌握', '熟练掌握', '融会贯通']
const feedbackCacheKey = computed(() => `resource-detail-${String(resource.value.id || '').trim()}`)

async function loadMermaid() {
  if (window.mermaid) return window.mermaid
  return new Promise((resolve, reject) => {
    const script = document.createElement('script')
    script.src = 'https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.min.js'
    script.onload = () => {
      window.mermaid.initialize({
        startOnLoad: false,
        theme: 'default',
        securityLevel: 'loose',
        mindmap: {
          useMaxWidth: true,
          htmlLabels: true,
          curve: 'curveBasis'
        }
      })
      resolve(window.mermaid)
    }
    script.onerror = reject
    document.head.appendChild(script)
  })
}

async function renderMindmap() {
  if (resource.value.type !== 'mindmap' || !mindmapRef.value) return
  await nextTick()
  try {
    const mermaid = await loadMermaid()
    const id = 'mindmap-' + Date.now()
    const { svg } = await mermaid.render(id, resource.value.content)
    mindmapRef.value.innerHTML = svg
  } catch (e) {
    mindmapRef.value.innerHTML = `<pre class="mindmap-content">${resource.value.content}</pre>`
  }
}

onMounted(async () => {
  try {
    const saved = localStorage.getItem('currentResourceDetail')
    if (saved) {
      resource.value = JSON.parse(saved)
      await renderMindmap()
      await loadEvaluation()
    } else {
      router.push('/personalized-resources')
    }
  } catch {
    router.push('/personalized-resources')
  }
})

onUnmounted(() => {
})

async function loadEvaluation() {
  if (feedbackCacheKey.value !== 'resource-detail-') {
    try {
      const response = await getLearningFeedback({ cacheKey: feedbackCacheKey.value, limit: 1 })
      const feedback = response?.data?.feedbacks?.[0]
      if (feedback) {
        rating.value = Number(feedback.rating || 0)
        note.value = feedback.note || ''
        isCompleted.value = feedback.outcome === 'completed'
        return
      }
    } catch {
      // Preserve existing local evaluations when the backend is temporarily unavailable.
    }
  }
  try {
    const raw = localStorage.getItem('resourceEvaluations')
    if (!raw) return
    const evaluations = JSON.parse(raw)
    const existing = evaluations.find(e => e.resourceId === resource.value.id)
    if (existing) {
      rating.value = existing.rating
      note.value = existing.note || ''
      isCompleted.value = true
    }
  } catch {}
}

async function submitEvaluation() {
  if (rating.value === 0 || isCompleted.value || evaluationSaving.value) return
  evaluationSaving.value = true
  evaluationError.value = ''

  const evaluation = {
    resourceId: resource.value.id,
    rating: rating.value,
    note: note.value,
    completedAt: new Date().toISOString(),
  }

  try {
    await submitLearningFeedback({
      taskId: String(resource.value.taskId || resource.value.metadata?.taskId || route.query.xzTask || ''),
      cacheKey: feedbackCacheKey.value,
      topic: resource.value.title || '历史学习资源',
      resourceType: resource.value.type || '',
      outcome: 'completed',
      difficulty: rating.value <= 2 ? 'hard' : (rating.value >= 4 ? 'easy' : 'appropriate'),
      helpful: rating.value >= 3,
      rating: rating.value,
      note: note.value,
      route: route.fullPath,
    })

    let evaluations = []
    const raw = localStorage.getItem('resourceEvaluations')
    if (raw) evaluations = JSON.parse(raw)
    evaluations = evaluations.filter(e => e.resourceId !== resource.value.id)
    evaluations.push(evaluation)
    localStorage.setItem('resourceEvaluations', JSON.stringify(evaluations))
    const profileRaw = localStorage.getItem('learningProfileData')
    const profileData = profileRaw ? JSON.parse(profileRaw) : {}
    profileData.resourceEvaluations = evaluations
    localStorage.setItem('learningProfileData', JSON.stringify(profileData))
    isCompleted.value = true
  } catch (error) {
    evaluationError.value = error?.response?.data?.msg || error?.message || '学习反馈记录失败'
  } finally {
    evaluationSaving.value = false
  }
}

watch(() => resource.value.content, async () => {
  await renderMindmap()
})

const cnDigits = { '零':0,'一':1,'二':2,'三':3,'四':4,'五':5,'六':6,'七':7,'八':8,'九':9,'十':10 }
function cnToNum(s) {
  if (!s) return 0
  if (/^\d+$/.test(s)) return parseInt(s)
  if (s === '十') return 10
  if (s.startsWith('十')) return 10 + cnDigits[s[1]]
  if (s.endsWith('十')) return cnDigits[s[0]] * 10
  const a = cnDigits[s[0]], b = cnDigits[s[1]]
  return a * 10 + b
}

const slides = computed(() => {
  if (resource.value.type !== 'ppt') return []
  const content = resource.value.content
  const normalSections = content.split(/\n(?=##\s+)/).filter(part => /^##\s+/.test(part.trim()))
  if (normalSections.length) {
    return normalSections.map(part => {
      const lines = part.split('\n').map(line => line.trim()).filter(Boolean)
      const title = lines[0].replace(/^##\s*/, '').trim()
      const points = lines.slice(1)
        .filter(line => /^[-*]\s+/.test(line))
        .map(line => line.replace(/^[-*]\s+/, ''))
      return { title, points: points.length ? points : lines.slice(1) }
    }).filter(slide => slide.title && slide.points.length)
  }
  const parts = content.split(/##\s*第(?:[一二三四五六七八九十零\d]+)页/).filter(p => p.trim())

  return parts.map(part => {
    const lines = part.split('\n').filter(l => l.trim())
    const title = (lines[0]?.replace(/^[：:：]\s*/, '').trim()) || '幻灯片'
    const points = lines.slice(1)
      .filter(l => l.startsWith('-') || l.startsWith('*'))
      .map(l => l.replace(/^[-*]\s*/, ''))
    return { title, points }
  }).filter(s => s.points.length > 0)
})

const isHtmlPpt = computed(() => {
  return resource.value.type === 'ppt' && /^\s*</.test(resource.value.content || '')
})

function prevSlide() {
  if (currentSlide.value > 0) currentSlide.value--
}

function nextSlide() {
  if (currentSlide.value < slides.value.length - 1) currentSlide.value++
}

const renderedContent = computed(() => {
  let content = resource.value.content
  content = content.replace(/```(\w+)?\n([\s\S]*?)```/g, (_, lang, code) => {
    return `<pre><code class="language-${lang || 'text'}">${escapeHtml(code.trim())}</code></pre>`
  })
  content = content.replace(/^### (.+)$/gm, '<h3>$1</h3>')
  content = content.replace(/^## (.+)$/gm, '<h2>$1</h2>')
  content = content.replace(/^# (.+)$/gm, '<h1>$1</h1>')
  content = content.replace(/\[([^\]]+)\]\((https?:\/\/[^)\s]+|\/[^)\s]+)\)/g, '<a href="$2" target="_blank" rel="noopener noreferrer">$1</a>')
  content = content.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
  content = content.replace(/^- (.+)$/gm, '<li>$1</li>')
  content = content.replace(/(<li>.*<\/li>\n?)+/gs, '<ul>$&</ul>')
  content = content.replace(/\n\n/g, '</p><p>')
  content = `<p>${content}</p>`
  content = content.replace(/---/g, '<hr>')
  return content
})

function escapeHtml(text) {
  const div = document.createElement('div')
  div.textContent = text
  return div.innerHTML
}

function getTypeName(type) {
  const names = {
    document: '课程讲义',
    mindmap: '思维导图',
    ppt: 'PPT',
    video: '视频',
    code: '代码示例',
    quiz: '练习题',
  }
  return names[type] || type
}

function goBack() {
  router.back()
}
</script>

<style scoped>
.resource-detail-page {
  min-height: 100vh;
  background: #f4faf9;
  padding: 24px;
}

.detail-header {
  display: flex;
  align-items: flex-start;
  gap: 20px;
  margin-bottom: 32px;
  max-width: 1200px;
  margin-left: auto;
  margin-right: auto;
}

.back-btn {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 16px;
  background: var(--surface, rgba(255, 255, 255, 0.94));
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  font-size: 14px;
  color: #64748b;
  cursor: pointer;
  transition: all 0.2s;
  flex-shrink: 0;
}

.back-btn:hover {
  border-color: #21b978;
  color: #21b978;
}

.back-btn svg {
  width: 18px;
  height: 18px;
}

.header-info {
  flex: 1;
}

.type-tag {
  display: inline-block;
  padding: 4px 12px;
  background: rgba(31, 188, 191, 0.1);
  color: #117a51;
  border-radius: 4px;
  font-size: 12px;
  font-weight: 500;
  margin-bottom: 8px;
}

.header-info h1 {
  font-size: 24px;
  font-weight: 700;
  color: #1f3f3b;
  margin: 0;
}

.mindmap-container {
  background: var(--surface, rgba(255, 255, 255, 0.94));
  border-radius: 12px;
  padding: 32px;
  max-width: 1200px;
  margin: 0 auto;
  box-shadow: 0 2px 8px rgba(15, 23, 42, 0.04);
  overflow-x: auto;
}

.mindmap-tree {
  background: #f4faf9;
  border-radius: 8px;
  padding: 24px;
}

.mindmap-render {
  width: 100%;
  min-height: 400px;
  display: flex;
  justify-content: center;
  align-items: center;
}

.mindmap-render :deep(svg) {
  max-width: 100%;
  height: auto;
}

.mindmap-content {
  font-family: 'Fira Code', monospace;
  font-size: 14px;
  color: #1f3f3b;
  line-height: 1.8;
  white-space: pre-wrap;
  margin: 0;
}

.ppt-container {
  max-width: 900px;
  margin: 0 auto;
}

.html-ppt-render {
  display: grid;
  gap: 18px;
}

.html-ppt-render :deep(.slide) {
  display: block;
}

.slides-wrapper {
  background: var(--surface, rgba(255, 255, 255, 0.94));
  border-radius: 12px;
  min-height: 400px;
  box-shadow: 0 2px 8px rgba(15, 23, 42, 0.04);
}

.slide {
  padding: 48px;
}

.slide h2 {
  font-size: 28px;
  font-weight: 700;
  color: #1f3f3b;
  margin: 0 0 32px;
  padding-bottom: 16px;
  border-bottom: 2px solid #e2e8f0;
}

.slide ul {
  list-style: none;
  padding: 0;
  margin: 0;
}

.slide li {
  font-size: 18px;
  color: #334155;
  padding: 12px 0;
  padding-left: 24px;
  position: relative;
  line-height: 1.6;
}

.slide li::before {
  content: '';
  position: absolute;
  left: 0;
  top: 18px;
  width: 8px;
  height: 8px;
  background: #21b978;
  border-radius: 50%;
}

.slide-controls {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 20px;
  margin-top: 24px;
}

.slide-btn {
  width: 40px;
  height: 40px;
  border-radius: 8px;
  border: 1px solid #e2e8f0;
  background: var(--surface, rgba(255, 255, 255, 0.94));
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s;
}

.slide-btn:hover:not(:disabled) {
  border-color: #21b978;
  color: #21b978;
}

.slide-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.slide-btn svg {
  width: 20px;
  height: 20px;
}

.slide-num {
  font-size: 14px;
  color: #64748b;
  font-weight: 500;
}

.content-container {
  max-width: 900px;
  margin: 0 auto;
  background: var(--surface, rgba(255, 255, 255, 0.94));
  border-radius: 12px;
  padding: 32px;
  box-shadow: 0 2px 8px rgba(15, 23, 42, 0.04);
}

.markdown-content :deep(h1) {
  font-size: 24px;
  font-weight: 700;
  color: #1f3f3b;
  margin: 0 0 24px;
  padding-bottom: 12px;
  border-bottom: 2px solid #e2e8f0;
}

.markdown-content :deep(h2) {
  font-size: 20px;
  font-weight: 600;
  color: #1f3f3b;
  margin: 32px 0 16px;
}

.markdown-content :deep(h3) {
  font-size: 16px;
  font-weight: 600;
  color: #1f3f3b;
  margin: 24px 0 12px;
}

.markdown-content :deep(p) {
  font-size: 15px;
  color: #334155;
  line-height: 1.7;
  margin: 0 0 16px;
}

.markdown-content :deep(pre) {
  background: #1f2937;
  border-radius: 8px;
  padding: 20px;
  overflow-x: auto;
  margin: 16px 0;
}

.markdown-content :deep(code) {
  font-family: 'Fira Code', monospace;
  font-size: 14px;
  color: #e5e7eb;
  line-height: 1.6;
}

.markdown-content :deep(ul) {
  padding-left: 20px;
  margin: 16px 0;
}

.markdown-content :deep(li) {
  font-size: 15px;
  color: #334155;
  line-height: 1.7;
  margin: 8px 0;
}

.markdown-content :deep(hr) {
  border: none;
  border-top: 1px solid #e2e8f0;
  margin: 32px 0;
}

.markdown-content :deep(strong) {
  color: #1f3f3b;
  font-weight: 600;
}

/* 视频播放器 */
.video-container {
  max-width: 1200px;
  margin: 0 auto;
}

.video-layout {
  display: flex;
  gap: 20px;
  align-items: flex-start;
}

.video-main {
  flex: 1;
  min-width: 0;
}

.video-iframe-wrap {
  width: 100%;
  aspect-ratio: 16 / 9;
  border-radius: 12px;
  overflow: hidden;
  background: #000;
  box-shadow: 0 4px 16px rgba(0,0,0,0.18);
}

.video-iframe {
  width: 100%;
  height: 100%;
  border: none;
}

.video-empty {
  display: flex;
  align-items: center;
  justify-content: center;
}

.empty-placeholder {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
  color: #64748b;
}

.empty-placeholder svg {
  width: 48px;
  height: 48px;
  opacity: 0.4;
}

.empty-placeholder p {
  font-size: 14px;
  margin: 0;
}

.video-info {
  padding: 14px 0 0;
}

.video-info h3 {
  font-size: 17px;
  font-weight: 600;
  color: #1f3f3b;
  margin: 0 0 4px;
}

.video-meta {
  font-size: 13px;
  color: #64748b;
}

/* 播放列表侧栏 */
.video-playlist {
  width: 320px;
  flex-shrink: 0;
  background: var(--surface, rgba(255, 255, 255, 0.94));
  border-radius: 12px;
  box-shadow: 0 2px 8px rgba(15,23,42,0.06);
  overflow: hidden;
  max-height: calc(16 / 9 * 50vw + 60px);
  overflow-y: auto;
}

.playlist-heading {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 15px;
  font-weight: 600;
  color: #1f3f3b;
  margin: 0;
  padding: 16px 18px 12px;
  border-bottom: 1px solid #f1f5f9;
  position: sticky;
  top: 0;
  background: var(--surface, rgba(255, 255, 255, 0.94));
  z-index: 1;
}

.playlist-heading svg {
  width: 18px;
  height: 18px;
  color: #21b978;
}

.video-playlist ul {
  list-style: none;
  margin: 0;
  padding: 0;
}

.video-playlist li {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  padding: 12px 18px;
  cursor: pointer;
  transition: background 0.15s;
  border-bottom: 1px solid #f4faf9;
}

.video-playlist li:last-child {
  border-bottom: none;
}

.video-playlist li:hover {
  background: #f4faf9;
}

.video-playlist li.active {
  background: rgba(31,188,191,0.06);
}

.pl-index {
  width: 24px;
  height: 24px;
  border-radius: 5px;
  background: #f1f5f9;
  color: #64748b;
  font-size: 12px;
  font-weight: 600;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  margin-top: 1px;
  transition: all 0.15s;
}

.video-playlist li.active .pl-index {
  background: #21b978;
  color: var(--surface, rgba(255, 255, 255, 0.94));
}

.pl-info {
  min-width: 0;
}

.pl-title {
  display: block;
  font-size: 13px;
  color: #334155;
  font-weight: 500;
  line-height: 1.4;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.video-playlist li.active .pl-title {
  color: #117a51;
  font-weight: 600;
}

.pl-meta {
  display: block;
  font-size: 12px;
  color: #94a3b8;
  margin-top: 3px;
}

.playlist-empty {
  padding: 32px 18px;
  text-align: center;
  color: #94a3b8;
  font-size: 13px;
}

.playlist-empty p {
  margin: 0;
}

.video-links {
  margin-top: 20px;
}

@media (max-width: 640px) {
  .resource-detail-page {
    padding: 16px;
  }

  .detail-header {
    flex-direction: column;
    gap: 12px;
  }

  .header-info h1 {
    font-size: 20px;
  }

  .slide {
    padding: 24px;
  }

  .slide h2 {
    font-size: 22px;
  }

  .slide li {
    font-size: 16px;
  }

  .content-container {
    padding: 20px;
  }

  .video-container {
    padding: 0;
  }

  .video-layout {
    flex-direction: column;
  }

  .video-playlist {
    width: 100%;
    max-height: 300px;
  }
}

.evaluation-section {
  max-width: 900px;
  margin: 24px auto 0;
}

.evaluation-card {
  background: var(--surface, rgba(255, 255, 255, 0.94));
  border-radius: 12px;
  box-shadow: 0 2px 8px rgba(15, 23, 42, 0.04);
  overflow: hidden;
}

.eval-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 20px 24px 0;
}

.eval-header h3 {
  font-size: 17px;
  font-weight: 600;
  color: #1f3f3b;
  margin: 0;
}

.completed-badge {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 4px 12px;
  background: #10b98118;
  color: #059669;
  border-radius: 20px;
  font-size: 13px;
  font-weight: 600;
}

.completed-badge svg {
  width: 16px;
  height: 16px;
}

.eval-body {
  padding: 20px 24px;
}

.eval-label {
  display: block;
  font-size: 14px;
  font-weight: 500;
  color: #334155;
  margin-bottom: 8px;
}

.eval-label .optional {
  color: #94a3b8;
  font-weight: 400;
}

.star-rating {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 20px;
}

.star-btn {
  background: none;
  border: none;
  padding: 2px;
  cursor: pointer;
  transition: transform 0.15s;
  display: flex;
}

.star-btn:hover:not(:disabled) {
  transform: scale(1.15);
}

.star-btn:disabled {
  cursor: default;
}

.star-btn svg {
  width: 28px;
  height: 28px;
}

.rating-text {
  font-size: 14px;
  color: #64748b;
  margin-left: 4px;
}

.note-input {
  width: 100%;
  padding: 12px 16px;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  font-size: 14px;
  color: #334155;
  background: #f4faf9;
  resize: vertical;
  font-family: inherit;
  line-height: 1.6;
  box-sizing: border-box;
  transition: border-color 0.2s;
}

.note-input:focus {
  outline: none;
  border-color: #21b978;
  background: var(--surface, rgba(255, 255, 255, 0.94));
}

.note-input:disabled {
  background: #f1f5f9;
  color: #94a3b8;
  cursor: not-allowed;
}

.note-input::placeholder {
  color: #94a3b8;
}

.eval-footer {
  padding: 0 24px 20px;
}

.evaluation-error {
  display: block;
  margin-top: 8px;
  color: #b24b3c;
  font-size: 12px;
  line-height: 1.5;
}

.submit-btn {
  width: 100%;
  padding: 12px;
  background: linear-gradient(135deg, #21b978, #117a51);
  color: var(--surface, rgba(255, 255, 255, 0.94));
  border: none;
  border-radius: 8px;
  font-size: 15px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
}

.submit-btn:hover:not(:disabled) {
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(31, 188, 191, 0.3);
}

.submit-btn:disabled {
  cursor: not-allowed;
}

.submit-btn.done {
  background: #f1f5f9;
  color: #94a3b8;
}
</style>
