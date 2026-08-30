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
const nodeCacheSource = fs.readFileSync(new URL('../src/services/learningPathNodeCache.js', import.meta.url), 'utf8')

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

test('a new workflow keeps the companion closed and increments the unread badge once', () => {
  assert.match(launcherSource, /window\.addEventListener\(XIAOZHI_WORKFLOW_EVENT, handleWorkflowCardOpen\)/)
  assert.match(launcherSource, /workflowId === lastWorkflowCardId/)
  assert.match(launcherSource, /if \(!isOpen\.value\) unreadCount\.value \+= 1/)
  assert.doesNotMatch(launcherSource, /handleWorkflowCardOpen[\s\S]{0,320}isOpen\.value = true/)
  assert.match(launcherSource, /if \(opening\) unreadCount\.value = 0/)
  assert.match(launcherSource, /v-if="unreadCount" class="task-dot"/)
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
  assert.match(launcherSource, /v-if="activeTab === 'chat'"/)
  assert.match(launcherSource, /v-else key="status" class="status-panel real-runtime-panel"/)
  assert.doesNotMatch(launcherSource, /<div class="mode-tabs"/)
  assert.match(launcherSource, /response\?\.data\?\.agentConversation/)
  assert.match(launcherSource, /class="agent-group-chat"/)
  assert.match(launcherSource, /class="conversation-handoff-strip"/)
  assert.match(launcherSource, /conversationCollaborationStep/)
  assert.match(launcherSource, /交接给/)
  assert.match(launcherSource, /toggleConversationGroup\(group\.key\)/)
  assert.match(launcherSource, /class="agent-conversation-details"/)
  assert.match(launcherSource, /class="conversation-resource-link"/)
  assert.match(launcherSource, /entry\.taskId \|\| entry\.runId/)
  assert.match(launcherSource, /result\.agentConversation\) agentConversation\.value = result\.agentConversation/)
  assert.match(launcherSource, /openConversationRoute\(group\)/)
  assert.match(launcherSource, /conversationCitations\(entry\)/)
  assert.match(launcherSource, /waiting: '待用户确认'/)
  assert.doesNotMatch(launcherSource, /findLast\(/)
  assert.match(launcherSource, /streamXiaoZhiChat\(\{[\s\S]{0,240}message: displayContent/)
  assert.doesNotMatch(launcherSource, /chatWithXiaoZhi\(\{ message: displayContent/)
})

test('profile switching resets the group chat and stale requests cannot cross profiles', () => {
  assert.match(profileSource, /profile-switch-dialog/)
  assert.match(profileSource, /岐小智群聊记录、学习路径和相关资源会一并切换/)
  assert.match(profileSource, /dispatchXiaoZhiProfileContextChanged\(profile\)/)
  assert.match(launcherSource, /XIAOZHI_PROFILE_CONTEXT_EVENT/)
  assert.match(launcherSource, /activeChatController\?\.abort\(\)/)
  assert.match(launcherSource, /profileRequestEpoch \+= 1/)
  assert.match(launcherSource, /clearProfileAssistantState\(\)/)
  assert.match(launcherSource, /profileReportId: sendProfileReportId/)
  assert.match(launcherSource, /sendEpoch !== profileRequestEpoch/)
})

test('the group composer supports agent mentions, Tab completion, and distinct avatars', () => {
  assert.match(launcherSource, /const mentionableAgents = \[/)
  assert.match(launcherSource, /name: 'PPT生成智能体'/)
  assert.doesNotMatch(launcherSource, /name: '单片机/)
  assert.match(launcherSource, /event\.key === 'Tab'/)
  assert.match(launcherSource, /completeAgentMention\(filteredMentionAgents/)
  assert.match(launcherSource, /class="agent-mention-menu"/)
  assert.match(launcherSource, /@focus="updateMentionContext"/)
  assert.match(launcherSource, /return Boolean\(activeMention\.value && filteredMentionAgents\.value\.length\)/)
  assert.match(launcherSource, /class="composer-highlight-layer"/)
  assert.match(launcherSource, /class="agent-mention-highlight"/)
  assert.match(launcherSource, /function mentionHighlightSegments\(value\)/)
  assert.match(launcherSource, /\.composer textarea\.has-highlight-mirror/)
  assert.match(launcherSource, /\.composer-highlight-content \{[\s\S]{0,300}color: transparent/)
  assert.match(launcherSource, /\.composer-highlight-content \.agent-mention-highlight \{[\s\S]{0,180}-webkit-text-fill-color: transparent/)
  assert.match(launcherSource, /\.composer textarea\.has-highlight-mirror \{[\s\S]{0,180}-webkit-text-fill-color: #213a39/)
  assert.match(launcherSource, /class="message-avatar"/)
  assert.match(launcherSource, /const learnerVisual = \{/)
  assert.match(launcherSource, /icon: markRaw\(UserRound\)/)
  assert.match(launcherSource, /agentAvatarStyle\(entry\.agentId\)/)
  assert.doesNotMatch(launcherSource, /agent\.description/)
  assert.doesNotMatch(launcherSource, /<kbd v-if="index === mentionSelectionIndex">/)
  assert.match(launcherSource, /background: #eef2f0/)
  assert.match(launcherSource, /\.agent-mention-menu \{[\s\S]{0,300}border: 0/)
  assert.doesNotMatch(launcherSource, /filteredMentionAgents[\s\S]{0,260}\.slice\(0, 8\)/)
})

test('expanding an agent conversation card preserves the current scroll position', () => {
  const toggleBody = launcherSource.match(/function toggleConversationGroup\(key\) \{([\s\S]*?)\n\}/)?.[1] || ''
  assert.match(toggleBody, /expandedConversationGroups\.value = next/)
  assert.doesNotMatch(toggleBody, /scrollToBottom/)
})

test('opening the assistant waits for all conversation cards before scrolling to the latest message', () => {
  const openWatch = launcherSource.match(/watch\(isOpen, async \(open\) => \{([\s\S]*?)\n\}\)/)?.[1] || ''
  assert.match(openWatch, /await loadHistory\(\)[\s\S]*await loadStatus\(\)[\s\S]*await scrollToBottom\(\)/)
})

test('conversation cards expose persisted citation counts as well as detailed citation arrays', () => {
  assert.match(launcherSource, /function conversationCitationCount\(entry\)/)
  assert.match(launcherSource, /Number\(payload\.citationCount \|\| 0\)/)
  assert.match(launcherSource, /Number\(details\.citationCount \|\| 0\)/)
  assert.match(launcherSource, /Math\.max\(count, conversationCitationCount\(entry\)\)/)
  assert.match(launcherSource, /function taskQualityEvaluation\(task\)/)
  assert.match(launcherSource, /taskQuality\?\.score \?\? reviewEntry\?\.payload\?\.score/)
  assert.match(launcherSource, /taskCitationCount\(relatedTask\)/)
  assert.match(launcherSource, /conversationCollaborationStep\(entry, taskQuality\?\.score\)/)
  assert.match(launcherSource, /function conversationEntryContent\(entry, group\)/)
  assert.match(launcherSource, /资源质量分 \$\{Number\(group\.qualityScore\)\}/)
})

test('chat uses the signed-in avatar, one streaming bubble, and reloadable server history', () => {
  assert.match(launcherSource, /import \{ readCurrentUser \} from '\.\.\/stores\/auth\.js'/)
  assert.match(launcherSource, /:src="learnerAvatar"/)
  assert.match(launcherSource, /window\.addEventListener\('current-user-change', syncLearnerAvatar\)/)
  assert.match(launcherSource, /if \(message\?\.role === 'user'\) return \{\}/)
  assert.match(launcherSource, /\.message\.user \.message-avatar \{[\s\S]{0,160}background: transparent;/)
  assert.match(launcherSource, /v-else-if="message\.streaming" class="typing-ellipsis"/)
  assert.match(launcherSource, /class="typing-ellipsis"[\s\S]{0,100}<span><\/span><span><\/span><span><\/span>/)
  assert.match(launcherSource, /@keyframes xiaozhiTypingDot/)
  assert.match(launcherSource, /const assistantMessage = reactive\(\{/)
  assert.doesNotMatch(launcherSource, /<article v-if="isSending" class="message assistant pending">/)
  assert.doesNotMatch(launcherSource, /岐小智正在分析你的学习上下文/)
  assert.match(launcherSource, /await loadHistory\(\)/)
})

test('the embedded workflow card clears global task cache when the profile changes', () => {
  assert.match(cardSource, /XIAOZHI_PROFILE_CONTEXT_EVENT/)
  assert.match(cardSource, /function handleProfileContextChanged\(\)/)
  assert.match(cardSource, /sessionStorage\.removeItem\(XIAOZHI_ACTIVE_TASK_KEY\)/)
  assert.match(cardSource, /task\.value = null/)
  assert.doesNotMatch(cardSource, /route\.query\.xzTask \|\| restoredTaskId\(\)/)
})

test('the group chat composer keeps resource shortcuts out of the message field', () => {
  assert.doesNotMatch(launcherSource, /class="resource-command-strip"/)
  assert.doesNotMatch(launcherSource, /class="resource-tool"/)
  assert.doesNotMatch(launcherSource, /sendResourceCommand\(command\)/)
})

test('the harness panel renders persisted runs and handoffs instead of a static fake topology', () => {
  assert.match(launcherSource, /response\?\.data\?\.orchestrationRuns/)
  assert.match(launcherSource, /const harnessFlowNodes = computed/)
  assert.match(launcherSource, /class="harness-flow-canvas"/)
  assert.match(launcherSource, /class="harness-node-overlay"/)
  assert.match(launcherSource, /selectedHarnessNodeDetail/)
  assert.match(launcherSource, /selectedRunHandoffs/)
  assert.match(launcherSource, /class="harness-runtime-brief"/)
  assert.match(launcherSource, /class="harness-loop-rail"/)
  assert.match(launcherSource, /const harnessLoopEdges = computed/)
  assert.match(launcherSource, /质量回退闭环/)
  assert.match(launcherSource, /学习反馈闭环/)
  assert.match(launcherSource, /没有运行记录，不展示模拟连接关系/)
  assert.doesNotMatch(launcherSource, /class="flow-trunk"/)
  assert.doesNotMatch(launcherSource, /class="specialist-flow-grid"/)
  assert.doesNotMatch(launcherSource, /class="actual-agent-grid"/)
  assert.doesNotMatch(launcherSource, /class="handoff-list"/)
})

test('learning paths stop after week one and advance only from task view evidence', () => {
  assert.doesNotMatch(pathSource, /generateRemainingWeeks/)
  assert.doesNotMatch(pathSource, /generateNextLearningPathWeek/)
  assert.match(pathSource, /查看完当前周的全部任务后/)
  assert.match(pathSource, /markNodeCacheViewed\(week\.cacheKey/)
  assert.match(nodeCacheSource, /viewSource: 'learning-path-task-open'/)
})
