import fs from 'fs'
import os from 'os'
import path from 'path'
import { afterEach, describe, expect, it } from 'vitest'
import { createThinkingWorkflowTools } from '../../../src/main/thinking/thinking-tools'

const tempDirs: string[] = []

const makeTempThinkingDir = async (): Promise<string> => {
  const dir = await fs.promises.mkdtemp(path.join(os.tmpdir(), 'thinking-tools-'))
  tempDirs.push(dir)
  await fs.promises.writeFile(
    path.join(dir, 'thinking.md'),
    [
      '# Thinking Brief',
      '',
      '## Topic',
      '',
      '## Page Count',
      '0',
      ''
    ].join('\n'),
    'utf-8'
  )
  return dir
}

const page = (title: string): {
  title: string
  role: 'content'
  objective: string
  summary: string
  keyPoints: string[]
} => ({
  title,
  role: 'content',
  objective: `说明 ${title}`,
  summary: `${title} 的内容摘要。`,
  keyPoints: [`${title} 重点一`, `${title} 重点二`]
})

afterEach(async () => {
  await Promise.all(
    tempDirs.splice(0).map((dir) => fs.promises.rm(dir, { recursive: true, force: true }))
  )
})

describe('thinking workflow tools', () => {
  it('stages page batches in memory and writes thinking.md only on final commit', async () => {
    const thinkingDir = await makeTempThinkingDir()
    const initial = await fs.promises.readFile(path.join(thinkingDir, 'thinking.md'), 'utf-8')
    const { tools, state } = createThinkingWorkflowTools({
      thinkingDir,
      currentStage: 'collect'
    })
    const updateThinking = tools.find((tool) => tool.name === 'update_thinking_document')
    expect(updateThinking).toBeTruthy()

    await updateThinking!.invoke({
      topic: '分批大纲',
      pageCount: 4,
      pageStart: 1,
      pages: [page('第一页'), page('第二页')]
    })
    expect(state.thinkingStaged).toBe(true)
    expect(state.thinkingUpdated).toBe(false)
    expect(await fs.promises.readFile(path.join(thinkingDir, 'thinking.md'), 'utf-8')).toBe(initial)

    await updateThinking!.invoke({
      pageStart: 3,
      pages: [page('第三页'), page('第四页')],
      commit: true
    })
    const committed = await fs.promises.readFile(path.join(thinkingDir, 'thinking.md'), 'utf-8')

    expect(state.thinkingStaged).toBe(false)
    expect(state.thinkingUpdated).toBe(true)
    expect(state.thinkingUpdateCount).toBe(1)
    expect(committed).toContain('## Topic\n分批大纲')
    expect(committed).toContain('## Page Count\n4')
    expect(committed).toContain('## Page 1: 第一页')
    expect(committed).toContain('## Page 2: 第二页')
    expect(committed).toContain('## Page 3: 第三页')
    expect(committed).toContain('## Page 4: 第四页')
  })

  it('keeps immediate full-page replacement behavior for small outlines', async () => {
    const thinkingDir = await makeTempThinkingDir()
    const { tools, state } = createThinkingWorkflowTools({
      thinkingDir,
      currentStage: 'collect'
    })
    const updateThinking = tools.find((tool) => tool.name === 'update_thinking_document')
    expect(updateThinking).toBeTruthy()

    await updateThinking!.invoke({
      topic: '小大纲',
      pages: [page('封面'), page('结论')]
    })
    const committed = await fs.promises.readFile(path.join(thinkingDir, 'thinking.md'), 'utf-8')

    expect(state.thinkingStaged).toBe(false)
    expect(state.thinkingUpdated).toBe(true)
    expect(committed).toContain('## Page Count\n2')
    expect(committed).toContain('## Page 1: 封面')
    expect(committed).toContain('## Page 2: 结论')
  })

  it('auto-commits a complete staged document when the model forgets commit', async () => {
    const thinkingDir = await makeTempThinkingDir()
    const { tools, state, finalizeStagedThinkingDocument } = createThinkingWorkflowTools({
      thinkingDir,
      currentStage: 'collect'
    })
    const updateThinking = tools.find((tool) => tool.name === 'update_thinking_document')
    expect(updateThinking).toBeTruthy()

    await updateThinking!.invoke({
      topic: '忘记提交',
      pageCount: 2,
      pageStart: 1,
      pages: [page('第一页'), page('第二页')]
    })
    const result = await finalizeStagedThinkingDocument()
    const committed = await fs.promises.readFile(path.join(thinkingDir, 'thinking.md'), 'utf-8')

    expect(result).toMatchObject({ status: 'committed', pageCount: 2 })
    expect(state.thinkingStaged).toBe(false)
    expect(state.thinkingUpdated).toBe(true)
    expect(committed).toContain('## Topic\n忘记提交')
    expect(committed).toContain('## Page 1: 第一页')
    expect(committed).toContain('## Page 2: 第二页')
  })

  it('keeps incomplete staged batches recoverable when commit is called too early', async () => {
    const thinkingDir = await makeTempThinkingDir()
    const initial = await fs.promises.readFile(path.join(thinkingDir, 'thinking.md'), 'utf-8')
    const { tools, state } = createThinkingWorkflowTools({
      thinkingDir,
      currentStage: 'collect'
    })
    const updateThinking = tools.find((tool) => tool.name === 'update_thinking_document')
    expect(updateThinking).toBeTruthy()

    const earlyResult = await updateThinking!.invoke({
      topic: '提前提交',
      pageCount: 3,
      pageStart: 1,
      pages: [page('第一页')],
      commit: true
    })
    const afterEarlyCommit = await fs.promises.readFile(path.join(thinkingDir, 'thinking.md'), 'utf-8')

    expect(String(earlyResult)).toContain('thinking.md is still staged')
    expect(String(earlyResult)).toContain('missing page 2')
    expect(state.thinkingStaged).toBe(true)
    expect(state.thinkingUpdated).toBe(false)
    expect(afterEarlyCommit).toBe(initial)

    const finalResult = await updateThinking!.invoke({
      pageStart: 2,
      pages: [page('第二页'), page('第三页')],
      commit: true
    })
    const committed = await fs.promises.readFile(path.join(thinkingDir, 'thinking.md'), 'utf-8')

    expect(String(finalResult)).toContain('thinking.md updated from staged batches')
    expect(state.thinkingStaged).toBe(false)
    expect(state.thinkingUpdated).toBe(true)
    expect(committed).toContain('## Page 1: 第一页')
    expect(committed).toContain('## Page 2: 第二页')
    expect(committed).toContain('## Page 3: 第三页')
  })

  it('discards an incomplete staged document instead of writing a partial thinking.md', async () => {
    const thinkingDir = await makeTempThinkingDir()
    const initial = await fs.promises.readFile(path.join(thinkingDir, 'thinking.md'), 'utf-8')
    const { tools, state, finalizeStagedThinkingDocument } = createThinkingWorkflowTools({
      thinkingDir,
      currentStage: 'collect'
    })
    const updateThinking = tools.find((tool) => tool.name === 'update_thinking_document')
    expect(updateThinking).toBeTruthy()

    await updateThinking!.invoke({
      topic: '半截大纲',
      pageCount: 3,
      pageStart: 1,
      pages: [page('第一页'), page('第二页')]
    })
    const result = await finalizeStagedThinkingDocument()
    const after = await fs.promises.readFile(path.join(thinkingDir, 'thinking.md'), 'utf-8')

    expect(result).toMatchObject({
      status: 'discarded',
      reason: 'missing page 3',
      pageCount: 2,
      expectedPageCount: 3
    })
    expect(state.thinkingStaged).toBe(false)
    expect(state.thinkingUpdated).toBe(false)
    expect(after).toBe(initial)
  })
})
