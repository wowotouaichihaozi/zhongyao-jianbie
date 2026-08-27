import assert from 'node:assert/strict'
import test from 'node:test'

import {
  createLearningProfileDeveloperFixture,
  isLearningProfileDeveloperShortcut,
  LEARNING_PROFILE_DEVELOPER_DIMENSIONS,
} from '../src/utils/learningProfileDeveloperTools.js'

const expectedDimensions = [
  '专业/课程背景',
  '学习目标',
  '当前知识基础',
  '学习进度',
  '薄弱知识点',
  '易错点类型',
  '学习风格/认知偏好',
  '资源形式偏好',
  '可投入时间',
  '难度接受程度',
]

test('developer fixture fills all ten supported learning-profile dimensions', () => {
  const fixture = createLearningProfileDeveloperFixture(100)

  assert.deepEqual(Object.keys(fixture.dimensions).filter(key => key !== '补充信息'), expectedDimensions)
  expectedDimensions.forEach((key) => {
    const value = fixture.dimensions[key]
    assert.ok(Array.isArray(value) ? value.length : String(value).trim().length, `${key} should be filled`)
  })
  assert.equal(fixture.messages.length, 2)
  assert.equal(fixture.chatHistory.length, 2)
  assert.equal(fixture.scaleScores.length, 6)
})

test('developer fixture returns an independent copy', () => {
  const first = createLearningProfileDeveloperFixture(100)
  first.dimensions['学习目标'].push('临时修改')

  const second = createLearningProfileDeveloperFixture(200)
  assert.deepEqual(second.dimensions['学习目标'], LEARNING_PROFILE_DEVELOPER_DIMENSIONS['学习目标'])
})

test('only plain F4 opens the hidden developer panel', () => {
  assert.equal(isLearningProfileDeveloperShortcut({ key: 'F4' }), true)
  assert.equal(isLearningProfileDeveloperShortcut({ key: 'F4', ctrlKey: true }), false)
  assert.equal(isLearningProfileDeveloperShortcut({ key: 'F4', altKey: true }), false)
  assert.equal(isLearningProfileDeveloperShortcut({ key: 'F5' }), false)
})
