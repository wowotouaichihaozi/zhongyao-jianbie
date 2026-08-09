import { fireEvent, render } from '@testing-library/vue'
import { describe, expect, it } from 'vitest'
import VerticalPath from '../src/components/VerticalPath.vue'

const nodes = [
  { id: 'done', order: 1, title: '已完成任务', state: 'done', resourceType: 'document' },
  { id: 'current', order: 2, title: '当前任务', state: 'current', resourceType: 'question_bank' },
  { id: 'locked', order: 3, title: '锁定任务', state: 'locked', resourceType: 'ppt' },
]

describe('VerticalPath', () => {
  it('expands the current node and disables locked nodes', async () => {
    const view = render(VerticalPath, { props: { nodes } })
    expect(await view.findByText('进度 60%')).toBeTruthy()
    expect(view.getByRole('button', { name: /锁定任务/ }).disabled).toBe(true)
  })

  it('emits an open action for available content', async () => {
    const view = render(VerticalPath, { props: { nodes, modelValue: 'done' } })
    await fireEvent.click(view.getByRole('button', { name: '重新查看' }))
    expect(view.emitted().open[0][0].id).toBe('done')
  })
})
