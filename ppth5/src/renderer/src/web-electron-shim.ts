type Listener = (event: unknown, payload: unknown) => void

type ModelConfig = {
  id: string
  name: string
  provider: 'anthropic' | 'openai' | 'google'
  model: string
  apiKey: string
  serverManaged?: boolean
  baseUrl: string
  maxTokens: number
  disableTemperature: boolean
  active: boolean
  createdAt: number
  updatedAt: number
}

type ImageModelConfig = {
  id: string
  name: string
  provider: string
  active: boolean
  modelConfig: string
  createdAt: number
  updatedAt: number
}

type SessionRecord = {
  id: string
  title: string
  topic: string
  styleId: string
  page_count: number
  generated_count: number
  status: string
  provider: string
  model: string
  created_at: number
  updated_at: number
  metadata: string | null
}

type GeneratedPageRecord = {
  id: string
  pageNumber: number
  title: string
  contentOutline?: string | null
  html: string
  htmlPath?: string
  pageId?: string
  sourceUrl?: string
  status?: string
  error?: string | null
}

type BrowserTemplateListItem = {
  id: string
  name: string
  description: string
  source: 'user'
  pageCount: number
  tags: string[]
  previewHtmlPath: string | null
  previewPages: Array<{
    pageNumber: number
    pageId: string
    title: string
    htmlPath: string
  }>
  createdAt: number
  updatedAt: number
}

type BrowserStoredTemplate = BrowserTemplateListItem & {
  pagesHtml: Array<{
    pageNumber: number
    pageId: string
    title: string
    html: string
  }>
}

type BrowserCustomStyle = {
  id: string
  styleKey: string
  label: string
  description: string
  aliases: string[]
  category: string
  styleSkill: string
  source: 'custom' | 'override'
  editable: boolean
  styleCase: string
  createdAt: number
  updatedAt: number
}

const STORAGE_PREFIX = 'oh-my-ppt-h5:'
const FIXED_MODEL_CONFIG: ModelConfig = {
  id: 'spark-x2-agent-default',
  name: 'Spark X2 Flash',
  provider: 'anthropic',
  model: 'astron-code-latest',
  apiKey: '',
  serverManaged: true,
  baseUrl: 'https://maas-coding-api.cn-huabei-1.xf-yun.com/anthropic',
  maxTokens: 8192,
  disableTemperature: false,
  active: true,
  createdAt: 0,
  updatedAt: 0
}
const DEFAULT_PPT_API_BASE = import.meta.env.BASE_URL?.startsWith('/ppt')
  ? import.meta.env.DEV
    ? '/api'
    : '/ppt-api'
  : ''
const API_BASE = import.meta.env.VITE_PPT_H5_API_BASE || DEFAULT_PPT_API_BASE
const FULL_IPC_BASE = import.meta.env.VITE_PPT_H5_FULL_IPC_BASE || ''
const listeners = new Map<string, Set<Listener>>()
const activeGenerationControllers = new Map<string, AbortController>()

const apiUrl = (path: string): string => `${API_BASE || '/api'}${path}`

const nowSeconds = (): number => Math.floor(Date.now() / 1000)
const uid = (prefix: string): string => `${prefix}_${Date.now().toString(36)}_${Math.random().toString(36).slice(2, 8)}`
const resourceUrl = (path: string): string => `${import.meta.env.BASE_URL}resources/${path.replace(/^\/+/, '')}`
const stylePreviewUrl = (styleKey: string): string => resourceUrl(`styleHtml/${encodeURIComponent(styleKey)}.html`)

const readJson = <T>(key: string, fallback: T): T => {
  try {
    const raw = localStorage.getItem(`${STORAGE_PREFIX}${key}`)
    return raw ? (JSON.parse(raw) as T) : fallback
  } catch {
    return fallback
  }
}

const writeJson = (key: string, value: unknown): void => {
  localStorage.setItem(`${STORAGE_PREFIX}${key}`, JSON.stringify(value))
}

const readModels = (): ModelConfig[] => [FIXED_MODEL_CONFIG]
const writeModels = (_models: ModelConfig[]): void => writeJson('models', [FIXED_MODEL_CONFIG])
const normalizeImageModel = (config: ImageModelConfig): ImageModelConfig => {
  let modelConfig: Record<string, unknown> = {}
  try {
    const parsed = JSON.parse(config.modelConfig || '{}')
    if (parsed && typeof parsed === 'object' && !Array.isArray(parsed)) modelConfig = parsed
  } catch {
    modelConfig = {}
  }
  return {
    ...config,
    name: config.name || '豆包 Seedream 4.5',
    provider: 'seedream',
    modelConfig: JSON.stringify({
      ...modelConfig,
      baseUrl: 'https://api.apimart.ai/v1',
      model: 'seedream-4-5',
      resolution: modelConfig.resolution || '2K'
    })
  }
}
const readImageModels = (): ImageModelConfig[] =>
  readJson<ImageModelConfig[]>('image-models', []).map(normalizeImageModel)
const writeImageModels = (models: ImageModelConfig[]): void =>
  writeJson('image-models', models.map(normalizeImageModel))
const readSessions = (): SessionRecord[] => readJson<SessionRecord[]>('sessions', [])
const writeSessions = (sessions: SessionRecord[]): void => writeJson('sessions', sessions)
const readPages = (sessionId: string): GeneratedPageRecord[] =>
  readJson<GeneratedPageRecord[]>(`pages:${sessionId}`, [])
const writePages = (sessionId: string, pages: GeneratedPageRecord[]): void =>
  writeJson(`pages:${sessionId}`, pages)
const readCustomStyles = (): BrowserCustomStyle[] => readJson<BrowserCustomStyle[]>('custom-styles', [])
const writeCustomStyles = (styles: BrowserCustomStyle[]): void => writeJson('custom-styles', styles)
const readStoredTemplates = (): BrowserStoredTemplate[] =>
  readJson<BrowserStoredTemplate[]>('templates', [])
const writeStoredTemplates = (templates: BrowserStoredTemplate[]): void =>
  writeJson('templates', templates)

const readJsonFromString = (value: string): Record<string, unknown> => {
  try {
    const parsed = JSON.parse(value)
    return parsed && typeof parsed === 'object' && !Array.isArray(parsed)
      ? (parsed as Record<string, unknown>)
      : {}
  } catch {
    return {}
  }
}

const emit = (channel: string, payload: unknown): void => {
  listeners.get(channel)?.forEach((listener) => listener({}, payload))
}

let fullIpcAvailable: boolean | null = null

const invokeFullIpc = async (channel: string, args: unknown[]): Promise<unknown> => {
  if (!FULL_IPC_BASE) {
    fullIpcAvailable = false
    throw new Error(`Full IPC backend is disabled in static H5 mode: ${channel}`)
  }
  const endpoint = `${FULL_IPC_BASE}/api/ipc/${encodeURIComponent(channel)}`
  const res = await fetch(endpoint, {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify({ args })
  })

  if (res.status === 404) {
    fullIpcAvailable = false
    throw new Error(`Full IPC channel not available: ${channel}`)
  }

  const data = (await res.json()) as { ok?: boolean; result?: unknown; error?: string }
  if (!res.ok || !data.ok) {
    throw new Error(data.error || `Full IPC request failed: ${channel}`)
  }
  fullIpcAvailable = true
  return data.result
}

const setupFullIpcEvents = (): void => {
  if (!FULL_IPC_BASE) {
    fullIpcAvailable = false
    return
  }
  if (typeof EventSource === 'undefined') return
  try {
    const events = new EventSource(`${FULL_IPC_BASE}/api/events`)
    events.addEventListener('ready', () => {
      fullIpcAvailable = true
    })
    events.addEventListener('ipc', (event) => {
      try {
        const data = JSON.parse((event as MessageEvent).data) as {
          channel?: unknown
          payload?: unknown
        }
        if (typeof data.channel === 'string') {
          emit(data.channel, data.payload)
        }
      } catch {
        // Ignore malformed backend event frames.
      }
    })
    events.onerror = () => {
      if (fullIpcAvailable === null) fullIpcAvailable = false
    }
  } catch {
    fullIpcAvailable = false
  }
}

const htmlToDataUrl = (html: string): string => {
  const bytes = new TextEncoder().encode(html)
  let binary = ''
  bytes.forEach((byte) => {
    binary += String.fromCharCode(byte)
  })
  return `data:text/html;base64,${btoa(binary)}`
}

const getSettings = (): Record<string, unknown> =>
  readJson<Record<string, unknown>>('settings', {
    storagePath: 'browser-local-storage',
    proxyUrl: '',
    timeouts: {}
  })

const saveSettings = (patch: Record<string, unknown>): { success: boolean } => {
  writeJson('settings', { ...getSettings(), ...patch })
  return { success: true }
}

const normalizeStyleItem = (
  style: Record<string, unknown>,
  index = 0,
  editable = false
): Record<string, unknown> => {
  const styleKey = String(style.styleKey || style.style || style.id || `style-${index}`)
  return {
    id: String(style.id || styleKey),
    styleKey,
    label: String(style.label || style.styleName || style.name || style.style || `Style ${index + 1}`),
    description: String(style.description || ''),
    aliases: Array.isArray(style.aliases) ? style.aliases : [],
    category: String(style.category || (editable ? '自定义' : 'Builtin')),
    source: style.source || (editable ? 'custom' : 'builtin'),
    editable: Boolean(style.editable ?? editable),
    styleSkill: String(style.styleSkill || ''),
    styleCase: String(style.styleCase || ''),
    previewPath:
      typeof style.previewPath === 'string' && style.previewPath
        ? style.previewPath
        : stylePreviewUrl(styleKey),
    createdAt: Number(style.createdAt || 0),
    updatedAt: Number(style.updatedAt || 0)
  }
}

const fetchBackendStyles = async (): Promise<Record<string, unknown>[]> => {
  if (!API_BASE) return []
  try {
    const res = await fetch(apiUrl('/styles'))
    if (!res.ok) return []
    const data = (await res.json()) as { items?: unknown[] }
    return Array.isArray(data.items)
      ? data.items
          .filter((item): item is Record<string, unknown> => !!item && typeof item === 'object')
          .map((item, index) => normalizeStyleItem(item, index, true))
      : []
  } catch {
    return []
  }
}

const uniqueStyles = (items: Record<string, unknown>[]): Record<string, unknown>[] => {
  const seen = new Set<string>()
  const result: Record<string, unknown>[] = []
  for (const item of items) {
    const keys = [item.id, item.styleKey].map((value) => String(value || '')).filter(Boolean)
    if (keys.some((key) => seen.has(key))) continue
    keys.forEach((key) => seen.add(key))
    result.push(item)
  }
  return result
}

const listStyles = async (): Promise<{ items: unknown[] }> => {
  const res = await fetch(`${import.meta.env.BASE_URL}styles.json`)
  const styles = (await res.json()) as Array<Record<string, unknown>>
  const builtinItems = styles.map((style, index) => normalizeStyleItem(style, index, false))
  const backendItems = await fetchBackendStyles()
  const customItems = readCustomStyles()
    .filter((style) => style.id && style.label)
    .map((style, index) => normalizeStyleItem(style, index, true))
  return {
    items: uniqueStyles([...backendItems, ...customItems, ...builtinItems])
  }
}

const getStyles = async (): Promise<{ categories: Record<string, unknown[]>; defaultStyle: string }> => {
  const { items } = await listStyles()
  const categories: Record<string, unknown[]> = {}
  for (const item of items as Array<Record<string, unknown>>) {
    const category = String(item.category || 'Builtin')
    categories[category] ||= []
    categories[category].push({
      id: item.id,
      label: item.label,
      description: item.description,
      source: item.source,
      editable: false,
      styleCase: item.styleCase
    })
  }
  const defaultStyle = (items as Array<Record<string, unknown>>).find(
    (item) => item.styleKey === 'bauhaus' || item.id === 'bauhaus'
  )?.id
  const first = (items[0] as Record<string, unknown> | undefined)?.id
  return { categories, defaultStyle: String(defaultStyle || first || 'bauhaus') }
}

const getStyleDetail = async (styleId: string): Promise<unknown> => {
  const custom = readCustomStyles().find((item) => item.id === styleId || item.styleKey === styleId)
  if (custom) return custom
  const { items } = await listStyles()
  const merged = (items as Array<Record<string, unknown>>).find(
    (item) => item.id === styleId || item.styleKey === styleId
  )
  if (merged) return merged
  const res = await fetch(`${import.meta.env.BASE_URL}styles.json`)
  const styles = (await res.json()) as Array<Record<string, unknown>>
  const style = styles.find((item) => item.style === styleId) || styles[0] || {}
  return {
    id: String(style.style || styleId),
    styleKey: String(style.style || styleId),
    label: String(style.styleName || style.style || styleId),
    description: String(style.description || ''),
    aliases: Array.isArray(style.aliases) ? style.aliases : [],
    styleSkill: String(style.styleSkill || ''),
    source: style.source || 'builtin',
    editable: false,
    category: String(style.category || 'Builtin'),
    styleCase: String(style.styleCase || ''),
    previewPath: stylePreviewUrl(String(style.style || styleId))
  }
}

const slugify = (value: string, fallback = 'style'): string => {
  const ascii = value
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9\u4e00-\u9fa5]+/g, '-')
    .replace(/^-+|-+$/g, '')
  return ascii || fallback
}

const createOrUpdateBrowserStyle = (
  payload: unknown,
  styleId?: string
): { success: boolean; id: string; source: 'custom' | 'override' } => {
  const data = (payload || {}) as Record<string, unknown>
  const timestamp = nowSeconds()
  const label = String(data.label || '').trim()
  const styleSkill = String(data.styleSkill || '').trim()
  if (!label) throw new Error('Style name is required.')
  if (!styleSkill) throw new Error('Style prompt is required.')
  const id = styleId || `style-${uid(slugify(label, 'custom')).replace(/^style_?/, '')}`
  const next: BrowserCustomStyle = {
    id,
    styleKey: id,
    label,
    description: String(data.description || '').trim(),
    aliases: Array.isArray(data.aliases) ? data.aliases.map((item) => String(item)) : [],
    category: String(data.category || '自定义').trim() || '自定义',
    styleSkill,
    source: 'custom',
    editable: true,
    styleCase: String(data.styleCase || '').trim(),
    createdAt: readCustomStyles().find((style) => style.id === id)?.createdAt || timestamp,
    updatedAt: timestamp
  }
  writeCustomStyles([next, ...readCustomStyles().filter((style) => style.id !== id)])
  return { success: true, id, source: 'custom' }
}

const parseBrowserStyleText = (content: string, fileName = ''): Record<string, unknown> => {
  const trimmed = content.trim()
  if (!trimmed) throw new Error('文件内容为空，无法解析风格。')
  try {
    const parsed = JSON.parse(trimmed) as Record<string, unknown>
    const label = String(parsed.label || parsed.styleName || parsed.name || '').trim()
    const styleSkill = String(parsed.styleSkill || parsed.prompt || parsed.content || trimmed).trim()
    return {
      label: label || fileName.replace(/\.[^.]+$/, '') || '导入风格',
      description: String(parsed.description || '').trim(),
      category: String(parsed.category || '自定义').trim() || '自定义',
      aliases: Array.isArray(parsed.aliases) ? parsed.aliases : [],
      styleCase: String(parsed.styleCase || '').trim(),
      styleSkill
    }
  } catch {
    const firstHeading = trimmed.match(/^#\s+(.+)$/m)?.[1]?.trim()
    const label = firstHeading || fileName.replace(/\.[^.]+$/, '') || '导入风格'
    const firstParagraph = trimmed
      .split(/\n{2,}/)
      .map((item) => item.replace(/^#+\s*/, '').trim())
      .find((item) => item && item !== firstHeading)
    return {
      label,
      description: firstParagraph?.slice(0, 160) || '从上传文件解析的浏览器本地风格',
      category: '自定义',
      aliases: [],
      styleCase: '',
      styleSkill: trimmed
    }
  }
}

const decodeBase64ToBytes = (base64: string): Uint8Array => {
  const raw = atob(base64.replace(/^data:[^,]+,/, ''))
  const bytes = new Uint8Array(raw.length)
  for (let i = 0; i < raw.length; i += 1) bytes[i] = raw.charCodeAt(i)
  return bytes
}

const decodeXmlText = (value: string): string =>
  value
    .replace(/<[^>]+>/g, ' ')
    .replace(/&lt;/g, '<')
    .replace(/&gt;/g, '>')
    .replace(/&amp;/g, '&')
    .replace(/&quot;/g, '"')
    .replace(/&#39;/g, "'")
    .replace(/\s+/g, ' ')
    .trim()

const extractPptxSlides = async (
  base64: string
): Promise<Array<{ pageNumber: number; title: string; text: string }>> => {
  const { unzipSync, strFromU8 } = await import('fflate')
  const files = unzipSync(decodeBase64ToBytes(base64))
  const slideEntries = Object.keys(files)
    .filter((name) => /^ppt\/slides\/slide\d+\.xml$/i.test(name))
    .sort((a, b) => Number(a.match(/slide(\d+)\.xml/i)?.[1] || 0) - Number(b.match(/slide(\d+)\.xml/i)?.[1] || 0))
  const slides = slideEntries.map((name, index) => {
    const xml = strFromU8(files[name])
    const text = decodeXmlText(xml)
    const title = text.split(/[。.!?\n]/)[0]?.slice(0, 36) || `第 ${index + 1} 页`
    return { pageNumber: index + 1, title, text }
  })
  if (!slides.length) throw new Error('没有在 PPTX 中找到可解析的幻灯片。')
  return slides
}

const buildImportedSlideHtml = (title: string, text: string): string => {
  const safeTitle = title.replace(/[<>&"]/g, '')
  const lines = text
    .split(/(?<=[。.!?])\s+|\n+/)
    .map((line) => line.trim())
    .filter(Boolean)
    .slice(0, 6)
  const body = lines.map((line) => `<li>${line.replace(/[<>&"]/g, '')}</li>`).join('')
  return `<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"/><style>
html,body{margin:0;width:100%;height:100%;font-family:"Microsoft YaHei",system-ui;background:#f8fafc;color:#172033}
.slide{box-sizing:border-box;width:100vw;height:56.25vw;min-height:100vh;padding:7%;display:flex;flex-direction:column;gap:28px;background:linear-gradient(135deg,#f8fafc,#e8f8f3)}
h1{font-size:56px;line-height:1.1;margin:0;color:#12352b}ul{font-size:25px;line-height:1.65;margin:0;padding-left:1.4em;max-width:1180px}.tag{font-size:16px;color:#16865f;font-weight:700;letter-spacing:.12em;text-transform:uppercase}
</style></head><body><main class="slide"><div class="tag">PPTX IMPORT</div><h1>${safeTitle}</h1><ul>${body || `<li>${safeTitle}</li>`}</ul></main></body></html>`
}

const importBrowserPptx = async (payload: unknown): Promise<{ sessionId: string; pageCount: number; warnings: string[] }> => {
  const data = (payload || {}) as { pptxBase64?: string; title?: string; styleId?: string | null }
  if (!data.pptxBase64) throw new Error('浏览器模式需要 PPTX base64 数据。')
  const slides = await extractPptxSlides(data.pptxBase64)
  const timestamp = nowSeconds()
  const sessionId = uid('session')
  const title = data.title || '导入的 PPTX'
  const session: SessionRecord = {
    id: sessionId,
    title,
    topic: title,
    styleId: data.styleId || 'bauhaus',
    page_count: slides.length,
    generated_count: slides.length,
    status: 'completed',
    provider: FIXED_MODEL_CONFIG.provider,
    model: FIXED_MODEL_CONFIG.model,
    created_at: timestamp,
    updated_at: timestamp,
    metadata: JSON.stringify({ h5: true, source: 'pptx-import' })
  }
  const pages = slides.map((slide) => {
    const pageId = `page-${slide.pageNumber}`
    const html = buildImportedSlideHtml(slide.title, slide.text)
    return {
      id: pageId,
      pageNumber: slide.pageNumber,
      title: slide.title,
      contentOutline: slide.text.slice(0, 500),
      html,
      htmlPath: `h5://${sessionId}/${pageId}.html`,
      pageId,
      sourceUrl: htmlToDataUrl(html),
      status: 'completed',
      error: null
    }
  })
  writeSessions([session, ...readSessions()])
  writePages(sessionId, pages)
  return { sessionId, pageCount: pages.length, warnings: ['浏览器 H5 模式已导入 PPTX 文本与基础版式；复杂动画和母版不会完整还原。'] }
}

const browserTemplateStyleId = (templateId: string): string =>
  templateId.startsWith('builtin-style:') ? templateId.slice('builtin-style:'.length) : templateId

const listBrowserTemplates = async (): Promise<{ items: BrowserTemplateListItem[] }> => {
  const { items } = await listStyles()
  const stored = readStoredTemplates().map(({ pagesHtml: _pagesHtml, ...template }) => template)
  const templates = (items as Array<Record<string, unknown>>).map((style) => {
    const styleId = String(style.id || '')
    const styleKey = String(style.styleKey || styleId)
    const previewHtmlPath = stylePreviewUrl(styleKey)
    return {
      id: `builtin-style:${styleId}`,
      name: `${String(style.label || styleId)}模板`,
      description: String(style.description || ''),
      source: 'user' as const,
      pageCount: 1,
      tags: [String(style.category || '内置风格'), String(style.styleCase || '内置模板')].filter(Boolean),
      previewHtmlPath,
      previewPages: [
        {
          pageNumber: 1,
          pageId: 'preview',
          title: String(style.label || styleId),
          htmlPath: previewHtmlPath
        }
      ],
      createdAt: 0,
      updatedAt: 0
    }
  })
  return { items: [...stored, ...templates] }
}

const fetchStylePreviewHtml = async (styleId: string): Promise<string> => {
  const style = (await getStyleDetail(styleId)) as { styleKey?: string; label?: string }
  const styleKey = style.styleKey || styleId
  const res = await fetch(stylePreviewUrl(styleKey))
  if (res.ok) return await res.text()
  return `<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"/><title>${style.label || styleId}</title></head><body><main style="width:100vw;height:56.25vw;display:grid;place-items:center;font-family:system-ui;background:#fff;color:#111"><h1>${style.label || styleId}</h1></main></body></html>`
}

const createSessionFromBrowserTemplate = async (
  payload: unknown,
  editable: boolean
): Promise<{ success: true; sessionId: string }> => {
  const data = (payload || {}) as { templateId?: string; title?: string; pageCount?: number }
  const storedTemplate = readStoredTemplates().find((template) => template.id === data.templateId)
  if (storedTemplate) {
    const timestamp = nowSeconds()
    const sessionId = uid('session')
    const session: SessionRecord = {
      id: sessionId,
      title: data.title || storedTemplate.name,
      topic: data.title || storedTemplate.name,
      styleId: 'bauhaus',
      page_count: data.pageCount || storedTemplate.pageCount || storedTemplate.pagesHtml.length,
      generated_count: editable ? storedTemplate.pagesHtml.length : 0,
      status: editable ? 'completed' : 'active',
      provider: FIXED_MODEL_CONFIG.provider,
      model: FIXED_MODEL_CONFIG.model,
      created_at: timestamp,
      updated_at: timestamp,
      metadata: JSON.stringify({ h5: true, source: 'stored-template', templateId: storedTemplate.id })
    }
    writeSessions([session, ...readSessions()])
    if (editable) {
      writePages(
        sessionId,
        storedTemplate.pagesHtml.map((page) => ({
          id: page.pageId,
          pageNumber: page.pageNumber,
          title: page.title,
          contentOutline: page.title,
          html: page.html,
          htmlPath: `h5://${sessionId}/${page.pageId}.html`,
          pageId: page.pageId,
          sourceUrl: htmlToDataUrl(page.html),
          status: 'completed',
          error: null
        }))
      )
    }
    return { success: true, sessionId }
  }
  const styleId = browserTemplateStyleId(String(data.templateId || 'bauhaus'))
  const detail = (await getStyleDetail(styleId)) as { label?: string }
  const timestamp = nowSeconds()
  const session: SessionRecord = {
    id: uid('session'),
    title: data.title || detail.label || 'PPT Template',
    topic: data.title || detail.label || '',
    styleId,
    page_count: Math.max(1, Number(data.pageCount || 1) || 1),
    generated_count: editable ? 1 : 0,
    status: editable ? 'completed' : 'active',
    provider: FIXED_MODEL_CONFIG.provider,
    model: FIXED_MODEL_CONFIG.model,
    created_at: timestamp,
    updated_at: timestamp,
    metadata: JSON.stringify({ h5: true, source: 'builtin-style-template', templateId: data.templateId || styleId })
  }
  writeSessions([session, ...readSessions()])
  if (editable) {
    const html = await fetchStylePreviewHtml(styleId)
    writePages(session.id, [
      {
        id: 'page-1',
        pageNumber: 1,
        title: detail.label || session.title,
        contentOutline: detail.label || session.title,
        html,
        htmlPath: `h5://${session.id}/page-1.html`,
        pageId: 'page-1',
        sourceUrl: htmlToDataUrl(html),
        status: 'completed',
        error: null
      }
    ])
  }
  return { success: true, sessionId: session.id }
}

const importBrowserPptxTemplate = async (
  payload: unknown
): Promise<{ success: true; id: string; pageCount: number; warnings: string[] }> => {
  const data = (payload || {}) as { pptxBase64?: string; name?: string }
  if (!data.pptxBase64) throw new Error('浏览器模式需要 PPTX base64 数据。')
  const slides = await extractPptxSlides(data.pptxBase64)
  const timestamp = nowSeconds()
  const id = uid('template')
  const pagesHtml = slides.map((slide) => ({
    pageNumber: slide.pageNumber,
    pageId: `page-${slide.pageNumber}`,
    title: slide.title,
    html: buildImportedSlideHtml(slide.title, slide.text)
  }))
  const previewPages = pagesHtml.map((page) => ({
    pageNumber: page.pageNumber,
    pageId: page.pageId,
    title: page.title,
    htmlPath: htmlToDataUrl(page.html)
  }))
  const template: BrowserStoredTemplate = {
    id,
    name: data.name || '导入的 PPTX 模板',
    description: '浏览器 H5 模式从 PPTX 解析生成的基础模板',
    source: 'user',
    pageCount: pagesHtml.length,
    tags: ['PPTX', 'H5导入'],
    previewHtmlPath: previewPages[0]?.htmlPath || null,
    previewPages,
    pagesHtml,
    createdAt: timestamp,
    updatedAt: timestamp
  }
  writeStoredTemplates([template, ...readStoredTemplates()])
  return {
    success: true,
    id,
    pageCount: pagesHtml.length,
    warnings: ['浏览器 H5 模式已导入 PPTX 文本与基础版式；复杂动画、母版和图片不会完整还原。']
  }
}

const defaultBackendModel = (): ModelConfig => ({
  id: FIXED_MODEL_CONFIG.id,
  name: FIXED_MODEL_CONFIG.name,
  provider: 'anthropic',
  model: FIXED_MODEL_CONFIG.model,
  apiKey: FIXED_MODEL_CONFIG.apiKey,
  serverManaged: FIXED_MODEL_CONFIG.serverManaged,
  baseUrl: FIXED_MODEL_CONFIG.baseUrl,
  maxTokens: FIXED_MODEL_CONFIG.maxTokens,
  disableTemperature: FIXED_MODEL_CONFIG.disableTemperature,
  active: true,
  createdAt: 0,
  updatedAt: 0
})

const activeModel = (): ModelConfig => readModels().find((model) => model.active) || defaultBackendModel()

const resolveStyleForBackend = async (
  styleId: string | null | undefined
): Promise<Record<string, string>> => {
  if (!styleId) return {}
  try {
    const detail = (await getStyleDetail(styleId)) as {
      label?: string
      description?: string
      styleSkill?: string
    }
    return {
      styleName: detail.label || '',
      styleDescription: detail.description || '',
      styleSkill: detail.styleSkill || ''
    }
  } catch {
    return {}
  }
}

const readPreviewArgs = (
  htmlPathOrPayload: unknown,
  pageIdArg?: unknown
): { htmlPath: string; pageId: string; sessionId: string } => {
  if (
    htmlPathOrPayload &&
    typeof htmlPathOrPayload === 'object' &&
    !Array.isArray(htmlPathOrPayload)
  ) {
    const payload = htmlPathOrPayload as Record<string, unknown>
    return {
      htmlPath: String(payload.htmlPath || ''),
      pageId: String(payload.pageId || pageIdArg || ''),
      sessionId: String(payload.sessionId || '')
    }
  }
  return {
    htmlPath: String(htmlPathOrPayload || ''),
    pageId: String(pageIdArg || ''),
    sessionId: ''
  }
}

const startBackendGeneration = async (
  payload: Record<string, unknown>
): Promise<{ success: boolean; runId: string }> => {
  const sessionId = String(payload.sessionId || '')
  const session = readSessions().find((item) => item.id === sessionId)
  if (!session) throw new Error('Session not found.')

  const runId = uid('run')
  const timestamp = (): string => new Date().toISOString()
  const totalPages = Math.max(1, Number(session.page_count || 5) || 5)

  emit('generate:chunk', {
    type: 'stage_started',
    payload: {
      runId,
      sessionId,
      stage: 'planning',
      label: '正在连接 H5 生成服务',
      progress: 6,
      totalPages,
      timestamp: timestamp()
    }
  })

  activeGenerationControllers.get(sessionId)?.abort()
  const controller = new AbortController()
  activeGenerationControllers.set(sessionId, controller)
  const startedAt = Date.now()
  const heartbeat = (): void => {
    const elapsedSeconds = Math.max(1, Math.round((Date.now() - startedAt) / 1000))
    let stage = 'planning'
    let progress = Math.min(24, 8 + Math.floor(elapsedSeconds / 4))
    let label = `正在分析主题并规划 ${totalPages} 页内容（已等待 ${elapsedSeconds} 秒）`

    if (elapsedSeconds >= 30) {
      stage = 'rendering'
      progress = Math.min(58, 24 + Math.floor((elapsedSeconds - 30) / 4))
      label = `模型正在生成 ${totalPages} 页 H5 内容（已等待 ${elapsedSeconds} 秒）`
    }
    if (elapsedSeconds >= 120) {
      progress = Math.min(74, 58 + Math.floor((elapsedSeconds - 120) / 10))
      label = `正在完善版式与动画（已等待 ${elapsedSeconds} 秒）`
    }
    if (elapsedSeconds >= 240) {
      progress = Math.min(82, 74 + Math.floor((elapsedSeconds - 240) / 20))
      label = `模型仍在返回完整结果，请稍候（已等待 ${elapsedSeconds} 秒）`
    }

    emit('generate:chunk', {
      type: 'stage_progress',
      payload: {
        runId,
        sessionId,
        stage,
        label,
        progress,
        totalPages,
        timestamp: timestamp()
      }
    })
  }
  const heartbeatTimer = window.setInterval(heartbeat, 5000)

  let response: Response
  try {
    const stylePayload = await resolveStyleForBackend(session.styleId)
    const authToken = window.localStorage.getItem('authToken')?.trim() || ''
    const headers: Record<string, string> = { 'content-type': 'application/json' }
    if (authToken) headers.authorization = `Bearer ${authToken}`
    heartbeat()
    response = await fetch(apiUrl('/generate'), {
      method: 'POST',
      headers,
      body: JSON.stringify({
        sessionId,
        topic: session.topic || session.title,
        pageCount: totalPages,
        userMessage: String(payload.userMessage || ''),
        ...stylePayload
      }),
      signal: controller.signal
    })
  } catch (error) {
    const message = controller.signal.aborted
      ? '生成已取消'
      : error instanceof Error
        ? error.message
        : '连接 H5 生成服务失败'
    emit('generate:chunk', {
      type: 'run_error',
      payload: {
        runId,
        sessionId,
        message,
        failedPageCount: totalPages,
        timestamp: timestamp()
      }
    })
    throw new Error(message)
  } finally {
    window.clearInterval(heartbeatTimer)
    if (activeGenerationControllers.get(sessionId) === controller) {
      activeGenerationControllers.delete(sessionId)
    }
  }

  if (!response.ok) {
    const responseBody = await response.text()
    const message =
      response.status === 504
        ? 'PPT 生成网关超时（HTTP 504），请重试；服务端不会把超时结果标记为成功。'
        : responseBody || `PPT 生成服务请求失败（HTTP ${response.status}）`
    emit('generate:chunk', {
      type: 'run_error',
      payload: {
        runId,
        sessionId,
        message,
        failedPageCount: totalPages,
        timestamp: timestamp()
      }
    })
    throw new Error(message)
  }

  emit('generate:chunk', {
    type: 'stage_progress',
    payload: {
      runId,
      sessionId,
      stage: 'validation',
      label: '模型返回完成，正在解析并校验页面',
      progress: 84,
      totalPages,
      timestamp: timestamp()
    }
  })

  const result = (await response.json()) as {
    title?: string
    pages?: Array<{
      pageNumber: number
      title: string
      contentOutline?: string
      html: string
    }>
  }

  const pages = (result.pages || []).map((page, index) => {
    const pageNumber = Number(page.pageNumber || index + 1)
    const pageId = `page-${pageNumber}`
    const htmlPath = `h5://${sessionId}/${pageId}.html`
    const html = String(page.html || '')
    const record: GeneratedPageRecord = {
      id: pageId,
      pageNumber,
      title: String(page.title || `Page ${pageNumber}`),
      contentOutline: page.contentOutline || '',
      html,
      htmlPath,
      pageId,
      sourceUrl: htmlToDataUrl(html),
      status: 'completed',
      error: null
    }
    emit('generate:chunk', {
      type: 'page_generated',
      payload: {
        runId,
        sessionId,
        stage: 'rendering',
        label: '页面已生成',
        progress: Math.min(96, 84 + Math.round((pageNumber / totalPages) * 12)),
        currentPage: pageNumber,
        totalPages,
        completedPageCount: pageNumber,
        timestamp: timestamp(),
        pageNumber,
        id: record.id,
        title: record.title,
        contentOutline: record.contentOutline,
        html: record.html,
        htmlPath: record.htmlPath,
        pageId: record.pageId,
        sourceUrl: record.sourceUrl
      }
    })
    return record
  })

  writePages(sessionId, pages)
  writeSessions(
    readSessions().map((item) =>
      item.id === sessionId
        ? {
            ...item,
            title: result.title || item.title,
            status: 'completed',
            generated_count: pages.length,
            page_count: totalPages,
            updated_at: nowSeconds(),
            metadata: JSON.stringify({
              ...(item.metadata ? readJsonFromString(item.metadata) : {}),
              generatedCount: pages.length,
              failedCount: 0,
              h5Backend: true
            })
          }
        : item
    )
  )

  emit('generate:chunk', {
    type: 'run_completed',
    payload: {
      runId,
      sessionId,
      totalPages,
      completedPageCount: pages.length,
      failedPageCount: 0,
      timestamp: timestamp()
    }
  })

  return { success: true, runId }
}

const notImplemented = (feature: string): never => {
  throw new Error(`${feature} still needs a backend implementation.`)
}

const safeFileName = (value: string, fallback: string): string =>
  (value || fallback).replace(/[\\/:*?"<>|]/g, '_').slice(0, 120) || fallback

const downloadBlob = (blob: Blob, fileName: string): string => {
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = fileName
  document.body.appendChild(link)
  link.click()
  link.remove()
  window.setTimeout(() => URL.revokeObjectURL(url), 60_000)
  return url
}

const sessionTitle = (sessionId: string): string =>
  readSessions().find((session) => session.id === sessionId)?.title || 'OhMyPPT'

const collectExportPages = (sessionId: string, pageId?: string): GeneratedPageRecord[] => {
  const pages = readPages(sessionId)
    .filter((page) => page.html)
    .sort((a, b) => a.pageNumber - b.pageNumber)
  if (!pageId) return pages
  return pages.filter((page) => page.id === pageId || page.pageId === pageId)
}

const buildDeckPrintHtml = (title: string, pages: GeneratedPageRecord[]): string => {
  const frames = pages
    .map((page) => {
      const src = htmlToDataUrl(page.html)
      return `<section class="print-slide"><iframe src="${src}" title="${safeFileName(page.title, `P${page.pageNumber}`)}"></iframe></section>`
    })
    .join('\n')
  return `<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8"/>
<title>${safeFileName(title, 'OhMyPPT')}</title>
<style>
html,body{margin:0;background:#111827}
.print-slide{width:100vw;height:56.25vw;max-height:100vh;page-break-after:always;break-after:page;background:white;overflow:hidden}
.print-slide iframe{width:1600px;height:900px;border:0;transform-origin:top left;transform:scale(calc(100vw / 1600))}
@page{size:16in 9in;margin:0}
@media print{html,body{background:white}.print-slide{width:16in;height:9in}.print-slide iframe{width:1600px;height:900px;transform:scale(0.96)}}
</style>
</head>
<body>${frames}</body>
</html>`
}

const exportBrowserPdf = async (payload: unknown): Promise<Record<string, unknown>> => {
  const data = (payload || {}) as { sessionId?: string }
  const sessionId = data.sessionId || ''
  if (!sessionId) throw new Error('No session ID provided')
  const pages = collectExportPages(sessionId)
  if (!pages.length) throw new Error('No pages found for this session')
  const title = sessionTitle(sessionId)
  const printWindow = window.open('', '_blank', 'noopener,noreferrer')
  if (!printWindow) throw new Error('Please allow pop-ups to export PDF.')
  printWindow.document.open()
  printWindow.document.write(buildDeckPrintHtml(title, pages))
  printWindow.document.close()
  window.setTimeout(() => {
    try {
      printWindow.focus()
      printWindow.print()
    } catch {
      // The print window is already open for manual Save as PDF.
    }
  }, 800)
  return {
    success: true,
    cancelled: false,
    path: `${safeFileName(title, 'OhMyPPT')}.pdf`,
    pageCount: pages.length,
    warnings: ['浏览器打印窗口已打开，请选择“另存为 PDF”。']
  }
}

const exportBrowserPng = async (payload: unknown): Promise<Record<string, unknown>> => {
  const data = (payload || {}) as { sessionId?: string; pageId?: string }
  const sessionId = data.sessionId || ''
  if (!sessionId) throw new Error('No session ID provided')
  const pages = collectExportPages(sessionId, data.pageId)
  if (!pages.length) throw new Error('No pages found for this session')
  const { zipSync, strToU8 } = await import('fflate')
  const { renderHtmlToPng } = await import('@renderer/lib/browser-pptx-export')
  const files: Record<string, Uint8Array> = {
    'README.txt': strToU8('PNG slides exported by the browser-only OhMyPPT H5 runtime.')
  }
  for (const page of pages) {
    const dataUrl = await renderHtmlToPng(page.html)
    const raw = atob(dataUrl.replace(/^data:image\/png;base64,/, ''))
    const bytes = new Uint8Array(raw.length)
    for (let i = 0; i < raw.length; i += 1) bytes[i] = raw.charCodeAt(i)
    files[`P${String(page.pageNumber).padStart(2, '0')}_${safeFileName(page.title, 'slide')}.png`] = bytes
  }
  const title = sessionTitle(sessionId)
  const fileName = `${safeFileName(title, 'OhMyPPT')}-png.zip`
  downloadBlob(new Blob([zipSync(files, { level: 6 })], { type: 'application/zip' }), fileName)
  return { success: true, cancelled: false, path: fileName, pageCount: pages.length, warnings: [] }
}

const exportBrowserSlidePack = async (payload: unknown): Promise<Record<string, unknown>> => {
  const data = (payload || {}) as { sessionId?: string }
  const sessionId = data.sessionId || ''
  if (!sessionId) throw new Error('No session ID provided')
  const pages = collectExportPages(sessionId)
  if (!pages.length) throw new Error('No pages found for this session')
  const { zipSync, strToU8 } = await import('fflate')
  const title = sessionTitle(sessionId)
  const files: Record<string, Uint8Array> = {
    'index.html': strToU8(buildDeckPrintHtml(title, pages))
  }
  for (const page of pages) {
    files[`pages/P${String(page.pageNumber).padStart(2, '0')}.html`] = strToU8(page.html)
  }
  const fileName = `${safeFileName(title, 'OhMyPPT')}-slide-pack.zip`
  downloadBlob(new Blob([zipSync(files, { level: 6 })], { type: 'application/zip' }), fileName)
  return { success: true, cancelled: false, path: fileName, pageCount: pages.length, warnings: [] }
}

const exportBrowserSessionZip = async (payload: unknown): Promise<Record<string, unknown>> => {
  const data = (payload || {}) as { sessionId?: string }
  const sessionId = data.sessionId || ''
  if (!sessionId) throw new Error('No session ID provided')
  const session = readSessions().find((item) => item.id === sessionId)
  const pages = collectExportPages(sessionId)
  if (!session || !pages.length) throw new Error('No pages found for this session')
  const { zipSync, strToU8 } = await import('fflate')
  const files: Record<string, Uint8Array> = {
    'session.json': strToU8(JSON.stringify({ session, pages }, null, 2)),
    'outlines.md': strToU8(buildOutlinesMarkdown(sessionId, pages))
  }
  for (const page of pages) {
    files[`pages/P${String(page.pageNumber).padStart(2, '0')}.html`] = strToU8(page.html)
  }
  const fileName = `${safeFileName(session.title, 'OhMyPPT')}-session.zip`
  downloadBlob(new Blob([zipSync(files, { level: 6 })], { type: 'application/zip' }), fileName)
  return { success: true, cancelled: false, path: fileName, pageCount: pages.length, warnings: [] }
}

const buildOutlinesMarkdown = (sessionId: string, pages = collectExportPages(sessionId)): string => {
  const title = sessionTitle(sessionId)
  return [
    `# ${title}`,
    '',
    ...pages.flatMap((page) => [
      `## P${page.pageNumber} ${page.title}`,
      '',
      page.contentOutline || page.title,
      ''
    ])
  ].join('\n')
}

const exportBrowserOutlines = async (payload: unknown): Promise<Record<string, unknown>> => {
  const data = (payload || {}) as { sessionId?: string }
  const sessionId = data.sessionId || ''
  if (!sessionId) throw new Error('No session ID provided')
  const markdown = buildOutlinesMarkdown(sessionId)
  const fileName = `${safeFileName(sessionTitle(sessionId), 'OhMyPPT')}-outlines.md`
  downloadBlob(new Blob([markdown], { type: 'text/markdown;charset=utf-8' }), fileName)
  return { success: true, cancelled: false, path: fileName, pageCount: collectExportPages(sessionId).length }
}

const handlers: Record<string, (...args: unknown[]) => unknown | Promise<unknown>> = {
  'app:getVersion': () => ({ version: '2.0.15-h5' }),
  'settings:get': () => getSettings(),
  'settings:save': (settings) => saveSettings((settings as Record<string, unknown>) || {}),
  'settings:listModelConfigs': () => readModels(),
  'settings:chooseStoragePath': () => ({ path: 'browser-local-storage' }),
  'settings:validateUploadPrerequisites': () => {
    const model = FIXED_MODEL_CONFIG
    const ready = Boolean(model?.model)
    return {
      ready,
      missing: ready ? [] : ['activeModel', 'model'],
      message: ready ? undefined : 'Please add and activate a model config in H5 Settings.'
    }
  },
  'settings:upsertModelConfig': (payload) => {
    void payload
    writeModels([FIXED_MODEL_CONFIG])
    return { success: true, id: FIXED_MODEL_CONFIG.id }
  },
  'settings:setActiveModelConfig': (id) => {
    void id
    writeModels([FIXED_MODEL_CONFIG])
    return { success: true }
  },
  'settings:deleteModelConfig': (id) => {
    void id
    writeModels([FIXED_MODEL_CONFIG])
    return { success: true }
  },
  'settings:verifyApiKey': () => ({
    valid: true,
    message: 'H5 config saved. Real connectivity is handled by the Python backend.'
  }),
  'imageModels:list': () => readImageModels(),
  'imageModels:upsert': (payload) => {
    const data = payload as Partial<ImageModelConfig>
    const models = readImageModels()
    const timestamp = nowSeconds()
    const id = data.id || uid('image_model')
    const next: ImageModelConfig = {
      id,
      name: data.name || '豆包 Seedream 4.5',
      provider: data.provider || 'openaiCompatible',
      modelConfig: data.modelConfig || '{}',
      active: Boolean(data.active || models.length === 0),
      createdAt: models.find((model) => model.id === id)?.createdAt || timestamp,
      updatedAt: timestamp
    }
    const merged = models.filter((model) => model.id !== id).map((model) => ({
      ...model,
      active: next.active ? false : model.active
    }))
    writeImageModels([...merged, next])
    return { success: true, id }
  },
  'imageModels:setActive': (id) => {
    writeImageModels(readImageModels().map((model) => ({ ...model, active: model.id === id })))
    return { success: true }
  },
  'imageModels:delete': (id) => {
    writeImageModels(readImageModels().filter((model) => model.id !== id))
    return { success: true }
  },
  'imageModels:verify': () => ({ valid: true, message: 'H5 local config is valid.' }),
  'session:list': () => readSessions().sort((a, b) => b.updated_at - a.updated_at),
  'session:create': (payload) => {
    const data = payload as {
      sessionId?: string
      topic?: string
      styleId?: string
      pageCount?: number
    }
    const model = activeModel()
    const timestamp = nowSeconds()
    const sessionId = String(data.sessionId || '').trim() || uid('session')
    const session: SessionRecord = {
      id: sessionId,
      title: `PPT: ${data.topic || 'Untitled'}`,
      topic: data.topic || '',
      styleId: data.styleId || '',
      page_count: Number(data.pageCount || 0),
      generated_count: 0,
      status: 'active',
      provider: model?.provider || 'anthropic',
      model: model?.model || '',
      created_at: timestamp,
      updated_at: timestamp,
      metadata: JSON.stringify({ h5: true, externalSessionId: Boolean(data.sessionId) })
    }
    writeSessions([session, ...readSessions().filter((item) => item.id !== session.id)])
    return { sessionId: session.id }
  },
  'session:get': (sessionId) => ({
    session: readSessions().find((session) => session.id === sessionId) || null,
    messages: [],
    generatedPages: readPages(String(sessionId))
  }),
  'session:getMessages': () => [],
  'session:migratePageOutlinesToSourceSkeletons': () => ({
    migrated: false,
    migratedCount: 0,
    existingCount: 0
  }),
  'session:delete': (sessionId) => {
    writeSessions(readSessions().filter((session) => session.id !== sessionId))
    return { success: true }
  },
  'session:updateTitle': (payload) => {
    const data = payload as { sessionId: string; title: string }
    writeSessions(readSessions().map((session) =>
      session.id === data.sessionId ? { ...session, title: data.title, updated_at: nowSeconds() } : session
    ))
    return { ok: true }
  },
  'styles:list': () => listStyles(),
  'styles:get': () => getStyles(),
  'styles:getDetail': (styleId) => getStyleDetail(String(styleId)),
  'styles:parseFile': (payload) => {
    const data = (payload || {}) as { content?: string; fileName?: string }
    return parseBrowserStyleText(String(data.content || ''), data.fileName)
  },
  'styles:parsePptx': async (payload) => {
    const data = (payload || {}) as { pptxBase64?: string; fileName?: string }
    if (!data.pptxBase64) throw new Error('浏览器模式需要 PPTX base64 数据。')
    const slides = await extractPptxSlides(data.pptxBase64)
    const content = slides.map((slide) => `## ${slide.title}\n${slide.text}`).join('\n\n')
    return parseBrowserStyleText(
      `# ${data.fileName?.replace(/\.pptx$/i, '') || 'PPTX 导入风格'}\n\n${content}`,
      data.fileName
    )
  },
  'styles:parseImage': (payload) => {
    const data = (payload || {}) as { mimeType?: string }
    return {
      label: '图片提取风格',
      description: `从 ${data.mimeType || 'image'} 图片导入的浏览器本地风格`,
      category: '自定义',
      aliases: ['image', '图片风格'],
      styleCase: '图片参考、视觉复刻、素材风格提取',
      styleSkill:
        '根据上传图片的整体观感建立风格：保留图片中的主色调、明暗关系、版式密度、图形语言和情绪表达。生成 PPT 时优先复刻图片的视觉氛围，保持配色克制、层级清晰、元素间距与图片参考一致。'
    }
  },
  'styles:create': (payload) => createOrUpdateBrowserStyle(payload),
  'styles:update': (payload) => {
    const data = (payload || {}) as { id?: string }
    return createOrUpdateBrowserStyle(payload, String(data.id || ''))
  },
  'styles:delete': (styleId) => {
    const id = String(styleId || '')
    const before = readCustomStyles()
    writeCustomStyles(before.filter((style) => style.id !== id))
    return { success: true, deleted: before.some((style) => style.id === id) }
  },
  'fonts:list': () => ({ googleFonts: [], userFonts: [] }),
  'fonts:previewCss': () => '',
  'templates:list': () => listBrowserTemplates(),
  'templates:createSession': (payload) => createSessionFromBrowserTemplate(payload, false),
  'templates:createEditableSession': (payload) => createSessionFromBrowserTemplate(payload, true),
  'templates:createFromSession': () => notImplemented('Save as template'),
  'templates:importPptx': (payload) => importBrowserPptxTemplate(payload),
  'templates:updateMetadata': async (payload) => {
    const data = (payload || {}) as { templateId?: string }
    const items = (await listBrowserTemplates()).items
    const item = items.find((template) => template.id === data.templateId) || items[0]
    return { success: true, item }
  },
  'templates:delete': (templateId) => {
    const id = String(templateId || '')
    const before = readStoredTemplates()
    writeStoredTemplates(before.filter((template) => template.id !== id))
    return { success: true, deleted: before.some((template) => template.id === id) }
  },
  'generate:state': (sessionId) => ({
    sessionId,
    runId: null,
    status: 'idle',
    hasActiveRun: false,
    progress: 0,
    totalPages: 0,
    events: [],
    error: null,
    startedAt: null,
    updatedAt: null
  }),
  'generate:listActive': () => [],
  'generate:start': (payload) => startBackendGeneration((payload || {}) as Record<string, unknown>),
  'generate:startTemplate': (payload) =>
    startBackendGeneration((payload || {}) as Record<string, unknown>),
  'generate:cancel': (sessionId) => {
    const controller = activeGenerationControllers.get(String(sessionId || ''))
    if (!controller) return { success: true, cancelled: false }
    controller.abort()
    return { success: true, cancelled: true }
  },
  'generate:addPage': () => notImplemented('Add page generation'),
  'generate:retryFailedPages': () => notImplemented('Retry failed pages'),
  'generate:retrySinglePage': () => notImplemented('Retry single page'),
  'documents:prepareReference': () => notImplemented('Document parsing'),
  'documents:parseImageReference': () => notImplemented('Image reference parsing'),
  'documents:parsePlan': () => notImplemented('Document outline parsing'),
  'pptx:import': (payload) => importBrowserPptx(payload),
  'export:pdf': (payload) => exportBrowserPdf(payload),
  'export:png': (payload) => exportBrowserPng(payload),
  'export:pptx': async (payload) => {
    const data = payload as { sessionId?: string; pageId?: string; imageOnly?: boolean } | undefined
    const sessionId = data?.sessionId || ''
    if (!sessionId) throw new Error('No session ID provided')
    if (fullIpcAvailable !== false) {
      try {
        const result = await invokeFullIpc('web:exportPptx', [payload])
        if (
          result &&
          typeof result === 'object' &&
          typeof (result as { downloadUrl?: unknown }).downloadUrl === 'string' &&
          (result as { downloadUrl: string }).downloadUrl.startsWith('/')
        ) {
          return {
            ...(result as Record<string, unknown>),
            downloadUrl: `${FULL_IPC_BASE}${(result as { downloadUrl: string }).downloadUrl}`
          }
        }
        return result
      } catch (error) {
        if (fullIpcAvailable === true) throw error
      }
    }
    // Try to get pages from the full IPC backend first (database), fall back to localStorage
    let pages: GeneratedPageRecord[] = readPages(sessionId)
    let title = readSessions().find((s) => s.id === sessionId)?.title || 'Presentation'
    if (!pages.length && fullIpcAvailable !== false) {
      try {
        const result = (await invokeFullIpc('session:get', [sessionId])) as {
          session?: { title?: string } | null
          generatedPages?: Array<{ pageNumber: number; title: string; html: string; htmlPath?: string }>
        } | undefined
        if (result?.generatedPages?.length) {
          pages = result.generatedPages.map((p) => ({
            id: `page-${p.pageNumber}`,
            pageNumber: p.pageNumber,
            title: p.title,
            html: p.html,
            htmlPath: p.htmlPath || '',
            pageId: `page-${p.pageNumber}`,
            sourceUrl: '',
            status: 'completed'
          }))
          if (result.session?.title) title = result.session.title
        }
      } catch {
        // Fall back to localStorage pages
      }
    }
    if (!pages.length) throw new Error('No pages found for this session')
    const { exportToPptx } = await import('@renderer/lib/browser-pptx-export')
    const targetPageId = data?.pageId
    let exportPages = pages
      .filter((p) => p.html)
      .sort((a, b) => a.pageNumber - b.pageNumber)
      .map((p) => {
        const rawPath = (p.htmlPath || '').replace(/\\/g, '/')
        const isH5 = /^h5:\/\//i.test(rawPath)
        let htmlUrl = ''
        if (rawPath && !isH5) {
          // Real filesystem path → /api/local-file/ URL (same as PreviewIframe.toFileUrl)
          const base = FULL_IPC_BASE || ''
          const encodedPath = rawPath.split('/').map(encodeURIComponent).join('/')
          htmlUrl = `${base}/api/local-file/${encodedPath}`
        } else if (p.sourceUrl) {
          htmlUrl = p.sourceUrl
        }
        return { pageNumber: p.pageNumber, title: p.title, html: p.html, htmlUrl }
      })
    if (targetPageId) {
      exportPages = exportPages.filter((p) => {
        const pid = `page-${p.pageNumber}`
        return pid === targetPageId
      })
    }
    if (!exportPages.length) throw new Error('No exportable pages found')
    // Build a browser Blob URL; the React export action owns the single download click.
    const downloadUrl = await exportToPptx(exportPages, title)
    // Return a result shape the caller understands
    return {
      success: true,
      path: `${title || 'presentation'}.pptx`,
      downloadUrl,
      cancelled: false,
      pageCount: exportPages.length
    }
  },
  'export:slidePack': (payload) => exportBrowserSlidePack(payload),
  'export:sessionZip': (payload) => exportBrowserSessionZip(payload),
  'export:outlinesMarkdown': (payload) => exportBrowserOutlines(payload),
  'preview:load': (htmlPath) => {
    const { htmlPath: target, sessionId } = readPreviewArgs(htmlPath)
    const sessions = sessionId
      ? readSessions().filter((session) => session.id === sessionId)
      : readSessions()
    for (const session of sessions) {
      const page = readPages(session.id).find((item) => item.htmlPath === target)
      if (page) return page.html
    }
    return ''
  },
  'preview:loadPage': (htmlPath, pageId) => {
    const { htmlPath: targetPath, pageId: targetPageId, sessionId } = readPreviewArgs(
      htmlPath,
      pageId
    )
    const sessions = sessionId
      ? readSessions().filter((session) => session.id === sessionId)
      : readSessions()
    for (const session of sessions) {
      const page = readPages(session.id).find(
        (item) => item.htmlPath === targetPath || item.pageId === targetPageId
      )
      if (page) {
        return {
          pageNumber: page.pageNumber,
          pageId: page.pageId,
          title: page.title,
          html: page.html
        }
      }
    }
    return { pageNumber: 1, pageId, title: '', html: '' }
  },
  'file:open': () => '',
  'file:save': () => ({ success: true }),
  'file:reveal': () => ({ success: true }),
  'file:openInBrowser': () => ({ success: true }),
  'thinking:createWorkspace': () => notImplemented('Thinking workspace'),
  'thinking:getLatestWorkspace': () => null,
  'thinking:listWorkspaces': () => [],
  'images:getState': () => null,
  'images:listHistory': () => [],
  'images:cancel': () => ({ success: true }),
  'images:generate': () => notImplemented('Image generation'),
  'images:generatePrompt': () => notImplemented('Image prompt generation')
}

// The integrated app should use the full Oh My PPT IPC backend whenever it is running.
// Local handlers remain as a fallback for pure static preview mode.
const LOCAL_ONLY_CHANNELS = new Set<string>()

const ipcRenderer = {
  invoke: async (channel: string, ...args: unknown[]): Promise<unknown> => {
    // Always use local handler for channels that are implemented in the browser shim
    if (!LOCAL_ONLY_CHANNELS.has(channel)) {
      if (fullIpcAvailable !== false) {
        try {
          return await invokeFullIpc(channel, args)
        } catch (error) {
          if (fullIpcAvailable === true) throw error
        }
      }
    }

    const handler = handlers[channel]
    if (!handler) {
      console.warn(`[h5-ipc] unimplemented channel: ${channel}`, args)
      return null
    }
    return handler(...args)
  },
  on: (channel: string, listener: Listener): void => {
    const set = listeners.get(channel) || new Set<Listener>()
    set.add(listener)
    listeners.set(channel, set)
  },
  removeListener: (channel: string, listener: Listener): void => {
    listeners.get(channel)?.delete(listener)
  }
}

if (!window.electron) {
  setupFullIpcEvents()
  window.electron = {
    ipcRenderer,
    process: {
      platform: 'browser',
      env: {
        NODE_ENV: import.meta.env.MODE
      }
    },
    getPathForFile: () => ''
  } as Window['electron']
}
