import { describe, expect, it } from 'vitest'

import { normalizeCreativePageFragment } from '../../../src/main/tools/page-fragment-normalizer'

describe('normalizeCreativePageFragment block ids', () => {
  it('adds stable block ids to nested inline text runs', () => {
    const html = normalizeCreativePageFragment(`
      <p>Normal <span class="accent"><strong>red text</strong></span> normal</p>
    `)

    expect(html).toContain('<p data-block-id="text">')
    expect(html).toMatch(/<span class="accent" data-block-id="text-\d+">/)
    expect(html).toMatch(/<strong data-block-id="text-\d+">red text<\/strong>/)
  })
})
