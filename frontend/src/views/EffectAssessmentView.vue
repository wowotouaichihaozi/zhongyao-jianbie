<template>
  <main class="assessment-page">
    <section class="assessment-head">
      <div>
        <p>学习效果评估</p>
        <h1>学习进展与路径调整</h1>
        <span>基于聊天、答题、实验、资源调用和路径完成记录计算，不对缺失证据做推断。</span>
      </div>
      <button type="button" :disabled="updating || !profile?.id" @click="updateProfile">
        <RefreshCcw :size="17" :class="{ spinning: updating }" />
        {{ updating ? '正在更新画像' : '更新学习画像' }}
      </button>
    </section>

    <section v-if="loading" class="loading-state">正在汇总学习记录...</section>
    <section v-else-if="error" class="loading-state error">{{ error }}</section>
    <template v-else>
      <section class="metric-grid" aria-label="学习效果核心指标">
        <article>
          <Target :size="20" />
          <span>学习达成率</span>
          <strong>{{ formatPercent(assessment.achievementRate) }}</strong>
          <small>路径、考试与实验综合</small>
        </article>
        <article>
          <BrainCircuit :size="20" />
          <span>知识掌握率</span>
          <strong>{{ formatPercent(assessment.masteryRate) }}</strong>
          <small>按有效知识证据加权</small>
        </article>
        <article>
          <Clock3 :size="20" />
          <span>学习时长</span>
          <strong>{{ assessment.learningDurationText }}</strong>
          <small>{{ assessment.activeLearningDays || 0 }} 个活跃学习日</small>
        </article>
        <article>
          <Layers3 :size="20" />
          <span>资源足迹</span>
          <strong>{{ assessment.resourceCount || 0 }} 次</strong>
          <small>{{ assessment.resourceTypes?.length || 0 }} 类实际访问</small>
        </article>
        <article>
          <CheckCircle2 :size="20" />
          <span>路径完成</span>
          <strong>{{ assessment.completedNodes || 0 }} / {{ assessment.trackedNodes || 0 }}</strong>
          <small>已完成任务 / 已跟踪任务</small>
        </article>
        <article>
          <ShieldCheck :size="20" />
          <span>证据置信度</span>
          <strong>{{ assessment.confidenceScore || 0 }}%</strong>
          <small>{{ confidenceLabel(assessment.confidenceLevel) }}</small>
        </article>
      </section>

      <section class="assessment-grid">
        <article class="panel radar-card">
          <div class="card-title">
            <div><span>能力雷达</span><h2>本次较上次的变化</h2></div>
            <em>证据驱动</em>
          </div>
          <div class="radar-wrap">
            <svg :key="assessment.updatedAt" viewBox="0 0 360 360" aria-label="学习能力雷达图">
              <g v-for="level in 5" :key="level"><polygon :points="polygon(level / 5)" class="grid" /></g>
              <line v-for="(_, index) in labels" :key="`axis-${index}`" x1="180" y1="180" :x2="axisPoint(index).x" :y2="axisPoint(index).y" />
              <polygon :points="dataPolygon(previousScores)" class="radar-before" />
              <polygon :points="dataPolygon(currentScores)" class="radar-after" />
              <text v-for="(label, index) in labels" :key="label" :x="labelPoint(index).x" :y="labelPoint(index).y" :text-anchor="labelAnchor(index)">{{ label }}</text>
            </svg>
            <div class="radar-legend">
              <span><i class="before"></i>上次画像</span>
              <span><i class="after"></i>本次评估</span>
            </div>
          </div>
        </article>

        <article class="panel insight-card">
          <div class="card-title"><div><span>进步对比</span><h2>证据支持的提升</h2></div></div>
          <div v-if="assessment.improvements?.length" class="improvement-list">
            <div v-for="item in assessment.improvements" :key="item.label">
              <span>{{ item.label }}</span>
              <strong>+{{ Number(item.delta || 0).toFixed(1) }}</strong>
            </div>
          </div>
          <p v-else>继续完成题单、实验和路径任务后，系统会在这里展示可验证的变化。</p>
          <div class="weak-panel">
            <span>当前薄弱点</span>
            <div>
              <b v-for="point in assessment.weakPoints?.slice(0, 6)" :key="point">{{ point }}</b>
              <em v-if="!assessment.weakPoints?.length">暂无明确薄弱点</em>
            </div>
          </div>
        </article>
      </section>

      <section class="diagnosis-grid">
        <article class="panel heatmap-panel">
          <div class="card-title">
            <div><span>知识点热力图</span><h2>掌握证据分布</h2></div>
            <em>{{ assessment.knowledgeHeatmap?.length || 0 }} 个知识点</em>
          </div>
          <div v-if="assessment.knowledgeHeatmap?.length" class="heatmap-list">
            <div v-for="item in assessment.knowledgeHeatmap" :key="item.knowledgePoint" :class="['heatmap-row', item.status]">
              <div>
                <strong>{{ item.knowledgePoint }}</strong>
                <small>{{ heatmapStatusLabel(item.status) }} · {{ item.attempts || 0 }} 条证据</small>
              </div>
              <div class="heatmap-rate">
                <span>{{ formatPercent(item.masteryRate) }}</span>
                <i><b :style="{ width: `${Math.max(0, Math.min(100, Number(item.masteryRate || 0)))}%` }"></b></i>
              </div>
            </div>
          </div>
          <p v-else class="empty-copy">完成题单或实验后，这里会按知识点聚合掌握证据。</p>
        </article>

        <article class="panel adjustment-panel">
          <div class="card-title">
            <div><span>动态学习计划</span><h2>{{ adjustmentPlan.targetWeekLabel || '当前周' }}调整建议</h2></div>
            <em :class="['plan-state', adjustmentPlan.status]">{{ adjustmentStatusLabel }}</em>
          </div>
          <p class="adjustment-reason">{{ adjustmentPlan.reason || '当前没有需要追加的学习任务。' }}</p>
          <div v-if="adjustmentPlan.tasks?.length" class="adjustment-list">
            <div v-for="(task, index) in adjustmentPlan.tasks" :key="task.nodeId">
              <span>{{ String(index + 1).padStart(2, '0') }}</span>
              <div>
                <strong>{{ task.title }}</strong>
                <p>{{ task.acceptanceCriteria }}</p>
                <small>{{ resourceLabel(task.resourceType) }} · 当前掌握率 {{ formatPercent(task.currentMasteryRate) }}</small>
              </div>
            </div>
          </div>
          <div v-if="actionError" class="action-message error">{{ actionError }}</div>
          <div v-else-if="actionMessage" class="action-message">{{ actionMessage }}</div>
          <div class="adjustment-actions">
            <button type="button" :disabled="!canApplyAdjustment || applying" @click="applyAdjustment">
              <Route :size="17" />
              {{ applying ? '正在应用' : adjustmentPlan.status === 'applied' ? '已应用到学习路径' : '应用到学习路径' }}
            </button>
            <RouterLink v-if="adjustmentPlan.status === 'applied'" to="/learning-path">查看学习路径</RouterLink>
          </div>
        </article>
      </section>

      <section class="evidence-grid">
        <article class="panel resource-evidence">
          <div class="card-title">
            <div><span>资源足迹</span><h2>已进入的资源</h2></div>
            <em>{{ assessment.resourceCount || 0 }} 次访问</em>
          </div>
          <div class="chip-row">
            <span v-for="item in assessment.resourceTypes" :key="item">{{ resourceLabel(item) }}</span>
            <em v-if="!assessment.resourceTypes?.length">暂无实际访问记录</em>
          </div>
          <div v-if="assessment.resourceVisits?.length" class="resource-visit-list">
            <div v-for="(item, index) in assessment.resourceVisits.slice(0, 8)" :key="`${item.createdAt}-${index}`">
              <strong>{{ resourceLabel(item.type) }}</strong>
              <span>{{ formatVisitTime(item.createdAt) }}</span>
            </div>
          </div>
        </article>
        <article class="panel path-evidence">
          <div class="card-title">
            <div><span>路径证据</span><h2>学习路径进度</h2></div>
            <em v-if="pathUpdatedAt">更新于 {{ pathUpdatedAt }}</em>
          </div>
          <template v-if="hasPathProgress">
            <div v-if="hasPathCounts || pathProgressText" class="path-overview">
              <div v-if="hasPathCounts" class="path-counts">
                <span v-if="pathCompletedNodes !== null"><strong>{{ pathCompletedNodes }}</strong><small>已完成</small></span>
                <span v-if="pathTrackedNodes !== null"><strong>{{ pathTrackedNodes }}</strong><small>已跟踪</small></span>
              </div>
              <div v-if="pathProgressText" class="path-progress-result">
                <span><small>完成进度</small><strong>{{ pathProgressText }}</strong></span>
              </div>
            </div>
            <div
              v-if="pathProgressPercent !== null"
              class="path-progress-track"
              role="progressbar"
              aria-label="学习路径完成进度"
              aria-valuemin="0"
              aria-valuemax="100"
              :aria-valuenow="pathProgressPercent"
            >
              <i><b :style="{ width: `${pathProgressPercent}%` }"></b></i>
            </div>
            <div v-if="currentPathWeek" class="current-path-week">
              <span>当前阶段</span>
              <div>
                <strong>{{ pathWeekLabel(currentPathWeek) }}</strong>
                <small v-if="pathWeekTitle(currentPathWeek)">{{ pathWeekTitle(currentPathWeek) }}</small>
              </div>
              <em :class="['week-status', pathStatusClass(currentPathWeek.status)]">{{ pathStatusLabel(currentPathWeek.status) }}</em>
            </div>
            <div v-if="pathWeeks.length" class="path-week-list">
              <div v-for="(week, index) in pathWeeks" :key="week.weekId || `${pathWeekLabel(week)}-${index}`">
                <div>
                  <strong>{{ pathWeekLabel(week) }}</strong>
                  <small v-if="pathWeekTitle(week)">{{ pathWeekTitle(week) }}</small>
                </div>
                <span :class="['week-status', pathStatusClass(week.status)]">{{ pathStatusLabel(week.status) }}</span>
              </div>
            </div>
          </template>
          <p v-else class="empty-copy">尚未生成学习路径。</p>
        </article>
        <article id="learning-feedback" class="panel feedback-evidence">
          <div class="card-title">
            <div><span>学习反馈闭环</span><h2>资源完成与巩固记录</h2></div>
            <em>{{ evidence.learningFeedbacks?.length || 0 }} 条</em>
          </div>
          <div v-if="evidence.learningFeedbacks?.length" class="feedback-list">
            <div v-for="item in evidence.learningFeedbacks.slice(0, 10)" :key="item.id">
              <span :class="`outcome-${item.outcome}`">{{ feedbackOutcomeLabel(item.outcome) }}</span>
              <strong>{{ item.topic || resourceLabel(item.resourceType) }}</strong>
              <small>{{ resourceLabel(item.resourceType) }} · {{ feedbackDifficultyLabel(item.difficulty) }} · {{ formatVisitTime(item.updatedAt) }}</small>
            </div>
          </div>
          <p v-else class="empty-copy">完成资源后提交学习结果，这里会保留可用于画像和路径调整的反馈证据。</p>
        </article>
      </section>
    </template>
  </main>
</template>

<script setup>
import { computed, nextTick, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import {
  BrainCircuit,
  CheckCircle2,
  Clock3,
  Layers3,
  RefreshCcw,
  Route,
  ShieldCheck,
  Target,
} from 'lucide-vue-next'
import {
  applyEffectAssessmentAdjustment,
  getEffectAssessment,
  refreshLearningProfile,
} from '../services/api.js'

const route = useRoute()
const loading = ref(true)
const updating = ref(false)
const applying = ref(false)
const error = ref('')
const actionError = ref('')
const actionMessage = ref('')
const profile = ref(null)
const evidence = ref({})
const assessment = ref({})

const labels = computed(() => assessment.value.labels || ['基础知识', '辨证思维', '方药应用', '医案实践', '学习投入', '综合素养'])
const previousScores = computed(() => assessment.value.previousRadarScores || [2, 2, 2, 2, 2, 2])
const currentScores = computed(() => assessment.value.radarScores || previousScores.value)
const adjustmentPlan = computed(() => assessment.value.pathAdjustmentPlan || {})
const pathProgress = computed(() => {
  const value = evidence.value.pathProgress
  return value && typeof value === 'object' && !Array.isArray(value) ? value : {}
})
const pathWeeks = computed(() => {
  const weeks = Array.isArray(pathProgress.value.weeks) ? pathProgress.value.weeks : []
  return weeks.filter((week) => (
    week
    && typeof week === 'object'
    && (week.week || week.title || week.weekId)
  ))
})
const pathCompletedNodes = computed(() => evidenceNumber(pathProgress.value.completedNodes))
const pathTrackedNodes = computed(() => evidenceNumber(pathProgress.value.trackedNodes))
const hasPathCounts = computed(() => pathCompletedNodes.value !== null || pathTrackedNodes.value !== null)
const derivedPathProgress = computed(() => {
  if (pathCompletedNodes.value === null || !pathTrackedNodes.value) return null
  return pathCompletedNodes.value / pathTrackedNodes.value * 100
})
const pathProgressPercent = computed(() => {
  const value = derivedPathProgress.value
  return value === null ? null : Math.max(0, Math.min(100, value))
})
const pathProgressText = computed(() => (
  derivedPathProgress.value === null ? '' : formatPercent(derivedPathProgress.value)
))
const currentPathWeek = computed(() => pathWeeks.value.find((week) => {
  const status = String(week.status || '').trim().toLowerCase().replaceAll('_', '-').replaceAll(' ', '-')
  return ['current', 'active', 'in-progress', 'running'].includes(status)
}) || null)
const pathUpdatedAt = computed(() => formatOptionalTime(pathProgress.value.updatedAt))
const hasPathProgress = computed(() => (
  pathWeeks.value.length > 0
  || Number(pathCompletedNodes.value || 0) > 0
  || Number(pathTrackedNodes.value || 0) > 0
))
const canApplyAdjustment = computed(() => (
  Boolean(adjustmentPlan.value.canApply)
  && adjustmentPlan.value.status !== 'applied'
  && Boolean(profile.value?.isActive)
))
const adjustmentStatusLabel = computed(() => {
  if (adjustmentPlan.value.status === 'applied') return '已应用'
  if (!profile.value?.isActive) return '需切换为当前画像'
  if (!adjustmentPlan.value.canApply) return '暂无可应用任务'
  return '待确认'
})

function point(index, value = 1, radius = 124) {
  const angle = (Math.PI * 2 * index / labels.value.length) - Math.PI / 2
  return { x: 180 + radius * value * Math.cos(angle), y: 180 + radius * value * Math.sin(angle) }
}

function polygon(ratio) {
  return labels.value.map((_, index) => {
    const item = point(index, ratio)
    return `${item.x},${item.y}`
  }).join(' ')
}

function dataPolygon(scores) {
  return scores.map((score, index) => {
    const item = point(index, Number(score || 0) / 5)
    return `${item.x},${item.y}`
  }).join(' ')
}

function axisPoint(index) { return point(index) }
function labelPoint(index) { return point(index, 1, 150) }
function labelAnchor(index) {
  const x = labelPoint(index).x
  return Math.abs(x - 180) < 10 ? 'middle' : x > 180 ? 'start' : 'end'
}

function formatPercent(value) { return `${Number(value || 0).toFixed(1)}%` }
function confidenceLabel(value) { return ({ high: '高置信度', medium: '中等置信度', low: '证据仍需补充' })[value] || '证据仍需补充' }
function heatmapStatusLabel(value) { return ({ mastered: '已掌握', developing: '巩固中', weak: '薄弱', unverified: '待验证' })[value] || '待验证' }
function feedbackOutcomeLabel(value) { return ({ completed: '已完成', needs_review: '需巩固', blocked: '有阻塞' })[value] || '已记录' }
function feedbackDifficultyLabel(value) { return ({ easy: '偏简单', appropriate: '难度适中', hard: '偏困难' })[value] || '难度未标记' }
function evidenceNumber(value) {
  if (value === undefined || value === null || value === '') return null
  const number = Number(value)
  return Number.isFinite(number) && number >= 0 ? number : null
}
function pathStatusLabel(value) {
  const raw = String(value || '').trim()
  const normalized = raw.toLowerCase().replaceAll('_', '-').replaceAll(' ', '-')
  return ({
    complete: '已完成',
    completed: '已完成',
    done: '已完成',
    success: '已完成',
    current: '当前阶段',
    active: '进行中',
    'in-progress': '进行中',
    running: '进行中',
    locked: '待解锁',
    pending: '待开始',
    waiting: '待开始',
    blocked: '有阻塞',
    failed: '有阻塞',
    'not-generated': '未生成',
  })[normalized] || raw || '状态未记录'
}
function pathStatusClass(value) {
  const normalized = String(value || '').trim().toLowerCase().replaceAll('_', '-').replaceAll(' ', '-')
  if (['complete', 'completed', 'done', 'success'].includes(normalized)) return 'is-complete'
  if (['current', 'active', 'in-progress', 'running'].includes(normalized)) return 'is-current'
  if (['blocked', 'failed'].includes(normalized)) return 'is-blocked'
  if (['locked', 'pending', 'waiting', 'not-generated'].includes(normalized)) return 'is-pending'
  return 'is-neutral'
}
function pathWeekLabel(week) { return String(week.week || week.title || week.weekId || '').trim() }
function pathWeekTitle(week) {
  const title = String(week.title || '').trim()
  return title && title !== pathWeekLabel(week) ? title : ''
}
function resourceLabel(value) {
  return ({
    mindmap: '思维导图',
    ppt: 'PPT',
    video: '学习视频',
    quiz: '题库',
    'question-bank': '题库',
    simulator: '课程讲义',
    mcu: '课程讲义',
    document: '课程讲义',
    animation: '动画讲解',
    'knowledge-base': '私有知识库',
  })[value] || value
}

function formatVisitTime(value) {
  return formatOptionalTime(value) || '时间未记录'
}

function formatOptionalTime(value) {
  if (!value) return ''
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return ''
  return date.toLocaleString('zh-CN', {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  })
}

async function load() {
  loading.value = true
  error.value = ''
  actionError.value = ''
  try {
    const data = await getEffectAssessment(route.query.profileId)
    profile.value = data.profile
    evidence.value = data.evidence || {}
    assessment.value = data.assessment || {}
    if (route.query.section === 'feedback') {
      await nextTick()
      document.getElementById('learning-feedback')?.scrollIntoView({ block: 'center' })
    }
  } catch (err) {
    error.value = err?.response?.data?.msg || err?.message || '效果评估加载失败'
  } finally {
    loading.value = false
  }
}

async function updateProfile() {
  if (!profile.value?.id || updating.value) return
  updating.value = true
  actionMessage.value = ''
  actionError.value = ''
  try {
    await refreshLearningProfile(profile.value.id)
    await load()
    actionMessage.value = '学习画像已根据最新证据更新。'
  } catch (err) {
    actionError.value = err?.response?.data?.msg || err?.message || '学习画像更新失败'
  } finally {
    updating.value = false
  }
}

async function applyAdjustment() {
  if (!canApplyAdjustment.value || applying.value) return
  applying.value = true
  actionMessage.value = ''
  actionError.value = ''
  try {
    const data = await applyEffectAssessmentAdjustment(profile.value.id, adjustmentPlan.value.planId)
    assessment.value = {
      ...assessment.value,
      pathAdjustmentPlan: {
        ...adjustmentPlan.value,
        status: 'applied',
        appliedAt: data.pathAdjustment?.appliedAt || new Date().toISOString(),
        assessmentId: data.assessmentId,
      },
    }
    actionMessage.value = data.alreadyApplied
      ? '该调整计划此前已经应用。'
      : `已向${data.pathAdjustment?.targetWeekLabel || '当前周'}追加 ${data.pathAdjustment?.addedCount || 0} 个巩固任务。`
  } catch (err) {
    actionError.value = err?.response?.data?.msg || err?.message || '路径调整应用失败'
  } finally {
    applying.value = false
  }
}

onMounted(load)
watch(() => route.query.profileId, load)
</script>

<style scoped>
.resource-visit-list{display:grid;margin-top:16px;border-top:1px solid #e5efea}.resource-visit-list div{display:flex;justify-content:space-between;gap:16px;padding:10px 0;border-bottom:1px solid #edf3f0;font-size:13px}.resource-visit-list strong{color:#315f54}.resource-visit-list span{color:#82958e;white-space:nowrap}
.assessment-page{max-width:1280px;margin:0 auto;padding:34px 34px 64px;color:#193b36}.assessment-head{display:flex;justify-content:space-between;align-items:flex-end;gap:24px;margin-bottom:24px}.assessment-head p,.card-title span{margin:0;color:#23875d;font-size:14px;font-weight:700}.assessment-head h1{margin:7px 0 8px;font-size:28px;letter-spacing:0}.assessment-head>div>span{color:#6c817b}.assessment-head button,.adjustment-actions button{display:flex;align-items:center;gap:8px;border:0;border-radius:6px;background:#177c51;color:#fff;padding:11px 16px;font-size:14px;cursor:pointer}.assessment-head button:disabled,.adjustment-actions button:disabled{cursor:not-allowed;opacity:.58}.spinning{animation:spin 1s linear infinite}.metric-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:14px}.metric-grid article,.panel{min-width:0;background:#fff;border:1px solid #dceae4;border-radius:8px}.metric-grid article{padding:18px;display:grid;grid-template-columns:22px minmax(0,1fr);column-gap:9px}.metric-grid svg{color:#229969}.metric-grid span{color:#6c817b;font-size:13px}.metric-grid strong{grid-column:1/-1;margin-top:10px;font-size:23px;letter-spacing:0}.metric-grid small{grid-column:1/-1;margin-top:5px;color:#8a9c96;font-size:12px}.assessment-grid,.diagnosis-grid,.evidence-grid{display:grid;gap:16px;margin-top:16px}.assessment-grid{grid-template-columns:minmax(0,1.25fr) minmax(300px,.75fr)}.diagnosis-grid{grid-template-columns:minmax(0,1.05fr) minmax(360px,.95fr)}.evidence-grid{grid-template-columns:1fr 1fr}.panel{padding:22px}.card-title{display:flex;justify-content:space-between;align-items:flex-start;gap:16px}.card-title h2,.evidence-grid h2{margin:4px 0 0;font-size:18px;letter-spacing:0}.card-title em{font-style:normal;color:#6c817b;font-size:12px}.radar-wrap{display:grid;grid-template-columns:minmax(0,1fr) 118px;align-items:center}.radar-wrap svg{width:100%;max-height:340px}.radar-wrap line{stroke:#cdded7}.grid{fill:none;stroke:#dbe8e3}.radar-before{fill:rgba(55,124,216,.16);stroke:#4b7ed4;stroke-width:2}.radar-after{fill:rgba(37,172,104,.25);stroke:#16875a;stroke-width:3;transform-origin:180px 180px;animation:radar-grow 1s ease-out}.radar-wrap text{font-size:12px;fill:#4e6961}.radar-legend{display:grid;gap:10px;color:#547068;font-size:13px}.radar-legend i{display:inline-block;width:10px;height:10px;border-radius:50%;margin-right:6px}.before{background:#4b7ed4}.after{background:#16875a}.improvement-list{margin-top:22px;display:grid;gap:10px}.improvement-list div{display:flex;justify-content:space-between;padding:10px 0;border-bottom:1px solid #edf3f0}.improvement-list strong{color:#188a58}.insight-card>p{margin-top:24px;color:#6c817b;line-height:1.7}.weak-panel{margin-top:28px;padding-top:17px;border-top:1px solid #e5efea}.weak-panel>span{font-weight:700}.weak-panel div,.chip-row,.week-row{display:flex;flex-wrap:wrap;gap:8px;margin-top:12px}.weak-panel b,.chip-row span,.week-row span{font-size:13px;font-weight:600;border-radius:4px;padding:6px 9px;background:#fff2ee;color:#b65335}.chip-row span{background:#e9f8ef;color:#16774f}.week-row span{background:#eef5f2;color:#647b73}.week-row span.current,.week-row span.active,.week-row span.done,.week-row span.completed{background:#d8f4e4;color:#147649}.weak-panel em,.chip-row em,.week-row em{font-style:normal;color:#84958f;font-size:13px}.heatmap-list{display:grid;gap:0;margin-top:18px}.heatmap-row{display:grid;grid-template-columns:minmax(0,1fr) 150px;align-items:center;gap:18px;padding:12px 0;border-bottom:1px solid #e7efeb}.heatmap-row:last-child{border-bottom:0}.heatmap-row>div:first-child{display:grid;gap:4px}.heatmap-row strong{font-size:14px}.heatmap-row small{color:#7b8e87}.heatmap-rate{display:grid;grid-template-columns:48px minmax(0,1fr);align-items:center;gap:10px}.heatmap-rate span{font-size:12px;font-weight:700;text-align:right}.heatmap-rate i{height:7px;overflow:hidden;border-radius:4px;background:#edf2ef}.heatmap-rate b{display:block;height:100%;border-radius:4px;background:#e6a23c}.heatmap-row.mastered .heatmap-rate b{background:#1c9a64}.heatmap-row.developing .heatmap-rate b{background:#62a872}.heatmap-row.weak .heatmap-rate b{background:#d96c4b}.heatmap-row.unverified .heatmap-rate b{background:#a9b7b1}.empty-copy,.adjustment-reason{color:#6c817b;line-height:1.7}.adjustment-reason{margin:18px 0}.plan-state{padding:5px 8px;border-radius:4px;background:#eef5f2}.plan-state.applied{background:#dcf5e7;color:#147649}.adjustment-list{display:grid;border-top:1px solid #e5efea}.adjustment-list>div{display:grid;grid-template-columns:28px minmax(0,1fr);gap:10px;padding:13px 0;border-bottom:1px solid #e5efea}.adjustment-list>div>span{color:#1b8c5c;font-size:12px;font-weight:800}.adjustment-list>div>div{min-width:0}.adjustment-list strong{font-size:14px}.adjustment-list p{margin:5px 0;color:#536b63;font-size:13px;line-height:1.55}.adjustment-list small{color:#87978f}.adjustment-actions{display:flex;align-items:center;gap:14px;margin-top:18px}.adjustment-actions a{color:#177c51;font-size:13px;font-weight:700}.action-message{margin-top:14px;color:#177c51;font-size:13px}.action-message.error{color:#b74f38}.loading-state{padding:80px;text-align:center;color:#648078}.loading-state.error{color:#bb4f39}@keyframes radar-grow{from{transform:scale(.05);opacity:.1}to{transform:scale(1);opacity:1}}@keyframes spin{to{transform:rotate(360deg)}}@media(max-width:950px){.assessment-grid,.diagnosis-grid,.evidence-grid{grid-template-columns:1fr}.radar-wrap{grid-template-columns:1fr}.radar-legend{display:flex;justify-content:center}}@media(max-width:720px){.assessment-page{padding:24px 16px 88px}.assessment-head{align-items:stretch;flex-direction:column}.assessment-head button{align-self:flex-start}.metric-grid{grid-template-columns:1fr 1fr}.panel{padding:18px}.heatmap-row{grid-template-columns:1fr}.heatmap-rate{grid-template-columns:48px minmax(0,1fr)}.adjustment-actions{align-items:flex-start;flex-direction:column}}@media(max-width:430px){.metric-grid{grid-template-columns:1fr}.assessment-head h1{font-size:25px}}
.feedback-evidence { grid-column: 1 / -1; }
.feedback-list { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 0 24px; margin-top: 16px; }
.feedback-list > div { min-width: 0; display: grid; grid-template-columns: auto minmax(0, 1fr); gap: 3px 9px; align-items: center; padding: 11px 0; border-top: 1px solid #e5efea; }
.feedback-list > div > span { grid-row: 1 / 3; min-width: 54px; padding: 5px 7px; border-radius: 4px; background: #e8f7f0; color: #17724f; font-size: 11px; font-weight: 800; text-align: center; }
.feedback-list > div > span.outcome-needs_review { background: #fff4df; color: #9a6920; }
.feedback-list > div > span.outcome-blocked { background: #fff0ec; color: #a64b36; }
.feedback-list strong { min-width: 0; overflow: hidden; color: #29483e; font-size: 13px; text-overflow: ellipsis; white-space: nowrap; }
.feedback-list small { color: #7d8f88; font-size: 11px; }
@media (max-width: 720px) { .feedback-list { grid-template-columns: 1fr; } }

.assessment-page {
  width: 100%;
  max-width: none;
  height: calc(100vh - 72px);
  height: calc(100dvh - 72px);
  max-height: calc(100vh - 72px);
  max-height: calc(100dvh - 72px);
  margin: 0;
  padding: 34px max(34px, calc((100vw - 1280px) / 2 + 34px)) 64px;
  overflow-x: hidden;
  overflow-y: scroll;
  scrollbar-gutter: stable;
  scrollbar-color: #8fbda9 #edf5f1;
  scrollbar-width: thin;
}

.assessment-page::-webkit-scrollbar {
  width: 10px;
}

.assessment-page::-webkit-scrollbar-track {
  background: #edf5f1;
}

.assessment-page::-webkit-scrollbar-thumb {
  border: 2px solid #edf5f1;
  border-radius: 8px;
  background: #8fbda9;
}

.assessment-page::-webkit-scrollbar-thumb:hover {
  background: #659f86;
}

.assessment-grid,
.diagnosis-grid,
.evidence-grid {
  align-items: start;
  grid-auto-rows: max-content;
}

.evidence-grid {
  grid-template-columns: minmax(0, .9fr) minmax(0, 1.1fr);
}

.insight-card,
.heatmap-panel,
.adjustment-panel,
.resource-evidence,
.path-evidence,
.feedback-evidence {
  align-self: start;
}

.panel {
  padding: 20px;
}

.chip-row {
  margin-top: 10px;
}

.resource-visit-list {
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0 18px;
  margin-top: 12px;
}

.resource-visit-list div {
  min-width: 0;
  padding: 8px 0;
}

.resource-visit-list strong {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.path-overview {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 20px;
  margin-top: 14px;
}

.path-counts {
  display: flex;
  gap: 22px;
}

.path-counts span,
.path-progress-result span {
  display: grid;
  gap: 2px;
}

.path-counts strong,
.path-progress-result strong {
  color: #21483d;
  font-size: 21px;
  line-height: 1.1;
}

.path-counts small,
.path-progress-result small {
  color: #7d9089;
  font-size: 11px;
}

.path-progress-result {
  text-align: right;
}

.path-progress-track {
  margin-top: 10px;
}

.path-progress-track > i {
  display: block;
  height: 7px;
  overflow: hidden;
  border-radius: 4px;
  background: #e9f0ed;
}

.path-progress-track b {
  display: block;
  height: 100%;
  border-radius: 4px;
  background: #249264;
}

.current-path-week {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr) auto;
  align-items: center;
  gap: 12px;
  margin-top: 14px;
  padding: 10px 12px;
  border-left: 3px solid #249264;
  border-radius: 6px;
  background: #f2f8f5;
}

.current-path-week > span {
  color: #23875d;
  font-size: 11px;
  font-weight: 700;
}

.current-path-week > div {
  display: grid;
  min-width: 0;
  gap: 2px;
}

.current-path-week strong {
  overflow: hidden;
  font-size: 13px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.current-path-week small,
.path-week-list small {
  color: #7a8e87;
  font-size: 11px;
}

.path-week-list {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0 18px;
  margin-top: 8px;
}

.path-week-list > div {
  display: flex;
  align-items: center;
  justify-content: space-between;
  min-width: 0;
  gap: 10px;
  padding: 8px 0;
  border-bottom: 1px solid #e7efeb;
}

.path-week-list > div > div {
  display: grid;
  min-width: 0;
  gap: 2px;
}

.path-week-list strong {
  overflow: hidden;
  color: #31564c;
  font-size: 12px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.week-status {
  flex: 0 0 auto;
  padding: 4px 6px;
  border-radius: 4px;
  background: #eef3f1;
  color: #657a73;
  font-size: 10px;
  font-style: normal;
  font-weight: 700;
}

.week-status.is-complete,
.week-status.is-current {
  background: #dff3e8;
  color: #176e4d;
}

.week-status.is-pending {
  background: #f1f3f2;
  color: #7b8b85;
}

.week-status.is-blocked {
  background: #fff0ec;
  color: #a64b36;
}

.heatmap-list,
.feedback-list {
  margin-top: 12px;
}

.heatmap-row {
  padding: 9px 0;
}

.adjustment-reason {
  margin: 13px 0;
}

.adjustment-list > div {
  padding: 10px 0;
}

.adjustment-actions {
  margin-top: 14px;
}

.feedback-list > div {
  padding: 9px 0;
}

.empty-copy {
  margin: 12px 0 0;
}

@media (min-width: 1180px) {
  .heatmap-list {
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 0 20px;
  }

  .heatmap-row {
    grid-template-columns: minmax(0, 1fr);
    gap: 7px;
  }
}

@media (max-width: 950px) {
  .evidence-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 720px) {
  .panel {
    padding: 18px;
  }

  .resource-visit-list,
  .path-week-list {
    grid-template-columns: 1fr;
  }

  .path-overview {
    align-items: flex-start;
  }
}

@media (max-width: 480px) {
  .current-path-week {
    grid-template-columns: minmax(0, 1fr) auto;
  }

  .current-path-week > span {
    grid-column: 1 / -1;
  }
}

@media (max-width: 768px) and (orientation: portrait) {
  .assessment-page {
    height: 100vh;
    height: 100dvh;
    max-height: 100vh;
    max-height: 100dvh;
    padding: 24px 16px calc(112px + env(safe-area-inset-bottom));
  }
}

/* Effect assessment workspace refresh. */
.assessment-page {
  --assessment-ink: #172522;
  --assessment-muted: #6d7d78;
  --assessment-line: #dfe6e3;
  --assessment-surface: #ffffff;
  box-sizing: border-box;
  padding: 30px clamp(24px, 4vw, 64px) 76px;
  background: #f5f7f6;
  color: var(--assessment-ink);
}

.assessment-page > .assessment-head,
.assessment-page > .loading-state,
.assessment-page > .metric-grid,
.assessment-page > .assessment-grid,
.assessment-page > .diagnosis-grid,
.assessment-page > .evidence-grid {
  width: min(100%, 1440px);
  margin-right: auto;
  margin-left: auto;
}

.assessment-head {
  align-items: center;
  margin-bottom: 0;
  padding: 4px 0 24px;
  border-bottom: 1px solid #d9e1de;
}

.assessment-head p {
  color: #28785d;
  font-size: 12px;
  font-weight: 800;
  line-height: 1;
}

.assessment-head h1 {
  margin: 8px 0 7px;
  color: #14211e;
  font-size: 30px;
  font-weight: 760;
  line-height: 1.15;
  letter-spacing: 0;
}

.assessment-head > div > span {
  display: block;
  max-width: 760px;
  color: #667670;
  font-size: 14px;
  line-height: 1.65;
}

.assessment-head button {
  min-height: 42px;
  padding: 0 15px;
  border: 1px solid #cfdad6;
  border-radius: 6px;
  background: #fff;
  color: #315e51;
  font-size: 13px;
  font-weight: 700;
  box-shadow: 0 1px 2px rgba(18, 41, 34, .04);
}

.assessment-head button:hover:not(:disabled) {
  border-color: #89af9f;
  background: #f4faf7;
  color: #176e4d;
}

.metric-grid {
  grid-template-columns: repeat(6, minmax(0, 1fr));
  gap: 10px;
  margin-top: 18px;
}

.metric-grid article {
  --metric-accent: #16845b;
  --metric-soft: #e4f3ec;
  position: relative;
  min-height: 128px;
  padding: 17px 16px 15px;
  overflow: hidden;
  border-color: var(--assessment-line);
  border-radius: 6px;
  box-shadow: 0 2px 8px rgba(28, 49, 42, .035);
}

.metric-grid article::before {
  position: absolute;
  inset: 0 0 auto;
  height: 3px;
  background: var(--metric-accent);
  content: '';
}

.metric-grid article:nth-child(2) { --metric-accent: #3578c8; --metric-soft: #e8f0fb; }
.metric-grid article:nth-child(3) { --metric-accent: #c78124; --metric-soft: #fbf0df; }
.metric-grid article:nth-child(4) { --metric-accent: #258b92; --metric-soft: #e3f3f3; }
.metric-grid article:nth-child(5) { --metric-accent: #b9584f; --metric-soft: #f9e9e7; }
.metric-grid article:nth-child(6) { --metric-accent: #6c6ab0; --metric-soft: #eeeeF8; }

.metric-grid svg {
  box-sizing: border-box;
  width: 30px;
  height: 30px;
  padding: 6px;
  border-radius: 6px;
  background: var(--metric-soft);
  color: var(--metric-accent);
}

.metric-grid span {
  align-self: center;
  color: #677872;
  font-size: 12px;
  font-weight: 650;
}

.metric-grid strong {
  margin-top: 12px;
  color: #18231f;
  font-size: 25px;
  font-weight: 780;
  line-height: 1;
  letter-spacing: 0;
}

.metric-grid small {
  margin-top: 8px;
  color: #83908c;
  font-size: 11px;
  line-height: 1.45;
}

.assessment-grid,
.diagnosis-grid,
.evidence-grid {
  gap: 16px;
  margin-top: 16px;
}

.assessment-grid {
  grid-template-columns: minmax(0, 1.55fr) minmax(320px, .75fr);
}

.diagnosis-grid {
  grid-template-columns: minmax(0, 1.2fr) minmax(380px, .8fr);
}

.evidence-grid {
  grid-template-columns: minmax(340px, .8fr) minmax(0, 1.2fr);
}

.panel {
  padding: 22px 24px;
  border-color: var(--assessment-line);
  border-radius: 6px;
  background: var(--assessment-surface);
  box-shadow: 0 3px 12px rgba(29, 49, 42, .035);
}

.card-title {
  align-items: center;
}

.card-title span {
  color: #27805e;
  font-size: 11px;
  font-weight: 800;
}

.card-title h2,
.evidence-grid h2 {
  margin-top: 6px;
  color: #192622;
  font-size: 18px;
  font-weight: 740;
  line-height: 1.25;
  letter-spacing: 0;
}

.card-title em {
  padding: 4px 7px;
  border-radius: 4px;
  background: #f0f4f2;
  color: #71827c;
  font-size: 10px;
  font-weight: 650;
}

.radar-card {
  min-height: 430px;
}

.radar-wrap {
  grid-template-columns: minmax(0, 1fr) 112px;
  min-height: 350px;
}

.radar-wrap svg {
  width: min(100%, 470px);
  max-height: 355px;
  margin: 0 auto;
}

.radar-wrap line,
.grid {
  stroke: #d7e0dd;
}

.radar-before {
  fill: rgba(56, 113, 193, .12);
  stroke: #3976c4;
}

.radar-after {
  fill: rgba(24, 145, 94, .20);
  stroke: #16875a;
}

.radar-legend {
  gap: 12px;
  padding-left: 14px;
  border-left: 1px solid #e5ebe8;
  color: #61736d;
  font-size: 12px;
}

.insight-card {
  border-top: 3px solid #3976c4;
}

.improvement-list {
  gap: 0;
  margin-top: 16px;
}

.improvement-list div {
  padding: 12px 0;
  border-bottom-color: #e9eeec;
}

.improvement-list span {
  color: #4f625c;
  font-size: 13px;
}

.improvement-list strong {
  color: #1e7354;
  font-size: 15px;
}

.weak-panel {
  margin-top: 20px;
  padding-top: 18px;
}

.weak-panel > span {
  color: #3f544d;
  font-size: 12px;
}

.weak-panel b {
  border: 1px solid #f0d6d1;
  background: #fff7f5;
  color: #a64d3d;
  font-size: 11px;
}

.heatmap-panel {
  border-top: 3px solid #258b92;
}

.heatmap-list {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0 24px;
  margin-top: 14px;
}

.heatmap-row {
  position: relative;
  grid-template-columns: minmax(0, 1fr) 118px;
  gap: 12px;
  min-height: 64px;
  padding: 11px 0 11px 12px;
  border-bottom: 1px solid #e7edeb;
}

.heatmap-row::before {
  position: absolute;
  inset: 14px auto 14px 0;
  width: 3px;
  border-radius: 2px;
  background: #a9b7b1;
  content: '';
}

.heatmap-row.mastered::before { background: #1c9a64; }
.heatmap-row.developing::before { background: #c58a2e; }
.heatmap-row.weak::before { background: #d0644a; }

.heatmap-row strong {
  overflow: hidden;
  color: #263b35;
  font-size: 13px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.heatmap-row small {
  color: #82908c;
  font-size: 10px;
}

.heatmap-rate {
  grid-template-columns: 42px minmax(0, 1fr);
}

.adjustment-panel {
  border-top: 3px solid #c78124;
  background: #fffefd;
}

.adjustment-reason {
  margin: 15px 0;
  padding: 12px 14px;
  border-left: 3px solid #d4a35f;
  background: #fbf7ef;
  color: #5d655f;
  font-size: 13px;
}

.adjustment-list > div {
  padding: 12px 0;
}

.adjustment-list > div > span {
  color: #b2701d;
}

.adjustment-actions button {
  min-height: 38px;
  padding: 0 13px;
  border-radius: 5px;
  background: #245f4d;
  font-size: 12px;
}

.resource-evidence {
  border-top: 3px solid #16875a;
}

.path-evidence {
  border-top: 3px solid #3976c4;
}

.feedback-evidence {
  border-top: 3px solid #6c6ab0;
}

.chip-row {
  gap: 6px;
  margin-top: 13px;
}

.chip-row span {
  padding: 5px 8px;
  border: 1px solid #d5e9df;
  background: #f0f8f4;
  color: #277456;
  font-size: 11px;
}

.resource-visit-list {
  gap: 0 16px;
  margin-top: 12px;
}

.resource-visit-list div {
  padding: 9px 0;
  font-size: 12px;
}

.current-path-week {
  background: #f1f7f4;
}

.path-progress-track > i {
  height: 8px;
  background: #e8eeeb;
}

.feedback-list {
  gap: 0 28px;
}

.feedback-list > div {
  min-height: 58px;
  padding: 10px 0;
}

.loading-state {
  margin-top: 18px;
  border: 1px solid var(--assessment-line);
  border-radius: 6px;
  background: #fff;
}

@media (max-width: 1280px) {
  .metric-grid {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }
}

@media (max-width: 1020px) {
  .assessment-grid,
  .diagnosis-grid,
  .evidence-grid {
    grid-template-columns: 1fr;
  }

  .radar-wrap {
    grid-template-columns: minmax(0, 1fr) 110px;
  }

  .feedback-evidence {
    grid-column: auto;
  }
}

@media (max-width: 760px) {
  .assessment-page,
  .assessment-page:is(.assessment-page) {
    height: 100dvh;
    max-height: 100dvh;
    padding: 74px 16px calc(96px + env(safe-area-inset-bottom));
  }

  .assessment-head {
    align-items: flex-start;
    gap: 16px;
    padding-bottom: 20px;
  }

  .assessment-head h1 {
    font-size: 26px;
  }

  .metric-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .panel {
    padding: 19px 18px;
  }

  .radar-card {
    min-height: 0;
  }

  .radar-wrap {
    grid-template-columns: 1fr;
    min-height: 0;
  }

  .radar-legend {
    display: flex;
    justify-content: center;
    padding: 12px 0 0;
    border-top: 1px solid #e5ebe8;
    border-left: 0;
  }

  .heatmap-list,
  .resource-visit-list,
  .path-week-list,
  .feedback-list {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 460px) {
  .metric-grid {
    grid-template-columns: 1fr;
  }

  .metric-grid article {
    min-height: 116px;
  }

  .heatmap-row {
    grid-template-columns: 1fr;
  }
}
</style>
