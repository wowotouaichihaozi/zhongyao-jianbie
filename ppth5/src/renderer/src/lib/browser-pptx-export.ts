/**
 * Browser-compatible PPTX export for H5 mode.
 * The H5 runtime cannot use Electron's offscreen renderer, so it exports each
 * slide as a full-slide PNG captured from the actual HTML preview.
 */
import { zipSync, strToU8 } from 'fflate'

const SLIDE_W = 12192000
const SLIDE_H = 6858000
const SNAPSHOT_W = 1600
const SNAPSHOT_H = 900

const esc = (s: string): string =>
  s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;')

interface TextBlock {
  text: string
  fontSize: number
  bold: boolean
  color: string
  top: number
  left: number
  width: number
  height: number
}

function extractTextBlocks(html: string): TextBlock[] {
  const parser = new DOMParser()
  const doc = parser.parseFromString(html, 'text/html')
  const blocks: TextBlock[] = []
  const elements = doc.querySelectorAll('h1, h2, h3, h4, p, li, td, th, strong, span')
  let yPos = 600000

  for (const el of elements) {
    const text = el.textContent?.trim()
    if (!text || text.length < 2) continue

    const tag = el.tagName.toLowerCase()
    let fontSize = 24
    let bold = false
    let color = '333333'

    if (tag === 'h1') {
      fontSize = 48
      bold = true
      color = '111827'
    } else if (tag === 'h2') {
      fontSize = 32
      bold = true
      color = '1F2937'
    } else if (tag === 'h3') {
      fontSize = 24
      bold = true
      color = '374151'
    } else if (tag === 'h4') {
      fontSize = 20
      bold = true
      color = '4B5563'
    } else if (tag === 'p') {
      fontSize = 18
      color = '44506A'
    } else if (tag === 'li') {
      fontSize = 16
      color = '44506A'
    } else if (tag === 'td' || tag === 'th') {
      fontSize = 14
      color = '374151'
    } else if (tag === 'strong') {
      bold = true
    }

    const displayText = text.length > 200 ? `${text.substring(0, 197)}...` : text
    const charsPerLine = Math.floor(10000000 / (fontSize * 12700))
    const lines = Math.ceil(displayText.length / Math.max(charsPerLine, 10))
    const lineHeight = Math.round(fontSize * 12700 * 1.4)
    const blockHeight = Math.max(lineHeight * lines, lineHeight)

    blocks.push({
      text: displayText,
      fontSize,
      bold,
      color,
      top: yPos,
      left: 600000,
      width: 11000000,
      height: blockHeight
    })

    yPos += blockHeight + 100000
    if (yPos > SLIDE_H - 400000) break
  }

  if (blocks.length === 0) {
    const titleMatch = html.match(/<title[^>]*>([^<]+)<\/title>/i)
    const title = titleMatch ? titleMatch[1].trim() : 'Slide'
    blocks.push({
      text: title,
      fontSize: 40,
      bold: true,
      color: '111827',
      top: 2500000,
      left: 1000000,
      width: 10000000,
      height: 1500000
    })
  }

  return blocks
}

function buildContentTypes(slideCount: number, hasPng: boolean): string {
  const slideOverrides = Array.from({ length: slideCount }, (_, i) =>
    `  <Override PartName="/ppt/slides/slide${i + 1}.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slide+xml"/>`
  ).join('\n')
  return `<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  ${hasPng ? '<Default Extension="png" ContentType="image/png"/>' : ''}
  <Override PartName="/ppt/presentation.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.presentation.main+xml"/>
  <Override PartName="/ppt/slideMasters/slideMaster1.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slideMaster+xml"/>
  <Override PartName="/ppt/slideLayouts/slideLayout1.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slideLayout+xml"/>
  <Override PartName="/ppt/theme/theme1.xml" ContentType="application/vnd.openxmlformats-officedocument.theme+xml"/>
${slideOverrides}
</Types>`
}

const ROOT_RELS = `<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="ppt/presentation.xml"/>
</Relationships>`

function buildPresentation(slideCount: number): string {
  const slideIds = Array.from({ length: slideCount }, (_, i) =>
    `    <p:sldId id="${256 + i}" r:id="rId${i + 1}"/>`
  ).join('\n')
  return `<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<p:presentation xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main">
  <p:sldMasterIdLst><p:sldMasterId id="2147483648" r:id="rIdSm"/></p:sldMasterIdLst>
  <p:sldIdLst>
${slideIds}
  </p:sldIdLst>
  <p:sldSz cx="${SLIDE_W}" cy="${SLIDE_H}" type="wide"/>
  <p:notesSz cx="${SLIDE_H}" cy="${SLIDE_W}"/>
</p:presentation>`
}

function buildPresentationRels(slideCount: number): string {
  const slideRels = Array.from({ length: slideCount }, (_, i) =>
    `  <Relationship Id="rId${i + 1}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slide" Target="slides/slide${i + 1}.xml"/>`
  ).join('\n')
  return `<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rIdSm" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideMaster" Target="slideMasters/slideMaster1.xml"/>
${slideRels}
</Relationships>`
}

const GROUP_PROPS =
  '<p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr><p:grpSpPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="0" cy="0"/><a:chOff x="0" y="0"/><a:chExt cx="0" cy="0"/></a:xfrm></p:grpSpPr>'

const SLIDE_MASTER = `<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<p:sldMaster xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main">
  <p:cSld><p:spTree>${GROUP_PROPS}</p:spTree></p:cSld>
  <p:clrMapOvr><a:masterClrMapping/></p:clrMapOvr>
</p:sldMaster>`

const SLIDE_MASTER_RELS = `<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideLayout" Target="../slideLayouts/slideLayout1.xml"/>
  <Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/theme" Target="../theme/theme1.xml"/>
</Relationships>`

const SLIDE_LAYOUT = `<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<p:sldLayout xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main" type="blank" preserve="1">
  <p:cSld><p:spTree>${GROUP_PROPS}</p:spTree></p:cSld>
  <p:clrMapOvr><a:masterClrMapping/></p:clrMapOvr>
</p:sldLayout>`

const SLIDE_LAYOUT_RELS = `<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideMaster" Target="../slideMasters/slideMaster1.xml"/>
</Relationships>`

const THEME = `<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<a:theme xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" name="OhMyPPT">
  <a:themeElements>
    <a:clrScheme name="OhMyPPT"><a:dk1><a:srgbClr val="111827"/></a:dk1><a:lt1><a:srgbClr val="FFFFFF"/></a:lt1><a:dk2><a:srgbClr val="1F2937"/></a:dk2><a:lt2><a:srgbClr val="F3F4F6"/></a:lt2><a:accent1><a:srgbClr val="2563EB"/></a:accent1><a:accent2><a:srgbClr val="7C3AED"/></a:accent2><a:accent3><a:srgbClr val="06B6D4"/></a:accent3><a:accent4><a:srgbClr val="10B981"/></a:accent4><a:accent5><a:srgbClr val="F59E0B"/></a:accent5><a:accent6><a:srgbClr val="EF4444"/></a:accent6><a:hlink><a:srgbClr val="2563EB"/></a:hlink><a:folHlink><a:srgbClr val="7C3AED"/></a:folHlink></a:clrScheme>
    <a:fontScheme name="OhMyPPT"><a:majorFont><a:latin typeface="Aptos Display"/><a:ea typeface="Microsoft YaHei"/><a:cs typeface=""/></a:majorFont><a:minorFont><a:latin typeface="Aptos"/><a:ea typeface="Microsoft YaHei"/><a:cs typeface=""/></a:minorFont></a:fontScheme>
    <a:fmtScheme name="Office"><a:fillStyleLst><a:solidFill><a:schemeClr val="phClr"/></a:solidFill><a:solidFill><a:schemeClr val="phClr"/></a:solidFill><a:solidFill><a:schemeClr val="phClr"/></a:solidFill></a:fillStyleLst><a:lnStyleLst><a:ln w="6350"><a:solidFill><a:schemeClr val="phClr"/></a:solidFill></a:ln><a:ln w="6350"><a:solidFill><a:schemeClr val="phClr"/></a:solidFill></a:ln><a:ln w="6350"><a:solidFill><a:schemeClr val="phClr"/></a:solidFill></a:ln></a:lnStyleLst><a:effectStyleLst><a:effectStyle><a:effectLst/></a:effectStyle><a:effectStyle><a:effectLst/></a:effectStyle><a:effectStyle><a:effectLst/></a:effectStyle></a:effectStyleLst><a:bgFillStyleLst><a:solidFill><a:schemeClr val="phClr"/></a:solidFill><a:solidFill><a:schemeClr val="phClr"/></a:solidFill><a:solidFill><a:schemeClr val="phClr"/></a:solidFill></a:bgFillStyleLst></a:fmtScheme>
  </a:themeElements>
</a:theme>`

function buildSlideRels(hasImage: boolean, imageFile: string): string {
  return `<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rIdLayout" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideLayout" Target="../slideLayouts/slideLayout1.xml"/>
  ${hasImage ? `<Relationship Id="rIdImage" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image" Target="../media/${imageFile}"/>` : ''}
</Relationships>`
}

function buildImageSlideXml(): string {
  return `<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<p:sld xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main">
  <p:cSld>
    <p:spTree>
      ${GROUP_PROPS}
      <p:pic>
        <p:nvPicPr><p:cNvPr id="2" name="Slide image"/><p:cNvPicPr/><p:nvPr/></p:nvPicPr>
        <p:blipFill><a:blip r:embed="rIdImage"/><a:stretch><a:fillRect/></a:stretch></p:blipFill>
        <p:spPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="${SLIDE_W}" cy="${SLIDE_H}"/></a:xfrm><a:prstGeom prst="rect"><a:avLst/></a:prstGeom></p:spPr>
      </p:pic>
    </p:spTree>
  </p:cSld>
  <p:clrMapOvr><a:masterClrMapping/></p:clrMapOvr>
  <p:transition spd="med" advClick="1"><p:fade/></p:transition>
</p:sld>`
}

function buildTextSlideXml(title: string, blocks: TextBlock[]): string {
  let shapeId = 3
  const shapes = blocks.map((block) => {
    const id = shapeId++
    const textRuns = block.text.split('\n').map((line) =>
      `<a:p><a:pPr/><a:r><a:rPr lang="zh-CN" sz="${Math.round(block.fontSize * 100)}"${block.bold ? ' b="1"' : ''} dirty="0"><a:solidFill><a:srgbClr val="${block.color}"/></a:solidFill><a:latin typeface="Aptos"/><a:ea typeface="Microsoft YaHei"/></a:rPr><a:t>${esc(line)}</a:t></a:r></a:p>`
    ).join('')
    return `<p:sp><p:nvSpPr><p:cNvPr id="${id}" name="Text ${id}"/><p:cNvSpPr txBox="1"/><p:nvPr/></p:nvSpPr><p:spPr><a:xfrm><a:off x="${block.left}" y="${block.top}"/><a:ext cx="${block.width}" cy="${block.height}"/></a:xfrm><a:prstGeom prst="rect"><a:avLst/></a:prstGeom><a:noFill/></p:spPr><p:txBody><a:bodyPr wrap="square" lIns="0" tIns="0" rIns="0" bIns="0" anchor="t"/><a:lstStyle/>${textRuns}</p:txBody></p:sp>`
  }).join('\n      ')
  const titleShape = `<p:sp><p:nvSpPr><p:cNvPr id="2" name="Title 2"/><p:cNvSpPr/><p:nvPr/></p:nvSpPr><p:spPr><a:xfrm><a:off x="600000" y="300000"/><a:ext cx="11000000" cy="800000"/></a:xfrm><a:prstGeom prst="rect"><a:avLst/></a:prstGeom><a:noFill/></p:spPr><p:txBody><a:bodyPr wrap="square" lIns="0" tIns="0" rIns="0" bIns="0" anchor="t"/><a:lstStyle/><a:p><a:pPr/><a:r><a:rPr lang="zh-CN" sz="3600" b="1" dirty="0"><a:solidFill><a:srgbClr val="111827"/></a:solidFill><a:latin typeface="Aptos Display"/><a:ea typeface="Microsoft YaHei"/></a:rPr><a:t>${esc(title)}</a:t></a:r></a:p></p:txBody></p:sp>`

  return `<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<p:sld xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main">
  <p:cSld>
    <p:bg><p:bgPr><a:solidFill><a:srgbClr val="F5F1E8"/></a:solidFill><a:effectLst/></p:bgPr></p:bg>
    <p:spTree>${GROUP_PROPS}${titleShape}${shapes}</p:spTree>
  </p:cSld>
  <p:clrMapOvr><a:masterClrMapping/></p:clrMapOvr>
</p:sld>`
}

function dataUriToBytes(dataUri: string): Uint8Array | null {
  const match = dataUri.match(/^data:image\/png;base64,(.+)$/)
  if (!match) return null
  const raw = atob(match[1])
  const bytes = new Uint8Array(raw.length)
  for (let i = 0; i < raw.length; i++) bytes[i] = raw.charCodeAt(i)
  return bytes
}

const wait = (ms: number): Promise<void> => new Promise((resolve) => setTimeout(resolve, ms))

export async function renderHtmlToPng(html: string): Promise<string> {
  const iframe = document.createElement('iframe')
  iframe.style.cssText = `position:fixed;left:-10000px;top:0;width:${SNAPSHOT_W}px;height:${SNAPSHOT_H}px;border:0;pointer-events:none;opacity:0;`
  iframe.setAttribute('aria-hidden', 'true')
  document.body.appendChild(iframe)

  try {
    iframe.srcdoc = html
    await new Promise<void>((resolve) => {
      iframe.onload = () => resolve()
      setTimeout(resolve, 1200)
    })
    const doc = iframe.contentDocument
    if (!doc?.documentElement || !doc.body) throw new Error('Preview document was not available')

    const style = doc.createElement('style')
    style.textContent = `
      html, body { width: ${SNAPSHOT_W}px !important; height: ${SNAPSHOT_H}px !important; margin: 0 !important; overflow: hidden !important; }
      [data-anim] { opacity: 1 !important; transform: none !important; filter: none !important; visibility: visible !important; }
      *, *::before, *::after { animation: none !important; transition: none !important; }
    `
    doc.head.appendChild(style)
    await (doc as Document & { fonts?: FontFaceSet }).fonts?.ready?.catch(() => undefined)
    await Promise.all(
      Array.from(doc.images).map((img) => {
        if (img.complete) return Promise.resolve()
        return new Promise<void>((resolve) => {
          img.onload = () => resolve()
          img.onerror = () => resolve()
          setTimeout(resolve, 1000)
        })
      })
    )
    await wait(100)

    const styles = Array.from(doc.querySelectorAll('style')).map((el) => el.outerHTML).join('\n')
    const bodyHtml = doc.body.innerHTML
    const xhtml = `<div xmlns="http://www.w3.org/1999/xhtml" style="width:${SNAPSHOT_W}px;height:${SNAPSHOT_H}px;overflow:hidden;background:white;">${styles}${bodyHtml}</div>`
    const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="${SNAPSHOT_W}" height="${SNAPSHOT_H}" viewBox="0 0 ${SNAPSHOT_W} ${SNAPSHOT_H}"><foreignObject width="100%" height="100%">${xhtml}</foreignObject></svg>`
    const url = `data:image/svg+xml;charset=utf-8,${encodeURIComponent(svg)}`
    const img = new Image()
    img.decoding = 'async'
    img.src = url
    await img.decode()

    const canvas = document.createElement('canvas')
    canvas.width = SNAPSHOT_W
    canvas.height = SNAPSHOT_H
    const ctx = canvas.getContext('2d')
    if (!ctx) throw new Error('Canvas context was not available')
    ctx.fillStyle = '#ffffff'
    ctx.fillRect(0, 0, SNAPSHOT_W, SNAPSHOT_H)
    ctx.drawImage(img, 0, 0, SNAPSHOT_W, SNAPSHOT_H)
    return canvas.toDataURL('image/png')
  } finally {
    iframe.remove()
  }
}

export interface BrowserExportPage {
  pageNumber: number
  title: string
  html: string
  htmlUrl: string
}

export async function exportToPptx(
  pages: BrowserExportPage[],
  _presentationTitle: string,
  onProgress?: (current: number, total: number) => void
): Promise<string> {
  if (!pages.length) throw new Error('No pages to export')

  const files: Record<string, Uint8Array> = {}
  const s = (path: string, content: string): void => { files[path] = strToU8(content) }
  const slideCount = pages.length
  let hasPng = false

  s('_rels/.rels', ROOT_RELS)
  s('ppt/presentation.xml', buildPresentation(slideCount))
  s('ppt/_rels/presentation.xml.rels', buildPresentationRels(slideCount))
  s('ppt/slideMasters/slideMaster1.xml', SLIDE_MASTER)
  s('ppt/slideMasters/_rels/slideMaster1.xml.rels', SLIDE_MASTER_RELS)
  s('ppt/slideLayouts/slideLayout1.xml', SLIDE_LAYOUT)
  s('ppt/slideLayouts/_rels/slideLayout1.xml.rels', SLIDE_LAYOUT_RELS)
  s('ppt/theme/theme1.xml', THEME)

  for (let i = 0; i < slideCount; i++) {
    onProgress?.(i + 1, slideCount)
    const page = pages[i]
    const imageFile = `slide${i + 1}.png`
    try {
      const pngDataUri = await renderHtmlToPng(page.html)
      const pngBytes = dataUriToBytes(pngDataUri)
      if (!pngBytes) throw new Error('PNG conversion failed')
      hasPng = true
      files[`ppt/media/${imageFile}`] = pngBytes
      s(`ppt/slides/slide${i + 1}.xml`, buildImageSlideXml())
      s(`ppt/slides/_rels/slide${i + 1}.xml.rels`, buildSlideRels(true, imageFile))
    } catch {
      const blocks = extractTextBlocks(page.html)
      s(`ppt/slides/slide${i + 1}.xml`, buildTextSlideXml(page.title, blocks))
      s(`ppt/slides/_rels/slide${i + 1}.xml.rels`, buildSlideRels(false, imageFile))
    }
  }

  s('[Content_Types].xml', buildContentTypes(slideCount, hasPng))
  const zipData = zipSync(files, { level: 6 })
  const blob = new Blob([zipData], {
    type: 'application/vnd.openxmlformats-officedocument.presentationml.presentation'
  })

  return URL.createObjectURL(blob)
}
