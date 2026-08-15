import log from 'electron-log/main.js'
import type {
  ImageGenerationProviderAdapter,
  ImageGenerationResult,
  ResolvedImageModelConfig
} from '../types'
import { collectImageResults, joinUrl, readRecord, readString } from './utils'

export const SEEDREAM_MODEL = 'seedream-4-5'
export const DEFAULT_SEEDREAM_BASE_URL = 'https://api.apimart.ai/v1'
const DEFAULT_POLL_INTERVAL_MS = 5000
const DEFAULT_POLL_TIMEOUT_MS = 360000
const FAILED_STATUSES = new Set(['failed', 'failure', 'error', 'cancelled', 'canceled'])

const boundedNumber = (
  value: unknown,
  fallback: number,
  minimum: number,
  maximum: number
): number => {
  const parsed = Number(value)
  return Number.isFinite(parsed) ? Math.max(minimum, Math.min(maximum, parsed)) : fallback
}

const normalizeBaseUrl = (_config: ResolvedImageModelConfig): string => DEFAULT_SEEDREAM_BASE_URL

export const buildSeedreamEndpoint = (baseUrl: string): string => {
  const normalized = baseUrl.replace(/\/+$/, '')
  if (/\/images\/generations$/i.test(normalized)) return normalized
  try {
    const url = new URL(normalized)
    const path = url.pathname.replace(/\/+$/, '')
    if (!path) return joinUrl(normalized, '/v1/images/generations')
  } catch {
    // Non-standard fetchable URLs retain their configured path.
  }
  return joinUrl(normalized, '/images/generations')
}

const buildTaskEndpoint = (generationEndpoint: string, taskId: string): string =>
  `${generationEndpoint.replace(/\/images\/generations$/i, '')}/tasks/${encodeURIComponent(taskId)}`

const responsePreview = (text: string): string => text.replace(/\s+/g, ' ').trim().slice(0, 500)

const readJson = async (response: Response, operation: string): Promise<unknown> => {
  const text = await response.text()
  if (!response.ok) {
    throw new Error(
      `Seedream ${operation} failed (${response.status}): ${responsePreview(text) || 'empty response'}`
    )
  }
  try {
    return JSON.parse(text)
  } catch {
    throw new Error(`Seedream ${operation} returned invalid JSON`)
  }
}

const firstString = (value: unknown, keys: string[], depth = 0): string => {
  if (depth > 8 || value == null) return ''
  if (Array.isArray(value)) {
    for (const item of value) {
      const found = firstString(item, keys, depth + 1)
      if (found) return found
    }
    return ''
  }
  const record = readRecord(value)
  for (const key of keys) {
    const found = readString(record, key)
    if (found) return found
  }
  for (const nested of Object.values(record)) {
    const found = firstString(nested, keys, depth + 1)
    if (found) return found
  }
  return ''
}

const collectImageCandidates = (value: unknown, output: string[], depth = 0): void => {
  if (depth > 10 || value == null) return
  if (Array.isArray(value)) {
    for (const item of value) collectImageCandidates(item, output, depth + 1)
    return
  }
  const record = readRecord(value)
  for (const key of ['url', 'image_url', 'imageUrl', 'b64_json', 'base64', 'image_base64']) {
    const candidate = record[key]
    if (typeof candidate === 'string' && candidate.trim()) output.push(candidate.trim())
    if (Array.isArray(candidate)) {
      for (const item of candidate) {
        if (typeof item === 'string' && item.trim()) output.push(item.trim())
      }
    }
  }
  for (const nested of Object.values(record)) collectImageCandidates(nested, output, depth + 1)
}

const extractImages = async (
  payload: unknown,
  signal?: AbortSignal
): Promise<ImageGenerationResult[]> => {
  const candidates: string[] = []
  collectImageCandidates(payload, candidates)
  return collectImageResults({ data: [...new Set(candidates)] }, signal)
}

const wait = (milliseconds: number, signal?: AbortSignal): Promise<void> =>
  new Promise((resolve, reject) => {
    if (signal?.aborted) {
      reject(signal.reason || new Error('Seedream generation cancelled'))
      return
    }
    const timeout = setTimeout(resolve, milliseconds)
    signal?.addEventListener(
      'abort',
      () => {
        clearTimeout(timeout)
        reject(signal.reason || new Error('Seedream generation cancelled'))
      },
      { once: true }
    )
  })

const pollTask = async (
  endpoint: string,
  taskId: string,
  apiKey: string,
  config: ResolvedImageModelConfig,
  signal?: AbortSignal
): Promise<ImageGenerationResult[]> => {
  const pollIntervalMs = boundedNumber(
    config.modelConfig.pollIntervalMs,
    DEFAULT_POLL_INTERVAL_MS,
    500,
    30000
  )
  const pollTimeoutMs = boundedNumber(
    config.modelConfig.pollTimeoutMs,
    DEFAULT_POLL_TIMEOUT_MS,
    30000,
    900000
  )
  const deadline = Date.now() + pollTimeoutMs
  while (Date.now() < deadline) {
    const response = await fetch(buildTaskEndpoint(endpoint, taskId), {
      signal,
      headers: { accept: 'application/json', authorization: `Bearer ${apiKey}` }
    })
    const payload = await readJson(response, 'task polling')
    const images = await extractImages(payload, signal)
    if (images.length > 0) return images
    const status = firstString(payload, ['status', 'state', 'task_status', 'taskStatus']).toLowerCase()
    if (FAILED_STATUSES.has(status)) throw new Error(`Seedream task ${status}`)
    await wait(pollIntervalMs, signal)
  }
  throw new Error('Seedream task polling timed out')
}

export const seedreamAdapter: ImageGenerationProviderAdapter = {
  async generate(config, input) {
    const startedAt = Date.now()
    const baseUrl = normalizeBaseUrl(config)
    const endpoint = buildSeedreamEndpoint(baseUrl)
    const apiKey = readString(config.modelConfig, 'apiKey') || readString(config.modelConfig, 'api_key')
    if (!apiKey) throw new Error('Seedream API key is required')
    const count = Math.max(1, Math.min(15, Math.floor(input.count)))
    const resolution = readString(config.modelConfig, 'resolution').toUpperCase() === '4K' ? '4K' : '2K'
    const headers = readRecord(config.modelConfig.headers) as Record<string, string>

    log.info('[images:seedream] generation start', {
      configId: config.id,
      model: SEEDREAM_MODEL,
      baseUrl,
      count,
      size: input.size,
      resolution,
      promptLength: input.prompt.length
    })

    const response = await fetch(endpoint, {
      method: 'POST',
      signal: input.signal,
      headers: {
        ...headers,
        accept: 'application/json',
        authorization: `Bearer ${apiKey}`,
        'content-type': 'application/json'
      },
      body: JSON.stringify({
        model: SEEDREAM_MODEL,
        prompt: input.prompt,
        size: input.size,
        resolution,
        n: count,
        watermark: false
      })
    })
    const payload = await readJson(response, 'submission')
    const immediate = await extractImages(payload, input.signal)
    if (immediate.length > 0) return immediate.slice(0, count)
    const taskId = firstString(payload, ['task_id', 'taskId', 'id'])
    if (!taskId) throw new Error('Seedream submission returned no task ID or image')
    const results = await pollTask(endpoint, taskId, apiKey, config, input.signal)
    log.info('[images:seedream] generation completed', {
      model: SEEDREAM_MODEL,
      resultCount: results.length,
      elapsedMs: Date.now() - startedAt
    })
    return results.slice(0, count)
  }
}
