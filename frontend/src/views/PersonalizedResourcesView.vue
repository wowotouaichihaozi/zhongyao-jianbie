<template>
  <div class="resources-page">
    <div class="resources-header">
      <span class="resources-kicker">学习资源工作台</span>
      <div class="resources-title-row">
        <h1>个性化资源</h1>
        <span class="profile-state" :class="{ ready: hasProfile }">
          {{ profileLoading ? '画像同步中' : hasProfile ? '已关联学习画像' : '未关联学习画像' }}
        </span>
      </div>
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
    <section class="resource-tools-section" aria-labelledby="resource-tools-title">
      <div class="resource-tools-head">
        <h2 id="resource-tools-title">新建资源</h2>
      </div>
      <div class="resource-tools-grid">
        <RouterLink
          v-for="tool in resourceTools"
          :key="tool.to"
          class="resource-tool-card"
          :to="tool.to"
          target="_blank"
          rel="noopener noreferrer"
          :aria-label="tool.title"
        >
          <span class="resource-tool-icon">
            <component :is="tool.icon" :size="26" :stroke-width="1.8" aria-hidden="true" />
          </span>
          <strong>{{ tool.title }}</strong>
        </RouterLink>
      </div>
    </section>

    <div class="resources-content">
      <div class="history-resources-head">
        <div class="history-title-group">
          <h2>资源记录</h2>
          <span>{{ resourcesLoading ? '正在同步' : `${resourceTopics.length} 个专题` }}</span>
        </div>
        <div class="history-head-actions">
          <button
            type="button"
            class="history-refresh-btn"
            :disabled="resourcesLoading"
            aria-label="刷新资源记录"
            @click="loadResources"
          >
            <RefreshCw :size="16" :class="{ spin: resourcesLoading }" aria-hidden="true" />
            {{ resourcesLoading ? '加载中' : '刷新' }}
          </button>
          <button class="generate-btn" @click="generateNewResource" :disabled="generating || !hasProfile">
            <svg v-if="!generating" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M12 4v16m8-8H4" stroke-linecap="round" stroke-linejoin="round"/>
            </svg>
            <span v-if="generating" class="loading-spinner"></span>
            {{ generating ? '生成中...' : '生成新资源' }}
          </button>
        </div>
      </div>
      <div v-if="resourcesWarning" class="history-status warning" role="status">
        <TriangleAlert :size="18" aria-hidden="true" />
        <span>{{ resourcesWarning }}</span>
        <button type="button" @click="loadResources">重新加载</button>
      </div>

      <!-- 资源专题卡片网格 -->
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
      <div v-else-if="!resources.length" class="empty-state compact-empty-state" role="status">
        <span>暂时没有已生成记录，八个专题入口仍可正常使用。</span>
      </div>
      <div v-if="!resourcesLoading && !(resourcesError && !resources.length)" class="resources-grid">
        <button
          v-for="topic in topicCards"
          :key="topic.key"
          type="button"
          class="resource-card topic-card"
          :aria-label="`进入${topic.title}专题`"
          @click="openTopic(topic)"
        >
          <div class="topic-card-media" :class="topic.coverClass">
            <img
              class="topic-cover-texture"
              :src="topic.coverTexture"
              :data-texture-style="topic.coverTextureStyle"
              alt=""
              aria-hidden="true"
              loading="lazy"
              decoding="async"
            />
            <span class="topic-cover-label">{{ topic.coverLabel }}</span>
            <span
              class="topic-cover-icon"
              :data-glyph="topic.glyph"
              aria-hidden="true"
            >
              <img
                class="topic-cover-icon-image"
                :src="topic.iconImage"
                alt=""
                aria-hidden="true"
                decoding="async"
              />
            </span>
          </div>
          <div class="topic-card-body">
            <div class="topic-card-copy">
              <h3>{{ topic.title }}</h3>
              <p>{{ topic.focus }}</p>
            </div>
            <span class="topic-card-meta">
              {{ topic.linkedCount ? `${topic.linkedCount} 项相关资源` : '进入专题' }}
            </span>
            <ArrowUpRight :size="18" :stroke-width="1.8" aria-hidden="true" />
          </div>
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, markRaw, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import {
  ArrowUpRight,
  BookOpenCheck,
  Box,
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
  extractTaskResources,
} from '../utils/personalizedResourceHistory.js'

const router = useRouter()

const resourceTools = [
  {
    title: 'AI 视频课程',
    to: '/personalized-resources/video-generator',
    icon: markRaw(Clapperboard),
  },
  {
    title: '题库生成',
    to: '/personalized-resources/question-bank',
    icon: markRaw(BookOpenCheck),
  },
  {
    title: 'PPT生成',
    to: '/personalized-resources/ppt',
    icon: markRaw(Presentation),
  },
  {
    title: '思维导图',
    to: '/personalized-resources/mind-map',
    icon: markRaw(Share2),
  },
  {
    title: '药材模型识别',
    to: '/personalized-resources/herb-model',
    icon: markRaw(Box),
  },
  {
    title: '视频查找',
    to: '/personalized-resources/video-search',
    icon: markRaw(Search),
  },
]

const resourceTopics = [
  { key: 'bagang', title: '八纲辨证', coverLabel: '中医辨证学习', coverClass: 'cover-cyan', coverTexture: '/images/resource-topic-patterns-v2/bagang-pattern-v2.png', coverTextureStyle: 'solid-corner-sweeps', glyph: 'diagnostic', iconImage: '/images/resource-topic-icons-v2/bagang-icon-v2.png', focus: '表里 · 寒热 · 虚实 · 阴阳', keywords: ['八纲', '表里', '寒热', '虚实'], to: '/personalized-resources/question-bank?module=generate&course=中医诊断学&chapter=八纲辨证' },
  { key: 'herbs', title: '药材识别', coverLabel: '中药鉴别学习', coverClass: 'cover-orange', coverTexture: '/images/resource-topic-patterns-v2/herbs-pattern-v2.png', coverTextureStyle: 'parallel-arcs-and-dots', glyph: 'ginseng', iconImage: '/images/resource-topic-icons-v2/herbs-icon-v2.png', focus: '来源 · 性状 · 真伪鉴别', keywords: ['药材', '中药鉴别', '性状'], to: '/herb-recognition' },
  { key: 'flavor', title: '性味归经', coverLabel: '中药药性学习', coverClass: 'cover-blue', coverTexture: '/images/resource-topic-patterns-v2/flavor-pattern-v2.png', coverTextureStyle: 'broad-bottom-wave', glyph: 'leaf', iconImage: '/images/resource-topic-icons-v2/flavor-icon-v2.png', focus: '四气 · 五味 · 升降浮沉', keywords: ['性味', '归经', '四气', '五味'], to: '/personalized-resources/question-bank?module=generate&course=中药学&chapter=性味归经' },
  { key: 'formula', title: '方剂配伍', coverLabel: '方剂应用学习', coverClass: 'cover-pink', coverTexture: '/images/resource-topic-patterns-v2/formula-pattern-v2.png', coverTextureStyle: 'solid-arc-and-square-dots', glyph: 'mortar', iconImage: '/images/resource-topic-icons-v2/formula-icon-v2.png', focus: '君臣佐使 · 配伍规律', keywords: ['方剂', '配伍', '君臣佐使'], to: '/personalized-resources/mind-map?topic=方剂配伍&keyword=君臣佐使' },
  { key: 'diagnostics', title: '四诊合参', coverLabel: '中医诊断学习', coverClass: 'cover-coral', coverTexture: '/images/resource-topic-patterns-v2/diagnostics-pattern-v2.png', coverTextureStyle: 'scalloped-shrub', glyph: 'pulse', iconImage: '/images/resource-topic-icons-v2/diagnostics-icon-v2.png', focus: '望闻问切 · 证据记录', keywords: ['四诊', '望诊', '闻诊', '问诊', '切诊', '脉诊', '舌诊'], to: '/personalized-resources/video-search?keyword=四诊合参' },
  { key: 'meridians', title: '经络腧穴', coverLabel: '经络腧穴学习', coverClass: 'cover-violet', coverTexture: '/images/resource-topic-patterns-v2/meridians-pattern-v2.png', coverTextureStyle: 'sparse-contours', glyph: 'acupoint', iconImage: '/images/resource-topic-icons-v2/meridians-icon-v2.png', focus: '经脉循行 · 腧穴定位', keywords: ['经络', '经脉', '腧穴', '针灸'], to: '/personalized-resources/ppt?topic=经络腧穴' },
  { key: 'wellness', title: '养生健康', coverLabel: '中医养生学习', coverClass: 'cover-green', coverTexture: '/images/resource-topic-patterns-v2/wellness-pattern-v2.png', coverTextureStyle: 'diagonal-bands', glyph: 'gourd', iconImage: '/images/resource-topic-icons-v2/wellness-icon-v2.png', focus: '四时调摄 · 药膳基础', keywords: ['养生', '药膳', '调摄'], to: '/personalized-resources/video-search?keyword=中医养生' },
  { key: 'cases', title: '医案研习', coverLabel: '医案实训学习', coverClass: 'cover-sky', coverTexture: '/images/resource-topic-patterns-v2/cases-pattern-v2.png', coverTextureStyle: 'halftone-and-curve', glyph: 'scroll', iconImage: '/images/resource-topic-icons-v2/cases-icon-v2.png', focus: '四诊证据 · 辨证推演', keywords: ['医案', '病例', '辨证'], to: '/smart-tutor?topic=中医医案辨析' },
]

const generating = ref(false)
const resources = ref([])
const hasProfile = ref(false)
const profileData = ref(null)
const profileLoading = ref(true)
const profileError = ref('')
const resourcesLoading = ref(true)
const resourcesError = ref('')
const resourcesWarning = ref('')
const hiddenResourceTypes = new Set(['document', 'animation', 'code', 'simulator', 'mcu'])

onMounted(async () => {
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

const visibleResources = computed(() => (
  resources.value.filter(resource => !hiddenResourceTypes.has(String(resource?.type || '')))
))

function resourceSearchText(resource) {
  const metadata = resource?.metadata && typeof resource.metadata === 'object' ? resource.metadata : {}
  return [
    resource?.title,
    resource?.description,
    metadata.topic,
    metadata.chapter,
    metadata.course,
  ].filter(Boolean).join(' ')
}

const topicCards = computed(() => resourceTopics.map(topic => {
  const linkedResources = visibleResources.value.filter(resource => {
    const text = resourceSearchText(resource)
    return topic.keywords.some(keyword => text.includes(keyword))
  })
  return {
    ...topic,
    linkedCount: linkedResources.length,
    linkedResource: linkedResources[0] || null,
  }
}))

function openTopic(topic) {
  if (topic.linkedResource) {
    openResource(topic.linkedResource)
    return
  }
  router.push(topic.to)
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

/* Personalized-resource workspace: compact commands above a scan-first record list. */
.resources-page {
  padding: 32px clamp(24px, 4vw, 64px) 64px;
  background: #ffffff;
}

.resources-header,
.no-profile-banner,
.resource-tools-section,
.resources-content {
  width: min(100%, 1440px);
  margin-right: auto;
  margin-left: auto;
}

.resources-header {
  margin-bottom: 24px;
  padding: 0;
  border: 0;
}

.resources-kicker {
  display: block;
  margin-bottom: 8px;
  color: #6d7773;
  font-size: 12px;
  font-weight: 600;
  line-height: 1;
}

.resources-title-row {
  display: flex;
  align-items: center;
  gap: 14px;
}

.resources-header h1 {
  color: #15201c;
  font-size: 28px;
  font-weight: 650;
  letter-spacing: 0;
}

.profile-state {
  padding-left: 12px;
  border-left: 1px solid #dce3df;
  color: #7a837f;
  font-size: 12px;
  font-weight: 500;
}

.profile-state.ready {
  color: #1b7655;
}

.no-profile-banner {
  margin-bottom: 24px;
  border-radius: 4px;
  background: #fffaf0;
}

.resource-tools-section {
  margin-bottom: 42px;
  padding: 0 0 22px;
  border: 0;
  border-top: 1px solid #dfe5e2;
  border-bottom: 1px solid #dfe5e2;
}

.resource-tools-head {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 16px;
  margin: 0;
  padding: 16px 0 10px;
}

.resource-tools-head h2,
.resource-tools-head h2::before {
  margin: 0;
  color: #1f2925;
  font-size: 14px;
  font-weight: 650;
  letter-spacing: 0;
}

.resource-tools-head h2::before {
  content: none;
}

.resource-tools-head > span {
  color: #858e8a;
  font-size: 12px;
}

.resource-tools-grid {
  grid-template-columns: repeat(6, minmax(0, 1fr));
  gap: 0;
}

.resource-tool-card,
.resource-tool-card.tool-blue,
.resource-tool-card.tool-purple,
.resource-tool-card.tool-teal,
.resource-tool-card.tool-green {
  min-height: 76px;
  padding: 12px 18px;
  grid-template-columns: 34px minmax(0, 1fr);
  gap: 12px;
  border: 0;
  border-left: 1px solid #e7ece9;
  border-radius: 0;
  background: transparent;
  box-shadow: none;
}

.resource-tool-card:first-child {
  padding-left: 0;
  border-left: 0;
}

.resource-tool-card:last-child {
  padding-right: 0;
}

.resource-tool-card:hover {
  transform: translateY(-2px);
  border-color: #e7ece9;
  background: transparent;
  box-shadow: none;
}

.resource-tool-card .resource-tool-icon,
.resource-tool-card.tool-blue .resource-tool-icon,
.resource-tool-card.tool-purple .resource-tool-icon,
.resource-tool-card.tool-teal .resource-tool-icon,
.resource-tool-card.tool-green .resource-tool-icon {
  width: 30px;
  height: 30px;
  border-radius: 0;
  color: #187455;
  background: transparent;
}

.resource-tool-card:hover .resource-tool-icon {
  transform: none;
  color: #0f5f44;
}

.resource-tool-copy {
  gap: 4px;
}

.resource-tool-copy strong {
  color: #1d2824;
  font-size: 14px;
  font-weight: 620;
}

.resource-tool-copy em {
  color: #747e79;
  font-size: 12px;
  line-height: 1.35;
  -webkit-line-clamp: 1;
}

.resources-content {
  padding: 0;
  border: 0;
  border-radius: 0;
  background: transparent;
  box-shadow: none;
}

.history-resources-head {
  align-items: center;
  margin: 0 0 16px;
  padding: 0;
}

.history-title-group {
  display: flex;
  align-items: baseline;
  gap: 10px;
}

.history-resources-head h2,
.history-resources-head h2::before {
  margin: 0;
  color: #17211d;
  font-size: 22px;
  font-weight: 650;
  letter-spacing: 0;
}

.history-resources-head h2::before,
.history-resources-head h2::after {
  content: none;
  display: none;
}

.history-title-group > span {
  color: #7d8782;
  font-size: 12px;
}

.history-head-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.history-refresh-btn,
.generate-btn {
  position: static;
  min-height: 38px;
  border-radius: 4px;
  box-shadow: none;
  font-size: 13px;
}

.history-refresh-btn {
  padding: 0 13px;
  border: 1px solid #d8dfdb;
  color: #4f5b56;
  background: #ffffff;
}

.history-refresh-btn:hover:not(:disabled) {
  transform: none;
  border-color: #9db9ad;
  color: #176e50;
  background: #f7faf8;
}

.generate-btn {
  padding: 0 15px;
  background: #176f50;
}

.generate-btn,
.generate-btn span {
  font-size: 13px;
}

.generate-btn::after {
  content: none;
}

.generate-btn:hover:not(:disabled) {
  transform: none;
  background: #105d42;
  box-shadow: none;
}

.category-tabs {
  gap: 2px;
  margin: 0 0 12px;
  padding-bottom: 10px;
  border-bottom: 1px solid #e3e8e5;
}

.tab-btn {
  min-width: 0;
  min-height: 34px;
  padding: 0 13px;
  border: 0;
  border-radius: 3px;
  color: #69736f;
  background: transparent;
  font-size: 13px;
}

.tab-btn:hover {
  transform: none;
  color: #176f50;
  background: #f2f6f4;
}

.tab-btn.active {
  border: 0;
  color: #125f45;
  background: #eaf3ee;
}

.resources-grid {
  display: grid;
  grid-template-columns: 1fr;
  gap: 0;
  border-bottom: 1px solid #e2e7e4;
}

.resource-card {
  min-height: 96px;
  padding: 15px 72px 15px 12px;
  display: grid;
  grid-template-columns: 38px minmax(0, 1fr) 18px;
  align-items: center;
  gap: 14px;
  border: 0;
  border-top: 1px solid #e2e7e4;
  border-radius: 0;
  background: transparent;
  box-shadow: none;
  text-align: left;
  transition: background-color 160ms ease, transform 160ms ease;
}

.resource-card:hover {
  transform: translateX(2px);
  border-color: #e2e7e4;
  background: #f7faf8;
  box-shadow: none;
}

.card-icon {
  width: 36px;
  height: 36px;
  border-radius: 0;
}

.resource-card:hover .card-icon {
  transform: none;
}

.card-icon svg {
  width: 24px;
  height: 24px;
}

.card-content {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  grid-template-rows: auto auto;
  align-items: center;
  column-gap: 28px;
  min-width: 0;
}

.card-content h3 {
  grid-column: 1;
  margin: 0 0 5px;
  padding: 0;
  color: #1b2521;
  font-size: 15px;
  font-weight: 620;
  line-height: 1.35;
}

.card-desc {
  grid-column: 1;
  margin: 0;
  color: #717b76;
  font-size: 12px;
  line-height: 1.45;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.card-footer {
  grid-column: 2;
  grid-row: 1 / span 2;
  justify-content: flex-end;
  gap: 9px;
  margin: 0;
  white-space: nowrap;
}

.type-tag,
.quality-badge,
.citation-badge,
.learned-badge,
.match-score {
  padding: 0;
  border: 0;
  border-radius: 0;
  color: #69736f !important;
  background: transparent;
  font-size: 12px;
  font-weight: 500;
}

.type-tag {
  padding-right: 9px;
  border-right: 1px solid #dce2de;
  color: #356a56 !important;
}

.history-time {
  color: #8a938f;
  font-size: 12px;
}

.card-arrow {
  position: static;
  width: 16px;
  height: 16px;
  color: #a0a8a4;
}

.resource-card:hover .card-arrow {
  transform: translateX(2px);
  color: #176f50;
}

.history-loading,
.history-error,
.empty-state {
  min-height: 260px;
  border: 1px solid #e1e7e3;
  border-radius: 4px;
  background: #fbfcfb;
}

@media (max-width: 1100px) {
  .resource-tools-grid {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }

  .resource-tool-card:nth-child(4) {
    padding-left: 0;
    border-left: 0;
  }

  .card-content {
    display: block;
  }

  .card-footer {
    justify-content: flex-start;
    margin-top: 9px;
    white-space: normal;
  }
}

@media (max-width: 720px) {
  .resources-page {
    padding: 24px 16px calc(112px + env(safe-area-inset-bottom));
  }

  .resources-header {
    margin-bottom: 20px;
  }

  .resources-header h1 {
    font-size: 24px;
  }

  .resources-title-row {
    align-items: flex-end;
    justify-content: space-between;
  }

  .profile-state {
    max-width: 110px;
    text-align: right;
  }

  .no-profile-banner {
    align-items: flex-start;
    flex-wrap: wrap;
  }

  .no-profile-banner .banner-btn {
    margin-left: 32px;
  }

  .resource-tools-section {
    margin-bottom: 32px;
  }

  .resource-tools-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .resource-tool-card,
  .resource-tool-card.tool-blue,
  .resource-tool-card.tool-purple,
  .resource-tool-card.tool-teal,
  .resource-tool-card.tool-green {
    min-height: 64px;
    padding: 10px 8px;
    border-left: 0;
    border-top: 1px solid #e7ece9;
  }

  .resource-tool-card:nth-child(odd) {
    padding-left: 0;
    border-right: 1px solid #e7ece9;
  }

  .resource-tool-card:nth-child(even) {
    padding-right: 0;
    padding-left: 12px;
  }

  .resource-tool-copy em,
  .resource-tools-head > span {
    display: none;
  }

  .history-resources-head {
    align-items: flex-start;
    padding: 0;
  }

  .history-title-group {
    display: grid;
    gap: 2px;
  }

  .history-resources-head h2,
  .history-resources-head h2::before {
    font-size: 20px;
  }

  .history-head-actions {
    gap: 6px;
  }

  .history-refresh-btn,
  .generate-btn {
    min-height: 40px;
    padding: 0 11px;
  }

  .history-refresh-btn {
    font-size: 0;
  }

  .history-refresh-btn svg {
    margin: 0;
  }

  .category-tabs {
    flex-wrap: nowrap;
    overflow-x: auto;
    scrollbar-width: none;
  }

  .category-tabs::-webkit-scrollbar {
    display: none;
  }

  .tab-btn {
    flex: 0 0 auto;
    min-height: 40px;
  }

  .resource-card {
    min-height: 116px;
    padding: 14px 66px 14px 4px;
    grid-template-columns: 34px minmax(0, 1fr) 14px;
    gap: 10px;
  }

  .card-icon {
    width: 32px;
    height: 32px;
  }

  .card-icon svg {
    width: 22px;
    height: 22px;
  }

  .card-content h3 {
    display: -webkit-box;
    overflow: hidden;
    -webkit-box-orient: vertical;
    -webkit-line-clamp: 2;
  }

  .card-desc {
    white-space: normal;
    display: -webkit-box;
    -webkit-box-orient: vertical;
    -webkit-line-clamp: 2;
  }

  .card-footer {
    gap: 7px;
    margin-top: 8px;
  }

  .quality-badge,
  .citation-badge,
  .learned-badge {
    display: none;
  }
}

/* Route-local correction for the global console theme's card and chip !important rules. */
#app .resources-page .resource-tools-grid,
#app .resources-page .resources-grid {
  gap: 0 !important;
}

#app .resources-page .resource-tool-card,
#app .resources-page .resource-tool-card[class*="tool-"] {
  border: 0 !important;
  border-left: 1px solid #e7ece9 !important;
  border-radius: 0 !important;
  background: transparent !important;
}

#app .resources-page .resource-tool-card:first-child {
  border-left: 0 !important;
}

#app .resources-page .resource-tool-card .resource-tool-icon,
#app .resources-page .resource-tool-card[class*="tool-"] .resource-tool-icon {
  border: 0 !important;
  border-radius: 0 !important;
  color: #187455 !important;
  background: transparent !important;
}

#app .resources-page .resource-card {
  border: 0 !important;
  border-top: 1px solid #e2e7e4 !important;
  border-radius: 0 !important;
  background: transparent !important;
}

#app .resources-page .resource-card:hover {
  background: #f7faf8 !important;
}

#app .resources-page .tab-btn {
  border: 0 !important;
  border-radius: 3px !important;
  background: transparent !important;
}

#app .resources-page .tab-btn:hover {
  background: #f2f6f4 !important;
}

#app .resources-page .tab-btn.active {
  background: #eaf3ee !important;
}

#app .resources-page :is(.type-tag, .match-score, .quality-badge, .citation-badge, .learned-badge) {
  border: 0 !important;
  border-radius: 0 !important;
  background: transparent !important;
}

@media (max-width: 720px) {
  #app .resources-page .resource-tool-card,
  #app .resources-page .resource-tool-card[class*="tool-"] {
    border-left: 0 !important;
    border-top: 1px solid #e7ece9 !important;
  }

  #app .resources-page .resource-tool-card:nth-child(odd) {
    border-right: 1px solid #e7ece9 !important;
  }
}

/* Week-organized course cards, revised after route-level visual review. */
.history-filter-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 18px;
  margin-bottom: 14px;
  padding-bottom: 12px;
  border-bottom: 1px solid #e3e8e5;
}

.history-filter-row .category-tabs {
  flex: 1 1 auto;
  margin: 0;
  padding: 0;
  border: 0;
}

.week-filter {
  position: relative;
  flex: 0 0 auto;
  display: flex;
  align-items: center;
  gap: 8px;
}

.week-filter-caption {
  color: #6f7974;
  font-size: 12px;
}

.week-filter-trigger {
  width: 164px;
  height: 40px;
  padding: 0 11px;
  display: flex;
  align-items: center;
  gap: 8px;
  border: 1px solid #d8dfdb;
  border-radius: 6px;
  color: #35413c;
  background: #ffffff;
  font-size: 13px;
  cursor: pointer;
  transition: border-color 160ms ease, box-shadow 160ms ease;
}

.week-filter-trigger strong {
  overflow: hidden;
  font-weight: 550;
  white-space: nowrap;
  text-overflow: ellipsis;
}

.week-filter-trigger > svg:last-child {
  margin-left: auto;
  transition: transform 160ms ease;
}

.week-filter-trigger > svg:last-child.open {
  transform: rotate(180deg);
}

.week-filter-trigger:hover,
.week-filter-trigger[aria-expanded="true"] {
  border-color: #9db9ad;
  box-shadow: 0 0 0 3px rgba(23, 111, 80, 0.08);
}

.week-filter-trigger:focus-visible {
  outline: 3px solid rgba(16, 150, 102, 0.2);
  outline-offset: 2px;
}

.week-filter-menu {
  position: absolute;
  z-index: 30;
  top: calc(100% + 8px);
  right: 0;
  width: 276px;
  margin: 0;
  padding: 13px 12px 12px;
  border: 1px solid #dce3df;
  border-radius: 8px;
  background: #ffffff;
  box-shadow: 0 14px 32px rgba(28, 55, 44, 0.16);
}

.week-filter-menu legend {
  width: 100%;
  margin: 0 0 8px;
  padding: 0 4px;
  color: #1d2824;
  font-size: 14px;
  font-weight: 650;
  line-height: 1.5;
}

.week-filter-options {
  max-height: 182px;
  padding-right: 3px;
  overflow-y: auto;
  overscroll-behavior: contain;
  scrollbar-width: thin;
  scrollbar-color: #b9cbc3 transparent;
}

.week-filter-options::-webkit-scrollbar {
  width: 6px;
}

.week-filter-options::-webkit-scrollbar-thumb {
  border-radius: 3px;
  background: #b9cbc3;
}

.week-filter-option {
  position: relative;
  height: 52px;
  padding: 0 11px;
  display: flex;
  align-items: center;
  gap: 10px;
  border-radius: 6px;
  color: #3f4945;
  font-size: 13px;
  font-weight: 550;
  cursor: pointer;
  user-select: none;
  transition: color 150ms ease, background-color 150ms ease, box-shadow 150ms ease;
}

.week-filter-option:hover {
  background: #f3f6f4;
}

.week-filter-option.selected {
  color: #176f50;
  background: #edf6f1;
  box-shadow: inset 0 0 0 1px #acd0c0;
}

.week-option-index {
  width: 26px;
  height: 26px;
  flex: 0 0 26px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border: 1px solid #d8e1dc;
  border-radius: 5px;
  color: #66716c;
  background: #ffffff;
  font-size: 11px;
  font-variant-numeric: tabular-nums;
}

.week-filter-option.selected .week-option-index {
  border-color: #8fc4ad;
  color: #176f50;
  background: #ffffff;
}

.week-filter-option input {
  width: 16px;
  height: 16px;
  margin-left: auto;
  accent-color: #176f50;
  cursor: pointer;
}

.week-filter-pop-enter-active,
.week-filter-pop-leave-active {
  transition: opacity 150ms ease, transform 150ms ease;
  transform-origin: top right;
}

.week-filter-pop-enter-from,
.week-filter-pop-leave-to {
  opacity: 0;
  transform: translateY(-5px) scale(0.985);
}

.resources-grid {
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 14px;
  border: 0;
}

.resource-card {
  position: relative;
  min-height: 178px;
  padding: 18px;
  display: grid;
  grid-template-columns: 42px minmax(0, 1fr) 16px;
  align-items: start;
  gap: 12px;
  border: 1px solid #e1e6e3;
  border-radius: 8px;
  background: #ffffff;
  box-shadow: 0 1px 2px rgba(25, 60, 47, 0.03);
  transition: transform 180ms ease, border-color 180ms ease, box-shadow 180ms ease;
}

.resource-card:hover {
  transform: translateY(-3px);
  border-color: #9fc7b6;
  background: #ffffff;
  box-shadow: 0 10px 24px rgba(26, 72, 54, 0.1);
}

.resource-card .card-icon {
  width: 40px;
  height: 40px;
  border: 1px solid currentColor;
  border-radius: 6px;
  opacity: 0.9;
}

.resource-card .card-icon svg {
  width: 23px;
  height: 23px;
}

.resource-card .card-content {
  min-height: 140px;
  display: flex;
  flex-direction: column;
  align-items: stretch;
}

.resource-card .card-content h3 {
  margin: 0 22px 7px 0;
  padding: 0;
  color: #1b2521;
  font-size: 15px;
  font-weight: 650;
  line-height: 1.45;
  display: -webkit-box;
  overflow: hidden;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
}

.resource-card .card-desc {
  margin: 0;
  color: #737d78;
  font-size: 12px;
  line-height: 1.55;
  white-space: normal;
  display: -webkit-box;
  overflow: hidden;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
}

.resource-card .card-footer {
  display: flex;
  flex-wrap: wrap;
  justify-content: flex-start;
  align-items: center;
  gap: 7px 9px;
  margin-top: auto;
  padding-top: 14px;
  white-space: normal;
}

.resource-card .type-tag {
  padding: 4px 7px;
  border: 0;
  border-radius: 3px;
  color: #356a56 !important;
  background: #edf4f0;
}

.resource-card .history-time,
.resource-card .match-score,
.resource-card .quality-badge,
.resource-card .citation-badge,
.resource-card .learned-badge {
  color: #727c77 !important;
  font-size: 11px;
}

.resource-card .card-arrow {
  position: absolute;
  top: 20px;
  right: 16px;
  width: 16px;
  height: 16px;
  color: #8f9994;
}

.resource-card:hover .card-arrow {
  transform: translateX(2px);
  color: #176f50;
}

#app .resources-page .resources-grid {
  gap: 14px !important;
}

#app .resources-page .resource-card {
  border: 1px solid #e1e6e3 !important;
  border-radius: 8px !important;
  background: #ffffff !important;
}

#app .resources-page .resource-card:hover {
  border-color: #9fc7b6 !important;
  background: #ffffff !important;
}

#app .resources-page .resource-card .type-tag {
  border: 0 !important;
  border-radius: 3px !important;
  background: #edf4f0 !important;
}

@media (max-width: 1100px) {
  .resources-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 720px) {
  .history-filter-row {
    align-items: flex-end;
    gap: 10px;
  }

  .history-filter-row .category-tabs {
    min-width: 0;
  }

  .week-filter-caption {
    display: none;
  }

  .week-filter-trigger {
    width: 136px;
    height: 40px;
  }

  .week-filter-menu {
    top: auto;
    bottom: calc(100% + 8px);
    width: min(276px, calc(100vw - 32px));
  }

  .resources-grid {
    grid-template-columns: 1fr;
  }

  .resource-card {
    min-height: 164px;
    padding: 16px;
    grid-template-columns: 38px minmax(0, 1fr) 14px;
    gap: 11px;
  }

  .resource-card .card-icon {
    width: 36px;
    height: 36px;
  }

  .resource-card .card-content {
    min-height: 130px;
  }

  .resource-card .card-arrow {
    top: 18px;
    right: 14px;
  }
}

/* Rolled-back compact learner workspace experiment retained temporarily for the next design discussion.
.resources-page {
  padding: 24px 28px 64px;
  background: #f4f6f4;
}

.resources-header {
  max-width: 1280px;
  min-height: 92px;
  margin: 0 auto;
  padding: 17px 0 16px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 28px;
  border-bottom: 1px solid #dfe5e1;
}

.workspace-heading {
  min-width: 0;
}

.resources-kicker {
  display: block;
  margin-bottom: 3px;
  color: #6c7772;
  font-size: 12px;
  font-weight: 600;
}

.resources-title-row {
  display: flex;
  align-items: baseline;
  gap: 10px;
}

.resources-header h1 {
  color: #18211d;
  font-size: 27px;
  font-weight: 720;
  letter-spacing: 0;
}

.resource-total {
  color: #7b8580;
  font-size: 12px;
  font-variant-numeric: tabular-nums;
}

.resources-header p {
  margin: 5px 0 0;
  color: #66716c;
  font-size: 13px;
}

.workspace-actions {
  display: flex;
  align-items: center;
  gap: 9px;
}

.profile-state {
  padding-right: 13px;
  border-right: 1px solid #dce2de;
  color: #717b76;
  font-size: 12px;
  white-space: nowrap;
}

.profile-state.ready {
  color: #26694f;
}

.compact-action {
  width: 42px;
  height: 42px;
  min-height: 42px;
  padding: 0;
  border-color: #cfd8d3;
  background: transparent;
}

.compact-action:hover:not(:disabled) {
  border-color: #839e91;
  background: #edf2ef;
}

.tool-launcher {
  position: relative;
}

.generate-btn.tool-launcher-trigger {
  min-height: 42px;
  padding: 0 15px;
  gap: 8px;
  border: 1px solid #185f47;
  border-radius: 5px;
  color: #ffffff !important;
  background: #185f47;
  box-shadow: none;
  font-size: 13px;
}

.generate-btn.tool-launcher-trigger > span,
.generate-btn.tool-launcher-trigger > svg {
  color: #ffffff !important;
}

.generate-btn.tool-launcher-trigger::after {
  content: none;
}

.tool-launcher-trigger > svg:last-child {
  transition: transform 160ms ease;
}

.tool-launcher-trigger > svg:last-child.open {
  transform: rotate(180deg);
}

.resource-create-menu {
  position: absolute;
  z-index: 40;
  top: calc(100% + 9px);
  right: 0;
  width: 350px;
  padding: 13px;
  border: 1px solid #d7dfda;
  border-radius: 7px;
  background: #ffffff;
  box-shadow: 0 18px 45px rgba(28, 50, 40, 0.17);
}

.resource-create-menu-head {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 12px;
  padding: 3px 5px 10px;
  border-bottom: 1px solid #edf0ee;
}

.resource-create-menu-head strong {
  color: #1c2823;
  font-size: 14px;
}

.resource-create-menu-head span {
  color: #8a938f;
  font-size: 11px;
}

.resource-create-options {
  display: grid;
  padding: 6px 0;
}

.resource-create-option {
  min-height: 53px;
  padding: 7px 8px;
  display: grid;
  grid-template-columns: 28px minmax(0, 1fr);
  align-items: center;
  gap: 9px;
  border-radius: 4px;
  color: #315b4a;
  text-decoration: none;
  transition: color 160ms ease, background-color 160ms ease, transform 160ms ease;
}

.resource-create-option:hover,
.resource-create-option:focus-visible {
  color: #174f3b;
  background: #f0f4f1;
  transform: translateX(2px);
}

.resource-create-option:focus-visible {
  outline: 2px solid #8db7a5;
  outline-offset: -2px;
}

.resource-create-option > span {
  min-width: 0;
  display: grid;
  gap: 2px;
}

.resource-create-option strong {
  color: #26332d;
  font-size: 13px;
  font-weight: 650;
}

.resource-create-option small {
  color: #7b8580;
  font-size: 11px;
}

.profile-generate-action {
  width: 100%;
  min-height: 40px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 7px;
  border: 1px solid #cdd8d2;
  border-radius: 4px;
  color: #285f49;
  background: #f7f9f7;
  font: inherit;
  font-size: 12px;
  font-weight: 650;
  cursor: pointer;
}

.profile-generate-action:hover:not(:disabled) {
  border-color: #8fb2a2;
  background: #edf4f0;
}

.profile-generate-action:disabled {
  color: #9aa19e;
  cursor: not-allowed;
}

.no-profile-banner {
  max-width: 1280px;
  margin: 12px auto 0;
}

.resources-content {
  max-width: 1280px;
  margin: 0 auto;
  padding: 22px 0 34px;
}

.history-resources-head {
  margin-bottom: 13px;
}

.history-title-group {
  display: flex;
  align-items: baseline;
  gap: 10px;
}

.history-resources-head h2,
.history-resources-head h2::before {
  color: #1b2420;
  font-size: 19px;
  font-weight: 680;
}

.history-resources-head h2::before,
.history-resources-head h2::after {
  content: none;
}

.history-title-group > span {
  color: #7c8581;
  font-size: 12px;
}

.history-filter-row {
  min-height: 50px;
  margin-bottom: 18px;
  padding: 0 0 9px;
}

.history-filter-row .category-tabs {
  gap: 2px;
}

#app .resources-page .tab-btn {
  min-width: auto;
  min-height: 36px;
  padding: 0 12px;
  border-bottom: 2px solid transparent !important;
  border-radius: 0 !important;
  color: #69736e;
  font-size: 13px;
}

#app .resources-page .tab-btn:hover {
  color: #174f3c;
  background: transparent !important;
}

#app .resources-page .tab-btn.active {
  border-bottom-color: #1b6b50 !important;
  color: #174f3c;
  background: transparent !important;
  font-weight: 650;
}

.week-filter-trigger {
  border-radius: 4px;
  background: transparent;
}

.resources-grid {
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 18px !important;
}

#app .resources-page .resource-card {
  position: relative;
  min-height: 270px;
  padding: 0;
  display: grid;
  grid-template-columns: 1fr;
  grid-template-rows: 100px minmax(0, 1fr);
  gap: 0;
  overflow: hidden;
  border: 1px solid #dfe5e1 !important;
  border-radius: 6px !important;
  background: #ffffff !important;
  box-shadow: 0 2px 4px rgba(28, 51, 41, 0.025);
  transition: transform 180ms ease, border-color 180ms ease, box-shadow 180ms ease;
}

#app .resources-page .resource-card:hover {
  transform: translateY(-4px);
  border-color: #a7bcb2 !important;
  background: #ffffff !important;
  box-shadow: 0 13px 28px rgba(34, 65, 51, 0.11);
}

.resource-cover {
  position: relative;
  min-width: 0;
  overflow: hidden;
  padding: 14px 16px;
  color: #f7f5eb;
  background: #225f4c;
}

.resource-cover::before {
  content: "";
  position: absolute;
  width: 122px;
  height: 122px;
  right: -25px;
  bottom: -72px;
  border: 1px solid rgba(238, 219, 166, 0.5);
  border-radius: 50%;
  box-shadow: 0 0 0 13px rgba(238, 219, 166, 0.08), 0 0 0 28px rgba(238, 219, 166, 0.06);
}

.resource-cover-type {
  position: relative;
  z-index: 1;
  padding: 0 !important;
  border: 0 !important;
  border-radius: 0 !important;
  color: rgba(255, 255, 255, 0.7);
  background: transparent !important;
  font-size: 11px;
}

.resource-cover > strong {
  position: absolute;
  z-index: 2;
  left: 16px;
  bottom: 13px;
  display: block !important;
  color: #fffdf3;
  font-size: 22px;
  font-weight: 620;
  letter-spacing: 0;
}

.cover-seal {
  position: absolute;
  top: 14px;
  right: 15px;
  width: 24px;
  height: 24px;
  display: grid;
  place-items: center;
  border: 1px solid rgba(244, 211, 137, 0.8);
  color: #f4d389;
  font-family: serif;
  font-size: 13px;
}

.cover-line {
  position: absolute;
  display: block !important;
  padding: 0 !important;
  border: 0 !important;
  border-radius: 0 !important;
  height: 1px;
  min-height: 0 !important;
  background: rgba(242, 213, 147, 0.55);
  transform-origin: left center;
}

.cover-line-one {
  width: 122px;
  left: 92px;
  top: 31px;
  transform: rotate(24deg);
}

.cover-line-two {
  width: 85px;
  left: 106px;
  top: 62px;
  transform: rotate(-18deg);
}

.cover-ppt { background: #2c5b4b; }
.cover-mindmap { background: #355b57; }
.cover-video,
.cover-generated_video { background: #466054; }
.cover-quiz { background: #725d36; }

.resource-card .card-content {
  min-height: 0;
  padding: 16px 42px 16px 17px;
}

.resource-card .card-content h3 {
  margin: 0 0 8px;
  color: #1d2823;
  font-size: 15px;
  font-weight: 650;
  line-height: 1.45;
  display: -webkit-box;
  overflow: hidden;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
}

.resource-card .card-desc {
  margin: 0;
  color: #6f7974;
  font-size: 12px;
  line-height: 1.55;
  display: -webkit-box;
  overflow: hidden;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
}

.resource-card .card-footer {
  margin-top: auto;
  padding-top: 13px;
  gap: 8px;
  color: #858d89;
  font-size: 11px;
}

.review-state::before {
  content: "";
  width: 5px;
  height: 5px;
  display: inline-block;
  margin: 0 6px 1px 0;
  border-radius: 50%;
  background: #5c9279;
}

#app .resources-page .review-state {
  padding: 0 !important;
  border: 0 !important;
  border-radius: 0 !important;
  color: #63716a !important;
  background: transparent !important;
  font-size: 11px;
  font-weight: 500;
}

.resource-card .learned-badge {
  padding: 0;
  color: #356a53 !important;
  background: transparent;
}

.resource-card .badge-stars {
  display: none;
}

.resource-card .card-arrow {
  top: auto;
  right: 17px;
  bottom: 18px;
  color: #8f9994;
}

@media (max-width: 1100px) {
  .resources-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 720px) {
  .resources-page {
    padding: 15px 16px calc(112px + env(safe-area-inset-bottom));
  }

  .resources-header {
    min-height: auto;
    padding: 10px 0 14px;
    align-items: flex-start;
    gap: 13px;
  }

  .resources-header h1 {
    font-size: 23px;
  }

  .resources-header p,
  .profile-state,
  .tool-launcher-trigger > span {
    display: none;
  }

  .workspace-actions {
    padding-top: 14px;
  }

  .generate-btn.tool-launcher-trigger {
    width: 42px;
    padding: 0;
    justify-content: center;
  }

  .tool-launcher-trigger > svg:last-child {
    display: none;
  }

  .resource-create-menu {
    position: fixed;
    top: auto;
    right: 16px;
    bottom: calc(86px + env(safe-area-inset-bottom));
    width: calc(100vw - 32px);
    max-height: calc(100dvh - 120px);
    overflow-y: auto;
  }

  .resources-content {
    padding-top: 18px;
  }

  .history-title-group {
    align-items: flex-end;
  }

  .history-filter-row {
    flex-wrap: wrap;
    align-items: center;
  }

  .history-filter-row .category-tabs {
    flex-basis: 100%;
    order: 2;
  }

  .week-filter {
    margin-left: auto;
  }

  .week-filter-trigger {
    width: 142px;
  }

  .resources-grid {
    grid-template-columns: 1fr;
    gap: 14px !important;
  }

  #app .resources-page .resource-card {
    min-height: 250px;
    grid-template-rows: 86px minmax(0, 1fr);
  }
}
*/

/* 2026-08-29: restrained topic-course workspace */
.resources-page {
  --topic-cover-background: #f3f5f1;
  padding: 28px 32px 64px;
  background: #f7f8f7;
}

.resources-header,
.resource-tools-section,
.resources-content {
  max-width: 1320px;
}

.resources-header {
  min-height: 0;
  margin-bottom: 0;
  padding: 4px 0 14px;
}

.resource-tools-section {
  margin-top: 0;
  margin-bottom: 0;
  padding: 8px 0 12px;
  border: 0;
  border-radius: 0;
  background: transparent;
}

.resource-tools-head {
  margin: 0 0 10px;
  padding: 0;
}

.resource-tools-head h2 {
  color: #202b27;
  font-size: 21px;
  font-weight: 650;
}

.resource-tools-grid {
  grid-template-columns: repeat(6, minmax(0, 1fr));
  gap: 0;
  border-top: 1px solid #e1e6e2;
  border-bottom: 1px solid #e1e6e2;
}

#app .resources-page .resource-tool-card,
#app .resources-page .resource-tool-card[class*="tool-"] {
  min-height: 88px;
  padding: 13px 12px 12px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 8px;
  border: 0 !important;
  border-right: 1px solid #e1e6e2 !important;
  border-radius: 0 !important;
  color: #26332e;
  background: transparent !important;
  box-shadow: none !important;
  text-align: center;
  transition: color 160ms ease, background-color 160ms ease, transform 160ms ease;
}

#app .resources-page .resource-tool-card:last-child {
  border-right: 0 !important;
}

#app .resources-page .resource-tool-card:hover {
  color: #176b50;
  background: #f0f4f1 !important;
  transform: translateY(-2px);
}

#app .resources-page .resource-tool-card .resource-tool-icon,
#app .resources-page .resource-tool-card[class*="tool-"] .resource-tool-icon {
  width: 30px;
  height: 30px;
  border: 0;
  border-radius: 0;
  color: currentColor;
  background: transparent !important;
}

.resource-tool-card > strong {
  color: currentColor;
  font-size: 14px;
  font-weight: 620;
  line-height: 1.2;
}

.resources-content {
  margin-top: 0;
  padding: 4px 0 36px;
  border: 0;
  border-radius: 0;
  background: transparent;
}

.history-resources-head {
  margin-bottom: 12px;
  padding: 0;
}

.history-title-group {
  display: flex;
  align-items: baseline;
  gap: 10px;
}

.history-resources-head h2 {
  margin: 0;
  color: #202b27;
  font-size: 21px !important;
  font-weight: 650;
}

.history-resources-head h2::before,
.history-resources-head h2::after {
  content: none !important;
  display: none !important;
}

.history-title-group > span {
  color: #7b8580;
  font-size: 12px;
}

.history-head-actions {
  gap: 8px;
}

.history-refresh-btn,
.generate-btn {
  min-height: 40px;
  border-radius: 5px;
}

.history-status,
.compact-empty-state {
  margin: 0 0 12px;
}

.compact-empty-state {
  min-height: 0;
  padding: 10px 13px;
  display: flex;
  justify-content: flex-start;
  border: 1px solid #e0e6e2;
  border-radius: 5px;
  color: #68736e;
  background: #fafbfa;
  font-size: 12px;
  text-align: left;
}

.resources-grid,
#app .resources-page .resources-grid {
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 18px !important;
}

#app .resources-page .resource-card.topic-card {
  min-width: 0;
  min-height: 0;
  padding: 0;
  display: grid;
  grid-template-columns: minmax(0, 1fr);
  grid-template-rows: auto minmax(108px, auto);
  align-items: stretch;
  gap: 0;
  overflow: hidden;
  border: 1px solid #dfe5e1 !important;
  border-radius: 8px !important;
  color: #25322d;
  background: #ffffff !important;
  box-shadow: 0 3px 11px rgba(30, 56, 45, 0.08);
  text-align: left;
  transition: transform 180ms ease, border-color 180ms ease, box-shadow 180ms ease;
}

#app .resources-page .resource-card.topic-card:hover {
  transform: translateY(-4px);
  border-color: #adc1b7 !important;
  background: #ffffff !important;
  box-shadow: 0 12px 24px rgba(30, 56, 45, 0.09);
}

.topic-card-media {
  position: relative;
  isolation: isolate;
  aspect-ratio: 16 / 9;
  min-width: 0;
  overflow: hidden;
  border-bottom: 1px solid #e5e9e6;
  color: #ffffff;
}

.topic-card-media::before,
.topic-card-media::after {
  position: absolute;
  content: '';
  pointer-events: none;
}

.topic-card-media::before {
  z-index: -1;
  inset: 0;
  background: none;
}

.topic-card-media::after {
  z-index: -1;
  background: none;
}

.cover-cyan {
  background-color: #48a8cf;
  background-image:
    radial-gradient(circle at 8% 82%, rgba(44, 126, 184, 0.2) 0 10%, transparent 10.5%),
    radial-gradient(ellipse at 104% 108%, rgba(255, 255, 255, 0.12) 0 25%, transparent 25.5%),
    linear-gradient(118deg, #55b5dc 0%, #3d9fd1 62%, #4d99c7 100%);
}

.cover-cyan::before {
  inset: -50% 42% -36% -34%;
  border-radius: 48%;
  opacity: 0.82;
  background:
    radial-gradient(ellipse at 44% 54%, transparent 0 24%, rgba(255, 255, 255, 0.15) 24.5% 31%, transparent 31.5% 42%, rgba(255, 255, 255, 0.11) 42.5% 50%, transparent 50.5%),
    radial-gradient(ellipse at 38% 48%, transparent 0 61%, rgba(255, 255, 255, 0.08) 61.5% 69%, transparent 69.5%);
  transform: rotate(-13deg);
}

.cover-cyan::after {
  right: 0;
  top: 0;
  width: 45%;
  height: 100%;
  opacity: 0.4;
  background:
    radial-gradient(rgba(255, 255, 255, 0.72) 0.8px, transparent 1px) 100% 0 / 6px 6px,
    repeating-radial-gradient(ellipse at 100% 110%, transparent 0 17px, rgba(255, 255, 255, 0.18) 18px 19px, transparent 20px 27px);
  -webkit-mask-image: linear-gradient(135deg, transparent 8%, #000 86%);
  mask-image: linear-gradient(135deg, transparent 8%, #000 86%);
}

.cover-orange {
  background-color: #de9752;
  background-image:
    radial-gradient(ellipse at 102% 112%, rgba(255, 255, 255, 0.16) 0 31%, transparent 31.5%),
    linear-gradient(112deg, #f18162 0%, #e59452 52%, #d4ab3e 100%);
}

.cover-orange::before {
  inset: 0 18% 48% 0;
  opacity: 0.62;
  background: repeating-radial-gradient(ellipse at 34% -115%, transparent 0 7px, rgba(255, 255, 255, 0.2) 8px 9px, transparent 10px 14px);
}

.cover-orange::after {
  inset: 42% -12% -46% 26%;
  opacity: 0.68;
  background:
    radial-gradient(ellipse at 60% 0, transparent 0 43%, rgba(255, 255, 255, 0.14) 43.5% 54%, transparent 54.5%),
    repeating-radial-gradient(ellipse at 70% 0, transparent 0 18px, rgba(255, 255, 255, 0.12) 19px 20px, transparent 21px 27px);
  transform: rotate(-7deg);
}

.cover-blue {
  background-color: #5288c9;
  background-image:
    linear-gradient(154deg, transparent 0 55%, rgba(255, 255, 255, 0.08) 55.5% 67%, transparent 67.5%),
    linear-gradient(112deg, #54c1d2 0%, #4a9fc9 42%, #4f73c8 100%);
}

.cover-blue::before {
  inset: 0 14% 52% 0;
  opacity: 0.6;
  background: repeating-radial-gradient(ellipse at 24% -120%, transparent 0 7px, rgba(255, 255, 255, 0.18) 8px 9px, transparent 10px 14px);
}

.cover-blue::after {
  inset: 50% -12% -8% 34%;
  opacity: 0.58;
  background:
    repeating-radial-gradient(ellipse at 88% 112%, transparent 0 8px, rgba(255, 255, 255, 0.16) 9px 10px, transparent 11px 15px),
    radial-gradient(ellipse at 78% 110%, transparent 0 44%, rgba(255, 255, 255, 0.12) 44.5% 59%, transparent 59.5%);
  transform: rotate(-4deg);
}

.cover-pink {
  background-color: #cf67a7;
  background-image:
    radial-gradient(ellipse at 104% -20%, rgba(255, 255, 255, 0.13) 0 38%, transparent 38.5%),
    linear-gradient(108deg, #cc5ca4 0%, #d75ba8 58%, #e255a7 100%);
}

.cover-pink::before {
  inset: -88% -26% 20% 16%;
  border-radius: 46%;
  opacity: 0.82;
  background:
    radial-gradient(ellipse, transparent 0 36%, rgba(255, 255, 255, 0.14) 36.5% 52%, transparent 52.5%),
    radial-gradient(ellipse, transparent 0 66%, rgba(255, 255, 255, 0.09) 66.5% 76%, transparent 76.5%);
  transform: rotate(-8deg);
}

.cover-pink::after {
  inset: 0;
  opacity: 0.32;
  background:
    radial-gradient(rgba(255, 255, 255, 0.8) 0.7px, transparent 1px) 0 0 / 6px 6px,
    radial-gradient(rgba(255, 255, 255, 0.72) 0.7px, transparent 1px) 100% 100% / 7px 7px;
  -webkit-mask-image: linear-gradient(135deg, #000 0, transparent 31%, transparent 69%, #000 100%);
  mask-image: linear-gradient(135deg, #000 0, transparent 31%, transparent 69%, #000 100%);
}

.cover-coral {
  background-color: #d96970;
  background-image:
    radial-gradient(ellipse at 86% -18%, rgba(182, 39, 70, 0.22) 0 32%, transparent 32.5%),
    linear-gradient(115deg, #f2827b 0%, #e86570 46%, #d74357 100%);
}

.cover-coral::before {
  inset: 0 24% 54% 0;
  opacity: 0.58;
  background: repeating-radial-gradient(ellipse at 32% -125%, transparent 0 7px, rgba(255, 255, 255, 0.18) 8px 9px, transparent 10px 14px);
}

.cover-coral::after {
  inset: 38% -10% -40% -8%;
  opacity: 0.55;
  background:
    radial-gradient(ellipse at 8% 72%, transparent 0 21%, rgba(255, 255, 255, 0.13) 21.5% 31%, transparent 31.5%),
    repeating-radial-gradient(ellipse at 100% 12%, transparent 0 8px, rgba(255, 255, 255, 0.12) 9px 10px, transparent 11px 15px);
  transform: rotate(4deg);
}

.cover-violet {
  background-color: #7563c7;
  background-image:
    linear-gradient(154deg, transparent 0 55%, rgba(255, 255, 255, 0.09) 55.5% 68%, transparent 68.5%),
    linear-gradient(112deg, #5c59e2 0%, #6747cf 48%, #7136b6 100%);
}

.cover-violet::before {
  inset: 0 12% 50% 0;
  opacity: 0.62;
  background: repeating-radial-gradient(ellipse at 26% -115%, transparent 0 7px, rgba(255, 255, 255, 0.19) 8px 9px, transparent 10px 14px);
}

.cover-violet::after {
  inset: 48% -12% -10% 26%;
  opacity: 0.6;
  background:
    repeating-radial-gradient(ellipse at 88% 112%, transparent 0 8px, rgba(255, 255, 255, 0.15) 9px 10px, transparent 11px 15px),
    radial-gradient(ellipse at 78% 108%, transparent 0 44%, rgba(255, 255, 255, 0.12) 44.5% 58%, transparent 58.5%);
  transform: rotate(-4deg);
}

.cover-green {
  background-color: #61c793;
  background-image:
    linear-gradient(132deg, transparent 0 30%, rgba(255, 255, 255, 0.08) 30.5% 54%, transparent 54.5%),
    linear-gradient(112deg, #74dba9 0%, #5bd797 48%, #4bd374 100%);
}

.cover-green::before {
  inset: -58% 32% 46% -24%;
  opacity: 0.62;
  background: repeating-radial-gradient(ellipse at 34% 94%, transparent 0 8px, rgba(255, 255, 255, 0.16) 9px 10px, transparent 11px 16px);
  transform: rotate(-7deg);
}

.cover-green::after {
  inset: 0;
  opacity: 0.66;
  background:
    radial-gradient(circle at 4% 96%, rgba(255, 255, 255, 0.16) 0 8%, transparent 8.5%),
    radial-gradient(circle at 13% 96%, rgba(255, 255, 255, 0.14) 0 6%, transparent 6.5%),
    radial-gradient(circle at 96% 100%, rgba(255, 255, 255, 0.17) 0 10%, transparent 10.5%),
    radial-gradient(circle at 87% 100%, rgba(255, 255, 255, 0.12) 0 7%, transparent 7.5%);
}

.cover-sky {
  background-color: #5ea2c1;
  background-image:
    linear-gradient(132deg, transparent 0 24%, rgba(255, 255, 255, 0.09) 24.5% 42%, transparent 42.5%),
    linear-gradient(132deg, transparent 0 58%, rgba(63, 135, 182, 0.14) 58.5% 76%, transparent 76.5%),
    linear-gradient(110deg, #62b2d1 0%, #5ca7ca 54%, #5b9bc3 100%);
}

.cover-sky::before {
  inset: -62% 48% 40% -34%;
  border-radius: 48%;
  opacity: 0.68;
  background:
    radial-gradient(ellipse, transparent 0 33%, rgba(255, 255, 255, 0.14) 33.5% 45%, transparent 45.5%),
    radial-gradient(ellipse, transparent 0 58%, rgba(255, 255, 255, 0.09) 58.5% 68%, transparent 68.5%);
  transform: rotate(-12deg);
}

.cover-sky::after {
  right: 0;
  bottom: 0;
  width: 42%;
  height: 52%;
  opacity: 0.34;
  background:
    radial-gradient(rgba(255, 255, 255, 0.72) 0.75px, transparent 1px) 100% 100% / 7px 7px,
    repeating-radial-gradient(ellipse at 100% 112%, transparent 0 18px, rgba(255, 255, 255, 0.13) 19px 20px, transparent 21px 28px);
  -webkit-mask-image: linear-gradient(135deg, transparent, #000 82%);
  mask-image: linear-gradient(135deg, transparent, #000 82%);
}

.topic-card-media::before,
.topic-card-media::after {
  display: none;
}

.topic-card-media.cover-cyan {
  background-image: linear-gradient(112deg, #56b3d9 0%, #3d9dcf 100%);
}

.topic-card-media.cover-orange {
  background-image: linear-gradient(112deg, #ef8063 0%, #d5aa3e 100%);
}

.topic-card-media.cover-blue {
  background-image: linear-gradient(112deg, #55bdd0 0%, #4d74c6 100%);
}

.topic-card-media.cover-pink {
  background-image: linear-gradient(108deg, #cb61a3 0%, #df58a7 100%);
}

.topic-card-media.cover-coral {
  background-image: linear-gradient(114deg, #ed8079 0%, #d54759 100%);
}

.topic-card-media.cover-violet {
  background-image: linear-gradient(112deg, #5d5cdd 0%, #7139b8 100%);
}

.topic-card-media.cover-green {
  background-image: linear-gradient(112deg, #74d8a7 0%, #4bcf76 100%);
}

.topic-card-media.cover-sky {
  background-image: linear-gradient(110deg, #65b1ce 0%, #5b9bc2 100%);
}

.topic-cover-texture {
  position: absolute;
  z-index: 0;
  inset: 0;
  width: 100%;
  height: 100%;
  object-fit: cover;
  opacity: 0.22;
  pointer-events: none;
  transform: scale(1.001);
  transition: opacity 180ms ease, transform 220ms ease;
}

.topic-card:hover .topic-cover-texture {
  opacity: 0.28;
  transform: scale(1.015);
}

.topic-cover-label {
  position: absolute;
  z-index: 1;
  left: 18px;
  top: 50%;
  width: calc(100% - 118px);
  min-height: 0;
  padding: 0 !important;
  border: 0 !important;
  border-radius: 0 !important;
  color: rgba(255, 255, 255, 0.96);
  background: transparent !important;
  box-shadow: none !important;
  font-size: 20px;
  font-weight: 500;
  line-height: 1.35;
  letter-spacing: 0;
  transform: translateY(-50%);
}

.topic-cover-icon {
  position: absolute;
  z-index: 1;
  top: 50%;
  right: 20px;
  width: 72px;
  height: 72px;
  padding: 0 !important;
  display: grid;
  place-items: center;
  border: 0 !important;
  border-radius: 0 !important;
  color: rgba(255, 249, 230, 0.74);
  background: transparent !important;
  transform: translateY(-50%);
  transition: transform 220ms ease;
}

.topic-cover-icon-image {
  width: 100%;
  height: 100%;
  display: block;
  object-fit: contain;
  opacity: 0.78;
  filter: drop-shadow(0 5px 8px rgba(36, 47, 54, 0.12));
}

.topic-cover-icon[data-glyph='ginseng'] {
  width: 78px;
  height: 78px;
}

.topic-cover-icon[data-glyph='leaf'] {
  transform: translateY(-50%) rotate(-8deg);
}

.topic-cover-icon[data-glyph='pulse'] {
  width: 76px;
  height: 76px;
}

.topic-cover-icon[data-glyph='acupoint'] {
  width: 68px;
  height: 68px;
}

.topic-card:hover .topic-cover-icon {
  transform: translateY(-50%) scale(1.035);
}

.topic-card:hover .topic-cover-icon[data-glyph='leaf'] {
  transform: translateY(-50%) rotate(-6deg) scale(1.035);
}

.topic-card-body {
  position: relative;
  min-width: 0;
  padding: 13px 38px 13px 15px;
  display: grid;
  grid-template-columns: minmax(0, 1fr);
  align-content: center;
  gap: 6px;
}

.topic-card-copy {
  min-width: 0;
}

.topic-card-copy h3 {
  margin: 0 0 4px;
  color: #202b27;
  font-size: 16px;
  font-weight: 650;
  line-height: 1.3;
}

.topic-card-copy p {
  margin: 0;
  overflow: hidden;
  color: #75807a;
  font-size: 12px;
  line-height: 1.45;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.topic-card-meta {
  color: #8a928e;
  font-size: 11px;
  line-height: 1.3;
}

#app .resources-page .topic-card-meta {
  min-height: 0;
  padding: 0 !important;
  border: 0 !important;
  border-radius: 0 !important;
  color: #8a928e !important;
  background: transparent !important;
  font-weight: 400;
}

.topic-card-body > svg {
  position: absolute;
  right: 14px;
  bottom: 15px;
  color: #7f8b85;
  transition: color 160ms ease, transform 160ms ease;
}

.topic-card:hover .topic-card-body > svg {
  color: #176b50;
  transform: translate(2px, -2px);
}

@media (max-width: 1120px) {
  .resources-grid,
  #app .resources-page .resources-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 720px) {
  .resources-page {
    padding: 16px 16px calc(112px + env(safe-area-inset-bottom));
  }

  .resources-header {
    margin-bottom: 0;
    padding: 2px 0 10px;
  }

  .resource-tools-section {
    margin-bottom: 0;
    padding: 6px 0 8px;
  }

  .resource-tools-head h2,
  .history-resources-head h2 {
    font-size: 19px !important;
  }

  .resource-tools-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
    border-bottom: 0;
  }

  #app .resources-page .resource-tool-card,
  #app .resources-page .resource-tool-card[class*="tool-"] {
    min-height: 74px;
    border-bottom: 1px solid #e1e6e2 !important;
  }

  #app .resources-page .resource-tool-card:nth-child(2n) {
    border-right: 0 !important;
  }

  #app .resources-page .resource-tool-card:last-child {
    border-right: 1px solid #e1e6e2 !important;
  }

  .resources-content {
    padding-top: 8px;
  }

  .history-resources-head {
    align-items: flex-end;
    gap: 10px;
  }

  .history-title-group {
    display: grid;
    gap: 2px;
  }

  .history-refresh-btn,
  .generate-btn {
    min-height: 38px;
    padding-inline: 11px;
    font-size: 12px;
  }

  .resources-grid,
  #app .resources-page .resources-grid {
    grid-template-columns: minmax(0, 1fr);
    gap: 14px !important;
  }

  #app .resources-page .resource-card.topic-card {
    grid-template-rows: auto minmax(100px, auto);
  }

  .topic-cover-label {
    font-size: 19px;
  }

  .topic-card-copy h3 {
    font-size: 15px;
  }
}

@media (prefers-reduced-motion: reduce) {
  #app .resources-page .resource-tool-card,
  #app .resources-page .resource-card.topic-card,
  .topic-cover-texture,
  .topic-cover-icon,
  .topic-card-body > svg {
    transition: none !important;
  }
}
</style>
