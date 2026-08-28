export const XIAOZHI_WORKFLOW_EVENT = 'xiaozhi-workflow-progress'
export const XIAOZHI_ACTIVE_TASK_KEY = 'qihuang:xiaozhi-active-task:v1'
export const XIAOZHI_WORKFLOW_STATE_KEY = 'qihuang:xiaozhi-workflow-state:v1'

export const PROFILE_WORKFLOW_STAGES = [
  { id: 'profile', label: '画像诊断' },
  { id: 'knowledge', label: '知识检索' },
  { id: 'review', label: '交叉审核' },
  { id: 'path', label: '路径规划' },
]

const KNOWLEDGE_STAGES = new Set([
  'knowledge_skipped',
  'retrieve_knowledge',
  'course_knowledge_retrieval',
])

const REVIEW_STAGES = new Set([
  'specialist_start',
  'skill_resolved',
  'skill_input_validated',
  'mcp_tool_start',
  'mcp_tool_complete',
  'skill_output_validated',
  'specialist_complete',
  'quality_review',
  'content_safety',
  'learning_feedback',
  'supervisor_finalize',
  'agent_returned',
  'save_report',
  'complete',
  'done',
  'result',
])

export function clampWorkflowProgress(value, fallback = 0) {
  const number = Number(value)
  if (!Number.isFinite(number)) return Math.max(0, Math.min(100, Number(fallback) || 0))
  return Math.max(0, Math.min(100, Math.round(number)))
}

export function profileStageIndex(stage, hasPathTask = false) {
  if (hasPathTask) return 3
  const normalized = String(stage || '').trim()
  if (KNOWLEDGE_STAGES.has(normalized)) return 1
  if (REVIEW_STAGES.has(normalized)) return 2
  return 0
}

export function profileProgress(event = {}) {
  if (Number.isFinite(Number(event.progress))) {
    return clampWorkflowProgress(event.progress)
  }
  const status = String(event.status || '')
  if (['failed', 'error'].includes(status)) return 100
  if (['complete', 'done'].includes(status)) return 86
  return [8, 32, 62, 88][profileStageIndex(event.stage, Boolean(event.task))]
}

export function learningPathProgress(task = {}) {
  const result = task.result && typeof task.result === 'object' ? task.result : {}
  if (Number.isFinite(Number(result.progress))) return clampWorkflowProgress(result.progress)
  if (workflowStatus(task.status) === 'complete') return 100
  const completed = Math.max(0, Number(result.completedWeeks) || 0)
  const total = Math.max(1, Number(result.totalWeeks) || 6)
  return clampWorkflowProgress((completed / total) * 100)
}

export function workflowStatus(value) {
  const normalized = String(value || '').toLowerCase()
  if (normalized === 'error') return 'failed'
  if (normalized === 'done') return 'complete'
  if (['queued', 'running', 'complete', 'failed'].includes(normalized)) return normalized
  return 'running'
}

export function dispatchXiaoZhiWorkflowProgress(detail) {
  if (typeof window === 'undefined') return
  try {
    const taskId = String(detail?.task?.taskId || '')
    const persisted = taskId
      ? { taskId }
      : {
          workflowId: String(detail?.workflowId || ''),
          workflow: String(detail?.workflow || ''),
          stage: String(detail?.stage || ''),
          status: workflowStatus(detail?.status),
          progress: detail?.progress,
          message: String(detail?.message || ''),
          completedWeeks: detail?.completedWeeks,
          totalWeeks: detail?.totalWeeks,
          route: String(detail?.route || ''),
        }
    if (taskId) sessionStorage.setItem(XIAOZHI_ACTIVE_TASK_KEY, taskId)
    if (taskId || persisted.workflowId) {
      sessionStorage.setItem(XIAOZHI_WORKFLOW_STATE_KEY, JSON.stringify(persisted))
    }
  } catch {
    // Storage can be unavailable in privacy-restricted webviews.
  }
  window.dispatchEvent(new CustomEvent(XIAOZHI_WORKFLOW_EVENT, { detail }))
}
