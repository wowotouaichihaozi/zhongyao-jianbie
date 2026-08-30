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
  assert.equal(model.stats.completedWeeks, 0)
  assert.equal(model.fruits.length, 6)
  assert.ok(model.fruits.every((fruit) => fruit.progress === 0 && fruit.available === false))
  assert.match(model.fruits[0].evidence, /不计入完成度/)
})

test('knowledge assessment does not invent weekly fruit maturity', () => {
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

  assert.equal(model.stats.masteryRate, 40)
  assert.equal(model.stats.completedWeeks, 0)
  assert.ok(model.fruits.every((fruit) => fruit.progress === 0))
})

test('legacy embedded-system radar labels are mapped to TCM dimensions', () => {
  const model = buildLifeTreeModel({
    assessment: {
      labels: ['基础知识', '编程调试', '实验实践', '项目能力', '学习投入', '工程意识'],
      radarScores: [3, 2.8, 3.2, 2.5, 3.8, 2.9],
    },
  })

  assert.deepEqual(
    model.profileDimensions.map((dimension) => dimension.label),
    ['基础知识', '辨证思维', '方药应用', '医案实践', '学习投入', '综合素养'],
  )
})

test('six learning-path fruits use real stage task completion as maturity', () => {
  const model = buildLifeTreeModel({
    profile: { id: 17, profileName: '六周画像', isActive: true },
    pathConfig: {
      meta: { profileReportId: 17, savedAt: '2026-08-29T10:00:00Z' },
      weeks: [
        { id: 'week-1', weekLabel: '第一周', title: '中医基础理论', status: 'completed', enabled: true },
        { id: 'week-2', weekLabel: '第二周', title: '四诊合参', status: 'current', enabled: true },
        { id: 'week-3', weekLabel: '第三周', title: '方剂配伍', status: 'locked', enabled: true },
      ],
      stages: {
        'week-1': { nodes: [{ id: '1', status: 'done' }, { id: '2', status: 'done' }] },
        'week-2': { nodes: [{ id: '1', status: 'done' }, { id: '2', status: 'current' }, { id: '3', status: 'locked' }] },
        'week-3': { nodes: [{ id: '1', status: 'locked' }] },
      },
    },
  })

  const [completed, current, locked, pending] = model.fruits
  assert.equal(model.fruits.length, 6)
  assert.equal(completed.progress, 100)
  assert.equal(completed.growthScale, 1.1)
  assert.equal(current.progress, 33)
  assert.equal(current.status, 'developing')
  assert.equal(current.recommended, true)
  assert.equal(current.action.to, '/learning-path/week/week-2')
  assert.match(current.evidence, /3 个可学习任务/)
  assert.equal(locked.status, 'unverified')
  assert.equal(locked.progress, 0)
  assert.equal(pending.available, false)
  assert.equal(model.stats.completedWeeks, 1)
  assert.equal(model.stats.generatedWeeks, 3)
  assert.equal(model.stats.currentWeekProgress, 33)
  assert.equal(model.stats.overallGrowth, 22.2)
})

test('weekly fruit maturity overlays learner interaction and explicit learning feedback without double counting', () => {
  const model = buildLifeTreeModel({
    profile: { id: 31, profileName: '动态反馈画像', isActive: true },
    pathNodeCaches: {
      'week-2-node-1': {
        cacheKey: 'week-2-node-1',
        stageId: 'week-2',
        nodeId: 'node-1',
        status: 'complete',
        completionSource: 'learning-feedback',
        learningFeedback: { outcome: 'completed' },
        updatedAt: '2026-08-30T08:00:00Z',
      },
      'week-2-node-2': {
        cacheKey: 'week-2-node-2',
        stageId: 'week-2',
        nodeId: 'node-2',
        status: 'complete',
        completionSource: 'resource-generation',
        lastOpenedAt: 1788074521000,
        updatedAt: '2026-08-30T08:05:00Z',
      },
      'week-2-node-3': {
        cacheKey: 'week-2-node-3',
        stageId: 'week-2',
        nodeId: 'node-3',
        status: 'complete',
        lastOpenedAt: 1788074522000,
        learningFeedback: { outcome: 'needs_review' },
        updatedAt: '2026-08-30T08:10:00Z',
      },
    },
    pathConfig: {
      meta: { profileReportId: 31 },
      weeks: [{ id: 'week-2', weekLabel: '第二周', title: '四诊合参', status: 'current', enabled: true }],
      stages: {
        'week-2': {
          nodes: [
            { id: 'node-1', cacheKey: 'week-2-node-1', status: 'done' },
            { id: 'node-2', cacheKey: 'week-2-node-2', status: 'current' },
            { id: 'node-3', cacheKey: 'week-2-node-3', status: 'current' },
          ],
        },
      },
    },
  })

  const fruit = model.fruits[0]
  assert.equal(fruit.progress, 67)
  assert.equal(fruit.completedNodes, 2)
  assert.equal(fruit.pathCompletedNodes, 1)
  assert.equal(fruit.cacheCompletedNodes, 1)
  assert.equal(fruit.feedbackCompletedNodes, 1)
  assert.equal(fruit.preparedNodes, 3)
  assert.equal(fruit.preparedOnlyNodes, 1)
  assert.match(fruit.evidence, /每个路径节点只计一次/)
  assert.match(fruit.evidence, /1 个已提交完成学习反馈/)
  assert.match(fruit.evidence, /1 个节点仅完成后台资源准备/)
  assert.equal(fruit.updatedAt, '2026-08-30T08:10:00Z')
})

test('background resource preparation does not mature fruit before learner activity', () => {
  const model = buildLifeTreeModel({
    pathNodeCaches: {
      prepared_document: {
        cacheKey: 'prepared_document',
        status: 'complete',
        progress: 100,
        resourceType: 'document',
      },
      prepared_mindmap: {
        cacheKey: 'prepared_mindmap',
        status: 'complete',
        progress: 100,
        resourceType: 'mindmap',
      },
    },
    pathConfig: {
      weeks: [{ id: 'week-1', weekLabel: '第一周', status: 'current', enabled: true }],
      stages: {
        'week-1': {
          nodes: [
            { id: '1', cacheKey: 'prepared_document', status: 'current' },
            { id: '2', cacheKey: 'prepared_mindmap', status: 'current' },
          ],
        },
      },
    },
  })

  const fruit = model.fruits[0]
  assert.equal(fruit.progress, 0)
  assert.equal(fruit.completedNodes, 0)
  assert.equal(fruit.preparedNodes, 2)
  assert.equal(fruit.preparedOnlyNodes, 2)
  assert.match(fruit.evidence, /2 个节点仅完成后台资源准备，不计入成熟度/)
})
