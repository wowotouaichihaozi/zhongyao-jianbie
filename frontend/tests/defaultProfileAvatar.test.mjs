import assert from 'node:assert/strict'
import { readFile, stat } from 'node:fs/promises'
import test from 'node:test'

const source = await readFile(new URL('../src/views/LearningProfileView.vue', import.meta.url), 'utf8')
const defaultAvatar = new URL('../../img/default-profile-avatar.webp', import.meta.url)

test('default portrait is lightweight and used until the report portrait is ready', async () => {
  const avatarStat = await stat(defaultAvatar)
  assert.ok(avatarStat.size > 10_000, 'default portrait should contain a real image')
  assert.ok(avatarStat.size < 250_000, 'default portrait should remain lightweight')
  assert.match(source, /DEFAULT_PROFILE_PORTRAIT_URL = '\/default-profile-avatar\.webp'/)
  assert.match(source, /reportPortraitUrl \|\| DEFAULT_PROFILE_PORTRAIT_URL/)
  assert.match(source, /reportPortraitState === 'ready'/)
  assert.match(source, /当前为默认头像/)
  assert.match(source, /专属头像生成失败/)
})
