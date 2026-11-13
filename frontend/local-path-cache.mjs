const pending = new Map(), epochs = new Map()
const clone = value => JSON.parse(JSON.stringify(value))
function identity() {
  const token = localStorage.getItem('authToken') || ''
  let hash = 2166136261
  for (const c of token) hash = Math.imul(hash ^ c.charCodeAt(0), 16777619)
  let id = ''
  try { id = JSON.parse(localStorage.getItem('currentUser') || '{}').id || '' } catch {}
  return `${id}:${(hash >>> 0).toString(16)}`
}
function keyFor(url) { return 'saved-path-v1:' + identity() + ':' + url }
function eligible(data) {
  const meta = data?.meta || data?.config?.meta || {}
  if (meta.profileSwitchPending || meta.needsRegeneration) return false
  if (data?.stage?.id) return Array.isArray(data.stage.nodes) && data.stage.nodes.length > 0
  return Number(meta.activeProfileReportId || meta.profileReportId) > 0 && Array.isArray(data?.weeks) && data.weeks.some(w => w.enabled !== false && !w.placeholder)
}
function read(key) {
  try { const item = JSON.parse(sessionStorage.getItem(key) || 'null'); if (Date.now() - item?.at < 1800000 && eligible(item.data)) return item } catch {}
  return null
}
function write(key, data) {
  if (!eligible(data)) return
  try {
    const json = JSON.stringify({ at: Date.now(), data })
    if (json.length < 2000000) sessionStorage.setItem(key, json)
  } catch { /* A storage quota must not block loading. */ }
}
function fetchOnce(key, load) {
  if (pending.has(key)) return pending.get(key)
  const epoch = epochs.get(identity()) || 0, owner = identity()
  const promise = Promise.resolve().then(load).then(data => {
    if (identity() === owner && (epochs.get(owner) || 0) === epoch) write(key, data)
    return { data, valid: identity() === owner && (epochs.get(owner) || 0) === epoch }
  }).finally(() => { if (pending.get(key) === promise) pending.delete(key) })
  pending.set(key, promise)
  return promise
}
export function invalidatePathCache(url = '') {
  if (!/\/api\/(?:auth\/logout|question-generator\/exam-results|learning-profile\/|learning-path\/(?:config|generate))/.test(url)) return
  const owner = identity()
  epochs.set(owner, (epochs.get(owner) || 0) + 1)
  const prefix = 'saved-path-v1:' + owner + ':'
  try { for (let i = sessionStorage.length - 1; i >= 0; i--) { const key = sessionStorage.key(i); if (key?.startsWith(prefix)) sessionStorage.removeItem(key) } } catch { /* Caching must not turn a successful save into an error. */ }
  for (const key of pending.keys()) if (key.startsWith(prefix)) pending.delete(key)
}
export async function readSavedPath(url, load, options = {}) {
  if (options.fresh) return load()
  const key = keyFor(url), cached = read(key)
  if (!cached) return (await fetchOnce(key, load)).data
  const displayed = clone(cached.data)
  if (displayed.meta) displayed.meta = { ...displayed.meta, canGeneratePersonalized: false, canPrepareResources: false }
  const refresh = Date.now() - cached.at < 15000 ? Promise.resolve({ data: cached.data, valid: true }) : fetchOnce(key, load)
  refresh.then(({ data, valid }) => {
    if (valid && options.onFresh) setTimeout(() => options.onFresh(clone(data)), 0)
  }).catch(() => { /* Keep the saved snapshot during a network interruption. */ })
  return displayed
}
async function getSaved(url) {
  const token = localStorage.getItem('authToken')
  if (!token) return null
  const response = await fetch(url, { credentials: 'include', signal: AbortSignal.timeout(20000), headers: { Authorization: 'Bearer ' + token } })
  if (!response.ok) throw new Error('Saved path request failed')
  const body = await response.json()
  return body.data || body
}
async function prefetch() {
  if (!localStorage.getItem('authToken')) return
  const url = '/api/learning-path/config?summary=1', key = keyFor(url)
  try {
    const item = read(key)
    const data = item && Date.now() - item.at < 15000 ? item.data : (await fetchOnce(key, () => getSaved(url))).data
    const first = data?.weeks?.find(w => w.enabled !== false && !w.placeholder)
    if (first?.id) {
      const stage = '/api/learning-path/stages/' + encodeURIComponent(first.id) + '?includeConfig=0'
      if (!read(keyFor(stage))) await fetchOnce(keyFor(stage), () => getSaved(stage))
    }
  } catch { /* Prefetch is read-only and must never block the active page. */ }
}
if (typeof window !== 'undefined') {
  setTimeout(() => prefetch().catch(() => {}), 800)
  window.addEventListener('current-user-change', () => setTimeout(() => prefetch().catch(() => {}), 300))
  window.addEventListener('storage', event => {
    if (event.key?.startsWith('learning-profile')) invalidatePathCache('/api/learning-profile/context-switch')
  })
}
