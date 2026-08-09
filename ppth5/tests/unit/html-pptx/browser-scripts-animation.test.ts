import { describe, expect, it } from 'vitest'
import {
  COLLECT_PPTX_ANIMATION_TRACES_SCRIPT,
  FREEZE_PAGE_FOR_PPTX_SCRIPT,
  HIDE_FOR_PPTX_BACKGROUND_SCRIPT
} from '../../../src/main/utils/html-pptx/browser-scripts'

describe('PPTX animation browser scripts', () => {
  it('marks data-anim nodes for native animation without baking them into the background', () => {
    expect(FREEZE_PAGE_FOR_PPTX_SCRIPT).toContain(
      "el.setAttribute('data-pptx-native-anim', '1');"
    )
    expect(HIDE_FOR_PPTX_BACKGROUND_SCRIPT).toContain('[data-pptx-native-anim]')
    expect(HIDE_FOR_PPTX_BACKGROUND_SCRIPT).toContain('box-shadow: none !important')
  })

  it('collects command-style anime targets as fade-up traces', () => {
    expect(COLLECT_PPTX_ANIMATION_TRACES_SCRIPT).toContain('[data-anime]')
    expect(COLLECT_PPTX_ANIMATION_TRACES_SCRIPT).toContain('[data-animate]')
    expect(COLLECT_PPTX_ANIMATION_TRACES_SCRIPT).toContain("collectTrace(el, 'fade-up', 'load', 'bottom', 560, index * 45")
    expect(COLLECT_PPTX_ANIMATION_TRACES_SCRIPT).toContain("el.setAttribute('data-pptx-native-anim', '1');")
  })

  it('collects extended data-anim metadata for native PPTX export', () => {
    expect(COLLECT_PPTX_ANIMATION_TRACES_SCRIPT).toContain("'fly-in'")
    expect(COLLECT_PPTX_ANIMATION_TRACES_SCRIPT).toContain("'exit-fly'")
    expect(COLLECT_PPTX_ANIMATION_TRACES_SCRIPT).toContain("const supportedTriggers = new Set(['load', 'click', 'with', 'after'])")
    expect(COLLECT_PPTX_ANIMATION_TRACES_SCRIPT).toContain('from,')
    expect(COLLECT_PPTX_ANIMATION_TRACES_SCRIPT).toContain("collectTrace(el, type, effectiveTrigger, from")
  })
})
