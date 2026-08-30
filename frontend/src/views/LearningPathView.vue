<template>
  <main class="learning-path-page">
    <section class="path-shell" aria-label="按周学习路径">
      <button
        v-if="isWeekTaskPage"
        type="button"
        class="back-to-week-map"
        aria-label="返回周次地图"
        @click="goBackToWeekMap"
      >
        <ArrowLeft :size="17" stroke-width="2.3" aria-hidden="true" />
        <span>返回周次地图</span>
      </button>
      <header class="path-heading">
        <div v-if="loading" class="path-heading-skeleton" aria-hidden="true">
          <p></p>
          <h1></h1>
          <span></span>
        </div>
        <div v-else>
          <p v-if="displayMeta.eyebrow">{{ displayMeta.eyebrow }}</p>
          <h1>{{ displayMeta.title }}</h1>
          <span v-if="pageSubtitle">{{ pageSubtitle }}</span>
        </div>
        <aside class="path-progress-card" :class="{ 'path-progress-skeleton': loading }" aria-label="学习路径总进度">
          <div class="progress-card-head">
            <Activity :size="16" stroke-width="2.4" aria-hidden="true" />
            <span>{{ loading ? '' : progressStatusLabel }}</span>
            <strong>{{ loading ? '--' : `${progressPercent}%` }}</strong>
          </div>
          <i><b :style="{ width: loading ? '0%' : `${progressPercent}%` }"></b></i>
        </aside>
      </header>

      <div v-if="loading" class="path-loading-panel" aria-live="polite">
        <div class="path-state">{{ loadingText }}</div>
        <div class="week-rail week-rail-skeleton" aria-hidden="true">
          <span v-for="index in 6" :key="`rail-skeleton-${index}`" class="rail-node">
            <span class="rail-dot"></span>
            <b></b>
          </span>
        </div>
        <div class="week-grid">
          <div v-for="index in 6" :key="`week-skeleton-${index}`" class="week-card week-card-skeleton">
            <span class="week-icon"></span>
            <span class="week-copy">
              <small></small>
              <strong></strong>
              <em></em>
            </span>
          </div>
        </div>
      </div>

      <template v-else>
        <div v-if="pathLoadError" class="path-request-error" role="alert">
          <CircleAlert :size="22" stroke-width="2.3" aria-hidden="true" />
          <span>
            <strong>{{ pathLoadError.title }}</strong>
            <small>{{ pathLoadError.message }}</small>
            <small v-if="isWeekTaskPage">已保留成功读取的学习画像与路径配置，不会自动创建资源。</small>
          </span>
          <button type="button" @click="retryLearningPathLoad">
            <RotateCcw :size="15" aria-hidden="true" />
            重新加载
          </button>
        </div>

        <template v-else>
          <div v-if="generationError" class="path-request-error generation-failed" role="alert">
            <CircleAlert :size="22" stroke-width="2.3" aria-hidden="true" />
            <span>
              <strong>{{ generationError.title }}</strong>
              <small>{{ generationError.message }}</small>
              <small>已生成并保存的周次会继续保留。</small>
            </span>
            <button type="button" :disabled="planning || planningRemaining" @click="retryLearningPathGeneration">
              <RotateCcw :size="15" aria-hidden="true" />
              继续生成
            </button>
          </div>

          <div v-if="!generationError && !hasActiveLearningProfile" class="path-context-state no-profile-state" role="status">
            <CircleAlert :size="17" stroke-width="2.3" aria-hidden="true" />
            <span>当前没有学习画像，请先完成学习画像后再生成个性化周任务。</span>
            <button type="button" @click="router.push('/learning-profile')">完成学习画像</button>
          </div>

          <div v-if="hasActiveLearningProfile && isWeekTaskPage && pathNotice" class="path-context-state" role="status">
            <CircleAlert :size="17" stroke-width="2.3" aria-hidden="true" />
            <span>{{ pathNotice }}</span>
            <button type="button" @click="handlePathNoticeAction">{{ pathNoticeActionLabel }}</button>
          </div>

          <div
            v-if="hasActiveLearningProfile && isWeekTaskPage && resourcePrepareError"
            class="resource-generation-state"
            :class="{ failed: resourcePrepareError }"
            role="status"
          >
            <CircleAlert :size="17" stroke-width="2.3" aria-hidden="true" />
            <span>{{ resourcePrepareError }}</span>
            <button type="button" @click="prepareWeekResources(String(route.params.stageId || ''))">
              重试
            </button>
          </div>

          <div v-if="hasActiveLearningProfile && !isWeekTaskPage" class="week-rail" aria-label="周学习进度">
            <i :style="{ width: `${railProgressPercent}%` }"></i>
            <component
              v-for="(week, weekIndex) in visibleWeeks"
              :key="`${week.id}-rail`"
              :is="weekEntryTag(week)"
              :type="weekEntryTag(week) === 'button' ? 'button' : null"
              :href="weekEntryHref(week)"
              :target="weekEntryHref(week) ? '_blank' : null"
              :rel="weekEntryHref(week) ? 'noopener noreferrer' : null"
              class="rail-node"
              :class="[`status-${week.status || 'locked'}`]"
              :disabled="weekEntryTag(week) === 'button' ? (isWeekTaskPage && !week.actionRoute) : undefined"
              @click="openWeek(week, $event)"
            >
              <span class="rail-dot">
                <component :is="resolveIcon(week.icon)" :size="16" stroke-width="2.15" aria-hidden="true" />
              </span>
              <b>{{ week.weekLabel }}</b>
            </component>
            <span v-if="placeholderCard" class="rail-node rail-placeholder">
              <span class="rail-dot">
                <Flag :size="16" stroke-width="2.15" aria-hidden="true" />
              </span>
              <b>{{ displayMeta.placeholderTitle }}</b>
            </span>
          </div>

          <TransitionGroup
            v-if="hasActiveLearningProfile"
            name="task-reveal"
            tag="div"
            class="week-grid"
            :class="{ 'task-resource-grid': isWeekTaskPage }"
          >
            <component
              v-for="(week, weekIndex) in visibleWeeks"
              :key="week.id"
              :is="weekEntryTag(week)"
              :type="weekEntryTag(week) === 'button' ? 'button' : null"
              :href="weekEntryHref(week)"
              :target="weekEntryHref(week) ? '_blank' : null"
              :rel="weekEntryHref(week) ? 'noopener noreferrer' : null"
              class="week-card"
              :class="[
                isWeekTaskPage ? 'task-resource-card' : `tone-${week.tone || 'green'}`,
                `status-${week.visualStatus || week.status || 'locked'}`,
              ]"
              :data-resource-type="isWeekTaskPage ? week.resourceType : undefined"
              :aria-label="`${week.weekLabel}${week.resourceLabel ? ` ${week.resourceLabel}` : ''} ${week.title}`"
              :disabled="weekEntryTag(week) === 'button' ? (isWeekTaskPage && !week.actionRoute) : undefined"
              @click="openWeek(week, $event)"
            >
              <template v-if="isWeekTaskPage">
                <span class="task-resource-cover" aria-hidden="true">
                  <span class="task-cover-loading" :class="{ hidden: isTaskCoverLoaded(week.coverKey) }">
                    <component :is="resolveIcon(week.icon)" :size="30" stroke-width="1.6" />
                    <small>{{ taskCoverStatusLabel(week) }}</small>
                  </span>
                  <img
                    v-if="isGeneratedVideoTask(week) && taskPosterUrl(week)"
                    :class="{ loaded: isTaskCoverLoaded(week.coverKey) }"
                    :src="taskPosterUrl(week)"
                    alt=""
                    loading="lazy"
                    decoding="async"
                    @load="markTaskCoverLoaded(week.coverKey)"
                    @error="retryTaskPoster(week)"
                  />
                  <iframe
                    v-else-if="taskCoverPreviewUrl(week)"
                    class="task-resource-live-cover"
                    :class="{ loaded: isTaskCoverLoaded(week.coverKey) }"
                    :src="taskCoverPreviewUrl(week)"
                    :title="`${week.title}页面封面`"
                    tabindex="-1"
                    loading="lazy"
                    scrolling="no"
                    aria-hidden="true"
                    @load="markTaskCoverLoaded(week.coverKey)"
                  ></iframe>
                </span>
                <span class="task-resource-copy">
                  <strong>{{ week.title }}</strong>
                  <small>{{ week.resourceLabel }}</small>
                </span>
              </template>
              <template v-else>
                <span class="week-icon" aria-hidden="true">
                  <component :is="resolveIcon(week.icon)" :size="28" stroke-width="2.1" />
                </span>
                <span class="week-copy">
                  <small>{{ week.weekLabel }}</small>
                  <strong>{{ week.title }}</strong>
                  <em>{{ week.description }}</em>
                </span>
                <span class="week-status">
                  <component :is="statusIcon(week.visualStatus || week.status)" :size="14" stroke-width="2.4" aria-hidden="true" />
                  {{ week.statusText || statusLabel(week.status) }}
                </span>
                <component class="week-watermark" :is="resolveIcon(week.icon)" :size="76" stroke-width="1.35" aria-hidden="true" />
                <ChevronRight class="week-arrow" :size="24" stroke-width="2.2" aria-hidden="true" />
              </template>
            </component>

            <button
              v-if="placeholderCard"
              key="path-placeholder"
              type="button"
              class="week-card placeholder-card"
              disabled
              aria-label="后续周数"
            >
              <span class="week-icon" aria-hidden="true">
                <MoreHorizontal :size="28" stroke-width="2.4" />
              </span>
              <span class="week-copy">
                <small>{{ displayMeta.placeholderWeekLabel }}</small>
                <strong>{{ displayMeta.placeholderTitle }}</strong>
                <em>更多阶段将根据学习进度继续开放。</em>
              </span>
              <LockKeyhole class="placeholder-lock" :size="16" stroke-width="2.2" aria-hidden="true" />
            </button>
          </TransitionGroup>

          <div
            v-if="hasActiveLearningProfile && !isWeekTaskPage && visibleWeeks.length"
            class="path-continuation"
            aria-label="后续学习路径"
          >
            <span>
              <strong>已规划 {{ visibleWeeks.length }} / {{ totalWeekCount }} 周</strong>
              <small>查看完当前周的全部任务后，岐小智会在后台自动规划下一周；更新画像后，后续任务将使用新画像。</small>
            </span>
            <button type="button" class="assessment-button" @click="router.push('/effect-assessment')">
              <ClipboardCheck :size="16" aria-hidden="true" />
              更新画像后再规划
            </button>
          </div>
        </template>
      </template>
    </section>
  </main>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import {
  Activity,
  ArrowLeft,
  BookOpen,
  Brain,
  Check,
  ChevronRight,
  CircleAlert,
  Clock3,
  ClipboardCheck,
  Cpu,
  FileText,
  Film,
  Flag,
  Layers,
  LockKeyhole,
  MoreHorizontal,
  Rocket,
  RotateCcw,
  ScanSearch,
  Target,
} from 'lucide-vue-next'
import { useRoute, useRouter } from 'vue-router'
import {
  generateLearningPath,
  getLearningPathConfig,
  getLearningPathStage,
  getLearningPathStageResourceTasks,
  prepareLearningPathStageResources,
} from '../services/api.js'
import { cloneLearningPathConfig, defaultLearningPathConfig } from '../config/learningPathDefaults.js'
import {
  getNodeCache,
  hydrateNodeCachesFromServer,
  markNodeCacheViewed,
} from '../services/learningPathNodeCache.js'
import { dispatchXiaoZhiWorkflowProgress } from '../utils/xiaozhiWorkflowProgress.js'

const router = useRouter()
const route = useRoute()
const loading = ref(false)
const planning = ref(false)
const planningRemaining = ref(false)
const pathLoadError = ref(null)
const generationError = ref(null)
const pathConfig = ref(cloneLearningPathConfig())
const taskStage = ref(createFallbackTaskStage(String(route.params.stageId || '')))
const resourcePreparing = ref(false)
const resourcePrepareError = ref('')
const loadedTaskCovers = ref(new Set())
const cacheVersion = ref(0)
let resourcePollTimer = null
let resourcePreparationRun = 0
let foregroundPathWorkflowId = ''
const taskPosterRetries = new Map()
const taskPosterRetryTimers = new Map()
const hiddenStageIds = new Set(['profile-diagnosis'])
const weekNumberLabels = ['一', '二', '三', '四', '五', '六', '七', '八', '九', '十', '十一', '十二']

const iconMap = {
  brain: Brain,
  'book-open': BookOpen,
  'clipboard-check': ClipboardCheck,
  cpu: Cpu,
  target: Target,
  layers: Layers,
  rocket: Rocket,
  'file-text': FileText,
  film: Film,
  'scan-search': ScanSearch,
}

const pageMeta = computed(() => ({
  ...defaultLearningPathConfig.meta,
  ...(pathConfig.value?.meta || {}),
}))

const isWeekTaskPage = computed(() => Boolean(route.params.stageId) && route.name === 'learning-path-week-detail')
const hasActiveLearningProfile = computed(() => Number(pathConfig.value?.meta?.activeProfileReportId || 0) > 0)
const totalWeekCount = computed(() => Math.max(1, Number(pathConfig.value?.meta?.totalWeeks || 6)))
const resourcePreparation = computed(() => (
  taskStage.value?.resourcePreparation && typeof taskStage.value.resourcePreparation === 'object'
    ? taskStage.value.resourcePreparation
    : {}
))

const resourcePreparationText = computed(() => {
  const total = Number(resourcePreparation.value.totalCount || taskStage.value?.nodes?.length || 0)
  const resolved = Number(resourcePreparation.value.resolvedCount || 0)
  const activeNodeIds = Array.isArray(resourcePreparation.value.activeNodeIds)
    ? resourcePreparation.value.activeNodeIds.filter(Boolean)
    : []
  if (activeNodeIds.length > 1) {
    return `正在创建 ${activeNodeIds.length} 个任务入口并提交后台生成，已就绪 ${resolved}/${total}`
  }
  const currentNodeId = String(resourcePreparation.value.currentNodeId || '')
  const currentNode = (taskStage.value?.nodes || []).find(node => String(node?.id || '') === currentNodeId)
  const sequence = Math.min(total || 1, resolved + 1)
  return currentNode
    ? `正在创建任务入口 ${sequence}/${total}：${currentNode.title || `任务 ${currentNodeId}`}`
    : '正在创建全部任务入口并提交后台并行生成。'
})

const pathNotice = computed(() => {
  const status = String(pathConfig.value?.meta?.personalizationStatus || '')
  const hasActiveProfile = Number(pathConfig.value?.meta?.activeProfileReportId || 0) > 0
  if (status === 'legacy-generic') {
    return hasActiveProfile
      ? '本周任务来自历史通用路径；新资源会按当前画像编排，路径本身需在周次地图中手动重新生成。'
      : '当前没有学习画像，请先完成学习画像后再生成个性化周任务。'
  }
  if (status === 'historical-profile') {
    return '当前没有学习画像，请先完成学习画像后再生成个性化周任务。'
  }
  if (status === 'stale-profile') {
    return '当前已切换学习画像。本周旧任务仍可查看，新路径需要回到周次地图后手动重新生成。'
  }
  return ''
})

const pathNoticeActionLabel = computed(() => {
  const hasActiveProfile = Number(pathConfig.value?.meta?.activeProfileReportId || 0) > 0
  return hasActiveProfile && pathConfig.value?.meta?.canGeneratePersonalized
    ? '返回周次地图'
    : '完成学习画像'
})

const displayMeta = computed(() => {
  if (!isWeekTaskPage.value) return pageMeta.value
  const stage = taskStage.value || {}
  const weekLabel = String(stage.weekLabel || findWeekLabel(route.params.stageId) || '本周')
  const rawTitle = String(stage.title || '').trim()
  const compactTitle = rawTitle
    .replace(/^第(?:[一二三四五六七八九十百]+|\d+)周\s*[：:\-·]?\s*/, '')
    .trim()
  const hasSpecificTitle = compactTitle && !['学习路径', '具体学习任务', '学习任务'].includes(compactTitle)
  return {
    ...pageMeta.value,
    eyebrow: '',
    title: hasSpecificTitle ? `${weekLabel} · ${compactTitle}` : `${weekLabel}学习任务`,
    placeholderTitle: '',
    placeholderWeekLabel: '',
  }
})

const pageSubtitle = computed(() => {
  if (isWeekTaskPage.value) return ''
  return pathConfig.value?.meta?.subtitle || '循序渐进，按周推进你的学习进度。'
})

const loadingText = computed(() => (
  planning.value ? '正在根据学习画像生成周学习路径' : '正在加载学习路径'
))

const visibleWeeks = computed(() => {
  if (isWeekTaskPage.value) return visibleTasks.value
  if (!pathConfig.value) return []
  const weeks = Array.isArray(pathConfig.value?.weeks) ? pathConfig.value.weeks : []
  return weeks
    .filter((week) => week && week.enabled !== false && !week.placeholder && !hiddenStageIds.has(String(week.id || '')))
    .sort((left, right) => Number(left.order || 0) - Number(right.order || 0))
    .map((week, index) => ({
      id: String(week.id || `week-${index + 1}`),
      order: index + 1,
      weekLabel: formatWeekLabel(index + 1),
      title: String(week.title || '学习任务'),
      status: String(week.status || 'locked'),
      tone: String(week.tone || 'green'),
      icon: String(week.icon || 'book-open'),
      description: String(week.description || '按当前阶段目标推进学习任务。'),
    }))
})

const visibleTasks = computed(() => {
  const allNodes = Array.isArray(taskStage.value?.nodes) ? taskStage.value.nodes : []
  return allNodes
    .filter((node) => node && node.enabled !== false)
    .sort((left, right) => Number(left.order || 0) - Number(right.order || 0))
    .map((node, index) => {
      const resourceTask = node.resourceTask && typeof node.resourceTask === 'object' ? node.resourceTask : {}
      const resourceStatus = String(resourceTask.status || (resourcePreparing.value ? 'planning' : 'unprepared'))
      const resourceType = normalizeTaskResourceType(node.resourceType, index)
      const taskId = String(resourceTask.taskId || '')
      const taskRoute = taskId ? String(resourceTask.route || node.actionRoute || '') : ''
      const coverKey = `${String(route.params.stageId || '')}:${taskId || node.id || index}`
      return {
        id: String(node.id || `task-${index + 1}`),
        order: index + 1,
        weekLabel: `任务 ${String(node.label || index + 1).padStart(2, '0')}`,
        title: String(node.title || '学习任务'),
        status: normalizeTaskStatus(node.state),
        visualStatus: resourceTaskCardStatus(resourceStatus, node.state, resourceType),
        statusText: resourceTaskStatusLabel(resourceStatus, resourceType),
        resourceStatus,
        resourceType,
        resourceLabel: taskResourceLabel(node.resourceType, index),
        icon: taskIcon(resourceType, index),
        taskId,
        coverKey,
        description: String(node.description || node.desc || '完成本任务并记录学习成果。'),
        actionRoute: taskRoute.includes('xzTask=') ? taskRoute : '',
        cacheKey: String(node.cacheKey || ''),
      }
    })
})

const placeholderCard = computed(() => !isWeekTaskPage.value && (displayMeta.value.placeholderTitle || displayMeta.value.placeholderWeekLabel))

const completedWeekCount = computed(() => (
  visibleWeeks.value.filter((week) => ['done', 'completed'].includes(week.status)).length
))

const allWeekTaskNodes = computed(() => (
  Array.isArray(taskStage.value?.nodes)
    ? taskStage.value.nodes.filter(node => node && node.enabled !== false)
    : []
))

const activeWeekCount = computed(() => (
  isWeekTaskPage.value
    ? allWeekTaskNodes.value.filter(isWeekTaskViewed).length
    : visibleWeeks.value
      .filter((item) => ['done', 'completed', 'current', 'active', 'progress'].includes(String(item?.state || item?.status || '')))
      .length
))

const progressPercent = computed(() => {
  const total = (isWeekTaskPage.value ? allWeekTaskNodes.value.length : visibleWeeks.value.length) || 1
  return Math.min(100, Math.round((activeWeekCount.value / total) * 100))
})

const currentWeekLabel = computed(() => String(
  taskStage.value?.weekLabel
  || findWeekLabel(route.params.stageId)
  || '本周',
))

const progressStatusLabel = computed(() => {
  if (!isWeekTaskPage.value) return '总进度'
  if (progressPercent.value <= 0) return `${currentWeekLabel.value}未开始`
  if (progressPercent.value >= 100) return `${currentWeekLabel.value}已完成`
  return `${currentWeekLabel.value}进行中`
})

const railProgressPercent = computed(() => {
  const itemCount = isWeekTaskPage.value ? allWeekTaskNodes.value.length : visibleWeeks.value.length
  const total = Math.max(itemCount - 1, 1)
  const activeIndex = Math.max(0, activeWeekCount.value - 1)
  return Math.min(100, Math.round((activeIndex / total) * 100))
})

onMounted(() => {
  window.addEventListener('storage', handleNodeCacheUpdated)
  window.addEventListener('learning-path-node-cache-updated', handleNodeCacheUpdated)
  void hydrateNodeCachesFromServer()
  void loadLearningPathConfig()
})

watch(
  () => `${String(route.name || '')}:${String(route.params.stageId || '')}`,
  (nextRoute, previousRoute) => {
    if (nextRoute === previousRoute) return
    cancelResourcePreparation()
    stopResourcePolling()
    loadLearningPathConfig()
  },
)

onBeforeUnmount(() => {
  window.removeEventListener('storage', handleNodeCacheUpdated)
  window.removeEventListener('learning-path-node-cache-updated', handleNodeCacheUpdated)
  cancelResourcePreparation()
  stopResourcePolling()
  for (const timer of taskPosterRetryTimers.values()) window.clearTimeout(timer)
  taskPosterRetryTimers.clear()
})

async function loadLearningPathConfig() {
  const hasVisibleData = isWeekTaskPage.value
    ? Array.isArray(taskStage.value?.nodes) && taskStage.value.nodes.length > 0
    : visibleWeeks.value.length > 0
  loading.value = !hasVisibleData
  planning.value = false
  planningRemaining.value = false
  try {
    const config = await getLearningPathConfig({ summary: true })
    let normalizedConfig = normalizeConfig(config)
    pathConfig.value = normalizedConfig
    if (!hasActiveLearningProfile.value) {
      taskStage.value = { id: String(route.params.stageId || ''), nodes: [] }
      return
    }
    if (isWeekTaskPage.value) {
      pathConfig.value = normalizedConfig
      taskStage.value = createFallbackTaskStage(String(route.params.stageId || ''), normalizedConfig)
      await loadWeekTasks(String(route.params.stageId))
      return
    }
    if (shouldAutoPlan(normalizedConfig)) {
      planning.value = true
      const totalWeeks = Math.max(4, Math.min(8, Number(normalizedConfig?.meta?.totalWeeks) || 6))
      startForegroundPathWorkflow(totalWeeks)
      const result = await generateLearningPath({
        persist: true,
        useLatestProfile: true,
        generationPhase: 'first-week',
        weekStart: 1,
        weekCount: 1,
        totalWeeks,
        useLLM: true,
      })
      if (result?.config) {
        normalizedConfig = normalizeConfig(result.config)
      }
      pathConfig.value = normalizedConfig
      publishForegroundPathProgress({
        status: 'complete',
        progress: 100,
        completedWeeks: visiblePathWeekCount(normalizedConfig),
        totalWeeks,
        message: '第一周路径已保存；后续周次将在你确认后逐周规划',
      })
      loading.value = false
      planning.value = false
    } else {
      pathConfig.value = normalizedConfig
    }
  } catch (error) {
    console.warn('Failed to load learning path config, using fallback data.', error)
    if (foregroundPathWorkflowId) {
      publishForegroundPathProgress({
        status: 'failed',
        progress: 100,
        message: error?.message || '学习路径生成失败',
      })
    }
    pathConfig.value = cloneLearningPathConfig()
    if (isWeekTaskPage.value) {
      taskStage.value = pathConfig.value.stages?.[String(route.params.stageId)] || null
    }
  } finally {
    planning.value = false
    loading.value = false
    openCurrentWeekFromEntry()
  }
}

async function loadWeekTasks(stageId) {
  const fallbackStage = createFallbackTaskStage(stageId, pathConfig.value)
  if (fallbackStage && (!taskStage.value?.nodes?.length || String(taskStage.value?.id || '') !== stageId)) {
    taskStage.value = fallbackStage
  }
  if (!fallbackStage) {
    const payload = await getLearningPathStage(stageId)
    if (payload?.config) {
      pathConfig.value = normalizeConfig(payload.config)
    }
    taskStage.value = payload?.stage || payload || null
  }
  loading.value = false
  void refreshWeekResourceStatus(stageId)
}

async function refreshWeekResourceStatus(stageId) {
  if (shouldPrepareWeekResources(taskStage.value) && pathConfig.value?.meta?.canPrepareResources !== false) {
    void prepareWeekResources(stageId)
  } else {
    try {
      const existingTasks = await getLearningPathStageResourceTasks(stageId)
      applyResourceStagePayload(existingTasks)
      if (existingTasks?.needsPreparationRetry && pathConfig.value?.meta?.canPrepareResources !== false) {
        void prepareWeekResources(stageId)
      } else if (existingTasks?.pending) {
        scheduleResourcePolling(stageId)
      }
    } catch (error) {
      console.warn('Failed to refresh existing learning-path resources.', error)
    }
  }
}

async function prepareWeekResources(stageId) {
  if (!stageId || resourcePreparing.value || pathConfig.value?.meta?.canPrepareResources === false) return
  const preparationRun = ++resourcePreparationRun
  resourcePreparing.value = true
  resourcePrepareError.value = ''
  stopResourcePolling()
  try {
    const payload = await prepareLearningPathStageResources(stageId, {
      useLLM: false,
      advance: false,
      parallelDispatch: true,
    })
    if (preparationRun !== resourcePreparationRun) return
    applyResourceStagePayload(payload)
    if (payload?.pending || payload?.needsPreparationRetry) scheduleResourcePolling(stageId)
  } catch (error) {
    if (preparationRun !== resourcePreparationRun) return
    console.warn('Failed to prepare learning-path resources.', error)
    resourcePrepareError.value = error?.response?.data?.msg || error?.message || '本周资源准备失败，请重试。'
  } finally {
    if (preparationRun === resourcePreparationRun) {
      resourcePreparing.value = false
    }
  }
}

function applyResourceStagePayload(payload) {
  const stage = payload?.stage
  if (stage && typeof stage === 'object') {
    taskStage.value = stage
  }
}

function createFallbackTaskStage(stageId, config = pathConfig.value) {
  const normalizedStageId = String(stageId || '')
  const stages = config?.stages && typeof config.stages === 'object' ? config.stages : {}
  const stage = stages[normalizedStageId]
    || Object.values(stages).find(item => item && String(item.id || '') === normalizedStageId)
    || Object.values(stages).find(item => item && Array.isArray(item.nodes) && item.nodes.length)
    || null
  return stage && typeof stage === 'object' ? { ...stage } : null
}

function shouldPrepareWeekResources(stage) {
  const preparationStatus = String(stage?.resourcePreparation?.status || '')
  const nodes = Array.isArray(stage?.nodes) ? stage.nodes : []
  if (!nodes.length) return false
  const hasMissingEntrypoint = nodes.some((node) => {
    const task = node?.resourceTask && typeof node.resourceTask === 'object' ? node.resourceTask : {}
    return !String(task.taskId || '') || !String(task.route || node?.actionRoute || '').includes('xzTask=')
  })
  if (['complete', 'completed'].includes(preparationStatus)) return hasMissingEntrypoint
  if (['running', 'initializing'].includes(preparationStatus)) {
    return hasMissingEntrypoint
  }
  return nodes.some((node) => {
    const task = node?.resourceTask && typeof node.resourceTask === 'object' ? node.resourceTask : {}
    const status = String(task.status || '')
    return !task.taskId && !['running', 'pending', 'complete', 'completed'].includes(status)
  })
}

function scheduleResourcePolling(stageId) {
  stopResourcePolling()
  resourcePollTimer = window.setTimeout(() => refreshResourceTasks(stageId), 2000)
}

async function refreshResourceTasks(stageId) {
  try {
    const payload = await getLearningPathStageResourceTasks(stageId)
    applyResourceStagePayload(payload)
    if (payload?.needsPreparationRetry && pathConfig.value?.meta?.canPrepareResources !== false) {
      void prepareWeekResources(stageId)
      return
    }
    if (payload?.pending) {
      scheduleResourcePolling(stageId)
    }
  } catch (error) {
    console.warn('Failed to refresh resource task status.', error)
    scheduleResourcePolling(stageId)
  }
}

function stopResourcePolling() {
  if (resourcePollTimer) {
    window.clearTimeout(resourcePollTimer)
    resourcePollTimer = null
  }
}

function cancelResourcePreparation() {
  resourcePreparationRun += 1
  resourcePreparing.value = false
}

function retryLearningPathGeneration() {
  generationError.value = null
  void loadLearningPathConfig()
}

function visiblePathWeekCount(config) {
  return (Array.isArray(config?.weeks) ? config.weeks : [])
    .filter(week => week && week.enabled !== false && !week.placeholder && !hiddenStageIds.has(String(week.id || '')))
    .length
}

function startForegroundPathWorkflow(totalWeeks) {
  foregroundPathWorkflowId = `learning-path-page-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`
  publishForegroundPathProgress({
    status: 'running',
    progress: 2,
    completedWeeks: 0,
    totalWeeks,
    message: '学习路径 Agent 正在读取当前画像并规划第一周',
  })
}

function publishForegroundPathProgress(detail = {}) {
  if (!foregroundPathWorkflowId) return
  dispatchXiaoZhiWorkflowProgress({
    workflow: 'learning-path',
    workflowId: foregroundPathWorkflowId,
    stage: detail.status === 'complete' ? 'complete' : detail.status === 'failed' ? 'error' : 'path_planning',
    route: '/learning-path',
    ...detail,
  })
}

function normalizeConfig(config) {
  if (!config || typeof config !== 'object') {
    return cloneLearningPathConfig()
  }
  return {
    ...cloneLearningPathConfig(),
    ...config,
    meta: {
      ...defaultLearningPathConfig.meta,
      ...(config.meta || {}),
    },
    weeks: Array.isArray(config.weeks) ? config.weeks : [],
    stages: config.stages && typeof config.stages === 'object' ? config.stages : {},
  }
}

function resolveIcon(iconName) {
  return iconMap[iconName] || BookOpen
}

function statusLabel(status) {
  if (['done', 'completed'].includes(status)) return '已完成'
  if (['current', 'active', 'progress'].includes(status)) return '进行中'
  return '未开始'
}

function statusIcon(status) {
  if (['done', 'completed'].includes(status)) return Check
  if (['current', 'active', 'progress'].includes(status)) return Activity
  if (status === 'failed') return CircleAlert
  return Clock3
}

function weekEntryTag(week) {
  return isWeekTaskPage.value && week?.actionRoute && !opensResourceInCurrentTab(week) ? 'a' : 'button'
}

function weekActionHref(week) {
  if (!isWeekTaskPage.value || !week?.actionRoute) return null
  return /^https?:\/\//i.test(week.actionRoute)
    ? week.actionRoute
    : router.resolve(week.actionRoute).href
}

function opensResourceInCurrentTab(week) {
  return normalizeTaskResourceType(week?.resourceType) === 'herb-model'
}

function weekEntryHref(week) {
  return opensResourceInCurrentTab(week) ? null : weekActionHref(week)
}

async function openWeek(week, event) {
  if (!week?.id) return
  if (isWeekTaskPage.value) {
    if (!week.actionRoute) {
      if (!resourcePreparing.value && pathConfig.value?.meta?.canPrepareResources !== false) {
        void prepareWeekResources(String(route.params.stageId || ''))
      }
      return
    }
    const href = weekActionHref(week)
    let viewSavePromise = null
    if (week.cacheKey) {
      viewSavePromise = markNodeCacheViewed(week.cacheKey, {
        stageId: String(route.params.stageId || ''),
        nodeId: week.id,
        profileReportId: Number(pathConfig.value?.meta?.profileReportId || pathConfig.value?.meta?.activeProfileReportId || 0),
        resourceType: week.resourceType,
        title: week.title,
        route: href,
        viewedAt: Date.now(),
      })
    }
    if (opensResourceInCurrentTab(week)) {
      if (viewSavePromise) await viewSavePromise
      router.push(href)
      return
    }
    if (event?.currentTarget?.tagName === 'A') return
    window.open(href, '_blank', 'noopener,noreferrer')
    return
  }
  router.push({ name: 'learning-path-week-detail', params: { stageId: week.id } })
}

function goBackToWeekMap() {
  router.push({ name: 'learning-path' })
}

function handlePathNoticeAction() {
  const hasActiveProfile = Number(pathConfig.value?.meta?.activeProfileReportId || 0) > 0
  if (hasActiveProfile && pathConfig.value?.meta?.canGeneratePersonalized) {
    goBackToWeekMap()
    return
  }
  router.push('/learning-profile')
}

function normalizeTaskStatus(state) {
  if (state === 'done') return 'done'
  if (state === 'current') return 'current'
  return 'available'
}

function resourceTaskCardStatus(resourceStatus, learningState, resourceType) {
  if (resourceStatus === 'complete') return 'done'
  if (resourceStatus === 'failed') return 'failed'
  if (resourceStatus === 'waiting' && resourceType === 'generated_video') return 'waiting'
  if (['planning', 'queued', 'running'].includes(resourceStatus)) return 'current'
  return normalizeTaskStatus(learningState)
}

function resourceTaskStatusLabel(resourceStatus, resourceType) {
  if (resourceStatus === 'waiting' && resourceType === 'generated_video') return '待用户确认'
  const labels = {
    planning: '正在创建入口',
    waiting: '准备生成',
    unprepared: '正在创建入口',
    queued: '资源生成中',
    running: '资源生成中',
    complete: '资源已生成',
    failed: '生成失败',
  }
  return labels[resourceStatus] || '正在创建入口'
}

function normalizeTaskResourceType(resourceType, index = 0) {
  const rawType = String(resourceType || '').trim().toLowerCase()
  const aliases = {
    question_bank: 'question-bank',
    quiz: 'question-bank',
    simulator: 'mcu',
    code: 'mcu',
    'mind-map': 'mindmap',
    handout: 'document',
    'learning-document': 'document',
    'animated-lesson': 'animation',
    'learning-animation': 'animation',
    'generated-video': 'generated_video',
    generatedvideo: 'generated_video',
    'video-generator': 'generated_video',
    video_generator: 'generated_video',
    'video-generation': 'generated_video',
    'ai-video': 'generated_video',
    ai_video: 'generated_video',
    herb_model: 'herb-model',
    'herb-recognition': 'herb-model',
  }
  const normalized = aliases[rawType] || rawType
  if (['video', 'generated_video', 'animation', 'document', 'ppt', 'mindmap', 'question-bank', 'herb-model', 'mcu'].includes(normalized)) return normalized
  return 'video'
}

function taskResourceLabel(resourceType, index) {
  const labels = {
    video: '视频查找',
    generated_video: 'AI 视频生成',
    animation: '动画微课',
    document: '课程讲义',
    ppt: 'PPT生成',
    mindmap: '思维导图',
    'question-bank': '题库生成',
    'herb-model': '药材模型辨识',
    mcu: '课程讲义',
  }
  return labels[normalizeTaskResourceType(resourceType, index)]
}

function taskIcon(resourceType, index) {
  const icons = {
    video: 'book-open',
    generated_video: 'film',
    animation: 'film',
    document: 'file-text',
    ppt: 'layers',
    mindmap: 'brain',
    'question-bank': 'clipboard-check',
    'herb-model': 'scan-search',
    mcu: 'cpu',
    quiz: 'clipboard-check',
    simulator: 'cpu',
    review: 'target',
  }
  return icons[normalizeTaskResourceType(resourceType, index)] || ['target', 'brain', 'book-open', 'cpu'][index % 4]
}

function isWeekTaskViewed(node) {
  cacheVersion.value
  const cacheKey = String(node?.cacheKey || '').trim()
  if (!cacheKey) return false
  const cache = getNodeCache(cacheKey)
  if (!cache?.viewedAt || cache?.viewSource !== 'learning-path-task-open') return false
  if (String(cache.stageId || '') !== String(route.params.stageId || '')) return false
  if (String(cache.nodeId || '') !== String(node?.id || '')) return false
  const expectedProfileId = Number(pathConfig.value?.meta?.profileReportId || pathConfig.value?.meta?.activeProfileReportId || 0)
  return expectedProfileId <= 0 || Number(cache.profileReportId || 0) === expectedProfileId
}

function handleNodeCacheUpdated(event) {
  if (event?.key && event.key !== 'qianzhi-learning-path-node-results:v1') return
  cacheVersion.value += 1
}

function taskCoverStatusLabel(task) {
  if (isGeneratedVideoTask(task)) return '首图生成中'
  if (['planning', 'unprepared', 'queued', 'running'].includes(String(task?.resourceStatus || ''))) {
    return '资源生成中'
  }
  return '正在读取封面'
}

function isTaskCoverLoaded(coverKey) {
  return loadedTaskCovers.value.has(String(coverKey || ''))
}

function markTaskCoverLoaded(coverKey) {
  const key = String(coverKey || '')
  if (!key || loadedTaskCovers.value.has(key)) return
  loadedTaskCovers.value = new Set([...loadedTaskCovers.value, key])
}

function isGeneratedVideoTask(task) {
  return String(task?.resourceType || '') === 'generated_video'
}

function taskPosterUrl(task) {
  cacheVersion.value
  const taskId = String(task?.taskId || '')
  if (!taskId) return ''
  const attempt = taskPosterRetries.get(String(task?.coverKey || '')) || 0
  const url = `/api/personalized-resources/generated-videos/${encodeURIComponent(taskId)}/poster`
  return attempt ? `${url}?coverAttempt=${attempt}` : url
}

function retryTaskPoster(task) {
  const key = String(task?.coverKey || '')
  if (!key || taskPosterRetryTimers.has(key)) return
  const loaded = new Set(loadedTaskCovers.value)
  loaded.delete(key)
  loadedTaskCovers.value = loaded
  const attempt = taskPosterRetries.get(key) || 0
  const timer = window.setTimeout(() => {
    taskPosterRetryTimers.delete(key)
    taskPosterRetries.set(key, attempt + 1)
    cacheVersion.value += 1
  }, Math.min(10000, 2000 + attempt * 500))
  taskPosterRetryTimers.set(key, timer)
}

function taskCoverPreviewUrl(task) {
  if (isGeneratedVideoTask(task)) return ''
  const target = String(task?.actionRoute || '').trim()
  if (!target || /^https?:\/\//i.test(target)) return ''
  try {
    const resolved = router.resolve(target)
    return router.resolve({
      path: resolved.path,
      query: { ...resolved.query, resourcePreview: 'cover' },
      hash: resolved.hash,
    }).href
  } catch {
    return ''
  }
}

function findWeekLabel(stageId) {
  const weeks = Array.isArray(pathConfig.value?.weeks) ? pathConfig.value.weeks : []
  return weeks.find((week) => String(week?.id || '') === String(stageId || ''))?.weekLabel
}

function openCurrentWeekFromEntry() {
  if (route.name !== 'learning-path') return
  router.replace({ name: 'learning-path-stage-detail', params: { stageId: 'overview' } })
}

function formatWeekLabel(index) {
  return `第${weekNumberLabels[index - 1] || index}周`
}

function shouldAutoPlan(config) {
  if (config?.meta?.canGeneratePersonalized === false) return false
  if (['queued', 'running'].includes(String(config?.meta?.backgroundGeneration?.status || ''))) return false
  if (Number(config?.version || 1) < 2) return true
  const weeks = Array.isArray(config?.weeks) ? config.weeks : []
  if (!weeks.length) return true
  return false
}
</script>

<style scoped>
.learning-path-page {
  position: relative;
  height: calc(100vh - 72px);
  min-height: calc(100vh - 72px);
  overflow-x: hidden;
  overflow-y: auto;
  color: #111827;
  background:
    linear-gradient(180deg, rgba(255, 255, 255, 0.62), rgba(242, 243, 245, 0.94)),
    #f2f3f5;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC", "Microsoft YaHei", sans-serif;
  -webkit-overflow-scrolling: touch;
}

.learning-path-page::before {
  position: absolute;
  inset: 0;
  background:
    linear-gradient(90deg, rgba(20, 184, 166, 0.035) 1px, transparent 1px),
    linear-gradient(0deg, rgba(20, 184, 166, 0.032) 1px, transparent 1px);
  background-size: 96px 96px;
  content: "";
  opacity: 0.42;
  pointer-events: none;
}

.learning-path-page::after {
  position: absolute;
  right: -120px;
  bottom: -90px;
  width: 520px;
  height: 360px;
  background:
    linear-gradient(90deg, transparent 0 42px, rgba(20, 184, 166, 0.12) 43px 45px, transparent 46px),
    linear-gradient(0deg, transparent 0 38px, rgba(20, 184, 166, 0.09) 39px 41px, transparent 42px);
  background-size: 92px 76px;
  content: "";
  opacity: 0.2;
  pointer-events: none;
  transform: rotate(-6deg);
}

.path-shell {
  position: relative;
  z-index: 1;
  width: min(1320px, calc(100% - 56px));
  margin: 0 auto;
  padding: 34px 0 48px;
}

.back-to-week-map {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  min-height: 38px;
  margin: 0 0 18px;
  padding: 8px 13px;
  border: 1px solid #d8e1e8;
  border-radius: 7px;
  color: #334155;
  background: rgba(255, 255, 255, 0.9);
  box-shadow: 0 8px 20px rgba(15, 23, 42, 0.04);
  font: inherit;
  font-size: 13px;
  font-weight: 850;
  cursor: pointer;
  transition: border-color 0.18s ease, color 0.18s ease, transform 0.18s ease;
}

.back-to-week-map:hover {
  border-color: #8bd7c2;
  color: #0f8f70;
  transform: translateY(-1px);
}

.path-heading {
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
  gap: 28px;
  margin-bottom: 20px;
  text-align: left;
}

.path-heading p {
  margin: 0;
  color: #11a97f;
  font-size: 15px;
  font-weight: 900;
  line-height: 1;
}

.path-heading h1 {
  margin: 10px 0 8px;
  color: #0f172a;
  font-size: clamp(32px, 3.2vw, 46px);
  font-weight: 950;
  letter-spacing: 0;
  line-height: 1.08;
}

.path-heading span {
  color: #64748b;
  font-size: 15px;
  font-weight: 700;
}

.path-heading-skeleton {
  display: grid;
  gap: 12px;
  width: min(520px, 100%);
}

.path-heading-skeleton p,
.path-heading-skeleton h1,
.path-heading-skeleton span,
.path-progress-skeleton .progress-card-head span,
.path-progress-skeleton .progress-card-head strong,
.path-progress-skeleton i {
  background: linear-gradient(90deg, #e8edf2 0%, #f6f8fa 48%, #e8edf2 100%);
  background-size: 220% 100%;
  animation: pathSkeleton 1.15s ease-in-out infinite;
}

.path-heading-skeleton p {
  width: 76px;
  height: 15px;
  border-radius: 999px;
}

.path-heading-skeleton h1 {
  width: min(360px, 74vw);
  height: 48px;
  margin: 0;
  border-radius: 8px;
}

.path-heading-skeleton span {
  width: min(320px, 68vw);
  height: 16px;
  border-radius: 999px;
}

.path-progress-card {
  position: relative;
  display: grid;
  gap: 12px;
  flex: 0 0 256px;
  padding: 18px 22px;
  border: 1px solid rgba(226, 232, 240, 0.88);
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.92);
  box-shadow: 0 16px 34px rgba(15, 23, 42, 0.055);
}

.path-progress-card::after {
  position: absolute;
  right: 18px;
  bottom: 16px;
  width: 54px;
  height: 34px;
  background:
    linear-gradient(90deg, rgba(20, 184, 166, 0.13) 1px, transparent 1px),
    linear-gradient(0deg, rgba(20, 184, 166, 0.13) 1px, transparent 1px);
  background-size: 16px 16px;
  content: "";
  opacity: 0.34;
  pointer-events: none;
}

.path-progress-card div {
  display: flex;
  align-items: center;
  gap: 8px;
  color: #64748b;
  font-size: 14px;
  font-weight: 800;
}

.progress-card-head svg {
  color: #12b69a;
}

.progress-card-head span {
  margin-right: auto;
}

.path-progress-card strong {
  color: #11a97f;
  font-size: 18px;
  font-weight: 950;
}

.path-progress-skeleton .progress-card-head svg {
  color: #cbd5df;
}

.path-progress-skeleton .progress-card-head span {
  display: block;
  width: 76px;
  height: 14px;
  border-radius: 999px;
}

.path-progress-skeleton .progress-card-head strong {
  display: block;
  width: 34px;
  height: 18px;
  overflow: hidden;
  border-radius: 999px;
  color: transparent;
}

.path-progress-card i {
  display: block;
  height: 12px;
  overflow: hidden;
  border-radius: 999px;
  background: #e9eef3;
}

.path-progress-card b {
  display: block;
  height: 100%;
  border-radius: inherit;
  background: linear-gradient(90deg, #12b69a, #69d7ca);
}

.path-state {
  width: fit-content;
  margin: 0 auto 18px;
  color: #64748b;
  font-size: 13px;
  font-weight: 700;
}

.path-loading-panel {
  display: grid;
  gap: 18px;
}

.path-generation-status {
  display: flex;
  align-items: center;
  gap: 8px;
  margin: 0 0 16px;
  color: #0f766e;
  font-size: 13px;
  font-weight: 800;
}

.path-generation-status svg {
  color: #12b69a;
  animation: pathSpin 1.1s linear infinite;
}

.resource-generation-state {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr) auto;
  align-items: center;
  gap: 10px;
  margin: 0 0 16px;
  padding: 12px 14px;
  border: 1px solid #bce9dc;
  border-radius: 8px;
  background: #f2fbf7;
  color: #0f766e;
  font-size: 13px;
  font-weight: 800;
}

.path-context-state {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr) auto;
  align-items: center;
  gap: 10px;
  margin: 0 0 16px;
  padding: 12px 14px;
  border: 1px solid rgba(202, 138, 4, 0.28);
  border-radius: 8px;
  color: #854d0e;
  background: #fffbeb;
  font-size: 13px;
  font-weight: 800;
  line-height: 1.55;
}

.path-context-state button {
  min-height: 34px;
  padding: 0 12px;
  border: 1px solid rgba(180, 83, 9, 0.24);
  border-radius: 6px;
  color: #7c2d12;
  background: #ffffff;
  font: inherit;
  white-space: nowrap;
  cursor: pointer;
}

.resource-generation-state svg {
  animation: pathSpin 1.1s linear infinite;
}

.resource-generation-state.failed {
  border-color: #fecaca;
  background: #fff7f7;
  color: #b42318;
}

.resource-generation-state.failed svg {
  animation: none;
}

.resource-generation-state button {
  border: 0;
  background: transparent;
  color: inherit;
  font: inherit;
  cursor: pointer;
}

.week-rail {
  position: relative;
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(118px, 1fr));
  align-items: start;
  gap: 0;
  margin-bottom: 18px;
  padding: 14px 28px 12px;
  border: 1px solid rgba(226, 232, 240, 0.88);
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.92);
  box-shadow: 0 14px 34px rgba(15, 23, 42, 0.045);
}

.week-rail::before,
.week-rail > i {
  content: "";
  position: absolute;
  left: 70px;
  right: 70px;
  top: 31px;
  height: 2px;
  border-radius: 999px;
}

.week-rail::before {
  background: #dbe4eb;
}

.week-rail > i {
  right: auto;
  width: 0;
  max-width: calc(100% - 140px);
  background: linear-gradient(90deg, #13b99b, #5fd6ca);
}

.rail-node {
  position: relative;
  z-index: 1;
  display: grid;
  justify-items: center;
  gap: 7px;
  min-height: 44px;
  padding: 0 !important;
  border: 0 !important;
  border-radius: 0 !important;
  background: transparent !important;
  box-shadow: none !important;
  color: #344256;
  font: inherit;
  text-decoration: none;
  cursor: pointer;
}

.rail-node span,
.rail-dot {
  display: grid;
  place-items: center;
  flex: 0 0 auto;
  width: 34px;
  height: 34px;
  border: 2px solid #94a3b8;
  border-radius: 50%;
  background: #ffffff;
  box-shadow: 0 0 0 6px #ffffff;
  color: #7d8b9b;
}

.rail-node b {
  font-size: 13px;
  font-weight: 800;
}

.rail-node.status-done span,
.rail-node.status-completed span,
.rail-node.status-current span,
.rail-node.status-active span,
.rail-node.status-progress span {
  border-color: #12b69a;
  background: #ffffff;
  color: #12a884;
}

.rail-placeholder {
  cursor: default;
}

.week-rail-skeleton {
  grid-template-columns: repeat(6, minmax(0, 1fr));
}

.week-rail-skeleton .rail-node {
  cursor: default;
}

.week-rail-skeleton .rail-dot,
.week-card-skeleton .week-icon,
.week-card-skeleton .week-copy small,
.week-card-skeleton .week-copy strong,
.week-card-skeleton .week-copy em {
  background: linear-gradient(90deg, #e8edf2 0%, #f6f8fa 48%, #e8edf2 100%);
  background-size: 220% 100%;
  animation: pathSkeleton 1.15s ease-in-out infinite;
}

.week-rail-skeleton .rail-dot {
  border-color: transparent;
  box-shadow: 0 0 0 6px #ffffff;
}

.week-rail-skeleton .rail-node b {
  width: 44px;
  height: 12px;
  border-radius: 999px;
  background: #edf2f6;
}

.week-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 14px;
  transition: opacity 0.18s ease;
}

.task-reveal-enter-active,
.task-reveal-move {
  transition: opacity 0.28s ease, transform 0.28s ease;
}

.task-reveal-enter-from {
  opacity: 0;
  transform: translateY(12px);
}

.week-grid.muted {
  opacity: 0.58;
}

.week-card {
  --tone: #16b98d;
  --tone-soft: #e7f8ef;
  position: relative;
  display: grid;
  grid-template-columns: 62px minmax(0, 1fr) auto 26px;
  align-items: center;
  gap: 16px;
  min-height: 106px;
  padding: 18px 22px !important;
  border: 1px solid rgba(226, 232, 240, 0.9) !important;
  border-radius: 8px !important;
  color: #0f172a !important;
  background: rgba(255, 255, 255, 0.96) !important;
  box-shadow: 0 14px 34px rgba(15, 23, 42, 0.05) !important;
  cursor: pointer;
  font: inherit;
  isolation: isolate;
  overflow: hidden;
  text-align: left;
  text-decoration: none;
  transition:
    transform 0.3s cubic-bezier(0.22, 1, 0.36, 1),
    box-shadow 0.3s ease,
    border-color 0.3s ease;
}

.week-card::before {
  position: absolute;
  inset: 0;
  z-index: 0;
  background: linear-gradient(108deg, transparent 24%, rgba(255, 255, 255, 0.88) 45%, transparent 66%);
  content: "";
  opacity: 0;
  pointer-events: none;
  transform: translateX(-110%);
  transition: transform 0.7s ease, opacity 0.24s ease;
}

.week-card::after {
  position: absolute;
  right: -16px;
  bottom: -20px;
  z-index: 0;
  width: 128px;
  height: 86px;
  background:
    linear-gradient(90deg, transparent 0 22px, rgba(20, 184, 166, 0.17) 23px 24px, transparent 25px),
    linear-gradient(0deg, transparent 0 18px, rgba(20, 184, 166, 0.15) 19px 20px, transparent 21px);
  background-size: 42px 34px;
  content: "";
  opacity: 0.22;
  pointer-events: none;
  transition: opacity 0.3s ease, transform 0.45s cubic-bezier(0.22, 1, 0.36, 1);
}

.week-card > * {
  position: relative;
  z-index: 1;
}

.week-card:hover:not(:disabled):not(.placeholder-card):not(.week-card-skeleton) {
  border-color: rgba(17, 185, 141, 0.34) !important;
  box-shadow: 0 20px 44px rgba(15, 23, 42, 0.12) !important;
  transform: translateY(-6px) scale(1.008) !important;
}

.week-card:hover:not(:disabled):not(.placeholder-card):not(.week-card-skeleton)::before {
  opacity: 0.74;
  transform: translateX(110%);
}

.week-card:hover:not(:disabled):not(.placeholder-card):not(.week-card-skeleton)::after {
  opacity: 0.48;
  transform: translate(-5px, -4px) scale(1.08);
}

.week-card:disabled {
  cursor: wait;
  opacity: 0.78;
}

.week-card:disabled:hover {
  border-color: rgba(226, 232, 240, 0.9) !important;
  box-shadow: 0 14px 34px rgba(15, 23, 42, 0.05) !important;
  transform: none;
}

.week-card-skeleton {
  cursor: default;
  pointer-events: none;
}

.week-card-skeleton:hover {
  border-color: rgba(226, 232, 240, 0.9) !important;
  box-shadow: 0 14px 34px rgba(15, 23, 42, 0.05) !important;
  transform: none;
}

.week-card-skeleton .week-copy small {
  width: 54px;
  height: 13px;
  border-radius: 999px;
}

.week-card-skeleton .week-copy strong {
  width: min(72%, 220px);
  height: 24px;
  border-radius: 6px;
}

.week-card-skeleton .week-copy em {
  width: min(88%, 280px);
  height: 14px;
  border-radius: 999px;
}

.week-icon {
  display: grid;
  place-items: center;
  width: 52px;
  height: 52px;
  border-radius: 14px;
  color: var(--tone);
  background: var(--tone-soft);
  transition:
    transform 0.38s cubic-bezier(0.22, 1, 0.36, 1),
    box-shadow 0.3s ease;
}

.week-card:hover:not(:disabled):not(.placeholder-card):not(.week-card-skeleton) .week-icon {
  box-shadow: 0 9px 20px color-mix(in srgb, var(--tone) 18%, transparent);
  transform: rotate(-4deg) scale(1.08);
}

.week-copy {
  display: grid;
  min-width: 0;
  gap: 8px;
}

.week-copy small {
  color: var(--tone);
  font-size: 15px;
  font-weight: 900;
  line-height: 1;
}

.week-copy strong {
  overflow-wrap: anywhere;
  color: #111827;
  font-size: 22px;
  font-weight: 950;
  letter-spacing: 0;
  line-height: 1.15;
}

.week-copy em {
  overflow: hidden;
  color: #718096;
  font-size: 13px;
  font-style: normal;
  font-weight: 700;
  line-height: 1.45;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.week-status {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  align-self: start;
  padding: 6px 10px;
  border-radius: 999px;
  background: #f0f5f8;
  color: #7a8899;
  font-size: 12px;
  font-weight: 900;
  white-space: nowrap;
}

.week-status svg {
  flex: 0 0 auto;
}

.week-watermark {
  position: absolute;
  right: 42px;
  bottom: 14px;
  z-index: 0;
  color: var(--tone);
  opacity: 0.045;
  pointer-events: none;
  transition: opacity 0.3s ease, transform 0.45s cubic-bezier(0.22, 1, 0.36, 1);
}

.week-card:hover:not(:disabled):not(.placeholder-card):not(.week-card-skeleton) .week-watermark {
  opacity: 0.11;
  transform: rotate(-8deg) scale(1.14);
}

.status-done .week-status,
.status-completed .week-status {
  border-color: #86efac;
  background: #dcfce7;
  color: #166534;
}

.status-current .week-status,
.status-active .week-status,
.status-progress .week-status {
  border-color: #93c5fd;
  background: #dbeafe;
  color: #1d4ed8;
}

.status-waiting .week-status {
  border-color: #f4cf72;
  background: #fff4cc;
  color: #805400;
}

.status-failed .week-status {
  border-color: #fca5a5;
  background: #fee2e2;
  color: #b42318;
}

.week-arrow {
  justify-self: end;
  color: #94a3b8;
  transition: color 0.3s ease, transform 0.3s cubic-bezier(0.22, 1, 0.36, 1);
}

.week-card:hover:not(:disabled):not(.placeholder-card):not(.week-card-skeleton) .week-arrow {
  color: var(--tone);
  transform: translateX(5px);
}

.week-card.task-resource-card {
  --tone-border: #dfe4e2;
  display: grid;
  grid-template-columns: 1fr;
  grid-template-rows: 202px minmax(0, 1fr);
  gap: 0;
  width: 100%;
  height: 292px;
  min-height: 292px;
  padding: 0 !important;
  overflow: hidden;
  border-color: var(--tone-border) !important;
  background: #ffffff !important;
  box-shadow: none !important;
  transition: transform 160ms ease, border-color 160ms ease, box-shadow 160ms ease;
}

.week-card.task-resource-card::before,
.week-card.task-resource-card::after {
  display: none;
}

.week-card.task-resource-card:hover:not(:disabled):not(.placeholder-card):not(.week-card-skeleton) {
  border-color: #a9beb5 !important;
  box-shadow: 0 8px 22px rgba(31, 55, 46, 0.08) !important;
  transform: translateY(-2px) !important;
}

.week-card.task-resource-card:focus-visible {
  outline: 3px solid var(--tone);
  outline-offset: 3px;
}

.week-card.task-resource-card:disabled,
.week-card.task-resource-card:disabled:hover {
  opacity: 1;
  border-color: var(--tone-border) !important;
  background: #ffffff !important;
  box-shadow: none !important;
  transform: none !important;
}

.task-resource-cover {
  position: relative;
  display: block;
  width: 100%;
  height: 202px;
  overflow: hidden;
  border-bottom: 1px solid #e1e6e4;
  background: #f1f4f2;
  isolation: isolate;
}

.task-cover-loading {
  position: absolute;
  inset: 0;
  z-index: 0;
  display: grid;
  place-items: center;
  color: var(--tone);
  background: #f1f4f2;
}

.task-cover-loading small {
  position: absolute;
  right: 12px;
  bottom: 10px;
  color: #75817c;
  font-size: 11px;
  font-weight: 650;
}

.task-cover-loading.hidden {
  visibility: hidden;
}

.task-resource-live-cover {
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

.task-resource-live-cover.loaded {
  opacity: 1;
}

.task-resource-cover img {
  position: absolute;
  inset: 0;
  z-index: 1;
  width: 100%;
  height: 100%;
  border: 0;
  opacity: 0;
  object-fit: cover;
  transition: opacity 180ms ease;
}

.task-resource-cover img.loaded {
  opacity: 1;
}

.task-resource-copy {
  display: grid;
  min-width: 0;
  align-content: center;
  gap: 5px;
  padding: 12px 14px 13px;
}

.task-resource-copy strong {
  display: -webkit-box;
  overflow: hidden;
  color: #1c2723;
  font-size: 17px;
  font-weight: 750;
  line-height: 1.35;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
}

.task-resource-copy small {
  overflow: hidden;
  color: #6f7d77;
  font-size: 12px;
  font-weight: 650;
  line-height: 1.4;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.task-resource-card[data-resource-type="video"] {
  --tone: #0e7490;
  --tone-soft: #e8f8fb;
  --tone-border: #9ed7e2;
}

.task-resource-card[data-resource-type="ppt"] {
  --tone: #1d4ed8;
  --tone-soft: #edf3ff;
  --tone-border: #b8caf5;
}

.task-resource-card[data-resource-type="mindmap"] {
  --tone: #6d28d9;
  --tone-soft: #f3efff;
  --tone-border: #d3c0f5;
}

.task-resource-card[data-resource-type="question-bank"] {
  --tone: #b42318;
  --tone-soft: #fff0ee;
  --tone-border: #efb7b1;
}

.task-resource-card[data-resource-type="herb-model"] {
  --tone: #9f2d35;
  --tone-soft: #fff0f1;
  --tone-border: #e7b3b7;
}

.task-resource-card[data-resource-type="mcu"] {
  --tone: #8a5a00;
  --tone-soft: #fff7df;
  --tone-border: #e3ca83;
}

.task-resource-card[data-resource-type="generated_video"] {
  --tone: #be185d;
  --tone-soft: #fff0f6;
  --tone-border: #efb5cd;
}

.placeholder-card {
  color: #64748b !important;
  background: rgba(255, 255, 255, 0.55) !important;
  border-style: dashed !important;
  cursor: default;
  box-shadow: none !important;
  grid-template-columns: 62px minmax(0, 1fr);
}

.placeholder-card::after {
  opacity: 0.14;
}

.placeholder-card .week-icon {
  color: #64748b;
  background: #eef2f7;
}

.placeholder-lock {
  position: absolute;
  right: 22px;
  bottom: 22px;
  color: #94a3b8;
}

.placeholder-card .week-copy small,
.placeholder-card .week-copy strong {
  color: #64748b;
}

.tone-green {
  --tone: #16b98d;
  --tone-soft: #e7f8ef;
}

.tone-blue {
  --tone: #2563eb;
  --tone-soft: #eaf1ff;
}

.tone-gold {
  --tone: #d97706;
  --tone-soft: #fff4d7;
}

.tone-purple {
  --tone: #7c3aed;
  --tone-soft: #f1ebff;
}

.tone-cyan {
  --tone: #0891b2;
  --tone-soft: #e5f8fb;
}

.tone-orange {
  --tone: #ea580c;
  --tone-soft: #fff0e7;
}

.status-locked {
  opacity: 0.92;
}

.path-continuation {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-top: 20px;
  padding: 16px 0 4px;
  border-top: 1px solid #d8e1e5;
}

.path-continuation > span {
  min-width: 0;
  flex: 1;
}

.path-continuation strong,
.path-continuation small {
  display: block;
}

.path-continuation strong {
  color: #23302e;
  font-size: 14px;
}

.path-continuation small {
  margin-top: 4px;
  color: #6d7a77;
  font-size: 12px;
  line-height: 1.5;
}

.path-continuation button {
  min-height: 38px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  padding: 0 13px;
  border-radius: 6px;
  font: inherit;
  font-size: 12px;
  font-weight: 800;
  cursor: pointer;
}

.next-week-button {
  border: 1px solid #167b61;
  color: #fff;
  background: #167b61;
}

.assessment-button {
  border: 1px solid #cbd6d2;
  color: #3d514b;
  background: #fff;
}

.path-continuation button:disabled {
  cursor: wait;
  opacity: 0.65;
}

@keyframes pathSkeleton {
  0% {
    background-position: 120% 0;
  }

  100% {
    background-position: -120% 0;
  }
}

@keyframes pathSpin {
  to {
    transform: rotate(360deg);
  }
}

@media (max-width: 1120px) {
  .path-heading {
    align-items: stretch;
    flex-direction: column;
  }

  .path-progress-card {
    flex-basis: auto;
    width: min(360px, 100%);
  }

  .week-rail {
    grid-template-columns: repeat(4, minmax(0, 1fr));
    row-gap: 16px;
  }

  .week-rail::before,
  .week-rail > i {
    display: none;
  }

  .week-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 720px) {
  .path-shell {
    width: min(100% - 28px, 520px);
    padding: 96px 0 116px;
  }

  .path-heading h1 {
    font-size: 34px;
  }

  .week-rail {
    grid-template-columns: repeat(2, minmax(0, 1fr));
    padding: 16px;
  }

  .week-grid {
    grid-template-columns: 1fr;
  }

  .week-card {
    grid-template-columns: 56px minmax(0, 1fr) 28px;
    min-height: 116px;
    padding: 22px !important;
  }

  .week-status {
    grid-column: 2;
    width: fit-content;
  }

  .week-copy strong {
    font-size: 23px;
  }

  .path-continuation {
    align-items: stretch;
    flex-direction: column;
  }
}

@media (prefers-reduced-motion: reduce) {
  .week-card,
  .week-card::before,
  .week-card::after,
  .week-icon,
  .week-watermark,
  .week-arrow {
    transition: none !important;
  }

  .week-card:hover:not(:disabled) {
    transform: none !important;
  }
}
</style>
