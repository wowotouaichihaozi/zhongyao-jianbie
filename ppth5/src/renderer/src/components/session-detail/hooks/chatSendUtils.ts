import type {
  ChatSendContext,
  ChatSendGuardInput,
  ResolveChatSendContextInput,
  SessionDetailChatType
} from '@renderer/types/session-detail'

export function isChatSendBlocked(input: ChatSendGuardInput): boolean {
  return (
    !input.sessionId ||
    input.sending ||
    input.generating ||
    (!input.input.trim() && input.pendingAssetCount === 0)
  )
}

export function resolveChatSendContext(input: ResolveChatSendContextInput): ChatSendContext {
  const selector = input.selectedSelector?.trim() || ''
  const hasSelector = selector.length > 0
  const chatType: SessionDetailChatType = hasSelector ? 'page' : input.chatType
  const targetPage = input.selectedPage ?? input.firstPage

  if (chatType === 'page') {
    if (!targetPage?.id) return { ready: false }
    return {
      ready: true,
      hasSelector,
      selector: hasSelector ? selector : null,
      chatType,
      targetPageId: targetPage.id,
      targetPagePath: targetPage.htmlPath || input.firstPage?.htmlPath,
      messagePageId: targetPage.id
    }
  }

  return {
    ready: true,
    hasSelector,
    selector: null,
    chatType,
    messagePageId: null
  }
}
