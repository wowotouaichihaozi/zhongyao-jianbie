export function escapeHtml(value) {
  return String(value ?? '')
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#039;')
}

export function safeResourceHref(value) {
  const href = String(value || '').trim()
  if (/^https?:\/\//i.test(href)) return href
  if (href.startsWith('/') && !href.startsWith('//')) return href
  return ''
}

function renderInline(value) {
  let output = escapeHtml(value)
  output = output.replace(/\[([^\]]+)\]\(([^)\s]+)\)/g, (match, label, href) => {
    const safe = safeResourceHref(href)
    if (!safe) return label
    return `<a href="${safe}" target="_blank" rel="noopener noreferrer">${label}</a>`
  })
  output = output.replace(/`([^`]+)`/g, '<code>$1</code>')
  output = output.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
  return output
}

export function renderSafeMarkdown(value) {
  const source = String(value ?? '').replaceAll('\r\n', '\n')
  const codeBlocks = []
  const tokenized = source.replace(/```([a-zA-Z0-9_-]*)\n([\s\S]*?)```/g, (_match, language, code) => {
    const index = codeBlocks.push({ language, code }) - 1
    return `\n@@CODE_BLOCK_${index}@@\n`
  })
  const output = []
  let paragraph = []
  let listType = ''
  let listItems = []

  const flushParagraph = () => {
    if (!paragraph.length) return
    output.push(`<p>${paragraph.map(renderInline).join('<br>')}</p>`)
    paragraph = []
  }
  const flushList = () => {
    if (!listItems.length) return
    output.push(`<${listType}>${listItems.map(item => `<li>${renderInline(item)}</li>`).join('')}</${listType}>`)
    listType = ''
    listItems = []
  }
  const flushText = () => {
    flushParagraph()
    flushList()
  }

  for (const rawLine of tokenized.split('\n')) {
    const line = rawLine.trim()
    if (!line) {
      flushText()
      continue
    }
    const codeMatch = line.match(/^@@CODE_BLOCK_(\d+)@@$/)
    if (codeMatch) {
      flushText()
      const block = codeBlocks[Number(codeMatch[1])] || { language: '', code: '' }
      const language = String(block.language || '').replace(/[^a-zA-Z0-9_-]/g, '') || 'text'
      output.push(`<pre><code class="language-${language}">${escapeHtml(block.code.trim())}</code></pre>`)
      continue
    }
    const heading = line.match(/^(#{1,3})\s+(.+)$/)
    if (heading) {
      flushText()
      const level = heading[1].length
      output.push(`<h${level}>${renderInline(heading[2])}</h${level}>`)
      continue
    }
    if (/^---+$/.test(line)) {
      flushText()
      output.push('<hr>')
      continue
    }
    if (line.startsWith('> ')) {
      flushText()
      output.push(`<blockquote>${renderInline(line.slice(2))}</blockquote>`)
      continue
    }
    const unordered = line.match(/^[-*]\s+(.+)$/)
    const ordered = line.match(/^\d+[.)]\s+(.+)$/)
    if (unordered || ordered) {
      flushParagraph()
      const nextType = unordered ? 'ul' : 'ol'
      if (listType && listType !== nextType) flushList()
      listType = nextType
      listItems.push((unordered || ordered)[1])
      continue
    }
    flushList()
    paragraph.push(line)
  }
  flushText()
  return output.join('')
}

export function mermaidMindmapSource(value) {
  const source = String(value ?? '').replaceAll('\r\n', '\n').trim()
  const fenced = source.match(/^```mermaid\s*\n([\s\S]*?)\n?```$/i)
  const candidate = String(fenced?.[1] || source).trim()
  return /^mindmap(?:\s|$)/i.test(candidate) ? candidate : ''
}

export function buildSandboxedHtmlDocument(value) {
  const source = String(value ?? '')
  const policy = [
    "default-src 'none'",
    "img-src data: blob:",
    "media-src data: blob:",
    "style-src 'unsafe-inline'",
    "font-src data:",
    "connect-src 'none'",
    "frame-src 'none'",
    "form-action 'none'",
    "base-uri 'none'",
  ].join('; ')
  const guard = `<meta http-equiv="Content-Security-Policy" content="${policy}"><base target="_blank">`
  if (/<head(?:\s[^>]*)?>/i.test(source)) {
    return source.replace(/<head(?:\s[^>]*)?>/i, match => `${match}${guard}`)
  }
  return `<!doctype html><html lang="zh-CN"><head><meta charset="utf-8">${guard}<meta name="viewport" content="width=device-width, initial-scale=1"></head><body>${source}</body></html>`
}
