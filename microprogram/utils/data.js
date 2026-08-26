function body(payload) {
  return payload && payload.data !== undefined ? payload.data : (payload || {})
}

function profileList(payload) {
  const value = body(payload)
  return Array.isArray(value.profiles) ? value.profiles : (Array.isArray(value.reports) ? value.reports : [])
}

function activeProfile(payload) {
  const value = body(payload)
  const list = profileList(payload)
  const activeId = Number(value.activeReportId || value.state?.activeReportId || 0)
  return list.find(item => item.isActive || Number(item.id) === activeId) || null
}

function normalizeState(value) {
  const state = String(value || '').toLowerCase()
  if (['done', 'complete', 'completed', 'success'].includes(state)) return 'done'
  if (['current', 'active', 'progress', 'running', 'in_progress'].includes(state)) return 'current'
  if (['locked', 'disabled'].includes(state)) return 'locked'
  return 'available'
}

function weeks(payload) {
  const value = body(payload)
  const config = value.config || value
  const list = Array.isArray(config.weeks) ? config.weeks : []
  return list.filter(item => item && item.enabled !== false && !item.placeholder).map((item, index) => ({
    ...item,
    id: String(item.id || `week-${index + 1}`),
    order: Number(item.order ?? item.week ?? index + 1),
    title: item.title || `第 ${index + 1} 周学习任务`,
    description: item.description || item.summary || '',
    state: normalizeState(item.status || item.state),
    tasks: (Array.isArray(item.tasks) ? item.tasks : (Array.isArray(item.nodes) ? item.nodes : [])).filter(task => {
      const type = String(task && (task.resourceType || task.type) || '').toLowerCase()
      return type !== 'mcu' && type !== 'simulator'
    }),
  })).sort((a, b) => a.order - b.order)
}

function normalizeTaskState(value) {
  const state = String(value || '').toLowerCase()
  if (['done', 'completed', 'complete', 'success', 'succeeded'].includes(state)) return 'complete'
  if (['error', 'failed', 'rejected'].includes(state)) return 'failed'
  if (['pending', 'created'].includes(state)) return 'queued'
  if (state === 'waiting_for_user') return 'waiting'
  return state || 'queued'
}

function tasks(payload) {
  const value = body(payload)
  const list = value.tasks || value.history || []
  return (Array.isArray(list) ? list : []).map(item => ({
    ...item,
    taskId: String(item.taskId || item.id || ''),
    status: normalizeTaskState(item.status),
  }))
}

function progress(task) {
  const value = Number(task.progress ?? task.result?.progress ?? task.result?.workflow?.progress)
  if (Number.isFinite(value)) return Math.max(0, Math.min(100, value))
  if (task.status === 'complete') return 100
  return 0
}

module.exports = { body, activeProfile, profileList, weeks, tasks, progress, normalizeTaskState }
