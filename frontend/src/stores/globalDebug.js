import { computed, ref } from 'vue'

const MAX_LOGS = 300

const visible = ref(false)
const collapsed = ref(false)
const logs = ref([])
const sections = ref([])

let sequence = 0

function formatTime(date = new Date()) {
  return date.toLocaleTimeString('zh-CN', {
    hour12: false,
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  })
}

function normalizeMessage(message) {
  if (message instanceof Error) {
    return message.stack || message.message
  }

  if (typeof message === 'string') {
    return message
  }

  try {
    return JSON.stringify(message, null, 2)
  } catch {
    return String(message)
  }
}

export function useGlobalDebug() {
  const logText = computed(() =>
    logs.value
      .map((item) => `[${item.time}] ${item.scope} ${item.level.toUpperCase()} ${item.message}`)
      .join('\n\n'),
  )

  function show() {
    visible.value = true
  }

  function hide() {
    visible.value = false
  }

  function toggle() {
    visible.value = !visible.value
  }

  function toggleCollapsed() {
    collapsed.value = !collapsed.value
  }

  function addLog(message, level = 'info', scope = '全局') {
    sequence += 1
    logs.value = [
      {
        id: `${Date.now()}-${sequence}`,
        time: formatTime(),
        level,
        scope,
        message: normalizeMessage(message),
      },
      ...logs.value,
    ].slice(0, MAX_LOGS)
  }

  function clearLogs() {
    logs.value = []
  }

  function setSection(id, payload) {
    const nextSection = {
      id,
      title: payload.title || id,
      items: Array.isArray(payload.items) ? payload.items : [],
      updatedAt: formatTime(),
    }
    const index = sections.value.findIndex((section) => section.id === id)
    if (index >= 0) {
      sections.value.splice(index, 1, nextSection)
      return
    }
    sections.value.push(nextSection)
  }

  function removeSection(id) {
    sections.value = sections.value.filter((section) => section.id !== id)
  }

  return {
    visible,
    collapsed,
    logs,
    sections,
    logText,
    show,
    hide,
    toggle,
    toggleCollapsed,
    addLog,
    clearLogs,
    setSection,
    removeSection,
  }
}
