import { afterEach, describe, expect, it, vi } from 'vitest'
import type { ResolvedImageModelConfig } from '../../../src/main/image-generation/types'
import {
  buildSeedreamEndpoint,
  seedreamAdapter
} from '../../../src/main/image-generation/providers/seedream'

vi.mock('electron-log/main.js', () => ({
  default: { info: vi.fn(), error: vi.fn(), warn: vi.fn() }
}))

const config = (overrides: Record<string, unknown> = {}): ResolvedImageModelConfig => ({
  id: 'seedream-test',
  name: 'Seedream 4.5',
  provider: 'seedream',
  active: true,
  modelConfig: {
    baseUrl: 'https://api.apimart.ai/v1',
    apiKey: 'test-key',
    model: 'legacy-model-must-be-ignored',
    pollIntervalMs: 500,
    ...overrides
  }
})

const input = {
  prompt: 'A clean embedded systems learning illustration',
  size: '16:9',
  count: 1
}

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('Seedream image adapter', () => {
  it('normalizes the APIMart generation endpoint', () => {
    expect(buildSeedreamEndpoint('https://api.apimart.ai')).toBe(
      'https://api.apimart.ai/v1/images/generations'
    )
    expect(buildSeedreamEndpoint('https://api.apimart.ai/v1')).toBe(
      'https://api.apimart.ai/v1/images/generations'
    )
  })

  it('forces seedream-4-5, 2K and Bearer auth, then polls and downloads the result', async () => {
    const imageBytes = new Uint8Array([137, 80, 78, 71, 13, 10, 26, 10, 1, 2, 3])
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({ data: [{ status: 'submitted', task_id: 'task-seedream-1' }] }),
          { status: 200, headers: { 'content-type': 'application/json' } }
        )
      )
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            code: 200,
            data: {
              status: 'completed',
              result: { images: [{ url: ['https://media.example/generated.png'] }] }
            }
          }),
          { status: 200, headers: { 'content-type': 'application/json' } }
        )
      )
      .mockResolvedValueOnce(
        new Response(imageBytes, { status: 200, headers: { 'content-type': 'image/png' } })
      )
    vi.stubGlobal('fetch', fetchMock)

    const results = await seedreamAdapter.generate(config(), input)

    const [submissionUrl, submissionInit] = fetchMock.mock.calls[0]
    expect(submissionUrl).toBe('https://api.apimart.ai/v1/images/generations')
    expect(submissionInit.headers.authorization).toBe('Bearer test-key')
    expect(JSON.parse(submissionInit.body)).toEqual({
      model: 'seedream-4-5',
      prompt: input.prompt,
      size: '16:9',
      resolution: '2K',
      n: 1,
      watermark: false
    })
    expect(fetchMock.mock.calls[1][0]).toBe(
      'https://api.apimart.ai/v1/tasks/task-seedream-1'
    )
    expect(results).toHaveLength(1)
    expect(results[0].mimeType).toBe('image/png')
  })

  it('rejects failed and empty submissions without falling back to another model', async () => {
    const failedFetch = vi
      .fn()
      .mockResolvedValueOnce(
        new Response(JSON.stringify({ data: [{ task_id: 'task-failed' }] }), { status: 200 })
      )
      .mockResolvedValueOnce(
        new Response(JSON.stringify({ data: { status: 'failed', error: { message: 'blocked' } } }), {
          status: 200
        })
      )
    vi.stubGlobal('fetch', failedFetch)
    await expect(seedreamAdapter.generate(config(), input)).rejects.toThrow('Seedream task failed')

    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(new Response(JSON.stringify({ data: [] }), { status: 200 }))
    )
    await expect(seedreamAdapter.generate(config(), input)).rejects.toThrow(
      'no task ID or image'
    )
  })
})
