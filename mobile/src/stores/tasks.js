import { computed, reactive } from 'vue'
import { getTask } from '../services/api.js'
import { normalizeTaskState, taskFromPayload, taskProgress, TERMINAL_TASK_STATES } from '../utils/data.js'

export const taskStore = reactive({ items: {}, expanded: false })
export const activeTasks = computed(() => Object.values(taskStore.items).filter(task => !TERMINAL_TASK_STATES.has(task.status)))

export function trackTask(task = {}) {
  const taskId = String(task.taskId || task.id || '')
  if (!taskId) return
  taskStore.items[taskId] = { ...taskStore.items[taskId], ...task, taskId, status: normalizeTaskState(task.status) }
  scheduleTask(taskId)
}

const timers = new Map()
function scheduleTask(taskId) {
  if (timers.has(taskId)) return
  const poll = async () => {
    try {
      const task = taskFromPayload(await getTask(taskId))
      taskStore.items[taskId] = { ...taskStore.items[taskId], ...task, taskId }
      if (TERMINAL_TASK_STATES.has(task.status)) { timers.delete(taskId); return }
    } catch (error) { taskStore.items[taskId].pollError = error.message }
    const delay = document.hidden ? 8000 : 1500
    timers.set(taskId, window.setTimeout(poll, delay))
  }
  timers.set(taskId, window.setTimeout(poll, 500))
}

export function displayTaskProgress(task) { return taskProgress(task) }
