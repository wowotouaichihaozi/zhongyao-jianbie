import assert from 'node:assert/strict'
import fs from 'node:fs'
import test from 'node:test'

import {
  clampWorkflowProgress,
  learningPathProgress,
  profileProgress,
  profileStageIndex,
  workflowStatus,
} from '../src/utils/xiaozhiWorkflowProgress.js'

const appSource = fs.readFileSync(new URL('../src/App.vue', import.meta.url), 'utf8')
const cardSource = fs.readFileSync(new URL('../src/components/ResourceTaskStatusBanner.vue', import.meta.url), 'utf8')
const launcherSource = fs.readFileSync(new URL('../src/components/FloatingLogoLauncher.vue', import.meta.url), 'utf8')
const profileSource = fs.readFileSync(new URL('../src/views/LearningProfileView.vue', import.meta.url), 'utf8')
const resourceDetailSource = fs.readFileSync(new URL('../src/views/ResourceDetailView.vue', import.meta.url), 'utf8')
const pathSource = fs.readFileSync(new URL('../src/views/LearningPathView.vue', import.meta.url), 'utf8')
const pptSource = fs.readFileSync(new URL('../src/views/PptGeneratingView.vue', import.meta.url), 'utf8')
const animationSource = fs.readFileSync(new URL('../src/views/LearningAnimationView.vue', import.meta.url), 'utf8')
const apiSource = fs.readFileSync(new URL('../src/services/api.js', import.meta.url), 'utf8')

test('workflow progress is clamped and normalizes server terminal states', () => {
  assert.equal(clampWorkflowProgress(-5), 0)
  assert.equal(clampWorkflowProgress(52.7), 53)
  assert.equal(clampWorkflowProgress(120), 100)
  assert.equal(workflowStatus('done'), 'complete')
  assert.equal(workflowStatus('error'), 'failed')
})

test('profile stages follow real analysis events without timer-driven progress', () => {
  assert.equal(profileStageIndex('load_context'), 0)
  assert.equal(profileStageIndex('retrieve_knowledge'), 1)
  assert.equal(profileStageIndex('quality_review'), 2)
  assert.equal(profileStageIndex('quality_review', true), 3)
  assert.equal(profileProgress({ stage: 'retrieve_knowledge', progress: 41 }), 41)
  assert.equal(profileProgress({ stage: 'quality_review' }), 62)
})

test('learning path progress uses persisted task progress and week counts', () => {
  assert.equal(learningPathProgress({ result: { progress: 47, completedWeeks: 2, totalWeeks: 6 } }), 47)
  assert.equal(learningPathProgress({ result: { completedWeeks: 3, totalWeeks: 6 } }), 50)
  assert.equal(learningPathProgress({ result: { completedWeeks: 6, totalWeeks: 6 } }), 100)
  assert.equal(learningPathProgress({ status: 'complete', result: {} }), 100)
})

test('the assistant mounts exactly one embedded progress card and the app has no separate card', () => {
  const appMounts = appSource.match(/<ResourceTaskStatusBanner/g) || []
  const assistantMounts = launcherSource.match(/<ResourceTaskStatusBanner/g) || []
  assert.equal(appMounts.length, 0)
  assert.equal(assistantMounts.length, 1)
  assert.match(launcherSource, /<ResourceTaskStatusBanner embedded \/>/)
  assert.match(cardSource, /class="xz-workflow-card"/)
  assert.match(cardSource, /\{ embedded \}/)
})

test('profile SSE hands the returned learning-path task to the assistant card', () => {
  assert.match(profileSource, /dispatchXiaoZhiWorkflowProgress\(\{/)
  assert.match(profileSource, /workflow: 'learning-profile'/)
  assert.match(profileSource, /task: data\?\.learningPathTask \|\| null/)
  assert.match(profileSource, /task: result\.learningPathTask/)
})

test('the card persists one active task and polls only its real backend status', () => {
  assert.match(cardSource, /XIAOZHI_WORKFLOW_EVENT/)
  assert.match(cardSource, /sessionStorage\.setItem\(XIAOZHI_ACTIVE_TASK_KEY/)
  assert.match(cardSource, /getXiaoZhiTask\(trackedTaskId\.value\)/)
  assert.match(cardSource, /result\.completedWeeks/)
  assert.match(cardSource, /result\.totalWeeks/)
  assert.match(cardSource, /查看学习路径/)
})

test('a new workflow opens the companion chat and reveals the embedded card once', () => {
  assert.match(launcherSource, /window\.addEventListener\(XIAOZHI_WORKFLOW_EVENT, handleWorkflowCardOpen\)/)
  assert.match(launcherSource, /workflowId === lastWorkflowCardId/)
  assert.match(launcherSource, /activeTab\.value = 'chat'/)
  assert.match(launcherSource, /isOpen\.value = true/)
  assert.doesNotMatch(launcherSource, /handleWorkflowCardOpen[\s\S]{0,320}isOpen\.value = false/)
})

test('task detail pages keep learning content primary and move audit metadata into the assistant card', () => {
  assert.doesNotMatch(resourceDetailSource, /class="evidence-column"/)
  assert.doesNotMatch(resourceDetailSource, /<h2>智能体协作<\/h2>/)
  assert.doesNotMatch(pptSource, /class="progress-band"/)
  assert.doesNotMatch(pptSource, /class="detail-panel"/)
  assert.doesNotMatch(animationSource, /class="task-progress"/)
  assert.doesNotMatch(animationSource, /<h2>知识依据<\/h2>/)
  assert.doesNotMatch(animationSource, /<h2>质量评价<\/h2>/)
  assert.match(animationSource, /<h2>学习检查<\/h2>/)
  assert.match(resourceDetailSource, /dispatchXiaoZhiWorkflowProgress\(\{/)
  assert.match(animationSource, /dispatchXiaoZhiWorkflowProgress\(\{ task \}\)/)
  assert.match(cardSource, /class="audit-drawer"/)
  assert.match(cardSource, /生成依据/)
})

test('weekly task details show one week heading and no duplicate task rail', () => {
  assert.match(pathSource, /eyebrow: ''/)
  assert.match(pathSource, /hasActiveLearningProfile && !isWeekTaskPage/)
  assert.doesNotMatch(pathSource, /\$\{weekLabel\}具体学习任务/)
})

test('the companion shows profile-scoped agent messages as expandable resource cards', () => {
  assert.match(launcherSource, /Map as MapIcon/)
  assert.match(launcherSource, /const grouped = new Map\(\)/)
  assert.doesNotMatch(launcherSource, /learning_path: markRaw\(Map\)/)
  assert.match(launcherSource, /const hiddenAgentIds = computed/)
  assert.match(launcherSource, /@click\.stop="handleOrbClick"/)
  assert.match(launcherSource, /@pointerdown="handlePointerDown"/)
  assert.match(launcherSource, /function handleOrbClick\(\)/)
  assert.doesNotMatch(launcherSource, /@click\.prevent>/)
  assert.doesNotMatch(launcherSource, /const shouldToggle = !pointerState\.moved/)
  assert.doesNotMatch(launcherSource, /<Transition name="motion-panel"/)
  assert.match(launcherSource, /v-else-if="activeTab === 'chat'"/)
  assert.match(launcherSource, /v-else key="status" class="status-panel real-runtime-panel"/)
  assert.match(launcherSource, /response\?\.data\?\.agentConversation/)
  assert.match(launcherSource, /class="agent-group-chat"/)
  assert.match(launcherSource, /toggleConversationGroup\(group\.key\)/)
  assert.match(launcherSource, /class="agent-conversation-details"/)
  assert.match(launcherSource, /class="conversation-resource-link"/)
  assert.match(launcherSource, /entry\.taskId \|\| entry\.runId/)
  assert.match(launcherSource, /data\.agentConversation\) agentConversation\.value = data\.agentConversation/)
  assert.match(launcherSource, /openConversationRoute\(group\)/)
  assert.match(launcherSource, /conversationCitations\(entry\)/)
  assert.match(launcherSource, /waiting: '待用户确认'/)
  assert.doesNotMatch(launcherSource, /findLast\(/)
  assert.match(launcherSource, /chatWithXiaoZhi\(\{ message: displayContent/)
})

test('the companion exposes direct resource commands inside the same group chat composer', () => {
  assert.match(launcherSource, /class="resource-command-strip"/)
  assert.match(launcherSource, /prepareResourceCommand\(command\)/)
  assert.match(launcherSource, /type: 'ppt'/)
  assert.match(launcherSource, /type: 'question_bank'/)
  assert.match(launcherSource, /type: 'generated_video'/)
  assert.match(launcherSource, /type: 'herb_model'/)
})

test('the harness panel renders persisted runs and handoffs instead of a static fake topology', () => {
  assert.match(launcherSource, /response\?\.data\?\.orchestrationRuns/)
  assert.match(launcherSource, /const harnessFlowNodes = computed/)
  assert.match(launcherSource, /class="harness-flow-canvas"/)
  assert.match(launcherSource, /class="harness-node-overlay"/)
  assert.match(launcherSource, /selectedHarnessNodeDetail/)
  assert.match(launcherSource, /selectedRunHandoffs/)
  assert.match(launcherSource, /class="harness-runtime-brief"/)
  assert.match(launcherSource, /没有运行记录，不展示模拟连接关系/)
  assert.doesNotMatch(launcherSource, /class="flow-trunk"/)
  assert.doesNotMatch(launcherSource, /class="specialist-flow-grid"/)
  assert.doesNotMatch(launcherSource, /class="actual-agent-grid"/)
  assert.doesNotMatch(launcherSource, /class="handoff-list"/)
})

test('learning paths stop after week one and expose an explicit next-week action', () => {
  assert.doesNotMatch(pathSource, /generateRemainingWeeks/)
  assert.match(pathSource, /generateNextLearningPathWeek/)
  assert.match(pathSource, /更新画像后再规划/)
  assert.match(apiSource, /\/api\/learning-path\/generate-next-week/)
})
