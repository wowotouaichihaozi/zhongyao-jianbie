import assert from 'node:assert/strict'
import test from 'node:test'

import { buildLifeTreeModel } from '../src/utils/lifeTreeModel.js'

test('missing learning evidence remains explicitly unverified', () => {
  const model = buildLifeTreeModel({
    profile: { id: 7, profileName: '测试画像' },
    evidence: {},
    assessment: { masteryRate: 0, achievementRate: 0 },
    pathConfig: {},
  })

  assert.equal(model.empty, true)
  assert.equal(model.stats.masteryRate, null)
  assert.equal(model.stats.achievementRate, null)
  assert.equal(model.stats.masteredCount, 0)
  assert.ok(model.branches.every((branch) => branch.status === 'unverified'))
})

test('quantified weak point keeps its evidence and routes its recommendation to a resource', () => {
  const model = buildLifeTreeModel({
    profile: { id: 11, profileName: '辨证学习画像', isActive: true },
    evidence: {
      knowledgePointStats: [{ knowledgePoint: '八纲辨证', attempts: 5 }],
      pathProgress: { trackedNodes: 2, completedNodes: 1 },
    },
    assessment: {
      masteryRate: 40,
      achievementRate: 50,
      evidenceCount: 6,
      knowledgeHeatmap: [{
        knowledgePoint: '八纲辨证',
        masteryRate: 40,
        attempts: 5,
        correctCount: 2,
        status: 'weak',
        evidenceTypes: ['question-bank'],
      }],
      pathAdjustmentPlan: {
        tasks: [{
          knowledgePoint: '八纲辨证',
          resourceType: 'question-bank',
          resourceParams: { topic: '八纲辨证专项巩固' },
          selectionReason: '当前掌握率偏低。',
        }],
      },
    },
  })

  const node = model.nodes.find((item) => item.label === '八纲辨证')
  assert.equal(node.status, 'weak')
  assert.equal(node.recommended, true)
  assert.equal(node.evidenceCount, 5)
  assert.match(node.evidence, /5 次/)
  assert.equal(node.action.to.path, '/personalized-resources/question-bank')
  assert.equal(node.action.to.query.source, 'life-tree')
  assert.equal(model.stats.masteryRate, 40)
})

test('learning path stages become actionable nodes without inventing mastery', () => {
  const model = buildLifeTreeModel({
    pathConfig: {
      weeks: [
        { id: 'week-1', weekLabel: '第一周', title: '中医基础理论', status: 'completed', enabled: true },
        { id: 'week-2', weekLabel: '第二周', title: '四诊合参', status: 'current', enabled: true },
        { id: 'week-3', weekLabel: '第三周', title: '方剂配伍', status: 'locked', enabled: true },
      ],
    },
  })

  const completed = model.nodes.find((node) => node.id === 'path-week-1')
  const current = model.nodes.find((node) => node.id === 'path-week-2')
  const locked = model.nodes.find((node) => node.id === 'path-week-3')
  assert.equal(completed.status, 'mastered')
  assert.equal(current.status, 'recommended')
  assert.equal(current.recommended, true)
  assert.equal(current.action.to, '/learning-path/week/week-2')
  assert.equal(locked.status, 'unverified')
})
