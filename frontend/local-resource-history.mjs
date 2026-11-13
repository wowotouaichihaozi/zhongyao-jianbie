const active = new WeakMap()
function cacheKey() {
  const identity = localStorage.getItem('authToken') || ''
  let hash = 2166136261
  for (const c of identity) hash = Math.imul(hash ^ c.charCodeAt(0), 16777619)
  return 'resource-history-v1:' + (hash >>> 0).toString(16)
}
function deadline(promise, ms) {
  let timer
  return Promise.race([promise, new Promise((_, reject) => { timer = setTimeout(() => reject(new Error('资源同步超时')), ms) })]).finally(() => clearTimeout(timer))
}
export async function loadVideoPages(fetchPage, publish) {
  const tasks = [], seen = new Set()
  let offset = 0
  for (;;) {
    const page = await fetchPage({ limit: 100, offset })
    const batch = Array.isArray(page?.tasks) ? page.tasks : []
    let added = 0
    for (const task of batch) {
      const id = String(task.taskId || task.id || JSON.stringify(task))
      if (!seen.has(id)) { seen.add(id); tasks.push(task); added++ }
    }
    if (publish(tasks) === false) return tasks
    if (!page?.hasMore || !batch.length) return tasks
    if (!added) throw new Error('视频历史分页没有推进，请重试')
    offset += batch.length
  }
}
export function loadHistory(options) {
  if (active.has(options.owner)) return active.get(options.owner)
  const job = run(options).finally(() => active.delete(options.owner))
  active.set(options.owner, job)
  return job
}
async function run(o) {
  const key = cacheKey(), timeout = o.timeout || 12000
  let cached = [], legacy = [], history = [], videos = [], remaining = 2
  const failures = []
  try { const value = JSON.parse(sessionStorage.getItem(key) || 'null'); if (Date.now() - value?.savedAt < 1800000 && Array.isArray(value?.items)) cached = value.items } catch {}
  try { const value = JSON.parse(localStorage.getItem('personalizedResources') || '[]'); if (Array.isArray(value)) legacy = value.filter(x => x?.source === 'workflow-real-data' || x?.metadata) } catch {}
  o.setError('')
  o.setWarning('')
  o.setLoading(true)
  const merge = includeCached => {
    const seen = new Set()
    return o.sort([...videos.flatMap(o.extract), ...history.flatMap(o.extract), ...legacy, ...(includeCached ? cached : [])].filter(x => {
      if (!x) return false
      const id = String(x.id || `${x.type}:${x.title}`)
      if (seen.has(id)) return false
      seen.add(id)
      return true
    }))
  }
  function show() {
    const items = merge(remaining > 0 || failures.length > 0)
    if (items.length || remaining === 0) { o.publish(items); o.setLoading(false) }
    if (items.length) o.setError('')
    if (remaining && items.length) o.setWarning('已展示可用资源，其余记录正在后台同步。')
    else if (!remaining && failures.length) {
      if (items.length) o.setWarning(failures.join('、') + '暂未同步，已保留可用记录，可点击刷新重试。')
      else o.setError('历史资源暂时无法同步，请点击重试。')
    } else if (!remaining) o.setWarning('')
    if (items.length && (history.length || videos.length)) {
      try { const json = JSON.stringify({ savedAt: Date.now(), items, partial: remaining > 0 || failures.length > 0 }); if (json.length < 2000000) sessionStorage.setItem(key, json) } catch {}
    }
    return items
  }
  if (cached.length || legacy.length) show()
  const initialWait = setTimeout(() => {
    if (remaining > 0 && !merge(true).length) {
      o.setLoading(false)
      o.setError('历史记录尚未返回，正在后台继续同步，可稍后重试。')
    }
  }, o.initialWait || 4000)
  async function source(name, fetch, update, limit = timeout) {
    let live = true
    try { await deadline(Promise.resolve().then(() => fetch(value => { if (live) { update(value); show() } return live })), limit) }
    catch { failures.push(name) }
    finally { live = false; remaining--; show() }
  }
  await Promise.all([
    source('任务历史', async publish => { const value = await o.history(); publish(value?.data?.tasks || []) }, value => { history = value }, o.historyTimeout || o.timeout || 45000),
    source('视频历史', async publish => { const value = await o.videos(publish); publish(value) }, value => { videos = value }),
  ])
  clearTimeout(initialWait)
  const items = show()
  if (!failures.length || history.length || videos.length) {
    try { const json = JSON.stringify({ savedAt: Date.now(), items, partial: failures.length > 0 }); if (json.length < 2000000) sessionStorage.setItem(key, json) } catch {}
  }
  return items
}
