import type { HtmlToPptxExtractOptions } from './types'

const DEFAULT_SLIDE_WIDTH = 13.333
const DEFAULT_SLIDE_HEIGHT = 7.5

export const buildTableExtractScript = (options: HtmlToPptxExtractOptions): string => {
  const slideWidth = options.slideWidthIn ?? DEFAULT_SLIDE_WIDTH
  const slideHeight = options.slideHeightIn ?? DEFAULT_SLIDE_HEIGHT

  return `
(function () {
  const slideWidthIn = ${JSON.stringify(slideWidth)};
  const slideHeightIn = ${JSON.stringify(slideHeight)};

  const rgbToHex = (value) => {
    const source = String(value || '').trim();
    if (!source || source === 'transparent') return '';
    if (source.startsWith('#')) {
      const raw = source.slice(1).toUpperCase();
      return raw.length === 3 ? raw.split('').map((p) => p + p).join('') : raw;
    }
    const m = source.match(/rgba?\\(\\s*(\\d+(?:\\.\\d+)?)(?:\\s*,\\s*|\\s+)(\\d+(?:\\.\\d+)?)(?:\\s*,\\s*|\\s+)(\\d+(?:\\.\\d+)?)(?:\\s*(?:,|\\/)\\s*(\\d+(?:\\.\\d+)?%?))?/i);
    if (!m) return '';
    const alpha = m[4] === undefined ? 1 : String(m[4]).endsWith('%') ? Number.parseFloat(m[4]) / 100 : Number(m[4]);
    if (alpha <= 0.02) return '';
    return [m[1], m[2], m[3]]
      .map((p) => Math.max(0, Math.min(255, Math.round(Number(p) || 0))).toString(16).padStart(2, '0'))
      .join('')
      .toUpperCase();
  };

  const parseAlpha = (value) => {
    const m = String(value || '').match(/rgba?\\(\\s*\\d+(?:\\.\\d+)?(?:\\s*,\\s*|\\s+)\\d+(?:\\.\\d+)?(?:\\s*,\\s*|\\s+)\\d+(?:\\.\\d+)?(?:\\s*(?:,|\\/)\\s*(\\d+(?:\\.\\d+)?%?))?/i);
    if (!m || m[1] === undefined) return 1;
    const raw = String(m[1]);
    return raw.endsWith('%') ? Number.parseFloat(raw) / 100 : Number(raw);
  };

  const pageElement =
    document.querySelector('.ppt-page-root[data-ppt-guard-root="1"]') ||
    document.querySelector('.ppt-page-root') ||
    document.querySelector('[data-ppt-page], [data-page], .ppt-page, .slide, .page') ||
    document.body;
  const pageRect = pageElement.getBoundingClientRect();
  const pageLeft = pageRect.left || 0;
  const pageTop = pageRect.top || 0;
  const layoutWidthPx = pageRect.width || ${JSON.stringify(options.pageWidthPx)};
  const layoutHeightPx = pageRect.height || ${JSON.stringify(options.pageHeightPx)};

  const pxToInX = (v) => ((Number(v) || 0) - pageLeft) / layoutWidthPx * slideWidthIn;
  const pxToInY = (v) => ((Number(v) || 0) - pageTop) / layoutHeightPx * slideHeightIn;
  const sizeToInX = (v) => (Number(v) || 0) / layoutWidthPx * slideWidthIn;
  const sizeToInY = (v) => (Number(v) || 0) / layoutHeightPx * slideHeightIn;
  const pointsPerPx = Math.min(slideWidthIn / layoutWidthPx, slideHeightIn / layoutHeightPx) * 72;

  const tables = [];
  const consumedTableElementIds = [];

  const tableElements = pageElement.querySelectorAll('table');
  for (const tableEl of tableElements) {
    if (tableEl.closest('script, style, noscript, .katex, .katex-mathml')) continue;
    const tableStyle = window.getComputedStyle(tableEl);
    const tableRect = tableEl.getBoundingClientRect();
    if (tableStyle.display === 'none' || tableStyle.visibility === 'hidden') continue;
    if (tableRect.width < 10 || tableRect.height < 10) continue;

    const trs = tableEl.querySelectorAll('tr');
    if (!trs.length) continue;

    // compute maxCols
    let maxCols = 0;
    for (const tr of trs) {
      let cols = 0;
      for (const cell of tr.children) {
        if (cell.tagName === 'TD' || cell.tagName === 'TH') {
          cols += Number(cell.getAttribute('colspan') || 1);
        }
      }
      maxCols = Math.max(maxCols, cols);
    }
    if (maxCols === 0) continue;

    // compute column widths: collect per-cell width contribution per column
    // Track rowspan occupancy so colIdx skips columns consumed by previous rows' rowspan
    const colWidthsPx = new Array(maxCols).fill(0);
    const rowHeightsPx = [];
    const rowSpanGrid = new Array(trs.length).fill(null).map(() => new Array(maxCols).fill(false));
    for (let trIdx = 0; trIdx < trs.length; trIdx++) {
      const tr = trs[trIdx];
      const trRect = tr.getBoundingClientRect();
      rowHeightsPx.push(trRect.height);
      let colIdx = 0;
      for (const cell of tr.children) {
        if (cell.tagName !== 'TD' && cell.tagName !== 'TH') continue;
        const cs = Number(cell.getAttribute('colspan') || 1);
        const rs = Number(cell.getAttribute('rowspan') || 1);
        while (colIdx < maxCols && rowSpanGrid[trIdx][colIdx]) colIdx++;
        if (colIdx >= maxCols) break;
        const cellRect = cell.getBoundingClientRect();
        const perCol = cellRect.width / cs;
        for (let c = 0; c < cs && colIdx + c < maxCols; c++) {
          colWidthsPx[colIdx + c] = Math.max(colWidthsPx[colIdx + c], perCol);
        }
        for (let r = 1; r < rs && trIdx + r < trs.length; r++) {
          for (let c = 0; c < cs && colIdx + c < maxCols; c++) {
            rowSpanGrid[trIdx + r][colIdx + c] = true;
          }
        }
        colIdx += cs;
      }
    }

    const rows = [];
    for (const tr of trs) {
      const row = [];
      for (const cell of tr.children) {
        if (cell.tagName !== 'TD' && cell.tagName !== 'TH') continue;
        const style = window.getComputedStyle(cell);
        const cellRect = cell.getBoundingClientRect();
        const rs = Number(cell.getAttribute('rowspan') || 1);
        const cs = Number(cell.getAttribute('colspan') || 1);

        const text = String(cell.textContent || '').replace(/\\s+/g, ' ').replace(/[\\u200b-\\u200d\\ufeff]/g, '').trim();
        const fontSizePx = Number.parseFloat(style.fontSize || '16') || 16;
        const fontWeight = Number.parseInt(style.fontWeight || '400', 10) || 400;

        const bgHex = rgbToHex(style.backgroundColor);
        const bgAlpha = parseAlpha(style.backgroundColor);
        const borderColorHex = rgbToHex(style.borderColor);
        const borderWidth = Number.parseFloat(style.borderWidth || '0') || 0;
        const hasBorder = borderWidth > 0 && style.borderStyle !== 'none' && borderColorHex;

        let valign = 'top';
        const va = String(style.verticalAlign || '');
        if (va === 'middle') valign = 'middle';
        else if (va === 'bottom') valign = 'bottom';

        let align = 'left';
        const ta = String(style.textAlign || '');
        if (ta === 'center') align = 'center';
        else if (ta === 'right' || ta === 'end') align = 'right';
        else if (ta === 'justify') align = 'justify';

        row.push({
          text,
          rowspan: rs,
          colspan: cs,
          x: pxToInX(cellRect.left),
          y: pxToInY(cellRect.top),
          w: sizeToInX(cellRect.width),
          h: sizeToInY(cellRect.height),
          fontSize: Math.max(6, Math.min(144, fontSizePx * pointsPerPx)),
          fontFace: String(style.fontFamily || '').split(',')[0].replace(/["']/g, '').trim() || 'Aptos',
          color: rgbToHex(style.color) || '111827',
          bold: fontWeight >= 600,
          italic: style.fontStyle === 'italic' || style.fontStyle === 'oblique',
          underline: String(style.textDecoration || '').includes('underline'),
          strike: String(style.textDecoration || '').includes('line-through'),
          align,
          valign,
          fill: bgHex || undefined,
          fillTransparency: bgHex ? Math.round((1 - bgAlpha) * 100) : undefined,
          border: hasBorder ? {
            color: borderColorHex,
            widthPt: borderWidth * 0.75,
            dash: style.borderStyle === 'dashed' ? 'dash' : 'solid'
          } : undefined
        });
      }
      rows.push(row);
    }

    const consumedId = 'pptx-table-' + tables.length;
    tableEl.setAttribute('data-pptx-consumed-table', consumedId);
    consumedTableElementIds.push(consumedId);

    tables.push({
      x: pxToInX(tableRect.left),
      y: pxToInY(tableRect.top),
      w: sizeToInX(tableRect.width),
      h: sizeToInY(tableRect.height),
      colWidths: colWidthsPx.map((w) => sizeToInX(w)),
      rowHeights: rowHeightsPx.map((h) => sizeToInY(h)),
      rows
    });
  }

  return { tables, consumedTableElementIds };
})()
`
}
