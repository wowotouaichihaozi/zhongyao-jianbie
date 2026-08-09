import type { DataAnimFrom, DataAnimType } from './data-anim-schema'

export type PptxPresetClass = 'entr' | 'emph' | 'exit'
export type PptxMotion = 'fromTop' | 'fromBottom' | 'fromLeft' | 'fromRight' | 'fromTrace'

export interface PptxAnimationPreset {
  presetId: number
  presetClass: PptxPresetClass
  presetSubtype?: number
  motion?: PptxMotion
  scale?: boolean
  scaleFrom?: number
  scaleTo?: number
  fade?: boolean
  effectFilter?: 'wipe'
  transition?: 'in' | 'out'
}

export const PPTX_ANIMATION_PRESETS: Record<DataAnimType, PptxAnimationPreset> = {
  fade: { presetId: 10, presetClass: 'entr', fade: true },
  'fade-up': {
    presetId: 2,
    presetClass: 'entr',
    presetSubtype: 8,
    motion: 'fromBottom',
    fade: true
  },
  'fade-down': {
    presetId: 2,
    presetClass: 'entr',
    presetSubtype: 1,
    motion: 'fromTop',
    fade: true
  },
  'fade-left': {
    presetId: 2,
    presetClass: 'entr',
    presetSubtype: 3,
    motion: 'fromRight',
    fade: true
  },
  'fade-right': {
    presetId: 2,
    presetClass: 'entr',
    presetSubtype: 2,
    motion: 'fromLeft',
    fade: true
  },
  'scale-in': { presetId: 31, presetClass: 'entr', scale: true, fade: true },
  'slide-up': {
    presetId: 2,
    presetClass: 'entr',
    presetSubtype: 8,
    motion: 'fromBottom',
    fade: true
  },
  'slide-left': {
    presetId: 2,
    presetClass: 'entr',
    presetSubtype: 3,
    motion: 'fromRight',
    fade: true
  },
  'fly-in': {
    presetId: 2,
    presetClass: 'entr',
    motion: 'fromTrace',
    fade: true
  },
  wipe: {
    presetId: 5,
    presetClass: 'entr',
    effectFilter: 'wipe'
  },
  'zoom-in': {
    presetId: 31,
    presetClass: 'entr',
    scale: true,
    scaleFrom: 75000,
    scaleTo: 100000,
    fade: true
  },
  'spin-in': {
    presetId: 31,
    presetClass: 'entr',
    scale: true,
    scaleFrom: 92000,
    scaleTo: 100000,
    fade: true
  },
  'grow-shrink': {
    presetId: 6,
    presetClass: 'emph',
    scale: true,
    scaleFrom: 90000,
    scaleTo: 108000
  },
  pulse: {
    presetId: 6,
    presetClass: 'emph',
    scale: true,
    scaleFrom: 100000,
    scaleTo: 106000
  },
  'exit-fade': {
    presetId: 10,
    presetClass: 'exit',
    fade: true,
    transition: 'out'
  },
  'exit-fly': {
    presetId: 2,
    presetClass: 'exit',
    motion: 'fromTrace',
    fade: true,
    transition: 'out'
  },
  path: { presetId: 10, presetClass: 'entr', fade: true }
}

export const getPptxAnimationPreset = (
  type: DataAnimType
): PptxAnimationPreset | undefined => PPTX_ANIMATION_PRESETS[type]

export const resolveTraceMotion = (from: DataAnimFrom | undefined): Exclude<PptxMotion, 'fromTrace'> => {
  switch (from) {
    case 'left':
      return 'fromLeft'
    case 'right':
      return 'fromRight'
    case 'top':
      return 'fromTop'
    case 'bottom':
    case 'center':
    default:
      return 'fromBottom'
  }
}

export const wipeFilterForFrom = (from: DataAnimFrom | undefined): string => {
  switch (from) {
    case 'right':
      return 'wipe(l)'
    case 'top':
      return 'wipe(d)'
    case 'bottom':
      return 'wipe(u)'
    case 'left':
    case 'center':
    default:
      return 'wipe(r)'
  }
}

export const mapPptxPresetToDataAnimType = (args: {
  presetId?: string
  presetSubtype?: string
  presetClass?: string
  hasScale: boolean
  effectFilter?: string
}): DataAnimType => {
  if (args.presetClass === 'exit') {
    if (args.presetId === '2') return 'exit-fly'
    return 'exit-fade'
  }
  if (args.presetClass === 'emph' && args.hasScale) return 'pulse'
  if (args.effectFilter?.startsWith('wipe') || args.presetId === '5') return 'wipe'
  if (args.hasScale) return 'scale-in'
  if (args.presetId === '10') return 'fade'
  if (args.presetId === '2') {
    switch (args.presetSubtype) {
      case '1':
        return 'fade-down'
      case '2':
        return 'fade-right'
      case '3':
      case '4':
        return 'fade-left'
      case '8':
        return 'fade-up'
      default:
        return 'fade-up'
    }
  }
  return 'fade'
}

export const mapPptxPresetToDataAnimFrom = (args: {
  presetSubtype?: string
  effectFilter?: string
}): DataAnimFrom | undefined => {
  if (args.effectFilter?.startsWith('wipe')) {
    if (args.effectFilter.includes('(l)')) return 'right'
    if (args.effectFilter.includes('(r)')) return 'left'
    if (args.effectFilter.includes('(u)')) return 'bottom'
    if (args.effectFilter.includes('(d)')) return 'top'
  }
  switch (args.presetSubtype) {
    case '1':
      return 'top'
    case '2':
      return 'left'
    case '3':
    case '4':
      return 'right'
    case '8':
      return 'bottom'
    default:
      return undefined
  }
}
