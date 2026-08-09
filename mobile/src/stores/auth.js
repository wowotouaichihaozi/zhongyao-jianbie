import { computed, reactive } from 'vue'

const AUTH_TOKEN_KEY = 'authToken'
const CURRENT_USER_KEY = 'currentUser'

function readUser() {
  try {
    return JSON.parse(localStorage.getItem(CURRENT_USER_KEY) || '{}')
  } catch {
    return {}
  }
}

export const authState = reactive({
  token: localStorage.getItem(AUTH_TOKEN_KEY) || '',
  user: readUser(),
})

export const isAuthenticated = computed(() => Boolean(authState.token))

export function getAuthToken() {
  return authState.token || localStorage.getItem(AUTH_TOKEN_KEY) || ''
}

export function setAuthSession(payload = {}) {
  const { token, expiresIn: _expiresIn, ...user } = payload
  if (token) localStorage.setItem(AUTH_TOKEN_KEY, token)
  localStorage.setItem(CURRENT_USER_KEY, JSON.stringify(user))
  localStorage.setItem('appMode', 'user')
  authState.token = token || authState.token
  authState.user = user
}

export function clearAuthSession() {
  localStorage.removeItem(AUTH_TOKEN_KEY)
  localStorage.removeItem(CURRENT_USER_KEY)
  localStorage.removeItem('appMode')
  authState.token = ''
  authState.user = {}
}

export function updateLocalUser(user = {}) {
  authState.user = { ...authState.user, ...user }
  localStorage.setItem(CURRENT_USER_KEY, JSON.stringify(authState.user))
}
