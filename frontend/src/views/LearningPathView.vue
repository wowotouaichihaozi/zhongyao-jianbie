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
          <p>{{ displayMeta.eyebrow }}</p>
          <h1>{{ displayMeta.title }}</h1>
          <span>{{ pageSubtitle }}</span>
        </div>
        <aside class="path-progress-card" :class="{ 'path-progress-skeleton': loading }" aria-label="学习路径总进度">
          <div class="progress-card-head">
            <Activity :size="16" stroke-width="2.4" aria-hidden="true" />
            <span>{{ loading ? '' : (isWeekTaskPage ? '本周进度' : '总进度') }}</span>
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
        <div v-if="!hasActiveLearningProfile" class="path-context-state no-profile-state" role="status">
          <CircleAlert :size="17" stroke-width="2.3" aria-hidden="true" />
          <span>当前没有学习画像，请先完成学习画像后再生成个性化周任务。</span>
          <button type="button" @click="router.push('/learning-profile')">完成学习画像</button>
        </div>

        <div v-if="hasActiveLearningProfile && planningRemaining" class="path-generation-status" role="status">
          <Activity :size="16" stroke-width="2.4" aria-hidden="true" />
          <span>第一周已生成，正在根据学习画像补全后续周任务与资源...</span>
        </div>

        <div v-if="hasActiveLearningProfile && isWeekTaskPage && pathNotice" class="path-context-state" role="status">
          <CircleAlert :size="17" stroke-width="2.3" aria-hidden="true" />
          <span>{{ pathNotice }}</span>
          <button type="button" @click="handlePathNoticeAction">{{ pathNoticeActionLabel }}</button>
        </div>

        <div
          v-if="hasActiveLearningProfile && isWeekTaskPage && (resourcePreparing || resourcePrepareError)"
          class="resource-generation-state"
          :class="{ failed: resourcePrepareError }"
          role="status"
        >
          <CircleAlert v-if="resourcePrepareError" :size="17" stroke-width="2.3" aria-hidden="true" />
          <LoaderCircle v-else :size="17" stroke-width="2.3" aria-hidden="true" />
          <span>{{ resourcePrepareError || resourcePreparationText }}</span>
          <button v-if="resourcePrepareError" type="button" @click="prepareWeekResources(String(route.params.stageId || ''))">
            重试
          </button>
        </div>

        <div v-if="hasActiveLearningProfile" class="week-rail" :aria-label="isWeekTaskPage ? '本周任务进度' : '周学习进度'">
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

        <TransitionGroup v-if="hasActiveLearningProfile" name="task-reveal" tag="div" class="week-grid">
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
            :style="isWeekTaskPage ? taskCardColorStyle(week, weekIndex) : undefined"
            :aria-label="`${week.weekLabel}${week.resourceLabel ? ` ${week.resourceLabel}` : ''} ${week.title}`"
            :disabled="weekEntryTag(week) === 'button' ? (isWeekTaskPage && !week.actionRoute) : undefined"
            @click="openWeek(week, $event)"
          >
            <span class="week-icon" aria-hidden="true">
              <component :is="resolveIcon(week.icon)" :size="28" stroke-width="2.1" />
            </span>
            <span class="week-copy">
              <small>
                {{ week.weekLabel }}
                <template v-if="week.resourceLabel"> · {{ week.resourceLabel }}</template>
              </small>
              <strong>{{ week.title }}</strong>
              <em>{{ week.description }}</em>
            </span>
            <span class="week-status">
              <component :is="statusIcon(week.visualStatus || week.status)" :size="14" stroke-width="2.4" aria-hidden="true" />
              {{ week.statusText || statusLabel(week.status) }}
            </span>
            <component class="week-watermark" :is="resolveIcon(week.icon)" :size="76" stroke-width="1.35" aria-hidden="true" />
            <ChevronRight class="week-arrow" :size="24" stroke-width="2.2" aria-hidden="true" />
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
  LoaderCircle,
  MoreHorizontal,
  Rocket,
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

const router = useRouter()
const route = useRoute()
const loading = ref(false)
const planning = ref(false)
const planningRemaining = ref(false)
const pathConfig = ref(cloneLearningPathConfig())
const taskStage = ref(createFallbackTaskStage(String(route.params.stageId || '')))
const resourcePreparing = ref(false)
const resourcePrepareError = ref('')
let resourcePollTimer = null
let resourcePreparationRun = 0
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
}

const pageMeta = computed(() => ({
  ...defaultLearningPathConfig.meta,
  ...(pathConfig.value?.meta || {}),
}))

const isWeekTaskPage = computed(() => Boolean(route.params.stageId) && route.name === 'learning-path-week-detail')
const hasActiveLearningProfile = computed(() => Number(pathConfig.value?.meta?.activeProfileReportId || 0) > 0)
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
  return {
    ...pageMeta.value,
    eyebrow: weekLabel,
    title: `${weekLabel}具体学习任务`,
    placeholderTitle: '',
    placeholderWeekLabel: '',
  }
})

const pageSubtitle = computed(() => {
  if (isWeekTaskPage.value) {
    return String(taskStage.value?.hint || '按顺序完成本周任务，并进入对应资源完成学习与验证。')
  }
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
        description: String(node.description || node.desc || '完成本任务并记录学习成果。'),
        actionRoute: taskRoute.includes('xzTask=') ? taskRoute : '',
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
  (isWeekTaskPage.value ? allWeekTaskNodes.value : visibleWeeks.value)
    .filter((item) => ['done', 'completed', 'current', 'active', 'progress'].includes(String(item?.state || item?.status || '')))
    .length
))

const progressPercent = computed(() => {
  const total = (isWeekTaskPage.value ? allWeekTaskNodes.value.length : visibleWeeks.value.length) || 1
  return Math.min(100, Math.round((activeWeekCount.value / total) * 100))
})

const railProgressPercent = computed(() => {
  const itemCount = isWeekTaskPage.value ? allWeekTaskNodes.value.length : visibleWeeks.value.length
  const total = Math.max(itemCount - 1, 1)
  const activeIndex = Math.max(0, activeWeekCount.value - 1)
  return Math.min(100, Math.round((activeIndex / total) * 100))
})

onMounted(loadLearningPathConfig)

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
  cancelResourcePreparation()
  stopResourcePolling()
})

async function loadLearningPathConfig() {
  const hasVisibleData = isWeekTaskPage.value
    ? Array.isArray(taskStage.value?.nodes) && taskStage.value.nodes.length > 0
    : visibleWeeks.value.length > 0
  loading.value = !hasVisibleData
  planning.value = false
  planningRemaining.value = false
  try {
    const config = await getLearningPathConfig()
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
      loading.value = false
      planning.value = false
      await generateRemainingWeeks(normalizedConfig, totalWeeks)
    } else {
      pathConfig.value = normalizedConfig
    }
  } catch (error) {
    console.warn('Failed to load learning path config, using fallback data.', error)
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

async function generateRemainingWeeks(firstWeekConfig, totalWeeks) {
  if (totalWeeks <= 1) return
  planningRemaining.value = true
  let currentConfig = firstWeekConfig
  try {
    // Preserve visible progress: every planner call creates exactly one next week.
    for (let week = 2; week <= totalWeeks; week += 1) {
      await new Promise(resolve => requestAnimationFrame(resolve))
      const result = await generateLearningPath({
        persist: true,
        useLatestProfile: true,
        generationPhase: 'remaining-weeks',
        weekStart: week,
        weekCount: 1,
        totalWeeks,
        existingConfig: currentConfig,
        useLLM: true,
      })
      if (result?.config) {
        currentConfig = normalizeConfig(result.config)
        pathConfig.value = currentConfig
      }
    }
  } catch (error) {
    console.warn('Failed to generate remaining learning-path weeks.', error)
  } finally {
    planningRemaining.value = false
  }
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
  return isWeekTaskPage.value && week?.actionRoute ? 'a' : 'button'
}

function weekEntryHref(week) {
  if (!isWeekTaskPage.value || !week?.actionRoute) return null
  return /^https?:\/\//i.test(week.actionRoute)
    ? week.actionRoute
    : router.resolve(week.actionRoute).href
}

function openWeek(week, event) {
  if (!week?.id) return
  if (isWeekTaskPage.value) {
    if (!week.actionRoute) {
      if (!resourcePreparing.value && pathConfig.value?.meta?.canPrepareResources !== false) {
        void prepareWeekResources(String(route.params.stageId || ''))
      }
      return
    }
    if (event?.currentTarget?.tagName === 'A') return
    window.open(weekEntryHref(week), '_blank', 'noopener,noreferrer')
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
  }
  const normalized = aliases[rawType] || rawType
  if (['video', 'generated_video', 'animation', 'document', 'ppt', 'mindmap', 'question-bank', 'mcu'].includes(normalized)) return normalized
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
    mcu: '单片机实验',
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
    mcu: 'cpu',
    quiz: 'clipboard-check',
    simulator: 'cpu',
    review: 'target',
  }
  return icons[normalizeTaskResourceType(resourceType, index)] || ['target', 'brain', 'book-open', 'cpu'][index % 4]
}

const TASK_CARD_COLOR_PALETTE = [
  { tone: '#0b6f66', soft: '#ccefe6', surface: '#e7f7f2', border: '#51b8a5' },
  { tone: '#1d4ed8', soft: '#dbe7ff', surface: '#edf2ff', border: '#7399ee' },
  { tone: '#6d28d9', soft: '#e8dcff', surface: '#f2ecff', border: '#a37ae8' },
  { tone: '#a92b22', soft: '#ffdcd7', surface: '#fff0ed', border: '#e17d73' },
  { tone: '#805400', soft: '#ffeab5', surface: '#fff5d9', border: '#d3a43d' },
  { tone: '#b51759', soft: '#ffd8e8', surface: '#ffedf5', border: '#e36b9a' },
  { tone: '#4338ca', soft: '#dedfff', surface: '#eeeeff', border: '#8c8fe3' },
  { tone: '#047857', soft: '#cff1df', surface: '#e9f8f0', border: '#58bd91' },
  { tone: '#9621a4', soft: '#f3d6f8', surface: '#faecfc', border: '#ce70d8' },
  { tone: '#155e75', soft: '#d2edf4', surface: '#e8f6fa', border: '#61afc1' },
]

function taskCardColorStyle(week, index) {
  const order = Math.max(1, Number(week?.order || index + 1))
  const palette = TASK_CARD_COLOR_PALETTE[(order - 1) % TASK_CARD_COLOR_PALETTE.length]
  return {
    '--tone': palette.tone,
    '--tone-soft': palette.soft,
    '--tone-surface': palette.surface,
    '--tone-border': palette.border,
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
  --tone-border: #b7c8d1;
  --tone-surface: #f2f6f8;
  border-color: var(--tone-border) !important;
  background: var(--tone-surface) !important;
  box-shadow:
    inset 6px 0 0 var(--tone),
    inset 0 4px 0 var(--tone),
    0 14px 34px rgba(15, 23, 42, 0.075) !important;
  transition: background-color 0.2s ease, border-color 0.2s ease, box-shadow 0.2s ease;
}

.week-card.task-resource-card::before,
.week-card.task-resource-card::after {
  display: none;
}

.week-card.task-resource-card .week-icon {
  background: var(--tone-soft);
  box-shadow:
    inset 0 0 0 2px color-mix(in srgb, var(--tone) 34%, transparent),
    0 8px 18px color-mix(in srgb, var(--tone) 13%, transparent);
}

.week-card.task-resource-card .week-copy small {
  width: fit-content;
  padding: 5px 8px;
  border: 1px solid color-mix(in srgb, var(--tone) 34%, transparent);
  border-radius: 4px;
  background: rgba(255, 255, 255, 0.72);
}

.week-card.task-resource-card .week-status {
  border: 1px solid rgba(255, 255, 255, 0.76);
  box-shadow: 0 4px 12px rgba(15, 23, 42, 0.06);
}

.week-card.task-resource-card:hover:not(:disabled):not(.placeholder-card):not(.week-card-skeleton) {
  border-color: var(--tone) !important;
  box-shadow:
    inset 6px 0 0 var(--tone),
    inset 0 4px 0 var(--tone),
    0 18px 40px color-mix(in srgb, var(--tone) 18%, transparent) !important;
  transform: none !important;
}

.week-card.task-resource-card:hover:not(:disabled) .week-icon,
.week-card.task-resource-card:hover:not(:disabled) .week-watermark,
.week-card.task-resource-card:hover:not(:disabled) .week-arrow {
  transform: none;
}

.week-card.task-resource-card:hover:not(:disabled) .week-arrow {
  color: var(--tone);
}

.week-card.task-resource-card:focus-visible {
  outline: 3px solid var(--tone);
  outline-offset: 3px;
}

.week-card.task-resource-card:disabled,
.week-card.task-resource-card:disabled:hover {
  opacity: 1;
  border-color: var(--tone-border) !important;
  background: var(--tone-surface) !important;
  box-shadow:
    inset 6px 0 0 var(--tone),
    inset 0 4px 0 var(--tone),
    0 14px 34px rgba(15, 23, 42, 0.075) !important;
  transform: none !important;
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
