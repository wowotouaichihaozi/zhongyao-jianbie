import { app, BrowserWindow, ipcMain, type IpcMainInvokeEvent } from 'electron'
import { createServer, type IncomingMessage, type ServerResponse } from 'node:http'
import { createReadStream, existsSync, mkdirSync, statSync } from 'node:fs'
import fs from 'node:fs'
import os from 'node:os'
import path, { extname, join, normalize } from 'node:path'
import { URL } from 'node:url'
import { electronApp, is } from '@electron-toolkit/utils'
import log from 'electron-log/main.js'
import { PPTDatabase } from '../main/db/database'
import { AgentManager } from '../main/agent'
import { setupIPC, registerLocalAssetProtocol } from '../main/ipc'
import { setStyleDb } from '../main/utils/style-skills'
import { applyProxy } from '../main/utils/proxy'
import { writeHtmlToPptx, type HtmlToPptxSlide } from '../main/utils/html-pptx'
import { captureHtmlPageToPptxImageSlide } from '../main/utils/html-pptx/renderer'
import {
  initializeSkills,
  resolveBuiltinSkillsSourcePath,
  resolveInstalledSkillsPath,
  setSkillsRuntime
} from '../main/skills'

type IpcHandler = (event: IpcMainInvokeEvent, ...args: unknown[]) => Promise<unknown> | unknown
type EventClient = {
  id: number
  response: ServerResponse
}

const PORT = Number(process.env.PPT_WEB_BACKEND_PORT || 8765)
const handlers = new Map<string, IpcHandler>()
const eventClients = new Map<number, EventClient>()
let nextClientId = 1
let db: PPTDatabase | null = null

const DEFAULT_MODEL_CONFIG = {
  id: 'spark-x2-agent-default',
  name: 'Spark X2 Agent',
  provider: 'anthropic',
  model: process.env.ANTHROPIC_MODEL || 'xsparkx2agent',
  apiKey: process.env.ANTHROPIC_AUTH_TOKEN || '',
  baseUrl: process.env.ANTHROPIC_BASE_URL || 'https://maas-coding-api.cn-huabei-1.xf-yun.com/anthropic',
  maxTokens: 8192,
  disableTemperature: false,
  active: true
} as const

const EXPORT_PAGE_READY_TIMEOUT_MS = 4000
const EXPORT_CAPTURE_SETTLE_MS = 120
const PRINT_READY_PREFIX = '__PPT_PRINT_READY__'

delete process.env.ELECTRON_RUN_AS_NODE
process.env.OHMYPPT_WEB_BACKEND = '1'

function configureLogging(): void {
  log.transports.file.level = 'info'
  log.transports.file.maxSize = 20 * 1024 * 1024
  const logDir = join(process.cwd(), 'logs')
  mkdirSync(logDir, { recursive: true })
  log.transports.file.resolvePathFn = () => join(logDir, 'web-backend.log')
  log.initialize()
  log.info('[web-backend] logger initialized', {
    env: is.dev ? 'dev' : 'prod',
    version: app.getVersion(),
    file: log.transports.file.getFile().path
  })
}

function sendJson(response: ServerResponse, status: number, body: unknown): void {
  response.writeHead(status, {
    'content-type': 'application/json; charset=utf-8',
    'access-control-allow-origin': '*',
    'access-control-allow-methods': 'GET,POST,OPTIONS',
    'access-control-allow-headers': 'content-type'
  })
  response.end(JSON.stringify(body))
}

function contentTypeFor(filePath: string): string {
  switch (extname(filePath).toLowerCase()) {
    case '.html':
    case '.htm':
      return 'text/html; charset=utf-8'
    case '.css':
      return 'text/css; charset=utf-8'
    case '.js':
    case '.mjs':
      return 'text/javascript; charset=utf-8'
    case '.json':
      return 'application/json; charset=utf-8'
    case '.png':
      return 'image/png'
    case '.jpg':
    case '.jpeg':
      return 'image/jpeg'
    case '.gif':
      return 'image/gif'
    case '.svg':
      return 'image/svg+xml'
    case '.webp':
      return 'image/webp'
    case '.woff2':
      return 'font/woff2'
    case '.woff':
      return 'font/woff'
    case '.ttf':
      return 'font/ttf'
    case '.mp4':
      return 'video/mp4'
    case '.pptx':
      return 'application/vnd.openxmlformats-officedocument.presentationml.presentation'
    default:
      return 'application/octet-stream'
  }
}

function serveLocalFile(requestUrl: URL, response: ServerResponse): void {
  const prefix = '/api/local-file/'
  const rawPath = decodeURIComponent(requestUrl.pathname.slice(prefix.length))
  const filePath = normalize(rawPath)

  if (!filePath || !existsSync(filePath)) {
    sendJson(response, 404, { ok: false, error: 'Local file not found' })
    return
  }

  const stat = statSync(filePath)
  if (!stat.isFile()) {
    sendJson(response, 400, { ok: false, error: 'Local path is not a file' })
    return
  }

  response.writeHead(200, {
    'content-type': contentTypeFor(filePath),
    'content-length': stat.size,
    'content-disposition': `inline; filename="${encodeURIComponent(filePath.split(/[\\/]/).pop() || 'download')}"`,
    'access-control-allow-origin': '*',
    'cache-control': 'no-cache'
  })
  createReadStream(filePath).pipe(response)
}

function readBody(request: IncomingMessage): Promise<unknown> {
  return new Promise((resolve, reject) => {
    const chunks: Buffer[] = []
    request.on('data', (chunk) => chunks.push(Buffer.from(chunk)))
    request.on('end', () => {
      const text = Buffer.concat(chunks).toString('utf-8')
      if (!text.trim()) {
        resolve({})
        return
      }
      try {
        resolve(JSON.parse(text))
      } catch (error) {
        reject(error)
      }
    })
    request.on('error', reject)
  })
}

function broadcast(channel: string, payload: unknown): void {
  const message = `event: ipc\ndata: ${JSON.stringify({ channel, payload })}\n\n`
  for (const client of eventClients.values()) {
    client.response.write(message)
  }
}

async function invokeRegisteredHandler(
  win: BrowserWindow,
  channel: string,
  ...args: unknown[]
): Promise<unknown> {
  const handler = handlers.get(channel)
  if (!handler) throw new Error(`IPC handler is not registered: ${channel}`)
  return handler({ sender: win.webContents } as IpcMainInvokeEvent, ...args)
}

async function ensureDefaultWebSettings(win: BrowserWindow): Promise<void> {
  const storagePath = join(process.cwd(), 'data', 'ppt-workspace')
  mkdirSync(storagePath, { recursive: true })

  await invokeRegisteredHandler(win, 'settings:save', {
    locale: 'zh',
    storagePath
  })
  await invokeRegisteredHandler(win, 'settings:upsertModelConfig', DEFAULT_MODEL_CONFIG)

  log.info('[web-backend] default web settings are ready', {
    storagePath,
    model: DEFAULT_MODEL_CONFIG.model,
    baseUrl: DEFAULT_MODEL_CONFIG.baseUrl
  })
}

const sanitizeExportBaseName = (value: string, fallback: string): string =>
  value.replace(/[\\/:*?"<>|]/g, '_').slice(0, 120) || fallback

const buildLocalFileDownloadUrl = (filePath: string): string => {
  const normalized = filePath.replace(/\\/g, '/')
  return `/api/local-file/${normalized.split('/').map(encodeURIComponent).join('/')}`
}

const resolvePageHtmlPath = (
  projectDir: string,
  fileSlug: string,
  htmlPath: string | null | undefined
): string => {
  const candidates = [
    htmlPath && path.isAbsolute(htmlPath) ? htmlPath : '',
    htmlPath ? path.join(projectDir, htmlPath) : '',
    path.join(projectDir, `${fileSlug}.html`),
    path.join(projectDir, 'pages', `${fileSlug}.html`)
  ].filter(Boolean)

  const found = candidates.find((candidate) => existsSync(candidate))
  return found || candidates[candidates.length - 1] || path.join(projectDir, `${fileSlug}.html`)
}

const waitForPrintReadySignal = async (args: {
  win: BrowserWindow
  pageId: string
  timeoutMs: number
}): Promise<{ timedOut: boolean; reportedPageId?: string }> => {
  const { win, pageId, timeoutMs } = args
  return new Promise((resolve) => {
    let done = false
    let timeoutRef: NodeJS.Timeout | null = null

    const finalize = (timedOut: boolean, reportedPageId?: string): void => {
      if (done) return
      done = true
      if (timeoutRef) clearTimeout(timeoutRef)
      win.webContents.removeListener('console-message', onConsoleMessage)
      win.removeListener('closed', onClosed)
      resolve({ timedOut, reportedPageId })
    }

    const resolveConsoleMessageText = (...rawArgs: unknown[]): string => {
      if (rawArgs.length >= 3 && typeof rawArgs[2] === 'string') return rawArgs[2]
      const firstArg = rawArgs[0] as
        | { message?: unknown; params?: { message?: unknown } }
        | undefined
      if (firstArg && typeof firstArg === 'object') {
        if (typeof firstArg.message === 'string') return firstArg.message
        if (firstArg.params && typeof firstArg.params.message === 'string') {
          return firstArg.params.message
        }
      }
      return ''
    }

    const extractReportedPageId = (message: string): string | null => {
      const prefixIndex = message.indexOf(PRINT_READY_PREFIX)
      if (prefixIndex < 0) return null
      const suffix = message.slice(prefixIndex + PRINT_READY_PREFIX.length)
      const colonIndex = suffix.indexOf(':')
      if (colonIndex < 0) return null
      return suffix.slice(colonIndex + 1).trim() || null
    }

    const onConsoleMessage = (...rawArgs: unknown[]): void => {
      const reported = extractReportedPageId(resolveConsoleMessageText(...rawArgs))
      if (reported === pageId || reported === 'page-unknown') finalize(false, reported)
    }

    const onClosed = (): void => finalize(true)

    timeoutRef = setTimeout(() => finalize(true), Math.max(500, timeoutMs))
    win.webContents.on('console-message', onConsoleMessage as (...args: unknown[]) => void)
    win.on('closed', onClosed)
  })
}

async function exportPptxForWeb(payload: unknown): Promise<{
  success: boolean
  cancelled: false
  path: string
  downloadUrl: string
  pageCount: number
  warnings: string[]
}> {
  if (!db) throw new Error('Database is not ready')
  const data = payload && typeof payload === 'object' ? (payload as Record<string, unknown>) : {}
  const sessionId = typeof data.sessionId === 'string' ? data.sessionId.trim() : ''
  const requestedPageId = typeof data.pageId === 'string' ? data.pageId.trim() : ''
  if (!sessionId) throw new Error('No session ID provided')

  const session = await db.getSession(sessionId)
  if (!session) throw new Error('Session not found')
  const project = await db.getProject(sessionId)
  const projectDir = project?.output_path || project?.root_path || ''
  if (!projectDir) throw new Error('Project directory not found')

  const allPages = await db.listSessionPages(sessionId)
  const pages = requestedPageId
    ? allPages.filter((page) => page.id === requestedPageId || page.file_slug === requestedPageId)
    : allPages
  if (pages.length === 0) throw new Error('No exportable pages found')

  const slides: HtmlToPptxSlide[] = []
  const warnings: string[] = []
  for (const page of pages) {
    const htmlPath = resolvePageHtmlPath(projectDir, page.file_slug, page.html_path)
    if (!existsSync(htmlPath)) {
      throw new Error(`Page file not found: ${page.file_slug}`)
    }
    const extracted = await captureHtmlPageToPptxImageSlide({
      page: {
        htmlPath,
        pageId: page.file_slug,
        title: page.title
      },
      timeoutMs: EXPORT_PAGE_READY_TIMEOUT_MS,
      settleMs: EXPORT_CAPTURE_SETTLE_MS,
      waitForPrintReadySignal
    })
    slides.push(extracted.slide)
    if (extracted.warning) warnings.push(extracted.warning)
  }

  const title = session.title?.trim() || `ohmyppt-${sessionId}`
  const outDir = path.join(os.tmpdir(), 'ohmyppt-web-exports')
  await fs.promises.mkdir(outDir, { recursive: true })
  const outputPath = path.join(outDir, `${sanitizeExportBaseName(title, `ohmyppt-${sessionId}`)}.pptx`)
  await writeHtmlToPptx(outputPath, {
    title,
    author: 'OhMyPPT',
    slides
  })

  return {
    success: true,
    cancelled: false,
    path: outputPath,
    downloadUrl: buildLocalFileDownloadUrl(outputPath),
    pageCount: slides.length,
    warnings
  }
}

function createHiddenWindow(): BrowserWindow {
  const win = new BrowserWindow({
    show: false,
    width: 1600,
    height: 900,
    webPreferences: {
      contextIsolation: true,
      sandbox: false,
      nodeIntegration: false,
      backgroundThrottling: false
    }
  })

  const originalSend = win.webContents.send.bind(win.webContents)
  win.webContents.send = ((channel: string, ...args: unknown[]) => {
    broadcast(channel, args.length <= 1 ? args[0] : args)
    return originalSend(channel, ...args)
  }) as typeof win.webContents.send

  void win.loadURL('about:blank')
  return win
}

function patchIpcRegistration(): void {
  const originalHandle = ipcMain.handle.bind(ipcMain)
  ipcMain.handle = ((channel: string, listener: IpcHandler) => {
    handlers.set(channel, listener)
    return originalHandle(channel, listener)
  }) as typeof ipcMain.handle
}

function handleEvents(request: IncomingMessage, response: ServerResponse): void {
  response.writeHead(200, {
    'content-type': 'text/event-stream; charset=utf-8',
    'cache-control': 'no-cache',
    connection: 'keep-alive',
    'access-control-allow-origin': '*'
  })
  response.write(`event: ready\ndata: ${JSON.stringify({ ok: true })}\n\n`)

  const id = nextClientId++
  eventClients.set(id, { id, response })
  request.on('close', () => {
    eventClients.delete(id)
  })
}

async function handleIpc(request: IncomingMessage, response: ServerResponse, channel: string, win: BrowserWindow): Promise<void> {
  const handler = handlers.get(channel)
  if (!handler) {
    sendJson(response, 404, { ok: false, error: `IPC channel not registered: ${channel}` })
    return
  }

  try {
    const raw = await readBody(request)
    const body = raw && typeof raw === 'object' && !Array.isArray(raw) ? raw as { args?: unknown[] } : {}
    const args = Array.isArray(body.args) ? body.args : []
    const event = {
      sender: win.webContents
    } as IpcMainInvokeEvent
    const result = await handler(event, ...args)
    sendJson(response, 200, { ok: true, result })
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error)
    log.error('[web-backend] ipc failed', { channel, message })
    sendJson(response, 500, { ok: false, error: message })
  }
}

function startHttpServer(win: BrowserWindow): void {
  const server = createServer((request, response) => {
    response.setHeader('access-control-allow-origin', '*')
    response.setHeader('access-control-allow-methods', 'GET,POST,OPTIONS')
    response.setHeader('access-control-allow-headers', 'content-type')

    if (request.method === 'OPTIONS') {
      response.writeHead(204)
      response.end()
      return
    }

    const requestUrl = new URL(request.url || '/', `http://127.0.0.1:${PORT}`)
    if (request.method === 'GET' && requestUrl.pathname === '/api/health') {
      sendJson(response, 200, {
        ok: true,
        mode: 'electron-ipc-web-backend',
        channels: handlers.size
      })
      return
    }

    if (request.method === 'GET' && requestUrl.pathname === '/api/events') {
      handleEvents(request, response)
      return
    }

    if (request.method === 'GET' && requestUrl.pathname.startsWith('/api/local-file/')) {
      serveLocalFile(requestUrl, response)
      return
    }

    const ipcPrefix = '/api/ipc/'
    if (request.method === 'POST' && requestUrl.pathname.startsWith(ipcPrefix)) {
      const channel = decodeURIComponent(requestUrl.pathname.slice(ipcPrefix.length))
      void handleIpc(request, response, channel, win)
      return
    }

    sendJson(response, 404, { ok: false, error: 'Not found' })
  })

  server.on('error', (error: NodeJS.ErrnoException) => {
    if (error.code === 'EADDRINUSE') {
      log.warn('[web-backend] port already in use; assuming backend is already running', {
        url: `http://127.0.0.1:${PORT}`
      })
      app.quit()
      return
    }
    log.error('[web-backend] server error', {
      message: error.message
    })
    app.exit(1)
  })

  server.listen(PORT, '127.0.0.1', () => {
    log.info('[web-backend] listening', {
      url: `http://127.0.0.1:${PORT}`,
      channels: handlers.size
    })
  })
}

async function main(): Promise<void> {
  configureLogging()
  electronApp.setAppUserModelId('com.ohmyppt.web')

  patchIpcRegistration()

  const dbPath = is.dev ? join(process.cwd(), 'ohmyppt.dev.db') : undefined
  db = new PPTDatabase(dbPath)
  await db.init()
  setStyleDb(db)
  log.info('[web-backend] database initialized', {
    env: is.dev ? 'dev' : 'prod',
    dbPath: dbPath || 'userData/ohmyppt.db'
  })

  const installedSkillsPath = resolveInstalledSkillsPath()
  const skillsReadyPromise = initializeSkills({
    builtinSourcePath: resolveBuiltinSkillsSourcePath(),
    installedRootPath: installedSkillsPath,
    logger: log
  }).catch((error) => {
    log.warn('[web-backend] skills initialize failed', {
      message: error instanceof Error ? error.message : String(error)
    })
    return null
  })
  setSkillsRuntime({ installedSkillsPath, ready: skillsReadyPromise })

  const agentManager = new AgentManager(db)
  const hiddenWindow = createHiddenWindow()
  registerLocalAssetProtocol()
  setupIPC(hiddenWindow, db, agentManager)
  ipcMain.handle('web:exportPptx', async (_event, payload: unknown) => exportPptxForWeb(payload))
  await ensureDefaultWebSettings(hiddenWindow)

  try {
    const savedSettings = await db.getAllSettings()
    if (typeof savedSettings.proxy_url === 'string' && savedSettings.proxy_url.trim()) {
      applyProxy(savedSettings.proxy_url.trim())
    }
  } catch (error) {
    log.warn('[web-backend] failed to apply saved proxy', {
      message: error instanceof Error ? error.message : String(error)
    })
  }

  startHttpServer(hiddenWindow)
}

app.whenReady().then(() => {
  void main().catch((error) => {
    log.error('[web-backend] startup failed', {
      message: error instanceof Error ? error.message : String(error)
    })
    app.exit(1)
  })
})

app.on('window-all-closed', (event) => {
  event.preventDefault()
})

app.on('before-quit', () => {
  if (db) {
    void db.close()
  }
})
