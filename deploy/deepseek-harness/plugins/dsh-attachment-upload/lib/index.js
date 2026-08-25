import { execFile } from 'node:child_process'
import { mkdir, mkdtemp, realpath, stat, writeFile } from 'node:fs/promises'
import path from 'node:path'
import { promisify } from 'node:util'

export const name = 'lzhan-dsh-attachment-upload'
export const inject = []

const execFileAsync = promisify(execFile)
const MAX_BYTES = 64 * 1024 * 1024
const INVALID_NAME_CHARS = /[\\/:*?"<>|\u0000-\u001f]/g

function responseJson(res, status, body) {
  const bytes = Buffer.from(JSON.stringify(body))
  res.setHeader('Content-Type', 'application/json; charset=utf-8')
  res.setHeader('Content-Length', String(bytes.length))
  res.setHeader('Cache-Control', 'no-store')
  res.setHeader('X-Content-Type-Options', 'nosniff')
  res.setHeader('Content-Security-Policy', "default-src 'none'; frame-ancestors 'none'")
  res.writeHead(status)
  res.end(bytes)
}

function sameOriginPost(req) {
  const fetchSite = req.headers['sec-fetch-site']
  if (fetchSite === 'cross-site') return false
  const origin = req.headers.origin
  if (origin === undefined) return fetchSite === 'same-origin' || fetchSite === 'same-site' || fetchSite === 'none'
  const host = req.headers.host
  if (host === undefined) return false
  try {
    const parsed = new URL(origin)
    return (parsed.protocol === 'http:' || parsed.protocol === 'https:') && parsed.host === host
  } catch {
    return false
  }
}

function sanitizeName(raw) {
  let value = String(raw ?? '').trim().replace(INVALID_NAME_CHARS, '_')
  value = value.replace(/^\.+/, '_')
  if (!value) value = 'attachment'
  if (value.length > 120) {
    const extension = path.extname(value).slice(0, 16)
    value = value.slice(0, 100) + extension
  }
  return value
}

async function readBody(req) {
  const chunks = []
  let total = 0
  for await (const chunk of req) {
    const part = Buffer.isBuffer(chunk) ? chunk : Buffer.from(chunk)
    total += part.length
    if (total > MAX_BYTES) throw new Error('file exceeds the 64 MB limit')
    chunks.push(part)
  }
  return Buffer.concat(chunks)
}

function isWithin(root, candidate) {
  const relative = path.relative(root, candidate)
  return relative === '' || (!relative.startsWith(`..${path.sep}`) && relative !== '..' && !path.isAbsolute(relative))
}

async function configuredWorkspaceRoot() {
  const configured = String(process.env.DSH_FILE_UPLOAD_ROOT || '').trim()
  if (!configured || !path.isAbsolute(configured)) throw new Error('DSH_FILE_UPLOAD_ROOT must be an absolute path')
  const root = await realpath(configured)
  const info = await stat(root)
  if (!info.isDirectory()) throw new Error('configured upload root is not a directory')
  return root
}

async function resolveTargetPath(root, rawName) {
  const name = sanitizeName(rawName)
  const uploadDir = path.join(root, '.dsh-attachments')
  await mkdir(uploadDir, { recursive: true, mode: 0o750 })
  const canonicalUploadDir = await realpath(uploadDir)
  if (!isWithin(root, canonicalUploadDir)) throw new Error('upload directory escaped the workspace')

  const extension = path.extname(name)
  const base = name.slice(0, name.length - extension.length)
  for (let index = 0; index < 1000; index += 1) {
    const filename = index === 0 ? name : `${base} (${index})${extension}`
    const candidate = path.join(canonicalUploadDir, filename)
    if (!isWithin(canonicalUploadDir, candidate)) throw new Error('invalid upload target')
    try {
      await stat(candidate)
    } catch (error) {
      if (error?.code === 'ENOENT') return candidate
      throw error
    }
  }
  throw new Error('could not allocate a file name')
}

async function extractZip(root, archivePath, originalName) {
  if (path.extname(originalName).toLowerCase() !== '.zip') return null
  const extractor = String(process.env.DSH_SAFE_ZIP_EXTRACTOR || '').trim()
  if (!extractor || !path.isAbsolute(extractor)) throw new Error('safe ZIP extractor is not configured')

  const extractionRoot = path.join(root, '.dsh-attachments', 'extracted')
  await mkdir(extractionRoot, { recursive: true, mode: 0o750 })
  const safeStem = sanitizeName(path.basename(originalName, '.zip')).replace(/\.[^.]+$/, '') || 'archive'
  const targetDir = await mkdtemp(path.join(extractionRoot, `${safeStem}-`))
  if (!isWithin(root, targetDir)) throw new Error('archive target escaped the workspace')

  const { stdout } = await execFileAsync('python3', [extractor, archivePath, targetDir], {
    timeout: 120000,
    maxBuffer: 1024 * 1024,
    windowsHide: true,
  })
  const result = JSON.parse(String(stdout || '').trim())
  if (!result?.ok) throw new Error(result?.error || 'safe ZIP extraction failed')
  return { path: targetDir, entries: result.entries, totalBytes: result.totalBytes }
}

export function apply(ctx) {
  ctx.inject(['webServer'], (webCtx) => {
    webCtx.effect(() => webCtx.webServer.register({
      kind: 'exact',
      path: '/_dsh/attachment-upload/upload',
      handler: async (req, res) => {
        try {
          if (req.method !== 'POST' || !sameOriginPost(req)) {
            return responseJson(res, 403, { ok: false, reason: 'same-origin POST required' })
          }
          const encodedName = req.headers['x-file-name']
          if (typeof encodedName !== 'string') return responseJson(res, 400, { ok: false, reason: 'missing file name' })

          const name = decodeURIComponent(encodedName)
          const body = await readBody(req)
          if (body.length === 0) return responseJson(res, 400, { ok: false, reason: 'empty file' })

          const root = await configuredWorkspaceRoot()
          const target = await resolveTargetPath(root, name)
          await writeFile(target, body, { flag: 'wx', mode: 0o640 })
          const extracted = await extractZip(root, target, name)
          return responseJson(res, 200, { ok: true, path: target, bytes: body.length, extracted })
        } catch (error) {
          return responseJson(res, 400, {
            ok: false,
            reason: String(error?.message || error).slice(0, 300),
          })
        }
      },
    }), 'lzhan-dsh-attachment-upload: upload route')
  })
}
