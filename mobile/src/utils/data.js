export const TERMINAL_TASK_STATES = new Set(['complete', 'failed', 'cancelled', 'waiting', 'waiting_for_user'])

export function normalizeTaskState(value) {
  const state = String(value || '').toLowerCase()
  if (['done', 'completed', 'success', 'succeeded'].includes(state)) return 'complete'
  if (['error', 'rejected'].includes(state)) return 'failed'
  if (['pending', 'created'].includes(state)) return 'queued'
  if (state === 'waiting_for_user') return 'waiting'
  return ['queued', 'running', 'complete', 'failed', 'cancelled', 'waiting'].includes(state) ? state : 'queued'
}

export function normalizeNodeState(value) {
  const state = String(value || '').toLowerCase()
  if (['done', 'complete', 'completed'].includes(state)) return 'done'
  if (['current', 'active', 'progress', 'running'].includes(state)) return 'current'
  if (['locked', 'disabled'].includes(state)) return 'locked'
  return 'available'
}

export function normalizePathPayload(payload = {}) {
  return payload?.data?.config || payload?.config || payload?.data || payload || {}
}

export function pathWeeks(payload = {}) {
  const config = normalizePathPayload(payload)
  return (Array.isArray(config.weeks) ? config.weeks : [])
    .filter(week => week && week.enabled !== false && !week.placeholder)
    .map((week, index) => ({
      ...week,
      tasks: (Array.isArray(week.tasks) ? week.tasks : []).filter(task => {
        const type = String(task?.resourceType || task?.type || '').toLowerCase()
        return !['mcu', 'simulator'].includes(type)
      }),
      id: String(week.id || `week-${index + 1}`),
      order: Number(week.order ?? index + 1),
      title: String(week.title || `第 ${index + 1} 周学习任务`),
      description: String(week.description || ''),
      state: normalizeNodeState(week.status || week.state),
      resourceType: 'week',
    }))
    .sort((a, b) => a.order - b.order)
}

function percentage(value) {
  const numeric = Number(value)
  return Number.isFinite(numeric) ? Math.max(0, Math.min(100, Math.round(numeric))) : null
}

export function effectAssessmentMetrics(payload = {}, weeks = [], tasks = []) {
  const assessment = payload?.data?.assessment || payload?.assessment || payload?.data || payload || {}
  const completedNodes = Number(assessment.completedNodes || 0)
  const trackedNodes = Number(assessment.trackedNodes || 0)
  const completedWeeks = weeks.filter(week => week?.state === 'done').length
  const weekProgress = weeks.length ? Math.round(completedWeeks / weeks.length * 100) : 0
  const pathProgress = trackedNodes > 0
    ? Math.round(Math.max(0, completedNodes) / trackedNodes * 100)
    : weekProgress
  const masteryEvidenceAvailable = (assessment.masteryBreakdown || []).some(item => item?.available)
    || (assessment.knowledgeHeatmap || []).some(item => Number(item?.attempts || 0) > 0)
  const persistedTaskCount = Number(assessment.generatedResourceCount)

  return {
    pathProgress: Math.max(0, Math.min(100, pathProgress)),
    achievementRate: percentage(assessment.achievementRate) ?? pathProgress,
    masteryRate: masteryEvidenceAvailable ? percentage(assessment.masteryRate) : null,
    generatedTaskCount: Number.isFinite(persistedTaskCount)
      ? Math.max(0, Math.round(persistedTaskCount))
      : tasks.length,
  }
}

export function stageNodes(payload = {}) {
  const stage = payload?.data?.stage || payload?.stage || payload?.data || payload || {}
  return (Array.isArray(stage.nodes) ? stage.nodes : [])
    .filter(node => !['mcu', 'simulator'].includes(String(node?.resourceType || '').toLowerCase()))
    .map((node, index) => ({
      ...node,
      id: String(node.id || node.cacheKey || index + 1),
      order: Number(node.order ?? index + 1),
      title: String(node.title || '学习任务'),
      description: String(node.description || node.desc || ''),
      state: normalizeNodeState(node.state || node.status),
      resourceType: String(node.resourceType || ''),
    }))
    .sort((a, b) => a.order - b.order)
}

export function activeProfile(payload = {}) {
  const body = payload?.data || payload || {}
  const profiles = Array.isArray(body.profiles) ? body.profiles : []
  const id = Number(body.activeReportId || 0)
  return profiles.find(profile => profile.isActive || Number(profile.id) === id) || null
}

export function taskList(payload = {}) {
  const tasks = payload?.data?.tasks || payload?.tasks || []
  return (Array.isArray(tasks) ? tasks : []).map(task => ({
    ...task,
    taskId: String(task.taskId || task.id || ''),
    taskType: String(task.taskType || task.type || ''),
    status: normalizeTaskState(task.status),
  }))
}

export function taskFromPayload(payload = {}) {
  const task = payload?.data?.task || payload?.task || payload?.data || payload || {}
  return { ...task, status: normalizeTaskState(task.status) }
}

export function taskResources(task = {}) {
  const result = task.result && typeof task.result === 'object' ? task.result : {}
  if (Array.isArray(result.workflow?.resources)) return result.workflow.resources
  if (result.selectedResource) return [result.selectedResource]
  if (task.taskType === 'generated_video' && result.content) return [{
    type: 'generated_video',
    title: task.title,
    description: result.message || '个性化 AI 视频',
    content: result.content,
    metadata: { taskId: task.taskId },
  }]
  const candidates = [result.questionGenerator, result.ppt, result.document, result.mindmap, result.video, result.animation]
  return candidates.filter(Boolean).flatMap(value => Array.isArray(value?.resources) ? value.resources : [value])
}

export function resourceTypeName(type) {
  return {
    question_bank: '题库', quiz: '题库', document: '学习文档', ppt: 'PPT 课件',
    mindmap: '思维导图', video: '视频检索', generated_video: 'AI 视频', animation: '教学动画',
  }[String(type || '')] || '学习资源'
}

export function taskProgress(task = {}) {
  const value = Number(task.progress ?? task.result?.progress ?? task.result?.workflow?.progress)
  if (Number.isFinite(value)) return Math.max(0, Math.min(100, value))
  if (task.status === 'complete') return 100
  if (task.status === 'running') return 58
  return task.status === 'queued' ? 12 : 0
}

export function formatDate(value) {
  if (!value) return '--'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return String(value)
  return new Intl.DateTimeFormat('zh-CN', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' }).format(date)
}
