export const DEFAULT_AUTHENTICATED_PATH = '/learning-profile'

const LOGIN_PATH = '/login'

function decodePathname(pathname) {
  let decodedPath = String(pathname || '')
  for (let index = 0; index < 5; index += 1) {
    try {
      const nextPath = decodeURIComponent(decodedPath)
      if (nextPath === decodedPath) return decodedPath
      decodedPath = nextPath
    } catch {
      return ''
    }
  }
  return ''
}

function isBlockedPath(pathname) {
  const decodedPath = decodePathname(pathname)
  if (!decodedPath || decodedPath.includes('\\') || decodedPath.startsWith('//')) return true
  const normalizedPath = decodedPath.toLowerCase().replace(/\/+/g, '/').replace(/\/+$/, '') || '/'
  return normalizedPath === '/' || normalizedPath === LOGIN_PATH || normalizedPath.startsWith(`${LOGIN_PATH}/`)
}

export function safeInternalRedirect(value, fallback = '') {
  if (typeof value !== 'string') return fallback

  const target = value.trim()
  if (!target.startsWith('/') || target.startsWith('//')) return fallback
  if (target.includes('\\') || /%5c/i.test(target) || /[\u0000-\u001f\u007f]/.test(target)) return fallback

  try {
    const parsed = new URL(target, 'https://internal.invalid')
    if (parsed.origin !== 'https://internal.invalid' || isBlockedPath(parsed.pathname)) return fallback
  } catch {
    return fallback
  }

  return target
}

export function internalRedirectFromLocation(locationLike) {
  if (!locationLike) return ''
  const pathname = String(locationLike.pathname || '/')
  const search = String(locationLike.search || '')
  const hash = String(locationLike.hash || '')
  return safeInternalRedirect(`${pathname}${search}${hash}`)
}

export function buildLoginRedirectPath(value) {
  const target = safeInternalRedirect(value)
  return target ? `${LOGIN_PATH}?redirect=${encodeURIComponent(target)}` : LOGIN_PATH
}
