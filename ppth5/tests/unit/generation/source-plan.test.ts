import { describe, expect, it } from 'vitest'
import {
  canUseSourcePlanDirectly,
  mapSourcePlanToOutlineItems,
  sourcePlanFromSkeletonRows
} from '../../../src/main/ipc/generation/source-plan'

describe('source page skeleton planning', () => {
  it('normalizes database rows into a source plan', () => {
    const sourcePlan = sourcePlanFromSkeletonRows([
      {
        page_number: 1,
        title: '第一篇：认知篇',
        role: 'chapter-divider',
        source_document_path: '/docs/source.md',
        source_document_name: 'source.md',
        source_heading: '# 第一篇：认知篇',
        heading_level: 1,
        line_start: 10,
        line_end: 28,
        reason: 'major # heading after the topic',
        confidence: 'high'
      }
    ])

    expect(sourcePlan).toMatchObject({
      confidence: 'high',
      sourceDocumentPath: '/docs/source.md',
      pageSkeleton: [
        {
          pageNumber: 1,
          title: '第一篇：认知篇',
          role: 'chapter-divider',
          sourceHeading: '# 第一篇：认知篇',
          lineStart: 10,
          lineEnd: 28,
          reason: ''
        }
      ]
    })
  })

  it('uses only high-confidence matching skeletons without restructure requests', () => {
    const sourcePlan = sourcePlanFromSkeletonRows([
      {
        page_number: 1,
        title: 'Market',
        role: 'content',
        source_document_path: '/docs/source.md',
        source_heading: '## Market',
        heading_level: 2,
        line_start: 3,
        line_end: 20,
        confidence: 'high'
      }
    ])

    expect(canUseSourcePlanDirectly({ sourcePlan, totalPages: 1, userMessage: '按文档生成' })).toBe(true)
    expect(canUseSourcePlanDirectly({ sourcePlan, totalPages: 2, userMessage: '按文档生成' })).toBe(false)
    expect(canUseSourcePlanDirectly({ sourcePlan, totalPages: 1, userMessage: '压缩成 1 页' })).toBe(false)
  })

  it('maps skeleton rows into range-bound outline items', () => {
    const sourcePlan = sourcePlanFromSkeletonRows([
      {
        page_number: 1,
        title: '收入增长',
        role: 'content',
        source_document_path: '/docs/source.md',
        source_heading: '## 收入增长',
        heading_level: 2,
        line_start: 30,
        line_end: 48,
        reason: 'leaf ## section without standalone child sections',
        confidence: 'high'
      }
    ])
    expect(sourcePlan).not.toBeNull()

    const [item] = mapSourcePlanToOutlineItems(sourcePlan!)

    expect(item).toMatchObject({
      title: '收入增长',
      layoutIntent: 'data-focus'
    })
    expect(item.contentOutline).toContain('Source heading: ## 收入增长')
    expect(item.contentOutline).toContain('Source range: lines 30-48')
    expect(item.contentOutline).not.toContain('Page purpose:')
    expect(item.contentOutline).not.toContain('leaf ## section')
  })
})
