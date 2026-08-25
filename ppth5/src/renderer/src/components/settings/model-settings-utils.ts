import type { ImageModelConfig, ImageModelProvider, ModelConfig } from '../../lib/ipc'
import type { ImageModelForm, ModelForm } from './types'

export const IMAGE_PROVIDER_OPTIONS: Array<{ value: ImageModelProvider; label: string }> = [
  { value: 'seedream', label: '豆包 Seedream 4.5' }
]

export const readJsonObject = (value: string): Record<string, unknown> | null => {
  const text = value.trim()
  if (!text) return null
  try {
    const parsed = JSON.parse(text)
    return parsed && typeof parsed === 'object' && !Array.isArray(parsed)
      ? (parsed as Record<string, unknown>)
      : null
  } catch {
    return null
  }
}

export const stringifyJsonObject = (record: Record<string, unknown>): string => {
  return JSON.stringify(record, null, 2)
}

export const summarizeImageModelConfig = (value: string): string => {
  const config = readJsonObject(value)
  if (!config) return 'model_config'
  const model = typeof config.model === 'string' ? config.model.trim() : ''
  const reqKey = typeof config.reqKey === 'string' ? config.reqKey.trim() : ''
  const endpoint =
    typeof config.endpoint === 'string'
      ? config.endpoint.trim()
      : typeof config.baseUrl === 'string'
        ? config.baseUrl.trim()
        : ''
  return [model || reqKey || 'model_config', endpoint].filter(Boolean).join(' · ')
}

export const createDefaultImageModelConfig = (_provider: ImageModelProvider): string => {
  return stringifyJsonObject({
    baseUrl: 'https://api.apimart.ai/v1',
    apiKey: '',
    model: 'seedream-4-5',
    resolution: '2K'
  })
}

export const createEmptyModelForm = (active = false): ModelForm => ({
  name: '',
  provider: 'openai',
  model: '',
  apiKey: '',
  baseUrl: '',
  maxTokens: '4096',
  disableTemperature: false,
  active
})

export const createModelForm = (config: ModelConfig): ModelForm => ({
  id: config.id,
  name: config.name,
  provider: config.provider,
  model: config.model,
  apiKey: config.apiKey,
  baseUrl: config.baseUrl,
  maxTokens: String(config.maxTokens || 4096),
  disableTemperature: config.disableTemperature,
  active: config.active
})

export const createEmptyImageModelForm = (active = false): ImageModelForm => ({
  name: '',
  provider: 'seedream',
  modelConfig: createDefaultImageModelConfig('seedream'),
  active
})

export const createImageModelForm = (config: ImageModelConfig): ImageModelForm => {
  return {
    id: config.id,
    name: config.name,
    provider: config.provider,
    modelConfig: config.modelConfig || createDefaultImageModelConfig(config.provider),
    active: config.active
  }
}
