import { learningResourceCompleted } from '../../local-exam-evidence.mjs'
const DOMAIN_DEFINITIONS = [
  { id: 'foundation', label: '基础知识', description: '中医基础理论、阴阳五行、藏象与气血津液' },
  { id: 'diagnosis', label: '辨证思维', description: '四诊合参、八纲辨证与证候鉴别' },
  { id: 'medicine', label: '方药应用', description: '中药药性、方剂配伍与加减化裁' },
  { id: 'cases', label: '医案实践', description: '医案证据链、临床推演与复盘验证' },
  { id: 'engagement', label: '学习投入', description: '学习活跃度、有效时长与反馈完成情况' },
  { id: 'literacy', label: '综合素养', description: '知识迁移、综合应用与中医人文素养' },
]

const STATUS_LABELS = {
  mastered: '已经成熟',
  developing: '正在生长',
  weak: '需要巩固',
  recommended: '当前学习周',
  unverified: '等待生长',
}

const COMPLETE_STATUSES = new Set(['complete', 'completed', 'done', 'success', 'mastered', 'passed'])
const ACTIVE_STATUSES = new Set(['current', 'active', 'in-progress', 'running', 'developing'])
const BLOCKED_STATUSES = new Set(['blocked', 'failed', 'error'])
const WEEK_LABELS = ['第一周', '第二周', '第三周', '第四周', '第五周', '第六周']
const LEGACY_RADAR_LABELS = new Set(['编程调试', '实验实践', '项目能力', '工程意识'])

function text(value) {
  return String(value ?? '').trim()
}

function numberOrNull(value) {
  if (value === '' || value === null || value === undefined) return null
  const parsed = Number(value)
  return Number.isFinite(parsed) ? parsed : null
}

function clampPercentage(value) {
  const parsed = numberOrNull(value)
  return parsed === null ? null : Math.max(0, Math.min(100, parsed))
}

function normalizedStatus(value) {
  return text(value).toLowerCase().replaceAll('_', '-').replaceAll(' ', '-')
}

function visibleStageNodes(stage) {
  const nodes = Array.isArray(stage?.nodes) ? stage.nodes : []
  return nodes.filter((node) => node && node.enabled !== false && node.placeholder !== true)
}

function nodeCacheEntries(pathNodeCaches) {
  if (!pathNodeCaches || typeof pathNodeCaches !== 'object' || Array.isArray(pathNodeCaches)) return []
  return Object.entries(pathNodeCaches)
    .filter(([, entry]) => entry && typeof entry === 'object' && !Array.isArray(entry))
    .map(([cacheKey, entry]) => ({ ...entry, cacheKey: text(entry.cacheKey) || cacheKey }))
}

function nodeCacheFor(week, node, caches) {
  const cacheKey = text(node?.cacheKey)
  if (cacheKey) {
    const exact = caches.find((entry) => text(entry.cacheKey) === cacheKey)
    if (exact) return exact
  }
  const weekId = text(week?.id)
  const nodeId = text(node?.id)
  if (!weekId || !nodeId) return null
  return caches.find((entry) => (
    text(entry.stageId || entry.resourceParams?.stageId) === weekId
    && text(entry.nodeId || entry.resourceParams?.nodeId) === nodeId
  )) || null
}

function nodeIsComplete(node) {
  return COMPLETE_STATUSES.has(normalizedStatus(node?.status || node?.state))
}

function cacheIsComplete(cache) {
  return COMPLETE_STATUSES.has(normalizedStatus(cache?.status))
}

function cacheHasLearnerCompletion(cache) { return learningResourceCompleted(cache?.resourceType, cache || {}) }

function weekProgress(week, stage, pathNodeCaches) {
  const weekStatus = normalizedStatus(week?.status)
  const nodes = visibleStageNodes(stage)
  const caches = nodeCacheEntries(pathNodeCaches)
  let pathCompletedNodes = 0
  let cacheCompletedNodes = 0
  let feedbackCompletedNodes = 0
  let preparedNodes = 0
  let preparedOnlyNodes = 0
  const matchedCaches = []
  const completedNodes = nodes.filter((node) => {
    const pathComplete = learningResourceCompleted(node.resourceType, node)
    const cache = nodeCacheFor(week, node, caches)
    const cachePrepared = cacheIsComplete(cache)
    const cacheComplete = learningResourceCompleted(node.resourceType || cache?.resourceType, cache || {})
    if (pathComplete) pathCompletedNodes += 1
    if (cacheComplete && !pathComplete) cacheCompletedNodes += 1
    if (cachePrepared) preparedNodes += 1
    if (cachePrepared && !cacheComplete && !pathComplete) preparedOnlyNodes += 1
    if (cacheComplete && (
      normalizedStatus(cache?.completionSource) === 'learning-feedback'
      || normalizedStatus(cache?.learningFeedback?.outcome) === 'completed'
    )) feedbackCompletedNodes += 1
    if (cache) matchedCaches.push(cache)
    return pathComplete || cacheComplete
  }).length
  const cacheUpdatedAt = matchedCaches
    .map((cache) => cache.updatedAt || cache.completedAt || cache.createdAt)
    .filter(Boolean)
    .sort((left, right) => new Date(right).getTime() - new Date(left).getTime())[0] || ''
  if (COMPLETE_STATUSES.has(weekStatus) && completedNodes === nodes.length && nodes.length > 0) {
    return {
      progress: 100,
      completedNodes: Math.max(completedNodes, nodes.length),
      totalNodes: nodes.length,
      pathCompletedNodes,
      cacheCompletedNodes,
      feedbackCompletedNodes,
      preparedNodes,
      preparedOnlyNodes,
      cacheUpdatedAt,
    }
  }
  const progress = nodes.length ? Math.round(completedNodes / nodes.length * 100) : 0
  return {
    progress,
    completedNodes,
    totalNodes: nodes.length,
    pathCompletedNodes,
    cacheCompletedNodes,
    feedbackCompletedNodes,
    preparedNodes,
    preparedOnlyNodes,
    cacheUpdatedAt,
  }
}

function fruitStatus(week, progress) {
  const status = normalizedStatus(week?.status)
  if (progress >= 100) return 'mastered'
  if (BLOCKED_STATUSES.has(status)) return 'weak'
  if (ACTIVE_STATUSES.has(status) || progress > 0) return 'developing'
  return 'unverified'
}

function latestTimestamp(evidence = {}, pathConfig = {}, pathNodeCaches = {}) {
  const candidates = [
    pathConfig.meta?.savedAt,
    evidence.pathProgress?.updatedAt,
    ...(evidence.learningFeedbacks || []).map((item) => item.updatedAt || item.createdAt),
    ...(evidence.resourceVisits || []).map((item) => item.updatedAt || item.createdAt),
    ...nodeCacheEntries(pathNodeCaches).map((item) => item.updatedAt || item.completedAt || item.createdAt),
  ].filter(Boolean)
  if (!candidates.length) return ''
  return candidates.sort((left, right) => new Date(right).getTime() - new Date(left).getTime())[0]
}

function buildWeekFruit(week, stage, index, pathConfig, pathNodeCaches, updatedAt) {
  const exists = Boolean(week)
  const weekId = text(week?.id)
  const progressEvidence = weekProgress(week, stage, pathNodeCaches)
  const status = exists ? fruitStatus(week, progressEvidence.progress) : 'unverified'
  const recommended = exists && ACTIVE_STATUSES.has(normalizedStatus(week.status))
  const title = text(week?.title)
  const weekLabel = text(week?.weekLabel) || WEEK_LABELS[index]
  const profileReportId = Number(pathConfig.meta?.profileReportId || 0)
  const feedbackBreakdown = progressEvidence.feedbackCompletedNodes
    ? `，其中 ${progressEvidence.feedbackCompletedNodes} 个已提交完成学习反馈`
    : progressEvidence.cacheCompletedNodes
      ? `，其中 ${progressEvidence.cacheCompletedNodes} 个已有学习者实际操作记录`
      : ''
  const preparationBreakdown = progressEvidence.preparedOnlyNodes
    ? `另有 ${progressEvidence.preparedOnlyNodes} 个节点仅完成后台资源准备，不计入成熟度。`
    : ''
  const nodeEvidence = progressEvidence.totalNodes
    ? `本周共 ${progressEvidence.totalNodes} 个可学习任务，已有 ${progressEvidence.completedNodes} 个学习完成记录${feedbackBreakdown}。每个路径节点只计一次。${preparationBreakdown}`
    : exists && progressEvidence.progress >= 100
      ? '学习路径已把本周记录为完成，因此果实成熟度为 100%。'
      : exists
        ? '本周路径已生成，但尚无任务完成记录，果实保持初始青果状态。'
        : '当前画像尚未生成这一周的路径内容，果实仅表示预留周次，不计入完成度。'

  return {
    id: exists ? `fruit-${weekId || index + 1}` : `fruit-pending-${index + 1}`,
    kind: 'fruit',
    weekId,
    order: index + 1,
    weekLabel,
    label: title || `${weekLabel}学习内容${exists ? '' : '待生成'}`,
    eyebrow: `${weekLabel}果实`,
    description: text(week?.description) || (exists ? '本周学习目标由当前画像生成。' : '完成画像与前序路径后生成本周内容。'),
    progress: progressEvidence.progress,
    growthScale: Number((0.46 + progressEvidence.progress / 100 * 0.64).toFixed(3)),
    status,
    statusLabel: STATUS_LABELS[recommended ? 'recommended' : status],
    evidenceCount: progressEvidence.completedNodes,
    completedNodes: progressEvidence.completedNodes,
    totalNodes: progressEvidence.totalNodes,
    pathCompletedNodes: progressEvidence.pathCompletedNodes,
    cacheCompletedNodes: progressEvidence.cacheCompletedNodes,
    feedbackCompletedNodes: progressEvidence.feedbackCompletedNodes,
    preparedNodes: progressEvidence.preparedNodes,
    preparedOnlyNodes: progressEvidence.preparedOnlyNodes,
    evidence: nodeEvidence,
    reason: exists
      ? `该周内容来自画像 #${profileReportId || '未标记'} 对应的已保存个性化路径。`
      : '尚无对应路径数据，不展示虚构课程内容或完成证据。',
    recommended,
    available: exists,
    action: {
      label: exists ? (recommended ? '继续本周学习' : '查看本周路径') : '查看路径生成状态',
      to: weekId ? `/learning-path/week/${encodeURIComponent(weekId)}` : '/learning-path/stage/overview',
    },
    updatedAt: text(progressEvidence.cacheUpdatedAt || stage?.updatedAt || pathConfig.meta?.savedAt || updatedAt),
  }
}

export function buildLifeTreeModel(payload = {}) {
  const profile = payload.profile && typeof payload.profile === 'object' ? payload.profile : {}
  const evidence = payload.evidence && typeof payload.evidence === 'object' ? payload.evidence : {}
  const assessment = payload.assessment && typeof payload.assessment === 'object' ? payload.assessment : {}
  const pathConfig = payload.pathConfig && typeof payload.pathConfig === 'object' ? payload.pathConfig : {}
  const pathNodeCaches = payload.pathNodeCaches && typeof payload.pathNodeCaches === 'object' ? payload.pathNodeCaches : {}
  const stages = pathConfig.stages && typeof pathConfig.stages === 'object' ? pathConfig.stages : {}
  const weeks = Array.isArray(pathConfig.weeks)
    ? pathConfig.weeks.filter((week) => week && week.enabled !== false && week.placeholder !== true).slice(0, 6)
    : []
  const updatedAt = latestTimestamp(evidence, pathConfig, pathNodeCaches)
  const fruits = WEEK_LABELS.map((_, index) => {
    const week = weeks[index] || null
    return buildWeekFruit(week, week ? stages[text(week.id)] : null, index, pathConfig, pathNodeCaches, updatedAt)
  })

  const labels = Array.isArray(assessment.labels) ? assessment.labels : []
  const radarScores = Array.isArray(assessment.radarScores) ? assessment.radarScores : []
  const usesLegacyRadarLabels = labels.some((label) => LEGACY_RADAR_LABELS.has(text(label)))
  const profileDimensions = DOMAIN_DEFINITIONS.map((domain, index) => ({
    id: `profile-dimension-${domain.id}`,
    label: usesLegacyRadarLabels ? domain.label : text(labels[index]) || domain.label,
    description: domain.description,
    score: numberOrNull(radarScores[index]),
  }))

  const profileName = text(profile.profileName || profile.name || profile.title) || '当前学习画像'
  const profileReportId = Number(profile.id || profile._profileReportId || pathConfig.meta?.profileReportId || 0)
  const root = {
    id: 'profile-root',
    kind: 'profile',
    label: profileName,
    eyebrow: '生命树根系',
    status: profileReportId ? 'developing' : 'unverified',
    statusLabel: profileReportId ? '画像已绑定' : '待建立画像',
    evidenceCount: Math.max(0, Number(assessment.evidenceCount || 0)),
    evidence: profileReportId
      ? `生命树绑定画像 #${profileReportId}${profile.isActive === false ? '，当前不是激活版本' : '，六周果实随该画像路径的学习证据生长'}。`
      : '尚未获得可用学习画像，树上仅保留六周生长位置，不显示虚构学习成果。',
    reason: text(assessment.summary) || '画像决定树的能力根系，学习路径决定六枚周次果实。',
    recommended: false,
    action: { label: profileReportId ? '查看学习画像' : '建立学习画像', to: '/learning-profile' },
    updatedAt,
  }

  const heatmap = Array.isArray(assessment.knowledgeHeatmap) ? assessment.knowledgeHeatmap : []
  const quantifiedKnowledge = heatmap.filter((item) => Number(item?.attempts || 0) > 0)
  const hasAchievementEvidence = Number(evidence.pathProgress?.trackedNodes || 0) > 0
    || (evidence.examResults || []).length > 0
    || (evidence.knowledgePointStats || []).some((item) => Number(item?.attempts || 0) > 0)
  const masteryRate = quantifiedKnowledge.length ? clampPercentage(assessment.masteryRate) : null
  const achievementRate = hasAchievementEvidence ? clampPercentage(assessment.achievementRate) : null
  const currentFruit = fruits.find((fruit) => fruit.recommended)
    || fruits.find((fruit) => fruit.available && fruit.progress < 100)
    || fruits.find((fruit) => fruit.available)
    || fruits[0]

  return {
    profile: root,
    profileDimensions,
    fruits,
    nodes: fruits,
    branches: [],
    currentFruitId: currentFruit?.id || '',
    updatedAt,
    empty: weeks.length === 0,
    stats: {
      masteryRate,
      achievementRate,
      overallGrowth: Number((fruits.reduce((total, fruit) => total + fruit.progress, 0) / fruits.length).toFixed(1)),
      completedWeeks: fruits.filter((fruit) => fruit.progress >= 100).length,
      generatedWeeks: fruits.filter((fruit) => fruit.available).length,
      currentWeekProgress: currentFruit?.progress || 0,
      evidenceCount: Math.max(0, Number(assessment.evidenceCount || 0)),
      confidenceLevel: text(assessment.confidenceLevel) || 'low',
    },
  }
}

export { DOMAIN_DEFINITIONS, STATUS_LABELS }
