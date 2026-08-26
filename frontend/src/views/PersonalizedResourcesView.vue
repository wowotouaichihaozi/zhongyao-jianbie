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

    <!-- 资源列表 -->
    <section class="resource-tools-section" aria-label="资源生成工具">
      <div class="resource-tools-grid">
        <RouterLink
          v-for="tool in resourceTools"
          :key="tool.to"
          class="resource-tool-card"
          :class="tool.tone"
          :to="tool.to"
          target="_blank"
          rel="noopener noreferrer"
        >
          <span class="resource-tool-icon">
            <component :is="tool.icon" :size="28" :stroke-width="2.2" aria-hidden="true" />
          </span>
          <span class="resource-tool-copy">
            <strong>{{ tool.title }}</strong>
            <em>{{ tool.description }}</em>
          </span>
          <ArrowRight :size="20" :stroke-width="2.2" aria-hidden="true" />
        </RouterLink>
      </div>
    </section>

    <div class="resources-content">
      <div class="history-resources-head">
        <h2>历史资源</h2>
        <button
          type="button"
          class="history-refresh-btn"
          :disabled="resourcesLoading"
          aria-label="刷新历史资源"
          @click="loadResources"
        >
          <RefreshCw :size="16" :class="{ spin: resourcesLoading }" aria-hidden="true" />
          {{ resourcesLoading ? '加载中' : '刷新' }}
        </button>
      </div>
      <div v-if="resourcesWarning" class="history-status warning" role="status">
        <TriangleAlert :size="18" aria-hidden="true" />
        <span>{{ resourcesWarning }}</span>
        <button type="button" @click="loadResources">重新加载</button>
      </div>
      <!-- 分类标签栏 -->
      <div class="category-tabs">
        <button
          v-for="cat in categories"
          :key="cat.key"
          :class="['tab-btn', { active: activeCategory === cat.key }]"
          @click="activeCategory = cat.key"
        >
          {{ cat.label }}
        </button>
      </div>

      <!-- 操作栏 -->
      <div class="action-bar">
        <span class="resource-count">
          {{ resourcesLoading ? '正在同步历史资源' : `共 ${filteredResources.length} 个资源` }}
        </span>
        <button class="generate-btn" @click="generateNewResource" :disabled="generating || !hasProfile">
          <svg v-if="!generating" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M12 4v16m8-8H4" stroke-linecap="round" stroke-linejoin="round"/>
          </svg>
          <span v-if="generating" class="loading-spinner"></span>
          {{ generating ? '生成中...' : '生成新资源' }}
        </button>
      </div>

      <!-- 资源卡片网格 -->
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
      <div v-else class="resources-grid">
        <button
          v-for="resource in filteredResources"
          :key="resource.id"
          type="button"
          class="resource-card"
          @click="openResource(resource)"
        >
          <div
            class="card-icon"
            :style="{
              background: getTypeColor(resource.type),
              color: getTypeIconColor(resource.type),
            }"
          >
            <svg v-if="resource.type === 'mindmap'" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
              <path d="M4 6h16M4 12h10m-10 6h16" stroke-linecap="round" stroke-linejoin="round"/>
            </svg>
            <svg v-else-if="resource.type === 'ppt'" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
              <path d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V7M3 7l9-4 9 4M3 7l9 4 9-4" stroke-linecap="round" stroke-linejoin="round"/>
            </svg>
            <svg v-else-if="resource.type === 'video' || resource.type === 'generated_video'" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
              <path d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z" stroke-linecap="round" stroke-linejoin="round"/>
              <path d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z" stroke-linecap="round" stroke-linejoin="round"/>
            </svg>
            <svg v-else-if="resource.type === 'animation'" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
              <rect x="3" y="5" width="18" height="14" rx="2" />
              <path d="m10 9 5 3-5 3V9Z" stroke-linecap="round" stroke-linejoin="round" />
              <path d="M7 3v2m10-2v2M7 19v2m10-2v2" stroke-linecap="round" />
            </svg>
            <svg v-else-if="resource.type === 'code'" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
              <path d="M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4" stroke-linecap="round" stroke-linejoin="round"/>
            </svg>
            <svg v-else-if="resource.type === 'simulator'" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
              <path d="M9 3h6v3h3a2 2 0 012 2v8a2 2 0 01-2 2h-3v3H9v-3H6a2 2 0 01-2-2V8a2 2 0 012-2h3V3zM8 11h2m4 0h2M8 15h8" stroke-linecap="round" stroke-linejoin="round"/>
            </svg>
            <svg v-else viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
              <path d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" stroke-linecap="round" stroke-linejoin="round"/>
            </svg>
          </div>
          <div class="card-content">
            <h3>{{ resource.title }}</h3>
            <p class="card-desc">{{ resource.description }}</p>
            <div class="card-footer">
              <span class="type-tag">{{ getTypeName(resource.type) }}</span>
              <time v-if="resource.createdAt" class="history-time" :datetime="resource.createdAt">
                {{ formatResourceTime(resource.createdAt) }}
              </time>
              <span v-if="Number.isFinite(resource.matchScore)" class="match-score" :style="{ color: getMatchColor(resource.matchScore) }">
                匹配度 {{ resource.matchScore }}%
              </span>
              <span v-if="resourceQuality(resource).score" class="quality-badge">
                质量 {{ resourceQuality(resource).score }}
              </span>
              <span v-if="resourceCitationCount(resource)" class="citation-badge">
                引用 {{ resourceCitationCount(resource) }}
              </span>
              <span v-if="getEvaluation(resource.id)" class="learned-badge">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
                  <path d="M5 13l4 4L19 7" stroke-linecap="round" stroke-linejoin="round"/>
                </svg>
                已学习
                <span class="badge-stars">
                  <svg v-for="s in 5" :key="s" viewBox="0 0 24 24" :fill="s <= getEvaluation(resource.id).rating ? '#f59e0b' : 'none'" :stroke="s <= getEvaluation(resource.id).rating ? '#f59e0b' : '#cbd5e1'" stroke-width="2" class="mini-star">
                    <path d="M11.049 2.927c.3-.921 1.603-.921 1.902 0l1.519 4.674a1 1 0 00.95.69h4.915c.969 0 1.371 1.24.588 1.81l-3.976 2.888a1 1 0 00-.363 1.118l1.518 4.674c.3.922-.755 1.688-1.538 1.118l-3.976-2.888a1 1 0 00-1.176 0l-3.976 2.888c-.783.57-1.838-.197-1.538-1.118l1.518-4.674a1 1 0 00-.363-1.118l-3.976-2.888c-.784-.57-.38-1.81.588-1.81h4.914a1 1 0 00.951-.69l1.519-4.674z"/>
                  </svg>
                </span>
              </span>
            </div>
          </div>
          <div class="card-arrow">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M9 5l7 7-7 7" stroke-linecap="round" stroke-linejoin="round"/>
            </svg>
          </div>
        </button>
      </div>

      <!-- 空状态 -->
      <div v-if="!resourcesLoading && !resourcesError && filteredResources.length === 0" class="empty-state">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
          <path d="M20 13V6a2 2 0 00-2-2H6a2 2 0 00-2 2v7m16 0v5a2 2 0 01-2 2H6a2 2 0 01-2-2v-5m16 0h-2.586a1 1 0 00-.707.293l-2.414 2.414a1 1 0 01-.707.293h-3.172a1 1 0 01-.707-.293l-2.414-2.414A1 1 0 006.586 13H4" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>
        <p>该分类暂无资源，点击"生成新资源"创建</p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, markRaw, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  ArrowRight,
  BookOpenCheck,
  Clapperboard,
  LoaderCircle,
  Presentation,
  RefreshCw,
  Search,
  Share2,
  TriangleAlert,
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
    description: '按学习画像生成讲解视频，自动配音、字幕与服务端剪辑。',
    to: '/personalized-resources/video-generator',
    icon: markRaw(Clapperboard),
    tone: 'tool-teal',
  },
  {
    title: '题库生成',
    description: '按章节和难度快速生成练习题单与考试。',
    to: '/personalized-resources/question-bank',
    icon: markRaw(BookOpenCheck),
    tone: 'tool-green',
  },
  {
    title: 'PPT生成',
    description: '根据主题和材料生成课程演示文稿。',
    to: '/personalized-resources/ppt',
    icon: markRaw(Presentation),
    tone: 'tool-blue',
  },
  {
    title: '思维导图',
    description: '把知识点整理成结构清晰的学习导图。',
    to: '/personalized-resources/mind-map',
    icon: markRaw(Share2),
    tone: 'tool-purple',
  },
  {
    title: '视频查找',
    description: '检索适合当前学习阶段的讲解视频。',
    to: '/personalized-resources/video-search',
    icon: markRaw(Search),
    tone: 'tool-teal',
  },
]

const categories = [
  { key: 'all', label: '全部' },
  { key: 'mindmap', label: '思维导图' },
  { key: 'ppt', label: 'PPT' },
  { key: 'video', label: '视频' },
  { key: 'generated_video', label: 'AI 视频生成' },
  { key: 'quiz', label: '练习题' },
]

const requestedCategory = String(route.query.category || '')
const activeCategory = ref(categories.some(item => item.key === requestedCategory) ? requestedCategory : 'all')
const generating = ref(false)
const resources = ref([])
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
    loadAllCompletedGeneratedVideos(),
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

async function loadAllCompletedGeneratedVideos() {
  const tasks = []
  let offset = 0
  while (true) {
    const page = await getGeneratedVideoTaskHistory({ status: 'complete', limit: 100, offset })
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
  if (activeCategory.value === 'all') return visibleResources
  return visibleResources.filter(r => r.type === activeCategory.value)
})

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
</style>
