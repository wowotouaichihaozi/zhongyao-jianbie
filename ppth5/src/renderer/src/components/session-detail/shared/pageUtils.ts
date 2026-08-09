import type { GeneratedPage } from '@renderer/store'
import type { SessionPreviewPage } from './types'

export function normalizePagesForSelection(pages: GeneratedPage[]): SessionPreviewPage[] {
  return [...pages]
    .sort((a, b) => a.pageNumber - b.pageNumber)
    .map((page) => {
      const pageId = page.pageId || `page-${page.pageNumber}`
      return {
        ...page,
        id: page.id || pageId,
        pageId
      }
    })
}
