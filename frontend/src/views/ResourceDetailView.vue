<template>
  <main class="resource-detail-page">
    <header class="detail-header">
      <button type="button" class="icon-button back-button" aria-label="返回个性化资源" title="返回个性化资源" @click="goBack">
        <ArrowLeft :size="20" aria-hidden="true" />
      </button>
      <div class="header-copy">
        <div class="header-meta">
          <span v-if="resource.id" class="type-tag">{{ resourceTypeName(resource.type) }}</span>
          <span v-if="sourceMode === 'task'" class="source-tag"><Database :size="14" />任务记录</span>
          <span v-else-if="sourceMode === 'legacy'" class="source-tag legacy"><HardDrive :size="14" />本机历史</span>
        </div>
        <h1>{{ resource.title || stateTitle }}</h1>
        <p v-if="resource.description">{{ resource.description }}</p>
      </div>
      <RouterLink class="header-link" to="/personalized-resources">
        <Library :size="17" aria-hidden="true" />资源库
      </RouterLink>
    </header>

    <section v-if="viewState === 'loading'" class="state-panel" aria-live="polite">
      <LoaderCircle class="spin" :size="28" aria-hidden="true" />
      <h2>正在恢复资源记录</h2>
      <p>正在读取对应任务及其审核证据。</p>
    </section>

    <section v-else-if="viewState === 'error'" class="state-panel error-state" role="alert">
      <CircleAlert :size="30" aria-hidden="true" />
      <h2>{{ stateTitle }}</h2>
      <p>{{ loadError }}</p>
      <div class="state-actions">
        <button type="button" class="primary-button" @click="loadResource"><RefreshCw :size="17" />重试</button>
        <RouterLink class="secondary-button" to="/personalized-resources">返回资源库</RouterLink>
      </div>
    </section>

    <template v-else>
      <div v-if="sourceMode === 'legacy'" class="legacy-notice" role="status">
        <Info :size="18" aria-hidden="true" />
        <span>该记录来自当前浏览器的历史缓存，任务运行证据可能不完整。</span>
      </div>

      <div class="detail-layout">
        <section class="artifact-column" aria-label="生成资源内容">
          <div v-if="!hasRenderableContent" class="content-empty">
            <FileQuestion :size="30" aria-hidden="true" />
            <h2>资源内容未返回</h2>
            <p>任务记录存在，但当前产物没有可展示的正文。</p>
          </div>

          <div v-else-if="resource.type === 'mindmap'" class="artifact-surface mindmap-surface">
            <div v-if="mermaidSource" ref="mindmapRef" class="mindmap-render" aria-label="思维导图"></div>
            <div v-else class="markdown-content mindmap-markdown" v-html="renderedContent"></div>
            <div v-if="mindmapError" class="render-warning" role="status">
              <TriangleAlert :size="17" />图形渲染失败，已显示安全原文。
            </div>
          </div>

          <div v-else-if="resource.type === 'ppt' && isHtmlPpt" class="artifact-surface ppt-html-surface">
            <iframe
              class="ppt-frame"
              :srcdoc="sandboxedPptDocument"
              sandbox=""
              title="生成的 HTML PPT 预览"
            ></iframe>
            <p class="sandbox-note"><ShieldCheck :size="15" />课件在禁用脚本与网络请求的沙箱中预览</p>
          </div>

          <div v-else-if="resource.type === 'ppt'" class="artifact-surface ppt-surface">
            <template v-if="slides.length">
              <article class="slide">
                <span class="slide-kicker">SLIDE {{ currentSlide + 1 }}</span>
                <h2>{{ slides[currentSlide].title }}</h2>
                <ul>
                  <li v-for="(point, index) in slides[currentSlide].points" :key="index">{{ point }}</li>
                </ul>
              </article>
              <nav class="slide-controls" aria-label="PPT 翻页">
                <button type="button" class="icon-button" aria-label="上一页" title="上一页" :disabled="currentSlide === 0" @click="currentSlide -= 1">
                  <ChevronLeft :size="20" />
                </button>
                <span>{{ currentSlide + 1 }} / {{ slides.length }}</span>
                <button type="button" class="icon-button" aria-label="下一页" title="下一页" :disabled="currentSlide === slides.length - 1" @click="currentSlide += 1">
                  <ChevronRight :size="20" />
                </button>
              </nav>
            </template>
            <div v-else class="content-empty compact">
              <FileQuestion :size="28" />
              <h2>没有可用幻灯片</h2>
            </div>
          </div>

          <div v-else-if="resource.type === 'video'" class="artifact-surface video-surface">
            <div class="video-layout">
              <div class="video-main">
                <div v-if="currentVideo" class="video-frame-wrap">
                  <iframe
                    class="video-frame"
                    :src="currentVideo.embedUrl || currentVideo.url"
                    :title="currentVideo.title || '学习视频'"
                    referrerpolicy="no-referrer"
                    allow="fullscreen"
                    allowfullscreen
                  ></iframe>
                </div>
                <div v-else class="content-empty compact">
                  <VideoOff :size="28" />
                  <h2>没有可播放视频</h2>
                </div>
                <h2 v-if="currentVideo" class="video-title">{{ currentVideo.title }}</h2>
                <p v-if="currentVideo?.author || currentVideo?.duration" class="video-meta">
                  {{ [currentVideo.author, currentVideo.duration].filter(Boolean).join(' · ') }}
                </p>
              </div>
              <div v-if="videoList.length" class="video-playlist" aria-label="播放列表">
                <button
                  v-for="(video, index) in videoList"
                  :key="video.bvid || video.url || index"
                  type="button"
                  :class="['playlist-item', { active: index === currentVideoIndex }]"
                  :aria-pressed="index === currentVideoIndex"
                  @click="currentVideoIndex = index"
                >
                  <span>{{ index + 1 }}</span>
                  <span><strong>{{ video.title }}</strong><small>{{ [video.author, video.duration].filter(Boolean).join(' · ') }}</small></span>
                </button>
              </div>
            </div>
            <div class="markdown-content video-notes" v-html="renderedContent"></div>
          </div>

          <div v-else-if="resource.type === 'generated_video' && generatedVideoUrl" class="artifact-surface generated-video-surface">
            <video :src="generatedVideoUrl" :poster="generatedVideoPoster" controls preload="metadata">
              当前浏览器无法播放该视频。
            </video>
          </div>

          <div v-else class="artifact-surface markdown-content" v-html="renderedContent"></div>

          <section v-if="hasRenderableContent" class="feedback-panel" aria-labelledby="feedback-title">
            <div class="section-heading">
              <div>
                <span class="eyebrow">LEARNING CHECK</span>
                <h2 id="feedback-title">学习验证</h2>
              </div>
              <span v-if="savedOutcome" :class="['feedback-status', savedOutcome]">{{ outcomeLabel(savedOutcome) }}</span>
            </div>

            <template v-if="!savedOutcome">
              <fieldset class="outcome-control">
                <legend>本次学习结果</legend>
                <button type="button" :class="{ selected: feedbackOutcome === 'completed' }" :aria-pressed="feedbackOutcome === 'completed'" @click="feedbackOutcome = 'completed'">
                  <CheckCircle2 :size="18" />完成学习
                </button>
                <button type="button" :class="{ selected: feedbackOutcome === 'needs_review' }" :aria-pressed="feedbackOutcome === 'needs_review'" @click="feedbackOutcome = 'needs_review'">
                  <RotateCcw :size="18" />需要巩固
                </button>
                <button type="button" :class="{ selected: feedbackOutcome === 'blocked' }" :aria-pressed="feedbackOutcome === 'blocked'" @click="feedbackOutcome = 'blocked'">
                  <CircleAlert :size="18" />遇到阻塞
                </button>
              </fieldset>

              <div class="rating-field">
                <span>掌握程度</span>
                <div class="star-rating">
                  <button
                    v-for="star in 5"
                    :key="star"
                    type="button"
                    :aria-label="`${star} 星：${ratingLabels[star - 1]}`"
                    :aria-pressed="rating === star"
                    @click="rating = star"
                  >
                    <Star :size="25" :fill="rating >= star ? '#e0a11b' : 'none'" :color="rating >= star ? '#e0a11b' : '#a9b2b0'" />
                  </button>
                  <span>{{ rating ? ratingLabels[rating - 1] : '请选择' }}</span>
                </div>
              </div>

              <label class="note-field">
                <span>学习备注 <small>选填</small></span>
                <textarea v-model="note" rows="3" placeholder="记录已掌握的内容、疑问或需要继续练习的部分"></textarea>
              </label>

              <div class="feedback-submit-row">
                <button type="button" class="primary-button" :disabled="evaluationSaving || !feedbackOutcome || !rating" @click="submitEvaluation">
                  <LoaderCircle v-if="evaluationSaving" class="spin" :size="17" />
                  <Send v-else :size="17" />
                  {{ evaluationSaving ? '正在记录' : '提交学习反馈' }}
                </button>
                <span class="privacy-note"><ShieldCheck :size="15" />反馈将用于效果评估与后续路径建议</span>
              </div>
              <p v-if="evaluationError" class="inline-error" role="alert">{{ evaluationError }}</p>
            </template>

            <div v-else class="feedback-result" aria-live="polite">
              <CheckCircle2 v-if="savedOutcome === 'completed'" :size="22" />
              <RotateCcw v-else-if="savedOutcome === 'needs_review'" :size="22" />
              <CircleAlert v-else :size="22" />
              <div>
                <strong>{{ feedbackMessage || '学习反馈已记录。' }}</strong>
                <p v-if="nextActions.length">{{ nextActions.join('；') }}</p>
                <div class="next-actions">
                  <RouterLink class="primary-button" :to="feedbackNextRoute">查看效果评估<ArrowRight :size="16" /></RouterLink>
                  <RouterLink class="secondary-button" to="/learning-path/stage/overview">返回学习路径</RouterLink>
                  <RouterLink v-if="savedOutcome !== 'completed'" class="secondary-button" to="/smart-tutor">向智能导师求助</RouterLink>
                </div>
              </div>
            </div>
          </section>
        </section>

        <aside class="evidence-column" aria-label="生成依据与可信度">
          <section class="evidence-panel">
            <div class="section-heading compact-heading">
              <div>
                <span class="eyebrow">EVIDENCE</span>
                <h2>生成依据</h2>
              </div>
              <span v-if="Number.isFinite(resource.matchScore)" class="score-badge">匹配 {{ resource.matchScore }}%</span>
            </div>
            <dl class="evidence-list">
              <div><dt>画像版本</dt><dd>{{ profileReportLabel }}</dd></div>
              <div><dt>目标薄弱点</dt><dd>{{ weakPoints.length ? weakPoints.join('、') : '未返回' }}</dd></div>
              <div><dt>生成策略</dt><dd>{{ plannerStrategy || '未返回' }}</dd></div>
            </dl>
          </section>

          <section class="evidence-panel">
            <div class="section-heading compact-heading">
              <div>
                <span class="eyebrow">ORCHESTRATION</span>
                <h2>智能体协作</h2>
              </div>
              <span class="count-badge">{{ handoffLabel }}</span>
            </div>
            <dl class="evidence-list">
              <div><dt>总控智能体</dt><dd>{{ rootAgentLabel }}</dd></div>
              <div><dt>资源智能体</dt><dd>{{ specialistAgentLabel }}</dd></div>
              <div><dt>运行编号</dt><dd class="mono">{{ runId || '未返回' }}</dd></div>
              <div><dt>Skill</dt><dd>{{ harness.skillId || '未返回' }}</dd></div>
              <div><dt>MCP</dt><dd>{{ mcpLabel }}</dd></div>
            </dl>
          </section>

          <section :class="['evidence-panel', 'quality-panel', { warning: verificationRequired || reviewFailed }]">
            <div class="section-heading compact-heading">
              <div>
                <span class="eyebrow">QUALITY</span>
                <h2>质量与核验</h2>
              </div>
              <span :class="['review-badge', reviewTone]">{{ reviewLabel }}</span>
            </div>
            <div v-if="qualityScore !== null" class="quality-score"><strong>{{ qualityScore }}</strong><span>/ 100</span></div>
            <dl class="criteria-list">
              <div v-for="criterion in qualityCriteria" :key="criterion.name">
                <dt>{{ criterionLabel(criterion.name) }}</dt><dd>{{ criterion.value }}</dd>
              </div>
              <div v-if="!qualityCriteria.length"><dt>评价明细</dt><dd>未返回</dd></div>
            </dl>
            <p v-if="verificationRequired" class="verification-warning"><TriangleAlert :size="17" />部分内容缺少直接依据，请结合经典医籍、教材或课程资料核验。</p>
          </section>

          <section class="evidence-panel sources-panel">
            <div class="section-heading compact-heading">
              <div>
                <span class="eyebrow">GROUNDING</span>
                <h2>知识来源</h2>
              </div>
              <span class="count-badge">{{ knowledgeSources.length }} 条</span>
            </div>
            <ol v-if="knowledgeSources.length" class="source-list">
              <li v-for="(source, index) in knowledgeSources" :key="source.id || source.source || index">
                <span>{{ index + 1 }}</span>
                <div><strong>{{ source.title || source.name || source.source || `来源 ${index + 1}` }}</strong><small>{{ sourceLocator(source) }}</small></div>
              </li>
            </ol>
            <p v-else class="evidence-empty">任务未返回可展示的知识来源，当前内容标记为待核验。</p>
          </section>
        </aside>
      </div>
    </template>
  </main>
</template>

<script setup>
import { computed, nextTick, onMounted, ref, watch } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'
import {
  ArrowLeft,
  ArrowRight,
  CheckCircle2,
  ChevronLeft,
  ChevronRight,
  CircleAlert,
  Database,
  FileQuestion,
  HardDrive,
  Info,
  Library,
  LoaderCircle,
  RefreshCw,
  RotateCcw,
  Send,
  ShieldCheck,
  Star,
  TriangleAlert,
  VideoOff,
} from 'lucide-vue-next'
import { getLearningFeedback, getXiaoZhiTask, submitLearningFeedback } from '../services/api.js'
import {
  findTaskResource,
  resourceContentText,
  resourceKnowledgeSources,
  resourceQuality,
  resourceTypeName,
  taskIdFromResourceId,
} from '../utils/personalizedResourceHistory.js'
import { buildSandboxedHtmlDocument, mermaidMindmapSource, renderSafeMarkdown, safeResourceHref } from '../utils/resourceMarkdown.js'

const route = useRoute()
const router = useRouter()
const currentSlide = ref(0)
const currentVideoIndex = ref(0)
const evaluationSaving = ref(false)
const evaluationError = ref('')
const feedbackOutcome = ref('completed')
const feedbackMessage = ref('')
const feedbackNextRoute = ref('/effect-assessment?section=feedback')
const mindmapError = ref(false)
const mindmapRef = ref(null)
const nextActions = ref([])
const note = ref('')
const orchestrationRuns = ref([])
const rating = ref(0)
const savedOutcome = ref('')
const sourceMode = ref('')
const viewState = ref('loading')
const loadError = ref('')
const resource = ref({ id: '', title: '', description: '', type: '', content: '', metadata: {} })

const ratingLabels = ['完全不会', '初步了解', '基本掌握', '熟练掌握', '融会贯通']
const feedbackCacheKey = computed(() => `resource-detail:${String(resource.value.id || '').trim()}`)
const contentText = computed(() => resourceContentText(resource.value))
const hasRenderableContent = computed(() => Boolean(contentText.value.trim()) || Boolean(generatedVideoUrl.value))
const renderedContent = computed(() => renderSafeMarkdown(contentText.value))
const mermaidSource = computed(() => resource.value.type === 'mindmap' ? mermaidMindmapSource(contentText.value) : '')
const isHtmlPpt = computed(() => resource.value.type === 'ppt' && /^\s*</.test(contentText.value))
const sandboxedPptDocument = computed(() => buildSandboxedHtmlDocument(contentText.value))
const knowledgeSources = computed(() => resourceKnowledgeSources(resource.value))
const quality = computed(() => resourceQuality(resource.value))
const qualityScore = computed(() => {
  const value = quality.value.score
  if (value === null || value === undefined || value === '') return null
  const number = Number(value)
  return Number.isFinite(number) ? number : null
})
const qualityCriteria = computed(() => Object.entries(objectValue(quality.value.criteria)).map(([name, value]) => ({ name, value })))
const verificationRequired = computed(() => quality.value.verificationRequired === true || knowledgeSources.value.length === 0)
const reviewFailed = computed(() => quality.value.passed === false || ['failed', 'rejected'].includes(String(quality.value.reviewStatus || '').toLowerCase()))
const reviewTone = computed(() => reviewFailed.value ? 'failed' : (verificationRequired.value ? 'warning' : (quality.value.passed === true ? 'passed' : 'neutral')))
const reviewLabel = computed(() => {
  if (reviewFailed.value) return '未通过'
  if (verificationRequired.value) return '待核验'
  if (quality.value.passed === true) return '已通过'
  return '未返回'
})

const metadata = computed(() => objectValue(resource.value.metadata))
const planner = computed(() => objectValue(metadata.value.planner))
const weakPoints = computed(() => listValue(planner.value.targetWeakPoints).map(String).filter(Boolean))
const plannerStrategy = computed(() => String(planner.value.strategy || ''))
const matchedRun = computed(() => {
  const runId = String(metadata.value.runId || '')
  return orchestrationRuns.value.find(run => String(run?.runId || '') === runId) || orchestrationRuns.value[0] || {}
})
const runId = computed(() => String(matchedRun.value.runId || metadata.value.runId || ''))
const harness = computed(() => objectValue(matchedRun.value.harness))
const rootAgentLabel = computed(() => String(matchedRun.value.rootAgent || metadata.value.rootAgent || resource.value.agent || '未返回'))
const agentRuns = computed(() => listValue(matchedRun.value.agentRuns).length ? listValue(matchedRun.value.agentRuns) : listValue(metadata.value.agentRuns))
const specialistAgentLabel = computed(() => {
  const workflowNode = String(metadata.value.workflowNode || '')
  const specialist = agentRuns.value.find(item => String(item?.role || '') === 'specialist' || String(item?.id || '') === workflowNode)
  return String(specialist?.name || specialist?.id || workflowNode || '未返回')
})
const handoffCount = computed(() => {
  const value = matchedRun.value.handoffCount
  return value === null || value === undefined || value === '' ? null : Number(value)
})
const handoffLabel = computed(() => Number.isFinite(handoffCount.value) ? `${handoffCount.value} 次交接` : '交接未返回')
const mcpLabel = computed(() => [harness.value.mcpServer, harness.value.mcpTool].filter(Boolean).join(' / ') || '未返回')
const profileReportId = computed(() => Number(matchedRun.value.profileReportId || metadata.value.profileReportId || 0))
const profileReportLabel = computed(() => profileReportId.value > 0 ? `报告 #${profileReportId.value}` : '未返回')
const stateTitle = computed(() => viewState.value === 'error' ? '无法打开该资源' : '资源详情')

const slides = computed(() => {
  if (resource.value.type !== 'ppt' || isHtmlPpt.value) return []
  const sections = contentText.value.split(/\n(?=##\s+)/).filter(section => /^##\s+/.test(section.trim()))
  return sections.map(section => {
    const lines = section.split('\n').map(line => line.trim()).filter(Boolean)
    const title = lines[0]?.replace(/^##\s*/, '') || '幻灯片'
    const points = lines.slice(1).map(line => line.replace(/^[-*]\s+/, '')).filter(Boolean)
    return { title, points }
  }).filter(slide => slide.points.length)
})

const videoList = computed(() => {
  if (resource.value.type !== 'video') return []
  const structured = listValue(metadata.value.results)
  if (structured.length) {
    return structured.map(item => ({
      ...item,
      title: String(item?.title || '学习视频'),
      embedUrl: safeVideoUrl(item?.embedUrl || (item?.bvid ? `https://player.bilibili.com/player.html?bvid=${item.bvid}&high_quality=1` : '')),
      url: safeVideoUrl(item?.url),
    })).filter(item => item.embedUrl || item.url)
  }
  return [...contentText.value.matchAll(/\[([^\]]+)\]\((https?:\/\/[^)]+)\)/g)].map(match => {
    const url = safeVideoUrl(match[2])
    const bvid = url.match(/(BV[\w]{10})/)?.[1] || ''
    return { title: match[1], url, bvid, embedUrl: bvid ? `https://player.bilibili.com/player.html?bvid=${bvid}&high_quality=1` : '' }
  }).filter(item => item.embedUrl)
})
const currentVideo = computed(() => videoList.value[currentVideoIndex.value] || null)
const generatedVideoContent = computed(() => objectValue(resource.value.content))
const generatedVideoUrl = computed(() => safeResourceHref(generatedVideoContent.value.videoUrl || metadata.value.videoUrl || ''))
const generatedVideoPoster = computed(() => safeResourceHref(generatedVideoContent.value.posterUrl || metadata.value.posterUrl || ''))

function objectValue(value) {
  return value && typeof value === 'object' && !Array.isArray(value) ? value : {}
}

function listValue(value) {
  return Array.isArray(value) ? value : []
}

function safeVideoUrl(value) {
  const url = String(value || '').trim()
  try {
    const parsed = new URL(url)
    const host = parsed.hostname.toLowerCase()
    return parsed.protocol === 'https:' && (host === 'bilibili.com' || host.endsWith('.bilibili.com')) ? parsed.href : ''
  } catch {
    return ''
  }
}

function loadLegacyResource(requestedId) {
  try {
    const parsed = JSON.parse(localStorage.getItem('currentResourceDetail') || 'null')
    if (parsed && String(parsed.id || '') === String(requestedId || '')) return parsed
  } catch {}
  return null
}

async function loadResource() {
  viewState.value = 'loading'
  loadError.value = ''
  sourceMode.value = ''
  orchestrationRuns.value = []
  const requestedId = String(route.query.id || '').trim()
  if (!requestedId) {
    viewState.value = 'error'
    loadError.value = '链接缺少资源编号，请从个性化资源库重新选择。'
    return
  }

  const taskId = taskIdFromResourceId(requestedId)
  if (taskId) {
    try {
      const response = await getXiaoZhiTask(taskId)
      const task = response?.data?.task
      const restored = findTaskResource(task, requestedId)
      if (!restored) throw new Error('任务存在，但未找到链接指定的资源。')
      resource.value = restored
      orchestrationRuns.value = listValue(response?.data?.orchestrationRuns)
      sourceMode.value = 'task'
      viewState.value = 'ready'
      await loadEvaluation()
      await renderMindmap()
      return
    } catch (error) {
      const legacy = loadLegacyResource(requestedId)
      if (legacy) {
        resource.value = legacy
        sourceMode.value = 'legacy'
        viewState.value = 'ready'
        await loadEvaluation()
        await renderMindmap()
        return
      }
      viewState.value = 'error'
      loadError.value = error?.response?.data?.msg || error?.message || '任务记录读取失败，请稍后重试。'
      return
    }
  }

  const legacy = loadLegacyResource(requestedId)
  if (!legacy) {
    viewState.value = 'error'
    loadError.value = '当前浏览器中没有该历史资源，无法从此链接恢复。'
    return
  }
  resource.value = legacy
  sourceMode.value = 'legacy'
  viewState.value = 'ready'
  await loadEvaluation()
  await renderMindmap()
}

async function loadEvaluation() {
  rating.value = 0
  note.value = ''
  savedOutcome.value = ''
  feedbackMessage.value = ''
  nextActions.value = []
  try {
    const response = await getLearningFeedback({ cacheKey: feedbackCacheKey.value, limit: 1 })
    const feedback = response?.data?.feedbacks?.[0]
    if (feedback) {
      rating.value = Number(feedback.rating || 0)
      note.value = String(feedback.note || '')
      savedOutcome.value = String(feedback.outcome || '')
      feedbackMessage.value = '该资源的学习反馈已记录。'
      return
    }
  } catch {}

  try {
    const evaluations = JSON.parse(localStorage.getItem('resourceEvaluations') || '[]')
    const existing = listValue(evaluations).find(item => String(item?.resourceId || '') === String(resource.value.id || ''))
    if (existing) {
      rating.value = Number(existing.rating || 0)
      note.value = String(existing.note || '')
      savedOutcome.value = String(existing.outcome || 'completed')
      feedbackMessage.value = '该资源的本机学习记录已恢复。'
    }
  } catch {}
}

async function submitEvaluation() {
  if (!feedbackOutcome.value || !rating.value || evaluationSaving.value) return
  evaluationSaving.value = true
  evaluationError.value = ''
  try {
    const taskId = String(metadata.value.taskId || taskIdFromResourceId(resource.value.id) || '')
    const response = await submitLearningFeedback({
      taskId,
      cacheKey: feedbackCacheKey.value,
      profileReportId: profileReportId.value || undefined,
      runId: runId.value,
      topic: resource.value.title || '历史学习资源',
      resourceType: resource.value.type || '',
      outcome: feedbackOutcome.value,
      difficulty: rating.value <= 2 ? 'hard' : (rating.value >= 4 ? 'easy' : 'appropriate'),
      helpful: feedbackOutcome.value === 'completed' && rating.value >= 3,
      rating: rating.value,
      note: note.value,
      route: route.fullPath,
    })
    const result = objectValue(response?.data)
    const feedback = objectValue(result.feedback)
    savedOutcome.value = String(feedback.outcome || feedbackOutcome.value)
    feedbackMessage.value = String(result.message || '学习反馈已记录。')
    feedbackNextRoute.value = String(result.route || '/effect-assessment?section=feedback')
    nextActions.value = listValue(result.orchestration?.feedback?.nextActions).map(String).filter(Boolean)
    saveLocalEvaluation(savedOutcome.value)
  } catch (error) {
    evaluationError.value = error?.response?.data?.msg || error?.message || '学习反馈记录失败，请稍后重试。'
  } finally {
    evaluationSaving.value = false
  }
}

function saveLocalEvaluation(outcome) {
  try {
    const values = listValue(JSON.parse(localStorage.getItem('resourceEvaluations') || '[]'))
      .filter(item => String(item?.resourceId || '') !== String(resource.value.id || ''))
    values.push({ resourceId: resource.value.id, outcome, rating: rating.value, note: note.value, completedAt: new Date().toISOString() })
    localStorage.setItem('resourceEvaluations', JSON.stringify(values))
  } catch {}
}

let mermaidPromise = null
async function loadMermaid() {
  if (!mermaidPromise) {
    mermaidPromise = import('mermaid').then(module => {
      const mermaid = module.default || module
      mermaid.initialize({ startOnLoad: false, securityLevel: 'strict', theme: 'neutral' })
      return mermaid
    })
  }
  return mermaidPromise
}

async function renderMindmap() {
  if (viewState.value !== 'ready' || resource.value.type !== 'mindmap' || !mermaidSource.value) return
  await nextTick()
  if (!mindmapRef.value) return
  mindmapError.value = false
  try {
    const mermaid = await loadMermaid()
    const renderId = `resource-mindmap-${Date.now()}`
    const { svg } = await mermaid.render(renderId, mermaidSource.value)
    mindmapRef.value.innerHTML = svg
  } catch {
    mindmapError.value = true
    mindmapRef.value.replaceChildren()
    const fallback = document.createElement('pre')
    fallback.className = 'mindmap-source'
    fallback.textContent = contentText.value
    mindmapRef.value.appendChild(fallback)
  }
}

function outcomeLabel(value) {
  return ({ completed: '已完成', needs_review: '需巩固', blocked: '有阻塞' })[value] || '已记录'
}

function criterionLabel(value) {
  const labels = {
    structure: '结构完整',
    knowledgeGrounding: '知识依据',
    personalization: '个性匹配',
    practiceReadiness: '实践可用',
    safety: '内容安全',
    relevance: '主题相关',
    usability: '学习可用',
    resultCompleteness: '结果完整',
    sourceValidity: '来源有效',
    routeValidity: '路径有效',
  }
  return labels[value] || value
}

function sourceLocator(source) {
  const parts = [source.id, source.page ? `第 ${source.page} 页` : '', source.section ? `第 ${source.section} 节` : ''].filter(Boolean)
  return parts.join(' · ') || '定位未返回'
}

function goBack() {
  router.push('/personalized-resources')
}

watch(() => route.query.id, loadResource)
watch(contentText, () => {
  currentSlide.value = 0
  currentVideoIndex.value = 0
  renderMindmap()
})
onMounted(loadResource)
</script>

<style scoped>
.resource-detail-page {
  min-height: calc(100vh - 72px);
  padding: 30px clamp(18px, 4vw, 56px) 64px;
  background: #f7f9f8;
  color: #1d2825;
}

.detail-header {
  display: grid;
  grid-template-columns: 42px minmax(0, 1fr) auto;
  gap: 16px;
  align-items: start;
  max-width: 1380px;
  margin: 0 auto 24px;
}

.header-copy { min-width: 0; }
.header-copy h1 { margin: 7px 0 6px; font-size: clamp(24px, 3vw, 34px); line-height: 1.22; letter-spacing: 0; overflow-wrap: anywhere; }
.header-copy p { max-width: 820px; margin: 0; color: #65736e; line-height: 1.65; }
.header-meta { display: flex; flex-wrap: wrap; gap: 8px; min-height: 24px; }
.type-tag, .source-tag, .score-badge, .count-badge, .review-badge, .feedback-status { display: inline-flex; align-items: center; gap: 5px; min-height: 24px; padding: 3px 9px; border-radius: 4px; font-size: 12px; font-weight: 700; }
.type-tag { background: #e8f5ee; color: #176f4b; }
.source-tag { background: #e9f2fa; color: #245f8a; }
.source-tag.legacy { background: #fff4df; color: #8b631d; }

.icon-button, .primary-button, .secondary-button, .header-link { display: inline-flex; align-items: center; justify-content: center; gap: 7px; min-height: 40px; border-radius: 6px; font: inherit; font-size: 14px; font-weight: 700; text-decoration: none; cursor: pointer; }
.icon-button { width: 42px; padding: 0; border: 1px solid #dce3e0; background: #fff; color: #46524e; }
.icon-button:disabled { cursor: not-allowed; opacity: .42; }
.primary-button { padding: 0 16px; border: 1px solid #176f4b; background: #176f4b; color: #fff; }
.secondary-button, .header-link { padding: 0 15px; border: 1px solid #d8dfdc; background: #fff; color: #34423d; }
.header-link { margin-top: 2px; }
button:focus-visible, a:focus-visible, textarea:focus-visible { outline: 3px solid rgba(23, 111, 75, .24); outline-offset: 3px; }

.state-panel { display: grid; justify-items: center; max-width: 760px; margin: 76px auto 0; padding: 52px 24px; border: 1px solid #e1e6e4; border-radius: 8px; background: #fff; text-align: center; }
.state-panel h2 { margin: 14px 0 6px; font-size: 22px; }
.state-panel p { margin: 0; color: #6a7772; line-height: 1.6; }
.state-actions { display: flex; flex-wrap: wrap; justify-content: center; gap: 10px; margin-top: 22px; }
.error-state > svg { color: #b6533f; }
.legacy-notice { display: flex; align-items: center; gap: 9px; max-width: 1380px; margin: 0 auto 18px; padding: 10px 13px; border: 1px solid #ead7aa; border-radius: 6px; background: #fffbef; color: #795a1f; font-size: 13px; }

.detail-layout { display: grid; grid-template-columns: minmax(0, 1fr) minmax(300px, 360px); gap: 22px; align-items: start; max-width: 1380px; margin: 0 auto; }
.artifact-column, .evidence-column { min-width: 0; }
.artifact-column { display: grid; gap: 20px; }
.evidence-column { display: grid; gap: 14px; position: sticky; top: 88px; }
.artifact-surface, .feedback-panel, .evidence-panel, .content-empty { border: 1px solid #e1e6e4; border-radius: 8px; background: #fff; }
.artifact-surface { min-height: 240px; padding: clamp(22px, 3vw, 40px); }
.content-empty { display: grid; justify-items: center; padding: 52px 22px; text-align: center; color: #78847f; }
.content-empty.compact { min-height: 200px; border: 0; }
.content-empty h2 { margin: 12px 0 4px; color: #34423d; font-size: 18px; }
.content-empty p { margin: 0; }

.mindmap-surface { overflow-x: auto; }
.mindmap-render { display: grid; place-items: center; min-height: 430px; }
.mindmap-render :deep(svg) { max-width: 100%; height: auto; }
.mindmap-render :deep(.mindmap-source) { width: 100%; margin: 0; white-space: pre-wrap; overflow-wrap: anywhere; }
.render-warning, .sandbox-note, .verification-warning, .privacy-note { display: flex; align-items: flex-start; gap: 7px; color: #7d6025; font-size: 12px; line-height: 1.55; }
.render-warning { margin-top: 12px; }

.ppt-html-surface { padding: 0; overflow: hidden; }
.ppt-frame { display: block; width: 100%; height: min(74vh, 820px); min-height: 560px; border: 0; background: #fff; }
.sandbox-note { margin: 0; padding: 10px 14px; border-top: 1px solid #e3e8e6; background: #f8faf9; color: #62706b; }
.ppt-surface { padding: 0; overflow: hidden; }
.slide { min-height: 470px; padding: clamp(30px, 6vw, 72px); background: #fcfdfc; }
.slide-kicker, .eyebrow { color: #17704e; font-size: 11px; font-weight: 800; text-transform: uppercase; }
.slide h2 { margin: 12px 0 28px; font-size: 30px; line-height: 1.3; }
.slide ul { margin: 0; padding-left: 24px; }
.slide li { margin: 12px 0; color: #40504a; font-size: 17px; line-height: 1.7; }
.slide-controls { display: flex; align-items: center; justify-content: center; gap: 14px; padding: 12px; border-top: 1px solid #e2e7e5; }
.slide-controls > span { width: 78px; text-align: center; color: #66736f; font-variant-numeric: tabular-nums; }

.video-surface { padding: 20px; }
.video-layout { display: grid; grid-template-columns: minmax(0, 1fr) 300px; gap: 18px; }
.video-frame-wrap { overflow: hidden; aspect-ratio: 16 / 9; border-radius: 6px; background: #0d1211; }
.video-frame { width: 100%; height: 100%; border: 0; }
.video-title { margin: 15px 0 4px; font-size: 18px; }
.video-meta { margin: 0; color: #74807c; font-size: 13px; }
.video-playlist { display: grid; align-content: start; gap: 4px; max-height: 520px; overflow-y: auto; }
.playlist-item { display: grid; grid-template-columns: 28px minmax(0, 1fr); gap: 9px; width: 100%; padding: 10px; border: 1px solid transparent; border-radius: 6px; background: transparent; color: #35423e; text-align: left; cursor: pointer; }
.playlist-item:hover, .playlist-item.active { border-color: #bfd9cf; background: #eef7f3; }
.playlist-item > span:first-child { display: grid; place-items: center; width: 25px; height: 25px; border-radius: 4px; background: #e7ecea; color: #5f6c67; font-size: 12px; font-weight: 800; }
.playlist-item strong, .playlist-item small { display: block; overflow-wrap: anywhere; }
.playlist-item strong { line-height: 1.4; }
.playlist-item small { margin-top: 4px; color: #78847f; }
.video-notes { margin-top: 24px; padding-top: 22px; border-top: 1px solid #e4e9e7; }
.generated-video-surface video { display: block; width: 100%; max-height: 72vh; background: #0f1513; }

.markdown-content { color: #33423d; line-height: 1.75; overflow-wrap: anywhere; }
.markdown-content :deep(h1) { margin: 0 0 24px; font-size: 28px; color: #1d2c27; }
.markdown-content :deep(h2) { margin: 30px 0 13px; font-size: 22px; color: #243a32; }
.markdown-content :deep(h3) { margin: 24px 0 10px; font-size: 18px; }
.markdown-content :deep(p) { margin: 0 0 16px; }
.markdown-content :deep(pre) { max-width: 100%; padding: 18px; overflow-x: auto; border-radius: 6px; background: #17211e; color: #e8f2ee; }
.markdown-content :deep(code) { font-family: ui-monospace, SFMono-Regular, Consolas, monospace; }
.markdown-content :deep(:not(pre) > code) { padding: 2px 5px; border-radius: 3px; background: #edf2f0; color: #8c3f31; }
.markdown-content :deep(a) { color: #126c4a; font-weight: 700; }
.markdown-content :deep(blockquote) { margin: 18px 0; padding: 10px 14px; border-left: 3px solid #d59b25; background: #fff9ea; color: #705826; }

.feedback-panel { padding: clamp(20px, 3vw, 30px); }
.section-heading { display: flex; align-items: flex-start; justify-content: space-between; gap: 12px; }
.section-heading h2 { margin: 3px 0 0; font-size: 20px; }
.compact-heading h2 { font-size: 16px; }
.outcome-control { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 8px; margin: 24px 0 20px; padding: 0; border: 0; }
.outcome-control legend { grid-column: 1 / -1; margin-bottom: 2px; color: #4b5b55; font-size: 13px; font-weight: 700; }
.outcome-control button { display: inline-flex; align-items: center; justify-content: center; gap: 7px; min-height: 44px; padding: 8px 10px; border: 1px solid #dce3e0; border-radius: 6px; background: #fff; color: #4b5954; font: inherit; font-size: 13px; font-weight: 700; cursor: pointer; }
.outcome-control button.selected { border-color: #4a9275; background: #edf6f2; color: #176f4b; box-shadow: inset 0 0 0 1px #4a9275; }
.rating-field { margin-bottom: 18px; }
.rating-field > span, .note-field > span { display: block; margin-bottom: 8px; color: #4b5b55; font-size: 13px; font-weight: 700; }
.star-rating { display: flex; align-items: center; gap: 4px; min-height: 34px; }
.star-rating button { display: flex; padding: 2px; border: 0; background: transparent; cursor: pointer; }
.star-rating > span { margin-left: 8px; color: #6f7c77; font-size: 13px; }
.note-field small { color: #8a9692; font-weight: 400; }
.note-field textarea { width: 100%; padding: 12px 13px; border: 1px solid #d8dfdc; border-radius: 6px; background: #fafcfb; color: #27352f; font: inherit; line-height: 1.55; resize: vertical; box-sizing: border-box; }
.feedback-submit-row { display: flex; align-items: center; gap: 14px; margin-top: 16px; }
.feedback-submit-row .primary-button:disabled { cursor: not-allowed; opacity: .55; }
.privacy-note { color: #73807b; }
.inline-error { margin: 10px 0 0; color: #a84634; font-size: 13px; }
.feedback-status.completed { background: #e7f5ed; color: #176f4b; }
.feedback-status.needs_review { background: #fff3d9; color: #92651a; }
.feedback-status.blocked { background: #ffede8; color: #a74835; }
.feedback-result { display: grid; grid-template-columns: 26px minmax(0, 1fr); gap: 11px; margin-top: 22px; color: #176f4b; }
.feedback-result strong { color: #273a33; line-height: 1.5; }
.feedback-result p { margin: 6px 0 0; color: #68766f; line-height: 1.6; }
.next-actions { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 16px; }

.evidence-panel { padding: 20px; }
.score-badge { background: #e7f3ff; color: #245f8a; }
.count-badge { background: #eff2f1; color: #58645f; }
.review-badge.passed { background: #e5f5ec; color: #176f4b; }
.review-badge.warning { background: #fff1d5; color: #8b611c; }
.review-badge.failed { background: #ffebe6; color: #a54a37; }
.review-badge.neutral { background: #eff2f1; color: #69746f; }
.evidence-list, .criteria-list { display: grid; gap: 0; margin: 16px 0 0; }
.evidence-list > div, .criteria-list > div { display: grid; grid-template-columns: 90px minmax(0, 1fr); gap: 10px; padding: 10px 0; border-top: 1px solid #edf0ef; }
.evidence-list dt, .criteria-list dt { color: #7a8581; font-size: 12px; }
.evidence-list dd, .criteria-list dd { min-width: 0; margin: 0; color: #34423d; font-size: 13px; font-weight: 650; line-height: 1.5; overflow-wrap: anywhere; }
.mono { font-family: ui-monospace, SFMono-Regular, Consolas, monospace; font-size: 11px !important; }
.quality-score { display: flex; align-items: baseline; gap: 5px; margin: 16px 0 2px; }
.quality-score strong { font-size: 34px; color: #176f4b; font-variant-numeric: tabular-nums; }
.quality-score span { color: #7f8b86; font-size: 12px; }
.criteria-list { grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 0 14px; }
.criteria-list > div { grid-template-columns: minmax(0, 1fr) auto; }
.criteria-list dd { font-variant-numeric: tabular-nums; }
.quality-panel.warning { border-color: #ead6a5; }
.verification-warning { margin: 15px 0 0; padding: 10px; border-radius: 5px; background: #fff8e7; }
.source-list { display: grid; gap: 10px; margin: 16px 0 0; padding: 0; list-style: none; }
.source-list li { display: grid; grid-template-columns: 24px minmax(0, 1fr); gap: 9px; }
.source-list li > span { display: grid; place-items: center; width: 22px; height: 22px; border-radius: 4px; background: #eaf4ef; color: #176f4b; font-size: 11px; font-weight: 800; }
.source-list strong, .source-list small { display: block; overflow-wrap: anywhere; }
.source-list strong { color: #35443e; font-size: 13px; line-height: 1.4; }
.source-list small { margin-top: 3px; color: #7d8984; font-size: 11px; }
.evidence-empty { margin: 16px 0 0; color: #7a8581; font-size: 13px; line-height: 1.6; }
.spin { animation: spin .8s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }

@media (max-width: 1040px) {
  .detail-layout { grid-template-columns: minmax(0, 1fr); }
  .evidence-column { position: static; grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .sources-panel { grid-column: 1 / -1; }
  .video-layout { grid-template-columns: minmax(0, 1fr) 260px; }
}

@media (max-width: 760px) {
  .resource-detail-page { padding: 20px 16px 46px; }
  .detail-header { grid-template-columns: 42px minmax(0, 1fr); }
  .header-link { grid-column: 2; justify-self: start; margin-top: 0; }
  .detail-layout, .artifact-column { gap: 14px; }
  .evidence-column { grid-template-columns: minmax(0, 1fr); }
  .sources-panel { grid-column: auto; }
  .artifact-surface { padding: 20px; }
  .ppt-html-surface, .ppt-surface { padding: 0; }
  .ppt-frame { min-height: 470px; height: 68vh; }
  .slide { min-height: 390px; }
  .video-layout { grid-template-columns: minmax(0, 1fr); }
  .video-playlist { max-height: 280px; }
  .outcome-control { grid-template-columns: minmax(0, 1fr); }
  .feedback-submit-row { align-items: flex-start; flex-direction: column; }
}

@media (max-width: 420px) {
  .header-copy h1 { font-size: 22px; }
  .header-meta { gap: 5px; }
  .artifact-surface, .feedback-panel, .evidence-panel { border-radius: 6px; }
  .artifact-surface { padding: 16px; }
  .ppt-html-surface, .ppt-surface { padding: 0; }
  .criteria-list { grid-template-columns: minmax(0, 1fr); }
  .next-actions { display: grid; }
  .next-actions > a { width: 100%; box-sizing: border-box; }
}
</style>
