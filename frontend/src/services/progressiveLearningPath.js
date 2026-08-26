import { generateLearningPathStream, getLearningPathConfig } from './api.js'

let firstWeekPromise = null
let remainingWeeksPromise = null
const progressListeners = new Set()
const traceListeners = new Set()
let traceHistory = []
let traceSequence = 0
const recoveryPollDelays = [0, 3000, 6000, 10000]

function sleep(ms) {
  return new Promise(resolve => window.setTimeout(resolve, ms))
}

function isStreamConnectionError(error) {
  const message = String(error?.message || '').toLowerCase()
  return error?.name === 'TypeError'
    || error?.code === 'LEARNING_PATH_STREAM_INTERRUPTED'
    || ['failed to fetch', 'networkerror', 'network error', 'load failed', 'connection'].some(token => message.includes(token))
}

function streamConnectionError(error, week) {
  if (!isStreamConnectionError(error)) return error
  const nextError = new Error(
    `第 ${week} 周生成连接中断，已保存的学习路径不会丢失。点击“继续生成”将从数据库进度补全。`,
  )
  nextError.name = 'LearningPathStreamError'
  nextError.code = 'LEARNING_PATH_STREAM_INTERRUPTED'
  nextError.cause = error
  return nextError
}

function emitProgress(config) {
  for (const listener of progressListeners) {
    try {
      listener(config)
    } catch (error) {
      console.warn('Failed to apply learning-path progress update.', error)
    }
  }
}

function normalizeTraceEvent(rawEvent) {
  const event = String(rawEvent?.event || 'progress')
  const data = rawEvent?.data && typeof rawEvent.data === 'object'
    ? rawEvent.data
    : { message: String(rawEvent?.data || '') }
  traceSequence += 1
  return {
    ...data,
    id: `learning-path-trace-${traceSequence}`,
    event,
    receivedAt: new Date().toISOString(),
  }
}

function notifyTraceListeners(event) {
  for (const listener of traceListeners) {
    try {
      listener(event, traceHistory.slice())
    } catch (error) {
      console.warn('Failed to apply learning-path trace update.', error)
    }
  }
}

function emitTrace(rawEvent) {
  const normalized = normalizeTraceEvent(rawEvent)
  if (normalized.event !== 'heartbeat') {
    traceHistory = [...traceHistory, normalized].slice(-160)
  }
  notifyTraceListeners(normalized)
  return normalized
}

function beginTrace(message) {
  traceHistory = []
  notifyTraceListeners(normalizeTraceEvent({ event: 'reset', data: {} }))
  emitTrace({
    event: 'request',
    data: {
      stage: 'frontend_request',
      status: 'running',
      progress: 0,
      message,
    },
  })
}

async function runGenerationStream(payload) {
  try {
    return await generateLearningPathStream(payload, emitTrace)
  } catch (error) {
    if (!error?.learningPathEventReported && !isStreamConnectionError(error)) {
      emitTrace({
        event: 'error',
        data: {
          stage: 'request_error',
          status: 'failed',
          progress: 100,
          errorCode: error?.code || 'LEARNING_PATH_REQUEST_FAILED',
          message: error?.message || '学习路径生成请求失败',
        },
      })
    }
    throw error
  }
}

function generatedWeekOrders(config, totalWeeks) {
  const orders = new Set(
    (Array.isArray(config?.weeks) ? config.weeks : [])
      .filter((week) => week && week.enabled !== false && !week.placeholder)
      .map((week) => Number(week.order))
      .filter((order) => Number.isInteger(order) && order >= 1 && order <= totalWeeks),
  )
  return orders
}

async function recoverPersistedWeek(previousConfig, week, totalWeeks, profileReportId = 0) {
  const expectedProfileId = Number(profileReportId || previousConfig?.meta?.profileReportId || 0)
  emitTrace({
    event: 'progress',
    data: {
      stage: 'recover_saved_progress',
      status: 'running',
      progress: 99,
      weekStart: week,
      message: `连接中断，正在确认第 ${week} 周是否已保存`,
    },
  })

  for (const delay of recoveryPollDelays) {
    if (delay) await sleep(delay)
    try {
      const savedConfig = await getLearningPathConfig()
      const savedProfileId = Number(savedConfig?.meta?.profileReportId || 0)
      if (savedConfig?.meta?.profileSwitchPending === true) return null
      if (expectedProfileId > 0 && savedProfileId > 0 && savedProfileId !== expectedProfileId) {
        return null
      }
      if (generatedWeekOrders(savedConfig, totalWeeks).has(week)) {
        emitTrace({
          event: 'progress',
          data: {
            stage: 'saved_progress_recovered',
            status: 'complete',
            progress: 100,
            weekStart: week,
            message: `已从数据库恢复第 ${week} 周学习路径`,
          },
        })
        return savedConfig
      }
    } catch {
      // Keep polling while the same network interruption is settling.
    }
  }
  return null
}

export function subscribeLearningPathProgress(listener) {
  if (typeof listener !== 'function') return () => {}
  progressListeners.add(listener)
  return () => progressListeners.delete(listener)
}

export function subscribeLearningPathTrace(listener) {
  if (typeof listener !== 'function') return () => {}
  traceListeners.add(listener)
  for (const event of traceHistory) {
    listener(event, traceHistory.slice())
  }
  return () => traceListeners.delete(listener)
}

export function generateFirstLearningPath(totalWeeks, profileReportId = 0) {
  if (firstWeekPromise) return firstWeekPromise
  beginTrace('正在请求岐小智生成第一周学习路径')
  firstWeekPromise = (async () => {
    try {
      const result = await runGenerationStream({
        persist: true,
        useLatestProfile: true,
        generationPhase: 'first-week',
        weekStart: 1,
        weekCount: 1,
        totalWeeks,
        useLLM: true,
      })
      if (!result?.config) throw new Error('学习路径智能体未返回首周配置')
      emitProgress(result.config)
      return result.config
    } catch (error) {
      if (isStreamConnectionError(error)) {
        const recovered = await recoverPersistedWeek(null, 1, totalWeeks, profileReportId)
        if (recovered) {
          emitProgress(recovered)
          return recovered
        }
      }
      throw streamConnectionError(error, 1)
    }
  })().finally(() => {
    firstWeekPromise = null
  })
  return firstWeekPromise
}

export function generateRemainingLearningPath(initialConfig, totalWeeks) {
  if (remainingWeeksPromise) return remainingWeeksPromise
  if (!traceHistory.length) beginTrace('正在请求岐小智补全后续周学习路径')

  remainingWeeksPromise = (async () => {
    let currentConfig = initialConfig
    const existingOrders = generatedWeekOrders(currentConfig, totalWeeks)
    const missingOrders = Array.from({ length: totalWeeks }, (_, index) => index + 1)
      .filter((week) => week > 1 && !existingOrders.has(week))

    for (const week of missingOrders) {
      emitTrace({
        event: 'request',
        data: {
          stage: 'next_week_request',
          status: 'running',
          progress: 0,
          weekStart: week,
          message: `正在生成第 ${week} 周学习路径`,
        },
      })
      let result
      try {
        result = await runGenerationStream({
          persist: true,
          useLatestProfile: true,
          generationPhase: 'remaining-weeks',
          weekStart: week,
          weekCount: 1,
          totalWeeks,
          existingConfig: currentConfig,
          useLLM: true,
        })
      } catch (error) {
        if (isStreamConnectionError(error)) {
          const recovered = await recoverPersistedWeek(currentConfig, week, totalWeeks)
          if (recovered) {
            currentConfig = recovered
            emitProgress(currentConfig)
            continue
          }
        }
        throw streamConnectionError(error, week)
      }
      if (!result?.config) throw new Error(`学习路径智能体未返回第 ${week} 周配置`)
      currentConfig = result.config
      emitProgress(currentConfig)
    }
    emitTrace({
      event: 'complete',
      data: {
        stage: 'all_weeks_complete',
        status: 'complete',
        progress: 100,
        message: '全部周次学习路径已生成并保存',
      },
    })
    return currentConfig
  })().finally(() => {
    remainingWeeksPromise = null
  })

  return remainingWeeksPromise
}
