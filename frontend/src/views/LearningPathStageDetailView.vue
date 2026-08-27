<template>
  <main class="clean-map-page">
    <section
      ref="mapViewportRef"
      class="clean-map-viewport"
      :class="{
        'week-overview-map': isWeekOverview,
        'compact-week-map': compactMap && isWeekOverview,
        'has-active-node': compactMap && isWeekOverview && Boolean(activeNode),
        'has-path-notice': Boolean(profileSwitchNotice),
      }"
      :style="compactViewportStyle"
      :aria-label="isWeekOverview ? '学习周次地图' : stageTitle"
    >
      <button
        v-if="!isWeekOverview"
        class="stage-exit-button"
        type="button"
        aria-label="退出当前学习路径地图"
        @pointerdown.stop
        @click.stop="exitStage"
      >
        <ArrowLeft :size="16" stroke-width="2.3" aria-hidden="true" />
        <span>选择周次</span>
      </button>

      <aside
        v-if="isWeekOverview && hasActiveLearningProfile && !pathLoadError"
        class="current-profile-path-switcher"
        aria-label="当前学习画像路径切换"
        @pointerdown.stop
      >
        <div class="profile-path-switcher-head">
          <span><UserRoundCheck :size="19" stroke-width="2.2" aria-hidden="true" /></span>
          <div>
            <small>当前画像路径</small>
            <strong>{{ activeProfilePathTitle }}</strong>
          </div>
          <em v-if="activeProfileSummary?.version">v{{ activeProfileSummary.version }}</em>
        </div>
        <p :class="{ error: Boolean(profilePathSwitchError) }">
          {{ profilePathSwitchError || activeProfilePathStatus }}
        </p>
        <button
          type="button"
          :disabled="profileSummaryLoading || profilePathSwitching || generationIsRunning || !activeProfileSummary?.id"
          @click.stop="switchToCurrentProfilePath"
        >
          <RefreshCcw :size="15" :class="{ spinning: profilePathSwitching }" aria-hidden="true" />
          {{ profilePathSwitchButtonLabel }}
        </button>
      </aside>

      <aside
        v-if="hasActiveLearningProfile && !pathLoadError"
        class="stage-overview"
        :aria-label="isWeekOverview ? '学习周次与进度' : '本周任务与资源'"
        @pointerdown.stop
      >
        <strong>{{ isWeekOverview ? '学习周次与进度' : '本周任务与资源' }}</strong>
        <div class="overview-body">
          <div class="overview-ring" :style="{ '--progress': `${stageProgressPercent}%` }">
            <b>{{ stageProgressPercent }}%</b>
            <span>整体进度</span>
          </div>
          <dl>
            <div>
              <dt>已完成</dt>
              <dd>{{ stageMetrics.done }} / {{ stageMetrics.total }} {{ isWeekOverview ? '周' : '任务' }}</dd>
            </div>
            <div>
              <dt>{{ isWeekOverview ? '已选周次' : '已选任务' }}</dt>
              <dd>{{ activeNode?.label || '--' }}</dd>
            </div>
            <div>
              <dt>状态</dt>
              <dd>{{ activeNode?.statusText || '待推进' }}</dd>
            </div>
          </dl>
        </div>
      </aside>

      <div
        v-if="profileSwitchNotice && !pathLoadError"
        class="path-basis-notice"
        role="status"
        @pointerdown.stop
      >
        <CircleAlert :size="18" stroke-width="2.3" aria-hidden="true" />
        <span>
          <strong>您的学习路径任务已切换</strong>
          <small>{{ profileSwitchNotice }}</small>
        </span>
        <button type="button" @click.stop="profileSwitchNotice = ''">
          知道了
        </button>
      </div>

      <div v-if="hasActiveLearningProfile && !pathLoadError" class="map-board" :style="boardStyle">
        <svg class="route-layer" :viewBox="`0 0 ${boardSize.width} ${boardSize.height}`" aria-hidden="true">
          <defs>
            <linearGradient id="learning-route-done" x1="0" y1="0" x2="1" y2="0">
              <stop offset="0%" stop-color="#16c7a0" />
              <stop offset="100%" stop-color="#2f8cff" />
            </linearGradient>
            <filter id="learning-route-glow" x="-20%" y="-80%" width="140%" height="260%">
              <feGaussianBlur stdDeviation="3.2" result="blur" />
              <feMerge>
                <feMergeNode in="blur" />
                <feMergeNode in="SourceGraphic" />
              </feMerge>
            </filter>
          </defs>
          <path v-if="fullRoutePath" class="route route-pending" :d="fullRoutePath" />
          <path v-if="completedRoutePath" class="route route-done" :d="completedRoutePath" />
        </svg>

        <button
          v-for="node in sortedNodes"
          :key="node.id"
          type="button"
          class="map-dot"
          :class="node.state"
          :data-active="activeNode?.id === node.id ? 'true' : undefined"
          :style="{
            left: `${node.x}px`,
            top: `${node.y}px`,
            '--academy-enter-index': node.academyEnterIndex,
          }"
          :aria-label="`${node.label} ${node.mapTitle}：${node.title}`"
          @pointerdown.stop
          @pointerup.stop="selectNode(node)"
          @click.stop="selectNode(node)"
        >
          <LearningPathAcademyNode
            v-if="isWeekOverview"
            :stage="node.academyStage"
            :growth="node.academyGrowth"
            :label="node.label"
            :state="node.state"
          />
          <span v-else class="dot-core">
            <CheckCircle2 v-if="node.state === 'done'" :size="31" stroke-width="2.6" aria-hidden="true" />
            <span v-else>{{ node.label }}</span>
          </span>
          <b class="dot-title">{{ isWeekOverview ? node.mapTitle : node.title }}</b>
          <small class="dot-state">{{ node.statusText }}</small>
        </button>

        <article v-if="activeNode" class="node-popover" :style="popoverStyle" @pointerdown.stop>
          <button class="popover-close" type="button" aria-label="关闭详情" @click.stop="activeNodeId = ''">
            <X :size="14" />
          </button>
          <div class="popover-head">
            <span class="popover-icon" :class="activeNode.state">
              <BookOpen :size="23" stroke-width="2.1" />
            </span>
            <div>
              <h2>{{ activeNode.title }}</h2>
              <p class="node-status" :class="activeNode.state"><span></span>{{ activeNode.statusText }}</p>
            </div>
          </div>
          <p class="node-desc">{{ activeNode.description }}</p>
          <div class="node-progress">
            <span>进度</span>
            <i><b :style="{ width: `${nodeProgress(activeNode)}%` }"></b></i>
            <em>{{ nodeProgress(activeNode) }}%</em>
          </div>
          <button
            class="enter-button"
            type="button"
            :disabled="!activeNode.actionRoute || activeNode.state === 'locked'"
            @click.stop="openNodeAction(activeNode)"
          >
            {{ activeNode.actionText || '进入关卡' }}
            <ArrowRight :size="15" />
          </button>
        </article>
      </div>

      <div v-if="!loading && pathLoadError" class="path-load-error" role="alert">
        <CircleAlert :size="24" stroke-width="2.2" aria-hidden="true" />
        <span>
          <strong>学习路径加载失败</strong>
          <small>{{ pathLoadError.message }}</small>
          <small v-if="activeProfileSummary?.id">当前画像：{{ activeProfilePathTitle }}</small>
        </span>
        <button type="button" @click="retryLearningPathLoad">
          <RotateCcw :size="15" aria-hidden="true" />
          重新加载
        </button>
      </div>

      <div v-if="!loading && !pathLoadError && !generationError && (!hasActiveLearningProfile || !sortedNodes.length)" class="empty-path-state" role="status">
        <strong>{{ hasActiveLearningProfile ? '尚未生成学习路径' : '当前没有学习画像' }}</strong>
        <span>{{ hasActiveLearningProfile ? '岐小智会按你的目标、薄弱点和资源偏好生成周学习计划。' : '请先完成学习画像后再生成个性化周任务。' }}</span>
        <button type="button" @click="handlePersonalizationAction">
          {{ hasActiveLearningProfile ? '生成学习路径' : '完成学习画像' }}
        </button>
      </div>

      <aside
        v-if="generationConsoleVisible"
        class="generation-console"
        :class="{ expanded: generationConsoleExpanded, failed: Boolean(generationError) }"
        aria-label="学习路径生成详细输出"
        @pointerdown.stop
      >
        <button
          class="generation-console-summary"
          type="button"
          :aria-expanded="generationConsoleExpanded"
          @click="generationConsoleExpanded = !generationConsoleExpanded"
        >
          <span class="generation-console-icon" :class="generationConsoleState">
            <span v-if="generationIsRunning" class="generation-spinner" aria-hidden="true"></span>
            <CircleAlert v-else-if="generationError" :size="17" aria-hidden="true" />
            <SquareTerminal v-else :size="17" aria-hidden="true" />
          </span>
          <span class="generation-console-copy">
            <strong>{{ generationConsoleTitle }}</strong>
            <small>{{ generationConsoleSubtitle }}</small>
          </span>
          <b>{{ generationProgress }}%</b>
          <ChevronUp v-if="generationConsoleExpanded" :size="17" aria-hidden="true" />
          <ChevronDown v-else :size="17" aria-hidden="true" />
        </button>

        <div class="generation-console-progress" aria-hidden="true">
          <span :style="{ width: `${generationProgress}%` }"></span>
        </div>

        <div v-if="generationConsoleExpanded" class="generation-console-detail">
          <dl class="generation-console-meta">
            <div><dt>当前智能体</dt><dd>{{ generationAgent }}</dd></div>
            <div><dt>执行阶段</dt><dd>{{ generationStage }}</dd></div>
            <div><dt>生成尝试</dt><dd>第 {{ generationAttempt }} 次</dd></div>
            <div><dt>质量审核</dt><dd>{{ generationReview }}</dd></div>
            <div v-if="generationRunId"><dt>运行 ID</dt><dd>{{ generationRunId }}</dd></div>
          </dl>

          <ol ref="traceLogRef" class="generation-trace-list" aria-live="polite">
            <li v-for="event in generationTrace" :key="event.id" :class="event.status || event.event">
              <time>{{ formatTraceTime(event.receivedAt || event.time) }}</time>
              <span>{{ event.agentName || event.agentId || event.agent || '系统' }}</span>
              <p>{{ event.message || event.detail || event.stage }}</p>
            </li>
          </ol>

          <div v-if="generationError" class="generation-error" role="alert">
            <span>
              <strong>{{ generationError.message }}</strong>
              <small v-if="generationError.detail">{{ generationError.detail }}</small>
              <small v-if="generationError.code">错误码：{{ generationError.code }}</small>
            </span>
            <button type="button" :disabled="generationIsRunning" @click="retryLearningPathGeneration">
              <RotateCcw :size="15" aria-hidden="true" />
              继续生成
            </button>
          </div>
        </div>
      </aside>
      <div v-if="loading" class="map-loading" aria-live="polite">{{ loadingMessage }}</div>
    </section>
  </main>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  ArrowLeft,
  ArrowRight,
  BookOpen,
  CheckCircle2,
  ChevronDown,
  ChevronUp,
  CircleAlert,
  LockKeyhole,
  RefreshCcw,
  RotateCcw,
  SquareTerminal,
  UserRoundCheck,
  X,
} from 'lucide-vue-next'
import { getLearningPathConfig, getLearningPathStage, getLearningProfiles } from '../services/api.js'
import LearningPathAcademyNode from '../components/LearningPathAcademyNode.vue'
import { cloneLearningPathConfig } from '../config/learningPathDefaults.js'
import {
  generateFirstLearningPath,
  generateRemainingLearningPath,
  subscribeLearningPathProgress,
  subscribeLearningPathTrace,
} from '../services/progressiveLearningPath.js'
import {
  appendNodeCacheParams,
  getNodeCache,
  hydrateNodeCachesFromServer,
  markNodeCacheComplete,
  markNodeCacheStarted,
} from '../services/learningPathNodeCache.js'

const route = useRoute()
const router = useRouter()
const removedStageIds = new Set(['profile-diagnosis'])
const firstVisibleStageId = 'week-1-embedded-foundation'
const weekOverviewStageId = 'overview'
const legacyStageAliases = {
  'courseware-recommend': firstVisibleStageId,
}
const staticWeekOneStageIds = new Set([firstVisibleStageId])
const staticWeekOneNodes = [
  {
    id: '01',
    cacheKey: 'week1-tcm-foundation-video',
    resourceType: 'video',
    label: '01',
    title: '中医基础理论视频',
    statusText: '可进入',
    description: '调用视频查找工具，检索阴阳五行、藏象学说与气血津液相关入门课程。',
    state: 'current',
    x: 112,
    y: 420,
    popX: 190,
    popY: 250,
    actionText: '查找视频',
    actionRoute: '/personalized-resources/video-search?keyword=%E4%B8%AD%E5%8C%BB%E5%9F%BA%E7%A1%80%E7%90%86%E8%AE%BA&topic=%E9%98%B4%E9%98%B3%E4%BA%94%E8%A1%8C%E4%B8%8E%E8%97%8F%E8%B1%A1',
    order: 1,
  },
  {
    id: '02',
    cacheKey: 'week1-tcm-pattern-ppt',
    resourceType: 'ppt',
    label: '02',
    title: '八纲辨证 PPT',
    statusText: '可进入',
    description: '进入 PPT 生成页面，围绕表里、寒热、虚实、阴阳梳理八纲辨证框架。',
    state: 'available',
    x: 402,
    y: 292,
    popX: 402,
    popY: 122,
    actionText: '生成 PPT',
    actionRoute: '/personalized-resources/ppt?topic=%E5%85%AB%E7%BA%B2%E8%BE%A8%E8%AF%81&prompt=%E7%94%9F%E6%88%90%E4%B8%80%E4%BB%BD%E9%9D%A2%E5%90%91%E4%B8%AD%E5%8C%BB%E5%88%9D%E5%AD%A6%E8%80%85%E7%9A%84%E5%85%AB%E7%BA%B2%E8%BE%A8%E8%AF%81PPT%EF%BC%8C%E5%8C%85%E5%90%AB%E8%A1%A8%E9%87%8C%E3%80%81%E5%AF%92%E7%83%AD%E3%80%81%E8%99%9A%E5%AE%9E%E4%B8%8E%E9%98%B4%E9%98%B3%E3%80%82&pageCount=6&autostart=1',
    order: 2,
  },
  {
    id: '03',
    cacheKey: 'week1-tcm-formula-mind-map',
    resourceType: 'mindmap',
    label: '03',
    title: '方剂配伍思维导图',
    statusText: '可进入',
    description: '进入思维导图工具，围绕君臣佐使、治法与代表方整理方剂配伍结构。',
    state: 'available',
    x: 646,
    y: 316,
    popX: 646,
    popY: 146,
    actionText: '生成导图',
    actionRoute: '/personalized-resources/mind-map?topic=%E6%96%B9%E5%89%82%E9%85%8D%E4%BC%8D%E6%80%9D%E7%BB%B4%E5%AF%BC%E5%9B%BE&keyword=%E5%90%9B%E8%87%A3%E4%BD%90%E4%BD%BF&autostart=1',
    order: 3,
  },
  {
    id: '04',
    cacheKey: 'week1-tcm-herb-question-bank',
    resourceType: 'question-bank',
    label: '04',
    title: '题库练习小测',
    statusText: '可进入',
    description: '进入题库生成页面，预填中药性味归经主题，生成一组用于自测的巩固练习。',
    state: 'available',
    x: 942,
    y: 369,
    popX: 942,
    popY: 198,
    actionText: '开始小测',
    actionRoute: '/personalized-resources/question-bank?module=generate&course=%E4%B8%AD%E8%8D%AF%E5%AD%A6&chapter=%E6%80%A7%E5%91%B3%E5%BD%92%E7%BB%8F&count=10&autostart=1',
    order: 4,
  },
  {
    id: '05',
    cacheKey: 'week1-tcm-case-document',
    resourceType: 'document',
    label: '05',
    title: '医案辨析讲义',
    statusText: '可进入',
    description: '生成一份包含四诊信息、证候判断、治法与方药思路的基础医案辨析讲义。',
    state: 'available',
    x: 1188,
    y: 284,
    popX: 1188,
    popY: 114,
    actionText: '生成讲义',
    actionRoute: '/personalized-resources/document?topic=%E5%9F%BA%E7%A1%80%E5%8C%BB%E6%A1%88%E8%BE%A8%E6%9E%90&autostart=1',
    order: 5,
  },
  {
    id: '06',
    cacheKey: 'week1-tcm-review',
    resourceType: 'review',
    label: '06',
    title: '阶段复盘',
    statusText: '可进入',
    description: '复盘前面五个节点的学习结果：视频笔记、PPT、导图、小测错题和医案讲义，整理下一步问题。',
    state: 'available',
    x: 1398,
    y: 185,
    popX: 1260,
    popY: 112,
    actionText: '整理复盘',
    actionRoute: '/personalized-resources?review=tcm-week-1',
    order: 6,
  },
]

const loading = ref(false)
const planning = ref(false)
const planningRemaining = ref(false)
const pathLoadError = ref(null)
const stageConfig = ref(getFallbackStage(normalizeStageId(String(route.params.stageId || ''))))
const pathMeta = ref({})
const activeNodeId = ref('')
const scale = ref(1)
const offset = ref({ x: 0, y: 0 })
const mapViewportRef = ref(null)
const cacheVersion = ref(0)
const compactMap = ref(typeof window !== 'undefined' && window.innerWidth <= 600)
const generationTrace = ref([])
const generationError = ref(null)
const generationConsoleExpanded = ref(true)
const profileSwitchNotice = ref('')
const activeProfileSummary = ref(null)
const profileSummaryLoading = ref(false)
const profilePathSwitching = ref(false)
const profilePathSwitchError = ref('')
const traceLogRef = ref(null)
let unsubscribeLearningPathProgress = () => {}
let unsubscribeLearningPathTrace = () => {}
let backgroundPathPollTimer = null
let profileSummaryPromise = null

const stageTitle = computed(() => stageConfig.value?.title || '学习路径')
const boardConfig = computed(() => stageConfig.value?.board || {})
const isWeekOverview = computed(() => String(route.params.stageId || '') === weekOverviewStageId)
const hasActiveLearningProfile = computed(() => Number(activeProfileSummary.value?.id || 0) > 0)
const backgroundPathGeneration = computed(() => (
  pathMeta.value?.backgroundGeneration && typeof pathMeta.value.backgroundGeneration === 'object'
    ? pathMeta.value.backgroundGeneration
    : {}
))
const backgroundPathIsRunning = computed(() => (
  ['queued', 'running'].includes(String(backgroundPathGeneration.value.status || ''))
))
const generationIsRunning = computed(() => (
  planning.value || planningRemaining.value || backgroundPathIsRunning.value
))
const activeProfilePathTitle = computed(() => {
  if (profileSummaryLoading.value) return '正在读取当前画像'
  return String(activeProfileSummary.value?.profileName || activeProfileSummary.value?.name || '尚未选择画像')
})
const activeProfilePathMatches = computed(() => {
  const profileId = Number(activeProfileSummary.value?.id || 0)
  const pathProfileId = Number(pathMeta.value?.profileReportId || 0)
  return profileId > 0
    && pathProfileId === profileId
    && Array.isArray(stageConfig.value?.nodes)
    && stageConfig.value.nodes.length > 0
    && pathMeta.value?.profileSwitchPending !== true
})
const activeProfilePathStatus = computed(() => {
  if (profileSummaryLoading.value) return '正在核对画像与已保存路径'
  if (!activeProfileSummary.value?.id) return '请先在学习画像中选择当前画像'
  if (profilePathSwitching.value) return '正在核对当前画像与已保存路径'
  if (activeProfilePathMatches.value) return '已是当前画像路径，点击只读取保存结果'
  return '点击后切换为当前画像对应的学习路径'
})
const profilePathSwitchButtonLabel = computed(() => {
  if (profilePathSwitching.value) return '正在检查路径'
  return activeProfilePathMatches.value ? '加载已保存路径' : '切换到当前画像路径'
})
const generationConsoleVisible = computed(() => (
  isWeekOverview.value
  && (generationIsRunning.value || Boolean(generationError.value) || generationTrace.value.length > 0)
))
const latestGenerationEvent = computed(() => (
  [...generationTrace.value].reverse().find((event) => event?.message || event?.stage) || {}
))
const latestProgressEvent = computed(() => (
  [...generationTrace.value].reverse().find((event) => Number.isFinite(Number(event?.progress))) || {}
))
const generationProgress = computed(() => {
  const progress = Number(latestProgressEvent.value?.progress)
  if (Number.isFinite(progress)) return Math.max(0, Math.min(100, Math.round(progress)))
  const backgroundProgress = Number(backgroundPathGeneration.value.progress)
  return Number.isFinite(backgroundProgress)
    ? Math.max(0, Math.min(100, Math.round(backgroundProgress)))
    : 0
})
const generationConsoleState = computed(() => (
  generationError.value ? 'failed' : generationIsRunning.value ? 'running' : 'complete'
))
const generationConsoleTitle = computed(() => {
  if (generationError.value) return '学习路径生成失败'
  if (generationIsRunning.value) return latestGenerationEvent.value?.message || '岐小智正在生成学习路径'
  return '学习路径生成完成'
})
const generationConsoleSubtitle = computed(() => {
  const event = latestGenerationEvent.value
  if (!event.stage && backgroundPathIsRunning.value) {
    const completed = Number(backgroundPathGeneration.value.completedWeeks || 0)
    const total = Number(backgroundPathGeneration.value.totalWeeks || 6)
    return `后台规划任务 · 已保存 ${completed} / ${total} 周`
  }
  const agent = event.agentName || event.agentId || event.agent || '岐小智'
  return `${agent} · ${formatGenerationStage(event.stage)}`
})
const generationAgent = computed(() => {
  const event = [...generationTrace.value].reverse().find((item) => item?.agentName || item?.agentId || item?.agent) || {}
  const name = event.agentName || event.agent || event.agentId || '岐小智'
  const id = event.agentId && event.agentId !== name ? ` (${event.agentId})` : ''
  return `${name}${id}`
})
const generationStage = computed(() => formatGenerationStage(latestGenerationEvent.value?.stage))
const generationAttempt = computed(() => {
  const event = [...generationTrace.value].reverse().find((item) => (
    Number(item?.attempt || item?.payload?.attempt || item?.payload?.payload?.attempt) > 0
  )) || {}
  return Number(event.attempt || event.payload?.attempt || event.payload?.payload?.attempt) || 1
})
const generationRunId = computed(() => {
  const event = [...generationTrace.value].reverse().find((item) => item?.runId)
  return String(event?.runId || '')
})
const generationReview = computed(() => {
  const event = [...generationTrace.value].reverse().find((item) => item?.stage === 'quality_review')
  if (!event) return generationIsRunning.value ? '等待审核' : generationError.value ? '未通过' : '已通过'
  const score = Number(event.payload?.score)
  const status = event.status === 'complete' ? '已通过' : '需修订'
  return Number.isFinite(score) ? `${status} · ${score} 分` : status
})
const loadingMessage = computed(() => (
  backgroundPathIsRunning.value
    ? backgroundPathGeneration.value.message || '学习路径正在后台生成'
    : planning.value
      ? '正在根据当前学习画像生成第一周学习计划'
      : '正在加载学习路径'
))

const academyMapTitles = [
  '本草基原与药用部位',
  '药材性状观察与记录',
  '真伪药材对比鉴别',
  '显微与理化鉴别进阶',
  '炮制品与易混品辨析',
  '综合中药鉴别实践',
]

const sortedNodes = computed(() => {
  cacheVersion.value
  const nodes = Array.isArray(stageConfig.value?.nodes) ? stageConfig.value.nodes : []
  const visibleNodes = nodes.filter((node) => {
      const type = String(node?.resourceType || '').toLowerCase()
      const routePath = String(node?.actionRoute || '').toLowerCase()
      return !['mcu', 'simulator'].includes(type) && !routePath.includes('mcu-simulator')
    })
  const lastIndex = Math.max(visibleNodes.length - 1, 1)
  return visibleNodes
    .map((node, index) => {
      const cacheKey = String(node.cacheKey || '').trim()
      const cache = getNodeCache(cacheKey)
      const cacheDone = cache?.status === 'complete'
      const compactCoords = compactMap.value && isWeekOverview.value
        ? {
            x: index % 2 === 0 ? 82 : 278,
            y: 292 + Math.floor(index / 2) * 164,
          }
        : null
      const academyStage = Math.min(6, Math.max(1, Math.round(1 + (index / lastIndex) * 5)))
      return {
        id: String(node.id || node.label || index + 1),
        cacheKey,
        resourceType: String(node.resourceType || ''),
        label: String(node.label || String(index + 1).padStart(2, '0')),
        title: String(node.title || '学习节点'),
        statusText: cacheDone ? '已保存' : String(node.statusText || ''),
        description: String(node.description || node.desc || ''),
        state: cacheDone ? 'done' : normalizeNodeState(node.state),
        x: compactCoords?.x ?? safeNumber(node.x, 120 + index * 180),
        y: compactCoords?.y ?? safeNumber(node.y, 320),
        popX: compactCoords?.x ?? safeNumber(node.popX, node.x ?? 120 + index * 180),
        popY: compactCoords?.y ?? safeNumber(node.popY, Math.max(88, safeNumber(node.y, 320) - 170)),
        actionText: cacheDone ? '继续查看' : String(node.actionText || '进入关卡'),
        actionRoute: String(node.actionRoute || ''),
        stageId: String(node.stageId || ''),
        order: safeNumber(node.order, index + 1),
        academyGrowth: index / lastIndex,
        academyStage,
        mapTitle: academyMapTitles[academyStage - 1],
      }
    })
    .sort((left, right) => left.order - right.order)
    .map((node, academyEnterIndex) => ({ ...node, academyEnterIndex }))
})

const boardSize = computed(() => {
  if (compactMap.value && isWeekOverview.value) {
    const maxNodeY = Math.max(...sortedNodes.value.map((node) => node.y), 0)
    return { width: 360, height: Math.max(720, maxNodeY + 170) }
  }
  const configuredWidth = safeNumber(boardConfig.value.width, 1440)
  const configuredHeight = safeNumber(boardConfig.value.height, 640)
  const maxNodeX = Math.max(...sortedNodes.value.map((node) => node.x), 0)
  const maxNodeY = Math.max(...sortedNodes.value.map((node) => node.y), 0)
  return {
    width: Math.max(configuredWidth, maxNodeX + 80),
    height: Math.max(configuredHeight, maxNodeY + 120),
  }
})

const activeNode = computed(() => {
  if (!sortedNodes.value.length) return null
  if (!activeNodeId.value) return null
  return sortedNodes.value.find((node) => node.id === activeNodeId.value) || null
})

const fullRoutePath = computed(() => createRoutePath(sortedNodes.value))
const completedRoutePath = computed(() => createRoutePath(completedRouteNodes.value))

const completedRouteNodes = computed(() => {
  const result = []
  for (const node of sortedNodes.value) {
    if (node.state !== 'done' && node.state !== 'current') break
    result.push(node)
    if (node.state === 'current') break
  }
  return result
})

const stageMetrics = computed(() => {
  const total = sortedNodes.value.length
  const done = sortedNodes.value.filter((node) => node.state === 'done').length
  const current = sortedNodes.value.filter((node) => node.state === 'current').length
  return { total, done, current }
})

const stageProgressPercent = computed(() => {
  const total = stageMetrics.value.total || 1
  const weightedDone = stageMetrics.value.done + stageMetrics.value.current * 0.5
  return Math.min(100, Math.round((weightedDone / total) * 100))
})

const popoverStyle = computed(() => {
  if (!activeNode.value) return {}
  if (compactMap.value && isWeekOverview.value) {
    return { left: '180px', top: '104px' }
  }
  const left = activeNode.value.x
  const top = activeNode.value.y - (isWeekOverview.value ? 112 : 70)
  return { left: `${left}px`, top: `${top}px` }
})

const boardStyle = computed(() => ({
  width: `${boardSize.value.width}px`,
  height: `${boardSize.value.height}px`,
  transform: `translate(${offset.value.x}px, ${offset.value.y}px) scale(${scale.value})`,
}))

const compactViewportStyle = computed(() => (
  compactMap.value && isWeekOverview.value
    ? { height: `${boardSize.value.height + 280}px` }
    : undefined
))

onMounted(() => {
  window.addEventListener('resize', resetViewport)
  window.addEventListener('storage', handleNodeCacheUpdated)
  window.addEventListener('learning-path-node-cache-updated', handleNodeCacheUpdated)
  unsubscribeLearningPathProgress = subscribeLearningPathProgress(handleLearningPathProgress)
  unsubscribeLearningPathTrace = subscribeLearningPathTrace(handleLearningPathTrace)
  consumeProfileSwitchNotice()
  hydrateNodeCachesFromServer()
  nextTick(resetViewport)
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', resetViewport)
  window.removeEventListener('storage', handleNodeCacheUpdated)
  window.removeEventListener('learning-path-node-cache-updated', handleNodeCacheUpdated)
  unsubscribeLearningPathProgress()
  unsubscribeLearningPathTrace()
  stopBackgroundPathPolling()
})

watch(
  () => route.params.stageId,
  (stageId) => {
    const normalizedStageId = normalizeStageId(String(stageId || ''))
    if (normalizedStageId !== String(stageId || '')) {
      router.replace({ name: 'learning-path-stage-detail', params: { stageId: normalizedStageId }, query: route.query })
      return
    }
    loadStage(normalizedStageId)
  },
  { immediate: true },
)

async function loadStage(stageId) {
  const fallbackStage = stageId === weekOverviewStageId
    ? createWeekOverviewStage(cloneLearningPathConfig())
    : applyStaticStageOverride(getFallbackStage(stageId), stageId)
  if (fallbackStage && (!stageConfig.value?.nodes?.length || String(stageConfig.value?.id || '') !== String(fallbackStage.id || ''))) {
    stageConfig.value = fallbackStage
  }
  loading.value = !Array.isArray(stageConfig.value?.nodes) || stageConfig.value.nodes.length === 0
  planning.value = false
  planningRemaining.value = false
  pathLoadError.value = null
  generationError.value = null
  stopBackgroundPathPolling()
  try {
    if (stageId === weekOverviewStageId) {
      await loadWeekOverview()
      return
    }
    const [profileResult, stageResult] = await Promise.allSettled([
      loadActiveProfileSummary({ throwOnError: true }),
      getLearningPathStage(stageId),
    ])
    if (stageResult.status === 'fulfilled') {
      const payload = stageResult.value
      pathMeta.value = payload?.meta || payload?.config?.meta || pathMeta.value
      stageConfig.value = applyStaticStageOverride(normalizeStage(payload?.stage || payload, stageId), stageId)
    }
    if (profileResult.status === 'rejected') throw profileResult.reason
    if (stageResult.status === 'rejected') throw stageResult.reason
    const activeProfile = profileResult.value
    if (!activeProfile?.id) {
      pathMeta.value = { activeProfileReportId: null, canGeneratePersonalized: false }
      stageConfig.value = { id: stageId, title: '学习路径', nodes: [], board: {} }
      return
    }
  } catch (error) {
    console.warn('Failed to load learning path stage.', error)
    setPathLoadFailure(
      error,
      stageId === weekOverviewStageId ? '学习路径配置加载失败，请稍后重试。' : '本周学习任务加载失败，请稍后重试。',
    )
  } finally {
    activeNodeId.value = ''
    loading.value = false
    await nextTick()
    resetViewport()
  }
}

async function loadWeekOverview() {
  let config = normalizePathConfig(await getLearningPathConfig())
  pathMeta.value = config.meta || {}
  applyActiveProfileSummary(config)
  if (!hasActiveLearningProfile.value && Number(config?.meta?.activeProfileReportId || 0) > 0) {
    await loadActiveProfileSummary({ throwOnError: true })
  }
  if (!hasActiveLearningProfile.value) {
    stageConfig.value = { id: weekOverviewStageId, title: '学习路径', nodes: [], board: {} }
    loading.value = false
    return
  }
  const totalWeeks = Math.max(4, Math.min(8, Number(config?.meta?.totalWeeks) || 6))
  stageConfig.value = createWeekOverviewStage(config)

  if (isBackgroundPathPending(config)) {
    loading.value = false
    scheduleBackgroundPathPolling()
    await nextTick()
    resetViewport()
    return
  }
  stopBackgroundPathPolling()

  if (shouldAutoPlan(config)) {
    planning.value = true
    try {
      config = normalizePathConfig(await generateFirstLearningPath(totalWeeks, activeProfileSummary.value?.id))
      pathMeta.value = config.meta || {}
    } catch (error) {
      console.warn('Failed to generate the first learning-path week.', error)
      setGenerationFailure(error)
      stageConfig.value = createWeekOverviewStage(config)
      loading.value = false
      return
    } finally {
      planning.value = false
    }
  }

  stageConfig.value = createWeekOverviewStage(config)
  loading.value = false
  await nextTick()
  resetViewport()

  const generatedWeekCount = visiblePathWeeks(config).length
  const generationComplete = config?.meta?.generationState === 'complete' && generatedWeekCount >= totalWeeks
  if (
    config?.meta?.canGeneratePersonalized !== false
    && !generationComplete
    && generatedWeekCount < totalWeeks
    && !planningRemaining.value
  ) {
    void generateRemainingWeeks(config, totalWeeks)
  }
}

async function rebuildPersonalizedPath() {
  if (pathMeta.value?.canGeneratePersonalized === false || planning.value || planningRemaining.value) return
  planning.value = true
  try {
    const activeProfile = activeProfileSummary.value || await loadActiveProfileSummary()
    if (!activeProfile?.id) {
      throw new Error('当前没有激活画像，请先在学习画像中选择一份画像。')
    }
    let config = normalizePathConfig(await getLearningPathConfig())
    const totalWeeks = Math.max(4, Math.min(8, Number(config?.meta?.totalWeeks || pathMeta.value?.totalWeeks) || 6))
    const savedPathMatchesProfile = isSavedPathForProfile(config, activeProfile)
    if (!savedPathMatchesProfile) {
      config = normalizePathConfig(await generateFirstLearningPath(totalWeeks, activeProfile.id))
    }
    pathMeta.value = config.meta || {}
    stageConfig.value = createWeekOverviewStage(config)
    planning.value = false
    await nextTick()
    resetViewport()
    if (visiblePathWeeks(config).length < totalWeeks) {
      await generateRemainingWeeks(config, totalWeeks)
    }
  } catch (error) {
    console.warn('Failed to rebuild personalized learning path.', error)
    setGenerationFailure(error)
  } finally {
    planning.value = false
  }
}

function applyActiveProfileSummary(config) {
  const summary = config?.meta?.activeProfileSummary
  if (summary && Number(summary.id || 0) > 0) {
    activeProfileSummary.value = { ...summary, isActive: true }
  } else if (Number(config?.meta?.activeProfileReportId || 0) <= 0) {
    activeProfileSummary.value = null
  }
}

async function loadActiveProfileSummary(options = {}) {
  if (!options.force && activeProfileSummary.value?.id) return activeProfileSummary.value
  if (!options.force && profileSummaryPromise) return profileSummaryPromise
  profileSummaryLoading.value = true
  const requestPromise = (async () => {
    const data = await getLearningProfiles()
    const profiles = Array.isArray(data?.profiles) ? data.profiles : []
    const activeReportId = Number(data?.activeReportId || 0)
    activeProfileSummary.value = profiles.find((profile) => (
      profile?.isActive || Number(profile?.id || 0) === activeReportId
    )) || null
    return activeProfileSummary.value
  })()
  profileSummaryPromise = requestPromise
  try {
    return await requestPromise
  } catch (error) {
    profilePathSwitchError.value = error?.response?.data?.msg || error?.message || '当前画像读取失败'
    if (options.throwOnError) throw error
    return activeProfileSummary.value || null
  } finally {
    if (profileSummaryPromise === requestPromise) profileSummaryPromise = null
    profileSummaryLoading.value = false
  }
}

function isSavedPathForProfile(config, profile) {
  const profileId = Number(profile?.id || 0)
  const pathProfileId = Number(config?.meta?.profileReportId || 0)
  return profileId > 0
    && pathProfileId === profileId
    && Array.isArray(config?.weeks)
    && config.weeks.some((week) => week && week.enabled !== false && !week.placeholder)
    && config?.meta?.profileSwitchPending !== true
}

async function switchToCurrentProfilePath() {
  if (profilePathSwitching.value || generationIsRunning.value) return
  profilePathSwitching.value = true
  profilePathSwitchError.value = ''
  let generationStarted = false
  try {
    const activeProfile = await loadActiveProfileSummary({ force: true })
    const activeProfileId = Number(activeProfile?.id || 0)
    if (!activeProfileId) {
      throw new Error(profilePathSwitchError.value || '当前没有激活画像，请先在学习画像中选择一份画像。')
    }

    const savedConfig = normalizePathConfig(await getLearningPathConfig())
    if (isSavedPathForProfile(savedConfig, activeProfile)) {
      generationError.value = null
      activeNodeId.value = ''
      pathMeta.value = savedConfig.meta || {}
      stageConfig.value = createWeekOverviewStage(savedConfig)
      const profileName = String(activeProfile.profileName || activeProfile.name || '当前画像').trim()
      const version = Number(activeProfile.version || 0)
      profileSwitchNotice.value = version > 0
        ? `当前已是 ${profileName} v${version} 的学习路径，已读取数据库保存结果。`
        : `当前已是 ${profileName} 的学习路径，已读取数据库保存结果。`
      await nextTick()
      resetViewport()
      return
    }

    generationStarted = true
    planning.value = true
    generationError.value = null
    activeNodeId.value = ''
    const totalWeeks = Math.max(4, Math.min(8, Number(pathMeta.value?.totalWeeks) || 6))
    let config = normalizePathConfig(await generateFirstLearningPath(totalWeeks, activeProfileId))
    pathMeta.value = config.meta || {}
    stageConfig.value = createWeekOverviewStage(config)
    planning.value = false
    await nextTick()
    resetViewport()

    if (visiblePathWeeks(config).length < totalWeeks) {
      planningRemaining.value = true
      config = normalizePathConfig(await generateRemainingLearningPath(config, totalWeeks))
      pathMeta.value = config.meta || {}
      stageConfig.value = createWeekOverviewStage(config)
    }

    const persistedConfig = normalizePathConfig(await getLearningPathConfig())
    if (!isSavedPathForProfile(persistedConfig, activeProfile)) {
      throw new Error('已保存路径与当前画像不一致，请重试切换。')
    }
    pathMeta.value = persistedConfig.meta || {}
    stageConfig.value = createWeekOverviewStage(persistedConfig)
    const profileName = String(activeProfile.profileName || activeProfile.name || '当前画像').trim()
    const version = Number(activeProfile.version || 0)
    profileSwitchNotice.value = version > 0
      ? `已根据 ${profileName} v${version} 生成并保存当前学习路径。`
      : `已根据 ${profileName} 生成并保存当前学习路径。`
    await nextTick()
    resetViewport()
  } catch (error) {
    profilePathSwitchError.value = error?.response?.data?.msg || error?.message || '当前画像路径切换失败'
    if (generationStarted) setGenerationFailure(error)
  } finally {
    planning.value = false
    planningRemaining.value = false
    profilePathSwitching.value = false
  }
}

function handlePersonalizationAction() {
  router.push('/learning-profile')
}

function consumeProfileSwitchNotice() {
  try {
    const raw = window.localStorage.getItem('learning-profile-switched')
    if (!raw) return
    window.localStorage.removeItem('learning-profile-switched')
    const event = JSON.parse(raw)
    const profileName = String(event?.profileName || '当前画像').trim()
    const version = Number(event?.version || 0)
    profileSwitchNotice.value = version > 0
      ? `已根据 ${profileName} v${version} 切换当前学习路径任务。`
      : `已根据 ${profileName} 切换当前学习路径任务。`
  } catch {
    window.localStorage.removeItem('learning-profile-switched')
    profileSwitchNotice.value = '已根据当前学习画像切换学习路径任务。'
  }
}

async function generateRemainingWeeks(initialConfig, totalWeeks) {
  planningRemaining.value = true
  try {
    const finalConfig = await generateRemainingLearningPath(initialConfig, totalWeeks)
    await handleLearningPathProgress(finalConfig)
  } catch (error) {
    console.warn('Failed to generate remaining learning-path weeks.', error)
    setGenerationFailure(error)
  } finally {
    planningRemaining.value = false
  }
}

async function handleLearningPathProgress(config) {
  if (!isWeekOverview.value || !config) return
  const normalized = normalizePathConfig(config)
  pathMeta.value = normalized.meta || {}
  stageConfig.value = createWeekOverviewStage(normalized)
  await nextTick()
  resetViewport()
}

function handleLearningPathTrace(event, history = []) {
  if (event?.event === 'reset') {
    generationTrace.value = []
    generationError.value = null
    generationConsoleExpanded.value = true
    return
  }
  generationTrace.value = Array.isArray(history) && history.length
    ? history
    : [...generationTrace.value, event].filter(Boolean).slice(-160)
  if (event?.event === 'error') {
    generationError.value = {
      code: String(event.errorCode || ''),
      message: String(event.message || event.detail || '学习路径生成失败'),
      detail: String(event.detail || ''),
    }
    generationConsoleExpanded.value = true
  }
  nextTick(() => {
    if (traceLogRef.value) {
      traceLogRef.value.scrollTop = traceLogRef.value.scrollHeight
    }
  })
}

function setGenerationFailure(error) {
  const code = String(error?.code || error?.details?.errorCode || 'LEARNING_PATH_GENERATION_FAILED')
  const rawMessage = String(error?.message || '学习路径生成失败，请查看详细输出后重试。')
  const networkInterrupted = code === 'LEARNING_PATH_STREAM_INTERRUPTED'
    || /failed to fetch|networkerror|network error|load failed/i.test(rawMessage)
  generationError.value = {
    code,
    message: networkInterrupted
      ? '生成连接暂时中断，已保存周次不会丢失。点击“继续生成”将从数据库进度补全。'
      : rawMessage,
    detail: String(error?.details?.detail || ''),
  }
  generationConsoleExpanded.value = true
}

function setPathLoadFailure(error, fallbackMessage) {
  pathLoadError.value = {
    message: String(
      error?.response?.data?.msg
      || error?.response?.data?.message
      || error?.details?.msg
      || error?.message
      || fallbackMessage,
    ),
  }
  planning.value = false
  planningRemaining.value = false
  stopBackgroundPathPolling()
}

function retryLearningPathLoad() {
  const stageId = normalizeStageId(String(route.params.stageId || weekOverviewStageId))
  void loadStage(stageId)
}

async function retryLearningPathGeneration() {
  if (generationIsRunning.value) return
  generationError.value = null
  loading.value = true
  try {
    if (pathMeta.value?.canGeneratePersonalized !== false) {
      await rebuildPersonalizedPath()
    } else {
      await loadWeekOverview()
    }
  } catch (error) {
    setGenerationFailure(error)
  } finally {
    planning.value = false
    planningRemaining.value = false
    loading.value = false
  }
}

function formatGenerationStage(stage) {
  const labels = {
    frontend_request: '准备请求',
    request_start: '总控接单',
    supervisor_plan: '任务规划',
    load_context: '读取画像与学习证据',
    retrieve_knowledge: '检索课程知识库',
    specialist_start: '学习路径智能体生成',
    skill_resolved: 'Skill 解析',
    skill_input_validated: '输入契约校验',
    mcp_tool_start: 'MCP 工具调用',
    mcp_tool_complete: 'MCP 工具完成',
    skill_output_validated: '输出契约校验',
    recover_saved_progress: '恢复保存进度',
    saved_progress_recovered: '保存进度已恢复',
    specialist_complete: '结构化产物提交',
    quality_review: '质量审核',
    content_safety: '内容安全审核',
    learning_feedback: '学习反馈整理',
    supervisor_finalize: '总控结果收口',
    next_week_request: '下一周生成',
    complete: '结果保存',
    all_weeks_complete: '全部周次完成',
    done: '请求结束',
    request_error: '请求失败',
    error: '生成失败',
  }
  return labels[String(stage || '')] || String(stage || '等待执行')
}

function formatTraceTime(value) {
  const date = new Date(value || Date.now())
  if (Number.isNaN(date.getTime())) return '--:--:--'
  return date.toLocaleTimeString('zh-CN', { hour12: false })
}

function normalizePathConfig(config) {
  const fallback = cloneLearningPathConfig()
  if (!config || typeof config !== 'object') return fallback
  return {
    ...fallback,
    ...config,
    meta: {
      ...(fallback.meta || {}),
      ...(config.meta || {}),
    },
    weeks: Array.isArray(config.weeks) ? config.weeks : [],
    stages: config.stages && typeof config.stages === 'object' ? config.stages : {},
  }
}

function visiblePathWeeks(config) {
  return (Array.isArray(config?.weeks) ? config.weeks : [])
    .filter((week) => week && week.enabled !== false && !week.placeholder && !removedStageIds.has(String(week.id || '')))
}

function shouldAutoPlan(config) {
  if (config?.meta?.canGeneratePersonalized === false) return false
  if (isBackgroundPathPending(config)) return false
  if (Number(config?.version || 1) < 2) return true
  const visibleWeeks = visiblePathWeeks(config)
  if (!visibleWeeks.length) return true
  return false
}

function isBackgroundPathPending(config) {
  return ['queued', 'running'].includes(String(config?.meta?.backgroundGeneration?.status || ''))
}

function stopBackgroundPathPolling() {
  if (backgroundPathPollTimer) {
    window.clearTimeout(backgroundPathPollTimer)
    backgroundPathPollTimer = null
  }
}

function scheduleBackgroundPathPolling() {
  if (backgroundPathPollTimer || !isWeekOverview.value) return
  backgroundPathPollTimer = window.setTimeout(() => {
    backgroundPathPollTimer = null
    if (isWeekOverview.value) void loadStage(weekOverviewStageId)
  }, 1500)
}

function createWeekOverviewStage(config) {
  const visibleWeeks = visiblePathWeeks(config)
    .sort((left, right) => safeNumber(left.order, 0) - safeNumber(right.order, 0))
  const weekLabels = ['一', '二', '三', '四', '五', '六', '七', '八', '九', '十', '十一', '十二']
  const nodes = visibleWeeks.map((week, index) => {
    const status = String(week.status || '')
    const state = ['done', 'completed'].includes(status)
      ? 'done'
      : ['current', 'active', 'progress'].includes(status)
        ? 'current'
        : 'available'
    const weekNumber = index + 1
    return {
      id: `week-${weekNumber}`,
      resourceType: 'week',
      stageId: String(week.id || `week-${weekNumber}`),
      label: `第${weekLabels[index] || weekNumber}周`,
      title: cleanWeekMapTitle(week.title, weekNumber),
      statusText: state === 'done' ? '已完成' : state === 'current' ? '进行中' : '未开始',
      description: String(week.description || `查看第${weekNumber}周的具体学习任务与资源。`),
      state,
      x: 126 + index * 246,
      y: index % 2 === 0 ? 388 : 254,
      actionText: '查看本周任务',
      actionRoute: `/learning-path/week/${encodeURIComponent(String(week.id || `week-${weekNumber}`))}`,
      order: weekNumber,
    }
  })
  return {
    id: weekOverviewStageId,
    title: '个性化周学习计划',
    hint: '选择周次后查看该周的具体学习任务与资源。',
    board: {
      width: Math.max(1440, 160 + nodes.length * 246),
      height: 640,
      initialScale: 1,
      minScale: 0.68,
      maxScale: 1.42,
    },
    nodes,
  }
}

function cleanWeekMapTitle(value, weekNumber) {
  const title = String(value || '').trim()
    .replace(/^第(?:[一二三四五六七八九十百]+|\d+)周\s*[：:\-]?\s*/, '')
  return title || `第${weekNumber}周学习任务`
}

function normalizeStage(stage, stageId) {
  if (!stage || typeof stage !== 'object') {
    return getFallbackStage(stageId)
  }
  const fallback = getFallbackStage(stageId) || {
    id: stageId,
    weekLabel: '当前周',
    title: '学习任务与资源',
    hint: '点击任务查看对应资源',
    board: { width: 1440, height: 640, initialScale: 1, minScale: 0.68, maxScale: 1.42 },
    nodes: [],
  }
  return {
    ...fallback,
    ...stage,
    board: {
      ...fallback.board,
      ...(stage.board || {}),
    },
    nodes: Array.isArray(stage.nodes) && stage.nodes.length ? stage.nodes : fallback.nodes,
  }
}

function getFallbackStage(stageId) {
  const config = cloneLearningPathConfig()
  const firstVisibleStage = config.stages[firstVisibleStageId]
    || Object.values(config.stages).find((stage) => stage && !removedStageIds.has(String(stage.id || '')))
  const fallbackStage = config.stages[stageId] || firstVisibleStage || Object.values(config.stages)[0]
  return applyStaticStageOverride(fallbackStage, normalizeStageId(stageId))
}

function normalizeStageId(stageId) {
  if (removedStageIds.has(stageId)) return firstVisibleStageId
  return legacyStageAliases[stageId] || stageId
}

function normalizeNodeState(state) {
  return ['done', 'current', 'available', 'locked'].includes(state) ? state : 'locked'
}

function safeNumber(value, fallback) {
  const number = Number(value)
  return Number.isFinite(number) ? number : Number(fallback)
}

function clamp(value, min, max) {
  return Math.min(max, Math.max(min, safeNumber(value, min)))
}

function createRoutePath(nodes) {
  if (!Array.isArray(nodes) || nodes.length < 2) return ''
  const [firstNode, ...restNodes] = nodes
  return restNodes.reduce((path, node, index) => {
    const previous = index === 0 ? firstNode : restNodes[index - 1]
    // Rounded orthogonal turns read as a route on a learning map, rather than a chart curve.
    const horizontalGap = Math.abs(node.x - previous.x)
    const turn = Math.max(28, Math.min(64, horizontalGap * 0.22))
    const direction = node.x >= previous.x ? 1 : -1
    const turnStartX = previous.x + direction * turn
    const turnEndX = node.x - direction * turn
    const radius = Math.min(24, Math.abs(node.y - previous.y) / 2)
    const verticalDirection = node.y >= previous.y ? 1 : -1
    return `${path} L ${turnStartX} ${previous.y} Q ${turnStartX + direction * radius} ${previous.y} ${turnStartX + direction * radius} ${previous.y + verticalDirection * radius} L ${turnEndX - direction * radius} ${node.y - verticalDirection * radius} Q ${turnEndX} ${node.y} ${turnEndX + direction * radius} ${node.y} L ${node.x} ${node.y}`
  }, `M ${firstNode.x} ${firstNode.y}`)
}

function selectNode(node) {
  if (isWeekOverview.value && node?.resourceType === 'week' && node.stageId && node.state !== 'locked') {
    router.push({ name: 'learning-path-week-detail', params: { stageId: node.stageId } })
    return
  }
  activeNodeId.value = node.id
}

async function openNodeAction(node) {
  if (!node?.actionRoute || node.state === 'locked') return
  if (node.resourceType === 'week' && node.stageId) {
    router.push({ name: 'learning-path-week-detail', params: { stageId: node.stageId } })
    return
  }
  await hydrateNodeCachesFromServer()
  const href = buildNodeActionHref(node)
  if (node.cacheKey) {
    const marker = node.resourceType === 'review' ? markNodeCacheComplete : markNodeCacheStarted
    marker(node.cacheKey, {
      stageId: normalizeStageId(String(route.params.stageId || firstVisibleStageId)),
      nodeId: node.id,
      resourceType: node.resourceType,
      title: node.title,
      route: href,
    })
  }
  window.open(href, '_blank', 'noopener,noreferrer')
}

function buildNodeActionHref(node) {
  const cache = getNodeCache(node.cacheKey)
  const cachedStatus = String(cache?.status || '')
  let shouldRestoreCachedResult = cachedStatus === 'complete' || cachedStatus === 'running'
  if (node.resourceType === 'question-bank' && cachedStatus === 'running' && !cache?.taskId) {
    shouldRestoreCachedResult = false
  }
  if (node.resourceType === 'video' && cachedStatus === 'running' && !cache?.fetchCache) {
    shouldRestoreCachedResult = false
  }
  const baseRoute = /^https?:\/\//i.test(node.actionRoute)
    ? node.actionRoute
    : router.resolve(node.actionRoute).href
  const routeWithCache = appendNodeCacheParams(baseRoute, {
    source: 'learning-path',
    stageId: normalizeStageId(String(route.params.stageId || firstVisibleStageId)),
    nodeId: node.id,
    cacheKey: node.cacheKey,
    restore: shouldRestoreCachedResult ? '1' : '',
  })
  const url = new URL(routeWithCache, window.location.origin)
  if (shouldRestoreCachedResult) {
    url.searchParams.delete('autostart')
  }
  if (node.resourceType === 'question-bank' && shouldRestoreCachedResult && cache?.sheetId) {
    url.searchParams.set('module', 'history')
  }
  if (node.resourceType === 'ppt' && shouldRestoreCachedResult && cache?.sessionId) {
    url.searchParams.set('session', cache.sessionId)
    url.searchParams.set('tab', 'history')
  }
  return `${url.pathname}${url.search}${url.hash}`
}

function handleNodeCacheUpdated(event) {
  if (event?.key && event.key !== 'qianzhi-learning-path-node-results:v1') return
  cacheVersion.value += 1
}

function exitStage() {
  router.push({ name: 'learning-path' })
}

function nodeProgress(node) {
  if (!node) return 0
  if (node.state === 'done') return 100
  if (node.state === 'current') return 66
  return 0
}

function applyStaticStageOverride(stage, stageId) {
  return stage
}

function resetViewport() {
  const viewport = mapViewportRef.value
  if (!viewport) return
  const rect = viewport.getBoundingClientRect()
  compactMap.value = rect.width <= 600
  const horizontalPadding = rect.width < 900 ? 28 : 72
  const verticalPadding = rect.height < 700 ? 28 : 52
  if (compactMap.value && isWeekOverview.value) {
    const configuredScale = clamp(boardConfig.value.initialScale, 0.35, 2.5)
    scale.value = clamp(
      Math.min(configuredScale, (rect.width - horizontalPadding) / boardSize.value.width),
      0.35,
      2.5,
    )
    offset.value = {
      x: Math.round((rect.width - boardSize.value.width * scale.value) / 2),
      y: 140,
    }
    return
  }
  const fitScale = Math.min(
    (rect.width - horizontalPadding) / boardSize.value.width,
    (rect.height - verticalPadding) / boardSize.value.height,
  )
  const configuredScale = clamp(boardConfig.value.initialScale, 0.35, 2.5)
  scale.value = clamp(Math.min(configuredScale, fitScale), 0.35, 2.5)
  offset.value = {
    x: Math.round((rect.width - boardSize.value.width * scale.value) / 2),
    y: Math.round((rect.height - boardSize.value.height * scale.value) / 2),
  }
}
</script>

<style scoped>
.clean-map-page {
  height: calc(100vh - 72px);
  min-height: 620px;
  overflow: hidden;
  color: #172033;
  background:
    linear-gradient(180deg, rgba(248, 251, 253, 0.04), rgba(242, 243, 245, 0.12)),
    url("/learning-path-academy-background-v1.png") center center / cover no-repeat,
    #f2f3f5;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC", "Microsoft YaHei", sans-serif;
}

.clean-map-viewport {
  position: relative;
  height: 100%;
  overflow: hidden;
  background: #f2f3f5;
  cursor: default;
  isolation: isolate;
  touch-action: auto;
}

.clean-map-viewport::before {
  position: absolute;
  inset: 0;
  z-index: 0;
  background:
    linear-gradient(180deg, rgba(248, 251, 253, 0.04), rgba(242, 243, 245, 0.12)),
    url("/learning-path-academy-background-v1.png") center center / cover no-repeat,
    #f2f3f5;
  content: "";
  pointer-events: none;
}

.clean-map-viewport::after {
  position: absolute;
  inset: 0;
  z-index: 1;
  background:
    linear-gradient(90deg, rgba(148, 163, 184, 0.08) 1px, transparent 1px),
    linear-gradient(0deg, rgba(148, 163, 184, 0.08) 1px, transparent 1px);
  background-size: 72px 72px;
  content: "";
  /* The circuit illustration already provides the map texture. */
  opacity: 0;
  pointer-events: none;
}

.stage-exit-button {
  position: absolute;
  z-index: 9;
  top: 28px;
  right: 28px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  min-height: 40px;
  padding: 0 16px !important;
  border: 1px solid rgba(215, 230, 226, 0.9) !important;
  border-radius: 999px !important;
  color: #2f5564 !important;
  background: rgba(255, 255, 255, 0.88) !important;
  box-shadow: 0 12px 28px rgba(15, 23, 42, 0.08) !important;
  font-size: 13px;
  font-weight: 900;
  backdrop-filter: blur(12px);
  transition: transform 0.18s ease, border-color 0.18s ease, color 0.18s ease, box-shadow 0.18s ease;
}

.stage-exit-button:hover {
  border-color: rgba(18, 185, 154, 0.34) !important;
  color: #0b8568 !important;
  box-shadow: 0 16px 34px rgba(15, 23, 42, 0.1) !important;
  transform: translateY(-1px);
}

.current-profile-path-switcher {
  position: absolute;
  z-index: 9;
  top: 28px;
  right: 28px;
  width: 300px;
  padding: 15px;
  border: 1px solid rgba(196, 222, 213, 0.92);
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.92);
  box-shadow: 0 16px 38px rgba(15, 23, 42, 0.09);
  backdrop-filter: blur(14px);
}

.week-overview-map .current-profile-path-switcher {
  animation: academy-path-card-right-enter 420ms cubic-bezier(0.22, 1, 0.36, 1) 35ms backwards;
}

.profile-path-switcher-head {
  display: grid;
  grid-template-columns: 34px minmax(0, 1fr) auto;
  align-items: center;
  gap: 9px;
}

.profile-path-switcher-head > span {
  width: 34px;
  height: 34px;
  display: grid;
  place-items: center;
  border-radius: 50%;
  color: #087a61;
  background: #e5f7ef;
}

.profile-path-switcher-head > div {
  min-width: 0;
  display: grid;
  gap: 2px;
}

.profile-path-switcher-head small {
  color: #73847f;
  font-size: 11px;
  font-weight: 800;
}

.profile-path-switcher-head strong {
  overflow: hidden;
  color: #173e34;
  font-size: 14px;
  font-weight: 950;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.profile-path-switcher-head em {
  padding: 3px 6px;
  border-radius: 4px;
  color: #087a61;
  background: #e9f8f1;
  font-size: 11px;
  font-style: normal;
  font-weight: 900;
}

.current-profile-path-switcher > p {
  min-height: 18px;
  margin: 10px 0;
  color: #647b74;
  font-size: 12px;
  font-weight: 700;
  line-height: 1.45;
}

.current-profile-path-switcher > p.error {
  color: #b4533d;
}

.current-profile-path-switcher > button {
  width: 100%;
  min-height: 36px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 7px;
  padding: 0 12px !important;
  border: 1px solid #087a61 !important;
  border-radius: 6px !important;
  color: #ffffff !important;
  background: #087a61 !important;
  box-shadow: none !important;
  font-size: 12px;
  font-weight: 900;
  cursor: pointer;
}

.current-profile-path-switcher > button:hover:not(:disabled) {
  background: #06664f !important;
}

.current-profile-path-switcher > button:disabled {
  cursor: wait;
  opacity: 0.56;
}

.current-profile-path-switcher .spinning {
  animation: mapGenerationSpin 0.8s linear infinite;
}

.stage-overview {
  position: absolute;
  z-index: 8;
  top: 34px;
  left: 28px;
  width: 284px;
  padding: 18px 20px;
  border: 1px solid rgba(219, 230, 238, 0.9);
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.88);
  box-shadow: 0 18px 45px rgba(15, 23, 42, 0.08);
  backdrop-filter: blur(14px);
}

.week-overview-map .stage-overview {
  animation: academy-path-card-left-enter 420ms cubic-bezier(0.22, 1, 0.36, 1) backwards;
}

@keyframes academy-path-card-left-enter {
  from {
    opacity: 0;
    transform: translate(-16px, 14px);
  }
}

@keyframes academy-path-card-right-enter {
  from {
    opacity: 0;
    transform: translate(16px, 14px);
  }
}

.stage-overview strong {
  display: block;
  margin-bottom: 14px;
  color: #0f172a;
  font-size: 17px;
  font-weight: 950;
}

.overview-body {
  display: grid;
  grid-template-columns: 98px minmax(0, 1fr);
  align-items: center;
  gap: 16px;
}

.overview-ring {
  display: grid;
  place-items: center;
  width: 88px;
  height: 88px;
  border-radius: 50%;
  background:
    radial-gradient(circle at center, #ffffff 0 58%, transparent 59%),
    conic-gradient(#14b99a 0 var(--progress), #e8eef3 var(--progress) 100%);
  box-shadow: inset 0 0 0 10px rgba(255, 255, 255, 0.72);
}

.overview-ring b {
  color: #0f9f7c;
  font-size: 21px;
  font-weight: 950;
  line-height: 1;
}

.overview-ring span {
  margin-top: -18px;
  color: #64748b;
  font-size: 11px;
  font-weight: 800;
}

.stage-overview dl {
  display: grid;
  gap: 10px;
  margin: 0;
}

.stage-overview dl div {
  display: flex;
  justify-content: space-between;
  gap: 12px;
}

.stage-overview dt,
.stage-overview dd {
  margin: 0;
  font-size: 13px;
  font-weight: 850;
}

.stage-overview dt {
  color: #6b7b8e;
}

.stage-overview dd {
  color: #1d2b3a;
  white-space: nowrap;
}

.path-basis-notice {
  position: absolute;
  z-index: 10;
  top: 28px;
  right: 28px;
  display: grid;
  grid-template-columns: auto minmax(0, 1fr) auto;
  align-items: center;
  gap: 12px;
  width: min(560px, calc(100% - 368px));
  min-height: 58px;
  padding: 10px 12px;
  border: 1px solid rgba(202, 138, 4, 0.25);
  border-radius: 8px;
  color: #854d0e;
  background: rgba(255, 251, 235, 0.94);
  box-shadow: 0 12px 28px rgba(120, 53, 15, 0.08);
  backdrop-filter: blur(12px);
}

.week-overview-map .path-basis-notice {
  top: 174px;
}

.path-basis-notice > span {
  display: grid;
  min-width: 0;
  gap: 2px;
}

.path-basis-notice strong,
.path-basis-notice small {
  overflow-wrap: anywhere;
}

.path-basis-notice strong {
  color: #713f12;
  font-size: 14px;
  font-weight: 950;
}

.path-basis-notice small {
  color: #946523;
  font-size: 12px;
  font-weight: 700;
  line-height: 1.45;
}

.path-basis-notice button,
.empty-path-state button {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  min-height: 34px;
  padding: 0 12px;
  border: 1px solid rgba(180, 83, 9, 0.24);
  border-radius: 6px;
  color: #7c2d12;
  background: #ffffff;
  font-size: 12px;
  font-weight: 900;
  white-space: nowrap;
  cursor: pointer;
}

.empty-path-state {
  position: absolute;
  z-index: 6;
  top: 50%;
  left: 50%;
  display: grid;
  justify-items: center;
  width: min(520px, calc(100% - 40px));
  gap: 10px;
  color: #64748b;
  text-align: center;
  transform: translate(-50%, -45%);
}

.empty-path-state strong {
  color: #172033;
  font-size: 22px;
  font-weight: 950;
}

.empty-path-state span {
  max-width: 440px;
  font-size: 14px;
  line-height: 1.7;
}

.map-board {
  position: absolute;
  z-index: 2;
  left: 0;
  top: 0;
  transform-origin: 0 0;
}

.route-layer {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  overflow: visible;
  pointer-events: none;
}

.route-layer {
  z-index: 1;
}

.route {
  fill: none;
  stroke-linecap: round;
  stroke-width: 5;
}

.route-done {
  stroke: url(#learning-route-done);
  filter: url(#learning-route-glow);
}

.route-pending {
  stroke: rgba(91, 209, 188, 0.78);
  stroke-dasharray: 12 16;
  stroke-width: 4;
}

.map-dot {
  position: absolute;
  z-index: 2;
  width: 210px;
  height: 184px;
  border: 0 !important;
  border-radius: 0 !important;
  color: #10785f !important;
  background: transparent !important;
  box-shadow: none !important;
  cursor: pointer;
  font: inherit;
  transform: translate(-50%, -50%);
  appearance: none;
  -webkit-tap-highlight-color: transparent;
}

.map-dot:hover,
.map-dot:focus,
.map-dot:focus-visible,
.map-dot[data-active="true"] {
  outline: none !important;
  background: transparent !important;
  box-shadow: none !important;
}

.clean-map-viewport .map-board button.map-dot,
.clean-map-viewport .map-board button.map-dot:hover,
.clean-map-viewport .map-board button.map-dot:focus,
.clean-map-viewport .map-board button.map-dot:focus-visible,
.clean-map-viewport .map-board button.map-dot[data-active="true"] {
  border: 0 !important;
  border-radius: 0 !important;
  color: #10785f !important;
  background: transparent !important;
  box-shadow: none !important;
}

.dot-core {
  position: absolute;
  left: 50%;
  top: 50%;
  display: grid;
  place-items: center;
  width: 66px;
  height: 66px;
  border: 5px solid rgba(255, 255, 255, 0.86);
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.88);
  box-shadow:
    0 8px 22px rgba(18, 73, 64, 0.11),
    0 0 0 8px rgba(255, 255, 255, 0.46);
  transform: translate(-50%, -50%);
  transition: transform 0.18s ease, box-shadow 0.18s ease, background 0.18s ease;
}

.dot-core span {
  color: currentColor;
  font-size: 15px;
  font-weight: 950;
  letter-spacing: 0;
  white-space: nowrap;
}

.map-dot:hover .dot-core,
.map-dot[data-active="true"] .dot-core {
  transform: translate(-50%, -50%) scale(1.08);
}

.map-dot.done .dot-core {
  color: #ffffff;
  background: linear-gradient(180deg, #6ee5c8, #18bd95);
  box-shadow:
    0 0 0 9px rgba(35, 198, 154, 0.18),
    0 12px 26px rgba(17, 143, 111, 0.2);
}

.map-dot.current .dot-core {
  color: #ffffff;
  background: linear-gradient(180deg, #63ddc2, #18b893);
  box-shadow:
    0 0 0 5px rgba(255, 255, 255, 0.9),
    0 0 0 12px rgba(34, 194, 151, 0.18),
    0 16px 34px rgba(13, 132, 102, 0.2);
}

.map-dot.locked .dot-core {
  color: #0f766e;
  background: rgba(255, 255, 255, 0.82);
  box-shadow:
    0 0 0 6px rgba(255, 255, 255, 0.7),
    0 8px 22px rgba(71, 85, 105, 0.12);
}

.dot-title,
.dot-state {
  position: absolute;
  left: 50%;
  width: 204px;
  text-align: center;
  transform: translateX(-50%);
}

.dot-title {
  top: calc(50% + 44px);
  display: -webkit-box;
  min-height: 38px;
  overflow: hidden;
  color: #24384b;
  font-size: 16px;
  font-weight: 950;
  line-height: 1.25;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
}

.dot-state {
  top: calc(50% + 91px);
  width: max-content;
  max-width: 160px;
  padding: 4px 10px;
  border-radius: 999px;
  color: #0f9f7c;
  background: rgba(231, 250, 242, 0.9);
  box-shadow: 0 6px 14px rgba(15, 23, 42, 0.06);
  font-size: 12px;
  font-weight: 850;
}

.map-dot.current .dot-state {
  color: #078465;
  background: rgba(226, 250, 241, 0.96);
}

.map-dot.locked .dot-state {
  color: #667789;
  background: rgba(255, 255, 255, 0.74);
}

.dot-mark,
.dot-lock {
  position: absolute;
  left: calc(50% + 20px);
  top: calc(50% + 15px);
  z-index: 3;
}

.dot-mark {
  color: #0bbf91;
  fill: #ffffff;
}

.dot-lock {
  color: #475569;
}

.node-popover {
  position: absolute;
  z-index: 10;
  width: 282px;
  padding: 20px;
  border: 1px solid rgba(215, 230, 226, 0.9);
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.94);
  box-shadow: 0 20px 52px rgba(15, 23, 42, 0.13);
  cursor: default;
  transform: translate(-50%, -100%);
  backdrop-filter: blur(14px);
}

.node-popover::after {
  position: absolute;
  left: 50%;
  bottom: -14px;
  width: 28px;
  height: 28px;
  border-right: 1px solid rgba(215, 230, 226, 0.9);
  border-bottom: 1px solid rgba(215, 230, 226, 0.9);
  background: rgba(255, 255, 255, 0.94);
  content: "";
  transform: translateX(-50%) rotate(45deg);
}

.popover-close {
  position: absolute;
  top: 13px;
  right: 13px;
  z-index: 2;
  display: grid;
  place-items: center;
  width: 26px;
  height: 26px;
  border: 0 !important;
  border-radius: 50% !important;
  color: #0f7a63 !important;
  background: #dbf7eb !important;
  box-shadow: none !important;
  cursor: pointer;
}

.popover-head {
  display: grid;
  grid-template-columns: 48px minmax(0, 1fr);
  align-items: start;
  gap: 14px;
  margin-right: 20px;
}

.popover-icon {
  display: grid;
  place-items: center;
  width: 44px;
  height: 44px;
  border-radius: 8px;
  color: #1d6df2;
  background: #e8f1ff;
}

.popover-icon.done {
  color: #0f9f7c;
  background: #e1f8ef;
}

.popover-icon.locked {
  color: #64748b;
  background: #edf2f7;
}

.node-popover h2 {
  margin: 0 0 8px;
  color: #172033;
  font-size: 21px;
  font-weight: 950;
  line-height: 1.25;
}

.node-status {
  display: flex;
  align-items: center;
  gap: 8px;
  margin: 0;
  color: #3f5f75;
  font-size: 13px;
  font-weight: 850;
}

.node-status span {
  width: 9px;
  height: 9px;
  border-radius: 50%;
  background: #268cff;
  box-shadow: 0 0 0 3px rgba(38, 140, 255, 0.12);
}

.node-status.done span {
  background: #12b981;
  box-shadow: 0 0 0 3px rgba(18, 185, 129, 0.12);
}

.node-status.locked span {
  background: #94a3b8;
  box-shadow: 0 0 0 3px rgba(148, 163, 184, 0.12);
}

.node-desc {
  margin: 16px 0 16px;
  color: #496074;
  font-size: 13px;
  font-weight: 650;
  line-height: 1.8;
}

.node-progress {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr) auto;
  align-items: center;
  gap: 10px;
  margin-bottom: 16px;
  color: #475569;
  font-size: 12px;
  font-weight: 850;
}

.node-progress i {
  display: block;
  height: 7px;
  overflow: hidden;
  border-radius: 999px;
  background: #e5edf4;
}

.node-progress b {
  display: block;
  height: 100%;
  border-radius: inherit;
  background: linear-gradient(90deg, #15bea0, #2f8cff);
}

.node-progress em {
  color: #1d6df2;
  font-style: normal;
}

.enter-button {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  min-height: 38px;
  padding: 0 18px !important;
  border: 1px solid rgba(19, 185, 133, 0.26) !important;
  border-radius: 999px !important;
  color: #0b805f !important;
  background: #ddf9eb !important;
  box-shadow: none !important;
  font-size: 13px;
  font-weight: 950;
  cursor: pointer;
}

.enter-button:disabled {
  color: #64748b !important;
  background: #edf2f7 !important;
  cursor: not-allowed;
}

.map-loading {
  position: absolute;
  left: 28px;
  z-index: 8;
  display: inline-flex;
  align-items: center;
  gap: 10px;
  padding: 11px 16px;
  border: 1px solid rgba(215, 230, 226, 0.86);
  border-radius: 999px;
  color: #3b5568;
  background: rgba(255, 255, 255, 0.86);
  box-shadow: 0 10px 22px rgba(15, 23, 42, 0.06);
  font-size: 13px;
  font-weight: 850;
  backdrop-filter: blur(12px);
}

.map-loading {
  top: 24px;
}

.map-generation-progress {
  position: absolute;
  top: 28px;
  right: 28px;
  z-index: 9;
  display: inline-flex;
  align-items: center;
  gap: 10px;
  max-width: min(440px, calc(100% - 360px));
  min-height: 42px;
  padding: 10px 14px;
  border: 1px solid rgba(18, 185, 154, 0.2);
  border-radius: 8px;
  color: #176d5b;
  background: rgba(239, 253, 248, 0.94);
  box-shadow: 0 12px 28px rgba(15, 118, 110, 0.08);
  font-size: 13px;
  font-weight: 850;
  line-height: 1.45;
  backdrop-filter: blur(12px);
}

.generation-spinner {
  flex: 0 0 auto;
  width: 15px;
  height: 15px;
  border: 2px solid rgba(18, 185, 154, 0.22);
  border-top-color: #12a982;
  border-radius: 50%;
  animation: mapGenerationSpin 0.8s linear infinite;
}

@keyframes mapGenerationSpin {
  to {
    transform: rotate(360deg);
  }
}

.generation-console {
  position: absolute;
  right: 24px;
  bottom: 24px;
  z-index: 14;
  width: min(500px, calc(100% - 48px));
  overflow: hidden;
  border: 1px solid rgba(197, 215, 225, 0.96);
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.96);
  box-shadow: 0 20px 48px rgba(15, 23, 42, 0.14);
  backdrop-filter: blur(16px);
}

.generation-console.failed {
  border-color: rgba(220, 38, 38, 0.26);
}

.generation-console-summary {
  display: grid !important;
  grid-template-columns: 34px minmax(0, 1fr) auto 18px;
  align-items: center;
  width: 100%;
  min-height: 62px;
  gap: 10px;
  padding: 10px 14px !important;
  border: 0 !important;
  border-radius: 0 !important;
  color: #253447 !important;
  background: transparent !important;
  box-shadow: none !important;
  text-align: left;
  cursor: pointer;
}

.generation-console-icon {
  display: grid;
  place-items: center;
  width: 32px;
  height: 32px;
  border-radius: 50%;
  color: #08795f;
  background: #e4f8f1;
}

.generation-console-icon.failed {
  color: #b42318;
  background: #feeceb;
}

.generation-console-copy {
  display: grid;
  min-width: 0;
  gap: 3px;
}

.generation-console-copy strong,
.generation-console-copy small {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.generation-console-copy strong {
  color: #182433;
  font-size: 14px;
  font-weight: 900;
}

.generation-console-copy small {
  color: #6a7a8d;
  font-size: 12px;
  font-weight: 700;
}

.generation-console-summary > b {
  color: #0b8568;
  font-size: 14px;
  font-weight: 900;
}

.generation-console.failed .generation-console-summary > b {
  color: #b42318;
}

.generation-console-progress {
  height: 3px;
  background: #e8eef2;
}

.generation-console-progress span {
  display: block;
  height: 100%;
  background: linear-gradient(90deg, #13af88, #2f8cff);
  transition: width 0.25s ease;
}

.generation-console.failed .generation-console-progress span {
  background: #dc4c45;
}

.generation-console-detail {
  padding: 14px;
  border-top: 1px solid #e9eef2;
}

.generation-console-meta {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 8px 16px;
  margin: 0 0 12px;
}

.generation-console-meta div {
  display: grid;
  min-width: 0;
  gap: 2px;
}

.generation-console-meta dt,
.generation-console-meta dd {
  margin: 0;
}

.generation-console-meta dt {
  color: #7a8999;
  font-size: 11px;
  font-weight: 750;
}

.generation-console-meta dd {
  overflow: hidden;
  color: #26374a;
  font-size: 12px;
  font-weight: 850;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.generation-trace-list {
  display: grid;
  max-height: 250px;
  gap: 0;
  margin: 0;
  padding: 0;
  overflow: auto;
  border: 1px solid #e3eaf0;
  border-radius: 6px;
  background: #f8fafb;
  list-style: none;
  overscroll-behavior: contain;
}

.generation-trace-list li {
  display: grid;
  grid-template-columns: 66px 116px minmax(0, 1fr);
  align-items: start;
  gap: 8px;
  padding: 8px 10px;
  border-bottom: 1px solid #e8edf1;
}

.generation-trace-list li:last-child {
  border-bottom: 0;
}

.generation-trace-list time,
.generation-trace-list span {
  color: #718094;
  font-size: 11px;
  font-weight: 750;
  line-height: 1.5;
}

.generation-trace-list span {
  overflow: hidden;
  color: #376071;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.generation-trace-list p {
  margin: 0;
  color: #29394c;
  font-size: 12px;
  font-weight: 700;
  line-height: 1.5;
  overflow-wrap: anywhere;
}

.generation-trace-list li.failed p,
.generation-trace-list li.error p {
  color: #b42318;
}

.generation-error {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-top: 12px;
  padding: 10px;
  border: 1px solid rgba(220, 38, 38, 0.18);
  border-radius: 6px;
  background: #fff5f4;
}

.generation-error > span {
  display: grid;
  min-width: 0;
  gap: 3px;
}

.generation-error strong,
.generation-error small {
  overflow-wrap: anywhere;
}

.generation-error strong {
  color: #9f241d;
  font-size: 12px;
  line-height: 1.45;
}

.generation-error small {
  color: #b45d58;
  font-size: 11px;
}

.generation-error button {
  display: inline-flex;
  flex: 0 0 auto;
  align-items: center;
  justify-content: center;
  gap: 6px;
  min-height: 34px;
  padding: 0 11px !important;
  border: 1px solid rgba(180, 35, 24, 0.24) !important;
  border-radius: 6px !important;
  color: #9f241d !important;
  background: #ffffff !important;
  box-shadow: none !important;
  font-size: 12px;
  font-weight: 850;
  cursor: pointer;
  white-space: nowrap;
}

.generation-error button:disabled {
  opacity: 0.55;
  cursor: wait;
}

@media (max-width: 900px) {
  .clean-map-page {
    min-height: 620px;
  }

  .current-profile-path-switcher {
    top: 20px;
    right: 16px;
    width: 280px;
  }

  .stage-overview {
    width: 248px;
    padding: 16px;
  }

  .map-generation-progress {
    top: auto;
    right: 16px;
    bottom: 18px;
    left: 16px;
    max-width: none;
  }

  .generation-console {
    right: 16px;
    bottom: 16px;
    width: min(500px, calc(100% - 32px));
  }

  .path-basis-notice {
    right: 16px;
    width: min(520px, calc(100% - 296px));
  }


  .overview-body {
    grid-template-columns: 82px minmax(0, 1fr);
  }

  .overview-ring {
    width: 76px;
    height: 76px;
  }
}

@media (max-width: 600px) {
  .clean-map-page {
    height: auto;
    overflow: visible;
  }

  .clean-map-viewport {
    min-height: calc(100vh - 64px);
  }

  .current-profile-path-switcher {
    top: 16px;
    right: 16px;
    left: 16px;
    width: auto;
  }

  .generation-console {
    right: 12px;
    bottom: 12px;
    width: calc(100% - 24px);
  }

  .generation-console-detail {
    padding: 10px;
  }

  .generation-console-meta {
    grid-template-columns: minmax(0, 1fr);
  }

  .generation-trace-list {
    max-height: 180px;
  }

  .generation-trace-list li {
    grid-template-columns: 58px minmax(0, 1fr);
  }

  .generation-trace-list p {
    grid-column: 1 / -1;
  }

  .generation-error {
    align-items: stretch;
    flex-direction: column;
  }

  .generation-error button {
    width: 100%;
  }

  .week-overview-map .stage-overview {
    top: 190px;
    left: 16px;
    width: calc(100% - 32px);
  }

  .week-overview-map.has-path-notice .stage-overview {
    top: 314px;
  }

  .week-overview-map .path-basis-notice {
    top: 190px;
    right: 16px;
    left: 16px;
    grid-template-columns: minmax(0, 1fr);
    width: auto;
    padding-left: 72px;
  }

  .path-basis-notice > svg {
    display: none;
  }

  .path-basis-notice button {
    grid-column: 1 / -1;
    width: 100%;
  }

  .node-popover {
    width: 320px;
    max-width: calc(100vw - 40px);
  }

  .compact-week-map .dot-title {
    display: -webkit-box;
    width: 150px;
    max-width: 150px;
    overflow: hidden;
    font-size: 14px;
    line-height: 1.25;
    -webkit-box-orient: vertical;
    -webkit-line-clamp: 2;
  }

  .compact-week-map .dot-state {
    display: none;
  }

  .compact-week-map.has-active-node .stage-overview {
    display: none;
  }

  .compact-week-map .node-popover {
    z-index: 12;
    transform: translateX(-50%);
  }
}

/* Keep map nodes transparent and position-stable over the circuit background. */
.clean-map-viewport .map-board .map-dot,
.clean-map-viewport .map-board .map-dot:hover,
.clean-map-viewport .map-board .map-dot:focus,
.clean-map-viewport .map-board .map-dot:focus-visible,
.clean-map-viewport .map-board .map-dot[data-active="true"] {
  pointer-events: auto !important;
  border: 0 !important;
  border-radius: 0 !important;
  outline: 0 !important;
  background: transparent !important;
  box-shadow: none !important;
  transform: translate(-50%, -50%) !important;
}

.clean-map-viewport .map-board .map-dot .dot-core,
.clean-map-viewport .map-board .map-dot.done .dot-core,
.clean-map-viewport .map-board .map-dot.current .dot-core,
.clean-map-viewport .map-board .map-dot.locked .dot-core,
.clean-map-viewport .map-board .map-dot:hover .dot-core,
.clean-map-viewport .map-board .map-dot:focus .dot-core,
.clean-map-viewport .map-board .map-dot:focus-visible .dot-core,
.clean-map-viewport .map-board .map-dot[data-active="true"] .dot-core {
  border-color: transparent !important;
  background: transparent !important;
  box-shadow: none !important;
  transform: translate(-50%, -50%) !important;
}

.clean-map-viewport .map-board .map-dot.done .dot-core,
.clean-map-viewport .map-board .map-dot.current .dot-core {
  color: #0f7b63 !important;
}

.clean-map-viewport .map-board .map-dot .dot-title,
.clean-map-viewport .map-board .map-dot .dot-state,
.clean-map-viewport .map-board .map-dot.current .dot-state,
.clean-map-viewport .map-board .map-dot.locked .dot-state {
  background: transparent !important;
  box-shadow: none !important;
}

.clean-map-viewport .map-board .map-dot:hover .dot-title,
.clean-map-viewport .map-board .map-dot:hover .dot-state,
.clean-map-viewport .map-board .map-dot:focus .dot-title,
.clean-map-viewport .map-board .map-dot:focus .dot-state,
.clean-map-viewport .map-board .map-dot[data-active="true"] .dot-title,
.clean-map-viewport .map-board .map-dot[data-active="true"] .dot-state {
  transform: translateX(-50%) !important;
}

:global(#app .clean-map-viewport .map-board .map-dot),
:global(#app .clean-map-viewport .map-board .map-dot:hover),
:global(#app .clean-map-viewport .map-board .map-dot:focus),
:global(#app .clean-map-viewport .map-board .map-dot:focus-visible),
:global(#app .clean-map-viewport .map-board .map-dot[data-active="true"]) {
  pointer-events: auto !important;
  background: transparent !important;
  box-shadow: none !important;
  transform: translate(-50%, -50%) !important;
}

:global(#app .clean-map-viewport .map-board .map-dot .dot-core),
:global(#app .clean-map-viewport .map-board .map-dot.current .dot-core),
:global(#app .clean-map-viewport .map-board .map-dot.done .dot-core),
:global(#app .clean-map-viewport .map-board .map-dot.locked .dot-core),
:global(#app .clean-map-viewport .map-board .map-dot:hover .dot-core),
:global(#app .clean-map-viewport .map-board .map-dot:focus .dot-core),
:global(#app .clean-map-viewport .map-board .map-dot:focus-visible .dot-core),
:global(#app .clean-map-viewport .map-board .map-dot[data-active="true"] .dot-core) {
  border-color: transparent !important;
  background: transparent !important;
  box-shadow: none !important;
  transform: translate(-50%, -50%) !important;
}

:global(#app .clean-map-viewport .map-board .map-dot.current .dot-core),
:global(#app .clean-map-viewport .map-board .map-dot.done .dot-core) {
  color: #0f7b63 !important;
}

:global(#app .clean-map-viewport .map-board .map-dot .dot-title),
:global(#app .clean-map-viewport .map-board .map-dot .dot-state),
:global(#app .clean-map-viewport .map-board .map-dot.current .dot-state),
:global(#app .clean-map-viewport .map-board .map-dot.done .dot-state),
:global(#app .clean-map-viewport .map-board .map-dot.locked .dot-state),
:global(#app .clean-map-viewport .map-board .map-dot:hover .dot-title),
:global(#app .clean-map-viewport .map-board .map-dot:hover .dot-state),
:global(#app .clean-map-viewport .map-board .map-dot:focus .dot-title),
:global(#app .clean-map-viewport .map-board .map-dot:focus .dot-state),
:global(#app .clean-map-viewport .map-board .map-dot[data-active="true"] .dot-title),
:global(#app .clean-map-viewport .map-board .map-dot[data-active="true"] .dot-state) {
  background: transparent !important;
  box-shadow: none !important;
}

:global(#app .clean-map-viewport .map-board .node-popover) {
  pointer-events: auto !important;
}

/* The map node stays borderless; the round core is the visual entry control. */
:global(#app .clean-map-viewport .map-board .map-dot .dot-core),
:global(#app .clean-map-viewport .map-board .map-dot.done .dot-core),
:global(#app .clean-map-viewport .map-board .map-dot.current .dot-core),
:global(#app .clean-map-viewport .map-board .map-dot.locked .dot-core) {
  width: 58px !important;
  height: 58px !important;
  border: 0 !important;
  color: #ffffff !important;
  background: radial-gradient(circle at 32% 26%, #dffff6 0 7%, #63e1c3 20%, #14ad87 57%, #08765f 100%) !important;
  box-shadow: 0 0 0 5px rgba(255, 255, 255, 0.72), 0 12px 24px rgba(9, 116, 94, 0.28) !important;
  transform: translate(-50%, -50%) !important;
  transition: transform 180ms ease, box-shadow 180ms ease, filter 180ms ease !important;
}

:global(#app .clean-map-viewport .map-board .map-dot.locked .dot-core) {
  color: #506273 !important;
  background: radial-gradient(circle at 32% 26%, #ffffff 0 8%, #e6edf2 38%, #b6c4d0 100%) !important;
  box-shadow: 0 0 0 5px rgba(255, 255, 255, 0.64), 0 10px 20px rgba(71, 85, 105, 0.16) !important;
}

:global(#app .clean-map-viewport .map-board .map-dot:hover .dot-core),
:global(#app .clean-map-viewport .map-board .map-dot:focus-visible .dot-core),
:global(#app .clean-map-viewport .map-board .map-dot[data-active="true"] .dot-core) {
  filter: saturate(1.08) brightness(1.04);
  box-shadow: 0 0 0 7px rgba(151, 249, 223, 0.58), 0 16px 30px rgba(9, 116, 94, 0.34) !important;
  transform: translate(-50%, -50%) scale(1.08) !important;
}

:global(#app .clean-map-viewport .map-board .map-dot .dot-action) {
  position: absolute;
  left: calc(50% + 12px);
  top: calc(50% + 10px);
  z-index: 4;
  display: grid;
  place-items: center;
  width: 23px;
  height: 23px;
  padding: 4px;
  border: 2px solid rgba(255, 255, 255, 0.9);
  border-radius: 50%;
  color: #08765f;
  background: #ffffff;
  box-shadow: 0 5px 12px rgba(9, 76, 64, 0.2);
  transition: transform 180ms ease, color 180ms ease;
}

:global(#app .clean-map-viewport .map-board .map-dot.locked .dot-action) {
  color: #718096;
  background: #f8fafc;
}

:global(#app .clean-map-viewport .map-board .map-dot:hover .dot-action),
:global(#app .clean-map-viewport .map-board .map-dot[data-active="true"] .dot-action) {
  color: #056b55;
  transform: translate(2px, -2px) scale(1.08);
}

/* Remove any inherited rectangular node surface; only the circular entry control remains. */
:global(#app .clean-map-viewport .map-board .map-dot),
:global(#app .clean-map-viewport .map-board .map-dot:hover),
:global(#app .clean-map-viewport .map-board .map-dot:focus),
:global(#app .clean-map-viewport .map-board .map-dot:focus-visible),
:global(#app .clean-map-viewport .map-board .map-dot[data-active="true"]) {
  border: 0 !important;
  outline: 0 !important;
  background: transparent !important;
  background-image: none !important;
  box-shadow: none !important;
}

:global(#app .clean-map-viewport .map-board .map-dot::before),
:global(#app .clean-map-viewport .map-board .map-dot::after) {
  display: none !important;
  content: none !important;
  border: 0 !important;
  background: transparent !important;
  box-shadow: none !important;
}

/* Minimal week map nodes: white circles, green labels, and an in-node completion mark. */
:global(#app .clean-map-viewport .map-board .map-dot .dot-core),
:global(#app .clean-map-viewport .map-board .map-dot.done .dot-core),
:global(#app .clean-map-viewport .map-board .map-dot.current .dot-core),
:global(#app .clean-map-viewport .map-board .map-dot.locked .dot-core) {
  width: 66px !important;
  height: 66px !important;
  color: #087a55 !important;
  background: rgba(255, 255, 255, 0.94) !important;
  box-shadow: 0 3px 12px rgba(28, 64, 54, 0.1) !important;
  filter: none !important;
}

:global(#app .clean-map-viewport .map-board .map-dot .dot-core svg) {
  color: #098158;
}

:global(#app .clean-map-viewport .map-board .map-dot:hover .dot-core),
:global(#app .clean-map-viewport .map-board .map-dot:focus-visible .dot-core),
:global(#app .clean-map-viewport .map-board .map-dot[data-active="true"] .dot-core) {
  box-shadow: 0 6px 16px rgba(28, 64, 54, 0.16) !important;
  filter: none !important;
  transform: translate(-50%, -50%) scale(1.05) !important;
}

:global(#app .clean-map-viewport .map-board .map-dot .dot-action),
:global(#app .clean-map-viewport .map-board .map-dot .dot-mark),
:global(#app .clean-map-viewport .map-board .map-dot .dot-lock) {
  display: none !important;
}

@media (prefers-reduced-motion: reduce) {
  .week-overview-map .current-profile-path-switcher,
  .week-overview-map .stage-overview {
    animation: none;
  }
}

/* Week milestones grow from a study house into a complete academy campus. */
.week-overview-map .map-dot {
  width: 280px;
  height: 264px;
}

.week-overview-map .dot-title {
  top: calc(50% + 112px);
  width: 230px;
  color: #203d35;
  font-size: 15px;
  text-shadow: 0 1px 0 rgba(255, 255, 255, 0.92);
}

.week-overview-map .dot-state {
  top: calc(50% + 153px);
  padding: 4px 9px;
  border: 1px solid rgba(45, 100, 81, 0.12);
  border-radius: 4px;
  background: rgba(247, 251, 247, 0.86) !important;
  backdrop-filter: blur(5px);
}

.week-overview-map .route-pending {
  stroke: rgba(72, 124, 105, 0.52);
  stroke-dasharray: 7 13;
  stroke-width: 3;
}

.week-overview-map .route-done {
  stroke-width: 4;
}

@media (max-width: 600px) {
  .compact-week-map .map-dot {
    width: 184px;
    height: 204px;
  }

  .compact-week-map .dot-title {
    top: calc(50% + 82px);
  }
}
</style>
