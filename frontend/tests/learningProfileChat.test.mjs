import assert from 'node:assert/strict'
import test from 'node:test'
import { readFile } from 'node:fs/promises'

import {
  buildProfileSessionChatMessages,
  INITIAL_CHAT_OPENING,
} from '../src/utils/learningProfileChat.js'

const profileViewSource = await readFile(
  new URL('../src/views/LearningProfileView.vue', import.meta.url),
  'utf8',
)

test('keeps the opening before the first persisted conversation turn', () => {
  const messages = buildProfileSessionChatMessages([
    { id: 1, role: 'user', content: '我在学习中医诊断学', createdAt: '2026-07-16T14:12:00Z' },
    { id: 2, role: 'assistant', content: '你目前更关注四诊还是八纲辨证？', createdAt: '2026-07-16T14:12:05Z' },
  ], { now: 100 })

  assert.deepEqual(messages.map(message => message.text), [
    INITIAL_CHAT_OPENING,
    '我在学习中医诊断学',
    '你目前更关注四诊还是八纲辨证？',
  ])
  assert.equal(messages[0].source, 'system')
})

test('moves a persisted opening to the front and removes duplicates', () => {
  const messages = buildProfileSessionChatMessages([
    { id: 1, role: 'user', content: '第一条回答' },
    { id: 2, role: 'assistant', content: INITIAL_CHAT_OPENING },
    { id: 3, role: 'assistant', content: INITIAL_CHAT_OPENING },
  ], { now: 100 })

  assert.equal(messages[0].text, INITIAL_CHAT_OPENING)
  assert.equal(messages.filter(message => message.text === INITIAL_CHAT_OPENING).length, 1)
  assert.equal(messages[1].text, '第一条回答')
})

test('leaves an empty session empty so the existing first-entry flow can speak the opening', () => {
  assert.deepEqual(buildProfileSessionChatMessages([], { now: 100 }), [])
})

test('shows animated dots inside an empty streaming profile-agent reply', () => {
  assert.match(profileViewSource, /'typing-indicator': isPendingProfileReply\(m\)/)
  assert.match(profileViewSource, /<span class="profile-typing-dots"[^>]*><\/span>/)
  assert.match(profileViewSource, /message\?\.source === 'llm-streaming'/)
  assert.match(profileViewSource, /color: #111111/)
  assert.match(profileViewSource, /@keyframes profileTypingCycle/)
  assert.match(profileViewSource, /0%, 24% \{ content: '\\00a0\\00a0\\00a0'; \}/)
  assert.match(profileViewSource, /25%, 49% \{ content: '\.'; \}/)
  assert.match(profileViewSource, /50%, 74% \{ content: '\.\.'; \}/)
  assert.match(profileViewSource, /75%, 100% \{ content: '\.\.\.'; \}/)
  assert.match(profileViewSource, /width: 48px !important/)
  assert.match(profileViewSource, /min-width: 48px !important/)
  assert.match(profileViewSource, /max-width: 48px !important/)
})
