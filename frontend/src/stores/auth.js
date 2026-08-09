const AUTH_TOKEN_KEY = 'authToken'
const CURRENT_USER_KEY = 'currentUser'
const LAST_LOGIN_ACCOUNT_KEY = 'lastLoginAccount'
const CODEX_PREVIEW_AUTH_KEY = 'codexPreviewAuth'
const CODEX_PREVIEW_TOKEN = 'codex-preview-token'

export function getAuthToken() {
  const token = localStorage.getItem(AUTH_TOKEN_KEY) || ''
  if (token) return token
  const isLocalHost = ['localhost', '127.0.0.1', '::1'].includes(window.location.hostname)
  if (isLocalHost && localStorage.getItem(CODEX_PREVIEW_AUTH_KEY) === '1') {
    return CODEX_PREVIEW_TOKEN
  }
  return ''
}

export function setAuthSession(payload) {
  const { token, expiresIn, ...user } = payload || {}
  if (token) {
    localStorage.setItem(AUTH_TOKEN_KEY, token)
  }
  localStorage.setItem('appMode', 'user')
  localStorage.setItem(CURRENT_USER_KEY, JSON.stringify(user))
  window.dispatchEvent(new Event('current-user-change'))
}

export function clearAuthSession() {
  const currentUser = readCurrentUser()
  rememberLoginAccount(
    currentUser.username || currentUser.email || currentUser.account || currentUser.loginName,
  )
  localStorage.removeItem(AUTH_TOKEN_KEY)
  localStorage.removeItem(CURRENT_USER_KEY)
  localStorage.removeItem('appMode')
  localStorage.removeItem(CODEX_PREVIEW_AUTH_KEY)
  window.dispatchEvent(new Event('current-user-change'))
}

export function rememberLoginAccount(value) {
  const account = String(value || '').trim()
  if (account) localStorage.setItem(LAST_LOGIN_ACCOUNT_KEY, account)
}

export function readRememberedLoginAccount() {
  return localStorage.getItem(LAST_LOGIN_ACCOUNT_KEY) || ''
}

export function readCurrentUser() {
  try {
    return JSON.parse(localStorage.getItem(CURRENT_USER_KEY) || '{}')
  } catch {
    return {}
  }
}

export function hasLocalAuth() {
  return Boolean(getAuthToken() || readCurrentUser().id)
}
