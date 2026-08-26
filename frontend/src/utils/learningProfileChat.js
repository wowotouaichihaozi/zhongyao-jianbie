export const INITIAL_CHAT_OPENING = '你好，我是你的数字人 AI 讲师，会陪你梳理中医学习画像，并根据你的回答逐步点亮右侧人脸画像。先从一个简单问题开始：你现在主要在学中医的哪一部分，比如中医基础理论、中医诊断学、中药学、方剂学，还是医案辨析？'

function messageTimestamp(createdAt, fallback) {
  const timestamp = createdAt ? new Date(createdAt).getTime() : Number.NaN
  return Number.isFinite(timestamp) ? timestamp : fallback
}

export function buildProfileSessionChatMessages(messages, { now = Date.now() } = {}) {
  const normalizedMessages = (Array.isArray(messages) ? messages : [])
    .map((message, index) => ({
      id: `session-${message?.id ?? index}`,
      role: message?.role === 'assistant' ? 'bot' : 'user',
      text: String(message?.content || ''),
      attachments: Array.isArray(message?.metadata?.attachments) ? message.metadata.attachments : [],
      timestamp: messageTimestamp(message?.createdAt, now + index),
      source: 'profile-session',
    }))
    .filter(message => message.text.trim())

  if (!normalizedMessages.length) return []

  const openingMessage = normalizedMessages.find(message => (
    message.role === 'bot' && message.text.trim() === INITIAL_CHAT_OPENING
  ))
  const conversationMessages = normalizedMessages.filter(message => (
    message.role !== 'bot' || message.text.trim() !== INITIAL_CHAT_OPENING
  ))

  return [
    openingMessage || {
      id: 'profile-session-opening',
      role: 'bot',
      text: INITIAL_CHAT_OPENING,
      attachments: [],
      timestamp: Math.max(0, normalizedMessages[0].timestamp - 1),
      source: 'system',
    },
    ...conversationMessages,
  ]
}
