<template>
  <div class="resources-page">
    <div class="resources-header">
      <h1>个性化资源</h1>
    </div>

    <!-- 无学习画像引导提示条 -->
    <div v-if="profileError" class="no-profile-banner status-banner error-banner" role="alert">
      <TriangleAlert :size="20" aria-hidden="true" />
      <span>{{ profileError }}</span>
      <button class="banner-btn" type="button" :disabled="profileLoading" @click="loadProfile">
        {{ profileLoading ? '正在重试' : '重试画像' }}
      </button>
    </div>
    <div v-else-if="!profileLoading && !hasProfile" class="no-profile-banner">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" class="banner-icon">
        <path d="M12 9v3.75m9-.75a9 9 0 11-18 0 9 9 0 0118 0zm-9 3.75h.008v.008H12v-.008z" stroke-linecap="round" stroke-linejoin="round"/>
      </svg>
      <span>完成学习画像后才能生成个性化资源；已生成的历史资源仍可查看</span>
      <button class="banner-btn" @click="$router.push('/learning-profile')">前往评估</button>
    </div>

    <section class="resource-launchers" aria-labelledby="resource-tools-title">
      <div class="section-line-heading">
        <h2 id="resource-tools-title">资源工具</h2>
      </div>
      <nav class="resource-launcher-grid" aria-label="资源生成工具">
        <RouterLink
          v-for="tool in resourceTools"
          :key="tool.to"
          class="resource-launcher"
          :class="tool.tone"
          :to="tool.to"
          target="_blank"
          rel="noopener noreferrer"
        >
          <span class="launcher-icon"><component :is="tool.icon" :size="22" :stroke-width="1.8" aria-hidden="true" /></span>
          <span class="launcher-copy">
            <strong>{{ tool.title }}</strong>
          </span>
          <ArrowRight :size="17" aria-hidden="true" />
        </RouterLink>
      </nav>
    </section>

    <section class="resource-archive" aria-labelledby="resource-archive-title">
      <div class="archive-heading">
        <div class="archive-title">
          <h2 id="resource-archive-title">历史资源</h2>
          <span>{{ resourcesLoading ? '正在同步' : `共 ${visibleResourceCount} 项` }}</span>
        </div>
        <div class="archive-actions">
          <label class="history-search archive-search">
            <Search :size="17" aria-hidden="true" />
            <input
              v-model="searchQuery"
              type="search"
              inputmode="search"
              autocomplete="off"
              aria-label="搜索历史资源"
              placeholder="搜索资源"
              @keydown.esc="clearSearch"
            />
            <button v-if="searchQuery" type="button" title="清除搜索" aria-label="清除搜索" @click="clearSearch">
              <X :size="15" aria-hidden="true" />
            </button>
          </label>
          <label class="type-filter">
            <span>类型</span>
            <select v-model="activeCategory" aria-label="按资源类型筛选">
              <option v-for="cat in categories" :key="cat.key" :value="cat.key">{{ cat.label }}</option>
            </select>
          </label>
          <button
            type="button"
            class="history-refresh-btn"
            :disabled="resourcesLoading"
            title="刷新资源"
            aria-label="刷新资源"
            @click="loadResources"
          >
            <RefreshCw :size="16" :class="{ spin: resourcesLoading }" aria-hidden="true" />
          </button>
          <button class="generate-btn" @click="generateNewResource" :disabled="generating || !hasProfile">
            <Plus v-if="!generating" :size="17" aria-hidden="true" />
            <span v-if="generating" class="loading-spinner"></span>
            {{ generating ? '生成中...' : '生成资源' }}
          </button>
        </div>
      </div>

      <div v-if="resourcesWarning" class="history-status warning" role="status">
        <TriangleAlert :size="18" aria-hidden="true" />
        <span>{{ resourcesWarning }}</span>
        <button type="button" @click="loadResources">重新加载</button>
      </div>

      <div class="archive-result-line" aria-live="polite">
        <span v-if="resourcesLoading || searchQuery.trim() || activeCategory !== 'all'">
          {{ resourcesLoading ? '正在读取资源记录' : resultSummary }}
        </span>
        <span v-if="filteredResources.length">第 {{ currentPage }} / {{ totalPages }} 页</span>
      </div>

      <div v-if="resourcesLoading && !resources.length" class="history-loading" role="status" aria-live="polite">
        <LoaderCircle :size="28" class="spin" aria-hidden="true" />
        <strong>正在同步真实资源记录</strong>
        <span>正在读取岐小智任务与已生成视频，请稍候。</span>
      </div>
      <div v-else-if="resourcesError && !resources.length" class="history-error" role="alert">
        <TriangleAlert :size="30" aria-hidden="true" />
        <strong>历史资源暂时无法加载</strong>
        <span>{{ resourcesError }}</span>
        <button type="button" @click="loadResources">重试</button>
      </div>
      <div v-else-if="filteredResources.length" class="resource-gallery" aria-label="历史资源">
        <article
          v-for="resource in paginatedResources"
          :key="resource.id"
          class="resource-cover-card"
          role="link"
          tabindex="0"
          @click="openResource(resource)"
          @keydown.enter="openResource(resource)"
          @keydown.space.prevent="openResource(resource)"
        >
          <div class="resource-cover-frame">
            <div class="cover-loading" :class="{ hidden: isPreviewLoaded(resource.id) }" aria-hidden="true">
              <component :is="getResourceIcon(resource.type)" :size="28" :stroke-width="1.5" />
              <span>{{ resource.type === 'generated_video' ? staticCoverLabel(resource) : '正在读取封面' }}</span>
            </div>
            <img
              v-if="usesStaticCover(resource)"
              class="resource-static-cover"
              :class="{ loaded: isPreviewLoaded(resource.id) }"
              :src="getResourceCoverImage(resource)"
              :alt="`${resource.title}封面`"
              loading="lazy"
              @load="markPreviewLoaded(resource.id)"
              @error="retryStaticCover(resource)"
            />
            <iframe
              v-else
              class="resource-live-cover"
              :class="{ loaded: isPreviewLoaded(resource.id) }"
              :src="getResourcePreviewUrl(resource)"
              :title="`${resource.title}页面封面`"
              tabindex="-1"
              loading="lazy"
              scrolling="no"
              aria-hidden="true"
              @load="markPreviewLoaded(resource.id)"
            ></iframe>
          </div>
          <div class="resource-cover-copy">
            <h3>{{ resource.title }}</h3>
            <footer>
              <span>质量 {{ resourceQualityScore(resource) }}</span>
              <span>{{ getTypeName(resource.type) }}</span>
              <time :datetime="resource.createdAt || undefined">{{ resource.createdAt ? formatResourceTime(resource.createdAt) : '--' }}</time>
            </footer>
          </div>
        </article>
      </div>

      <div v-if="!resourcesLoading && !resourcesError && filteredResources.length === 0" class="empty-state">
        <Search :size="30" aria-hidden="true" />
        <p>{{ searchQuery ? `没有找到与“${searchQuery}”相关的资源` : '当前类型暂无资源' }}</p>
        <button v-if="searchQuery" type="button" @click="clearSearch">清除搜索</button>
      </div>

      <nav v-if="!resourcesLoading && totalPages > 1" class="history-pagination" aria-label="历史资源分页">
        <button type="button" class="page-nav-btn" :disabled="currentPage === 1" title="上一页" aria-label="上一页" @click="goToPage(currentPage - 1)">
          <ChevronLeft :size="17" aria-hidden="true" />
        </button>
        <template v-for="item in paginationItems" :key="item">
          <span v-if="typeof item === 'string'" class="page-ellipsis" aria-hidden="true">...</span>
          <button
            v-else
            type="button"
            class="page-number-btn"
            :class="{ active: item === currentPage }"
            :aria-current="item === currentPage ? 'page' : undefined"
            :aria-label="`第 ${item} 页`"
            @click="goToPage(item)"
          >
            {{ item }}
          </button>
        </template>
        <button type="button" class="page-nav-btn" :disabled="currentPage === totalPages" title="下一页" aria-label="下一页" @click="goToPage(currentPage + 1)">
          <ChevronRight :size="17" aria-hidden="true" />
        </button>
      </nav>
    </section>
  </div>
</template>

<script setup>
import { ref, computed, markRaw, onMounted, onUnmounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  ArrowRight,
  Box,
  ChevronLeft,
  ChevronRight,
  CirclePlay,
  Film,
  FileText,
  ListChecks,
  LoaderCircle,
  PanelsTopLeft,
  Plus,
  RefreshCw,
  Search,
  TriangleAlert,
  Workflow,
  X,
} from 'lucide-vue-next'
import {
  getLearningProfiles,
  getGeneratedVideoTaskHistory,
  getXiaoZhiHistory,
  getXiaoZhiTask,
  startPersonalizedResourceAgentTask,
} from '../services/api.js'
import {
  defaultResourceTitle,
  extractTaskResources,
  resourceCitationCount,
  resourceQuality,
} from '../utils/personalizedResourceHistory.js'

const router = useRouter()
const route = useRoute()

const resourceTools = [
  {
    title: 'AI 视频课程',
    to: '/personalized-resources/video-generator',
    icon: markRaw(Film),
    tone: 'launcher-teal',
  },
  {
    title: '题库生成',
    to: '/personalized-resources/question-bank',
    icon: markRaw(ListChecks),
    tone: 'launcher-amber',
  },
  {
    title: 'PPT生成',
    to: '/personalized-resources/ppt',
    icon: markRaw(PanelsTopLeft),
    tone: 'launcher-blue',
  },
  {
    title: '思维导图',
    to: '/personalized-resources/mind-map',
    icon: markRaw(Workflow),
    tone: 'launcher-violet',
  },
  {
    title: '药材模型识别',
    to: '/personalized-resources/herb-model',
    icon: markRaw(Box),
    tone: 'launcher-coral',
  },
  {
    title: '视频查找',
    to: '/personalized-resources/video-search',
    icon: markRaw(Search),
    tone: 'launcher-cyan',
  },
]

const categories = [
  { key: 'all', label: '全部' },
  { key: 'mindmap', label: '思维导图' },
  { key: 'ppt', label: 'PPT' },
  { key: 'video', label: '视频' },
  { key: 'generated_video', label: 'AI 视频生成' },
  { key: 'quiz', label: '练习题' },
  { key: 'herb_model', label: '药材模型' },
]

const requestedCategory = String(route.query.category || '')
const activeCategory = ref(categories.some(item => item.key === requestedCategory) ? requestedCategory : 'all')
const searchQuery = ref('')
const currentPage = ref(1)
const pageSize = 9
const generating = ref(false)
const resources = ref([])
const loadedResourcePreviews = ref(new Set())
const hasProfile = ref(false)
const profileData = ref(null)
const evaluations = ref([])
const profileLoading = ref(true)
const profileError = ref('')
const resourcesLoading = ref(true)
const resourcesError = ref('')
const resourcesWarning = ref('')
const hiddenResourceTypes = new Set(['document', 'animation', 'code', 'simulator', 'mcu'])

onMounted(async () => {
  loadEvaluations()
  await Promise.all([loadProfile(), loadResources()])
})

async function loadProfile() {
  profileLoading.value = true
  profileError.value = ''
  try {
    const data = await getLearningProfiles()
    const activeId = Number(data?.activeReportId || 0)
    const activeProfile = (data?.profiles || []).find(item => Number(item?.id || 0) === activeId) || null
    hasProfile.value = Boolean(activeProfile)
    profileData.value = activeProfile
  } catch (error) {
    hasProfile.value = false
    profileData.value = null
    profileError.value = error?.response?.data?.msg || error?.message || '学习画像暂时无法读取，当前不能确认个性化生成条件。'
  } finally {
    profileLoading.value = false
  }
}

async function loadResources() {
  resourcesLoading.value = true
  resourcesError.value = ''
  resourcesWarning.value = ''
  const [historyResult, videoResult] = await Promise.allSettled([
    getXiaoZhiHistory(100),
    loadAllGeneratedVideos(),
  ])
  try {
    const response = historyResult.status === 'fulfilled' ? historyResult.value : {}
    const generatedVideoTasks = videoResult.status === 'fulfilled' ? videoResult.value : []
    const generatedVideoResources = generatedVideoTasks.flatMap(extractTaskResources)
    const backendResources = (response?.data?.tasks || []).flatMap(extractTaskResources)
    let legacyResources = []
    try {
      const saved = localStorage.getItem('personalizedResources')
      legacyResources = saved
        ? JSON.parse(saved).filter(item => item?.source === 'workflow-real-data' || item?.metadata)
        : []
    } catch {}

    const failedSources = []
    if (historyResult.status === 'rejected') failedSources.push('岐小智任务历史')
    if (videoResult.status === 'rejected') failedSources.push('AI 视频历史')
    const seen = new Set()
    const mergedResources = sortResourceHistory(
      [...generatedVideoResources, ...backendResources, ...legacyResources].filter(item => {
        const key = String(item?.id || `${item?.type}:${item?.title}`)
        if (!item || seen.has(key)) return false
        seen.add(key)
        return true
      }),
    )
    resources.value = mergedResources

    if (failedSources.length === 2 && legacyResources.length) {
      resourcesWarning.value = `资源服务暂时未响应，当前仅展示 ${legacyResources.length} 条本地历史。重试后可同步真实任务记录。`
    } else if (failedSources.length === 2) {
      resourcesError.value = '资源服务暂时未响应，无法确认是否存在历史资源。请重试。'
    } else if (failedSources.length) {
      resourcesWarning.value = `${failedSources.join('、')}暂时未同步，当前列表可能不完整。`
    }
  } catch (error) {
    resourcesError.value = error?.message || '历史资源解析失败，请重试。'
  } finally {
    resourcesLoading.value = false
  }
}

async function loadAllGeneratedVideos() {
  const tasks = []
  let offset = 0
  while (true) {
    const page = await getGeneratedVideoTaskHistory({ limit: 100, offset })
    const pageTasks = Array.isArray(page?.tasks) ? page.tasks : []
    tasks.push(...pageTasks)
    if (!page?.hasMore || pageTasks.length === 0) break
    offset += pageTasks.length
  }
  return tasks
}

function sortResourceHistory(items) {
  return [...items].sort((left, right) => {
    const leftTime = Date.parse(left?.createdAt || '') || 0
    const rightTime = Date.parse(right?.createdAt || '') || 0
    return rightTime - leftTime
  })
}

function loadEvaluations() {
  try {
    const raw = localStorage.getItem('resourceEvaluations')
    if (raw) evaluations.value = JSON.parse(raw)
  } catch {}
}

function getEvaluation(resourceId) {
  return evaluations.value.find(e => e.resourceId === resourceId)
}

function saveResources() {
  localStorage.setItem('personalizedResources', JSON.stringify(resources.value))
}

function initDefaultResources() {
  const defaults = [
    {
      id: Date.now(),
      title: '中医基础理论思维导图',
      description: '涵盖阴阳五行、藏象、气血津液与经络等核心知识点',
      type: 'mindmap',
      matchScore: 85,
      content: `mindmap
  root((中医基础理论))
    整体观念
      人体自身整体
      人与自然统一
    阴阳五行
      阴阳制约互根
      五行生克制化
    藏象
      五脏六腑
      形体官窍
    气血津液
      生成运行
      相互关系
    经络
      经脉络脉
      运行气血`,
      createdAt: new Date().toISOString(),
    },
    {
      id: Date.now() + 1,
      title: '四诊与八纲辨证基础',
      description: '适合初学者的中医诊断学 PPT 课件',
      type: 'ppt',
      matchScore: 78,
      content: `# 四诊与八纲辨证基础

## 第一页：四诊合参
- 望、闻、问、切相互补充
- 不以单一症状直接下结论

## 第二页：望诊与舌诊
- 神色形态
- 舌质与舌苔

## 第三页：问诊与脉诊
- 主诉、寒热、饮食、睡眠与二便
- 脉位、脉数、脉形与脉势

## 第四页：八纲辨证
- 表里、寒热、虚实、阴阳

## 第五页：医案练习
- 提取四诊信息
- 推导证候、病机与治法`,
      createdAt: new Date().toISOString(),
    },
    {
      id: Date.now() + 2,
      title: '舌诊与脉诊视频学习单',
      description: '通过典型案例学习舌象、脉象和四诊合参',
      type: 'video',
      matchScore: 90,
      content: `# 舌诊与脉诊视频学习单

## 课程大纲

### 第1节：舌诊观察
- 舌质与舌苔
- 舌色、舌形与津液

### 第2节：脉诊基础
- 脉位、脉数、脉形与脉势
- 常见脉象对比

### 第3节：四诊信息记录
\`\`\`c
按望、闻、问、切分类整理医案信息，标出支持和不支持候选证候的依据。
\`\`\`

### 第4节：辨证练习
- 对比相近证候
- 写出病机与治法思路

### 第5节：核验与总结
- 使用教材或知识库核对结论
- 记录需要继续查证的知识点`,
      createdAt: new Date().toISOString(),
    },
    {
      id: Date.now() + 3,
      title: '脾胃病医案辨析示例',
      description: '按四诊、证候、病机、治法组织医案分析',
      type: 'document',
      matchScore: 82,
      content: `# 脾胃病医案辨析示例

## 四诊信息

\`\`\`c
按主诉、兼症、舌象和脉象分类记录，不遗漏否定信息。
\`\`\`

## 关键点说明
1. 先列候选证候，再逐项核对支持与不支持证据
2. 病机和治法的推导不得跳过关键依据
3. 方药内容须核对权威教材，并提示禁忌与安全边界`,
      createdAt: new Date().toISOString(),
    },
    {
      id: Date.now() + 4,
      title: '中药与方剂基础练习题',
      description: '检验性味归经、功效主治和方剂配伍掌握程度',
      type: 'quiz',
      matchScore: 88,
      content: `# 中药与方剂基础练习题

## 题目1：中药知识框架
**问题：** 学习一味中药时，应从哪些维度建立知识卡片？

A. 只记药名
B. 只记功效
C. 性味、归经、功效、主治、配伍与禁忌
D. 只记药物图片

**答案：** C
**解析：** 应建立完整知识框架并注明可靠来源。

---

## 题目2：方剂配伍
**问题：** 君臣佐使主要用于说明什么？

A. 药物颜色
B. 方中药物的主次与协同制约关系
C. 药物产地
D. 煎药器具

**答案：** B
**解析：** 应结合具体方剂理解主治核心、协同加强、兼治制约与引经调和。

---

## 题目3：安全边界
**问题：** 为什么不能只凭单个症状直接推荐方药？

A. 症状没有意义
B. 中医强调四诊合参和辨证论治，方药还涉及禁忌与个体差异
C. 所有方剂都一样
D. 不需要学习方剂

**答案：** B
**解析：** 学习讨论不能替代现实诊断和个体化处方建议。`,
      createdAt: new Date().toISOString(),
    },
  ]

  resources.value = defaults
  saveResources()
}

const filteredResources = computed(() => {
  const visibleResources = resources.value.filter(r => !hiddenResourceTypes.has(String(r?.type || '')))
  const categoryResources = activeCategory.value === 'all'
    ? visibleResources
    : visibleResources.filter(r => r.type === activeCategory.value)
  const query = searchQuery.value.trim().toLocaleLowerCase('zh-CN')
  if (!query) return categoryResources
  return categoryResources.filter(resource => [
    resource?.title,
    resource?.description,
    getTypeName(resource?.type),
  ].some(value => String(value || '').toLocaleLowerCase('zh-CN').includes(query)))
})

const visibleResourceCount = computed(() => (
  resources.value.filter(resource => !hiddenResourceTypes.has(String(resource?.type || ''))).length
))

const totalPages = computed(() => Math.max(1, Math.ceil(filteredResources.value.length / pageSize)))

const paginatedResources = computed(() => {
  const start = (currentPage.value - 1) * pageSize
  return filteredResources.value.slice(start, start + pageSize)
})

const resultSummary = computed(() => {
  if (searchQuery.value.trim() || activeCategory.value !== 'all') {
    return `找到 ${filteredResources.value.length} 项，共 ${visibleResourceCount.value} 项`
  }
  return `共 ${visibleResourceCount.value} 项`
})

const paginationItems = computed(() => {
  const total = totalPages.value
  if (total <= 7) return Array.from({ length: total }, (_, index) => index + 1)
  const items = [1]
  const start = Math.max(2, currentPage.value - 1)
  const end = Math.min(total - 1, currentPage.value + 1)
  if (start > 2) items.push('before')
  for (let page = start; page <= end; page += 1) items.push(page)
  if (end < total - 1) items.push('after')
  items.push(total)
  return items
})

watch([activeCategory, searchQuery], () => {
  currentPage.value = 1
})

watch(totalPages, total => {
  if (currentPage.value > total) currentPage.value = total
})

function clearSearch() {
  searchQuery.value = ''
}

function goToPage(page) {
  currentPage.value = Math.min(Math.max(1, Number(page) || 1), totalPages.value)
  document.querySelector('.archive-heading')?.scrollIntoView({ behavior: 'smooth', block: 'start' })
}

function getResourceIcon(type) {
  return {
    mindmap: Workflow,
    ppt: PanelsTopLeft,
    video: CirclePlay,
    generated_video: Film,
    quiz: ListChecks,
    herb_model: Box,
  }[type] || FileText
}

function previewResourceKey(resourceId) {
  return String(resourceId || '')
}

function isPreviewLoaded(resourceId) {
  return loadedResourcePreviews.value.has(previewResourceKey(resourceId))
}

function markPreviewLoaded(resourceId) {
  const next = new Set(loadedResourcePreviews.value)
  next.add(previewResourceKey(resourceId))
  loadedResourcePreviews.value = next
}

const staticCoverRetries = new Map()
const staticCoverRetryTimers = new Map()

function usesStaticCover(resource) {
  return ['video', 'generated_video'].includes(String(resource?.type || ''))
}

function proxiedCoverUrl(value) {
  const cover = String(value || '').trim()
  if (!cover) return ''
  return /^https?:\/\//i.test(cover) ? `/api-cover?url=${encodeURIComponent(cover)}` : cover
}

function getResourceCoverImage(resource) {
  const attempt = staticCoverRetries.get(previewResourceKey(resource?.id)) || 0
  const metadata = (resource?.metadata && typeof resource.metadata === 'object') ? resource.metadata : {}
  const content = (resource?.content && typeof resource.content === 'object') ? resource.content : {}
  let cover = ''
  if (resource?.type === 'video') {
    cover = metadata?.results?.[0]?.cover
      || content?.results?.[0]?.cover
      || content?.cover
      || metadata?.cover
      || content?.thumbnailUrl
      || metadata?.thumbnailUrl
      || ''
  } else if (resource?.type === 'generated_video') {
    const taskId = String(resource?.metadata?.taskId || resource?.taskId || '')
    cover = content?.posterUrl
      || metadata?.posterUrl
      || content?.cover
      || metadata?.cover
      || content?.thumbnailUrl
      || metadata?.thumbnailUrl
      || (taskId ? `/api/personalized-resources/generated-videos/${encodeURIComponent(taskId)}/poster` : '')
  }
  const url = proxiedCoverUrl(cover)
  if (!url || !attempt) return url
  return `${url}${url.includes('?') ? '&' : '?'}coverAttempt=${attempt}`
}

function retryStaticCover(resource) {
  const key = previewResourceKey(resource?.id)
  const attempt = staticCoverRetries.get(key) || 0
  if (resource?.type !== 'generated_video') return
  if (staticCoverRetryTimers.has(key)) return
  const timer = window.setTimeout(() => {
    staticCoverRetryTimers.delete(key)
    staticCoverRetries.set(key, attempt + 1)
    resources.value = [...resources.value]
  }, Math.min(10000, 2000 + attempt * 500))
  staticCoverRetryTimers.set(key, timer)
}

function staticCoverLabel() {
  return '首图生成中'
}

onUnmounted(() => {
  for (const timer of staticCoverRetryTimers.values()) window.clearTimeout(timer)
  staticCoverRetryTimers.clear()
})

function getResourcePreviewUrl(resource) {
  const target = String(resource?.route || '').trim()
  const canUseActualRoute = target
    && !/^https?:\/\//i.test(target)
    && target !== '/personalized-resources'
    && (
      (resource?.type === 'ppt' && target.includes('/ppt-generator/generating/'))
      || resource?.type === 'herb_model'
      || resource?.type === 'mindmap'
    )

  if (canUseActualRoute) {
    try {
      const resolved = router.resolve(target)
      return router.resolve({
        path: resolved.path,
        query: { ...resolved.query, resourcePreview: 'cover' },
        hash: resolved.hash,
      }).href
    } catch {}
  }

  return router.resolve({
    name: 'resource-detail',
    query: {
      id: String(resource?.id || ''),
      resourcePreview: 'cover',
    },
  }).href
}

function resourceQualityScore(resource) {
  const score = Number(resourceQuality(resource).score)
  if (Number.isFinite(score)) return score
  if (Number.isFinite(resource?.matchScore)) return resource.matchScore
  return '--'
}

function hasResourceQuality(resource) {
  return Number.isFinite(resource?.matchScore)
    || Boolean(resourceQuality(resource).score)
    || Boolean(resourceCitationCount(resource))
    || Boolean(getEvaluation(resource?.id))
}

function getTypeName(type) {
  const names = {
    document: '课程讲义',
    mindmap: '思维导图',
    ppt: 'PPT',
    video: '视频',
    generated_video: 'AI 视频生成',
    animation: '动画微课',
    code: '代码示例',
    quiz: '练习题',
    herb_model: '药材模型辨识',
  }
  return names[type] || type
}

const resourceTypePalettes = {
  document: { background: '#eef2ff', foreground: '#4f46e5' },
  mindmap: { background: '#f3e8ff', foreground: '#7c3aed' },
  ppt: { background: '#e8f1ff', foreground: '#2563eb' },
  video: { background: '#e5f8f6', foreground: '#0f8f8a' },
  generated_video: { background: '#dff4f1', foreground: '#0e777d' },
  animation: { background: '#fff0f3', foreground: '#c2415d' },
  code: { background: '#e8f7ef', foreground: '#177a4e' },
  quiz: { background: '#fff7df', foreground: '#a16207' },
  simulator: { background: '#fff1e7', foreground: '#d66a08' },
  herb_model: { background: '#fce8e8', foreground: '#a33434' },
}

function getTypeColor(type) {
  return resourceTypePalettes[type]?.background || '#eef3f1'
}

function getTypeIconColor(type) {
  return resourceTypePalettes[type]?.foreground || '#176f4b'
}

function getMatchColor(score) {
  return score >= 80 ? '#202424' : score >= 60 ? '#555c5b' : '#747b7a'
}

function openResource(resource) {
  const target = String(resource?.route || '')
  if (target) {
    if (/^https?:\/\//i.test(target)) {
      window.open(target, '_blank', 'noopener,noreferrer')
    } else if (resource?.type === 'generated_video') {
      window.open(router.resolve(target).href, '_blank', 'noopener,noreferrer')
    } else {
      router.push(target)
    }
    return
  }
  localStorage.setItem('currentResourceDetail', JSON.stringify(resource))
  router.push({ name: 'resource-detail', query: { id: resource.id } })
}

function wait(milliseconds) {
  return new Promise(resolve => window.setTimeout(resolve, milliseconds))
}

async function waitForResourceTask(taskId) {
  for (let attempt = 0; attempt < 180; attempt += 1) {
    const response = await getXiaoZhiTask(taskId)
    const task = response?.data?.task
    if (!task) throw new Error('后台资源任务不存在')
    if (task.status === 'complete') return task
    if (task.status === 'failed') throw new Error(task.error || task.result?.qualityError || '资源任务未通过审核')
    await wait(1500)
  }
  throw new Error('资源任务仍在后台运行，请稍后在历史资源中查看')
}

async function generateNewResource() {
  if (generating.value) return
  generating.value = true

  try {
    if (!hasProfile.value) {
      router.push('/learning-profile')
      return
    }
    const analysis = profileData.value?.aiAnalysis || {}
    const focus = analysis.weaknesses?.[0] || analysis.weakPoints?.[0] || '当前学习目标与薄弱点'
    const response = await startPersonalizedResourceAgentTask({
      resourceType: 'personalized_resources',
      topic: `${focus}个性化资源包`,
      prompt: '根据当前激活画像、学习路径与最近学习证据生成多类型资源包。',
      params: {
        profileReportId: profileData.value?.id,
      },
    })
    const task = response?.data?.task
    if (!task?.taskId) throw new Error('资源智能体未创建后台任务')
    await waitForResourceTask(task.taskId)
    await loadResources()
  } catch (e) {
    console.error('生成资源失败:', e)
    const msg = e.message || '生成失败，请稍后重试'
    alert(msg.includes('AI API') ? msg : `生成失败：${msg}`)
  } finally {
    generating.value = false
  }
}

function getDefaultTitle(type) {
  return defaultResourceTitle(type)
}

function getDefaultDesc(type) {
  return `基于您的学习画像生成的${getTypeName(type)}资源`
}

function formatResourceTime(value) {
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return ''
  return date.toLocaleString('zh-CN', {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    hour12: false,
  })
}
</script>

<style scoped>
.resources-page {
  position: relative;
  height: calc(100vh - 72px);
  min-height: calc(100vh - 72px);
  overflow-y: auto;
  overflow-x: hidden;
  scrollbar-gutter: stable;
  background: #f8f8f8;
  padding: 42px 24px 64px;
}

.resources-page::before,
.resources-page::after {
  display: none;
}

.resources-page::before {
  width: 250px;
  height: 250px;
  right: -34px;
  top: 118px;
  opacity: 0.45;
  background: repeating-linear-gradient(-35deg, rgba(167, 226, 213, 0.42) 0 2px, transparent 2px 8px);
}

.resources-page::after {
  width: 255px;
  height: 255px;
  left: -108px;
  top: 420px;
  opacity: 0.32;
  background: repeating-linear-gradient(-35deg, rgba(167, 226, 213, 0.45) 0 2px, transparent 2px 8px);
}

.resources-corner-illustration {
  position: fixed;
  left: 0;
  bottom: 0;
  z-index: 1;
  width: 168px;
  max-width: 14vw;
  pointer-events: none;
  user-select: none;
}

.resources-page::-webkit-scrollbar {
  width: 10px;
}

.resources-page::-webkit-scrollbar-track {
  background: #edf6f2;
}

.resources-page::-webkit-scrollbar-thumb {
  border: 2px solid #edf6f2;
  border-radius: 999px;
  background: #b8ddd1;
}

.resources-page::-webkit-scrollbar-thumb:hover {
  background: #8ecfba;
}

.resources-header {
  position: relative;
  z-index: 2;
  max-width: 1260px;
  text-align: left;
  margin: 0 auto 16px;
}

.resources-header h1 {
  font-size: 26px;
  font-weight: 700;
  color: #173533;
  margin: 0;
  line-height: 1.2;
}

.no-profile-banner {
  max-width: 1200px;
  margin: 0 auto 24px;
  padding: 12px 20px;
  background: linear-gradient(135deg, #fef9ee, #fef3cd);
  border: 1px solid #f59e0b33;
  border-radius: 10px;
  display: flex;
  align-items: center;
  gap: 12px;
  font-size: 14px;
  color: #92400e;
}

.banner-icon {
  width: 20px;
  height: 20px;
  flex-shrink: 0;
  color: #f59e0b;
}

.banner-btn {
  margin-left: auto;
  padding: 6px 16px;
  background: linear-gradient(135deg, #21b978, #117a51);
  color: var(--surface, rgba(255, 255, 255, 0.94));
  border: none;
  border-radius: 6px;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  white-space: nowrap;
  transition: transform 0.2s, box-shadow 0.2s;
}

.banner-btn:hover {
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(31, 188, 191, 0.3);
}

.resource-tools-section {
  position: relative;
  z-index: 2;
  max-width: 1260px;
  margin: 0 auto 16px;
  padding: 24px 30px 28px;
  border: 1px solid #e5e7e7;
  border-radius: 8px;
  background: #ffffff;
  box-shadow: none;
}

.resource-tools-grid {
  display: grid;
  grid-template-columns: repeat(6, minmax(0, 1fr));
  gap: 12px;
}

.resource-tool-card {
  aspect-ratio: auto;
  min-height: 104px;
  padding: 14px;
  display: grid;
  grid-template-columns: 46px minmax(0, 1fr) 24px;
  align-items: center;
  gap: 10px;
  color: #1f3433;
  text-decoration: none;
  border: 1px solid #e5e7e7;
  border-radius: 6px;
  background: #ffffff;
  box-shadow: none;
  transition: transform 0.2s ease, box-shadow 0.2s ease, border-color 0.2s ease;
}

.resource-tool-card:hover {
  transform: none;
  border-color: #b9c3c0;
  box-shadow: none;
}

.resource-tool-icon {
  width: 38px;
  height: 38px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 6px;
  color: #176b50;
  background: #edf5f2;
}

.resource-tool-copy {
  display: grid;
  gap: 6px;
  min-width: 0;
}

.resource-tool-copy strong {
  color: #213a39;
  font-size: 15px;
  font-weight: 700;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.resource-tool-copy em {
  color: #667a77;
  font-size: 11px;
  font-style: normal;
  line-height: 1.45;
  display: -webkit-box;
  overflow: hidden;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
}

.resource-tool-card > svg {
  width: 18px;
  height: 18px;
  padding: 0;
  border: 0;
  border-radius: 0;
  color: #7a8381;
}

.resource-tool-card.tool-gold .resource-tool-icon {
  color: #9a7129;
  background: #fbf3e3;
}

.resource-tool-card.tool-gold {
  border-color: #eadcbc;
}

.resource-tool-card.tool-gold > svg {
  color: #9a7129;
}

.resource-tool-card.tool-blue .resource-tool-icon {
  color: #2f7de1;
  background: #e6f0ff;
}

.resource-tool-card.tool-blue {
  border-color: #d7e6ff;
}

.resource-tool-card.tool-blue > svg {
  color: #2f7de1;
}

.resource-tool-card.tool-purple .resource-tool-icon {
  color: #7c3aed;
  background: #f0e7ff;
}

.resource-tool-card.tool-purple {
  border-color: #e4d6ff;
}

.resource-tool-card.tool-purple > svg {
  color: #7c3aed;
}

.resource-tool-card.tool-teal .resource-tool-icon {
  color: #f26a2e;
  background: #fff0e8;
}

.resource-tool-card.tool-teal {
  border-color: #f6dacb;
}

.resource-tool-card.tool-teal > svg {
  color: #f26a2e;
}

.resource-tool-card.tool-orange .resource-tool-icon {
  color: #0e9f6e;
  background: #e5f9ef;
}

.resource-tool-card.tool-orange {
  border-color: #d3f0e1;
}

.resource-tool-card.tool-orange > svg {
  color: #0e9f6e;
}

.resource-tool-card.tool-coral .resource-tool-icon {
  color: #c2415d;
  background: #fff0f3;
}

.resource-tool-card.tool-coral {
  border-color: #f4d6dc;
}

.resource-tool-card.tool-coral > svg {
  color: #c2415d;
}

.resource-tool-card.tool-red .resource-tool-icon {
  color: #b94a3c;
  background: #fff0ed;
}

.resource-tool-card.tool-red {
  border-color: #f2d2cb;
}

.resource-tool-card.tool-red > svg {
  color: #b94a3c;
}

.resources-content {
  position: relative;
  z-index: 2;
  max-width: 1260px;
  margin: 0 auto;
  padding: 28px 30px 34px;
  border: 1px solid #e5e7e7;
  border-radius: 8px;
  background: #ffffff;
  box-shadow: none;
}

.history-resources-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 18px;
  margin: 0 0 16px;
  padding-left: 0;
  border-left: 0;
  border-radius: 0;
}

.history-resources-head h2 {
  margin: 0;
  color: #1f3433;
  font-size: 24px;
  font-weight: 700;
}

.history-resources-head h2::before {
  content: "历史资源";
}

.history-resources-head h2 {
  font-size: 0;
}

.history-resources-head h2::before {
  font-size: 24px;
}

.history-resources-head h2::after {
  content: "按生成时间记录智能体为当前用户保存的学习资源";
  display: block;
  margin-top: 4px;
  color: #6f8581;
  font-size: 14px;
  font-weight: 400;
}

.category-tabs {
  display: flex;
  gap: 14px;
  flex-wrap: wrap;
  margin-bottom: 20px;
  justify-content: flex-start;
}

.tab-btn {
  min-width: 76px;
  padding: 9px 20px;
  border: 1px solid #e7edf0;
  background: var(--surface, rgba(255, 255, 255, 0.94));
  border-radius: 999px;
  font-size: 14px;
  color: #64748b;
  cursor: pointer;
  transition: all 0.2s;
}

.tab-btn:hover {
  border-color: #21b978;
  color: #21b978;
}

.tab-btn.active {
  background: linear-gradient(135deg, #21b978, #117a51);
  color: var(--surface, rgba(255, 255, 255, 0.94));
  border-color: transparent;
}

.action-bar {
  position: absolute;
  top: 28px;
  right: 30px;
  display: flex;
  justify-content: flex-start;
  align-items: center;
  margin-bottom: 0;
}

.resource-count {
  display: none;
  font-size: 14px;
  color: #64748b;
}

.generate-btn {
  display: flex;
  align-items: center;
  gap: 8px;
  min-height: 44px;
  padding: 0 24px;
  background: linear-gradient(135deg, #21b978, #117a51);
  color: var(--surface, rgba(255, 255, 255, 0.94));
  border: none;
  border-radius: 12px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: transform 0.2s, box-shadow 0.2s;
  font-size: 0;
}

.generate-btn::after {
  content: "生成新资源";
  font-size: 14px;
  font-weight: 600;
}

.history-generate-btn {
  flex: 0 0 auto;
  box-shadow: 0 12px 24px rgba(17, 122, 81, 0.2);
}

.generate-btn:hover:not(:disabled) {
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(31, 188, 191, 0.3);
}

.generate-btn:disabled {
  opacity: 0.7;
  cursor: not-allowed;
}

.generate-btn svg {
  width: 18px;
  height: 18px;
}

.loading-spinner {
  width: 16px;
  height: 16px;
  border: 2px solid rgba(255, 255, 255, 0.3);
  border-top-color: var(--surface, rgba(255, 255, 255, 0.94));
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.resources-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 16px 18px;
}

.resource-card {
  min-height: 132px;
  width: 100%;
  background: rgba(255, 255, 255, 0.96);
  border-radius: 14px;
  padding: 20px;
  display: flex;
  align-items: flex-start;
  gap: 16px;
  cursor: pointer;
  transition: all 0.2s;
  box-shadow: 0 10px 28px rgba(31, 72, 66, 0.06);
  border: 1px solid #edf2f1;
  color: inherit;
  font: inherit;
  text-align: left;
}

.resource-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 24px rgba(15, 23, 42, 0.08);
  border-color: #21b978;
}

.card-icon {
  width: 58px;
  height: 58px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.card-icon svg {
  width: 24px;
  height: 24px;
  color: currentColor;
}

.card-content {
  flex: 1;
  min-width: 0;
}

.card-content h3 {
  font-size: 16px;
  font-weight: 600;
  color: #1f3f3b;
  margin: 0 0 8px;
  line-height: 1.4;
}

.card-desc {
  font-size: 13px;
  color: #64748b;
  margin: 0 0 12px;
  line-height: 1.5;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.card-footer {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.type-tag {
  padding: 4px 10px;
  background: rgba(31, 188, 191, 0.1);
  color: #117a51;
  border-radius: 4px;
  font-size: 12px;
  font-weight: 500;
}

.history-time {
  color: #7a8583;
  font-size: 11px;
  white-space: nowrap;
}

.match-score {
  font-size: 13px;
  font-weight: 600;
}

.quality-badge,
.citation-badge {
  padding: 3px 7px;
  border: 1px solid #d8e8e1;
  border-radius: 4px;
  color: #365f50;
  background: #f3f8f5;
  font-size: 11px;
  font-weight: 700;
}

.citation-badge {
  color: #71571f;
  border-color: #eadfbd;
  background: #fbf8ed;
}

.card-arrow {
  color: #94a3b8;
  flex-shrink: 0;
  margin-top: 4px;
}

.card-arrow svg {
  width: 20px;
  height: 20px;
}

.empty-state {
  text-align: center;
  padding: 60px 20px;
  color: #94a3b8;
}

.empty-state svg {
  width: 48px;
  height: 48px;
  margin-bottom: 16px;
}

.empty-state p {
  font-size: 14px;
  margin: 0;
}

.history-resources-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}

.history-refresh-btn,
.history-status button,
.history-error button {
  display: inline-flex;
  min-height: 34px;
  align-items: center;
  justify-content: center;
  gap: 6px;
  border: 1px solid #cbd9d3;
  border-radius: 6px;
  background: #fff;
  padding: 0 11px;
  color: #27664f;
  font: inherit;
  font-size: 12px;
  font-weight: 700;
  cursor: pointer;
}

.history-refresh-btn:disabled {
  cursor: wait;
  opacity: 0.58;
}

.history-status {
  display: flex;
  align-items: center;
  gap: 9px;
  margin: 14px 0 2px;
  border-left: 3px solid #a7771c;
  background: #fff8e8;
  padding: 11px 13px;
  color: #73581e;
  font-size: 13px;
}

.history-status span {
  min-width: 0;
  flex: 1;
}

.history-status button {
  flex: 0 0 auto;
  border-color: #e2cb91;
  color: #73581e;
}

.history-loading,
.history-error {
  display: grid;
  min-height: 260px;
  place-content: center;
  justify-items: center;
  gap: 9px;
  padding: 36px 20px;
  text-align: center;
}

.history-loading {
  color: #287356;
}

.history-error {
  color: #a34431;
}

.history-loading strong,
.history-error strong {
  color: #30483f;
  font-size: 15px;
}

.history-loading span,
.history-error span {
  max-width: 520px;
  color: #72817b;
  font-size: 13px;
  line-height: 1.6;
}

.status-banner svg {
  flex: 0 0 auto;
}

.error-banner {
  border-color: #e4bdb4;
  background: #fff1ed;
  color: #99462f;
}

.spin {
  animation: history-spin 0.85s linear infinite;
}

@keyframes history-spin {
  to { transform: rotate(360deg); }
}

.learned-badge {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 3px 10px;
  background: #10b98118;
  color: #059669;
  border-radius: 4px;
  font-size: 12px;
  font-weight: 600;
}

.learned-badge svg {
  width: 14px;
  height: 14px;
}

.badge-stars {
  display: inline-flex;
  align-items: center;
  margin-left: 2px;
}

.mini-star {
  width: 12px;
  height: 12px;
}

/* The resource hub follows the same flat black-and-white system as the docs UI. */
.resources-page {
  color: #202323;
  background: #fbfbfb;
  scrollbar-color: #c4c9c8 #f1f2f2;
}

.resources-page::-webkit-scrollbar-track {
  background: #f1f2f2;
}

.resources-page::-webkit-scrollbar-thumb {
  border-color: #f1f2f2;
  background: #c4c9c8;
}

.resources-header {
  border-color: #e3e6e5;
}

.resources-header h1,
.resource-tools-head h2,
.history-resources-head h2,
.resource-tool-copy strong,
.card-content h3 {
  color: #171919;
}

.resources-header p,
.resource-tools-head p,
.resource-tool-copy em,
.card-desc,
.resource-count {
  color: #747b7a;
}

.no-profile-banner {
  border-color: #dfe3e2;
  border-radius: 6px;
  background: #ffffff;
  color: #4f5655;
}

.no-profile-banner svg {
  color: #5d6463;
}

.resource-tools-section,
.resources-content {
  border: 0;
  border-radius: 0;
  background: transparent;
  box-shadow: none;
}

.resource-tools-section {
  padding: 0;
}

.resources-content {
  padding: 26px 0 34px;
}

.resource-tool-card,
.resource-tool-card.tool-gold,
.resource-tool-card.tool-blue,
.resource-tool-card.tool-purple,
.resource-tool-card.tool-teal,
.resource-tool-card.tool-orange,
.resource-tool-card.tool-coral,
.resource-tool-card.tool-red {
  min-height: 104px;
  border-color: #e1e4e3;
  border-radius: 6px;
  background: #ffffff;
  box-shadow: none;
}

.resource-tool-card:hover {
  border-color: #aeb5b4;
  background: #f8f9f9;
  transform: none;
}

.resource-tool-card .resource-tool-icon,
.resource-tool-card.tool-gold .resource-tool-icon,
.resource-tool-card.tool-blue .resource-tool-icon,
.resource-tool-card.tool-purple .resource-tool-icon,
.resource-tool-card.tool-teal .resource-tool-icon,
.resource-tool-card.tool-orange .resource-tool-icon,
.resource-tool-card.tool-coral .resource-tool-icon,
.resource-tool-card.tool-red .resource-tool-icon {
  border: 1px solid #e2e5e4;
  border-radius: 6px;
  background: #f0f1f1;
  color: #303534;
}

.resource-tool-card > svg,
.resource-tool-card.tool-gold > svg,
.resource-tool-card.tool-blue > svg,
.resource-tool-card.tool-purple > svg,
.resource-tool-card.tool-teal > svg,
.resource-tool-card.tool-orange > svg,
.resource-tool-card.tool-coral > svg,
.resource-tool-card.tool-red > svg {
  color: #737a79;
}

.category-tabs {
  gap: 6px;
}

.tab-btn {
  min-width: 68px;
  padding: 8px 14px;
  border-color: #dfe3e2;
  border-radius: 6px;
  background: #ffffff;
  color: #5e6564;
}

.tab-btn:hover,
.tab-btn.active {
  border-color: #9ab8aa;
  background: #edf5f1;
  color: #176f4b;
}

.generate-btn,
.generate-btn:hover:not(:disabled) {
  min-height: 40px;
  border: 1px solid #176f4b;
  border-radius: 6px;
  background: #176f4b;
  color: #ffffff;
  box-shadow: none;
  transform: none;
}

.resource-card {
  min-height: 126px;
  border-color: #e1e4e3;
  border-radius: 6px;
  background: #ffffff;
  box-shadow: none;
}

.resource-card:hover {
  border-color: #aeb5b4;
  background: #fafafa;
  box-shadow: none;
  transform: none;
}

.card-icon {
  border: 1px solid #e1e4e3;
  border-radius: 6px;
}

.card-icon svg {
  color: currentColor;
  fill: none;
}

.card-arrow,
.card-arrow svg,
.mini-star {
  color: #4e5554;
  fill: currentColor;
}

.type-tag,
.learned-badge,
.quality-badge,
.citation-badge {
  border: 1px solid #dfe3e2;
  border-radius: 4px;
  background: #f1f2f2;
  color: #4c5352;
}

.empty-state,
.empty-state svg {
  color: #858b8a;
}

@media (max-width: 1100px) {
  .resource-tools-grid {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }
}

@media (max-width: 640px) {
  .resources-page {
    padding: 24px 16px calc(128px + env(safe-area-inset-bottom));
    scroll-padding-bottom: calc(128px + env(safe-area-inset-bottom));
  }

  .resource-tools-section {
    padding: 18px;
  }

  .resource-tools-grid {
    grid-template-columns: 1fr;
  }

  .history-status {
    align-items: flex-start;
    flex-wrap: wrap;
  }

  .history-status button {
    margin-left: 27px;
  }

  .resources-header h1 {
    font-size: 22px;
  }

  .category-tabs {
    gap: 6px;
  }

  .tab-btn {
    padding: 6px 14px;
    font-size: 13px;
  }

  .resources-grid {
    grid-template-columns: 1fr;
  }

  .resource-card {
    padding: 16px;
  }

  .action-bar {
    flex-direction: column;
    gap: 12px;
    align-items: stretch;
  }

  .generate-btn {
    justify-content: center;
    min-height: 44px;
  }

  .banner-btn,
  .tab-btn {
    min-height: 44px;
  }

  .resource-card,
  .tool-card {
    scroll-margin-bottom: calc(128px + env(safe-area-inset-bottom));
  }
}

/* Resource hub refresh: hover effects only use composited properties, so cards never reflow. */
.resources-page {
  min-height: 100%;
  padding: 36px 56px 64px;
  background: #ffffff;
}

.resources-page::before,
.resources-page::after {
  display: none;
}

.resources-header {
  max-width: none;
  margin: 0 0 22px;
  padding-bottom: 22px;
  border-bottom: 1px solid #e7ebef;
}

.resources-header h1,
.resources-header h1::before,
.resource-tools-head h2,
.resource-tools-head h2::before,
.history-resources-head h2,
.history-resources-head h2::before {
  color: #171d26;
}

.resources-header p,
.resources-header p::before,
.resource-tools-head p,
.resource-tools-head p::before,
.history-resources-head h2::after {
  color: #657080;
}

.resource-tools-section,
.resources-content {
  max-width: none;
  margin: 0;
  padding: 0;
  border: 0;
  border-radius: 0;
  background: transparent;
  box-shadow: none;
}

.resource-tools-section {
  padding-bottom: 40px;
}

.resource-tools-head {
  margin-bottom: 20px;
}

.resource-tools-grid {
  gap: 16px;
}

.resource-tool-card {
  min-height: 132px;
  padding: 18px 16px;
  grid-template-columns: 48px minmax(0, 1fr) 18px;
  border-color: #e8edf2;
  border-radius: 8px;
  background: #ffffff;
  box-shadow: 0 1px 2px rgba(19, 31, 45, 0.02);
  will-change: transform;
  transition: transform 180ms ease, box-shadow 180ms ease, border-color 180ms ease;
}

.resource-tool-card:hover {
  transform: translateY(-5px);
  border-color: #b9d9cd;
  box-shadow: 0 12px 24px rgba(23, 72, 58, 0.12);
}

.resource-tool-card:focus-visible,
.resource-card:focus-visible {
  outline: 3px solid rgba(16, 150, 102, 0.24);
  outline-offset: 3px;
}

.resource-tool-card .resource-tool-icon {
  width: 46px;
  height: 46px;
  border-radius: 8px;
  transition: transform 180ms ease;
}

.resource-tool-card:hover .resource-tool-icon {
  transform: scale(1.07) rotate(-3deg);
}

.resource-tool-card > svg {
  transition: transform 180ms ease;
}

.resource-tool-card:hover > svg {
  transform: translateX(4px);
}

.resource-tool-copy strong {
  color: #151b24;
}

.resource-tool-copy em {
  color: #657080;
  font-size: 12px;
}

.resources-content {
  padding-top: 4px;
}

.history-resources-head {
  margin-bottom: 16px;
}

.history-resources-head h2::after {
  display: none;
}

.category-tabs {
  gap: 12px;
  margin-bottom: 18px;
}

.tab-btn {
  min-width: 0;
  padding: 8px 18px;
  border-radius: 7px;
  color: #4b5563;
  background: #ffffff;
  transition: color 160ms ease, background-color 160ms ease, border-color 160ms ease, transform 160ms ease;
}

.tab-btn:hover {
  transform: translateY(-1px);
  border-color: #8bcdb5;
  color: #087a55;
}

.tab-btn.active {
  color: #087a55;
  border-color: #a6d9c4;
  background: #ecf8f2;
}

.action-bar {
  top: 4px;
  right: 0;
}

.generate-btn {
  min-height: 42px;
  padding: 0 18px;
  border-radius: 6px;
  background: #07855b;
  box-shadow: 0 4px 10px rgba(7, 133, 91, 0.16);
  transition: transform 180ms ease, background-color 180ms ease, box-shadow 180ms ease;
}

.generate-btn:hover:not(:disabled) {
  transform: translateY(-2px);
  background: #056c4a;
  box-shadow: 0 9px 18px rgba(7, 133, 91, 0.24);
}

.resources-grid {
  gap: 16px;
}

.resource-card {
  position: relative;
  min-height: 184px;
  padding: 22px;
  border: 1px solid #e7ebef;
  border-radius: 8px;
  background: #ffffff;
  box-shadow: none;
  will-change: transform;
  transition: transform 200ms ease, box-shadow 200ms ease, border-color 200ms ease;
}

.resource-card:hover {
  transform: translateY(-5px);
  border-color: #92cdb7;
  box-shadow: 0 14px 30px rgba(22, 59, 49, 0.13);
}

.card-icon {
  width: 60px;
  height: 60px;
  border-radius: 8px;
  transition: transform 200ms ease;
}

.resource-card:hover .card-icon {
  transform: scale(1.06) rotate(-3deg);
}

.card-content h3 {
  padding-right: 20px;
  color: #171d26;
}

.card-desc {
  color: #657080;
}

.card-arrow {
  position: absolute;
  top: 24px;
  right: 20px;
  color: #44505f;
  transition: transform 200ms ease, color 200ms ease;
}

.resource-card:hover .card-arrow {
  color: #07855b;
  transform: translateX(4px);
}

.type-tag,
.quality-badge,
.citation-badge,
.learned-badge {
  border-radius: 4px;
}

@media (max-width: 1100px) {
  .resources-page {
    padding: 32px 28px 52px;
  }

  .resource-tools-grid {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }
}

@media (max-width: 720px) {
  .resources-page {
    padding: 24px 18px 44px;
  }

  .resource-tools-grid,
  .resources-grid {
    grid-template-columns: 1fr;
  }

  .resource-tool-card,
  .resource-card {
    min-height: 0;
  }

  .history-resources-head {
    padding-right: 148px;
  }
}

/* History browsing uses a quiet utility layout instead of decorative AI-dashboard chrome. */
.history-head-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.history-head-actions .history-refresh-btn,
.history-head-actions .generate-btn {
  min-height: 38px;
  border-radius: 5px;
  box-shadow: none;
}

.history-head-actions .generate-btn {
  padding: 0 14px;
  font-size: 14px;
  background: #176b50;
}

.history-head-actions .generate-btn::after {
  display: none;
}

.history-head-actions .generate-btn:hover:not(:disabled) {
  transform: none;
  background: #115640;
  box-shadow: none;
}

.history-controls {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 20px;
  margin: 18px 0 12px;
}

.history-controls .category-tabs {
  min-width: 0;
  margin: 0;
  gap: 6px;
}

.history-controls .tab-btn {
  min-height: 38px;
  padding: 0 13px;
  border-color: transparent;
  border-radius: 4px;
  background: transparent;
  color: #55615e;
  transition: color 140ms ease, background-color 140ms ease;
}

.history-controls .tab-btn:hover {
  transform: none;
  border-color: transparent;
  background: #f1f4f3;
  color: #1c4f40;
}

.history-controls .tab-btn.active {
  border-color: transparent;
  background: #e8f1ed;
  color: #165d47;
  font-weight: 700;
}

.history-search {
  flex: 0 1 320px;
  display: grid;
  grid-template-columns: 18px minmax(0, 1fr) 28px;
  align-items: center;
  min-width: 240px;
  min-height: 40px;
  padding: 0 7px 0 11px;
  border: 1px solid #d8dfdc;
  border-radius: 5px;
  background: #ffffff;
  color: #68736f;
}

.history-search:focus-within {
  border-color: #6da58f;
  box-shadow: 0 0 0 3px rgba(23, 107, 80, 0.1);
}

.history-search input {
  width: 100%;
  min-width: 0;
  border: 0;
  outline: 0;
  background: transparent;
  padding: 0 8px;
  color: #1b2522;
  font: inherit;
  font-size: 13px;
}

.history-search input::placeholder {
  color: #8b9491;
}

.history-search input::-webkit-search-cancel-button {
  display: none;
}

.history-search button {
  width: 28px;
  height: 28px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border: 0;
  border-radius: 4px;
  background: transparent;
  color: #6f7976;
  cursor: pointer;
}

.history-search button:hover {
  background: #eef2f0;
  color: #244c40;
}

.history-result-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  min-height: 36px;
  margin-bottom: 12px;
  border-top: 1px solid #edf0ef;
  color: #6b7572;
  font-size: 12px;
}

.history-result-bar .resource-count {
  display: inline;
  color: inherit;
  font-size: inherit;
}

.page-summary {
  white-space: nowrap;
}

.resource-tool-card[class*="tool-"] {
  min-height: 108px;
  border-color: #e4e8e6;
  background: #ffffff;
}

.resource-tools-section {
  padding: 0 0 28px;
}

.resource-tools-grid {
  gap: 0;
  border-top: 1px solid #e4e8e6;
  border-bottom: 1px solid #e4e8e6;
}

.resource-tool-card {
  min-height: 68px;
  padding: 10px 14px;
  grid-template-columns: 34px minmax(0, 1fr) 16px;
  gap: 9px;
  border: 0;
  border-right: 1px solid #e8ecea;
  border-radius: 0;
  background: transparent;
  box-shadow: none;
}

.resource-tool-card:last-child {
  border-right: 0;
}

.resource-tool-card .resource-tool-icon {
  width: 32px;
  height: 32px;
  border-radius: 4px;
  background: #edf3f0;
  color: #2b6c57;
}

.resource-tool-card .resource-tool-icon svg {
  width: 19px;
  height: 19px;
}

.resource-tool-copy {
  display: block;
}

.resource-tool-copy strong {
  font-size: 14px;
}

.resource-tool-card:hover {
  transform: none;
  border-color: #e8ecea;
  background: #f6f8f7;
  box-shadow: none;
}

.resource-tool-card[class*="tool-"] .resource-tool-icon {
  width: 40px;
  height: 40px;
  border-radius: 5px;
  background: #edf3f0;
  color: #2b6c57;
}

.resource-tool-card[class*="tool-"] > svg {
  color: #75807c;
}

.resource-tool-card[class*="tool-"]:hover {
  transform: none;
  border-color: #9cbcaf;
  background: #fbfcfc;
  box-shadow: none;
}

.resource-tool-card:hover .resource-tool-icon,
.resource-tool-card:hover > svg {
  transform: none;
}

.resource-card {
  min-height: 146px;
  padding: 18px 8px 18px 0;
  border: 0;
  border-top: 1px solid #e1e6e4;
  border-radius: 0;
}

.resource-card:hover {
  transform: none;
  border-color: #c9d5d0;
  background: transparent;
  box-shadow: none;
}

.resource-card .card-icon {
  width: 38px;
  height: 38px;
  border-radius: 4px;
  background: transparent !important;
  color: #356957 !important;
}

.resource-card .card-icon svg {
  width: 21px;
  height: 21px;
}

.resource-card:hover .card-icon,
.resource-card:hover .card-arrow {
  transform: none;
}

.card-content h3 {
  margin-bottom: 6px;
  font-weight: 650;
}

.card-footer {
  gap: 7px 10px;
}

.type-tag,
.quality-badge,
.citation-badge,
.learned-badge {
  padding: 0;
  border: 0;
  border-radius: 0;
  background: transparent;
  color: #68736f;
  font-size: 11px;
  font-weight: 500;
}

.match-score {
  color: #68736f !important;
  font-size: 11px;
  font-weight: 500;
}

.history-pagination {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 4px;
  margin-top: 24px;
  padding-top: 18px;
  border-top: 1px solid #edf0ef;
}

.page-nav-btn,
.page-number-btn {
  width: 34px;
  height: 34px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border: 1px solid transparent;
  border-radius: 4px;
  background: transparent;
  color: #4f5b57;
  font: inherit;
  font-size: 12px;
  cursor: pointer;
}

.page-nav-btn:hover:not(:disabled),
.page-number-btn:hover {
  background: #f0f3f2;
  color: #174f3e;
}

.page-number-btn.active {
  border-color: #9bbcaf;
  background: #e9f1ee;
  color: #165d47;
  font-weight: 700;
}

.page-nav-btn:disabled {
  opacity: 0.32;
  cursor: not-allowed;
}

.page-ellipsis {
  width: 24px;
  color: #909895;
  text-align: center;
}

.empty-state button {
  margin-top: 12px;
  border: 0;
  background: transparent;
  color: #176b50;
  font: inherit;
  font-size: 13px;
  cursor: pointer;
}

@media (max-width: 1100px) {
  .history-controls {
    align-items: stretch;
    flex-direction: column-reverse;
    gap: 12px;
  }

  .history-search {
    flex-basis: auto;
    width: min(100%, 420px);
  }
}

@media (max-width: 720px) {
  .history-resources-head {
    align-items: flex-start;
    padding-right: 0;
  }

  .history-head-actions {
    flex-wrap: wrap;
    justify-content: flex-end;
  }

  .history-controls .category-tabs {
    flex-wrap: nowrap;
    overflow-x: auto;
    padding-bottom: 4px;
  }

  .history-controls .tab-btn {
    flex: 0 0 auto;
  }

  .history-search {
    width: 100%;
    min-width: 0;
  }
}

/* Archive workspace: document-first navigation and stable table rows. */
.resources-page {
  padding: 34px 52px 64px;
  background: #fbfcfb;
}

.resources-page button {
  border-radius: 4px !important;
  box-shadow: none !important;
}

.resources-header {
  margin: 0 0 28px;
  padding: 0 0 18px;
}

.resources-header h1 {
  font-size: 25px;
  line-height: 1.25;
}

.resource-workspace {
  display: grid;
  grid-template-columns: 210px minmax(0, 1fr);
  align-items: start;
  gap: 32px;
}

.resource-tool-sidebar {
  position: sticky;
  top: 94px;
  min-width: 0;
  padding-right: 24px;
  border-right: 1px solid #dfe5e2;
}

.sidebar-heading,
.archive-heading,
.archive-heading > div,
.archive-actions,
.archive-result-line {
  display: flex;
  align-items: center;
}

.sidebar-heading {
  justify-content: space-between;
  min-height: 42px;
  margin-bottom: 8px;
}

.sidebar-heading h2,
.archive-heading h2 {
  margin: 0;
  color: #18211e;
  letter-spacing: 0;
}

.sidebar-heading h2 {
  font-size: 14px;
  font-weight: 700;
}

.sidebar-heading > span {
  color: #89918e;
  font-size: 12px;
}

.resource-tool-list {
  display: grid;
  gap: 2px;
}

.resource-tool-row {
  display: grid;
  grid-template-columns: 24px minmax(0, 1fr) 16px;
  align-items: center;
  gap: 9px;
  min-height: 46px;
  padding: 0 8px;
  border-radius: 4px;
  color: #3f4c47;
  text-decoration: none;
  transition: color 140ms ease, background-color 140ms ease;
}

.resource-tool-row > svg:first-child {
  color: #477565;
}

.resource-tool-row > svg:last-child {
  color: #9aa29f;
}

.resource-tool-row span {
  overflow: hidden;
  font-size: 13px;
  font-weight: 600;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.resource-tool-row:hover {
  background: #edf2ef;
  color: #164f3d;
}

.resource-archive {
  min-width: 0;
}

.archive-heading {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  min-height: 50px;
  padding-bottom: 14px;
  border-bottom: 1px solid #dfe5e2;
}

.archive-title {
  gap: 10px;
  white-space: nowrap;
}

.archive-heading h2 {
  font-size: 20px;
  font-weight: 700;
}

.archive-heading > div:first-child > span {
  color: #7b8581;
  font-size: 12px;
}

.archive-actions {
  margin-left: auto;
  gap: 8px;
  white-space: nowrap;
}

.archive-heading .archive-search {
  width: 100%;
  min-width: 220px;
  max-width: 320px;
  min-height: 36px;
  border-radius: 4px;
}

.archive-heading .archive-search input {
  border: 0 !important;
  border-radius: 0 !important;
  background: transparent !important;
  box-shadow: none !important;
}

.archive-actions .type-filter {
  width: 170px;
  min-height: 36px;
}

.archive-actions .type-filter select {
  border: none !important;
  box-shadow: none !important;
}

.archive-actions .history-refresh-btn {
  width: 36px;
  min-height: 36px;
  padding: 0;
  border-color: #d7dfdc !important;
  border-radius: 4px !important;
  background: #ffffff !important;
  box-shadow: none !important;
  color: #52615c !important;
  font-weight: 500;
}

.archive-actions .history-refresh-btn:hover:not(:disabled) {
  border-color: #b8c7c1 !important;
  background: #f3f6f5 !important;
  color: #244c40 !important;
}

.archive-actions .generate-btn {
  min-height: 36px;
  padding: 0 13px;
  border-color: #176b50 !important;
  border-radius: 4px !important;
  background: #176b50 !important;
  box-shadow: none !important;
  color: #ffffff !important;
  font-size: 13px;
}

.archive-actions .generate-btn::after {
  display: none;
}

.archive-actions .generate-btn:hover:not(:disabled) {
  transform: none;
  border-color: #115640 !important;
  background: #115640 !important;
  box-shadow: none !important;
}

.archive-toolbar {
  display: grid;
  grid-template-columns: minmax(280px, 1fr);
  margin: 18px 0 10px;
}

.archive-toolbar .history-search {
  width: 100%;
  min-width: 0;
  max-width: none;
  min-height: 38px;
  border-radius: 4px;
}

.archive-toolbar .history-search input {
  border: 0 !important;
  border-radius: 0 !important;
  background: transparent !important;
  box-shadow: none !important;
}

.archive-toolbar .history-search button {
  border: 0 !important;
  border-radius: 3px !important;
  background: transparent !important;
  box-shadow: none !important;
  color: #6f7976 !important;
}

.archive-toolbar .history-search button:hover {
  background: #eef2f0 !important;
  color: #244c40 !important;
}

.type-filter {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr);
  align-items: center;
  gap: 9px;
  min-height: 38px;
  padding: 0 9px 0 11px;
  border: 1px solid #d8dfdc;
  border-radius: 4px;
  background: #fff;
  color: #77817d;
  font-size: 12px;
}

.type-filter select {
  min-width: 0;
  border: 0 !important;
  border-radius: 0 !important;
  outline: 0;
  background: transparent !important;
  box-shadow: none !important;
  color: #29332f;
  font: inherit;
  font-size: 13px;
  cursor: pointer;
}

.archive-result-line {
  justify-content: space-between;
  min-height: 34px;
  color: #78817e;
  font-size: 11px;
}

.archive-result-line > span:last-child {
  margin-left: auto;
}

.resource-table {
  border-top: 1px solid #dfe5e2;
}

.resource-table-head,
.resource-table-row {
  display: grid;
  grid-template-columns: minmax(300px, 1fr) 108px 116px minmax(145px, 0.6fr) 24px;
  align-items: center;
  gap: 18px;
}

.resource-table-head {
  min-height: 38px;
  padding: 0 10px;
  border-bottom: 1px solid #dfe5e2;
  color: #737d79;
  font-size: 11px;
  font-weight: 600;
}

.resource-table-row {
  width: 100%;
  min-height: 82px;
  padding: 10px;
  border: 0;
  border-bottom: 1px solid #e6ebe9;
  border-radius: 0 !important;
  background: transparent;
  box-shadow: none !important;
  color: inherit;
  font: inherit;
  text-align: left;
  cursor: pointer;
  outline: 0;
  transition: background-color 140ms ease;
}

.resource-table-row:hover {
  transform: none !important;
  background: #f2f5f3;
  box-shadow: none !important;
}

.resource-table-row:focus-visible {
  position: relative;
  z-index: 1;
  outline: 2px solid #6fa18f;
  outline-offset: -2px;
}

.resource-name-cell {
  display: grid;
  grid-template-columns: 34px minmax(0, 1fr);
  align-items: center;
  gap: 11px;
  min-width: 0;
}

.resource-row-icon {
  width: 32px;
  height: 32px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border: 1px solid #dce5e1;
  border-radius: 4px;
  color: #356957;
  background: #f7f9f8;
}

.resource-name-cell > span:last-child {
  min-width: 0;
}

.resource-name-cell strong,
.resource-name-cell em {
  display: block;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.resource-name-cell strong {
  color: #1e2824;
  font-size: 13px;
  font-weight: 650;
  line-height: 1.45;
}

.resource-name-cell em {
  margin-top: 4px;
  color: #818a87;
  font-size: 11px;
  font-style: normal;
}

.resource-type-cell,
.resource-time-cell {
  overflow: hidden;
  color: #66716d;
  font-size: 12px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.resource-quality-cell {
  display: flex;
  align-items: center;
  gap: 5px 10px;
  min-width: 0;
  flex-wrap: wrap;
  color: #68736f;
  font-size: 11px;
}

.resource-open-icon {
  color: #929b97;
}

.resource-table-row:hover .resource-open-icon {
  color: #1f6950;
}

.resource-archive .history-loading,
.resource-archive .history-error,
.resource-archive .empty-state {
  min-height: 360px;
  border-bottom: 1px solid #e1e6e4;
}

.resource-archive .history-pagination {
  margin-top: 16px;
  padding-top: 0;
  border-top: 0;
}

.resource-archive .page-nav-btn,
.resource-archive .page-number-btn {
  border-color: transparent !important;
  border-radius: 3px !important;
  background: transparent !important;
  box-shadow: none !important;
  color: #4f5b57 !important;
}

.resource-archive .page-nav-btn:hover:not(:disabled),
.resource-archive .page-number-btn:hover {
  background: #f0f3f2 !important;
  color: #174f3e !important;
}

.resource-archive .page-number-btn.active {
  border-color: #9bbcaf !important;
  background: #e9f1ee !important;
  color: #165d47 !important;
}

@media (max-width: 1180px) {
  .resource-workspace {
    grid-template-columns: 180px minmax(0, 1fr);
    gap: 24px;
  }

  .resource-table-head,
  .resource-table-row {
    grid-template-columns: minmax(260px, 1fr) 92px 104px minmax(120px, 0.5fr) 20px;
    gap: 12px;
  }
}

@media (max-width: 900px) {
  .resources-page {
    padding: 28px 24px 52px;
  }

  .resource-workspace {
    grid-template-columns: 1fr;
  }

  .resource-tool-sidebar {
    position: static;
    padding: 0 0 18px;
    border-right: 0;
    border-bottom: 1px solid #dfe5e2;
  }

  .resource-tool-list {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }

  .resource-table-head {
    display: none;
  }

  .resource-table-row {
    grid-template-columns: minmax(0, 1fr) 24px;
    gap: 10px;
  }

  .resource-type-cell,
  .resource-time-cell,
  .resource-quality-cell {
    display: none;
  }
}

@media (max-width: 600px) {
  .archive-toolbar {
    grid-template-columns: 1fr;
  }

  .resource-tool-list {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

/* Resource portfolio: real page previews with restrained editorial cards. */
.resource-launchers {
  margin-bottom: 34px;
}

.section-line-heading {
  display: flex;
  align-items: center;
  min-height: 42px;
  margin-bottom: 10px;
}

.section-line-heading h2 {
  margin: 0;
  color: #1d2723;
  font-size: 17px;
  font-weight: 700;
  letter-spacing: 0;
}

.resource-launcher-grid {
  display: grid;
  grid-template-columns: repeat(6, minmax(0, 1fr));
  gap: 12px;
}

.resource-launcher {
  --launcher-accent: #168063;
  --launcher-surface: #f5fbf8;
  --launcher-icon-surface: #ddf3ea;
  --launcher-border: #d7ebe2;
  display: grid;
  grid-template-columns: 44px minmax(0, 1fr) 18px;
  align-items: center;
  gap: 13px;
  min-height: 88px;
  padding: 14px 15px;
  border: 1px solid var(--launcher-border);
  border-radius: 6px;
  background: var(--launcher-surface);
  color: #25312d;
  text-decoration: none;
  transition: border-color 150ms ease, background-color 150ms ease, transform 150ms ease;
}

.resource-launcher:hover {
  border-color: color-mix(in srgb, var(--launcher-accent) 42%, white);
  background: color-mix(in srgb, var(--launcher-surface) 70%, white);
  transform: translateY(-1px);
}

.resource-launcher:focus-visible,
.resource-cover-card:focus-visible {
  outline: 2px solid #6fa18f;
  outline-offset: 2px;
}

.launcher-icon {
  width: 44px;
  height: 44px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border: 0;
  border-radius: 5px;
  background: var(--launcher-icon-surface);
  color: var(--launcher-accent);
}

.launcher-copy {
  min-width: 0;
}

.launcher-copy strong {
  display: block;
}

.launcher-copy strong {
  color: #17231f;
  font-size: 15px;
  font-weight: 700;
  line-height: 1.3;
}

.resource-launcher > svg {
  color: var(--launcher-accent);
  opacity: 0.72;
}

.resource-launcher.launcher-amber {
  --launcher-accent: #a86812;
  --launcher-surface: #fffaf1;
  --launcher-icon-surface: #ffedc9;
  --launcher-border: #f1e2c3;
}

.resource-launcher.launcher-blue {
  --launcher-accent: #356fc1;
  --launcher-surface: #f5f8ff;
  --launcher-icon-surface: #e2ebff;
  --launcher-border: #dbe5f7;
}

.resource-launcher.launcher-violet {
  --launcher-accent: #7650ae;
  --launcher-surface: #faf7ff;
  --launcher-icon-surface: #ece3fa;
  --launcher-border: #e7def2;
}

.resource-launcher.launcher-coral {
  --launcher-accent: #b75c47;
  --launcher-surface: #fff8f6;
  --launcher-icon-surface: #fde6df;
  --launcher-border: #f1dfda;
}

.resource-launcher.launcher-cyan {
  --launcher-accent: #147987;
  --launcher-surface: #f3fbfc;
  --launcher-icon-surface: #dcf2f4;
  --launcher-border: #d5eaed;
}

.resource-archive {
  min-width: 0;
}

.resource-gallery {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 20px;
}

.resource-cover-card {
  min-width: 0;
  overflow: hidden;
  border: 1px solid #dfe4e2;
  border-radius: 6px;
  background: #ffffff;
  cursor: pointer;
  transition: transform 160ms ease, border-color 160ms ease, box-shadow 160ms ease;
}

.resource-cover-card:hover {
  transform: translateY(-2px);
  border-color: #a9beb5;
  box-shadow: 0 8px 22px rgba(31, 55, 46, 0.08);
}

.resource-cover-frame {
  position: relative;
  overflow: hidden;
  aspect-ratio: 2 / 1;
  border-bottom: 1px solid #e1e6e4;
  background: #f1f4f2;
  isolation: isolate;
}

.resource-live-cover {
  position: absolute;
  inset: 0 auto auto 0;
  z-index: 1;
  width: 300%;
  height: 300%;
  border: 0;
  opacity: 0;
  background: #f7f9f8;
  pointer-events: none;
  transform: scale(0.333333);
  transform-origin: 0 0;
  transition: opacity 180ms ease;
}

.resource-live-cover.loaded {
  opacity: 1;
}

.resource-static-cover {
  position: absolute;
  inset: 0;
  z-index: 1;
  width: 100%;
  height: 100%;
  object-fit: cover;
  border: 0;
  opacity: 0;
  background: #eef2ef;
  transition: opacity 180ms ease;
}

.resource-static-cover.loaded {
  opacity: 1;
}

.cover-loading {
  position: absolute;
  inset: 0;
  z-index: 0;
  display: grid;
  place-content: center;
  justify-items: center;
  gap: 9px;
  color: #6f7d77;
  font-size: 11px;
}

.cover-loading.hidden {
  visibility: hidden;
}

.resource-cover-copy {
  padding: 12px 14px 11px;
}

.resource-cover-copy h3 {
  margin: 0;
  overflow: hidden;
  color: #1c2723;
  font-size: 16px;
  font-weight: 700;
  line-height: 1.45;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.resource-cover-copy footer {
  display: grid;
  grid-template-columns: auto auto minmax(0, 1fr);
  align-items: center;
  gap: 8px;
  min-height: 20px;
  margin-top: 7px;
  color: #7b8581;
  font-size: 10px;
}

.resource-cover-copy footer time {
  overflow: hidden;
  text-align: right;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.resource-cover-copy footer span {
  white-space: nowrap;
}

@media (max-width: 1080px) {
  .archive-heading {
    gap: 12px;
  }

  .archive-actions .type-filter {
    width: 150px;
  }
}

@media (max-width: 1280px) {
  .resource-launcher-grid {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }
}

@media (max-width: 980px) {
  .resource-gallery {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 680px) {
  .archive-heading {
    display: grid;
    grid-template-columns: 1fr;
    align-items: stretch;
  }

  .archive-heading .archive-search {
    width: 100%;
    max-width: none;
  }

  .archive-actions {
    justify-content: space-between;
  }

  .resource-launcher-grid,
  .resource-gallery {
    grid-template-columns: 1fr;
  }
}
</style>
