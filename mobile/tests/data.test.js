import { describe, expect, it } from 'vitest'
import { effectAssessmentMetrics, normalizeNodeState, normalizeTaskState, pathWeeks, stageNodes, taskResources } from '../src/utils/data.js'

describe('mobile data contracts', () => {
  it('normalizes backend task aliases', () => {
    expect(normalizeTaskState('completed')).toBe('complete')
    expect(normalizeTaskState('pending')).toBe('queued')
    expect(normalizeTaskState('waiting_for_user')).toBe('waiting')
  })

  it('sorts weeks vertically by order without using desktop coordinates', () => {
    const weeks = pathWeeks({ config: { weeks: [
      { id: 'w2', order: 2, title: '第二周', x: 900, y: 20, status: 'available' },
      { id: 'w1', order: 1, title: '第一周', x: 100, y: 400, status: 'current' },
    ] } })
    expect(weeks.map(item => item.id)).toEqual(['w1', 'w2'])
    expect(weeks[0].state).toBe('current')
  })

  it('normalizes stage nodes and preserves locked state', () => {
    const nodes = stageNodes({ stage: { nodes: [{ id: 'a', order: 2 }, { id: 'b', order: 1, state: 'locked' }] } })
    expect(nodes.map(item => item.id)).toEqual(['b', 'a'])
    expect(normalizeNodeState(nodes[0].state)).toBe('locked')
  })

  it('extracts distinct specialist resources from a completed workflow', () => {
    const resources = taskResources({ result: { workflow: { resources: [{ type: 'ppt' }, { type: 'mindmap' }] } } })
    expect(resources.map(item => item.type)).toEqual(['ppt', 'mindmap'])
  })

  it('uses node evidence for path progress and does not invent mastery', () => {
    const metrics = effectAssessmentMetrics({ data: { assessment: {
      completedNodes: 28,
      trackedNodes: 40,
      achievementRate: 70,
      masteryRate: 0,
      generatedResourceCount: 40,
      masteryBreakdown: [
        { label: '知识点答题', available: false },
        { label: '综合考试', available: false },
      ],
    } } }, [{ state: 'current' }, { state: 'locked' }])

    expect(metrics).toEqual({ pathProgress: 70, achievementRate: 70, masteryRate: null, generatedTaskCount: 40 })
  })

  it('shows mastery only when verified evidence exists', () => {
    const metrics = effectAssessmentMetrics({ assessment: {
      masteryRate: 82.4,
      masteryBreakdown: [{ label: '综合考试', available: true }],
    } })
    expect(metrics.masteryRate).toBe(82)
  })

  it('falls back to persisted task history when the assessment count is absent', () => {
    const metrics = effectAssessmentMetrics({}, [], [{ taskId: 'a' }, { taskId: 'b' }])
    expect(metrics.generatedTaskCount).toBe(2)
  })
})
