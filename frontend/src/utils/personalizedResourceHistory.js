const TASK_RESOURCE_TYPES = {
  question_bank: 'quiz',
  ppt: 'ppt',
  document: 'document',
  mindmap: 'mindmap',
  video: 'video',
  generated_video: 'generated_video',
  animation: 'animation',
  mcu: 'simulator',
  herb_model: 'herb_model',
}

const RESOURCE_TITLES = {
  document: '中医学习讲义',
  mindmap: '中医学习思维导图',
  ppt: '中医学习课件',
  video: '中医视频教程',
  generated_video: 'AI 学习讲解视频',
  animation: '中医动画微课',
  code: '中医辨证示例',
  quiz: '中医练习题',
  simulator: '中医医案推演',
  herb_model: '药材模型辨识',
}

const RESOURCE_TYPE_NAMES = {
  document: '课程讲义',
  mindmap: '思维导图',
  ppt: 'PPT',
  video: '视频',
  generated_video: 'AI 视频生成',
  animation: '动画微课',
  code: '代码示例',
  quiz: '练习题',
  simulator: '模拟器实验',
  herb_model: '药材模型辨识',
}

function objectValue(value) {
  return value && typeof value === 'object' && !Array.isArray(value) ? value : {}
}

function listValue(value) {
  return Array.isArray(value) ? value : []
}

function firstObject(...values) {
  return values.find(value => value && typeof value === 'object' && !Array.isArray(value)) || {}
}

function firstList(...values) {
  return values.find(Array.isArray) || []
}

function numericOrNull(value) {
  if (value === null || value === undefined || value === '') return null
  const number = Number(value)
  return Number.isFinite(number) ? number : null
}

export function resourceTypeName(type) {
  return RESOURCE_TYPE_NAMES[String(type || '')] || String(type || '学习资源')
}

export function defaultResourceTitle(type) {
  return RESOURCE_TITLES[String(type || '')] || '个性化学习资源'
}

export function taskIdFromResourceId(resourceId) {
  const match = String(resourceId || '').match(/^task:([^:]+):/)
  return match ? match[1] : ''
}

export function extractTaskResources(task) {
  if (!task || task.status !== 'complete') return []

  const result = objectValue(task.result)
  const taskType = String(task.taskType || '')
  const workflow = objectValue(result.workflow)
  const orchestration = objectValue(result.orchestration)
  const review = objectValue(orchestration.review)
  const planner = objectValue(workflow.planner)
  let items = []

  if (taskType === 'personalized_resources') {
    items = listValue(workflow.resources)
  } else if (Object.keys(objectValue(result.selectedResource)).length) {
    items = [result.selectedResource]
  } else if (taskType === 'generated_video') {
    const content = objectValue(result.content)
    items = [{
      type: 'generated_video',
      title: task.title,
      description: result.message || 'AI 讲解视频已生成并保存',
      content: {
        ...content,
        videoUrl: content.videoUrl || `/api/personalized-resources/generated-videos/${encodeURIComponent(task.taskId)}/file`,
        posterUrl: content.posterUrl || `/api/personalized-resources/generated-videos/${encodeURIComponent(task.taskId)}/poster`,
      },
      metadata: { taskId: task.taskId },
    }]
  } else {
    const payloadByType = {
      question_bank: result.questionGenerator,
      ppt: result.ppt,
      document: result.document,
      animation: result.animation,
    }
    const payload = objectValue(payloadByType[taskType])
    if (Object.keys(payload).length) {
      items = [{
        type: TASK_RESOURCE_TYPES[taskType],
        title: task.title,
        description: result.message,
        content: payload,
      }]
    }
  }

  return items.filter(item => item && typeof item === 'object').map((item, index) => {
    const itemType = String(item.type || TASK_RESOURCE_TYPES[taskType] || 'document')
    const itemMetadata = objectValue(item.metadata)
    const qualityEvaluation = firstObject(
      item.qualityEvaluation,
      itemMetadata.qualityEvaluation,
      result.qualityEvaluation,
    )
    const knowledgeSources = firstList(
      item.knowledgeSources,
      itemMetadata.knowledgeSources,
      result.knowledgeSources,
      workflow.knowledgeSources,
    )
    const route = String(
      item.route
      || item.actionRoute
      || (taskType !== 'personalized_resources' ? task.route : '')
      || '',
    )
    const runId = String(orchestration.runId || result.runId || '')
    const profileReportId = Number(
      orchestration.profileReportId
      || result.profileReportId
      || itemMetadata.profileReportId
      || 0,
    )
    const itemKey = String(item.id ?? index)

    return {
      id: `task:${task.taskId}:${itemKey}`,
      title: item.title || task.title || defaultResourceTitle(itemType),
      description: item.description || result.message || `基于当前学习画像生成的${resourceTypeName(itemType)}资源`,
      type: itemType,
      matchScore: numericOrNull(item.matchScore ?? review.score),
      content: item.content ?? item,
      route,
      agent: String(result.orchestrator || orchestration.rootAgent || ''),
      source: 'xiaozhi-task',
      qualityEvaluation,
      knowledgeSources,
      createdAt: task.createdAt || task.updatedAt || '',
      metadata: {
        ...itemMetadata,
        taskId: String(task.taskId || ''),
        taskType,
        resourceIndex: index,
        runId,
        profileReportId,
        review,
        rootAgent: String(orchestration.rootAgent || result.orchestrator || ''),
        agentRuns: listValue(orchestration.agentRuns),
        planner,
        grounded: itemMetadata.grounded ?? workflow.grounded ?? Boolean(knowledgeSources.length),
      },
    }
  })
}

export function findTaskResource(task, resourceId) {
  const resources = extractTaskResources(task)
  if (!resources.length) return null
  const requestedId = String(resourceId || '')
  return requestedId ? (resources.find(item => item.id === requestedId) || null) : resources[0]
}

function preferredResourceText(value, depth = 0) {
  if (typeof value === 'string') return value
  if (!value || typeof value !== 'object' || depth > 3) return ''

  const preferredKeys = [
    'html',
    'markdown',
    'content',
    'text',
    'body',
    'source',
    'mermaid',
    'document',
    'lesson',
    'script',
  ]
  for (const key of preferredKeys) {
    const candidate = preferredResourceText(value[key], depth + 1)
    if (candidate) return candidate
  }
  return ''
}

export function resourceContentText(resource) {
  const content = resource?.content
  const preferred = preferredResourceText(content)
  if (preferred) return preferred
  if (content === null || content === undefined) return ''
  if (typeof content !== 'object') return String(content)
  try {
    return `\`\`\`json\n${JSON.stringify(content, null, 2)}\n\`\`\``
  } catch {
    return String(content)
  }
}

export function resourceQuality(resource) {
  return firstObject(resource?.qualityEvaluation, resource?.metadata?.qualityEvaluation)
}

export function resourceKnowledgeSources(resource) {
  return firstList(resource?.knowledgeSources, resource?.metadata?.knowledgeSources)
}

export function resourceCitationCount(resource) {
  return Math.max(
    Number(resourceQuality(resource).citationCount || 0),
    resourceKnowledgeSources(resource).length,
  )
}
