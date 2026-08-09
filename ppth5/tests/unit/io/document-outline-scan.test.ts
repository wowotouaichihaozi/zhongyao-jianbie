import { describe, expect, it } from 'vitest'
import {
  deriveOutlinePageCandidates,
  estimateOutlinePageCount,
  formatDocumentOutlineScanForPrompt,
  scanDocumentOutline,
  scanHasMultipleSlideCandidates
} from '../../../src/main/ipc/io/document-outline-scan'

describe('document outline scan', () => {
  it('extracts markdown heading structure and density hints', () => {
    const scan = scanDocumentOutline(
      [
        '# AI Animation Report',
        '',
        'Intro text.',
        '',
        '## Market Size',
        '- Global growth reached 15%',
        '- China market expanded in 2026',
        '',
        '### Global Growth',
        'Revenue grew 15% YoY.',
        '',
        '## Production Workflow',
        '| Stage | Tool |',
        '| --- | --- |',
        '| Script | LLM |'
      ].join('\n')
    )

    expect(scan.headingCount).toBe(4)
    expect(scan.topLevelTitle).toBe('AI Animation Report')
    expect(scan.sectionTree[0].children.map((node) => node.title)).toEqual([
      'Market Size',
      'Production Workflow'
    ])
    expect(scan.sectionTree[0].children[0].hasMetrics).toBe(true)
    expect(scan.sectionTree[0].children[1].tableCount).toBeGreaterThan(0)
    expect(scan.recommendedSplitHints.join('\n')).toContain(
      'Substantial level-3+ sections can be standalone slides'
    )
    expect(scan.recommendedSplitHints.join('\n')).toContain('### Global Growth')
    expect(scanHasMultipleSlideCandidates(scan)).toBe(true)
  })

  it('derives an authoritative page candidate skeleton in source order', () => {
    const scan = scanDocumentOutline(
      [
        '# Growth Manual',
        '',
        '# 第一篇：认知篇',
        '## 1.1 行业现状',
        'Details.',
        '### 核心变化',
        '- 消费链路变化',
        '',
        '# 第二篇：实操篇',
        '## 2.1 账号定位',
        'Details.'
      ].join('\n')
    )
    const candidates = deriveOutlinePageCandidates(scan)
    const promptText = formatDocumentOutlineScanForPrompt(scan)

    expect(candidates.map((candidate) => candidate.sourceHeading)).toEqual([
      '# 第一篇：认知篇',
      '### 核心变化',
      '# 第二篇：实操篇',
      '## 2.1 账号定位'
    ])
    expect(candidates.map((candidate) => candidate.role)).toEqual([
      'chapter-divider',
      'content',
      'chapter-divider',
      'content'
    ])
    expect(promptText).toContain('Page candidate skeleton (4 slides)')
    expect(promptText).toContain('[chapter-divider] # 第一篇：认知篇')
    expect(promptText).toContain('[content] ### 核心变化')
    expect(promptText).toContain('authoritative first-pass outline')
  })

  it('uses GFM task lists as standalone slide signals', () => {
    const scan = scanDocumentOutline(
      [
        '# Launch Checklist',
        '',
        '## Team Setup',
        '',
        '### Day 1 Checklist',
        '- [x] Register account',
        '- [ ] Configure profile',
        '- [ ] Publish first video'
      ].join('\n')
    )

    const h3 = scan.sectionTree[0].children[0].children[0]
    expect(h3.title).toBe('Day 1 Checklist')
    expect(h3.taskListCount).toBe(3)
    expect(scan.recommendedSplitHints.join('\n')).toContain('### Day 1 Checklist')
  })

  it('keeps parent heading ranges across nested child sections', () => {
    const scan = scanDocumentOutline(
      [
        '# Guide',
        '',
        '## Part A',
        'Intro.',
        '### Step 1',
        'Details.',
        '### Step 2',
        'More details.',
        '## Part B',
        'Done.'
      ].join('\n')
    )

    const partA = scan.sectionTree[0].children[0]
    const step1 = partA.children[0]
    expect(partA.lineStart).toBe(3)
    expect(partA.lineEnd).toBe(8)
    expect(step1.lineStart).toBe(5)
    expect(step1.lineEnd).toBe(6)
  })

  it('marks truncated heading maps so agents grep the rest', () => {
    const source = [
      '# Large Guide',
      ...Array.from({ length: 85 }, (_, index) => [
        `## Section ${index + 1}`,
        `Content ${index + 1}.`
      ]).flat()
    ].join('\n')
    const promptText = formatDocumentOutlineScanForPrompt(scanDocumentOutline(source))

    expect(promptText).toContain('Markdown headings detected: 86')
    expect(promptText).toContain('Heading map truncated: 6 additional headings')
    expect(promptText).toContain('single-shot parse prompt')
  })

  it('keeps substantial level-2 body content before standalone child sections', () => {
    const overview = '市场概述'.repeat(45)
    const scan = scanDocumentOutline(
      [
        '# Market Manual',
        '',
        '## 市场分析',
        overview,
        '',
        '### 增长指标',
        '- GMV grew 15%',
        '- Conversion improved 8%',
        '',
        '### 渠道策略',
        '- Short video',
        '- Live commerce'
      ].join('\n')
    )
    const candidates = deriveOutlinePageCandidates(scan)

    expect(candidates.map((candidate) => candidate.sourceHeading)).toEqual([
      '## 市场分析',
      '### 增长指标',
      '### 渠道策略'
    ])
    expect(candidates[0]).toMatchObject({
      lineStart: 3,
      lineEnd: 5,
      reason: '## section has substantial own body before standalone child sections'
    })
  })

  it('promotes substantial level-4 sections to standalone page candidates', () => {
    const deepDetails = 'implementation detail '.repeat(18)
    const scan = scanDocumentOutline(
      [
        '# Engineering Guide',
        '',
        '## Deployment',
        '',
        '### Runtime',
        '',
        '#### Canary Strategy',
        deepDetails
      ].join('\n')
    )
    const candidates = deriveOutlinePageCandidates(scan)

    expect(candidates.map((candidate) => candidate.sourceHeading)).toContain('#### Canary Strategy')
    expect(candidates.find((candidate) => candidate.sourceHeading === '#### Canary Strategy')).toMatchObject({
      headingLevel: 4,
      reason: 'standalone level-4 section'
    })
  })

  it('keeps large candidate skeleton counts aligned with the prompt-visible target', () => {
    const source = [
      '# Large Manual',
      ...Array.from({ length: 150 }, (_, index) => [
        `## Section ${index + 1}`,
        `Operational content ${index + 1}.`
      ]).flat()
    ].join('\n')
    const scan = scanDocumentOutline(source)
    const estimate = estimateOutlinePageCount(scan)
    const promptText = formatDocumentOutlineScanForPrompt(scan)

    expect(deriveOutlinePageCandidates(scan)).toHaveLength(150)
    expect(estimate?.preferredPageCount).toBe(150)
    expect(promptText).toContain('Page candidate skeleton (150 slides)')
    expect(promptText).not.toContain('Page candidate skeleton truncated')
  })

  it('caps extremely large candidate skeletons to the visible parse target', () => {
    const source = [
      '# Very Large Manual',
      ...Array.from({ length: 520 }, (_, index) => [
        `## Section ${index + 1}`,
        `Operational content ${index + 1}.`
      ]).flat()
    ].join('\n')
    const scan = scanDocumentOutline(source)
    const estimate = estimateOutlinePageCount(scan)
    const promptText = formatDocumentOutlineScanForPrompt(scan)

    expect(deriveOutlinePageCandidates(scan)).toHaveLength(520)
    expect(estimate?.preferredPageCount).toBe(500)
    expect(estimate?.basis).toContain('capped to 500 visible page candidates')
    expect(promptText).toContain('Page candidate skeleton (500 visible of 520 candidates)')
    expect(promptText).toContain('Return pageCount=500')
  })

  it('estimates a stable slide count for large multi-section manuals', () => {
    const source = [
      '# Dealer Growth Guide',
      ...Array.from({ length: 40 }, (_, index) => [
        `## Section ${index + 1}`,
        `Operational content ${index + 1}.`,
        `### Checklist ${index + 1}`,
        '- Step one',
        '- Step two',
        '- Step three'
      ]).flat()
    ].join('\n')
    const scan = scanDocumentOutline(source)
    const estimate = estimateOutlinePageCount(scan)
    const promptText = formatDocumentOutlineScanForPrompt(scan)

    expect(estimate?.preferredPageCount).toBe(40)
    expect(estimate?.minPageCount).toBeLessThanOrEqual(40)
    expect(estimate?.maxPageCount).toBeGreaterThanOrEqual(40)
    expect(promptText).toContain('Deterministic slide-count estimate: prefer 40 slides')
  })

  it('counts major level-1 headings as standalone chapter divider slides', () => {
    const scan = scanDocumentOutline(
      [
        '# Growth Manual',
        '',
        '# 第一篇：认知篇',
        '## 1.1 行业现状',
        'Details.',
        '## 1.2 用户行为',
        'Details.',
        '',
        '# 第二篇：账号搭建定平台',
        '## 2.1 矩阵认知',
        'Details.',
        '## 2.2 平台差异化',
        'Details.',
        '',
        '# 第三篇：账号定位及内容方向',
        '## 3.1 个人号',
        'Details.',
        '## 3.2 蓝V',
        'Details.'
      ].join('\n')
    )
    const estimate = estimateOutlinePageCount(scan)
    const promptText = formatDocumentOutlineScanForPrompt(scan)

    expect(estimate?.preferredPageCount).toBe(9)
    expect(estimate?.basis).toContain('3 chapter divider headings')
    expect(promptText).toContain('Chapter divider slides: # 第一篇：认知篇; # 第二篇：账号搭建定平台; # 第三篇：账号定位及内容方向')
    expect(promptText).toContain('Keep these as standalone section-divider pages')
  })

  it('ignores headings inside fenced code blocks', () => {
    const scan = scanDocumentOutline(
      [
        '# Real Title',
        '```md',
        '# Fake Heading',
        '## Also Fake',
        '```',
        '## Real Section'
      ].join('\n')
    )

    expect(scan.headingCount).toBe(2)
    expect(formatDocumentOutlineScanForPrompt(scan)).toContain('## Real Section')
    expect(formatDocumentOutlineScanForPrompt(scan)).not.toContain('Fake Heading')
  })

  it('formats no-heading documents as paragraph/list fallback', () => {
    const scan = scanDocumentOutline('First paragraph.\n\n- one\n- two', 'text')
    const promptText = formatDocumentOutlineScanForPrompt(scan)

    expect(scan.headingCount).toBe(0)
    expect(promptText).toContain('No heading hierarchy was detected')
    expect(promptText).toContain('split by paragraphs')
  })
})
