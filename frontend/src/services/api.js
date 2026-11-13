import { readSavedPath, invalidatePathCache } from '../../local-path-cache.mjs'
import axios from 'axios'
import { clearAuthSession, getAuthToken } from '../stores/auth.js'
import { buildLoginRedirectPath, internalRedirectFromLocation } from '../utils/authRedirect.js'

const configuredApiBaseUrl = (import.meta.env.VITE_API_BASE_URL || '').replace(/\/$/, '')
const usesLocalBackend =
  !configuredApiBaseUrl || /^https?:\/\/(localhost|127\.0\.0\.1):3000$/i.test(configuredApiBaseUrl)
const apiBaseUrl = import.meta.env.DEV
  ? (usesLocalBackend ? '' : configuredApiBaseUrl)
  : (usesLocalBackend ? '' : configuredApiBaseUrl)
const directApiBaseUrl = configuredApiBaseUrl || (import.meta.env.DEV ? 'http://localhost:3000' : window.location.origin)

const apiClient = axios.create({
  baseURL: apiBaseUrl,
  timeout: 60000,
  withCredentials: true,
})

apiClient.interceptors.response.use(response => {
  if (!['get', 'head'].includes(String(response.config?.method || 'get').toLowerCase())) invalidatePathCache(String(response.config?.url || ''))
  return response
})

const CODEX_PREVIEW_AUTH_KEY = 'codexPreviewAuth'

const API_STATUS_MESSAGES = {
  400: '请求内容不完整或格式有误，请检查后重试',
  403: '当前账号没有执行此操作的权限',
  404: '请求的内容不存在或已被移除',
  409: '数据状态已发生变化，请刷新后重试',
  413: '上传内容过大，请缩小文件后重试',
  429: '操作过于频繁，请稍后再试',
  500: '服务处理失败，请稍后重试',
  502: '上游智能服务暂时不可用，请稍后重试',
  503: '当前任务较多，服务暂时繁忙，请稍后重试',
  504: '智能服务响应超时，请稍后重试',
}

function isTechnicalErrorMessage(value) {
  const message = String(value || '').trim()
  return !message
    || /<!doctype|<html|traceback|connectionpool|newconnectionerror|ECONN|ENOTFOUND|method not allowed|request failed with status/i.test(message)
}

export function getApiErrorMessage(error, fallback = '请求失败，请稍后重试') {
  const status = Number(error?.response?.status || error?.status || 0)
  const payload = error?.response?.data
  const serverMessage = typeof payload === 'string'
    ? payload
    : payload?.msg || payload?.message || payload?.error?.message || payload?.error
  if (!isTechnicalErrorMessage(serverMessage)) return String(serverMessage).trim()
  if (error?.code === 'ECONNABORTED' || /timeout/i.test(String(error?.message || ''))) {
    return API_STATUS_MESSAGES[504]
  }
  if (!error?.response) return '网络连接失败，请检查网络后重试'
  return API_STATUS_MESSAGES[status] || fallback
}

function makeApiUrl(path) {
  const normalizedPath = path.startsWith('/') ? path : `/${path}`
  return `${apiBaseUrl}${normalizedPath}`
}

function makeDirectApiUrl(path) {
  const normalizedPath = path.startsWith('/') ? path : `/${path}`
  return `${directApiBaseUrl}${normalizedPath}`
}

function clearAuthAndRedirect() {
  const isLocalHost = ['localhost', '127.0.0.1', '::1'].includes(window.location.hostname)
  if (isLocalHost && localStorage.getItem(CODEX_PREVIEW_AUTH_KEY) === '1') return
  const redirectTarget = internalRedirectFromLocation(window.location)
  clearAuthSession()
  if (redirectTarget) {
    window.location.href = buildLoginRedirectPath(redirectTarget)
  }
}

function isAuthEntryRequest(config = {}) {
  const url = String(config.url || '')
  return url.includes('/api/auth/login') || url.includes('/api/admin-auth/login')
}

apiClient.interceptors.request.use((config) => {
  const token = getAuthToken()
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401 && !isAuthEntryRequest(error.config)) {
      clearAuthAndRedirect()
    }
    error.userMessage = getApiErrorMessage(error)
    const responsePayload = error.response?.data
    const isPlainPayload = Object.prototype.toString.call(responsePayload) === '[object Object]'
    if (error.response && !isPlainPayload) {
      error.response.data = { msg: error.userMessage }
    } else if (isPlainPayload && isTechnicalErrorMessage(
      responsePayload.msg || responsePayload.message || responsePayload.error,
    )) {
      responsePayload.msg = error.userMessage
    }
    return Promise.reject(error)
  },
)

function parseSseChunk(chunk) {
  const lines = chunk
    .split('\n')
    .map((line) => line.trimEnd())
    .filter(Boolean)

  let event = 'message'
  const dataParts = []

  lines.forEach((line) => {
    if (line.startsWith('event:')) {
      event = line.slice(6).trim()
      return
    }

    if (line.startsWith('data:')) {
      dataParts.push(line.slice(5).trim())
    }
  })

  const rawData = dataParts.join('\n')
  if (!rawData) return null
  if (rawData === '"[DONE]"' || rawData === '[DONE]') {
    return { event, data: '[DONE]', rawData }
  }

  try {
    return { event, data: JSON.parse(rawData), rawData }
  } catch {
    return { event, data: rawData, rawData }
  }
}

export async function consumeSseResponse(response, onEvent) {
  if (!response.ok || !response.body) {
    let message = API_STATUS_MESSAGES[response.status] || `请求失败（${response.status}）`
    try {
      const payload = await response.json()
      const candidate = payload?.msg || payload?.message
      if (!isTechnicalErrorMessage(candidate)) message = candidate
    } catch {
      // Keep the status message when the response body is not JSON.
    }
    if (response.status === 401) {
      clearAuthAndRedirect()
    }
    throw new Error(message)
  }

  const reader = response.body.getReader()
  const decoder = new TextDecoder('utf-8')
  let buffer = ''

  while (true) {
    const { value, done } = await reader.read()
    if (done) break

    buffer += decoder.decode(value, { stream: true })
    const chunks = buffer.split(/\r?\n\r?\n/)
    buffer = chunks.pop() || ''

    for (const chunk of chunks) {
      const parsed = parseSseChunk(chunk)
      if (parsed && typeof onEvent === 'function') {
        await onEvent(parsed)
      }
    }
  }

  if (buffer.trim()) {
    const parsed = parseSseChunk(buffer)
    if (parsed && typeof onEvent === 'function') {
      await onEvent(parsed)
    }
  }
}

export async function loginUser(payload) {
  try {
    const { data } = await apiClient.post('/api/auth/login', payload, { timeout: 12000 })
    return data
  } catch (error) {
    if (error.code === 'ECONNABORTED') {
      error.response = { data: { msg: '服务器响应超时，请稍后重试或联系管理员查看运行监控' } }
    } else if (!error.response) {
      error.response = { data: { msg: '认证服务暂时无法连接，请检查网络后重试' } }
    }
    throw error
  }
}

export async function loginAdminUser(payload) {
  const controller = new AbortController()
  const timeoutId = setTimeout(() => controller.abort(), 12000)
  try {
    const response = await fetch(makeDirectApiUrl('/api/admin-auth/login'), {
      method: 'POST',
      credentials: 'omit',
      signal: controller.signal,
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(payload),
    })
    const data = await response.json().catch(() => ({}))
    if (String(data?.code) !== '0000' || !data?.data?.token) {
      const error = new Error(data?.msg || '管理员登录失败')
      error.response = { data }
      throw error
    }
    return data.data
  } catch (error) {
    if (error.name === 'AbortError') {
      const timeoutError = new Error('服务器响应超时，请稍后重试或检查运行监控')
      timeoutError.response = { data: { msg: timeoutError.message } }
      throw timeoutError
    }
    if (!error.response) {
      error.response = { data: { msg: '认证服务暂时无法连接，请检查网络后重试' } }
    }
    throw error
  } finally {
    clearTimeout(timeoutId)
  }
}

export async function registerUser(payload) {
  const { data } = await apiClient.post('/api/auth/register', payload)
  return data
}

export async function sendRegisterEmailCode(payload) {
  const { data } = await apiClient.post('/api/auth/email-code', payload)
  return data
}

export async function getCurrentUser() {
  const { data } = await apiClient.get('/api/auth/me')
  return data
}

export async function changePassword(payload) {
  const { data } = await apiClient.post('/api/auth/change-password', payload)
  return data
}

export async function logoutUser() {
  const { data } = await apiClient.post('/api/auth/logout')
  return data
}

export async function getLoginCaptcha() {
  const { data } = await apiClient.get('/api/auth/captcha')
  return data
}

export async function generateQuestions(formData) {
  const token = getAuthToken()
  const response = await fetch(makeApiUrl('/api/question-generator/upload-generate'), {
    method: 'POST',
    credentials: 'include',
    headers: token ? { Authorization: `Bearer ${token}` } : undefined,
    body: formData,
  })

  if (!response.ok) {
    const payload = await response.json().catch(() => ({}))
    const error = new Error(payload.error || payload.details || `请求失败 (${response.status})`)
    error.response = { status: response.status, data: payload }
    throw error
  }

  return response.json()
}

export async function generateQuestionsStream(formData, onEvent) {
  const token = getAuthToken()
  const response = await fetch(makeApiUrl('/api/question-generator/upload-generate-stream'), {
    method: 'POST',
    credentials: 'include',
    headers: token ? { Authorization: `Bearer ${token}` } : undefined,
    body: formData,
  })

  await consumeSseResponse(response, async (parsed) => {
    if (typeof onEvent === 'function') {
      await onEvent(parsed)
    }
  })
}

export async function startQuestionGeneration(formData) {
  const token = getAuthToken()
  const response = await fetch(makeApiUrl('/api/question-generator/upload-generate-background'), {
    method: 'POST',
    credentials: 'include',
    headers: token ? { Authorization: `Bearer ${token}` } : undefined,
    body: formData,
  })
  const data = await response.json().catch(() => ({}))
  if (!response.ok) {
    const error = new Error(data.error || data.msg || data.details || `请求失败 (${response.status})`)
    error.response = { status: response.status, data }
    throw error
  }
  return data
}

export async function getQuestionGeneratorHistory() {
  const { data } = await apiClient.get('/api/question-generator/history')
  return data
}

export async function getQuestionGeneratorStatus() {
  const { data } = await apiClient.get('/api/question-generator/status')
  return data
}

export async function saveQuestionGeneratorExamResult(payload) {
  const { data } = await apiClient.post('/api/question-generator/exam-results', payload)
  return data
}

export async function requestQuestionGeneratorAiScore(payload) {
  const { data } = await apiClient.post('/api/question-generator/ai-score', payload)
  return data
}

export async function getQuestionGeneratorConfig() {
  const { data } = await apiClient.get('/api/question-generator/config')
  return data
}

export async function saveQuestionGeneratorConfig(payload) {
  const { data } = await apiClient.put('/api/question-generator/config', payload)
  return data
}

export async function analyzeLearningProfile(payload) {
  const { data } = await apiClient.post('/api/learning-profile/analyze', payload, { timeout: 240000 })
  return data
}

export async function analyzeLearningProfileStream(payload, onEvent) {
  const token = getAuthToken()
  const response = await fetch(makeApiUrl('/api/learning-profile/analyze-stream'), {
    method: 'POST',
    credentials: 'include',
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: JSON.stringify(payload),
  })

  await consumeSseResponse(response, async (parsed) => {
    if (typeof onEvent === 'function') {
      await onEvent(parsed)
    }
  })
}

export async function streamLearningProfileBackgroundChat(payload, onEvent, options = {}) {
  const token = getAuthToken()
  const response = await fetch(makeApiUrl('/api/learning-profile/background-chat-stream'), {
    method: 'POST',
    credentials: 'include',
    signal: options.signal,
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: JSON.stringify(payload),
  })

  await consumeSseResponse(response, async (parsed) => {
    if (typeof onEvent === 'function') {
      await onEvent(parsed)
    }
  })
}

export async function requestLearningProfileBackgroundChat(payload, options = {}) {
  const token = getAuthToken()
  const response = await fetch(makeApiUrl('/api/learning-profile/background-chat'), {
    method: 'POST',
    credentials: 'include',
    signal: options.signal,
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: JSON.stringify(payload),
  })
  const data = await response.json().catch(() => ({}))
  if (!response.ok || data?.code !== 0 || !data?.data) {
    throw new Error(data?.msg || data?.message || `Request failed with status ${response.status}`)
  }
  return data.data
}

export async function resetLearningProfileBackgroundChat(options = {}) {
  const token = getAuthToken()
  const response = await fetch(makeApiUrl('/api/learning-profile/background-chat/reset'), {
    method: 'POST',
    credentials: 'include',
    signal: options.signal,
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
  })
  const data = await response.json().catch(() => ({}))
  if (!response.ok || data?.code !== 0) {
    throw new Error(data?.msg || data?.message || `Request failed with status ${response.status}`)
  }
  return data.data
}

export async function getLearningProfileSessions() {
  const { data } = await apiClient.get('/api/learning-profile/sessions')
  return data?.data?.sessions || []
}

export async function createLearningProfileSession(payload = {}) {
  const { data } = await apiClient.post('/api/learning-profile/sessions', payload)
  return data?.data?.session
}

export async function getLearningProfileSession(sessionId) {
  const { data } = await apiClient.get(`/api/learning-profile/sessions/${sessionId}`)
  return data?.data?.session
}

export async function sendLearningProfileSessionMessage(sessionId, content, attachments = []) {
  const { data } = await apiClient.post(`/api/learning-profile/sessions/${sessionId}/messages`, { content, attachments }, { timeout: 120000 })
  return data?.data
}

export async function streamLearningProfileSessionMessage(sessionId, content, attachments = [], onEvent, options = {}) {
  const token = getAuthToken()
  const response = await fetch(makeApiUrl(`/api/learning-profile/sessions/${sessionId}/messages-stream`), {
    method: 'POST',
    credentials: 'include',
    signal: options.signal,
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: JSON.stringify({ content, attachments }),
  })

  await consumeSseResponse(response, async (parsed) => {
    if (typeof onEvent === 'function') {
      await onEvent(parsed)
    }
  })
}

export async function uploadMultimodalInputs(files, context = 'chat', route = '') {
  const formData = new FormData()
  Array.from(files || []).forEach(file => formData.append('files', file))
  formData.append('context', context)
  if (route) formData.append('route', route)
  const { data } = await apiClient.post('/api/multimodal-inputs', formData, {
    timeout: 180000,
  })
  if (data?.code !== 0) throw new Error(data?.msg || '附件上传失败')
  return data?.data?.attachments || []
}

export async function recognizeHerb(file) {
  const formData = new FormData()
  formData.append('file', file)
  const { data } = await apiClient.post('/api/herb-recognition/recognize', formData, {
    timeout: 120000,
  })
  if (data?.code !== 0) throw new Error(data?.msg || '药材识别失败')
  return data?.data
}

export async function calibrateHerbWithAi(file) {
  const formData = new FormData()
  formData.append('file', file)
  const { data } = await apiClient.post('/api/herb-recognition/ai-calibrate', formData, {
    timeout: 120000,
  })
  if (data?.code !== 0) throw new Error(data?.msg || 'AI 校准失败')
  return data?.data
}

export async function analyzeRecognizedHerb(name) {
  const { data } = await apiClient.post('/api/herb-recognition/analyze', { name }, {
    timeout: 150000,
  })
  if (data?.code !== 0) throw new Error(data?.msg || '大模型药性分析失败')
  return data?.data
}

export async function getLearningProfileHistory() {
  const { data } = await apiClient.get('/api/learning-profile/history')
  return data
}

export async function getLearningProfiles() {
  const { data } = await apiClient.get('/api/learning-profile/profiles')
  return data.data
}

export async function getLearningProfile(reportId) {
  const { data } = await apiClient.get(`/api/learning-profile/profiles/${reportId}`)
  return data.data
}

export async function generateLearningProfilePortrait(reportId, options = {}) {
  const { data } = await apiClient.post(`/api/learning-profile/profiles/${reportId}/portrait`, {
    force: Boolean(options.force),
  }, {
    timeout: 15000,
  })
  return data.data
}

export async function getLearningProfilePortraitStatus(reportId) {
  const { data } = await apiClient.get(`/api/learning-profile/profiles/${reportId}/portrait/status`, {
    timeout: 15000,
  })
  return data.data
}

export async function getLearningProfilePortraitFile(url) {
  const { data } = await apiClient.get(url, {
    responseType: 'blob',
    timeout: 60000,
  })
  return data
}

export async function activateLearningProfile(reportId) {
  const { data } = await apiClient.post(`/api/learning-profile/profiles/${reportId}/activate`)
  return data.data
}

export async function refreshLearningProfile(reportId, payload = {}) {
  const { data } = await apiClient.post(`/api/learning-profile/profiles/${reportId}/refresh`, payload, {
    timeout: 240000,
  })
  return data.data
}

export async function getEffectAssessment(profileId = '') {
  const { data } = await apiClient.get('/api/effect-assessment', {
    params: profileId ? { profileId } : {},
  })
  return data.data
}

export async function applyEffectAssessmentAdjustment(profileId, planId) {
  const { data } = await apiClient.post('/api/effect-assessment/apply-adjustment', {
    profileId,
    planId,
  }, {
    timeout: 180000,
  })
  return data.data
}

export async function renameLearningProfile(reportId, profileName) {
  const { data } = await apiClient.patch(`/api/learning-profile/profiles/${reportId}`, { profileName })
  return data.data
}

export async function deleteLearningProfile(reportId) {
  const { data } = await apiClient.delete(`/api/learning-profile/profiles/${reportId}`)
  return data.data
}

export async function resetLearningProfile() {
  const { data } = await apiClient.post('/api/learning-profile/reset')
  return data.data
}

export async function saveLearningProfileQuestionnaire(payload) {
  const token = getAuthToken()
  const response = await fetch(makeApiUrl('/api/learning-profile/questionnaire'), {
    method: 'POST',
    credentials: 'include',
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: JSON.stringify(payload),
  })
  const data = await response.json().catch(() => ({}))
  if (!response.ok) {
    throw new Error(data.msg || data.message || `Request failed with status ${response.status}`)
  }
  return data
}

export async function generateLearningPath(payload) {
  const { data } = await apiClient.post('/api/learning-path/generate', payload, { timeout: 180000 })
  return data?.data || data
}

export async function generateNextLearningPathWeek(payload = {}) {
  const { data } = await apiClient.post('/api/learning-path/generate-next-week', payload, { timeout: 180000 })
  return data?.data || data
}

export async function generateLearningPathStream(payload, onEvent, options = {}) {
  const token = getAuthToken()
  invalidatePathCache('/api/learning-path/generate-stream')
  const response = await fetch(makeApiUrl('/api/learning-path/generate-stream'), {
    method: 'POST',
    credentials: 'include',
    signal: options.signal,
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: JSON.stringify(payload),
  })

  let result = null
  let streamError = null
  await consumeSseResponse(response, async (parsed) => {
    if (typeof onEvent === 'function') {
      await onEvent(parsed)
    }
    if (parsed.event === 'result') {
      result = parsed.data?.result || parsed.data?.data || parsed.data
    }
    if (parsed.event === 'error') {
      const message = parsed.data?.message || parsed.data?.msg || '学习路径生成失败'
      streamError = new Error(message)
      streamError.code = parsed.data?.errorCode || 'LEARNING_PATH_GENERATION_FAILED'
      streamError.details = parsed.data
      streamError.learningPathEventReported = true
    }
  })

  if (streamError) throw streamError
  if (!result) throw new Error('学习路径生成流已结束，但未返回可用结果')
  return result
}

export async function getLearningPathConfig(options = {}) {
  const load = async () => { const { data } = await apiClient.get('/api/learning-path/config', { params: { summary: options.summary === true ? 1 : 0 }, timeout: 20000 }); return data?.data || data }
  return options.summary === true ? readSavedPath('/api/learning-path/config?summary=1', load, options) : load()
}

export async function saveLearningPathConfig(config) {
  const { data } = await apiClient.put('/api/learning-path/config', { config })
  return data?.data || data
}

export async function getLearningPathStage(stageId, options = {}) {
  const url = `/api/learning-path/stages/${encodeURIComponent(stageId)}?includeConfig=${options.includeConfig === true ? 1 : 0}`
  return readSavedPath(url, async () => { const { data } = await apiClient.get(url, { timeout: 20000 }); return data?.data || data }, options)
}

export async function prepareLearningPathStageResources(stageId, payload = {}) {
  const { data } = await apiClient.post(
    `/api/learning-path/stages/${encodeURIComponent(stageId)}/prepare-resources`,
    payload,
    { timeout: 180000 },
  )
  return data?.data || data
}

export async function getLearningPathStageResourceTasks(stageId) {
  const { data } = await apiClient.get(
    `/api/learning-path/stages/${encodeURIComponent(stageId)}/resource-tasks`,
  )
  return data?.data || data
}

export async function getLearningPathNodeCaches() {
  const token = getAuthToken()
  if (!token) return {}
  const response = await fetch(makeApiUrl('/api/learning-path/node-caches'), {
    method: 'GET',
    credentials: 'include',
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  })
  if (!response.ok) return {}
  const data = await response.json().catch(() => ({}))
  return data?.data?.caches || data?.data || data || {}
}

export async function saveLearningPathNodeCache(cacheKey, entry) {
  const token = getAuthToken()
  if (!token) return null
  const response = await fetch(makeApiUrl(`/api/learning-path/node-caches/${encodeURIComponent(cacheKey)}`), {
    method: 'PUT',
    keepalive: true,
    credentials: 'include',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify({ entry }),
  })
  if (!response.ok) return null
  const data = await response.json().catch(() => ({}))
  return data?.data || data
}

export async function generateLearningPathStageDetail(payload) {
  const { data } = await apiClient.post('/api/learning-path/stage-detail', payload, { timeout: 120000 })
  return data
}

export async function generatePersonalizedResources(payload) {
  const { data } = await apiClient.post('/api/personalized-resources/generate', payload)
  return data
}

export async function startPersonalizedResourceAgentTask(payload) {
  const { data } = await apiClient.post('/api/personalized-resources/agent-task', payload)
  return data
}

export async function startGeneratedVideoTask(taskId, payload) {
  const { data } = await apiClient.post(
    `/api/personalized-resources/generated-videos/${encodeURIComponent(taskId)}/start`,
    payload,
  )
  return data
}

export async function getGeneratedVideoTaskHistory(params = {}) {
  const { data } = await apiClient.get('/api/personalized-resources/generated-videos', { params })
  return data?.data || { tasks: [], total: 0, limit: 50, offset: 0, hasMore: false }
}

export async function getMindMapTaskHistory(params = {}) {
  const { data } = await apiClient.get('/api/personalized-resources/mind-map/tasks', { params })
  return data?.data || { tasks: [], activeCount: 0, statusCounts: {} }
}

export async function getPptTaskHistory(params = {}) {
  const { data } = await apiClient.get('/api/personalized-resources/ppt/tasks', { params })
  return data?.data || { tasks: [], activeCount: 0, statusCounts: {}, engine: 'ohmyppt-fastapi' }
}

export async function getLearningDocuments(limit = 30) {
  const { data } = await apiClient.get('/api/learning-documents', { params: { limit } })
  return data?.data?.documents || []
}

export async function getLearningDocument(documentId) {
  const { data } = await apiClient.get(`/api/learning-documents/${encodeURIComponent(documentId)}`)
  return data?.data?.document
}

export async function getMcuCatalog(params = {}) {
  const { data } = await apiClient.get('/api/mcu/catalog', { params })
  return data?.data || { boards: [], components: [], experiments: [], sources: [], counts: {} }
}

export async function getHerbModelCatalog(params = {}) {
  const { data } = await apiClient.get('/api/herb-models/catalog', { params })
  return data?.data || { revision: '', count: 0, items: [], usage: '' }
}

export async function getMcuRecommendations(payload = {}) {
  const { data } = await apiClient.post('/api/mcu/recommendations', payload)
  return data?.data || { recommendations: [], profileBound: false, historyCount: 0 }
}

export async function flashMcuProgram(payload) {
  try {
    const { data } = await apiClient.post('/api/mcu/flash', payload, { timeout: 30000 })
    return data?.data || data
  } catch (error) {
    const responseData = error?.response?.data
    if (responseData?.data) return responseData.data
    throw error
  }
}

export async function saveMcuExperiment(payload) {
  const { data } = await apiClient.post('/api/mcu/save-experiment', payload)
  return data
}

export async function generatePptH5(payload) {
  const { data } = await apiClient.post('/api/ppt-h5/generate', payload, { timeout: 240000 })
  return data
}

export async function startPptH5Generation(payload) {
  const { data } = await apiClient.post('/api/ppt-h5/generate-background', payload)
  return data
}

export async function getPptH5Status() {
  const { data } = await apiClient.get('/api/ppt-h5/status')
  return data
}

// ===== 数字人面试 API =====

const INTERVIEW_REQUEST_TIMEOUT = 90000

export async function getAvatarConfig() {
  const { data } = await apiClient.get('/api/avatar/config')
  return data
}

export async function getAvatarDiagnostics(params = {}) {
  const { data } = await apiClient.get('/api/avatar/diagnostics', { params })
  return data
}

export async function startLegacyAvatar(payload = {}) {
  try {
    const { data } = await apiClient.post('/api/avatar/legacy/start', payload, { timeout: 45000 })
    return data
  } catch (error) {
    if (error?.response?.data) return error.response.data
    throw error
  }
}

export async function stopLegacyAvatar(payload = {}) {
  const { data } = await apiClient.post('/api/avatar/legacy/stop', payload)
  return data
}

export async function pingLegacyAvatar(payload = {}) {
  const { data } = await apiClient.post('/api/avatar/legacy/ping', payload)
  return data
}

export async function speakLegacyAvatar(payload = {}) {
  const { data } = await apiClient.post('/api/avatar/legacy/text', payload, { timeout: 30000 })
  return data
}

export async function startInterviewSession(payload) {
  const { data } = await apiClient.post('/api/interview/session/start', payload, { timeout: INTERVIEW_REQUEST_TIMEOUT })
  return data
}

export async function sendInterviewMessage(payload) {
  const { data } = await apiClient.post('/api/interview/session/message', payload, { timeout: INTERVIEW_REQUEST_TIMEOUT })
  return data
}

export async function endInterviewSession(payload) {
  const { data } = await apiClient.post('/api/interview/session/end', payload, { timeout: INTERVIEW_REQUEST_TIMEOUT })
  return data
}

export async function testInterviewModel(payload) {
  const { data } = await apiClient.post('/api/interview/model-test', payload, { timeout: INTERVIEW_REQUEST_TIMEOUT })
  return data
}

export async function analyzeInterviewFrame(payload) {
  const { data } = await apiClient.post('/api/interview/analyze-frame', payload, { timeout: INTERVIEW_REQUEST_TIMEOUT })
  return data
}

export async function logXiaoZhiEvent(payload) {
  const { data } = await apiClient.post('/api/xiaozhi/events', payload)
  return data
}

export async function pulseLearningActivity(payload, options = {}) {
  if (options.keepalive) {
    const headers = { 'Content-Type': 'application/json' }
    const token = getAuthToken()
    if (token) headers.Authorization = `Bearer ${token}`
    const response = await fetch(makeApiUrl('/api/learning-activity/pulse'), {
      method: 'POST',
      headers,
      body: JSON.stringify(payload),
      credentials: 'include',
      keepalive: true,
    })
    if (!response.ok) throw new Error(`学习时长记录失败 (${response.status})`)
    return response.json()
  }
  const { data } = await apiClient.post('/api/learning-activity/pulse', payload)
  return data
}

export async function chatWithXiaoZhi(payload) {
  const { data } = await apiClient.post('/api/xiaozhi/chat', payload, { timeout: 90000 })
  return data
}

export async function streamXiaoZhiChat(payload, onEvent, options = {}) {
  const token = getAuthToken()
  const response = await fetch(makeApiUrl('/api/xiaozhi/chat-stream'), {
    method: 'POST',
    credentials: 'include',
    signal: options.signal,
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: JSON.stringify(payload),
  })

  await consumeSseResponse(response, async (parsed) => {
    if (typeof onEvent === 'function') {
      await onEvent(parsed)
    }
  })
}

export async function getXiaoZhiHistory(taskLimit = 20) {
  const { data } = await apiClient.get('/api/xiaozhi/history', {
    params: { taskLimit },
  })
  return data
}

export async function getXiaoZhiTask(taskId) {
  const { data } = await apiClient.get(`/api/xiaozhi/tasks/${encodeURIComponent(taskId)}`)
  return data
}

export async function submitLearningFeedback(payload) {
  const { data } = await apiClient.post('/api/xiaozhi/feedback', payload, { timeout: 90000 })
  return data
}

export async function getLearningFeedback(params = {}) {
  const { data } = await apiClient.get('/api/learning-feedback', { params })
  return data
}

export async function getXiaoZhiStatus() {
  const { data } = await apiClient.get('/api/xiaozhi/status')
  return data
}

export async function getXiaoZhiRuntimeSettings() {
  const { data } = await apiClient.get('/api/xiaozhi/runtime-settings')
  return data
}

export async function saveXiaoZhiRuntimeSettings(payload) {
  const { data } = await apiClient.put('/api/xiaozhi/runtime-settings', payload, { timeout: 35000 })
  return data
}

export async function testXiaoZhiRuntimeSettings(payload) {
  const { data } = await apiClient.post('/api/xiaozhi/runtime-settings/test', payload, { timeout: 35000 })
  return data
}

export async function getKnowledgeCollections() {
  const { data } = await apiClient.get('/api/knowledge/collections')
  return data
}

export async function createKnowledgeCollection(payload) {
  const { data } = await apiClient.post('/api/knowledge/collections', payload)
  return data
}

export async function updateKnowledgeCollection(collectionId, payload) {
  const { data } = await apiClient.patch(`/api/knowledge/collections/${encodeURIComponent(collectionId)}`, payload)
  return data
}

export async function activateKnowledgeCollection(collectionId) {
  const { data } = await apiClient.post(`/api/knowledge/collections/${encodeURIComponent(collectionId)}/activate`)
  return data
}

export async function deleteKnowledgeCollection(collectionId) {
  const { data } = await apiClient.delete(`/api/knowledge/collections/${encodeURIComponent(collectionId)}`)
  return data
}

export async function uploadKnowledgeDocument(collectionId, file) {
  const formData = new FormData()
  formData.append('file', file)
  const { data } = await apiClient.post(
    `/api/knowledge/collections/${encodeURIComponent(collectionId)}/documents`,
    formData,
    { timeout: 120000 },
  )
  return data
}

export async function deleteKnowledgeDocument(documentId) {
  const { data } = await apiClient.delete(`/api/knowledge/documents/${encodeURIComponent(documentId)}`)
  return data
}

export async function retrieveKnowledge(payload) {
  const { data } = await apiClient.post('/api/knowledge/retrieve', payload, { timeout: 60000 })
  return data
}

export async function getKnowledgeNetworkOverview(params = {}) {
  const { data } = await apiClient.get('/api/knowledge-network/overview', { params })
  return data.data
}

export async function expandKnowledgeNetworkNode(nodeId, limit = 30) {
  const { data } = await apiClient.get('/api/knowledge-network/expand', { params: { nodeId, limit } })
  return data.data
}

export async function getKnowledgeNetworkTimeline(limit = 40) {
  const { data } = await apiClient.get('/api/knowledge-network/timeline', { params: { limit } })
  return data.data
}

export async function getKnowledgeGrowthOverview(limit = 60) {
  const { data } = await apiClient.get('/api/knowledge-growth/overview', { params: { limit } })
  return data.data
}

export async function createKnowledgeFeedback(payload) {
  const { data } = await apiClient.post('/api/knowledge-network/feedback', payload)
  return data.data
}

export async function getKnowledgeFeedback(params = {}) {
  const { data } = await apiClient.get('/api/knowledge-network/feedback', { params })
  return data.data
}

export async function reviewKnowledgeFeedback(candidateId, payload) {
  const { data } = await apiClient.post(`/api/knowledge-network/feedback/${encodeURIComponent(candidateId)}/review`, payload)
  return data.data
}

export default apiClient
