import { describe, expect, it, vi } from 'vitest'
import {
  isCurrentModelTemperatureEnabled,
  resolveCurrentModelTemperature
} from '../../../src/main/model-runtime'

vi.mock('../../../src/main/ipc/config/locale-utils', () => ({
  readAppLocale: vi.fn(async () => 'zh'),
  uiText: vi.fn((_locale: string, zh: string) => zh)
}))

vi.mock('@shared/model-timeout', () => ({
  MODEL_TIMEOUT_PROFILES: ['planning', 'design', 'agent', 'document'],
  resolveModelTimeoutMs: vi.fn(() => 1000)
}))

describe('resolveModelConfigForTask temperature control', () => {
  it('binds the selected model temperature setting to the current async task', async () => {
    const { resolveModelConfigForTask } =
      await import('../../../src/main/ipc/config/model-config-utils')
    const ctx = {
      db: {
        getModelConfig: vi.fn(async () => ({
          id: 'model-1',
          name: 'Reasoning model',
          provider: 'openai',
          model: 'reasoner',
          apiKey: 'secret',
          baseUrl: '',
          maxTokens: 4096,
          disableTemperature: 1
        }))
      },
      decryptApiKey: vi.fn((value: unknown) => String(value))
    }

    const config = await resolveModelConfigForTask(ctx as never, {
      modelConfigId: 'model-1',
      purpose: 'test'
    })
    await Promise.resolve()

    expect(config.disableTemperature).toBe(true)
    expect(isCurrentModelTemperatureEnabled()).toBe(false)
    expect(resolveCurrentModelTemperature(0.3)).toBeUndefined()
  })
})
