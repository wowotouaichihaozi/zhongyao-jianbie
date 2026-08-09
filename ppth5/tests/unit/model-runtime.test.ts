import { describe, expect, it } from 'vitest'
import {
  bindCurrentModelTemperatureControl,
  DEFAULT_MODEL_TEMPERATURE,
  getCurrentModelTemperatureControl,
  isCurrentModelTemperatureEnabled,
  resolveCurrentModelTemperature,
  resolveCurrentModelTemperatureOptions,
  runWithModelTemperatureControl
} from '../../src/main/model-runtime'

describe('model temperature runtime', () => {
  it('keeps temperature enabled when no model control is bound', () => {
    expect(getCurrentModelTemperatureControl()).toBeUndefined()
    expect(isCurrentModelTemperatureEnabled()).toBe(true)
    expect(resolveCurrentModelTemperature(0.4)).toBe(0.4)
  })

  it('uses the requested or default temperature when enabled', () => {
    runWithModelTemperatureControl({ disableTemperature: false }, () => {
      expect(isCurrentModelTemperatureEnabled()).toBe(true)
      expect(resolveCurrentModelTemperature(0.2)).toBe(0.2)
      expect(resolveCurrentModelTemperature(undefined)).toBe(DEFAULT_MODEL_TEMPERATURE)
      expect(resolveCurrentModelTemperature(3)).toBe(2)
    })
  })

  it('omits temperature throughout the current async model task when disabled', async () => {
    await runWithModelTemperatureControl(
      { id: 'reasoning-model', disableTemperature: true },
      async () => {
        await Promise.resolve()
        expect(isCurrentModelTemperatureEnabled()).toBe(false)
        expect(resolveCurrentModelTemperature(0.7)).toBeUndefined()
        expect(resolveCurrentModelTemperature(undefined)).toBeUndefined()
        expect(resolveCurrentModelTemperatureOptions(0.7)).not.toHaveProperty('temperature')
      }
    )
  })

  it('isolates enterWith bindings between concurrent async model tasks', async () => {
    let releaseTasks: (() => void) | undefined
    const waitForRelease = new Promise<void>((resolve) => {
      releaseTasks = resolve
    })
    let readyCount = 0
    let releaseReady: (() => void) | undefined
    const allReady = new Promise<void>((resolve) => {
      releaseReady = resolve
    })

    const runTask = async (id: string, disableTemperature: boolean): Promise<number | undefined> => {
      await Promise.resolve()
      bindCurrentModelTemperatureControl({ id, disableTemperature })
      readyCount += 1
      if (readyCount === 2) releaseReady?.()
      await waitForRelease
      expect(getCurrentModelTemperatureControl()?.modelConfigId).toBe(id)
      return resolveCurrentModelTemperature(0.5)
    }

    const disabledTask = runTask('disabled-model', true)
    const enabledTask = runTask('enabled-model', false)
    await allReady
    releaseTasks?.()

    await expect(disabledTask).resolves.toBeUndefined()
    await expect(enabledTask).resolves.toBe(0.5)
  })
})
