const { request } = require('./request')

const api = {
  captcha: () => request({ url: '/api/auth/captcha' }),
  login: data => request({ url: '/api/auth/login', method: 'POST', data }),
  logout: () => request({ url: '/api/auth/logout', method: 'POST' }),
  me: () => request({ url: '/api/auth/me' }),
  profiles: () => request({ url: '/api/learning-profile/profiles' }),
  activateProfile: id => request({ url: `/api/learning-profile/profiles/${id}/activate`, method: 'POST' }),
  profileChat: data => request({ url: '/api/learning-profile/background-chat', method: 'POST', data, timeout: 120000 }),
  resetProfileChat: () => request({ url: '/api/learning-profile/background-chat/reset', method: 'POST' }),
  pathConfig: () => request({ url: '/api/learning-path/config' }),
  taskHistory: (limit = 60) => request({ url: `/api/xiaozhi/history?taskLimit=${limit}` }),
  task: id => request({ url: `/api/xiaozhi/tasks/${encodeURIComponent(id)}` }),
  createResourceTask: data => request({ url: '/api/personalized-resources/agent-task', method: 'POST', data, timeout: 120000 }),
  startVideoTask: (id, data) => request({ url: `/api/personalized-resources/generated-videos/${encodeURIComponent(id)}/start`, method: 'POST', data, timeout: 120000 }),
  tutor: data => request({ url: '/api/xiaozhi/tutor', method: 'POST', data, timeout: 120000 }),
  submitFeedback: data => request({ url: '/api/xiaozhi/feedback', method: 'POST', data, timeout: 120000 }),
  assessment: profileId => request({ url: `/api/effect-assessment${profileId ? `?profileId=${profileId}` : ''}` }),
}

module.exports = api
