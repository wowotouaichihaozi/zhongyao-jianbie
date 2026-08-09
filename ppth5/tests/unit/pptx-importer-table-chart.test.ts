import { describe, expect, it, vi } from 'vitest'
import { __pptxImporterTestUtils } from '../../src/main/utils/pptx-importer'

vi.mock('../../src/main/ipc/engine/template', () => ({
  buildPageScaffoldHtml: () => '',
  buildProjectIndexHtml: () => ''
}))

const baseBlockArgs = {
  scaleX: 2,
  scaleY: 2,
  textScale: 2,
  zIndex: 3,
  offsetX: 0,
  offsetY: 0
}

describe('pptx importer table and chart blocks', () => {
  it('fits 4:3 slides into the 16:9 canvas without stretching', () => {
    const fit = __pptxImporterTestUtils.resolveSlideFit({ width: 720, height: 540 })

    expect(fit.scale).toBeCloseTo(900 / 540)
    expect(fit.offsetX).toBeCloseTo(200)
    expect(fit.offsetY).toBeCloseTo(0)
  })

  it('removes table style flags when the referenced table style is missing', () => {
    const knownStyleIds = __pptxImporterTestUtils.collectPptxTableStyleIds(
      '<a:tblStyleLst><a:tblStyle styleId="{known-style}"></a:tblStyle></a:tblStyleLst>'
    )
    const result = __pptxImporterTestUtils.removeUnsupportedTableStyleFlags(
      '<a:tblPr firstRow="1" firstCol="1" bandRow="1"><a:tableStyleId>{missing-style}</a:tableStyleId></a:tblPr>',
      knownStyleIds
    )

    expect(result.changed).toBe(true)
    expect(result.xml).toBe(
      '<a:tblPr><a:tableStyleId>{missing-style}</a:tableStyleId></a:tblPr>'
    )
  })

  it('keeps table style flags when the referenced table style exists', () => {
    const knownStyleIds = __pptxImporterTestUtils.collectPptxTableStyleIds(
      '<a:tblStyleLst><a:tblStyle styleId="{known-style}"></a:tblStyle></a:tblStyleLst>'
    )
    const original =
      '<a:tblPr firstRow="1" firstCol="1" bandRow="1"><a:tableStyleId>{known-style}</a:tableStyleId></a:tblPr>'
    const result = __pptxImporterTestUtils.removeUnsupportedTableStyleFlags(original, knownStyleIds)

    expect(result.changed).toBe(false)
    expect(result.xml).toBe(original)
  })

  it('preserves table dimensions, borders, merged cells, and stable cell ids', () => {
    const html = __pptxImporterTestUtils.buildTableBlock({
      ...baseBlockArgs,
      blockId: 'table-1',
      element: {
        left: 10,
        top: 20,
        width: 300,
        height: 120,
        colWidths: [80, 120],
        rowHeights: [24, 32],
        borders: {
          top: { borderColor: '#111111', borderWidth: 1, borderType: 'solid' }
        },
        data: [
          [
            {
              text: '<p style="font-weight:700">Header</p>',
              colSpan: 2,
              fillColor: '#eeeeee',
              fontColor: '#222222',
              borders: {
                bottom: { borderColor: '#333333', borderWidth: 2, borderType: 'dashed' }
              },
              vAlign: 'mid'
            },
            { text: 'merged continuation', hMerge: 1 }
          ],
          [{ text: 'A' }, { text: 'B', vAlign: 'down' }]
        ]
      }
    })

    expect(html).toContain('data-pptx-kind="table"')
    expect(html).toContain('data-pptx-import-mode="editable"')
    expect(html).toContain('<col style="width:160.0px;" />')
    expect(html).toContain('<tr style="height:48.0px;">')
    expect(html).toContain('data-cell-id="r1-c1" colspan="2"')
    expect(html).toContain('border-bottom:4.0px dashed #333333')
    expect(html).toContain('vertical-align:middle')
    expect(html).toContain('vertical-align:bottom')
    expect(html).not.toContain('merged continuation')
  })

  it('preserves table placeholder spacing from form templates', () => {
    const html = __pptxImporterTestUtils.buildTableBlock({
      ...baseBlockArgs,
      blockId: 'table-form',
      element: {
        left: 0,
        top: 0,
        width: 240,
        height: 40,
        colWidths: [120, 120],
        rowHeights: [24],
        data: [
          [
            {
              text: '<p style="text-align:center"><span style="font-size:11pt;font-family:微软雅黑;font-weight:bold">完成（&nbsp;&nbsp;&nbsp;）&nbsp;</span></p>',
              vAlign: 'mid'
            },
            {
              text: '<p style="text-align:left"><span style="font-size:18pt;font-family:Aptos">&nbsp;</span></p>',
              vAlign: 'up'
            }
          ]
        ]
      }
    })

    expect(html).toContain('white-space:pre-wrap')
    expect(html).toContain('完成（&nbsp;&nbsp;&nbsp;）&nbsp;')
    expect(html).toContain('font-size:13.8px')
    expect(html).toContain('&nbsp;</span>')
  })

  it('marks supported charts editable and simplifies area charts to filled lines', () => {
    const html = __pptxImporterTestUtils.buildChartBlock({
      element: {
        type: 'chart',
        chartType: 'areaChart',
        left: 0,
        top: 0,
        width: 320,
        height: 180,
        order: 1,
        colors: ['#1f77b4'],
        data: [
          {
            key: 'Revenue',
            values: [
              { x: 'Q1', y: 10 },
              { x: 'Q2', y: 16 }
            ],
            xlabels: {}
          }
        ]
      },
      blockId: 'chart-1',
      pageId: 'page-1',
      chartIndex: 1,
      scaleX: 1,
      scaleY: 1,
      zIndex: 2,
      offsetX: 0,
      offsetY: 0
    })

    expect(html).toContain('data-pptx-kind="chart"')
    expect(html).toContain('data-pptx-import-mode="editable"')
    expect(html).toContain('data-pptx-chart-type="areaChart"')
    expect(html).toContain('"type":"line"')
    expect(html).toContain('"fill":true')
  })

  it('marks unsupported chart data as a placeholder with warnings', () => {
    const warnings: Array<{ pageNumber?: number; message: string }> = []
    const html = __pptxImporterTestUtils.buildChartBlock({
      element: {
        type: 'chart',
        chartType: 'bubbleChart',
        left: 0,
        top: 0,
        width: 320,
        height: 180,
        order: 1,
        colors: ['#1f77b4'],
        data: [
          [1, 2],
          [3, 4]
        ]
      } as never,
      blockId: 'chart-2',
      pageId: 'page-1',
      chartIndex: 2,
      scaleX: 1,
      scaleY: 1,
      zIndex: 2,
      offsetX: 0,
      offsetY: 0,
      pageNumber: 4,
      warnings
    })

    expect(html).toContain('data-pptx-import-mode="placeholder"')
    expect(html).toContain('data-pptx-chart-type="bubbleChart"')
    expect(warnings).toEqual([
      {
        pageNumber: 4,
        message: '图表 chart-2（bubbleChart）暂不支持结构化导入，已作为占位导入'
      }
    ])
  })
})
