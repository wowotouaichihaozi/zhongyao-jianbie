import { AsyncLocalStorage } from 'node:async_hooks'

export const DEFAULT_MODEL_TEMPERATURE = 0.7

type ModelTemperatureRuntime = {
  modelConfigId?: string
  disableTemperature: boolean
  pendingResolution?: boolean
}

const modelTemperatureRuntime = new AsyncLocalStorage<ModelTemperatureRuntime>()

export const getCurrentModelTemperatureControl = (): ModelTemperatureRuntime | undefined =>
  modelTemperatureRuntime.getStore()

export const bindCurrentModelTemperatureControl = (config: {
  id?: string
  disableTemperature?: boolean
}): void => {
  const current = modelTemperatureRuntime.getStore()
  if (current?.pendingResolution) {
    current.modelConfigId = config.id
    current.disableTemperature = config.disableTemperature === true
    current.pendingResolution = false
    return
  }
  modelTemperatureRuntime.enterWith({
    modelConfigId: config.id,
    disableTemperature: config.disableTemperature === true
  })
}

export const prepareCurrentModelTemperatureControl = (): void => {
  modelTemperatureRuntime.enterWith({
    disableTemperature: false,
    pendingResolution: true
  })
}

export const runWithModelTemperatureControl = <T>(
  config: {
    id?: string
    disableTemperature?: boolean
  },
  task: () => T
): T =>
  modelTemperatureRuntime.run(
    {
      modelConfigId: config.id,
      disableTemperature: config.disableTemperature === true
    },
    task
  )

export const isCurrentModelTemperatureEnabled = (): boolean =>
  getCurrentModelTemperatureControl()?.disableTemperature !== true

export const resolveCurrentModelTemperature = (
  temperature: number | undefined
): number | undefined => {
  if (!isCurrentModelTemperatureEnabled()) return undefined
  if (Number.isFinite(temperature) && typeof temperature === 'number') {
    return Math.max(0, Math.min(2, temperature))
  }
  return DEFAULT_MODEL_TEMPERATURE
}

export const resolveCurrentModelTemperatureOptions = (
  temperature: number | undefined
): { temperature?: number } => {
  const resolvedTemperature = resolveCurrentModelTemperature(temperature)
  return resolvedTemperature === undefined ? {} : { temperature: resolvedTemperature }
}
