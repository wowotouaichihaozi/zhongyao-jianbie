import { getLearningPathNodeCaches, saveLearningPathNodeCache } from './api.js'

export const LEARNING_PATH_NODE_CACHE_KEY = 'qianzhi-learning-path-node-results:v1'

let hydratePromise = null

export function readNodeCaches() {
  try {
    if (typeof localStorage === 'undefined') return {}
    const parsed = JSON.parse(localStorage.getItem(LEARNING_PATH_NODE_CACHE_KEY) || '{}')
    return parsed && typeof parsed === 'object' && !Array.isArray(parsed) ? parsed : {}
  } catch {
    return {}
  }
}

export function getNodeCache(cacheKey) {
  const key = String(cacheKey || '').trim()
  if (!key) return null
  return readNodeCaches()[key] || null
}

function updateNodeCache(cacheKey, patch = {}, shouldPersist = true) {
  const key = String(cacheKey || '').trim()
  if (!key) return null
  const now = Date.now()
  const caches = readNodeCaches()
  const previous = caches[key] || {}
  const entry = {
    ...previous,
    ...patch,
    cacheKey: key,
    createdAt: previous.createdAt || now,
    updatedAt: now,
  }
  caches[key] = entry
  try {
    localStorage.setItem(LEARNING_PATH_NODE_CACHE_KEY, JSON.stringify(caches))
    window.dispatchEvent(new CustomEvent('learning-path-node-cache-updated', { detail: { cacheKey: key, entry } }))
  } catch {
    // Ignore quota failures; the resource page can still work without cache.
  }
  if (shouldPersist) void persistNodeCache(entry)
  return entry
}

export function setNodeCache(cacheKey, patch = {}) {
  return updateNodeCache(cacheKey, patch, true)
}

export function markNodeCacheStarted(cacheKey, metadata = {}) {
  const previous = getNodeCache(cacheKey)
  if (previous?.status === 'complete') {
    return setNodeCache(cacheKey, { ...metadata, status: 'complete', lastOpenedAt: Date.now() })
  }
  return setNodeCache(cacheKey, { ...metadata, status: 'running', startedAt: previous?.startedAt || Date.now() })
}

export async function markNodeCacheViewed(cacheKey, metadata = {}) {
  const previous = getNodeCache(cacheKey)
  const now = Date.now()
  const entry = updateNodeCache(cacheKey, {
    ...metadata,
    status: previous?.status === 'complete' ? 'complete' : 'running',
    startedAt: previous?.startedAt || now,
    lastOpenedAt: now,
    viewedAt: metadata.viewedAt || now,
    viewSource: 'learning-path-task-open',
  }, false)
  const result = await persistNodeCache(entry)
  if (result?.entry) {
    updateNodeCache(cacheKey, result.entry, false)
  }
  return {
    entry: result?.entry || entry,
    nextWeekTask: result?.nextWeekTask || null,
    viewProgress: result?.viewProgress || null,
  }
}

export function markNodeCacheComplete(cacheKey, metadata = {}) {
  return setNodeCache(cacheKey, {
    ...metadata,
    status: 'complete',
    completedAt: metadata.completedAt || Date.now(),
    lastOpenedAt: Date.now(),
  })
}

export function markNodeCacheError(cacheKey, metadata = {}) {
  return setNodeCache(cacheKey, { ...metadata, status: 'error', lastErrorAt: Date.now() })
}

export function appendNodeCacheParams(rawRoute, params = {}) {
  const route = String(rawRoute || '').trim()
  if (!route) return ''
  if (/^https?:\/\//i.test(route)) {
    const url = new URL(route)
    Object.entries(params).forEach(([key, value]) => {
      if (value !== undefined && value !== null && String(value) !== '') url.searchParams.set(key, String(value))
    })
    return url.toString()
  }
  const url = new URL(route, window.location.origin)
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null && String(value) !== '') url.searchParams.set(key, String(value))
  })
  return `${url.pathname}${url.search}${url.hash}`
}

export function hydrateNodeCachesFromServer() {
  if (hydratePromise) return hydratePromise
  hydratePromise = getLearningPathNodeCaches()
    .then((remoteCaches) => {
      if (!remoteCaches || typeof remoteCaches !== 'object' || Array.isArray(remoteCaches)) return readNodeCaches()
      const localCaches = readNodeCaches()
      const merged = { ...remoteCaches, ...localCaches }
      Object.entries(remoteCaches).forEach(([key, remoteEntry]) => {
        const localEntry = localCaches[key]
        if (!localEntry || compareCacheTime(remoteEntry, localEntry) > 0) {
          merged[key] = remoteEntry
        }
      })
      try {
        localStorage.setItem(LEARNING_PATH_NODE_CACHE_KEY, JSON.stringify(merged))
        window.dispatchEvent(new CustomEvent('learning-path-node-cache-updated', { detail: { caches: merged } }))
      } catch {
        // Keep local cache untouched when storage is unavailable.
      }
      return merged
    })
    .catch(() => readNodeCaches())
    .finally(() => {
      hydratePromise = null
    })
  return hydratePromise
}

function persistNodeCache(entry) {
  if (!entry?.cacheKey) return Promise.resolve(null)
  return saveLearningPathNodeCache(entry.cacheKey, entry).catch(() => null)
}

function compareCacheTime(left, right) {
  return cacheTime(left) - cacheTime(right)
}

function cacheTime(entry) {
  const value = entry?.updatedAt || entry?.updated_at || entry?.completedAt || entry?.createdAt || 0
  if (typeof value === 'number') return value
  const parsed = Date.parse(value)
  return Number.isFinite(parsed) ? parsed : 0
}
