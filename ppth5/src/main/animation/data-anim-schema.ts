export const DATA_ANIM_SUPPORTED_TYPES = [
  'fade',
  'fade-up',
  'fade-down',
  'fade-left',
  'fade-right',
  'scale-in',
  'slide-up',
  'slide-left',
  'fly-in',
  'wipe',
  'zoom-in',
  'spin-in',
  'grow-shrink',
  'pulse',
  'exit-fade',
  'exit-fly',
  'path'
] as const

export type DataAnimType = (typeof DATA_ANIM_SUPPORTED_TYPES)[number]

export const DATA_ANIM_FROM_VALUES = ['left', 'right', 'top', 'bottom', 'center'] as const
export type DataAnimFrom = (typeof DATA_ANIM_FROM_VALUES)[number]

export const DATA_ANIM_TRIGGERS = ['load', 'with', 'after', 'click'] as const
export type DataAnimTrigger = (typeof DATA_ANIM_TRIGGERS)[number]
export type DataAnimPptxTrigger = Extract<DataAnimTrigger, 'load' | 'click'>
