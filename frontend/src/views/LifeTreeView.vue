<template>
  <main class="life-tree-page">
    <LifeTreeScene
      v-if="treeModel"
      :model="treeModel"
      :selected-id="selectedId"
      :auto-rotate="autoRotate"
      :reset-token="resetToken"
      @select="selectNode"
      @ready="sceneReady = true"
      @error="sceneError = $event"
    />

    <header class="tree-heading">
      <div>
        <span class="tree-kicker"><TreePine :size="16" />个性化学习生命树</span>
        <h1>生命树</h1>
        <p>把学习画像、路径、资源与测评证据汇成一棵持续生长的中医能力树。</p>
      </div>
      <div class="scene-controls" aria-label="三维场景控制">
        <button type="button" :aria-pressed="autoRotate" :title="autoRotate ? '暂停自动旋转' : '开启自动旋转'" @click="autoRotate = !autoRotate">
          <Pause v-if="autoRotate" :size="18" />
          <Play v-else :size="18" />
        </button>
        <button type="button" title="重置视角" aria-label="重置视角" @click="resetToken += 1">
          <Focus :size="18" />
        </button>
        <button type="button" title="刷新学习证据" aria-label="刷新学习证据" :disabled="loading" @click="loadTree">
          <RefreshCcw :class="{ spinning: loading }" :size="18" />
        </button>
      </div>
    </header>

    <aside v-if="treeModel" class="growth-panel" aria-label="生命树成长概览">
      <div class="growth-panel-head">
        <div><span>成长概览</span><strong>{{ treeModel.profile.label }}</strong></div>
        <em :class="`confidence-${treeModel.stats.confidenceLevel}`">{{ confidenceLabel(treeModel.stats.confidenceLevel) }}</em>
      </div>
      <dl class="metric-grid">
        <div>
          <dt>知识掌握</dt>
          <dd>{{ percent(treeModel.stats.masteryRate) }}</dd>
        </div>
        <div>
          <dt>学习达成</dt>
          <dd>{{ percent(treeModel.stats.achievementRate) }}</dd>
        </div>
        <div>
          <dt>已掌握节点</dt>
          <dd>{{ treeModel.stats.masteredCount }}</dd>
        </div>
        <div>
          <dt>证据总量</dt>
          <dd>{{ treeModel.stats.evidenceCount }}</dd>
        </div>
      </dl>

      <section class="signal-section">
        <div class="section-label"><Sparkles :size="15" />下一步生长信号</div>
        <button
          v-for="node in growthSignals"
          :key="node.id"
          type="button"
          :class="['signal-row', `status-${node.recommended ? 'recommended' : node.status}`]"
          @click="selectNode(node.id)"
        >
          <span></span>
          <strong>{{ node.label }}</strong>
          <small>{{ node.recommended ? '建议优先' : node.statusLabel }}</small>
        </button>
        <p v-if="!growthSignals.length">完成画像或一次专项测评后，这里会出现可行动的生长信号。</p>
      </section>

      <section class="agent-chain" aria-label="多智能体闭环链路">
        <div class="section-label"><Workflow :size="15" />协同闭环</div>
        <div>
          <span>画像分析</span><ChevronRight :size="13" />
          <span>路径规划</span><ChevronRight :size="13" />
          <span>资源生成</span><ChevronRight :size="13" />
          <span>效果评估</span>
        </div>
      </section>
    </aside>

    <aside v-if="selectedNode" class="node-detail" aria-live="polite">
      <button class="detail-close" type="button" title="关闭节点详情" aria-label="关闭节点详情" @click="selectedId = ''">
        <X :size="18" />
      </button>
      <span class="detail-eyebrow">{{ selectedNode.eyebrow || kindLabel(selectedNode.kind) }}</span>
      <h2>{{ selectedNode.label }}</h2>
      <div class="status-line">
        <span :class="`status-${selectedNode.recommended ? 'recommended' : selectedNode.status}`">
          {{ selectedNode.recommended ? '推荐下一步' : selectedNode.statusLabel }}
        </span>
        <em v-if="selectedNode.masteryRate !== null && selectedNode.masteryRate !== undefined">掌握率 {{ percent(selectedNode.masteryRate) }}</em>
        <em v-else-if="selectedNode.score !== null && selectedNode.score !== undefined">画像评分 {{ Number(selectedNode.score).toFixed(1) }}/5</em>
      </div>
      <p v-if="selectedNode.description" class="detail-description">{{ selectedNode.description }}</p>
      <div class="evidence-block">
        <span><ShieldCheck :size="15" />状态依据</span>
        <p>{{ selectedNode.evidence }}</p>
      </div>
      <div v-if="selectedNode.reason" class="reason-block">
        <span><Lightbulb :size="15" />推荐解释</span>
        <p>{{ selectedNode.reason }}</p>
      </div>
      <small class="updated-at">{{ updatedLabel(selectedNode.updatedAt || treeModel.updatedAt) }}</small>
      <RouterLink v-if="selectedNode.action" class="detail-action" :to="selectedNode.action.to">
        {{ selectedNode.action.label }}<ArrowRight :size="16" />
      </RouterLink>
    </aside>

    <div v-if="loading || !sceneReady" class="scene-state" role="status">
      <LoaderCircle class="spinning" :size="26" />
      <strong>{{ loading ? '正在汇聚学习证据' : '正在生长三维生命树' }}</strong>
      <span>画像、路径、资源与评估状态正在对齐</span>
    </div>

    <div v-else-if="fatalError || sceneError" class="scene-state error" role="alert">
      <CircleAlert :size="26" />
      <strong>生命树暂时无法生长</strong>
      <span>{{ fatalError || sceneError }}</span>
      <button type="button" @click="loadTree"><RefreshCcw :size="16" />重新加载</button>
      <RouterLink to="/learning-profile">检查学习画像</RouterLink>
    </div>

    <div v-else-if="treeModel?.empty && !selectedNode" class="empty-notice">
      <Sprout :size="18" />
      <div><strong>能力骨架已建立，等待第一条成长证据</strong><span>完成学习画像、进入当前周或参加一次测评即可点亮节点。</span></div>
      <RouterLink to="/learning-profile">建立画像</RouterLink>
    </div>

    <div v-if="warning && !fatalError" class="partial-warning" role="status">
      <CircleAlert :size="15" /><span>{{ warning }}</span>
    </div>

    <footer class="tree-legend" aria-label="生命树状态图例">
      <span v-for="item in legend" :key="item.status"><i :class="`status-${item.status}`"></i>{{ item.label }}</span>
      <small>拖拽旋转 · 滚轮缩放 · 点击节点查看依据</small>
    </footer>
  </main>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { RouterLink, useRoute } from 'vue-router'
import {
  ArrowRight,
  ChevronRight,
  CircleAlert,
  Focus,
  Lightbulb,
  LoaderCircle,
  Pause,
  Play,
  RefreshCcw,
  ShieldCheck,
  Sparkles,
  Sprout,
  TreePine,
  Workflow,
  X,
} from 'lucide-vue-next'
import LifeTreeScene from '../components/LifeTreeScene.vue'
import { getEffectAssessment, getLearningPathConfig } from '../services/api.js'
import { buildLifeTreeModel } from '../utils/lifeTreeModel.js'

const route = useRoute()
const loading = ref(true)
const sceneReady = ref(false)
const fatalError = ref('')
const sceneError = ref('')
const warning = ref('')
const treeModel = ref(null)
const selectedId = ref('')
const autoRotate = ref(true)
const resetToken = ref(0)

const legend = [
  { status: 'mastered', label: '已掌握' },
  { status: 'developing', label: '学习中' },
  { status: 'weak', label: '薄弱' },
  { status: 'recommended', label: '推荐下一步' },
  { status: 'unverified', label: '待验证' },
]

const allNodes = computed(() => {
  if (!treeModel.value) return []
  return [treeModel.value.profile, ...treeModel.value.branches, ...treeModel.value.nodes]
})
const selectedNode = computed(() => allNodes.value.find((node) => node.id === selectedId.value) || null)
const growthSignals = computed(() => {
  const nodes = treeModel.value?.nodes || []
  return [
    ...nodes.filter((node) => node.recommended),
    ...nodes.filter((node) => node.status === 'weak' && !node.recommended),
    ...nodes.filter((node) => node.status === 'developing' && !node.recommended),
  ].slice(0, 4)
})

function percent(value) {
  if (value === null || value === undefined || !Number.isFinite(Number(value))) return '待验证'
  return `${Number(value).toFixed(1)}%`
}

function confidenceLabel(value) {
  return ({ high: '高置信度', medium: '中等置信度', low: '证据待补充' })[value] || '证据待补充'
}

function kindLabel(value) {
  return ({ profile: '学习画像', branch: '能力主枝', knowledge: '知识节点', path: '学习路径节点' })[value] || '成长节点'
}

function updatedLabel(value) {
  if (!value) return '尚无可核验更新时间'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return '更新时间未记录'
  return `证据更新于 ${date.toLocaleString('zh-CN', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' })}`
}

function selectNode(nodeId) {
  selectedId.value = nodeId
  if (nodeId) autoRotate.value = false
}

function errorMessage(result, fallback) {
  const reason = result?.reason
  return reason?.response?.data?.msg || reason?.message || fallback
}

async function loadTree() {
  loading.value = true
  fatalError.value = ''
  sceneError.value = ''
  warning.value = ''
  sceneReady.value = false
  try {
    const [assessmentResult, pathResult] = await Promise.allSettled([
      getEffectAssessment(route.query.profileId || ''),
      getLearningPathConfig(),
    ])
    const assessmentPayload = assessmentResult.status === 'fulfilled' ? assessmentResult.value : {}
    const pathConfig = pathResult.status === 'fulfilled' ? pathResult.value : {}
    const nextModel = buildLifeTreeModel({ ...assessmentPayload, pathConfig })
    treeModel.value = nextModel

    if (assessmentResult.status === 'rejected' && pathResult.status === 'rejected') {
      fatalError.value = errorMessage(assessmentResult, '学习画像与效果评估数据加载失败')
      return
    }
    if (assessmentResult.status === 'rejected') {
      warning.value = `${errorMessage(assessmentResult, '效果评估暂不可用')}；当前仅显示学习路径骨架。`
    } else if (pathResult.status === 'rejected') {
      warning.value = `${errorMessage(pathResult, '学习路径暂不可用')}；当前仅显示画像与评估证据。`
    }

    const preferred = nextModel.nodes.find((node) => node.recommended)
      || nextModel.nodes.find((node) => node.status === 'weak')
      || nextModel.profile
    selectedId.value = preferred?.id || ''
  } finally {
    loading.value = false
  }
}

onMounted(loadTree)
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

.signal-section,
.agent-chain { margin-top: 18px; }
.section-label { display: flex; align-items: center; gap: 6px; color: #c7d5d0; font-size: 11px; font-weight: 750; }
.signal-section > p { margin: 11px 0 0; color: #8fa29b; font-size: 11px; line-height: 1.55; }

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

.signal-row > span { width: 7px; height: 7px; border-radius: 50%; background: #9ca8a3; }
.signal-row strong { min-width: 0; overflow: hidden; font-size: 11px; text-overflow: ellipsis; white-space: nowrap; }
.signal-row small { color: #91a39c; font-size: 9px; }
.signal-row:hover strong { color: #74d7aa; }

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
  .growth-panel { width: 260px; }
  .node-detail { width: 270px; }
  .agent-chain { display: none; }
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
    width: 224px;
    padding: 12px;
  }
  .growth-panel-head { padding-bottom: 9px; }
  .growth-panel-head strong { font-size: 12px; }
  .metric-grid { margin-top: 9px; }
  .metric-grid div { padding: 8px; }
  .metric-grid dd { font-size: 15px; }
  .signal-section { margin-top: 11px; }
  .signal-row:nth-of-type(n + 4) { display: none; }
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
  .node-detail h2 { margin-top: 5px; margin-bottom: 8px; font-size: 17px; }
  .detail-description { margin-top: 9px; }
  .evidence-block,
  .reason-block { margin-top: 10px; padding-top: 9px; }
  .detail-action { position: sticky; bottom: 0; }
  .tree-legend { right: 12px; bottom: 12px; left: 12px; gap: 8px; justify-content: flex-end; }
  .tree-legend span { font-size: 0; }
  .tree-legend span i { width: 9px; height: 9px; }
  .tree-legend small { margin: 0; font-size: 8px; }
  .empty-notice { bottom: 48px; }
}

@media (max-width: 520px) {
  .tree-heading > div:first-child { width: calc(100vw - 160px); }
  .tree-heading p { display: none; }
  .growth-panel {
    top: 74px;
    right: 16px;
    width: auto;
    padding: 9px 10px;
  }
  .growth-panel-head { display: none; }
  .metric-grid { grid-template-columns: repeat(4, minmax(0, 1fr)); margin: 0; }
  .metric-grid div { padding: 7px 5px; text-align: center; }
  .metric-grid dt { overflow: hidden; font-size: 8px; text-overflow: ellipsis; white-space: nowrap; }
  .metric-grid dd { margin-top: 3px; font-size: 12px; }
  .signal-section { display: none; }
  .node-detail { bottom: 42px; max-height: 40vh; }
  .tree-legend { justify-content: center; }
  .tree-legend small { display: none; }
  .partial-warning { top: 126px; width: calc(100% - 32px); box-sizing: border-box; }
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
</style>
