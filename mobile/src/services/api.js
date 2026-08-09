import axios from 'axios'
import { clearAuthSession, getAuthToken } from '../stores/auth.js'

export class ApiError extends Error {
  constructor(message, { status = 0, code = '', details = null } = {}) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.code = code
    this.details = details
  }
}

const DEFAULT_NATIVE_API_BASE = 'https://lzhan.xyz'
const configuredBase = (
  import.meta.env.VITE_API_BASE_URL
  || (import.meta.env.VITE_NATIVE_BUILD === 'true' ? DEFAULT_NATIVE_API_BASE : '')
).replace(/\/$/, '')
const client = axios.create({ baseURL: configuredBase, timeout: 90000, withCredentials: true })

export function resolveApiUrl(value) {
  const url = String(value || '').trim()
  if (/^https:\/\//i.test(url)) return url
  if (!/^\/api\//i.test(url)) return ''
  return configuredBase ? `${configuredBase}${url}` : url
}

client.interceptors.request.use((config) => {
  const token = getAuthToken()
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

export function normalizeApiError(error) {
  if (error instanceof ApiError) return error
  const status = Number(error?.response?.status || 0)
  const payload = error?.response?.data || {}
  let message = payload.msg || payload.message || payload.error || error?.message || '请求失败'
  if (!navigator.onLine) message = '网络已断开，请恢复后重试'
  else if (status === 409) message = payload.msg || '请先完成学习画像'
  else if (status === 422) message = payload.msg || '智能体输出未通过结构校验'
  else if (status === 429) message = '请求过于频繁，请稍后重试'
  else if (status >= 500) message = payload.msg || '服务暂时不可用'
  return new ApiError(String(message), {
    status,
    code: String(payload.errorCode || payload.code || ''),
    details: payload,
  })
}

client.interceptors.response.use(
  response => response,
  (error) => {
    const normalized = normalizeApiError(error)
    if (normalized.status === 401) {
      clearAuthSession()
      if (!window.location.pathname.endsWith('/login')) window.location.assign(`${import.meta.env.BASE_URL}login`)
    }
    return Promise.reject(normalized)
  },
)

function directUrl(path) {
  return `${configuredBase}${path.startsWith('/') ? path : `/${path}`}`
}

function authHeaders(extra = {}) {
  const token = getAuthToken()
  return { ...extra, ...(token ? { Authorization: `Bearer ${token}` } : {}) }
}

async function readSse(response, onEvent) {
  if (!response.ok || !response.body) {
    const payload = await response.json().catch(() => ({}))
    throw new ApiError(payload.msg || `请求失败 (${response.status})`, { status: response.status, details: payload })
  }
  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''
  let lastData = null
  while (true) {
    const { value, done } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })
    const blocks = buffer.split(/\r?\n\r?\n/)
    buffer = blocks.pop() || ''
    for (const block of blocks) {
      const eventLine = block.split(/\r?\n/).find(line => line.startsWith('event:'))
      const data = block.split(/\r?\n/).filter(line => line.startsWith('data:')).map(line => line.slice(5).trim()).join('\n')
      if (!data) continue
      let parsed = data
      try { parsed = JSON.parse(data) } catch {}
      lastData = parsed
      await onEvent?.({ event: eventLine?.slice(6).trim() || 'message', data: parsed })
    }
  }
  return lastData
}

export async function login(payload) { return (await client.post('/api/auth/login', payload)).data }
export async function logout() { return (await client.post('/api/auth/logout')).data }
export async function getCurrentUser() { return (await client.get('/api/auth/me')).data }
export async function getCaptcha() { return (await client.get('/api/auth/captcha')).data }
export async function getProfiles() { return (await client.get('/api/learning-profile/profiles')).data }
export async function getProfile(id) { return (await client.get(`/api/learning-profile/profiles/${id}`)).data }
export async function activateProfile(id) { return (await client.post(`/api/learning-profile/profiles/${id}/activate`)).data }
export async function renameProfile(id, profileName) { return (await client.patch(`/api/learning-profile/profiles/${id}`, { profileName })).data }
export async function getProfileSessions() { return (await client.get('/api/learning-profile/sessions')).data }
export async function uploadInputs(files, context = 'chat') {
  const form = new FormData()
  Array.from(files).forEach(file => form.append('files', file))
  form.append('context', context)
  const { data } = await client.post('/api/multimodal-inputs', form, { timeout: 180000 })
  return data?.data?.attachments || []
}
export async function streamProfileChat(payload, onEvent, signal) {
  try {
    const response = await fetch(directUrl('/api/learning-profile/background-chat-stream'), {
      method: 'POST', credentials: 'include', signal,
      headers: authHeaders({ 'Content-Type': 'application/json' }), body: JSON.stringify(payload),
    })
    return await readSse(response, onEvent)
  } catch (error) { throw normalizeApiError(error) }
}
export async function resetProfileChat() { return (await client.post('/api/learning-profile/background-chat/reset')).data }
export async function getPathConfig() { return (await client.get('/api/learning-path/config')).data }
export async function getPathStage(stageId) { return (await client.get(`/api/learning-path/stages/${encodeURIComponent(stageId)}`)).data }
export async function getStageTasks(stageId) { return (await client.get(`/api/learning-path/stages/${encodeURIComponent(stageId)}/resource-tasks`)).data }
export async function prepareStage(stageId, payload = {}) { return (await client.post(`/api/learning-path/stages/${encodeURIComponent(stageId)}/prepare-resources`, payload)).data }
export async function streamGeneratePath(payload, onEvent, signal) {
  try {
    const response = await fetch(directUrl('/api/learning-path/generate-stream'), {
      method: 'POST', credentials: 'include', signal,
      headers: authHeaders({ 'Content-Type': 'application/json' }), body: JSON.stringify(payload),
    })
    return await readSse(response, onEvent)
  } catch (error) { throw normalizeApiError(error) }
}
export async function getTaskHistory(limit = 60) { return (await client.get('/api/xiaozhi/history', { params: { taskLimit: limit } })).data }
export async function getTask(taskId) { return (await client.get(`/api/xiaozhi/tasks/${encodeURIComponent(taskId)}`)).data }
export async function createResourceTask(payload) { return (await client.post('/api/personalized-resources/agent-task', payload)).data }
export async function startVideoTask(taskId, payload) { return (await client.post(`/api/personalized-resources/generated-videos/${encodeURIComponent(taskId)}/start`, payload)).data }
export async function tutor(payload) { return (await client.post('/api/xiaozhi/tutor', payload, { timeout: 120000 })).data }
export async function chat(payload) { return (await client.post('/api/xiaozhi/chat', payload, { timeout: 120000 })).data }
export async function getFeedback(params = {}) { return (await client.get('/api/learning-feedback', { params })).data }
export async function submitFeedback(payload) { return (await client.post('/api/xiaozhi/feedback', payload, { timeout: 120000 })).data }
export async function getEffectAssessment(profileId = '') { return (await client.get('/api/effect-assessment', { params: { profileId } })).data }
export async function pulseActivity(payload) { return (await client.post('/api/learning-activity/pulse', payload)).data }
export async function getQuestionHistory() { return (await client.get('/api/question-generator/history')).data }
export async function saveExamResult(payload) { return (await client.post('/api/question-generator/exam-results', payload)).data }
export async function scoreExam(payload) { return (await client.post('/api/question-generator/ai-score', payload, { timeout: 120000 })).data }

export { client }
