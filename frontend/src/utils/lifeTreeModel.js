const DOMAIN_DEFINITIONS = [
  {
    id: 'foundation',
    label: '中医基础',
    description: '阴阳五行、藏象与气血津液等基础理论',
    keywords: ['阴阳', '五行', '藏象', '脏腑', '气血', '津液', '经络', '基础'],
  },
  {
    id: 'diagnosis',
    label: '辨证思维',
    description: '四诊合参、八纲辨证与证候鉴别',
    keywords: ['辨证', '证候', '八纲', '四诊', '望诊', '闻诊', '问诊', '切诊', '舌', '脉'],
  },
  {
    id: 'herbs',
    label: '中药药性',
    description: '性味归经、功效主治与用药安全',
    keywords: ['中药', '药性', '性味', '归经', '功效', '药材', '炮制', '禁忌'],
  },
  {
    id: 'formulas',
    label: '方剂配伍',
    description: '君臣佐使、方义分析与加减化裁',
    keywords: ['方剂', '方药', '配伍', '君臣佐使', '治法', '处方'],
  },
  {
    id: 'cases',
    label: '医案实践',
    description: '医案证据链、临床推演与复盘验证',
    keywords: ['医案', '案例', '临床', '实践', '实训', '推演', '复盘'],
  },
  {
    id: 'humanity',
    label: '医道与安全',
    description: '中医人文、伦理规范与安全边界',
    keywords: ['医德', '人文', '伦理', '安全', '规范', '风险', '文化'],
  },
]

const STATUS_LABELS = {
  mastered: '已掌握',
  developing: '学习中',
  weak: '薄弱',
  recommended: '推荐下一步',
  unverified: '待验证',
}

const RESOURCE_ROUTES = {
  'question-bank': '/personalized-resources/question-bank',
  quiz: '/personalized-resources/question-bank',
  mindmap: '/personalized-resources/mind-map',
  ppt: '/personalized-resources/ppt',
  video: '/personalized-resources/video-search',
  document: '/personalized-resources/document',
  animation: '/personalized-resources/animation',
  mcu: '/personalized-resources/document',
  simulator: '/personalized-resources/document',
}

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

function normalizePathStatus(value) {
  const normalized = text(value).toLowerCase().replaceAll('_', '-').replaceAll(' ', '-')
  if (['complete', 'completed', 'done', 'success'].includes(normalized)) return 'mastered'
  if (['current', 'active', 'in-progress', 'running'].includes(normalized)) return 'recommended'
  if (['blocked', 'failed'].includes(normalized)) return 'weak'
  return 'unverified'
}

function domainFor(label, index = 0) {
  const normalized = text(label).toLowerCase()
  const matched = DOMAIN_DEFINITIONS.find((domain) => (
    domain.keywords.some((keyword) => normalized.includes(keyword.toLowerCase()))
  ))
  return matched || DOMAIN_DEFINITIONS[Math.abs(index) % DOMAIN_DEFINITIONS.length]
}

function latestTimestamp(evidence = {}) {
  const candidates = [
    evidence.pathProgress?.updatedAt,
    ...(evidence.learningFeedbacks || []).map((item) => item.updatedAt || item.createdAt),
    ...(evidence.resourceVisits || []).map((item) => item.updatedAt || item.createdAt),
  ].filter(Boolean)
  if (!candidates.length) return ''
  return candidates.sort((left, right) => new Date(right).getTime() - new Date(left).getTime())[0]
}

function resourceAction(task, fallbackTopic) {
  if (!task) return null
  const resourceType = text(task.resourceType)
  const path = RESOURCE_ROUTES[resourceType]
  if (!path) return null
  const rawParams = task.resourceParams && typeof task.resourceParams === 'object'
    ? task.resourceParams
    : {}
  const query = Object.fromEntries(
    Object.entries({
      ...rawParams,
      topic: rawParams.topic || fallbackTopic,
      source: 'life-tree',
    }).filter(([, value]) => value !== '' && value !== null && value !== undefined),
  )
  return {
    label: resourceType === 'question-bank' || resourceType === 'quiz' ? '开始专项测评' : '生成巩固资源',
    to: { path, query },
  }
}

function knowledgeEvidence(item) {
  const attempts = Math.max(0, Number(item.attempts || 0))
  if (attempts > 0) {
    return `来自 ${attempts} 次答题或测评，答对 ${Math.max(0, Number(item.correctCount || 0))} 次。`
  }
  const evidenceTypes = Array.isArray(item.evidenceTypes) ? item.evidenceTypes : []
  if (evidenceTypes.includes('profile-reported-weakness')) {
    return '来自学习画像中的自述薄弱点，尚未完成量化测评。'
  }
  if (evidenceTypes.includes('weak-point-record')) {
    return '来自平台学习记录中的薄弱点，尚未完成量化测评。'
  }
  return '当前没有足够的量化学习证据，需通过测评进一步验证。'
}

function branchStatus(children) {
  const quantified = children.filter((node) => node.evidenceCount > 0)
  if (!quantified.length) return 'unverified'
  if (quantified.some((node) => node.status === 'weak')) return 'weak'
  if (quantified.every((node) => node.status === 'mastered')) return 'mastered'
  return 'developing'
}

export function buildLifeTreeModel(payload = {}) {
  const profile = payload.profile && typeof payload.profile === 'object' ? payload.profile : {}
  const evidence = payload.evidence && typeof payload.evidence === 'object' ? payload.evidence : {}
  const assessment = payload.assessment && typeof payload.assessment === 'object' ? payload.assessment : {}
  const pathConfig = payload.pathConfig && typeof payload.pathConfig === 'object' ? payload.pathConfig : {}
  const heatmap = Array.isArray(assessment.knowledgeHeatmap) ? assessment.knowledgeHeatmap : []
  const recommendations = Array.isArray(assessment.pathAdjustmentPlan?.tasks)
    ? assessment.pathAdjustmentPlan.tasks
    : []
  const weeks = Array.isArray(pathConfig.weeks) ? pathConfig.weeks.filter((week) => week?.enabled !== false) : []
  const updatedAt = latestTimestamp(evidence)

  const knowledgeNodes = heatmap.slice(0, 18).map((item, index) => {
    const label = text(item.knowledgePoint) || `知识点 ${index + 1}`
    const recommendation = recommendations.find((task) => text(task.knowledgePoint) === label)
    const status = STATUS_LABELS[item.status] ? item.status : 'unverified'
    const domain = domainFor(label, index)
    const masteryRate = clampPercentage(item.masteryRate)
    return {
      id: `knowledge-${index}-${label}`,
      kind: 'knowledge',
      domainId: domain.id,
      label,
      status,
      statusLabel: STATUS_LABELS[status],
      masteryRate,
      evidenceCount: Math.max(0, Number(item.attempts || 0)),
      evidence: knowledgeEvidence(item),
      reason: recommendation?.selectionReason || '',
      recommended: Boolean(recommendation),
      action: resourceAction(recommendation, label) || {
        label: status === 'mastered' ? '查看效果评估' : '进入效果评估',
        to: { path: '/effect-assessment', query: { profileId: profile.id || undefined } },
      },
      updatedAt,
    }
  })

  const pathNodes = weeks.slice(0, 8).map((week, index) => {
    const label = text(week.title || week.weekLabel) || `学习阶段 ${index + 1}`
    const domain = domainFor(`${label} ${week.description || ''}`, index)
    const status = normalizePathStatus(week.status)
    return {
      id: `path-${text(week.id) || index}`,
      kind: 'path',
      domainId: domain.id,
      label,
      eyebrow: text(week.weekLabel) || `第 ${index + 1} 阶段`,
      status,
      statusLabel: STATUS_LABELS[status],
      masteryRate: status === 'mastered' ? 100 : null,
      evidenceCount: status === 'mastered' ? 1 : 0,
      evidence: `来自当前学习路径，阶段状态为“${text(week.status) || '未记录'}”。`,
      reason: text(week.description),
      recommended: status === 'recommended',
      action: {
        label: status === 'recommended' ? '继续当前阶段' : '查看学习路径',
        to: text(week.id) ? `/learning-path/week/${encodeURIComponent(week.id)}` : '/learning-path',
      },
      updatedAt: text(pathConfig.meta?.savedAt || evidence.pathProgress?.updatedAt),
    }
  })

  const nodes = [...knowledgeNodes, ...pathNodes]
  const labels = Array.isArray(assessment.labels) ? assessment.labels : []
  const radarScores = Array.isArray(assessment.radarScores) ? assessment.radarScores : []
  const branches = DOMAIN_DEFINITIONS.map((domain, index) => {
    const children = nodes.filter((node) => node.domainId === domain.id)
    const status = branchStatus(children)
    const score = numberOrNull(radarScores[index])
    return {
      id: `branch-${domain.id}`,
      kind: 'branch',
      domainId: domain.id,
      label: labels[index] || domain.label,
      eyebrow: '能力主枝',
      description: domain.description,
      status,
      statusLabel: STATUS_LABELS[status],
      score,
      evidenceCount: children.reduce((total, node) => total + node.evidenceCount, 0),
      evidence: children.length
        ? `关联 ${children.length} 个知识或路径节点，其中 ${children.filter((node) => node.evidenceCount > 0).length} 个已有量化证据。`
        : '该能力主枝暂未关联可核验的知识或路径节点。',
      reason: '主枝状态只根据其下已有证据的节点汇总，不使用缺失数据推断掌握度。',
      recommended: children.some((node) => node.recommended),
      action: { label: '查看能力评估', to: '/effect-assessment' },
      updatedAt,
      children,
      branchIndex: index,
    }
  })

  const profileName = text(profile.profileName || profile.name || profile.title) || '当前学习画像'
  const root = {
    id: 'profile-root',
    kind: 'profile',
    label: profileName,
    eyebrow: '生命树主干',
    status: profile.id ? 'developing' : 'unverified',
    statusLabel: profile.id ? '持续生长' : '待建立画像',
    evidenceCount: Math.max(0, Number(assessment.evidenceCount || 0)),
    evidence: profile.id
      ? `当前生命树绑定画像 #${profile.id}${profile.isActive === false ? '，该画像不是当前激活版本' : '，并使用平台学习证据持续更新'}。`
      : '尚未获得可用学习画像，生命树只能显示待验证的能力骨架。',
    reason: text(assessment.summary) || '完成学习画像后，路径、资源和测评证据会在这里汇聚。',
    recommended: false,
    action: { label: profile.id ? '查看学习画像' : '建立学习画像', to: '/learning-profile' },
    updatedAt,
  }

  const quantifiedKnowledge = knowledgeNodes.filter((node) => node.evidenceCount > 0)
  const hasAchievementEvidence = Number(evidence.pathProgress?.trackedNodes || 0) > 0
    || (evidence.examResults || []).length > 0
    || (evidence.mcuExperiments || []).length > 0
  const masteryRate = quantifiedKnowledge.length ? clampPercentage(assessment.masteryRate) : null
  const achievementRate = hasAchievementEvidence ? clampPercentage(assessment.achievementRate) : null

  return {
    profile: root,
    branches,
    nodes,
    updatedAt,
    empty: nodes.length === 0,
    stats: {
      masteryRate,
      achievementRate,
      masteredCount: nodes.filter((node) => node.status === 'mastered').length,
      weakCount: nodes.filter((node) => node.status === 'weak').length,
      recommendedCount: nodes.filter((node) => node.recommended).length,
      evidenceCount: Math.max(0, Number(assessment.evidenceCount || 0)),
      confidenceLevel: text(assessment.confidenceLevel) || 'low',
    },
  }
}

export { DOMAIN_DEFINITIONS, STATUS_LABELS }
