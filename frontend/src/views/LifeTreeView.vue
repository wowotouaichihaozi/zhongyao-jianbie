<template>
  <main class="life-tree-page">
    <LifeTreeGrowthScene
      :key="sceneKey"
      v-if="treeModel"
      :model="treeModel"
      :selected-id="selectedId"
      :reset-token="resetToken"
      :growth-from="growthFrom"
      @select="selectNode"
      @ready="sceneReady = true"
      @error="sceneError = $event"
    />

    <header class="tree-heading">
      <div>
        <span class="tree-kicker"><TreePine :size="16" />画像驱动的六周成长</span>
        <h1>学习成长树</h1>
        <p>完成每周真实学习，果实才会生长。</p>
      </div>
      <div class="scene-controls" aria-label="三维场景控制">
        <button type="button" title="重置视角" aria-label="重置视角" @click="resetToken += 1">
          <Focus :size="18" />
        </button>
        <button type="button" title="刷新学习证据" aria-label="刷新学习证据" :disabled="loading || refreshing" @click="loadTree()">
          <RefreshCcw :class="{ spinning: loading || refreshing }" :size="18" />
        </button>
      </div>
    </header>

    <Transition name="growth-feedback">
      <div v-if="growthFeedback" class="growth-feedback" role="status" aria-live="polite">
        <Sparkles :size="16" /><span>{{ growthFeedback }}</span>
      </div>
    </Transition>

    <section v-if="treeModel" class="tree-status" aria-label="当前学习画像">
      <header class="profile-summary-heading">
        <div>
          <span><TreePine :size="15" />学习画像</span>
          <strong>{{ treeModel.profile.label }}</strong>
        </div>
        <button type="button" class="profile-link" aria-label="查看画像六维能力详情" @click="selectNode(treeModel.profile.id)">
          {{ profileConfidenceLabel }}<ChevronRight :size="14" />
        </button>
      </header>

      <div class="profile-radar-stage">
        <svg viewBox="0 0 240 210" role="img" aria-label="当前画像六维能力雷达图">
          <polygon
            v-for="level in radarLevels"
            :key="`profile-grid-${level}`"
            :points="radarGridPoints(level)"
            class="profile-radar-grid"
          />
          <line
            v-for="(_, index) in treeModel.profileDimensions"
            :key="`profile-axis-${index}`"
            x1="120"
            y1="96"
            :x2="radarPoint(index, 5).x"
            :y2="radarPoint(index, 5).y"
            class="profile-radar-axis"
          />
          <polygon :points="profileRadarPoints" class="profile-radar-value" />
          <circle
            v-for="(dimension, index) in treeModel.profileDimensions"
            :key="`profile-score-${dimension.id}`"
            :cx="radarPoint(index, dimension.score).x"
            :cy="radarPoint(index, dimension.score).y"
            r="3"
            class="profile-radar-dot"
          />
          <text
            v-for="(dimension, index) in treeModel.profileDimensions"
            :key="`profile-label-${dimension.id}`"
            :x="radarLabelPoint(index).x"
            :y="radarLabelPoint(index).y"
            :text-anchor="radarLabelAnchor(index)"
            class="profile-radar-label"
          >
            <tspan :x="radarLabelPoint(index).x">{{ dimension.label }}</tspan>
            <tspan :x="radarLabelPoint(index).x" dy="13" class="profile-radar-score">{{ profileScore(dimension.score) }}</tspan>
          </text>
        </svg>
      </div>

      <div class="profile-dimension-list" aria-label="画像六维能力分值">
        <div v-for="dimension in treeModel.profileDimensions" :key="dimension.id" :style="dimensionBarStyle(dimension.score)">
          <span>{{ dimension.label }}</span><small>{{ profileScore(dimension.score) }}</small><i><b></b></i>
        </div>
      </div>

      <footer class="profile-summary-footer">
        <span><ShieldCheck :size="13" />{{ treeModel.stats.evidenceCount }} 条画像证据</span>
        <RouterLink to="/learning-profile">完整画像<ArrowRight :size="13" /></RouterLink>
      </footer>
      <div class="sync-note" :class="{ syncing: refreshing }" :title="syncLabel">
        <RefreshCcw :class="{ spinning: refreshing }" :size="11" />
        <span>{{ shortSyncLabel }}</span>
        <em v-if="lastGrowth">{{ shortGrowthLabel }}</em>
      </div>
    </section>

    <nav v-if="treeModel" class="week-path" aria-label="六周果实成熟度">
      <span class="week-path-heading"><b>六周路径</b><small>{{ treeModel.stats.generatedWeeks }}/6 已生成</small></span>
      <button
        v-for="node in growthSignals"
        :key="node.id"
        type="button"
        :class="{ current: node.recommended, selected: node.id === selectedId, complete: node.progress >= 80 }"
        :style="fruitMarkerStyle(node)"
        :aria-label="`${node.weekLabel}，成熟度 ${Math.round(node.progress)}%`"
        @click="selectNode(node.id)"
      >
        <i><span></span></i>
        <span><b><span>第</span>{{ node.order }}<span>周</span></b><em>{{ node.available ? `${Math.round(node.progress)}%` : '--' }}</em></span>
      </button>
    </nav>

    <aside v-if="selectedNode" class="node-detail" aria-live="polite">
      <button class="detail-close" type="button" title="关闭节点详情" aria-label="关闭节点详情" @click="selectedId = ''">
        <X :size="18" />
      </button>
      <header class="detail-heading">
        <span class="detail-eyebrow">{{ selectedNode.eyebrow || kindLabel(selectedNode.kind) }}</span>
        <h2>{{ selectedNode.label }}</h2>
      </header>

      <section v-if="selectedNode.kind === 'fruit'" class="fruit-inspector" :style="fruitMarkerStyle(selectedNode)">
        <div class="week-number"><small>WEEK</small><strong>{{ String(selectedNode.order).padStart(2, '0') }}</strong></div>
        <div>
          <strong>{{ wholePercent(selectedNode.progress) }}<small>%</small></strong>
          <span :class="`status-${selectedNode.recommended ? 'recommended' : selectedNode.status}`">
            {{ selectedNode.recommended ? '当前学习周' : selectedNode.statusLabel }}
          </span>
          <i class="detail-progress"><b></b></i>
        </div>
      </section>
      <section v-else class="profile-inspector">
        <TreePine :size="26" /><div><strong>{{ selectedNode.evidenceCount || 0 }}</strong><span>画像证据</span></div>
      </section>

      <section v-if="selectedNode.kind === 'profile'" class="profile-root-list" aria-label="画像六维能力根系">
        <div
          v-for="dimension in treeModel.profileDimensions"
          :key="dimension.id"
          :style="dimensionBarStyle(dimension.score)"
        >
          <span>{{ dimension.label }}</span><i><b></b></i><small>{{ dimension.score === null ? '--' : Number(dimension.score).toFixed(1) }}</small>
        </div>
      </section>

      <dl v-if="selectedNode.kind === 'fruit'" class="evidence-metrics">
        <div><dt>学习完成</dt><dd>{{ selectedNode.completedNodes || 0 }}<small>/{{ selectedNode.totalNodes || 0 }}</small></dd></div>
        <div><dt>资源备好</dt><dd>{{ selectedNode.preparedNodes || 0 }}</dd></div>
        <div><dt>反馈完成</dt><dd>{{ selectedNode.feedbackCompletedNodes || 0 }}</dd></div>
      </dl>

      <p v-if="selectedNode.description" class="detail-description">{{ selectedNode.description }}</p>
      <details class="evidence-disclosure">
        <summary><ShieldCheck :size="15" /><span>查看成熟依据</span><ChevronRight :size="15" /></summary>
        <div>
          <section><strong>成熟度依据</strong><p>{{ selectedNode.evidence }}</p></section>
          <section v-if="selectedNode.reason"><strong><Lightbulb :size="13" />画像关联</strong><p>{{ selectedNode.reason }}</p></section>
        </div>
      </details>
      <small class="updated-at">{{ updatedLabel(selectedNode.updatedAt || treeModel.updatedAt) }}</small>
      <RouterLink v-if="selectedNode.action" class="detail-action" :to="selectedNode.action.to">
        {{ selectedNode.action.label }}<ArrowRight :size="16" />
      </RouterLink>
    </aside>

    <div v-if="fatalError || sceneError" class="scene-state error" role="alert">
      <CircleAlert :size="26" />
      <strong>学习成长树暂时无法加载</strong>
      <span>{{ fatalError || sceneError }}</span>
      <button type="button" @click="loadTree()"><RefreshCcw :size="16" />重新加载</button>
      <RouterLink to="/learning-profile">检查学习画像</RouterLink>
    </div>

    <div v-else-if="loading || !sceneReady" class="scene-state" role="status">
      <LoaderCircle class="spinning" :size="26" />
      <strong>{{ loading ? '正在读取画像与六周路径' : '正在加载苹果果实模型' }}</strong>
      <span>周任务状态会转换为果实大小和成熟颜色</span>
    </div>

    <div v-else-if="treeModel?.empty && !selectedNode" class="empty-notice">
      <Sprout :size="18" />
      <div><strong>六个果位已经建立，等待画像路径</strong><span>完成学习画像后生成六周内容；未生成周次只显示青果位置，不计为学习成果。</span></div>
      <RouterLink to="/learning-profile">建立画像</RouterLink>
    </div>

    <div v-if="warning && !fatalError" class="partial-warning" role="status">
      <CircleAlert :size="15" /><span>{{ warning }}</span>
    </div>

    <footer class="tree-legend" aria-label="果实成熟度图例">
      <span v-for="item in legend" :key="item.status"><i :class="item.status"></i>{{ item.label }}</span>
    </footer>
  </main>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { RouterLink, useRoute } from 'vue-router'
import {
  ArrowRight,
  ChevronRight,
  CircleAlert,
  Focus,
  Lightbulb,
  LoaderCircle,
  RefreshCcw,
  ShieldCheck,
  Sparkles,
  Sprout,
  TreePine,
  X,
} from 'lucide-vue-next'
import LifeTreeGrowthScene from '../components/LifeTreeGrowthScene.vue'
import { getEffectAssessment, getLearningPathConfig } from '../services/api.js'
import { hydrateNodeCachesFromServer, LEARNING_PATH_NODE_CACHE_KEY } from '../services/learningPathNodeCache.js'
import { buildLifeTreeModel } from '../utils/lifeTreeModel.js'

const route = useRoute()
const MATURITY_SNAPSHOT_KEY = 'qihuang:life-tree-maturity:v2'
const LAST_GROWTH_KEY = 'qihuang:life-tree-last-growth:v2'
const loading = ref(true)
const refreshing = ref(false)
const sceneReady = ref(false)
const sceneKey = ref(0)
const fatalError = ref('')
const sceneError = ref('')
const warning = ref('')
const treeModel = ref(null)
const selectedId = ref('')
const resetToken = ref(0)
const growthFeedback = ref('')
const growthFrom = ref({})
const lastGrowth = ref(readStoredGrowth())
const lastSyncAt = ref(null)
let feedbackTimer = 0
let growthFromTimer = 0
let refreshTimer = 0
let loadPromise = null

const legend = [
  { status: 'fruit-young', label: '青果' },
  { status: 'fruit-turning', label: '转色' },
  { status: 'fruit-ripe', label: '成熟' },
  { status: 'fruit-current', label: '当前' },
]
const radarLevels = [1, 2, 3, 4, 5]

const allNodes = computed(() => {
  if (!treeModel.value) return []
  return [treeModel.value.profile, ...treeModel.value.fruits]
})
const selectedNode = computed(() => allNodes.value.find((node) => node.id === selectedId.value) || null)
const growthSignals = computed(() => {
  return (treeModel.value?.fruits || []).slice(0, 6)
})
const profileConfidenceLabel = computed(() => ({
  high: '高置信度',
  medium: '中置信度',
  low: '待补充证据',
})[String(treeModel.value?.stats?.confidenceLevel || '').toLowerCase()] || '证据待核验')
const profileRadarPoints = computed(() => (treeModel.value?.profileDimensions || [])
  .map((dimension, index) => {
    const point = radarPoint(index, dimension.score)
    return `${point.x},${point.y}`
  })
  .join(' '))
const syncLabel = computed(() => {
  if (loading.value) return '正在读取成长证据'
  if (refreshing.value) return '正在同步学习反馈'
  if (!lastSyncAt.value) return '等待学习反馈同步'
  return `学习反馈已同步 ${lastSyncAt.value.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })}`
})
const shortSyncLabel = computed(() => {
  if (loading.value) return '读取中'
  if (refreshing.value) return '同步中'
  if (!lastSyncAt.value) return '等待同步'
  return `${lastSyncAt.value.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })} 已同步`
})
const shortGrowthLabel = computed(() => {
  const match = lastGrowth.value.match(/^(第.周).*?([0-9]+)%\s*→\s*([0-9]+)%$/)
  return match ? `${match[1]} ${match[2]}→${match[3]}%` : '有新成长'
})

function wholePercent(value) {
  return Math.round(Math.max(0, Math.min(100, Number(value) || 0)))
}

function profileScore(value) {
  return value === null || value === undefined ? '--' : Number(value).toFixed(1)
}

function radarPoint(index, value = 5) {
  const count = Math.max(1, treeModel.value?.profileDimensions?.length || 6)
  const angle = -Math.PI / 2 + (Math.PI * 2 * index) / count
  const score = value === null || value === undefined ? 0 : Math.max(0, Math.min(5, Number(value) || 0))
  const radius = 65 * score / 5
  return {
    x: Number((120 + Math.cos(angle) * radius).toFixed(2)),
    y: Number((96 + Math.sin(angle) * radius).toFixed(2)),
  }
}

function radarGridPoints(level) {
  return (treeModel.value?.profileDimensions || [])
    .map((_, index) => {
      const point = radarPoint(index, level)
      return `${point.x},${point.y}`
    })
    .join(' ')
}

function radarLabelPoint(index) {
  const count = Math.max(1, treeModel.value?.profileDimensions?.length || 6)
  const angle = -Math.PI / 2 + (Math.PI * 2 * index) / count
  return {
    x: Number((120 + Math.cos(angle) * 91).toFixed(2)),
    y: Number((96 + Math.sin(angle) * 91 - 4).toFixed(2)),
  }
}

function radarLabelAnchor(index) {
  if (index === 0 || index === 3) return 'middle'
  return index < 3 ? 'start' : 'end'
}

function dimensionBarStyle(value) {
  const percentage = value === null || value === undefined ? 8 : Math.max(8, Math.min(100, Number(value) / 5 * 100))
  return { '--dimension-level': `${percentage}%` }
}

function fruitTone(progress) {
  const value = wholePercent(progress)
  if (value >= 80) return '#c8443b'
  if (value >= 35) return '#c79a3b'
  return '#58ae91'
}

function fruitMarkerStyle(node) {
  const progress = wholePercent(node?.progress)
  return {
    '--fruit-tone': fruitTone(progress),
    '--fruit-progress': `${progress}%`,
    '--fruit-visual-scale': String(0.72 + progress / 100 * 0.28),
  }
}

function kindLabel(value) {
  return ({ profile: '学习画像', fruit: '周次果实' })[value] || '成长节点'
}

function updatedLabel(value) {
  if (!value) return '尚无可核验更新时间'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return '更新时间未记录'
  return `证据更新于 ${date.toLocaleString('zh-CN', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' })}`
}

function selectNode(nodeId) {
  selectedId.value = nodeId
}

function errorMessage(result, fallback) {
  const reason = result?.reason
  return reason?.response?.data?.msg || reason?.message || fallback
}

function maturityChange(previousModel, nextModel) {
  if (!previousModel) return ''
  for (const fruit of nextModel.fruits || []) {
    const previous = previousModel.fruits?.find((item) => item.id === fruit.id)
    if (!previous || Number(previous.progress) === Number(fruit.progress)) continue
    const direction = fruit.progress > previous.progress ? '提升' : '调整'
    return `${fruit.weekLabel}果实成熟度${direction}：${Math.round(previous.progress)}% → ${Math.round(fruit.progress)}%`
  }
  return ''
}

function readMaturitySnapshot() {
  try {
    const value = JSON.parse(sessionStorage.getItem(MATURITY_SNAPSHOT_KEY) || 'null')
    return value && Array.isArray(value.fruits) ? value : null
  } catch {
    return null
  }
}

function readStoredGrowth() {
  try {
    return String(JSON.parse(sessionStorage.getItem(LAST_GROWTH_KEY) || '{}')?.message || '')
  } catch {
    return ''
  }
}

function persistMaturitySnapshot(model) {
  try {
    const snapshot = {
      fruits: (model?.fruits || []).map((fruit) => ({
        id: fruit.id,
        weekLabel: fruit.weekLabel,
        progress: fruit.progress,
        growthScale: fruit.growthScale,
      })),
    }
    sessionStorage.setItem(MATURITY_SNAPSHOT_KEY, JSON.stringify(snapshot))
  } catch {}
}

function rememberGrowth(message, previousModel) {
  if (!message) return
  lastGrowth.value = message
  growthFrom.value = Object.fromEntries((previousModel?.fruits || []).map((fruit) => [fruit.id, {
    progress: fruit.progress,
    growthScale: fruit.growthScale,
  }]))
  window.clearTimeout(growthFromTimer)
  growthFromTimer = window.setTimeout(() => { growthFrom.value = {} }, 1_500)
  try {
    sessionStorage.setItem(LAST_GROWTH_KEY, JSON.stringify({ message, updatedAt: new Date().toISOString() }))
  } catch {}
}

function showGrowthFeedback(message) {
  if (!message) return
  growthFeedback.value = message
  window.clearTimeout(feedbackTimer)
  feedbackTimer = window.setTimeout(() => { growthFeedback.value = '' }, 4_800)
}

async function performLoad({ silent = false } = {}) {
  if (sceneError.value && !silent) sceneKey.value += 1
  if (silent) refreshing.value = true
  else {
    loading.value = true
    fatalError.value = ''
    sceneError.value = ''
    warning.value = ''
    sceneReady.value = false
  }
  try {
    const [assessmentResult, pathResult, cacheResult] = await Promise.allSettled([
      getEffectAssessment(route.query.profileId || ''),
      getLearningPathConfig(),
      hydrateNodeCachesFromServer(),
    ])
    const assessmentPayload = assessmentResult.status === 'fulfilled' ? assessmentResult.value : {}
    const pathConfig = pathResult.status === 'fulfilled' ? pathResult.value : {}
    const pathNodeCaches = cacheResult.status === 'fulfilled' ? cacheResult.value : {}
    const nextModel = buildLifeTreeModel({ ...assessmentPayload, pathConfig, pathNodeCaches })
    const previousModel = treeModel.value
    const comparisonModel = previousModel || readMaturitySnapshot()

    if (assessmentResult.status === 'rejected' && pathResult.status === 'rejected') {
      if (!silent || !treeModel.value) fatalError.value = errorMessage(assessmentResult, '学习画像与效果评估数据加载失败')
      return
    }
    fatalError.value = ''
    warning.value = ''
    if (assessmentResult.status === 'rejected') {
      warning.value = `${errorMessage(assessmentResult, '效果评估暂不可用')}；当前仅显示学习路径骨架。`
    } else if (pathResult.status === 'rejected') {
      warning.value = `${errorMessage(pathResult, '学习路径暂不可用')}；当前仅显示画像与评估证据。`
    } else if (cacheResult.status === 'rejected') {
      warning.value = `${errorMessage(cacheResult, '学习反馈同步暂不可用')}；当前沿用路径中已保存的任务状态。`
    }

    const changed = JSON.stringify(previousModel) !== JSON.stringify(nextModel)
    const growthMessage = maturityChange(comparisonModel, nextModel)
    rememberGrowth(growthMessage, comparisonModel)
    if (changed) treeModel.value = nextModel
    showGrowthFeedback(growthMessage)
    persistMaturitySnapshot(nextModel)
    lastSyncAt.value = new Date()

    if (!previousModel) {
      const requestedNodeId = String(route.query.node || '')
      selectedId.value = nextModel.fruits.some((fruit) => fruit.id === requestedNodeId) ? requestedNodeId : ''
    }
  } finally {
    if (silent) refreshing.value = false
    else loading.value = false
  }
}

function loadTree(options = {}) {
  if (loadPromise) return loadPromise
  loadPromise = performLoad(options).finally(() => { loadPromise = null })
  return loadPromise
}

function refreshVisibleTree() {
  if (document.visibilityState === 'visible') void loadTree({ silent: Boolean(treeModel.value) })
}

function handleStorage(event) {
  if (!event?.key || event.key === LEARNING_PATH_NODE_CACHE_KEY) refreshVisibleTree()
}

onMounted(() => {
  void loadTree()
  window.addEventListener('focus', refreshVisibleTree)
  window.addEventListener('pageshow', refreshVisibleTree)
  window.addEventListener('storage', handleStorage)
  window.addEventListener('learning-path-node-cache-updated', refreshVisibleTree)
  document.addEventListener('visibilitychange', refreshVisibleTree)
  refreshTimer = window.setInterval(refreshVisibleTree, 15_000)
})

onBeforeUnmount(() => {
  window.clearInterval(refreshTimer)
  window.clearTimeout(feedbackTimer)
  window.clearTimeout(growthFromTimer)
  window.removeEventListener('focus', refreshVisibleTree)
  window.removeEventListener('pageshow', refreshVisibleTree)
  window.removeEventListener('storage', handleStorage)
  window.removeEventListener('learning-path-node-cache-updated', refreshVisibleTree)
  document.removeEventListener('visibilitychange', refreshVisibleTree)
})
</script>

<style scoped>
.life-tree-page {
  --tree-ink: #f2f6f4;
  --tree-muted: #a7b7b1;
  --tree-line: rgba(225, 239, 233, 0.16);
  position: relative;
  width: 100%;
  height: calc(100vh - 72px);
  height: calc(100dvh - 72px);
  min-height: 620px;
  overflow: hidden;
  background: #07130f;
  color: var(--tree-ink);
}

.tree-heading {
  position: absolute;
  z-index: 5;
  top: 24px;
  left: 28px;
  right: 28px;
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 20px;
  pointer-events: none;
}

.tree-heading > div:first-child {
  width: min(520px, calc(100vw - 160px));
}

.tree-kicker {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  color: #74d7aa;
  font-size: 12px;
  font-weight: 750;
}

.tree-heading h1 {
  margin: 7px 0 5px;
  color: var(--tree-ink);
  font-size: 28px;
  line-height: 1;
  letter-spacing: 0;
}

.tree-heading p {
  margin: 0;
  color: var(--tree-muted);
  font-size: 13px;
  line-height: 1.6;
}

.scene-controls {
  display: flex;
  gap: 8px;
  pointer-events: auto;
}

.scene-controls button,
.detail-close {
  width: 40px;
  height: 40px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border: 1px solid var(--tree-line);
  border-radius: 6px;
  background: rgba(9, 24, 19, 0.9);
  color: #d9e7e1;
  cursor: pointer;
}

.scene-controls button:hover,
.detail-close:hover {
  border-color: rgba(116, 215, 170, 0.5);
  color: #74d7aa;
}

.scene-controls button:disabled { cursor: wait; opacity: 0.55; }

.growth-feedback {
  position: absolute;
  z-index: 7;
  top: 86px;
  left: 50%;
  min-height: 34px;
  display: inline-flex;
  align-items: center;
  gap: 8px;
  max-width: min(520px, calc(100% - 40px));
  padding: 0 12px;
  box-sizing: border-box;
  border: 1px solid rgba(116, 215, 170, 0.35);
  border-radius: 5px;
  background: rgba(9, 34, 25, 0.96);
  color: #dff4ea;
  font-size: 11px;
  font-weight: 720;
  transform: translateX(-50%);
  box-shadow: 0 10px 28px rgba(0, 0, 0, 0.24);
}
.growth-feedback svg { flex: 0 0 auto; color: #74d7aa; }
.growth-feedback-enter-active,
.growth-feedback-leave-active { transition: opacity 180ms ease, transform 180ms ease; }
.growth-feedback-enter-from,
.growth-feedback-leave-to { opacity: 0; transform: translate(-50%, -8px); }

.growth-panel,
.node-detail {
  position: absolute;
  z-index: 4;
  top: 126px;
  width: 292px;
  box-sizing: border-box;
  border: 1px solid var(--tree-line);
  border-radius: 7px;
  background: rgba(7, 20, 16, 0.91);
  box-shadow: 0 16px 40px rgba(0, 0, 0, 0.22);
  backdrop-filter: blur(12px);
}

.growth-panel { left: 28px; padding: 18px; }
.node-detail { right: 28px; padding: 22px; }

.growth-panel-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 10px;
  padding-bottom: 14px;
  border-bottom: 1px solid var(--tree-line);
}

.growth-panel-head > div { display: grid; gap: 4px; min-width: 0; }
.growth-panel-head span,
.detail-eyebrow { color: #75caa4; font-size: 11px; font-weight: 750; }
.growth-panel-head strong { overflow: hidden; color: var(--tree-ink); font-size: 15px; text-overflow: ellipsis; white-space: nowrap; }
.growth-panel-head em { flex: 0 0 auto; padding: 4px 6px; border-radius: 4px; background: rgba(242, 189, 82, 0.13); color: #f2bd52; font-size: 10px; font-style: normal; }
.growth-panel-head em.confidence-high { background: rgba(85, 210, 138, 0.14); color: #71dca0; }
.growth-panel-head em.confidence-medium { background: rgba(90, 169, 255, 0.14); color: #83bbf5; }

.metric-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1px;
  margin: 14px 0 0;
  overflow: hidden;
  border: 1px solid var(--tree-line);
  border-radius: 5px;
  background: var(--tree-line);
}

.metric-grid div { min-width: 0; padding: 11px; background: rgba(10, 29, 22, 0.97); }
.metric-grid dt { color: #8fa29b; font-size: 10px; }
.metric-grid dd { margin: 5px 0 0; color: #f5f8f7; font-size: 19px; font-weight: 760; letter-spacing: 0; }

.sync-line {
  min-height: 24px;
  display: flex;
  align-items: center;
  gap: 6px;
  margin-top: 7px;
  color: #789087;
  font-size: 9px;
}
.sync-line svg { flex: 0 0 auto; }
.sync-line.syncing { color: #75caa4; }

.last-growth {
  min-height: 24px;
  display: flex;
  align-items: flex-start;
  gap: 6px;
  padding: 6px 7px;
  border-left: 2px solid #74d7aa;
  background: rgba(116, 215, 170, 0.07);
  color: #a9c8bb;
  font-size: 9px;
  line-height: 1.45;
}
.last-growth svg { flex: 0 0 auto; margin-top: 1px; color: #74d7aa; }

.signal-section,
.agent-chain,
.profile-dimensions { margin-top: 18px; }
.section-label { display: flex; align-items: center; gap: 6px; color: #c7d5d0; font-size: 11px; font-weight: 750; }
.signal-section > p { margin: 11px 0 0; color: #8fa29b; font-size: 11px; line-height: 1.55; }

.profile-dimensions > div:last-child {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 7px 12px;
  margin-top: 10px;
}

.profile-dimensions span {
  min-width: 0;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 6px;
}

.profile-dimensions strong {
  min-width: 0;
  overflow: hidden;
  color: #c7d5d0;
  font-size: 9px;
  font-weight: 600;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.profile-dimensions small {
  flex: 0 0 auto;
  color: #7f958c;
  font-size: 8px;
  font-variant-numeric: tabular-nums;
}

.signal-row {
  position: relative;
  width: 100%;
  min-height: 38px;
  display: grid;
  grid-template-columns: 8px minmax(0, 1fr) auto;
  align-items: center;
  gap: 8px;
  padding: 7px 0;
  border: 0;
  border-bottom: 1px solid rgba(225, 239, 233, 0.09);
  background: transparent;
  color: #eef3f1;
  text-align: left;
  cursor: pointer;
}

.signal-row > span { width: 7px; height: 7px; border-radius: 50%; background: #61b99b; }
.signal-row strong { min-width: 0; overflow: hidden; font-size: 11px; text-overflow: ellipsis; white-space: nowrap; }
.signal-row small { color: #91a39c; font-size: 9px; }
.signal-row:hover strong { color: #74d7aa; }
.signal-row.current > span { background: #d3a64c; box-shadow: 0 0 0 3px rgba(211, 166, 76, 0.15); }

.agent-chain > div:last-child {
  display: flex;
  align-items: center;
  gap: 3px;
  margin-top: 10px;
  color: #8fa29b;
  font-size: 9px;
  white-space: nowrap;
}
.agent-chain svg { flex: 0 0 auto; color: #567168; }

.detail-close { position: absolute; top: 14px; right: 14px; width: 32px; height: 32px; background: transparent; }
.node-detail h2 { margin: 8px 38px 12px 0; color: var(--tree-ink); font-size: 21px; line-height: 1.25; letter-spacing: 0; overflow-wrap: anywhere; }
.status-line { display: flex; align-items: center; flex-wrap: wrap; gap: 8px; }
.status-line span { padding: 5px 8px; border-radius: 4px; background: rgba(156, 168, 163, 0.15); color: #b8c1bd; font-size: 10px; font-weight: 750; }
.status-line em { color: #9aada5; font-size: 10px; font-style: normal; }
.detail-description { margin: 14px 0 0; color: #b5c3be; font-size: 12px; line-height: 1.6; }
.evidence-block,
.reason-block { margin-top: 16px; padding-top: 14px; border-top: 1px solid var(--tree-line); }
.evidence-block > span,
.reason-block > span { display: flex; align-items: center; gap: 6px; color: #75caa4; font-size: 10px; font-weight: 750; }
.evidence-block p,
.reason-block p { margin: 8px 0 0; color: #bdcac5; font-size: 11px; line-height: 1.65; }
.updated-at { display: block; margin-top: 14px; color: #758a82; font-size: 9px; }
.detail-action { min-height: 40px; display: inline-flex; align-items: center; justify-content: center; gap: 7px; margin-top: 16px; padding: 0 13px; border-radius: 5px; background: #dba84a; color: #182017; font-size: 12px; font-weight: 800; text-decoration: none; }
.detail-action:hover { background: #edc36f; }

/* Compact visual summaries keep the tree, rather than prose, as the primary surface. */
.growth-panel,
.node-detail {
  border-color: rgba(154, 193, 177, 0.16);
  background: rgba(6, 20, 15, 0.84);
  box-shadow: 0 18px 46px rgba(0, 0, 0, 0.26);
  backdrop-filter: blur(15px);
}
.growth-panel { width: 260px; padding: 14px; }
.node-detail { width: 306px; padding: 18px; }

.panel-identity {
  display: grid;
  grid-template-columns: 32px minmax(0, 1fr) auto;
  align-items: center;
  gap: 9px;
}
.profile-mark {
  width: 32px;
  height: 32px;
  display: grid;
  place-items: center;
  border: 1px solid rgba(116, 215, 170, 0.2);
  border-radius: 6px;
  background: rgba(116, 215, 170, 0.09);
  color: #74d7aa;
}
.panel-identity > div { min-width: 0; display: grid; gap: 1px; }
.panel-identity small { color: #789087; font-size: 8px; }
.panel-identity strong { overflow: hidden; font-size: 13px; text-overflow: ellipsis; white-space: nowrap; }
.panel-identity em {
  min-width: 22px;
  padding: 3px 5px;
  border-radius: 4px;
  background: rgba(116, 215, 170, 0.1);
  color: #75caa4;
  font-size: 9px;
  font-style: normal;
  text-align: center;
}

.growth-overview {
  display: grid;
  grid-template-columns: 78px minmax(0, 1fr);
  align-items: center;
  gap: 12px;
  margin-top: 13px;
  padding: 12px 0;
  border-top: 1px solid var(--tree-line);
  border-bottom: 1px solid var(--tree-line);
}
.maturity-dial {
  position: relative;
  width: 72px;
  aspect-ratio: 1;
  display: grid;
  place-items: center;
  border-radius: 50%;
  background: conic-gradient(#d9ad54 var(--maturity-angle), rgba(133, 164, 151, 0.16) 0deg);
}
.maturity-dial::before {
  position: absolute;
  inset: 6px;
  border-radius: inherit;
  background: #0a1d16;
  content: '';
}
.maturity-dial > div,
.maturity-dial > small { position: relative; z-index: 1; }
.maturity-dial > div { display: flex; align-items: baseline; margin-top: 4px; }
.maturity-dial strong { font-size: 22px; line-height: 1; font-variant-numeric: tabular-nums; }
.maturity-dial span { color: #d9ad54; font-size: 9px; }
.maturity-dial > small { margin-top: -22px; color: #7f958c; font-size: 8px; }
.overview-numbers { min-width: 0; display: flex; align-items: center; margin: 0; }
.overview-numbers div { flex: 1; min-width: 0; padding-left: 10px; border-left: 1px solid var(--tree-line); }
.overview-numbers dt { color: #7f958c; font-size: 8px; }
.overview-numbers dd { margin: 4px 0 0; font-size: 19px; font-weight: 760; font-variant-numeric: tabular-nums; }
.overview-numbers dd small { margin-left: 2px; color: #82958e; font-size: 9px; }

.sync-strip { min-height: 27px; display: flex; align-items: center; gap: 5px; color: #71867d; font-size: 8px; }
.sync-strip.syncing { color: #75caa4; }
.sync-strip > em {
  min-width: 0;
  display: flex;
  align-items: center;
  gap: 3px;
  margin-left: auto;
  overflow: hidden;
  color: #d9ad54;
  font-size: 8px;
  font-style: normal;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.sync-strip svg { flex: 0 0 auto; }

.fruit-orchard,
.root-spectrum { margin-top: 10px; }
.fruit-orchard > header,
.root-spectrum > header { display: flex; align-items: center; justify-content: space-between; }
.fruit-orchard > header span,
.root-spectrum > header span { color: #c9d7d2; font-size: 9px; font-weight: 750; }
.fruit-orchard > header small,
.root-spectrum > header small { color: #71867d; font-size: 8px; }
.fruit-orchard > div {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  margin-top: 7px;
  border-top: 1px solid var(--tree-line);
  border-left: 1px solid var(--tree-line);
}
.fruit-orchard button {
  position: relative;
  width: 100%;
  min-width: 0;
  min-height: 62px;
  display: grid;
  grid-template-areas: 'fruit week' 'fruit value' 'progress progress';
  grid-template-columns: 30px minmax(0, 1fr);
  grid-template-rows: 1fr 1fr 3px;
  align-items: center;
  gap: 0 4px;
  padding: 7px 6px 6px;
  border: 0;
  border-right: 1px solid var(--tree-line);
  border-bottom: 1px solid var(--tree-line);
  background: transparent;
  color: #eef3f1;
  text-align: left;
  cursor: pointer;
}
.fruit-orchard button:hover,
.fruit-orchard button.selected { background: rgba(116, 215, 170, 0.07); }
.fruit-orchard button.current { box-shadow: inset 0 0 0 1px rgba(227, 188, 100, 0.45); }
.mini-fruit {
  grid-area: fruit;
  position: relative;
  width: 21px;
  height: 23px;
  justify-self: center;
  border-radius: 48% 48% 44% 44%;
  background: var(--fruit-tone);
  box-shadow: inset -4px -5px 7px rgba(34, 38, 22, 0.27), 0 3px 8px rgba(0, 0, 0, 0.2);
  transform: scale(var(--fruit-visual-scale));
}
.mini-fruit::before,
.inspection-fruit::before {
  position: absolute;
  top: -5px;
  left: 48%;
  width: 9px;
  height: 6px;
  border-radius: 90% 10% 80% 20%;
  background: #72a45e;
  content: '';
  transform: rotate(-22deg);
  transform-origin: left bottom;
}
.mini-fruit i { position: absolute; top: 4px; left: 5px; width: 4px; height: 6px; border-radius: 50%; background: rgba(255, 255, 255, 0.25); }
.fruit-orchard button > b { grid-area: week; align-self: end; font-size: 9px; font-weight: 700; }
.fruit-orchard button > em { grid-area: value; align-self: start; color: #879b93; font-size: 8px; font-style: normal; font-variant-numeric: tabular-nums; }
.week-progress { grid-area: progress; height: 2px; overflow: hidden; background: rgba(132, 161, 149, 0.16); }
.week-progress i { display: block; width: var(--fruit-progress); height: 100%; background: var(--fruit-tone); }

.root-spectrum > div { height: 64px; display: grid; grid-template-columns: repeat(6, minmax(0, 1fr)); gap: 4px; align-items: end; margin-top: 7px; }
.root-spectrum > div > span { min-width: 0; display: grid; justify-items: center; gap: 4px; }
.root-spectrum span > i { width: 7px; height: 42px; display: flex; align-items: flex-end; overflow: hidden; border-radius: 2px 2px 0 0; background: rgba(129, 159, 147, 0.13); }
.root-spectrum span > i b { width: 100%; height: var(--dimension-level); background: linear-gradient(#74d7aa, #477c66); }
.root-spectrum span > small { width: 100%; overflow: hidden; color: #7f958c; font-size: 7px; text-align: center; text-overflow: ellipsis; white-space: nowrap; }

.loop-track { display: flex; align-items: center; margin-top: 12px; padding-top: 10px; border-top: 1px solid var(--tree-line); }
.loop-track span { display: grid; flex: 0 0 auto; justify-items: center; gap: 2px; color: #6f9d8a; }
.loop-track span small { font-size: 7px; }
.loop-track > i { flex: 1; height: 1px; margin: 0 3px 11px; background: rgba(116, 215, 170, 0.17); }

.detail-heading { padding-right: 38px; }
.detail-eyebrow { color: #75caa4; font-size: 9px; font-weight: 750; }
.detail-heading h2 {
  display: -webkit-box;
  margin: 5px 0 0;
  overflow: hidden;
  font-size: 19px;
  line-height: 1.27;
  letter-spacing: 0;
  overflow-wrap: anywhere;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
}
.fruit-inspector { display: grid; grid-template-columns: 70px minmax(0, 1fr); align-items: center; gap: 15px; margin-top: 14px; padding: 14px 0; border-top: 1px solid var(--tree-line); border-bottom: 1px solid var(--tree-line); }
.inspection-fruit {
  position: relative;
  width: 56px;
  height: 60px;
  justify-self: center;
  border-radius: 48% 48% 43% 43%;
  background: var(--fruit-tone);
  box-shadow: inset -10px -11px 18px rgba(39, 37, 20, 0.27), 0 8px 18px rgba(0, 0, 0, 0.25);
  transform: scale(var(--fruit-visual-scale));
}
.inspection-fruit::before { top: -8px; width: 19px; height: 11px; }
.fruit-inspector > div:last-child { min-width: 0; display: grid; gap: 4px; }
.fruit-inspector strong { font-size: 31px; line-height: 1; font-variant-numeric: tabular-nums; }
.fruit-inspector strong small { margin-left: 2px; color: #8da199; font-size: 11px; }
.fruit-inspector span { font-size: 9px; font-weight: 750; }
.detail-progress { height: 3px; display: block; margin-top: 3px; overflow: hidden; background: rgba(132, 161, 149, 0.16); }
.detail-progress b { display: block; width: var(--fruit-progress); height: 100%; background: var(--fruit-tone); }
.profile-inspector { display: flex; align-items: center; gap: 12px; margin-top: 14px; padding: 14px 0; border-top: 1px solid var(--tree-line); border-bottom: 1px solid var(--tree-line); color: #74d7aa; }
.profile-inspector div { display: grid; }
.profile-inspector strong { font-size: 25px; line-height: 1; }
.profile-inspector span { color: #84988f; font-size: 9px; }
.evidence-metrics { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); margin: 0; padding: 10px 0; border-bottom: 1px solid var(--tree-line); }
.evidence-metrics div { min-width: 0; padding: 0 8px; border-left: 1px solid var(--tree-line); }
.evidence-metrics div:first-child { padding-left: 0; border-left: 0; }
.evidence-metrics dt { overflow: hidden; color: #7d9189; font-size: 8px; text-overflow: ellipsis; white-space: nowrap; }
.evidence-metrics dd { margin: 4px 0 0; font-size: 17px; font-weight: 750; font-variant-numeric: tabular-nums; }
.evidence-metrics dd small { margin-left: 2px; color: #758a82; font-size: 8px; }
.detail-description { display: -webkit-box; margin: 11px 0 0; overflow: hidden; color: #aabbb4; font-size: 10px; line-height: 1.55; -webkit-box-orient: vertical; -webkit-line-clamp: 3; }
.evidence-disclosure { margin-top: 10px; border-top: 1px solid var(--tree-line); border-bottom: 1px solid var(--tree-line); }
.evidence-disclosure summary { min-height: 34px; display: flex; align-items: center; gap: 6px; color: #75caa4; font-size: 9px; font-weight: 750; cursor: pointer; list-style: none; }
.evidence-disclosure summary::-webkit-details-marker { display: none; }
.evidence-disclosure summary svg:last-child { margin-left: auto; transition: transform 160ms ease; }
.evidence-disclosure[open] summary svg:last-child { transform: rotate(90deg); }
.evidence-disclosure > div { padding: 0 0 10px; }
.evidence-disclosure section + section { margin-top: 9px; padding-top: 9px; border-top: 1px solid var(--tree-line); }
.evidence-disclosure section strong { display: flex; align-items: center; gap: 5px; color: #a9bbb4; font-size: 9px; }
.evidence-disclosure p { margin: 5px 0 0; color: #98aaa3; font-size: 9px; line-height: 1.55; }
.updated-at { display: block; margin-top: 9px; color: #758a82; font-size: 8px; }
.detail-action { min-height: 38px; margin-top: 12px; font-size: 11px; }

.status-mastered { color: #71dca0 !important; }
.status-developing { color: #83bbf5 !important; }
.status-weak { color: #f18b84 !important; }
.status-recommended { color: #f2bd52 !important; }
.status-unverified { color: #aeb8b4 !important; }
.signal-row.status-mastered > span,
.tree-legend i.status-mastered { background: #55d28a; }
.signal-row.status-developing > span,
.tree-legend i.status-developing { background: #5aa9ff; }
.signal-row.status-weak > span,
.tree-legend i.status-weak { background: #ef756d; }
.signal-row.status-recommended > span,
.tree-legend i.status-recommended { background: #f2bd52; }
.signal-row.status-unverified > span,
.tree-legend i.status-unverified { background: #9ca8a3; }

.tree-legend i.fruit-young { background: #61b99b; }
.tree-legend i.fruit-turning { background: #c79a3b; }
.tree-legend i.fruit-ripe { background: #c43d34; }
.tree-legend i.fruit-current {
  background: transparent;
  border: 1px solid #e3bc64;
  box-shadow: 0 0 0 2px rgba(227, 188, 100, 0.14);
}

.scene-state {
  position: absolute;
  z-index: 8;
  inset: 50% auto auto 50%;
  width: min(360px, calc(100% - 40px));
  display: grid;
  justify-items: center;
  gap: 8px;
  padding: 24px;
  box-sizing: border-box;
  border: 1px solid var(--tree-line);
  border-radius: 7px;
  background: rgba(7, 20, 16, 0.96);
  color: #dfe9e5;
  text-align: center;
  transform: translate(-50%, -50%);
}
.scene-state strong { font-size: 14px; }
.scene-state span { color: #94a7a0; font-size: 11px; }
.scene-state button,
.scene-state a { display: inline-flex; align-items: center; gap: 6px; margin-top: 5px; border: 0; background: transparent; color: #75caa4; font: inherit; font-size: 11px; text-decoration: none; cursor: pointer; }
.scene-state.error svg { color: #ef756d; }

.empty-notice,
.partial-warning {
  position: absolute;
  z-index: 6;
  left: 50%;
  display: flex;
  align-items: center;
  gap: 10px;
  border: 1px solid var(--tree-line);
  border-radius: 6px;
  background: rgba(7, 20, 16, 0.94);
  transform: translateX(-50%);
}
.empty-notice { bottom: 72px; max-width: min(620px, calc(100% - 40px)); padding: 12px 14px; }
.empty-notice > svg { flex: 0 0 auto; color: #74d7aa; }
.empty-notice div { display: grid; gap: 2px; }
.empty-notice strong { color: var(--tree-ink); font-size: 11px; }
.empty-notice span { color: #93a69f; font-size: 10px; }
.empty-notice a { margin-left: auto; color: #f2bd52; font-size: 10px; font-weight: 750; text-decoration: none; white-space: nowrap; }
.partial-warning { top: 86px; padding: 7px 10px; color: #e9c57f; font-size: 10px; }

.tree-legend {
  position: absolute;
  z-index: 4;
  right: 28px;
  bottom: 22px;
  left: 28px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 16px;
  pointer-events: none;
}
.tree-legend span { display: inline-flex; align-items: center; gap: 6px; color: #b2c0bb; font-size: 10px; }
.tree-legend i { width: 8px; height: 8px; border-radius: 50%; }
.tree-legend small { margin-left: 8px; color: #71867d; font-size: 9px; }
.spinning { animation: spin 0.9s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }

@media (max-width: 1120px) {
  .growth-panel { width: 244px; }
  .node-detail { width: 270px; }
  .root-spectrum { display: none; }
}

@media (max-width: 820px) {
  .life-tree-page {
    height: calc(100vh - 88px);
    height: calc(100dvh - 88px);
    min-height: 0;
  }
  .tree-heading { top: 14px; left: 16px; right: 16px; }
  .tree-heading h1 { margin-top: 5px; font-size: 23px; }
  .tree-heading p { max-width: 300px; font-size: 10px; }
  .tree-kicker { font-size: 10px; }
  .scene-controls { gap: 5px; }
  .scene-controls button { width: 36px; height: 36px; }
  .growth-panel {
    top: 102px;
    left: 16px;
    width: 218px;
    padding: 10px;
  }
  .growth-overview { grid-template-columns: 62px minmax(0, 1fr); gap: 7px; padding: 9px 0; }
  .maturity-dial { width: 58px; }
  .maturity-dial strong { font-size: 18px; }
  .maturity-dial > small { margin-top: -18px; }
  .overview-numbers div { padding-left: 7px; }
  .overview-numbers dd { font-size: 15px; }
  .fruit-orchard button { min-height: 54px; grid-template-columns: 26px minmax(0, 1fr); padding: 6px 4px 5px; }
  .mini-fruit { width: 18px; height: 20px; }
  .loop-track { display: none; }
  .node-detail {
    top: auto;
    right: 16px;
    bottom: 54px;
    left: 16px;
    width: auto;
    max-height: 35vh;
    padding: 16px;
    overflow-y: auto;
  }
  .detail-heading h2 { font-size: 17px; }
  .fruit-inspector { margin-top: 10px; padding: 9px 0; }
  .detail-description { margin-top: 8px; -webkit-line-clamp: 2; }
  .detail-action { position: static; }
  .tree-legend { right: 12px; bottom: 12px; left: 12px; gap: 8px; justify-content: flex-end; }
  .tree-legend span { font-size: 0; }
  .tree-legend span i { width: 9px; height: 9px; }
  .tree-legend small { margin: 0; font-size: 8px; }
  .empty-notice { bottom: 48px; }
}

@media (max-width: 520px) {
  .tree-heading > div:first-child { width: calc(100vw - 125px); }
  .tree-heading p { display: none; }
  .growth-panel {
    top: 74px;
    right: 16px;
    width: auto;
    padding: 9px 10px;
  }
  .panel-identity,
  .sync-strip,
  .root-spectrum,
  .loop-track,
  .fruit-orchard > header { display: none; }
  .growth-overview { grid-template-columns: 54px minmax(0, 1fr); width: 154px; margin: 0; padding: 0 9px 0 0; border: 0; border-right: 1px solid var(--tree-line); }
  .maturity-dial { width: 48px; }
  .maturity-dial::before { inset: 4px; }
  .maturity-dial strong { font-size: 14px; }
  .maturity-dial > small { margin-top: -14px; font-size: 7px; }
  .overview-numbers dd { margin-top: 2px; font-size: 12px; }
  .overview-numbers dt,
  .overview-numbers dd small { font-size: 7px; }
  .fruit-orchard { position: absolute; top: 9px; right: 10px; left: 174px; margin: 0; }
  .fruit-orchard > div { grid-template-columns: repeat(6, minmax(0, 1fr)); margin: 0; border: 0; }
  .fruit-orchard button { min-height: 48px; display: grid; grid-template-areas: 'fruit' 'week'; grid-template-columns: 1fr; grid-template-rows: 28px 12px; justify-items: center; padding: 2px; border: 0; }
  .mini-fruit { width: 16px; height: 18px; }
  .fruit-orchard button > b { align-self: center; font-size: 7px; }
  .fruit-orchard button > em,
  .week-progress { display: none; }
  .node-detail { bottom: 42px; max-height: 43vh; }
  .fruit-inspector { grid-template-columns: 54px minmax(0, 1fr); }
  .inspection-fruit { width: 44px; height: 47px; }
  .evidence-metrics { padding: 8px 0; }
  .tree-legend { justify-content: center; }
  .tree-legend small { display: none; }
  .partial-warning { top: 142px; width: calc(100% - 32px); box-sizing: border-box; }
  .growth-feedback { top: 142px; width: calc(100% - 32px); justify-content: center; text-align: center; }
  .empty-notice { bottom: 38px; width: calc(100% - 32px); box-sizing: border-box; }
  .empty-notice span { display: none; }
}
</style>

<style>
body:has(.life-tree-page) { overflow: hidden; }

/* This route is an intentional dark visualization surface. */
#app .life-tree-page :where(h1, h2, h3, h4, h5, h6, strong, b):not(button *) {
  color: #f2f6f4 !important;
}

#app .life-tree-page :where(p, small, em, dt):not(button *) {
  color: #a7b7b1 !important;
}

#app .life-tree-page .metric-grid dd {
  color: #f5f8f7 !important;
}

#app .life-tree-page .growth-panel-head em {
  color: #f2bd52 !important;
}

#app .life-tree-page .growth-panel-head em.confidence-high {
  color: #71dca0 !important;
}

#app .life-tree-page .growth-panel-head em.confidence-medium {
  color: #83bbf5 !important;
}

#app .life-tree-page .fruit-orchard button {
  background: transparent !important;
  color: #eef3f1 !important;
}

#app .life-tree-page .fruit-orchard button:hover,
#app .life-tree-page .fruit-orchard button.selected {
  background: rgba(116, 215, 170, 0.07) !important;
}

#app .life-tree-page .fruit-orchard button > b {
  color: #eef3f1 !important;
}

#app .life-tree-page .fruit-orchard button > em {
  color: #879b93 !important;
}

/* The left rail is the same evidence-backed learning profile used by the profile report. */
#app .life-tree-page .tree-status {
  position: absolute;
  z-index: 4;
  top: 150px;
  left: 28px;
  width: 292px;
  padding-left: 18px;
  box-sizing: border-box;
  border-left: 1px solid rgba(135, 187, 164, 0.32);
  color: #edf4f1;
}

#app .life-tree-page .profile-summary-heading {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 14px;
}

#app .life-tree-page .profile-summary-heading > div {
  min-width: 0;
  display: grid;
  gap: 4px;
}

#app .life-tree-page .profile-summary-heading > div > span {
  display: flex;
  align-items: center;
  gap: 6px;
  color: #76ad94 !important;
  font-size: 12px;
  font-weight: 650;
}

#app .life-tree-page .profile-summary-heading > div > strong {
  max-width: 100%;
  overflow: hidden;
  color: #edf4f1 !important;
  font-size: 18px;
  font-weight: 620;
  text-overflow: ellipsis;
  white-space: nowrap;
}

#app .life-tree-page .profile-link {
  flex: 0 0 auto;
  display: inline-flex;
  align-items: center;
  gap: 2px;
  padding: 3px 0 !important;
  border: 0 !important;
  border-radius: 0 !important;
  background: transparent !important;
  color: #8ca198 !important;
  font-size: 10px;
  cursor: pointer;
  transition: color 180ms ease;
}

#app .life-tree-page .profile-link:hover,
#app .life-tree-page .profile-link:focus-visible { color: #9bd0b7 !important; }

#app .life-tree-page .profile-link:focus-visible,
#app .life-tree-page .week-path button:focus-visible {
  outline: 1px solid #87bba4;
  outline-offset: 5px;
}

#app .life-tree-page .profile-radar-stage {
  width: 100%;
  height: 214px;
  margin-top: 5px;
}

#app .life-tree-page .profile-radar-stage svg {
  width: 100%;
  height: 100%;
  overflow: visible;
}

#app .life-tree-page .profile-radar-grid {
  fill: none;
  stroke: rgba(151, 184, 170, 0.2);
  stroke-width: 0.8;
}

#app .life-tree-page .profile-radar-axis { stroke: rgba(151, 184, 170, 0.16); stroke-width: 0.8; }
#app .life-tree-page .profile-radar-value { fill: rgba(105, 177, 143, 0.2); stroke: #7ac09f; stroke-width: 1.6; }
#app .life-tree-page .profile-radar-dot { fill: #e1b55b; stroke: #0b1b15; stroke-width: 1.5; }
#app .life-tree-page .profile-radar-label { fill: #b9c9c2; font-size: 10.5px; letter-spacing: 0; }
#app .life-tree-page .profile-radar-score { fill: #71877d; font-size: 9px; font-variant-numeric: tabular-nums; }

#app .life-tree-page .profile-dimension-list {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px 16px;
  margin-top: 5px;
}

#app .life-tree-page .profile-dimension-list > div {
  min-width: 0;
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  align-items: center;
  gap: 5px 8px;
}

#app .life-tree-page .profile-dimension-list span {
  overflow: hidden;
  color: #b9c8c2;
  font-size: 12px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

#app .life-tree-page .profile-dimension-list small {
  color: #d5b66d !important;
  font-size: 11px;
  font-variant-numeric: tabular-nums;
}

#app .life-tree-page .profile-dimension-list i {
  grid-column: 1 / -1;
  height: 2px;
  overflow: hidden;
  background: rgba(132, 161, 149, 0.16);
}

#app .life-tree-page .profile-dimension-list i b {
  display: block;
  width: var(--dimension-level);
  height: 100%;
  background: #71b092;
}

#app .life-tree-page .profile-summary-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-top: 17px;
  padding-top: 12px;
  border-top: 1px solid rgba(151, 184, 170, 0.16);
}

#app .life-tree-page .profile-summary-footer span,
#app .life-tree-page .profile-summary-footer a {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  color: #7f968c;
  font-size: 10px;
  text-decoration: none;
}

#app .life-tree-page .profile-summary-footer a { color: #b9c8c2; }
#app .life-tree-page .profile-summary-footer a:hover { color: #92c9b0; }

#app .life-tree-page .sync-note {
  min-width: 0;
  display: flex;
  align-items: center;
  gap: 5px;
  margin-top: 10px;
  color: #60786d;
  font-size: 10px;
}

#app .life-tree-page .sync-note.syncing { color: #78b398; }
#app .life-tree-page .sync-note > em {
  min-width: 0;
  margin-left: auto;
  overflow: hidden;
  color: #ae9051 !important;
  font-style: normal;
  text-overflow: ellipsis;
  white-space: nowrap;
}

#app .life-tree-page .week-path {
  position: absolute;
  z-index: 4;
  right: auto;
  bottom: 54px;
  left: 50%;
  width: min(620px, calc(100% - 690px));
  display: grid;
  grid-template-columns: repeat(6, minmax(0, 1fr));
  gap: 0;
  transform: translateX(-50%);
}

#app .life-tree-page .week-path::before {
  position: absolute;
  z-index: -1;
  top: 36px;
  right: 8%;
  bottom: auto;
  left: 8%;
  width: auto;
  height: 1px;
  background: rgba(137, 167, 154, 0.24);
  content: '';
}

#app .life-tree-page .week-path-heading {
  grid-column: 1 / -1;
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  margin-bottom: 6px;
}

#app .life-tree-page .week-path-heading b { color: #dce7e2 !important; font-size: 12px; font-weight: 600; }
#app .life-tree-page .week-path-heading small { color: #667d73 !important; font-size: 9px; }

#app .life-tree-page .week-path button {
  min-height: 42px;
  display: grid;
  grid-template-columns: 1fr;
  grid-template-rows: 13px 1fr;
  align-items: center;
  justify-items: center;
  gap: 4px;
  padding: 0 !important;
  border: 0 !important;
  border-radius: 0 !important;
  background: transparent !important;
  color: #81968d !important;
  text-align: center;
  cursor: pointer;
  transition: color 180ms ease, transform 180ms ease;
}

#app .life-tree-page .week-path button:hover { color: #dbe6e1 !important; transform: translateY(-2px); }
#app .life-tree-page .week-path button > i {
  width: 13px;
  height: 13px;
  display: grid;
  place-items: center;
  box-sizing: border-box;
  border: 1px solid rgba(166, 190, 180, 0.42);
  border-radius: 50%;
  background: #0b1b15;
}

#app .life-tree-page .week-path button > i span {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--fruit-tone);
}

#app .life-tree-page .week-path button.current > i { border-color: #ddb45d; box-shadow: 0 0 0 3px rgba(221, 180, 93, 0.13); }
#app .life-tree-page .week-path button.selected > i { background: var(--fruit-tone); }
#app .life-tree-page .week-path button.selected > i span { background: #eef5f2; }
#app .life-tree-page .week-path button > span { min-width: 0; display: flex; align-items: baseline; gap: 5px; }
#app .life-tree-page .week-path button b { color: inherit !important; font-size: 11px; font-weight: 600; font-variant-numeric: tabular-nums; }
#app .life-tree-page .week-path button em { color: #71877d !important; font-size: 9px; font-style: normal; font-variant-numeric: tabular-nums; }
#app .life-tree-page .week-path button.current b { color: #dfb961 !important; }

#app .life-tree-page .node-detail {
  top: 144px;
  right: 0;
  width: 306px;
  max-height: calc(100% - 194px);
  padding: 24px 28px 26px;
  overflow-y: auto;
  border: 0;
  border-left: 1px solid rgba(151, 184, 170, 0.2);
  border-radius: 0;
  background: rgba(7, 20, 16, 0.94);
  box-shadow: -18px 0 42px rgba(2, 11, 7, 0.2);
  backdrop-filter: none;
}

#app .life-tree-page .detail-close {
  top: 20px;
  right: 22px;
  border: 0;
  border-radius: 0;
  background: transparent;
}

#app .life-tree-page .fruit-inspector {
  grid-template-columns: 54px minmax(0, 1fr);
  gap: 18px;
  margin-top: 18px;
  padding: 16px 0;
}

#app .life-tree-page .week-number {
  display: grid;
  align-content: center;
  border-right: 1px solid rgba(151, 184, 170, 0.2);
}

#app .life-tree-page .week-number small { color: #677f74 !important; font-size: 7px; }
#app .life-tree-page .week-number strong { color: var(--fruit-tone) !important; font-size: 27px; font-weight: 520; line-height: 1; }

#app .life-tree-page .evidence-metrics div { padding-right: 8px; padding-left: 8px; }
#app .life-tree-page .evidence-metrics dd { font-weight: 560; }

#app .life-tree-page .profile-root-list {
  display: grid;
  gap: 11px;
  padding: 14px 0;
  border-bottom: 1px solid rgba(151, 184, 170, 0.16);
}

#app .life-tree-page .profile-root-list > div {
  display: grid;
  grid-template-columns: 64px minmax(0, 1fr) 20px;
  align-items: center;
  gap: 8px;
}

#app .life-tree-page .profile-root-list span { overflow: hidden; color: #9baca5; font-size: 9px; text-overflow: ellipsis; white-space: nowrap; }
#app .life-tree-page .profile-root-list i { height: 2px; overflow: hidden; background: rgba(132, 161, 149, 0.15); }
#app .life-tree-page .profile-root-list i b { display: block; width: var(--dimension-level); height: 100%; background: #71b092; }
#app .life-tree-page .profile-root-list small { color: #71877d !important; font-size: 8px; font-variant-numeric: tabular-nums; text-align: right; }

#app .life-tree-page .scene-controls button {
  border-color: rgba(151, 184, 170, 0.18) !important;
  background: rgba(7, 20, 16, 0.7) !important;
  color: #a7bbb2 !important;
  box-shadow: none !important;
}

@media (max-width: 1120px) {
  #app .life-tree-page .tree-status { width: 264px; }
  #app .life-tree-page .profile-radar-stage { height: 190px; }
  #app .life-tree-page .week-path { width: min(540px, calc(100% - 360px)); }
}

@media (max-width: 820px) {
  #app .life-tree-page .tree-status { top: 108px; left: 16px; width: 250px; }
  #app .life-tree-page .profile-radar-stage { height: 178px; }
  #app .life-tree-page .week-path {
    top: auto;
    right: auto;
    bottom: 46px;
    left: 50%;
    width: min(520px, calc(100% - 32px));
  }
  #app .life-tree-page .node-detail {
    top: auto;
    right: 16px;
    bottom: 54px;
    left: 16px;
    width: auto;
    max-height: 40vh;
    padding: 18px 20px 20px;
    border-top: 1px solid rgba(151, 184, 170, 0.2);
    border-left: 0;
    box-shadow: 0 -18px 42px rgba(2, 11, 7, 0.24);
  }
}

@media (max-width: 520px) {
  #app .life-tree-page .tree-status {
    top: 76px;
    right: 16px;
    left: 16px;
    width: auto;
    padding-left: 12px;
  }
  #app .life-tree-page .profile-summary-heading > div > span { font-size: 9px; }
  #app .life-tree-page .profile-summary-heading > div > strong { font-size: 14px; }
  #app .life-tree-page .profile-link { font-size: 9px; }
  #app .life-tree-page .profile-radar-stage { display: none; }
  #app .life-tree-page .profile-dimension-list { grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 8px 12px; margin-top: 10px; }
  #app .life-tree-page .profile-dimension-list span { font-size: 10px; }
  #app .life-tree-page .profile-dimension-list small { font-size: 9px; }
  #app .life-tree-page .profile-summary-footer { margin-top: 10px; padding-top: 8px; }
  #app .life-tree-page .profile-summary-footer span,
  #app .life-tree-page .profile-summary-footer a { font-size: 10px; }
  #app .life-tree-page .sync-note { display: none; }
  #app .life-tree-page .week-path {
    top: 232px;
    right: 16px;
    bottom: auto;
    left: 16px;
    width: auto;
    grid-template-columns: repeat(6, minmax(0, 1fr));
    gap: 0;
    transform: none;
  }
  #app .life-tree-page .week-path-heading { display: none; }
  #app .life-tree-page .week-path::before { top: 6px; right: 8%; bottom: auto; left: 8%; width: auto; height: 1px; }
  #app .life-tree-page .week-path button { min-height: 37px; grid-template-columns: 1fr; grid-template-rows: 13px 1fr; justify-items: center; gap: 4px; text-align: center; }
  #app .life-tree-page .week-path button:hover { transform: none; }
  #app .life-tree-page .week-path button > span { display: block; }
  #app .life-tree-page .week-path button b { font-size: 10px; }
  #app .life-tree-page .week-path button b span { display: none; }
  #app .life-tree-page .week-path button em { display: none; }
  #app .life-tree-page .node-detail { right: 0; bottom: 40px; left: 0; max-height: 45vh; }
  #app .life-tree-page .partial-warning,
  #app .life-tree-page .growth-feedback { top: 172px; }
}
</style>
