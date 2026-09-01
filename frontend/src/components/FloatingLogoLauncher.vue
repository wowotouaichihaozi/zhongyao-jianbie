<template>
  <div
    class="xiaozhi-float"
    :class="{ dragging: isDragging, open: isOpen }"
    :style="floatStyle"
  >
    <button
      class="xiaozhi-orb"
      type="button"
      :aria-label="isOpen ? '关闭嵌小智' : '打开嵌小智'"
      :aria-expanded="isOpen"
      @pointerdown="handlePointerDown"
      @click.stop="handleOrbClick"
    >
      <picture>
        <source srcset="/logogif-128.webp" type="image/webp" />
        <img class="xiaozhi-orb-logo" src="/logogif.gif" alt="嵌小智" draggable="false" decoding="async" />
      </picture>
      <span class="orb-pulse" aria-hidden="true"></span>
      <span v-if="unreadCount" class="task-dot" :aria-label="`${unreadCount} 条未读动态`">{{ unreadBadgeText }}</span>
    </button>

    <Transition name="motion-pop">
    <section v-if="isOpen" class="xiaozhi-window" :class="[windowPlacement, { wide: activeTab === 'status' }]" :style="windowStyle" @pointerdown.stop>
      <header class="window-head">
        <div class="title-block">
          <strong>嵌小智</strong>
        </div>
        <div class="window-head-actions">
          <button type="button" class="icon-btn" aria-label="关闭嵌小智" @click.stop="isOpen = false">
            <X :size="18" />
          </button>
        </div>
      </header>

      <div v-if="activeTab === 'chat'" key="chat" class="chat-panel">
        <div ref="messageListRef" class="chat-scroll-area">
          <div class="message-list">
          <div v-if="messages.length === 0 && agentConversationGroups.length === 0 && !agentConversation?.summary" class="empty-chat">
            <Sparkles :size="22" />
            <strong>你好，我是嵌小智</strong>
          </div>

          <section
            class="agent-group-chat"
            aria-label="当前学习画像的多智能体群聊"
          >
            <article v-if="agentConversation?.summary" class="agent-conversation-card compacted-history">
              <button type="button" class="agent-conversation-main" @click="toggleConversationGroup('compacted-summary')">
                <span class="agent-conversation-icon"><Archive :size="15" /></span>
                <span class="agent-conversation-copy">
                  <small>自动上下文压缩 · v{{ agentConversation.summaryVersion }}</small>
                  <strong>更早的协作记录已压缩</strong>
                  <em>保留关键结论、任务和知识引用，不再占用完整模型上下文。</em>
                </span>
                <ChevronUp v-if="isConversationGroupExpanded('compacted-summary')" :size="17" />
                <ChevronDown v-else :size="17" />
              </button>
              <div v-if="isConversationGroupExpanded('compacted-summary')" class="agent-conversation-details">
                <p class="conversation-summary-text">{{ agentConversation.summary }}</p>
              </div>
            </article>

            <article
              v-for="group in agentConversationGroups"
              :key="group.key"
              :class="['agent-conversation-card', group.status]"
            >
              <button type="button" class="agent-conversation-main" @click="toggleConversationGroup(group.key)">
                <span class="agent-conversation-icon" :style="agentAvatarStyle(group.primaryAgentId)">
                  <component :is="agentVisual(group.primaryAgentId).icon" :size="15" />
                </span>
                <span class="agent-conversation-copy">
                  <small>{{ group.flowLabel }}</small>
                  <strong>{{ group.collaborationTitle }}</strong>
                  <em>{{ group.summary }}</em>
                  <span class="conversation-handoff-strip" aria-label="协同交接动态">
                    <i
                      v-for="step in group.collaborationSteps"
                      :key="`${group.key}-${step.agent}-${step.text}`"
                      :class="step.status"
                    >
                      <b></b>
                      {{ step.text }}
                    </i>
                  </span>
                  <span class="conversation-card-meta">
                    <i v-if="group.resourceLabel">{{ group.resourceLabel }}</i>
                    <i v-if="group.citationCount">引用 {{ group.citationCount }}</i>
                    <i v-if="group.qualityScore !== null">评分 {{ group.qualityScore }}</i>
                  </span>
                </span>
                <ChevronUp v-if="isConversationGroupExpanded(group.key)" :size="17" />
                <ChevronDown v-else :size="17" />
              </button>

              <i v-if="group.progress > 0" class="agent-conversation-progress" aria-hidden="true">
                <b :style="{ width: `${group.progress}%` }"></b>
              </i>

              <div v-if="isConversationGroupExpanded(group.key)" class="agent-conversation-details">
                <ol>
                  <li v-for="entry in group.messages" :key="entry.id || `${group.key}-${entry.sequence}`">
                    <span
                      class="conversation-entry-avatar"
                      :style="agentAvatarStyle(entry.agentId)"
                      :title="compactAgentName(entry.agentName, entry.agentId)"
                    >
                      <component :is="agentVisual(entry.agentId).icon" :size="13" />
                    </span>
                    <div>
                      <header>
                        <strong>{{ entry.agentName || entry.agentId }}</strong>
                        <time>{{ formatConversationTime(entry.createdAt) }}</time>
                      </header>
                      <p>{{ conversationEntryContent(entry, group) }}</p>
                      <small v-if="conversationDetailText(entry)">{{ conversationDetailText(entry) }}</small>
                      <span v-if="conversationCitations(entry).length" class="conversation-citations">
                        <span v-for="citation in conversationCitations(entry).slice(0, 4)" :key="citation.id || citation.title || citation.excerpt">
                          <strong>{{ citation.title || citation.source || '知识库引用' }}</strong>
                          <small>{{ citation.excerpt || citation.content || citation.snippet }}</small>
                        </span>
                      </span>
                      <span v-if="entry.resourceReferences?.length" class="conversation-references">
                        <i v-for="reference in entry.resourceReferences.slice(0, 6)" :key="`${reference.type}-${reference.id}`">
                          {{ reference.type }} · {{ reference.id }}
                        </i>
                      </span>
                    </div>
                  </li>
                </ol>
                <button
                  v-if="group.route"
                  type="button"
                  class="conversation-resource-link"
                  @click="openConversationRoute(group)"
                >
                  打开对应资源
                  <ExternalLink :size="14" />
                </button>
              </div>
            </article>
          </section>

          <template v-for="(message, index) in messages" :key="`${message.createdAt || index}-${index}`">
            <article class="message" :class="message.role">
              <span
                class="message-avatar"
                :class="{ learner: message.role === 'user' }"
                :style="messageAvatarStyle(message)"
                :title="messageAgentVisual(message).name"
              >
                <img
                  v-if="message.role === 'user'"
                  :src="learnerAvatar"
                  alt="我的头像"
                  @error="resetLearnerAvatar"
                />
                <component v-else :is="messageAgentVisual(message).icon" :size="16" />
              </span>
              <div class="bubble">
                <p v-if="message.content">
                  <template v-for="(segment, segmentIndex) in mentionHighlightSegments(message.content)" :key="`${index}-${segmentIndex}`">
                    <mark v-if="segment.mention" class="agent-mention-highlight">{{ segment.text }}</mark>
                    <template v-else>{{ segment.text }}</template>
                  </template>
                </p>
                <p v-else-if="message.streaming" class="typing-ellipsis" aria-label="正在回复">
                  <span></span><span></span><span></span>
                </p>
                <div v-if="message.attachments?.length" class="message-attachments">
                  <a
                    v-for="attachment in message.attachments"
                    :key="attachment.id || attachment.name"
                    :href="attachment.url || undefined"
                    target="_blank"
                    rel="noopener noreferrer"
                    :title="attachment.name"
                  >
                    <component :is="attachmentIcon(attachment.kind)" :size="14" />
                    <span>{{ attachment.name }}</span>
                  </a>
                </div>
              </div>
            </article>

            <article
              v-for="task in messageTaskPreviews(message)"
              :key="`message-task-${task.taskId}`"
              class="message assistant task-preview-message"
            >
              <a
                :href="resolveRouteHref(taskRoute(task))"
                target="_blank"
                rel="noopener noreferrer"
                :class="['task-preview-bubble', normalizeStatus(task.status)]"
                :aria-label="`新窗口打开任务：${compactTaskTitle(task)}`"
                @click="logTaskOpen(task)"
              >
                <header class="task-preview-head">
                  <span>
                    <component :is="resourceIcon(task.taskType || task.type)" :size="15" />
                    {{ taskTypeLabel(task) }} · {{ statusText(task.status) }}
                  </span>
                  <time>{{ formatTaskTime(task) }}</time>
                </header>
                <span class="task-preview-frame">
                  <iframe
                    :src="taskPreviewUrl(task)"
                    :title="`${compactTaskTitle(task)}任务页面预览`"
                    loading="lazy"
                    referrerpolicy="no-referrer"
                  ></iframe>
                  <span class="task-preview-open"><Maximize2 :size="14" />点开查看</span>
                </span>
                <footer class="task-preview-foot">
                  <strong>{{ compactTaskTitle(task) }}</strong>
                  <span>{{ taskMessage(task) }}</span>
                </footer>
                <i v-if="['queued', 'running'].includes(task.status)" class="companion-task-progress">
                  <b :style="{ width: `${taskProgress(task)}%` }"></b>
                </i>
              </a>
            </article>
          </template>

          <ResourceTaskStatusBanner embedded />

          </div>
        </div>

        <form class="composer" @submit.prevent.stop="sendMessage">
          <div v-if="pendingAttachments.length" class="pending-attachments">
            <span v-for="(file, index) in pendingAttachments" :key="`${file.name}-${file.lastModified}-${index}`">
              <component :is="attachmentIcon(fileKind(file))" :size="14" />
              <b>{{ file.name }}</b>
              <button type="button" :title="`移除 ${file.name}`" @click="removePendingAttachment(index)"><X :size="13" /></button>
            </span>
          </div>
          <input ref="assistantImageInputRef" type="file" accept="image/*" multiple hidden @change="queueAssistantAttachments" />
          <input ref="assistantVideoInputRef" type="file" accept="video/*" multiple hidden @change="queueAssistantAttachments" />
          <input ref="assistantFileInputRef" type="file" accept=".pdf,.doc,.docx,.ppt,.pptx,.txt,.md" multiple hidden @change="queueAssistantAttachments" />
          <div class="composer-editor-shell">
            <div v-if="draft" class="composer-highlight-layer" aria-hidden="true">
              <div class="composer-highlight-content" :style="composerHighlightStyle">
                <template v-for="(segment, index) in composerHighlightSegments" :key="index">
                  <mark v-if="segment.mention" class="agent-mention-highlight">{{ segment.text }}</mark>
                  <template v-else>{{ segment.text }}</template>
                </template>
              </div>
            </div>
            <textarea
              ref="composerInputRef"
              v-model="draft"
              :class="{ 'has-highlight-mirror': Boolean(draft) }"
              rows="2"
              placeholder="输入 @ 选择智能体；不点名时由嵌小智回复"
              @input="updateMentionContext"
              @focus="updateMentionContext"
              @click="updateMentionContext"
              @select="updateMentionContext"
              @scroll="syncComposerScroll"
              @blur="closeMentionMenu"
              @keydown="handleComposerKeydown"
            ></textarea>
          </div>
          <div v-if="mentionMenuOpen" class="agent-mention-menu" role="listbox" aria-label="选择智能体">
            <button
              v-for="(agent, index) in filteredMentionAgents"
              :key="agent.id"
              type="button"
              class="agent-mention-option"
              role="option"
              :aria-selected="index === mentionSelectionIndex"
              :class="{ active: index === mentionSelectionIndex }"
              @mouseenter="mentionSelectionIndex = index"
              @mousedown.prevent="completeAgentMention(agent)"
            >
              <span class="mention-agent-avatar" :style="agentAvatarStyle(agent.id)">
                <component :is="agent.icon" :size="15" />
              </span>
              <strong>{{ agent.name }}</strong>
            </button>
          </div>
          <p v-if="sendError" class="composer-error" role="alert">
            <CircleAlert :size="15" />
            <span>{{ sendError }}</span>
          </p>
          <div class="composer-actions">
            <div class="composer-input-tools">
              <button type="button" class="composer-tool" title="添加图片" aria-label="添加图片" @click="assistantImageInputRef?.click()"><ImagePlus :size="17" /></button>
              <button type="button" class="composer-tool" title="添加视频" aria-label="添加视频" @click="assistantVideoInputRef?.click()"><Video :size="17" /></button>
              <button type="button" class="composer-tool" title="添加文件" aria-label="添加文件" @click="assistantFileInputRef?.click()"><Paperclip :size="17" /></button>
              <button type="button" class="composer-tool" :class="{ active: isListening }" title="语音输入" aria-label="语音输入" @click="toggleVoiceInput"><Mic :size="17" /></button>
            </div>
            <button class="send-btn" type="submit" :disabled="!canSendMessage">
              <LoaderCircle v-if="isSending" :size="17" class="spin" />
              <SendHorizontal v-else :size="17" />
              {{ isSending ? '发送中' : '发送' }}
            </button>
          </div>
        </form>
      </div>

      <div v-else key="status" class="status-panel real-runtime-panel">
        <div class="status-toolbar">
          <div>
            <strong>真实协作记录</strong>
            <p>仅展示 Harness 已保存的实际调用与交接</p>
          </div>
          <button type="button" class="refresh-btn icon-only" title="刷新协作记录" aria-label="刷新协作记录" @click="loadStatus">
            <RefreshCw :size="16" />
          </button>
        </div>

        <div v-if="selectedOrchestrationRun" class="runtime-run-picker">
          <label for="xiaozhi-real-run">查看任务</label>
          <select id="xiaozhi-real-run" v-model="selectedRunId">
            <option v-for="run in realOrchestrationRuns" :key="run.runId" :value="run.runId">
              {{ runOptionLabel(run) }}
            </option>
          </select>
        </div>

        <section class="agent-topology" aria-label="嵌小智真实智能体协作记录">
          <div class="topology-activity">
            <Activity :size="15" />
            <span>{{ harnessActivityText }}</span>
          </div>

          <template v-if="selectedOrchestrationRun">
            <article class="real-run-summary">
              <header>
                <span>{{ runTaskLabel(selectedOrchestrationRun) }}</span>
                <em :class="normalizeStatus(selectedOrchestrationRun.status)">
                  {{ statusText(selectedOrchestrationRun.status) }}
                </em>
              </header>
              <strong>{{ selectedOrchestrationRun.topic || '未命名协作任务' }}</strong>
              <p>
                {{ formatRunTime(selectedOrchestrationRun.updatedAt || selectedOrchestrationRun.createdAt) }}
                <span v-if="selectedOrchestrationRun.harness?.skillId">· {{ selectedOrchestrationRun.harness.skillId }}</span>
              </p>
              <dl>
                <div><dt>实际参与</dt><dd>{{ selectedRunAgents.length }}</dd></div>
                <div><dt>真实交接</dt><dd>{{ selectedRunHandoffs.length }}</dd></div>
                <div><dt>执行事件</dt><dd>{{ selectedOrchestrationRun.eventCount || selectedOrchestrationRun.events?.length || 0 }}</dd></div>
                <div><dt>审核得分</dt><dd>{{ selectedOrchestrationRun.review?.score ?? '--' }}</dd></div>
              </dl>
            </article>

            <section class="harness-flow-section" aria-label="Agent Harness 智能体协作流程">
              <header>
                <strong>真实协作流程</strong>
                <span>点击节点查看详情 · 含审核回退与学习反馈闭环</span>
              </header>

              <div class="harness-flow-canvas" role="list">
                <template v-for="(node, index) in harnessFlowNodes" :key="node.id">
                  <button
                    v-if="index > 0"
                    type="button"
                    class="harness-flow-link"
                    :title="node.edgeLabel || '协作流转'"
                    @click="openHarnessNodeDetail(node.edgeNode)"
                  >
                    <MoveRight v-if="node.edgeDirection !== 'both'" :size="14" />
                    <MoveHorizontal v-else :size="15" />
                    <span>{{ node.edgeLabel }}</span>
                  </button>
                  <button
                    type="button"
                    role="listitem"
                    :class="['harness-flow-node', node.kind, normalizeStatus(node.status), { active: selectedHarnessNodeId === node.id }]"
                    @click="openHarnessNodeDetail(node)"
                  >
                    <span class="harness-node-icon"><component :is="agentIcon(node.agent)" :size="15" /></span>
                    <strong>{{ node.label }}</strong>
                    <small>{{ statusText(node.status) }}</small>
                    <i class="harness-node-light" aria-hidden="true"></i>
                  </button>
                </template>
              </div>

              <div class="harness-loop-rail">
                <button type="button" class="harness-loop-edge review" @click="openHarnessNodeDetail(harnessLoopEdges.reviewRevision.from)">
                  <RotateCcw :size="13" />
                  <span>未通过 · 携带问题回退生成</span>
                </button>
                <button type="button" class="harness-loop-edge assessment" @click="openHarnessNodeDetail(harnessLoopEdges.assessmentFeedback.from)">
                  <RefreshCw :size="13" />
                  <span>评估反馈 · 更新画像后重新调度</span>
                </button>
              </div>
            </section>

            <section class="harness-runtime-brief" aria-label="真实交接摘要">
              <div class="harness-brief-card">
                <strong>真实交接</strong>
                <p>{{ selectedRunHandoffs.length ? selectedRunHandoffs[0].summary || '已完成结构化上下文交接' : '本次运行暂无交接记录' }}</p>
              </div>
              <div class="harness-brief-card">
                <strong>最近产物</strong>
                <p>{{ latestHarnessArtifact || '等待资源生成完成' }}</p>
              </div>
            </section>
          </template>

          <div v-else class="real-run-empty">
            <Network :size="28" />
            <strong>暂无真实协作记录</strong>
            <p>创建一次画像、路径或资源任务后，这里将显示实际参与者和交接关系。</p>
          </div>
        </section>
      </div>
    </section>
    </Transition>
    <Transition name="fade">
      <div v-if="selectedHarnessNodeDetail" class="harness-node-overlay" @click.self="closeHarnessNodeDetail">
        <article class="harness-node-detail" role="dialog" aria-modal="true" :aria-label="selectedHarnessNodeDetail.label">
          <header>
            <span><component :is="agentIcon(selectedHarnessNodeDetail.agent)" :size="17" /></span>
            <div>
              <small>{{ selectedHarnessNodeDetail.stage }}</small>
              <strong>{{ selectedHarnessNodeDetail.label }}</strong>
            </div>
            <button type="button" @click="closeHarnessNodeDetail">
              <X :size="16" />
            </button>
          </header>
          <dl>
            <div><dt>运行状态</dt><dd>{{ statusText(selectedHarnessNodeDetail.status) }}</dd></div>
            <div><dt>运行详情</dt><dd>{{ selectedHarnessNodeDetail.description }}</dd></div>
            <div><dt>执行事件</dt><dd>{{ selectedHarnessNodeDetail.eventCount }} 个</dd></div>
            <div><dt>更新时间</dt><dd>{{ selectedHarnessNodeDetail.time }}</dd></div>
          </dl>
          <div class="harness-node-handoffs">
            <strong>相关交接</strong>
            <p v-for="handoff in selectedHarnessNodeDetail.handoffs" :key="`${handoff.sequence}-${handoff.fromAgent}-${handoff.toAgent}`">
              {{ handoffAgentName(handoff.fromAgent, handoff.fromAgentName) }} → {{ handoffAgentName(handoff.toAgent, handoff.toAgentName) }}
              · {{ handoffArtifactLabel(handoff.artifactType) }}
              <small>{{ handoff.summary }}</small>
            </p>
            <p v-if="!selectedHarnessNodeDetail.handoffs.length" class="empty">本次运行未保存该节点的结构化交接。</p>
          </div>
        </article>
      </div>
    </Transition>
  </div>
</template>

<script setup>
import { computed, markRaw, nextTick, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  Activity,
  Archive,
  ArrowRight,
  BrainCircuit,
  BookOpenCheck,
  ChevronDown,
  ChevronUp,
  CircleAlert,
  ExternalLink,
  FileText,
  Film,
  ImagePlus,
  LoaderCircle,
  Maximize2,
  Map as MapIcon,
  MessageCircle,
  Mic,
  MoveHorizontal,
  MoveRight,
  Network,
  Paperclip,
  Presentation,
  RefreshCw,
  RotateCcw,
  Search,
  SendHorizontal,
  ShieldCheck,
  Sparkles,
  Video,
  UserRound,
  X,
} from 'lucide-vue-next'
import ResourceTaskStatusBanner from './ResourceTaskStatusBanner.vue'
import {
  getXiaoZhiHistory,
  getXiaoZhiStatus,
  logXiaoZhiEvent,
  streamXiaoZhiChat,
  uploadMultimodalInputs,
} from '../services/api.js'
import { useGlobalDebug } from '../stores/globalDebug.js'
import { readCurrentUser } from '../stores/auth.js'
import { XIAOZHI_WORKFLOW_EVENT } from '../utils/xiaozhiWorkflowProgress.js'
import { XIAOZHI_PROFILE_CONTEXT_EVENT } from '../utils/profileContextEvents.js'

const STORAGE_KEY = 'qianxiaozhiFloatingPosition:v2'
const DESKTOP_ORB_SIZE = 66
const MOBILE_ORB_SIZE = 58
const EDGE_PADDING = 16

const router = useRouter()
const route = useRoute()
const { addLog } = useGlobalDebug()

const isOpen = ref(false)
const isDragging = ref(false)
const isSending = ref(false)
const isListening = ref(false)
const activeTab = ref('chat')
const draft = ref('')
const sendError = ref('')
const pendingAttachments = ref([])
const assistantImageInputRef = ref(null)
const assistantVideoInputRef = ref(null)
const assistantFileInputRef = ref(null)
const composerInputRef = ref(null)
const mentionCaretPosition = ref(0)
const mentionSelectionIndex = ref(0)
const activeMention = ref(null)
const composerScroll = reactive({ left: 0, top: 0 })
const messages = ref([])
const agentConversation = ref(null)
const expandedConversationGroups = ref(new Set())
const tasks = ref([])
const agents = ref([])
const orchestrationRuns = ref([])
const selectedRunId = ref('')
const harnessStatus = ref(null)
const messageListRef = ref(null)
const viewport = reactive({ width: window.innerWidth, height: window.innerHeight })
const position = reactive(loadPosition())
let pointerState = null
let statusTimer = null
let recognition = null
let lastWorkflowCardId = ''
let suppressOrbClickUntil = 0
let profileRequestEpoch = 0
let activeChatController = null
const activeProfileReportId = ref(0)
const unreadCount = ref(0)
const pendingTargetAgentId = ref('xiaozhi-companion-agent')
const DEFAULT_USER_AVATAR = '/userlogo.png'
const learnerAvatar = ref(DEFAULT_USER_AVATAR)

const iconMap = {
  learning_background: markRaw(MessageCircle),
  learning_path: markRaw(MapIcon),
  learning_path_stage: markRaw(MapIcon),
  personalized_resources: markRaw(Sparkles),
  ppt: markRaw(Presentation),
  mindmap: markRaw(MapIcon),
  video: markRaw(Search),
  generated_video: markRaw(Film),
  question_bank: markRaw(BookOpenCheck),
  document: markRaw(FileText),
  animation: markRaw(Film),
  profile_update: markRaw(BrainCircuit),
  profile_management: markRaw(BrainCircuit),
  mcu: markRaw(Activity),
  interview: markRaw(Mic),
  smart_tutor: markRaw(BrainCircuit),
  effect_assessment: markRaw(Activity),
  learning_feedback: markRaw(Activity),
  knowledge_base: markRaw(BookOpenCheck),
}

const resourceLabels = {
  learning_background: '学习背景',
  learning_path: '学习路径',
  learning_path_stage: '周任务',
  personalized_resources: '资源工作流',
  ppt: 'PPT 生成',
  mindmap: '思维导图',
  video: '视频查找',
  generated_video: 'AI 视频生成',
  question_bank: '题库生成',
  document: '课程讲义',
  animation: '动画微课',
  profile_update: '学习画像',
  profile_management: '画像管理',
  mcu: '课程讲义',
  interview: '学习访谈',
  smart_tutor: '智能辅导',
  effect_assessment: '效果评估',
  learning_feedback: '学习反馈',
  knowledge_base: '知识库',
}

const handoffArtifactLabels = {
  task_plan: '任务计划',
  learner_context: '学习上下文',
  grounded_knowledge: '知识依据',
  specialist_output: '资源产物',
  revision_request: '修订要求',
  review_result: '审核结论',
  feedback_summary: '反馈摘要',
}

const companionTaskTypes = new Set(
  Object.keys(resourceLabels).filter(type => !['profile_management', 'learning_feedback', 'mcu'].includes(type)),
)

const agentNameAliases = {
  'xiaozhi-companion-agent': '嵌小智总控智能体',
  'learning-background-dialogue-agent': '学习背景采集智能体',
  'learning-profile-agent': '学习画像智能体',
  'learning-route-agent': '学习路径规划智能体',
  'learning-path-stage-agent': '周任务规划智能体',
  'personalized-resource-workflow': '个性化资源调度智能体',
  'question-generator-workflow': '题库生成智能体',
  'ppt-agent': 'PPT 生成智能体',
  'learning-document-agent': '课程讲义智能体',
  'mindmap-agent': '思维导图智能体',
  'video-search-agent': '视频检索智能体',
  'generated-video-agent': 'AI 视频生成智能体',
  'interview-agent': '学习访谈智能体',
  'smart-tutor-agent': '智能辅导智能体',
  'learning-effect-assessment-agent': '效果评估智能体',
  'private-knowledge-agent': '私有知识库智能体',
  'learner-context-agent': '学习上下文智能体',
  'course-knowledge-retrieval-agent': '课程知识检索智能体',
  'skill-registry-agent': 'Skill 注册智能体',
  'mcp-tool-gateway': 'MCP 工具网关',
  'quality-review-agent': '质量审核智能体',
  'content-safety-agent': '内容安全智能体',
  'learning-feedback-agent': '学习反馈智能体',
  'qwen-multimodal-evidence-agent': '多模态证据智能体',
  'document-text-extraction-agent': '文档解析智能体',
  'spark-text-reasoning-agent': '文本推理智能体',
}

const mentionableAgents = [
  { id: 'xiaozhi-companion-agent', name: '嵌小智', taskType: '', icon: markRaw(Sparkles), color: '#17684f', background: '#dcece5' },
  { id: 'learning-background-dialogue-agent', name: '学习背景智能体', taskType: 'learning_background', icon: markRaw(MessageCircle), color: '#3b6f9b', background: '#dce8f0' },
  { id: 'learning-profile-agent', name: '学习画像智能体', taskType: 'profile_update', icon: markRaw(BrainCircuit), color: '#7a5c9e', background: '#e8e1ef' },
  { id: 'learning-route-agent', name: '学习路径智能体', taskType: 'learning_path', icon: markRaw(MapIcon), color: '#9a672f', background: '#eee4d5' },
  { id: 'learning-path-stage-agent', name: '周任务规划智能体', taskType: 'learning_path_stage', icon: markRaw(MoveRight), color: '#397965', background: '#dcece6' },
  { id: 'personalized-resource-workflow', name: '个性化资源智能体', taskType: 'personalized_resources', icon: markRaw(Network), color: '#386d87', background: '#dce9ee' },
  { id: 'question-generator-workflow', name: '题库生成智能体', taskType: 'question_bank', icon: markRaw(BookOpenCheck), color: '#946338', background: '#efe3d8' },
  { id: 'ppt-agent', name: 'PPT生成智能体', taskType: 'ppt', icon: markRaw(Presentation), color: '#a14f52', background: '#f0dddd' },
  { id: 'learning-document-agent', name: '课程讲义智能体', taskType: 'document', icon: markRaw(FileText), color: '#586f43', background: '#e4eadc' },
  { id: 'mindmap-agent', name: '思维导图智能体', taskType: 'mindmap', icon: markRaw(Network), color: '#75649a', background: '#e6e1ef' },
  { id: 'video-search-agent', name: '视频检索智能体', taskType: 'video', icon: markRaw(Search), color: '#3e7194', background: '#dce8ef' },
  { id: 'generated-video-agent', name: 'AI视频生成智能体', taskType: 'generated_video', icon: markRaw(Film), color: '#9b5d73', background: '#eedde3' },
  { id: 'interview-agent', name: '学习访谈智能体', taskType: 'interview', icon: markRaw(Mic), color: '#47796f', background: '#dceae6' },
  { id: 'smart-tutor-agent', name: '智能辅导智能体', taskType: 'smart_tutor', icon: markRaw(BrainCircuit), color: '#6b659d', background: '#e4e2ef' },
  { id: 'learning-effect-assessment-agent', name: '效果评估智能体', taskType: 'effect_assessment', icon: markRaw(Activity), color: '#9a6a35', background: '#eee4d6' },
  { id: 'learning-feedback-agent', name: '学习反馈智能体', taskType: 'learning_feedback', icon: markRaw(RefreshCw), color: '#447b58', background: '#dce9df' },
  { id: 'private-knowledge-agent', name: '私有知识库智能体', taskType: 'knowledge_base', icon: markRaw(Archive), color: '#4e6b85', background: '#dfe6ec' },
]

const agentVisualsById = new Map(mentionableAgents.map(agent => [agent.id, agent]))
const mentionAgentNamePattern = mentionableAgents
  .map(agent => agent.name)
  .sort((left, right) => right.length - left.length)
  .map(name => name.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'))
  .join('|')
const mentionTokenPattern = new RegExp(`@(?:${mentionAgentNamePattern})(?=$|[\\s，,。：:；;！？!?])`, 'g')
const learnerVisual = {
  id: 'learner',
  name: '我',
  icon: markRaw(UserRound),
  color: '#ffffff',
  background: '#17684f',
}

function normalizeLearnerAvatar(value) {
  const avatar = String(value || '').trim()
  if (!avatar || avatar.startsWith('data:image/svg+xml')) return DEFAULT_USER_AVATAR
  return avatar
}

function syncLearnerAvatar() {
  const user = readCurrentUser()
  learnerAvatar.value = normalizeLearnerAvatar(user.avatar || user.avatarUrl)
}

function resetLearnerAvatar() {
  learnerAvatar.value = DEFAULT_USER_AVATAR
}

function agentVisual(agentId) {
  return agentVisualsById.get(String(agentId || '')) || mentionableAgents[0]
}

function agentAvatarStyle(agentId) {
  const visual = agentVisual(agentId)
  return { color: visual.color, background: visual.background }
}

function messageAgentVisual(message) {
  if (message?.role === 'user') return learnerVisual
  const target = message?.targetAgent || message?.intent?.targetAgent || {}
  return agentVisual(target.id)
}

function messageAvatarStyle(message) {
  if (message?.role === 'user') return {}
  const visual = messageAgentVisual(message)
  return { color: visual.color, background: visual.background }
}

const floatStyle = computed(() => ({
  left: `${position.x}px`,
  top: `${position.y}px`,
}))

const windowPlacement = computed(() => {
  const nearRight = position.x > viewport.width - 480
  const nearBottom = position.y > viewport.height - 560
  return {
    left: nearRight,
    right: !nearRight,
    up: nearBottom,
    down: !nearBottom,
  }
})

const windowStyle = computed(() => {
  if (viewport.width <= 768) return {}

  const viewportPadding = 16
  const orbGap = 18
  const size = orbSize()
  const isStatusTab = activeTab.value === 'status'
  const width = Math.max(1, Math.min(isStatusTab ? 820 : 440, viewport.width - viewportPadding * 2))
  const height = Math.max(1, Math.min(isStatusTab ? 520 : 660, viewport.height - viewportPadding * 2))
  const opensLeft = windowPlacement.value.left
  const opensUp = windowPlacement.value.up

  const preferredLeft = opensLeft
    ? position.x - width - orbGap
    : position.x + size + orbGap
  const preferredTop = opensUp
    ? position.y + size - height
    : position.y

  const clamp = (value, min, max) => Math.max(min, Math.min(max, value))

  return {
    position: 'fixed',
    left: `${clamp(preferredLeft, viewportPadding, viewport.width - width - viewportPadding)}px`,
    top: `${clamp(preferredTop, viewportPadding, viewport.height - height - viewportPadding)}px`,
    right: 'auto',
    bottom: 'auto',
    width: `${width}px`,
    height: `${height}px`,
    maxHeight: `${height}px`,
  }
})

const runningTaskCount = computed(() => tasks.value.filter(task => ['queued', 'running'].includes(task.status)).length)
const unreadBadgeText = computed(() => unreadCount.value > 99 ? '99+' : String(unreadCount.value))
const canSendMessage = computed(() => !isSending.value && Boolean(draft.value.trim() || pendingAttachments.value.length))
const filteredMentionAgents = computed(() => {
  if (!activeMention.value) return []
  const query = activeMention.value.query
  return mentionableAgents
    .filter(agent => !query || `${agent.name} ${agent.taskType}`.toLowerCase().includes(query))
})
const mentionMenuOpen = computed(() => {
  return Boolean(activeMention.value && filteredMentionAgents.value.length)
})
const composerHighlightSegments = computed(() => mentionHighlightSegments(draft.value))
const composerHighlightStyle = computed(() => ({
  transform: `translate(${-composerScroll.left}px, ${-composerScroll.top}px)`,
}))
const hiddenAgentIds = computed(() => new Set(
  agents.value.filter(agent => agent.hidden).map(agent => String(agent.id || '')),
))
const realOrchestrationRuns = computed(() => orchestrationRuns.value.filter(run => (
  run?.runId
  && (
    (Array.isArray(run.agentRuns) && run.agentRuns.length)
    || (Array.isArray(run.handoffs) && run.handoffs.length)
    || (Array.isArray(run.events) && run.events.length)
  )
)))
const selectedHarnessNodeId = ref('')
const selectedOrchestrationRun = computed(() => (
  realOrchestrationRuns.value.find(run => run.runId === selectedRunId.value)
  || realOrchestrationRuns.value[0]
  || null
))
const selectedRunAgents = computed(() => {
  const unique = new Map()
  for (const agent of selectedOrchestrationRun.value?.agentRuns || []) {
    const agentId = String(agent?.id || '').trim()
    if (!agentId || hiddenAgentIds.value.has(agentId)) continue
    unique.set(agentId, agent)
  }
  return Array.from(unique.values())
})
const selectedRunHandoffs = computed(() => (
  (selectedOrchestrationRun.value?.handoffs || []).filter(handoff => (
    handoff?.fromAgent
    && handoff?.toAgent
    && !hiddenAgentIds.value.has(String(handoff.fromAgent))
    && !hiddenAgentIds.value.has(String(handoff.toAgent))
  ))
))
const harnessActivityText = computed(() => {
  const run = selectedOrchestrationRun.value
  if (!run) return '没有运行记录，不展示模拟连接关系'
  const taskLabel = runTaskLabel(run)
  if (['running', 'queued'].includes(run.status)) return `${taskLabel}正在由 ${selectedRunAgents.value.length} 个智能体协作执行`
  if (run.status === 'failed') return `${taskLabel}执行失败，以下记录来自真实运行链路`
  return `${taskLabel}已完成，以下为本次真实调用与交接`
})
const harnessFlowNodes = computed(() => {
  const run = selectedOrchestrationRun.value
  if (!run) return []
  const runAgentMap = new Map(selectedRunAgents.value.map(agent => [String(agent.id), agent]))
  const definitions = [
    { id: 'user', label: '用户', kind: 'actor', stage: '学习起点', role: '发起学习请求与反馈' },
    { id: 'learning-profile-agent', label: '学习画像智能体', kind: 'stage', stage: '画像构建', role: '整合采集信息与历史证据' },
    { id: 'xiaozhi-companion-agent', label: '嵌小智总控智能体', kind: 'master', stage: '总控调度', role: '拆解任务并分发专家智能体' },
    { id: 'learning-route-agent', label: '学习路径智能体', kind: 'stage', stage: '路径规划', role: '规划周目标与阶段任务' },
    { id: 'personalized-resource-workflow', label: '资源生成智能体', kind: 'generate', stage: '资源生成', role: '生成题库、课件、导图、视频与单片机实验资源' },
    { id: 'quality-review-agent', label: '质量审核智能体', kind: 'review', stage: '质量审核', role: '校验引用、结构与内容安全' },
    { id: 'learning-effect-assessment-agent', label: '效果评估智能体', kind: 'stage', stage: '效果评估', role: '汇总学习结果与薄弱点' },
  ]
  const edgeLabels = ['', '发起', '画像上下文', '路径调度', '周任务', '调用知识', '审核结论', '学习反馈']
  const nodes = definitions.map((definition, index) => {
    const agent = runAgentMap.get(definition.id) || agents.value.find(item => String(item.id) === definition.id)
      || { id: definition.id, name: definition.label, status: 'idle' }
    const status = runAgentMap.has(definition.id) ? normalizeStatus(agent.status) : 'idle'
    return {
      ...definition,
      agent,
      status,
      eventCount: Number(agent?.eventCount || 0),
      description: runAgentMap.has(definition.id) ? actualAgentDetail(agent) : definition.role,
      time: formatRunTime(agent?.lastRunAt || run.updatedAt || run.createdAt),
      edgeLabel: edgeLabels[index] || '协作',
      edgeDirection: index === 5 ? 'both' : 'forward',
      edgeNode: null,
    }
  })
  nodes.forEach((node, index) => {
    if (index > 0) node.edgeNode = nodes[index - 1]
  })
  return nodes
})
const harnessLoopEdges = computed(() => ({
  reviewRevision: {
    from: harnessFlowNodes.value.find(node => node.id === 'quality-review-agent') || null,
    to: harnessFlowNodes.value.find(node => node.id === 'personalized-resource-workflow') || null,
    label: '质量回退闭环',
    detail: selectedRunHandoffs.value.some(handoff => handoff.artifactType === 'revision_request')
      ? '本次已保存审核修订交接，未通过内容会携带问题回退资源生成。'
      : '审核未通过时，质量审核智能体会携带问题回退资源生成智能体重新处理。',
  },
  assessmentFeedback: {
    from: harnessFlowNodes.value.find(node => node.id === 'learning-effect-assessment-agent') || null,
    to: harnessFlowNodes.value.find(node => node.id === 'xiaozhi-companion-agent') || null,
    label: '学习反馈闭环',
    detail: selectedRunHandoffs.value.some(handoff => ['feedback_summary', 'learner_context'].includes(handoff.artifactType))
      ? '本次已保存学习反馈/上下文交接，评估结论会更新画像并进入下一轮调度。'
      : '学习完成后，效果评估智能体会把成绩、行为与薄弱点写回画像，再由总控智能体调整后续任务。',
  },
}))
const latestHarnessArtifact = computed(() => {
  for (const handoff of [...selectedRunHandoffs.value].reverse()) {
    if (handoff.artifactType) return handoffArtifactLabel(handoff.artifactType)
  }
  return harnessFlowNodes.value.find(node => node.id === 'personalized-resource-workflow')?.agent?.detail || ''
})
const selectedHarnessNodeDetail = computed(() => {
  if (!selectedOrchestrationRun.value || !selectedHarnessNodeId.value) return null
  const node = harnessFlowNodes.value.find(item => item.id === selectedHarnessNodeId.value)
  if (!node) return null
  const handoffs = selectedRunHandoffs.value.filter(handoff => (
    String(handoff.fromAgent) === node.id || String(handoff.toAgent) === node.id
  ))
  return {
    ...node,
    handoffs,
    description: node.id === 'user'
      ? (selectedOrchestrationRun.value.topic || '用户发起了本次学习协作')
      : node.description,
    time: node.id === 'user'
      ? formatRunTime(selectedOrchestrationRun.value.updatedAt || selectedOrchestrationRun.value.createdAt)
      : node.time,
  }
})
const agentConversationGroups = computed(() => {
  const recentMessages = Array.isArray(agentConversation.value?.recentMessages)
    ? agentConversation.value.recentMessages
    : []
  const grouped = new Map()
  for (const entry of recentMessages) {
    if (!entry || ['user_message', 'supervisor_reply'].includes(String(entry.type || ''))) continue
    const key = String(entry.taskId || entry.runId || `message-${entry.id || entry.sequence}`)
    if (!grouped.has(key)) {
      grouped.set(key, {
        key,
        runId: String(entry.runId || ''),
        taskId: String(entry.taskId || ''),
        messages: [],
      })
    }
    grouped.get(key).messages.push(entry)
  }
  return Array.from(grouped.values()).slice(-10).map((group) => {
    const relatedTaskId = group.taskId || group.messages
      .flatMap(entry => Array.isArray(entry.resourceReferences) ? entry.resourceReferences : [])
      .find(reference => reference?.type === 'task')?.id || ''
    const relatedTask = tasks.value.find(task => String(task.taskId || '') === String(relatedTaskId))
    const latestStatus = String([...group.messages].reverse().find(entry => entry.status)?.status || '')
    const runtimeStatus = String(relatedTask?.status || latestStatus)
    const statusSource = ['failed', 'error', 'needs_attention'].includes(latestStatus)
      ? latestStatus
      : runtimeStatus
    const status = ['failed', 'error', 'needs_attention'].includes(statusSource)
      ? 'failed'
      : ['running', 'queued'].includes(statusSource)
        ? 'running'
        : ['waiting', 'waiting_for_user'].includes(statusSource)
          ? 'waiting'
          : ['warning', 'needs-verification'].includes(statusSource) ? 'warning' : 'complete'
    const progress = Math.max(
      0,
      ...group.messages.map(entry => Number(entry.payload?.progress || entry.payload?.details?.progress || 0)),
    )
    const names = Array.from(new Set(group.messages.map(entry => entry.agentName || entry.agentId).filter(Boolean)))
    const routeReference = group.messages
      .flatMap(entry => Array.isArray(entry.resourceReferences) ? entry.resourceReferences : [])
      .find(reference => reference?.type === 'route')
    const lastMessage = group.messages.at(-1) || {}
    const reviewEntry = [...group.messages].reverse().find(entry => entry.type === 'review')
    const taskQuality = taskQualityEvaluation(relatedTask)
    const qualityScoreValue = Number(taskQuality?.score ?? reviewEntry?.payload?.score)
    const resourceType = String(
      relatedTask?.taskType
      || group.messages.find(entry => entry.payload?.resourceType)?.payload?.resourceType
      || '',
    )
    const citationCount = group.messages.reduce(
      (count, entry) => Math.max(count, conversationCitationCount(entry)),
      taskCitationCount(relatedTask),
    )
    const collaborationSteps = group.messages
      .map(entry => conversationCollaborationStep(entry, taskQuality?.score))
      .filter(Boolean)
      .slice(-3)
    const baseTitle = relatedTask?.title
      || group.messages.find(entry => entry.payload?.title)?.payload?.title
      || group.messages.find(entry => entry.type === 'review')?.content
      || lastMessage.content
      || '智能体协同任务'
    return {
      ...group,
      primaryAgentId: String(lastMessage.agentId || 'xiaozhi-companion-agent'),
      status,
      progress,
      agentNames: names.slice(0, 2).join('、') + (names.length > 2 ? ` 等 ${names.length} 个智能体` : ''),
      flowLabel: `${names.length ? `${names.length} 个智能体协同` : '多智能体协同'} · ${conversationStatusLabel(status)}`,
      title: baseTitle,
      collaborationTitle: collaborationSteps.at(-1)?.text || conciseConversationText(baseTitle, 36),
      summary: conversationGroupSummary(group.messages, relatedTask),
      collaborationSteps,
      route: relatedTask?.route || routeReference?.id || '',
      resourceType,
      resourceLabel: resourceLabels[resourceType] || '',
      citationCount,
      qualityScore: Number.isFinite(qualityScoreValue) ? qualityScoreValue : null,
    }
  })
})

watch(isOpen, async (open) => {
  if (!open) {
    stopStatusPolling()
    return
  }
  await loadHistory()
  await loadStatus()
  await scrollToBottom()
  startStatusPolling()
})

watch(activeTab, (tab) => {
  if (tab === 'status') {
    loadStatus()
  }
})

function resourceIcon(type) {
  return iconMap[type] || FileText
}

function orbSize() {
  return window.innerWidth <= 768 ? MOBILE_ORB_SIZE : DESKTOP_ORB_SIZE
}

function bottomReserve() {
  return window.innerWidth <= 768 ? 110 : 32
}

function defaultPosition() {
  const size = orbSize()
  return {
    x: Math.max(EDGE_PADDING, window.innerWidth - size - 32),
    y: Math.max(EDGE_PADDING, window.innerHeight - size - bottomReserve()),
  }
}

function loadPosition() {
  try {
    const saved = JSON.parse(localStorage.getItem(STORAGE_KEY) || 'null')
    if (saved && Number.isFinite(saved.x) && Number.isFinite(saved.y)) {
      return clampPosition(saved)
    }
  } catch {
    // Ignore broken persisted state.
  }
  return defaultPosition()
}

function clampPosition(next) {
  const size = orbSize()
  return {
    x: Math.min(Math.max(EDGE_PADDING, next.x), Math.max(EDGE_PADDING, window.innerWidth - size - EDGE_PADDING)),
    y: Math.min(Math.max(EDGE_PADDING, next.y), Math.max(EDGE_PADDING, window.innerHeight - size - bottomReserve())),
  }
}

function persistPosition() {
  localStorage.setItem(STORAGE_KEY, JSON.stringify({ x: position.x, y: position.y }))
}

function handlePointerDown(event) {
  if (event.button !== 0) return
  pointerState = {
    id: event.pointerId,
    startX: event.clientX,
    startY: event.clientY,
    originX: position.x,
    originY: position.y,
    moved: false,
  }
  event.currentTarget.setPointerCapture?.(event.pointerId)
  window.addEventListener('pointermove', handlePointerMove)
  window.addEventListener('pointerup', handlePointerUp)
  window.addEventListener('pointercancel', handlePointerCancel)
}

function handlePointerMove(event) {
  if (!pointerState || event.pointerId !== pointerState.id) return
  const dx = event.clientX - pointerState.startX
  const dy = event.clientY - pointerState.startY
  if (Math.hypot(dx, dy) > 4) {
    pointerState.moved = true
    isDragging.value = true
  }
  const next = clampPosition({
    x: pointerState.originX + dx,
    y: pointerState.originY + dy,
  })
  position.x = next.x
  position.y = next.y
}

function handlePointerUp(event) {
  if (!pointerState || event.pointerId !== pointerState.id) return
  const moved = pointerState.moved
  pointerState = null
  isDragging.value = false
  persistPosition()
  removePointerListeners()
  if (moved) suppressOrbClickUntil = Date.now() + 250
}

function handlePointerCancel(event) {
  if (!pointerState || event.pointerId !== pointerState.id) return
  pointerState = null
  isDragging.value = false
  removePointerListeners()
}

function removePointerListeners() {
  window.removeEventListener('pointermove', handlePointerMove)
  window.removeEventListener('pointerup', handlePointerUp)
  window.removeEventListener('pointercancel', handlePointerCancel)
}

function handleOrbClick() {
  if (Date.now() < suppressOrbClickUntil) return
  activeTab.value = 'chat'
  const opening = !isOpen.value
  isOpen.value = opening
  if (opening) unreadCount.value = 0
}

function handleResize() {
  viewport.width = window.innerWidth
  viewport.height = window.innerHeight
  const next = clampPosition(position)
  position.x = next.x
  position.y = next.y
  persistPosition()
}

function handleWorkflowCardOpen(event) {
  const workflowId = String(event?.detail?.workflowId || event?.detail?.task?.taskId || '')
  if (!workflowId || workflowId === lastWorkflowCardId) return
  lastWorkflowCardId = workflowId
  if (!isOpen.value) unreadCount.value += 1
}

function acceptsProfileResponse(response, requestEpoch) {
  if (requestEpoch !== profileRequestEpoch) return false
  const responseProfileId = Number(response?.data?.profileReportId || 0)
  if (!activeProfileReportId.value && responseProfileId) {
    activeProfileReportId.value = responseProfileId
  }
  return responseProfileId === Number(activeProfileReportId.value || 0)
}

function clearProfileAssistantState() {
  messages.value = []
  tasks.value = []
  agents.value = []
  agentConversation.value = null
  orchestrationRuns.value = []
  selectedRunId.value = ''
  selectedHarnessNodeId.value = ''
  expandedConversationGroups.value = new Set()
  harnessStatus.value = null
  sendError.value = ''
  unreadCount.value = 0
}

async function handleProfileContextChanged(event) {
  activeChatController?.abort()
  activeChatController = null
  profileRequestEpoch += 1
  activeProfileReportId.value = Number(event?.detail?.profileReportId || 0)
  isSending.value = false
  pendingTargetAgentId.value = 'xiaozhi-companion-agent'
  clearProfileAssistantState()
  await Promise.all([loadHistory(), loadStatus()])
  if (isOpen.value) await scrollToBottom()
}

async function loadHistory() {
  const requestEpoch = profileRequestEpoch
  try {
    const response = await getXiaoZhiHistory()
    if (!acceptsProfileResponse(response, requestEpoch)) return
    messages.value = response?.data?.messages || []
    tasks.value = response?.data?.tasks || []
    agentConversation.value = response?.data?.agentConversation || agentConversation.value
    await scrollToBottom()
  } catch (error) {
    addLog(error?.message || '嵌小智历史加载失败', 'warn', '嵌小智')
  }
}

async function loadStatus() {
  const requestEpoch = profileRequestEpoch
  try {
    const response = await getXiaoZhiStatus()
    if (!acceptsProfileResponse(response, requestEpoch)) return
    agents.value = response?.data?.agents || []
    tasks.value = response?.data?.tasks || tasks.value
    harnessStatus.value = response?.data?.architecture || null
    orchestrationRuns.value = Array.isArray(response?.data?.orchestrationRuns)
      ? response.data.orchestrationRuns
      : []
    if (!orchestrationRuns.value.some(run => run?.runId === selectedRunId.value)) {
      selectedRunId.value = orchestrationRuns.value[0]?.runId || ''
    }
    agentConversation.value = response?.data?.agentConversation || agentConversation.value
    if (statusTimer && !isOpen.value && !runningTaskCount.value) {
      stopStatusPolling()
    }
  } catch (error) {
    addLog(error?.message || '嵌小智状态加载失败', 'warn', '嵌小智')
  }
}

function toggleConversationGroup(key) {
  const next = new Set(expandedConversationGroups.value)
  if (next.has(key)) next.delete(key)
  else next.add(key)
  expandedConversationGroups.value = next
}

function isConversationGroupExpanded(key) {
  return expandedConversationGroups.value.has(key)
}

function conversationStatusLabel(status) {
  return {
    running: '协同中',
    waiting: '待用户确认',
    failed: '需处理',
    warning: '待核验',
    complete: '已完成',
  }[status] || '已记录'
}

function compactAgentName(value, fallbackId = '') {
  const raw = String(value || fallbackId || '').trim()
  if (!raw) return '智能体'
  const alias = agentNameAliases[raw]
  const normalized = alias || raw
  const englishMap = {
    'Quality Review Agent': '质量审核智能体',
    'Skill Registry': 'Skill 注册智能体',
    'MCP Tool Gateway': 'MCP 工具网关',
  }
  return englishMap[normalized] || normalized
}

function handoffActionText(targetName, artifactType) {
  const target = String(targetName || '')
  const artifact = String(artifactType || '')
  if (target.includes('学习路径')) return '规划任务'
  if (target.includes('PPT')) return '生成课件'
  if (target.includes('题库')) return '生成题库'
  if (target.includes('导图')) return '生成导图'
  if (target.includes('视频')) return '生成视频'
  if (target.includes('审核') || artifact === 'review_result') return '审核质量'
  if (target.includes('知识') || artifact === 'grounded_knowledge') return '补充知识依据'
  if (target.includes('总控')) return '重新调度'
  return '继续处理'
}

function runningActionText(entry) {
  const payload = entry?.payload && typeof entry.payload === 'object' ? entry.payload : {}
  const stage = String(payload.stage || payload.details?.stage || entry?.content || '').trim()
  const agent = compactAgentName(entry?.agentName, entry?.agentId)
  if (stage.includes('retrieve') || stage.includes('检索')) return `${agent}正在检索知识库`
  if (stage.includes('review') || stage.includes('审核')) return `${agent}正在核验内容质量`
  if (stage.includes('path') || stage.includes('路径')) return `${agent}正在规划学习任务`
  if (stage.includes('profile') || stage.includes('画像')) return `${agent}正在更新学习画像`
  if (stage.includes('resource') || stage.includes('生成')) return `${agent}正在生成学习资源`
  return `${agent}正在协同处理`
}

function conversationCollaborationStep(entry, qualityScoreOverride = null) {
  if (!entry) return null
  const payload = entry.payload && typeof entry.payload === 'object' ? entry.payload : {}
  const status = normalizeStatus(entry.status)
  if (entry.type === 'handoff') {
    const from = compactAgentName(entry.agentName, entry.agentId)
    const to = compactAgentName(payload.toAgentName, payload.toAgent)
    return {
      agent: from,
      status: 'complete',
      text: `${from}已完成，交接给${to}${handoffActionText(to, payload.artifactType)}`,
    }
  }
  if (entry.type === 'review') {
    const persistedScore = Number(payload.score)
    const overrideScore = Number(qualityScoreOverride)
    const hasOverride = qualityScoreOverride !== null && qualityScoreOverride !== undefined && qualityScoreOverride !== ''
    const score = hasOverride && Number.isFinite(overrideScore) ? overrideScore : persistedScore
    const passed = payload.passed !== false && !['failed', 'needs_attention'].includes(String(entry.status || ''))
    return {
      agent: '质量审核智能体',
      status: passed ? 'complete' : 'warning',
      text: Number.isFinite(score)
        ? `质量审核智能体${passed ? '已通过' : '要求修改'}，评分 ${score}`
        : `质量审核智能体${passed ? '已通过' : '要求修改'}`,
    }
  }
  if (['running', 'queued'].includes(status)) {
    return {
      agent: compactAgentName(entry.agentName, entry.agentId),
      status: 'running',
      text: runningActionText(entry),
    }
  }
  const agent = compactAgentName(entry.agentName, entry.agentId)
  const text = String(entry.content || '').trim()
  return {
    agent,
    status: status === 'failed' ? 'failed' : 'complete',
    text: text ? `${agent}已完成：${conciseConversationText(text, 24)}` : `${agent}已完成协同处理`,
  }
}

function conversationEntryContent(entry, group) {
  if (entry?.type !== 'review' || !Number.isFinite(Number(group?.qualityScore))) {
    return entry?.content || ''
  }
  const passed = entry?.payload?.passed !== false && group?.status !== 'failed'
  return `审核完成，资源质量分 ${Number(group.qualityScore)}，${passed ? '已通过' : '需要继续处理'}。`
}

function conversationGroupSummary(messages, relatedTask) {
  const taskLabel = relatedTask?.title ? `产物：${relatedTask.title}` : ''
  const latest = messages.at(-1)
  const latestStep = conversationCollaborationStep(latest)
  return conciseConversationText(taskLabel || latestStep?.text || latest?.content || '协同记录已更新', 42)
}

function conciseConversationText(value, maxLength = 42) {
  const text = String(value || '').replace(/\s+/g, ' ').trim()
  return text.length > maxLength ? `${text.slice(0, maxLength)}...` : text
}

function formatConversationTime(value) {
  if (!value) return ''
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return ''
  return date.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
}

function conversationDetailText(entry) {
  const payload = entry?.payload && typeof entry.payload === 'object' ? entry.payload : {}
  const parts = []
  if (payload.stage) parts.push(`阶段：${payload.stage}`)
  if (Number.isFinite(Number(payload.progress)) && Number(payload.progress) > 0) parts.push(`进度：${Number(payload.progress)}%`)
  if (payload.artifactType) parts.push(`交接物：${payload.artifactType}`)
  if (payload.toAgentName) parts.push(`交给：${payload.toAgentName}`)
  const details = payload.details && typeof payload.details === 'object' ? payload.details : {}
  const citationCount = conversationCitationCount(entry)
  if (citationCount) parts.push(`知识引用：${citationCount} 条`)
  return parts.join(' · ')
}

function conversationCitationCount(entry) {
  const payload = entry?.payload && typeof entry.payload === 'object' ? entry.payload : {}
  const details = payload.details && typeof payload.details === 'object' ? payload.details : {}
  return Math.max(
    conversationCitations(entry).length,
    Number(payload.citationCount || 0),
    Number(details.citationCount || 0),
  )
}

function taskQualityEvaluation(task) {
  const result = task?.result && typeof task.result === 'object' ? task.result : {}
  const selected = result.selectedResource && typeof result.selectedResource === 'object' ? result.selectedResource : {}
  const metadata = selected.metadata && typeof selected.metadata === 'object' ? selected.metadata : {}
  const candidates = [
    result.qualityEvaluation,
    result.questionGenerator?.qualityEvaluation,
    result.ppt?.qualityEvaluation,
    result.document?.qualityEvaluation,
    result.animation?.qualityEvaluation,
    result.tutor?.qualityEvaluation,
    selected.qualityEvaluation,
    metadata.qualityEvaluation,
  ]
  return candidates.find(value => value && typeof value === 'object' && Number.isFinite(Number(value.score))) || null
}

function taskCitationCount(task) {
  const result = task?.result && typeof task.result === 'object' ? task.result : {}
  const selected = result.selectedResource && typeof result.selectedResource === 'object' ? result.selectedResource : {}
  const metadata = selected.metadata && typeof selected.metadata === 'object' ? selected.metadata : {}
  const quality = taskQualityEvaluation(task) || {}
  const sourceLists = [
    result.knowledgeSources,
    result.questionGenerator?.knowledgeSources,
    result.ppt?.knowledgeSources,
    selected.knowledgeSources,
    metadata.knowledgeSources,
  ]
  return Math.max(
    Number(quality.citationCount || 0),
    ...sourceLists.map(value => Array.isArray(value) ? value.length : 0),
  )
}

function conversationCitations(entry) {
  const payload = entry?.payload && typeof entry.payload === 'object' ? entry.payload : {}
  const details = payload.details && typeof payload.details === 'object' ? payload.details : {}
  const candidates = [payload.citations, payload.knowledgeSources, details.citations, details.knowledgeSources]
  return candidates.find(value => Array.isArray(value)) || []
}

async function openConversationRoute(group) {
  const routeTarget = taskRoute({
    route: group?.route,
    taskId: group?.taskId,
    taskType: group?.resourceType,
    title: group?.title,
  })
  if (!routeTarget) return
  logTaskOpen({
    taskId: group.taskId,
    taskType: group.resourceType,
    title: group.title,
    route: routeTarget,
  })
  if (/^https?:\/\//i.test(routeTarget)) {
    const targetUrl = new URL(routeTarget, window.location.origin)
    if (targetUrl.origin !== window.location.origin) {
      window.open(targetUrl.href, '_blank', 'noopener,noreferrer')
      return
    }
    await router.push(`${targetUrl.pathname}${targetUrl.search}${targetUrl.hash}`)
  } else {
    await router.push(routeTarget)
  }
  isOpen.value = false
}

function startStatusPolling() {
  stopStatusPolling()
  statusTimer = window.setInterval(loadStatus, runningTaskCount.value ? 2000 : 5000)
}

function stopStatusPolling() {
  if (statusTimer) {
    window.clearInterval(statusTimer)
    statusTimer = null
  }
}

async function handleExternalTaskUpdate() {
  await loadStatus()
  if (runningTaskCount.value) {
    startStatusPolling()
  }
}

function messageTaskPreviews(message) {
  if (!Array.isArray(message?.cards)) return []
  const seenTaskIds = new Set()
  return message.cards
    .map((card) => {
      const currentTask = tasks.value.find(task => task.taskId === card?.taskId)
      return {
        ...card,
        ...(currentTask || {}),
        taskId: currentTask?.taskId || card?.taskId || '',
        taskType: currentTask?.taskType || card?.type || '',
        type: card?.type || currentTask?.taskType || '',
        route: currentTask?.route || card?.route || '',
        status: currentTask?.status || card?.status || 'queued',
        result: currentTask?.result || card?.result || {},
      }
    })
    .filter((task) => {
      const type = task.taskType || task.type
      if (!task.taskId || !task.route || !companionTaskTypes.has(type) || seenTaskIds.has(task.taskId)) return false
      seenTaskIds.add(task.taskId)
      return true
    })
    .sort((left, right) => taskActivityTimestamp(left) - taskActivityTimestamp(right))
}

function withEmbedParam(routeTarget) {
  if (!routeTarget) return ''
  try {
    const url = new URL(String(routeTarget), window.location.origin)
    url.searchParams.set('xzEmbed', '1')
    return url.toString()
  } catch {
    return String(routeTarget)
  }
}

function taskPreviewUrl(task) {
  return withEmbedParam(taskRoute(task))
}

function taskRoute(task) {
  const routeTarget = task?.route || fallbackTaskRoute(task)
  if (!routeTarget || !task?.taskId) return routeTarget
  try {
    const url = new URL(String(routeTarget), window.location.origin)
    url.searchParams.delete('autostart')
    url.searchParams.set('xzTask', String(task.taskId))
    return url.toString()
  } catch {
    return routeTarget
  }
}

function fallbackTaskRoute(task) {
  const result = taskResult(task)
  const type = task?.taskType || task?.type || result.resourceType || ''
  const topic = String(result.topic || task?.prompt || compactTaskTitle(task)).trim()
  const taskId = encodeURIComponent(task?.taskId || '')
  if (type === 'learning_background') {
    return '/learning-profile?collect=chat'
  }
  if (type === 'profile_update') {
    return '/learning-profile?menu=report'
  }
  if (type === 'profile_management') {
    return '/learning-profile?menu=history'
  }
  if (type === 'learning_path') {
    return '/learning-path'
  }
  if (type === 'learning_path_stage') {
    const stageId = String(result?.params?.stageId || result?.stageId || '').trim()
    return stageId ? `/learning-path/week/${encodeURIComponent(stageId)}` : '/learning-path'
  }
  if (type === 'personalized_resources') {
    return '/personalized-resources'
  }
  if (type === 'question_bank') {
    return `/personalized-resources/question-bank?module=generate&chapter=${encodeURIComponent(topic)}&autostart=1&xzTask=${taskId}`
  }
  if (type === 'ppt') {
    return `/personalized-resources/ppt?topic=${encodeURIComponent(topic)}&autostart=1&xzTask=${taskId}`
  }
  if (type === 'document') {
    return `/personalized-resources/document?topic=${encodeURIComponent(topic)}&autostart=1&xzTask=${taskId}`
  }
  if (type === 'mindmap') {
    return `/personalized-resources/mind-map?topic=${encodeURIComponent(topic)}&autostart=1&xzTask=${taskId}`
  }
  if (type === 'generated_video') {
    return `/personalized-resources/video-generator?topic=${encodeURIComponent(topic)}&xzTask=${taskId}`
  }
  if (type === 'video') {
    return `/personalized-resources/video-search?keyword=${encodeURIComponent(topic)}&xzTask=${taskId}`
  }
  if (type === 'animation') {
    return `/personalized-resources/animation?topic=${encodeURIComponent(topic)}&xzTask=${taskId}`
  }
  if (type === 'mcu') {
    return '/personalized-resources'
  }
  if (type === 'interview') {
    return `/digital-human-interview?xzTask=${taskId}`
  }
  if (type === 'smart_tutor') {
    return `/smart-tutor?xzTask=${taskId}`
  }
  if (type === 'effect_assessment') {
    return `/effect-assessment?xzTask=${taskId}`
  }
  if (type === 'learning_feedback') {
    return `/effect-assessment?section=feedback&xzTask=${taskId}`
  }
  if (type === 'knowledge_base') {
    return `/personalized-resources/knowledge-base?xzTask=${taskId}`
  }
  return '/personalized-resources'
}

function mentionHighlightSegments(value) {
  const content = String(value || '')
  if (!content) return []
  const segments = []
  let cursor = 0
  for (const match of content.matchAll(mentionTokenPattern)) {
    const start = Number(match.index || 0)
    if (start > cursor) segments.push({ text: content.slice(cursor, start), mention: false })
    segments.push({ text: match[0], mention: true })
    cursor = start + match[0].length
  }
  if (cursor < content.length) segments.push({ text: content.slice(cursor), mention: false })
  return segments.length ? segments : [{ text: content, mention: false }]
}

function syncComposerScroll(event) {
  composerScroll.left = Number(event?.target?.scrollLeft || 0)
  composerScroll.top = Number(event?.target?.scrollTop || 0)
}

function handleComposerKeydown(event) {
  if (mentionMenuOpen.value) {
    if (event.key === 'Tab' || event.key === 'Enter') {
      event.preventDefault()
      completeAgentMention(filteredMentionAgents.value[mentionSelectionIndex.value] || filteredMentionAgents.value[0])
      return
    }
    if (event.key === 'ArrowDown' || event.key === 'ArrowUp') {
      event.preventDefault()
      const direction = event.key === 'ArrowDown' ? 1 : -1
      const total = filteredMentionAgents.value.length
      mentionSelectionIndex.value = (mentionSelectionIndex.value + direction + total) % total
      return
    }
    if (event.key === 'Escape') {
      event.preventDefault()
      activeMention.value = null
      return
    }
  }
  if (event.key !== 'Enter' || event.shiftKey) return
  if (event.isComposing || event.keyCode === 229) return
  event.preventDefault()
  sendMessage()
}

function updateMentionContext(event) {
  const inputValue = String(event?.target?.value ?? draft.value)
  const caret = Math.max(0, Math.min(Number(event?.target?.selectionStart ?? inputValue.length), inputValue.length))
  mentionCaretPosition.value = caret
  mentionSelectionIndex.value = 0
  const match = inputValue.slice(0, caret).match(/(^|\s)@([^\s@]*)$/)
  activeMention.value = match
    ? {
        query: String(match[2] || '').toLowerCase(),
        start: match.index + String(match[1] || '').length,
        end: caret,
      }
    : null
}

function closeMentionMenu() {
  activeMention.value = null
  mentionSelectionIndex.value = 0
}

function completeAgentMention(agent) {
  if (!agent || !activeMention.value) return
  const mention = activeMention.value
  const insertion = `@${agent.name} `
  draft.value = `${draft.value.slice(0, mention.start)}${insertion}${draft.value.slice(mention.end)}`
  const nextCaret = mention.start + insertion.length
  mentionCaretPosition.value = nextCaret
  mentionSelectionIndex.value = 0
  activeMention.value = null
  nextTick(() => {
    composerInputRef.value?.focus()
    composerInputRef.value?.setSelectionRange?.(nextCaret, nextCaret)
  })
}

function mentionedAgent(content) {
  const match = String(content || '').match(/(^|\s)@([^\s，,：:]+)/)
  const name = String(match?.[2] || '').toLowerCase()
  return mentionableAgents.find(agent => agent.name.toLowerCase() === name) || mentionableAgents[0]
}

async function sendMessage() {
  const content = draft.value.trim()
  const queuedFiles = pendingAttachments.value.slice()
  if ((!content && !queuedFiles.length) || isSending.value) return
  const displayContent = content || '请分析我上传的学习材料。'
  const targetAgent = mentionedAgent(displayContent)
  const sendEpoch = profileRequestEpoch
  const sendProfileReportId = Number(activeProfileReportId.value || 0)
  const chatController = new AbortController()
  activeChatController?.abort()
  activeChatController = chatController
  pendingTargetAgentId.value = targetAgent.id
  sendError.value = ''
  const userMessage = {
    role: 'user',
    content: displayContent,
    attachments: queuedFiles.map(file => ({ name: file.name, kind: fileKind(file), size: file.size })),
    createdAt: new Date().toISOString(),
    cards: [],
  }
  messages.value.push(userMessage)
  draft.value = ''
  pendingAttachments.value = []
  isSending.value = true
  try {
    await scrollToBottom()
    const attachments = queuedFiles.length
      ? await uploadMultimodalInputs(queuedFiles, 'xiaozhi', route.fullPath)
      : []
    userMessage.attachments = attachments

    const assistantMessage = reactive({
      role: 'assistant',
      content: '',
      cards: [],
      intent: {},
      createdAt: new Date().toISOString(),
      streaming: true,
      targetAgent,
    })
    messages.value.push(assistantMessage)
    await scrollToBottom()

    await streamXiaoZhiChat({
      message: displayContent,
      attachments,
      route: route.fullPath,
      profileReportId: sendProfileReportId,
    }, async ({ event, data }) => {
      if (sendEpoch !== profileRequestEpoch || chatController.signal.aborted) return
      if (event === 'delta') {
        assistantMessage.content += String(data?.text || '')
        await scrollToBottom()
        return
      }
      if (event === 'result') {
        const result = data?.data || data || {}
        if (Number(result.profileReportId || 0) !== Number(activeProfileReportId.value || 0)) return
        if (result.agentConversation) agentConversation.value = result.agentConversation
        assistantMessage.cards = result.cards || []
        assistantMessage.intent = result.intent || {}
        assistantMessage.targetAgent = result.targetAgent || targetAgent
        if (!assistantMessage.content && result.reply) assistantMessage.content = result.reply
        return
      }
      if (event === 'error') {
        const serverProfileId = data?.data?.profileReportId
        if (serverProfileId !== undefined && Number(serverProfileId) !== Number(activeProfileReportId.value || 0)) {
          await handleProfileContextChanged({ detail: { profileReportId: Number(serverProfileId || 0) } })
          return
        }
        throw new Error(data?.message || data?.error || '嵌小智智能体调用失败')
      }
    }, { signal: chatController.signal })
    if (sendEpoch !== profileRequestEpoch || chatController.signal.aborted) return
    assistantMessage.streaming = false
    if (!assistantMessage.content.trim()) {
      throw new Error('嵌小智智能体没有返回有效回复')
    }
    await loadStatus()
    if (runningTaskCount.value) startStatusPolling()
    await scrollToBottom()
  } catch (error) {
    if (chatController.signal.aborted || sendEpoch !== profileRequestEpoch || error?.name === 'AbortError') return
    const errorMessage = error?.response?.data?.msg || error?.message || '嵌小智暂时连接失败，请稍后再试。'
    sendError.value = errorMessage
    if (!draft.value.trim()) draft.value = content
    if (queuedFiles.length) pendingAttachments.value = queuedFiles
    const lastMessage = messages.value[messages.value.length - 1]
    const failedAssistantMessage = lastMessage?.role === 'assistant' && lastMessage.streaming ? lastMessage : null
    const errorPayload = {
      role: 'assistant',
      content: errorMessage,
      cards: [],
      createdAt: new Date().toISOString(),
      streaming: false,
    }
    if (failedAssistantMessage) Object.assign(failedAssistantMessage, errorPayload)
    else messages.value.push(errorPayload)
    addLog(error?.message || '嵌小智对话失败', 'error', '嵌小智')
  } finally {
    if (activeChatController === chatController) {
      activeChatController = null
      isSending.value = false
      pendingTargetAgentId.value = 'xiaozhi-companion-agent'
    }
  }
}

function fileKind(file) {
  const type = String(file?.type || '').toLowerCase()
  if (type.startsWith('image/')) return 'image'
  if (type.startsWith('video/')) return 'video'
  return 'document'
}

function attachmentIcon(kind) {
  if (kind === 'image') return ImagePlus
  if (kind === 'video') return Video
  return FileText
}

function queueAssistantAttachments(event) {
  const selected = Array.from(event?.target?.files || [])
  if (event?.target) event.target.value = ''
  const next = pendingAttachments.value.slice()
  for (const file of selected) {
    if (file.size > 50 * 1024 * 1024) {
      addLog(`${file.name} 超过 50 MB，未加入附件`, 'warn', '嵌小智多模态输入')
      continue
    }
    const duplicate = next.some(item => item.name === file.name && item.size === file.size && item.lastModified === file.lastModified)
    if (!duplicate && next.length < 4) next.push(file)
  }
  pendingAttachments.value = next
  if (selected.length && next.length >= 4) {
    addLog('每次最多添加 4 个多模态附件', 'warn', '嵌小智多模态输入')
  }
}

function removePendingAttachment(index) {
  pendingAttachments.value.splice(index, 1)
}

async function scrollToBottom() {
  await nextTick()
  if (messageListRef.value) {
    messageListRef.value.scrollTop = messageListRef.value.scrollHeight
  }
}

function toggleVoiceInput() {
  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition
  if (!SpeechRecognition) {
    addLog('当前浏览器不支持 Web Speech API，可继续使用文字输入。', 'warn', '嵌小智语音')
    return
  }
  if (isListening.value && recognition) {
    recognition.stop()
    return
  }
  recognition = new SpeechRecognition()
  recognition.lang = 'zh-CN'
  recognition.interimResults = true
  recognition.continuous = false
  recognition.onstart = () => {
    isListening.value = true
  }
  recognition.onresult = (event) => {
    let finalText = ''
    let interimText = ''
    for (let index = event.resultIndex; index < event.results.length; index += 1) {
      const text = event.results[index][0]?.transcript || ''
      if (event.results[index].isFinal) {
        finalText += text
      } else {
        interimText += text
      }
    }
    draft.value = `${draft.value.replace(interimText, '')}${finalText || interimText}`.trim()
  }
  recognition.onerror = (event) => {
    addLog(`语音输入失败：${event.error || 'unknown'}`, 'warn', '嵌小智语音')
  }
  recognition.onend = () => {
    isListening.value = false
  }
  recognition.start()
}

function parseTimelineTimestamp(value) {
  const timestamp = Date.parse(String(value || ''))
  return Number.isFinite(timestamp) ? timestamp : 0
}

function taskActivityTimestamp(task) {
  return parseTimelineTimestamp(task?.updatedAt || task?.createdAt)
}

function formatTaskTime(task) {
  const timestamp = taskActivityTimestamp(task)
  if (!timestamp) return ''
  return new Intl.DateTimeFormat('zh-CN', {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    hour12: false,
  }).format(new Date(timestamp)).replaceAll('/', '-')
}

function logTaskOpen(task) {
  const routeTarget = taskRoute(task)
  if (!routeTarget) return
  logXiaoZhiEvent({
    eventType: 'assistant_task_click',
    route: routeTarget,
    title: task.title || '',
    payload: { taskId: task.taskId, type: task.taskType || task.type },
  }).catch(() => {})
}

function resolveRouteHref(routeTarget) {
  if (!routeTarget) return ''
  if (/^https?:\/\//i.test(String(routeTarget))) return String(routeTarget)
  return new URL(router.resolve(routeTarget).href, window.location.origin).href
}

function normalizeStatus(status) {
  if (['running', 'queued', 'ready', 'complete', 'failed', 'warning'].includes(status)) return status
  if (['waiting', 'waiting_for_user'].includes(status)) return 'ready'
  return status === 'idle' ? 'idle' : 'ready'
}

function statusText(status) {
  const map = {
    queued: '排队中',
    running: '运行中',
    ready: '已就绪',
    complete: '已完成',
    failed: '失败',
    warning: '待核验',
    idle: '待命',
    waiting: '等待确认',
    waiting_for_user: '等待确认',
  }
  return map[status] || status || '待命'
}

function agentIcon(agent) {
  if (agent?.type) return resourceIcon(agent.type)
  const agentId = String(agent?.id || '')
  if (agentId === 'xiaozhi-companion-agent') return BrainCircuit
  if (agentId.includes('knowledge')) return BookOpenCheck
  if (agentId.includes('review') || agentId.includes('safety')) return ShieldCheck
  if (agentId.includes('context') || agentId.includes('profile')) return BrainCircuit
  if (agentId.includes('ppt')) return Presentation
  if (agentId.includes('mindmap')) return MapIcon
  if (agentId.includes('question')) return BookOpenCheck
  if (agentId.includes('video')) return Film
  return Activity
}

function agentDisplayName(agent) {
  if (!agent) return '智能体'
  if (agent.role === 'supervisor') return agent.name || '嵌小智总控智能体'
  if (agent.type && resourceLabels[agent.type]) return `${resourceLabels[agent.type]}智能体`
  return agentNameAliases[agent.id] || agent.name || agent.id || '智能体'
}

function agentDetail(agent) {
  const detail = String(agent?.detail || '').trim()
  if (!detail) return '等待嵌小智总控调度'
  if (/^Platform task\b/i.test(detail)) {
    return `${resourceLabels[agent?.type] || '平台能力'}已就绪`
  }
  return detail
}

function agentRoleText(agent) {
  const idRoleMap = {
    'learner-context-agent': 'Context',
    'course-knowledge-retrieval-agent': 'Knowledge RAG',
    'skill-registry-agent': 'Skill Registry',
    'mcp-tool-gateway': 'MCP Gateway',
    'quality-review-agent': 'Quality Review',
    'content-safety-agent': 'Safety Guard',
  }
  if (idRoleMap[agent?.id]) return idRoleMap[agent.id]
  const roleMap = {
    supervisor: 'Supervisor',
    context: 'Context',
    gateway: 'MCP Gateway',
    registry: 'Skill Registry',
    reviewer: 'Quality Review',
    safety: 'Safety Guard',
    specialist: 'Specialist',
  }
  return roleMap[agent?.role] || 'Agent'
}

function runTaskLabel(run) {
  return resourceLabels[run?.taskType] || run?.taskType || '协作任务'
}

function runOptionLabel(run) {
  const topic = String(run?.topic || '未命名任务').trim()
  const compactTopic = topic.length > 22 ? `${topic.slice(0, 22)}...` : topic
  return `${runTaskLabel(run)} · ${compactTopic}`
}

function formatRunTime(value) {
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return '时间未记录'
  return date.toLocaleString('zh-CN', {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    hour12: false,
  })
}

function actualAgentDetail(agent) {
  const detail = String(agent?.detail || '').trim()
  if (detail) return detail
  const eventCount = Number(agent?.eventCount || 0)
  return eventCount > 0 ? `记录 ${eventCount} 个执行事件` : '已参与本次实际运行'
}

function handoffAgentName(agentId, recordedName) {
  const persistedName = String(recordedName || '').trim()
  if (persistedName && persistedName !== agentId) return persistedName
  const runtimeAgent = selectedRunAgents.value.find(agent => String(agent.id) === String(agentId))
    || agents.value.find(agent => String(agent.id) === String(agentId))
  return agentDisplayName(runtimeAgent || { id: agentId, name: persistedName })
}

function handoffArtifactLabel(artifactType) {
  const type = String(artifactType || '').trim()
  return handoffArtifactLabels[type] || type.replaceAll('_', ' ') || '结构化交接'
}

function openHarnessNodeDetail(node) {
  if (!node) return
  selectedHarnessNodeId.value = String(node.id || '')
}

function closeHarnessNodeDetail() {
  selectedHarnessNodeId.value = ''
}

function taskTypeLabel(task) {
  return resourceLabels[task?.taskType || task?.type] || '学习任务'
}

function taskResult(task) {
  return task?.result && typeof task.result === 'object' ? task.result : {}
}

function taskProgress(task) {
  const progress = Number(taskResult(task).progress || 0)
  if (!Number.isFinite(progress)) return 0
  return Math.max(0, Math.min(100, Math.round(progress)))
}

function taskMessage(task) {
  const result = taskResult(task)
  const type = task?.taskType || task?.type || result.resourceType
  if (type === 'generated_video' && ['waiting', 'waiting_for_user'].includes(task?.status)) {
    return '打开任务页面后确认生成，确认前不会调用视频模型'
  }
  if (result.message) return result.message
  if (task?.status === 'running') return '智能体正在后台执行任务'
  if (task?.status === 'queued') return '任务已进入队列'
  if (task?.status === 'complete') return '任务已完成'
  if (task?.status === 'failed') return task?.error || '任务执行失败'
  if (['waiting', 'waiting_for_user'].includes(task?.status)) return '打开任务页面后确认生成'
  return task?.prompt || '等待调度'
}

function compactTaskTitle(task) {
  const rawTitle = String(task?.title || taskResult(task).topic || '学习任务').trim()
  return rawTitle.replace(/\s*·\s*PPT.*$/i, '').replace(/^PPT[:：]\s*/i, 'PPT: ')
}

onMounted(() => {
  syncLearnerAvatar()
  window.addEventListener('resize', handleResize)
  window.addEventListener('current-user-change', syncLearnerAvatar)
  window.addEventListener('xiaozhi-task-updated', handleExternalTaskUpdate)
  window.addEventListener(XIAOZHI_WORKFLOW_EVENT, handleWorkflowCardOpen)
  window.addEventListener(XIAOZHI_PROFILE_CONTEXT_EVENT, handleProfileContextChanged)
  handleResize()
  loadStatus()
})

onBeforeUnmount(() => {
  activeChatController?.abort()
  removePointerListeners()
  window.removeEventListener('resize', handleResize)
  window.removeEventListener('current-user-change', syncLearnerAvatar)
  window.removeEventListener('xiaozhi-task-updated', handleExternalTaskUpdate)
  window.removeEventListener(XIAOZHI_WORKFLOW_EVENT, handleWorkflowCardOpen)
  window.removeEventListener(XIAOZHI_PROFILE_CONTEXT_EVENT, handleProfileContextChanged)
  stopStatusPolling()
  recognition?.stop?.()
})
</script>

<style scoped>
.xiaozhi-float {
  position: fixed;
  z-index: 9998;
  width: 66px;
  height: 66px;
  color: #46504e;
  user-select: none;
  touch-action: none;
}

.xiaozhi-float.dragging {
  cursor: grabbing;
}

.xiaozhi-orb {
  position: relative;
  width: 66px;
  height: 66px;
  display: grid;
  place-items: center;
  padding: 0;
  border: 1px solid rgba(16, 185, 129, 0.34);
  border-radius: 50%;
  background: radial-gradient(circle at 32% 24%, #ffffff, #f3fffb 54%, #dff8ed);
  color: #1f3433;
  box-shadow: 0 12px 30px rgba(16, 185, 129, 0.2), inset 0 0 0 6px rgba(255, 255, 255, 0.76);
  cursor: grab;
  overflow: visible;
}

.xiaozhi-orb-logo {
  width: 58px;
  height: 58px;
  display: block;
  border-radius: 50%;
  object-fit: cover;
  pointer-events: none;
}

.orb-pulse {
  position: absolute;
  inset: -8px;
  border: 2px solid rgba(16, 185, 129, 0.2);
  border-radius: 50%;
  animation: xiaozhiPulse 2.6s ease-in-out infinite;
  pointer-events: none;
}

.task-dot {
  position: absolute;
  right: -2px;
  top: -2px;
  min-width: 22px;
  height: 22px;
  display: grid;
  place-items: center;
  padding: 0 6px;
  border: 2px solid #fff;
  border-radius: 999px;
  background: #10b981;
  color: #fff;
  font-size: 12px;
  font-weight: 800;
}

.xiaozhi-window {
  position: absolute;
  width: min(440px, calc(100vw - 32px));
  height: min(660px, var(--xiaozhi-window-max-height, calc(100dvh - 28px)));
  max-height: min(660px, var(--xiaozhi-window-max-height, calc(100dvh - 28px)));
  display: flex;
  flex-direction: column;
  padding: 18px;
  box-sizing: border-box;
  border: 1px solid #dfe3e2;
  border-radius: 10px;
  background: #ffffff;
  box-shadow: 0 12px 32px rgba(24, 34, 31, 0.14);
  overflow: hidden;
}

.xiaozhi-window.previewing {
  width: min(760px, calc(100vw - 32px));
}

.xiaozhi-window.wide {
  width: min(820px, calc(100vw - 32px));
  height: min(520px, calc(100dvh - 28px));
  max-height: min(520px, calc(100dvh - 28px));
}

.xiaozhi-window.right {
  left: 84px;
}

.xiaozhi-window.left {
  right: 84px;
}

.xiaozhi-window.down {
  top: 0;
}

.xiaozhi-window.up {
  bottom: 0;
}

.window-head,
.mode-tabs,
.composer-actions,
.status-toolbar,
.agent-row,
.resource-card {
  display: flex;
  align-items: center;
}

.window-head {
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 8px;
}

.window-head-actions {
  display: flex;
  align-items: center;
  gap: 6px;
}

.title-block strong {
  display: block;
  color: #172033;
  font-size: 20px;
  line-height: 1.1;
}

.runtime-settings-panel {
  display: grid;
  gap: 14px;
  min-height: 420px;
  padding: 4px 2px 2px;
  overflow-y: auto;
}

.runtime-settings-head,
.runtime-toggle,
.runtime-settings-actions,
.runtime-security-note,
.harness-summary,
.task-harness-meta {
  display: flex;
  align-items: center;
}

.runtime-settings-head {
  justify-content: space-between;
  gap: 12px;
  padding-bottom: 10px;
  border-bottom: 1px solid #dce9e5;
}

.runtime-settings-head span {
  display: block;
  color: #0e9f6e;
  font-size: 11px;
  font-weight: 800;
}

.runtime-settings-head strong {
  display: block;
  margin-top: 3px;
  color: #172033;
  font-size: 18px;
}

.runtime-settings-panel > label:not(.runtime-toggle) {
  display: grid;
  gap: 6px;
}

.runtime-settings-panel label > span {
  color: #314a47;
  font-size: 12px;
  font-weight: 800;
}

.runtime-settings-panel input[type='url'],
.runtime-settings-panel input[type='text'],
.runtime-settings-panel select {
  width: 100%;
  min-height: 42px;
  padding: 9px 11px;
  border: 1px solid #cfe2dc;
  border-radius: 7px;
  outline: none;
  background: #fff;
  color: #172033;
  font: inherit;
  font-size: 13px;
}

.runtime-settings-panel input:focus,
.runtime-settings-panel select:focus {
  border-color: #10b981;
  box-shadow: 0 0 0 3px rgba(16, 185, 129, 0.1);
}

.runtime-settings-panel input:disabled,
.runtime-settings-panel select:disabled {
  color: #849792;
  background: #f2f6f4;
  cursor: not-allowed;
}

.runtime-toggle {
  justify-content: space-between;
  gap: 12px;
  padding: 11px 12px;
  border: 1px solid #d7e9e3;
  border-radius: 7px;
  background: #f7fbf9;
}

.runtime-toggle span {
  display: grid;
  gap: 3px;
}

.runtime-toggle small {
  color: #71847f;
  font-size: 11px;
  font-weight: 500;
}

.runtime-toggle input {
  width: 36px;
  height: 20px;
  accent-color: #10b981;
}

.runtime-security-note {
  gap: 8px;
  padding: 10px 11px;
  border-left: 3px solid #10b981;
  background: #f2faf6;
  color: #526a65;
  font-size: 11px;
  line-height: 1.5;
}

.runtime-security-note svg {
  flex: 0 0 auto;
  color: #0e9f6e;
}

.runtime-settings-message {
  margin: 0;
  padding: 8px 10px;
  border-radius: 6px;
  background: #f3f6f5;
  color: #526a65;
  font-size: 11px;
  line-height: 1.45;
}

.runtime-settings-message.success {
  background: #ecfdf5;
  color: #047857;
}

.runtime-settings-message.error {
  background: #fef2f2;
  color: #b91c1c;
}

.runtime-settings-actions {
  justify-content: flex-end;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: auto;
  padding-top: 4px;
}

.harness-summary {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 6px;
  margin-bottom: 12px;
  padding: 10px;
  border: 1px solid #d8e9e3;
  border-radius: 7px;
  background: #f6fbf8;
}

.harness-summary span {
  min-width: 0;
  color: #71847f;
  font-size: 9px;
  text-align: center;
}

.harness-summary strong {
  display: block;
  overflow: hidden;
  color: #123b32;
  font-size: 12px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.icon-btn {
  width: 36px;
  height: 36px;
  display: grid;
  place-items: center;
  border: 1px solid #d9eee8;
  border-radius: 50%;
  background: #f6fffb;
  color: #48615e;
  cursor: pointer;
}

.mode-tabs {
  gap: 8px;
  padding: 5px;
  border: 1px solid #e0f1ec;
  border-radius: 16px;
  background: rgba(243, 251, 247, 0.9);
}

.mode-tabs button {
  flex: 1;
  min-height: 40px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 7px;
  border: 0;
  border-radius: 12px;
  background: transparent;
  color: #536b68;
  font-size: 13px;
  font-weight: 800;
  cursor: pointer;
  text-decoration: none;
}

.mode-tabs button.active {
  background: #fff;
  color: #0e9f6e;
  box-shadow: 0 8px 20px rgba(31, 72, 66, 0.08);
}

.chat-panel,
.status-panel {
  min-height: 0;
  display: flex;
  flex: 1;
  flex-direction: column;
  gap: 12px;
  margin-top: 12px;
}

.status-panel {
  overflow-x: hidden;
  overflow-y: auto;
  padding-right: 3px;
  overscroll-behavior: contain;
  scrollbar-color: #c4c9c8 transparent;
}

.chat-panel {
  overflow: hidden;
}

.chat-scroll-area {
  min-height: 0;
  flex: 1 1 auto;
  overflow-x: hidden;
  overflow-y: auto;
  padding-right: 3px;
}

.message-list {
  min-height: 180px;
  max-height: none;
  overflow: visible;
  padding: 2px 4px 2px 0;
}

.empty-chat {
  padding: 16px;
  text-align: center;
}

.empty-chat svg {
  color: #10b981;
}

.empty-chat strong {
  display: block;
  margin-top: 6px;
  color: #172033;
}

.agent-group-chat {
  display: grid;
  gap: 8px;
  margin: 2px 0 12px;
}

.agent-group-chat-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  padding: 0 2px;
}

.agent-group-chat-head span {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  color: #185b49;
  font-size: 12px;
  font-weight: 850;
}

.agent-group-chat-head small {
  color: #7b8b87;
  font-size: 11px;
}

.agent-conversation-empty {
  display: grid;
  gap: 4px;
  padding: 12px;
  border: 1px dashed #cbded8;
  border-radius: 7px;
  background: #f8fbfa;
  color: #54706a;
}

.agent-conversation-empty strong {
  color: #244b41;
  font-size: 12px;
}

.agent-conversation-empty span {
  font-size: 11px;
  line-height: 1.5;
}

.agent-conversation-card {
  overflow: hidden;
  border: 1px solid #e4ede9;
  border-radius: 10px;
  background: linear-gradient(135deg, #ffffff, #fbfefd);
}

.agent-conversation-card.running {
  border-color: #cfe3f2;
  background: linear-gradient(135deg, #ffffff, #f7fbff);
}

.agent-conversation-card.failed {
  border-color: #efcccc;
  background: linear-gradient(135deg, #ffffff, #fff8f8);
}

.agent-conversation-card.warning,
.agent-conversation-card.compacted-history {
  border-color: #eadbb6;
  background: linear-gradient(135deg, #ffffff, #fffaf0);
}

.agent-conversation-main {
  width: 100%;
  display: grid;
  grid-template-columns: 28px minmax(0, 1fr) 16px;
  align-items: start;
  gap: 8px;
  padding: 10px 11px;
  border: 0;
  background: transparent;
  color: #263a35;
  text-align: left;
  cursor: pointer;
}

.agent-conversation-main:hover {
  background: rgba(241, 249, 246, .72);
}

.agent-conversation-main > svg {
  color: #84938f;
}

.agent-conversation-icon {
  width: 28px;
  height: 28px;
  display: grid;
  place-items: center;
  border-radius: 50%;
  color: #147257;
  background: #edf7f3;
}

.agent-conversation-card.running .agent-conversation-icon {
  color: #286ca8;
  background: #edf5fc;
}

.agent-conversation-card.failed .agent-conversation-icon {
  color: #a73737;
  background: #fdf0f0;
}

.agent-conversation-copy {
  min-width: 0;
  display: block;
}

.agent-conversation-copy small,
.agent-conversation-copy strong,
.agent-conversation-copy em {
  display: block;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.agent-conversation-copy small {
  color: #397866;
  font-size: 9px;
  font-weight: 850;
}

.agent-conversation-copy strong {
  margin-top: 2px;
  color: #21332f;
  font-size: 12px;
}

.agent-conversation-copy em {
  margin-top: 2px;
  color: #71817d;
  font-size: 10px;
  font-style: normal;
}

.conversation-handoff-strip {
  display: grid;
  gap: 4px;
  margin-top: 7px;
}

.conversation-handoff-strip i {
  min-width: 0;
  display: inline-flex;
  align-items: center;
  gap: 5px;
  overflow: hidden;
  color: #4f625c;
  font-size: 10px;
  font-style: normal;
  line-height: 1.35;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.conversation-handoff-strip b {
  width: 6px;
  height: 6px;
  flex: 0 0 auto;
  border-radius: 50%;
  background: #2a8a6c;
}

.conversation-handoff-strip i.running b {
  background: #3182ce;
  box-shadow: 0 0 0 3px rgba(49, 130, 206, .1);
}

.conversation-handoff-strip i.warning b {
  background: #b47a1f;
}

.conversation-handoff-strip i.failed b {
  background: #c84b4b;
}

.conversation-card-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  margin-top: 6px;
}

.conversation-card-meta i {
  padding: 2px 5px;
  border: 1px solid #e1e9e5;
  border-radius: 999px;
  color: #5e746d;
  background: rgba(255,255,255,.72);
  font-size: 9px;
  font-style: normal;
  line-height: 1.2;
}

.agent-conversation-progress {
  display: block;
  height: 3px;
  background: #edf2f0;
}

.agent-conversation-progress b {
  display: block;
  height: 100%;
  background: #2a8a6c;
  transition: width 0.25s ease;
}

.agent-conversation-details {
  padding: 0 11px 11px 48px;
  border-top: 1px solid #edf1ef;
  background: #fbfcfc;
}

.agent-conversation-details ol {
  display: grid;
  gap: 0;
  margin: 0;
  padding: 8px 0 0;
  list-style: none;
}

.agent-conversation-details li {
  position: relative;
  display: grid;
  grid-template-columns: 12px minmax(0, 1fr);
  gap: 7px;
  padding: 5px 0 8px;
}

.agent-conversation-details li:not(:last-child)::before {
  position: absolute;
  top: 18px;
  bottom: -4px;
  left: 5px;
  width: 1px;
  background: #cddbd6;
  content: '';
}

.conversation-entry-marker {
  z-index: 1;
  width: 10px;
  height: 10px;
  margin-top: 3px;
  border: 2px solid #fff;
  border-radius: 50%;
  background: #2a8a6c;
  box-shadow: 0 0 0 1px #9abeb3;
}

.agent-conversation-details li header {
  display: flex;
  justify-content: space-between;
  gap: 8px;
}

.agent-conversation-details li header strong {
  color: #29453d;
  font-size: 10px;
}

.agent-conversation-details time {
  color: #87948f;
  font-size: 9px;
}

.agent-conversation-details li p,
.conversation-summary-text {
  margin: 3px 0 0;
  color: #536660;
  font-size: 11px;
  line-height: 1.55;
  white-space: pre-wrap;
}

.agent-conversation-details li small {
  display: block;
  margin-top: 3px;
  color: #7b8985;
  font-size: 9px;
}

.conversation-summary-text {
  max-height: 220px;
  overflow-y: auto;
  padding-top: 8px;
}

.conversation-references {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  margin-top: 5px;
}

.conversation-references i {
  max-width: 100%;
  overflow: hidden;
  padding: 2px 5px;
  border: 1px solid #d7e3df;
  border-radius: 4px;
  color: #527068;
  background: #fff;
  font-size: 9px;
  font-style: normal;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.conversation-citations {
  display: grid;
  gap: 5px;
  margin-top: 6px;
}

.conversation-citations > span {
  display: grid;
  gap: 2px;
  padding: 6px 7px;
  border-left: 2px solid #7eaa9c;
  background: #f3f8f6;
}

.conversation-citations strong {
  color: #365d51;
  font-size: 9px;
}

.conversation-citations small {
  display: -webkit-box !important;
  overflow: hidden;
  margin: 0 !important;
  color: #667771 !important;
  font-size: 9px !important;
  line-height: 1.45;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 3;
}

.conversation-resource-link {
  width: fit-content;
  display: inline-flex;
  align-items: center;
  gap: 5px;
  margin-top: 5px;
  padding: 6px 8px;
  border: 1px solid #bcd6cd;
  border-radius: 5px;
  color: #17684f;
  background: #fff;
  font-size: 10px;
  font-weight: 800;
  cursor: pointer;
  text-decoration: none;
}

.message {
  display: flex;
  align-items: flex-end;
  gap: 8px;
  margin: 10px 0;
}

.message.user {
  justify-content: flex-end;
}

.message.user .message-avatar {
  order: 2;
  border: 0;
  background: transparent;
  box-shadow: none;
}

.message-avatar,
.conversation-entry-avatar,
.mention-agent-avatar {
  flex: 0 0 auto;
  display: grid;
  place-items: center;
  border: 1px solid rgba(39, 76, 65, 0.09);
  border-radius: 50%;
}

.message-avatar {
  width: 30px;
  height: 30px;
  margin-bottom: 2px;
  box-shadow: 0 4px 12px rgba(31, 72, 66, 0.08);
}

.message-avatar img {
  width: 100%;
  height: 100%;
  display: block;
  border-radius: inherit;
  object-fit: cover;
}

.conversation-entry-avatar {
  width: 26px;
  height: 26px;
  margin-top: 1px;
}

.mention-agent-avatar {
  width: 30px;
  height: 30px;
  border: 0 !important;
  box-shadow: none !important;
}

.message.assistant {
  justify-content: flex-start;
}

.bubble {
  max-width: 86%;
  padding: 12px 14px;
  border-radius: 17px;
  border: 1px solid #e2f1ec;
  background: #fff;
  box-shadow: 0 8px 18px rgba(31, 72, 66, 0.05);
}

.message-attachments,
.pending-attachments {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.message-attachments {
  margin-top: 8px;
}

.message-attachments a,
.pending-attachments > span {
  min-width: 0;
  display: inline-flex;
  align-items: center;
  gap: 5px;
  max-width: 100%;
  padding: 5px 7px;
  border: 1px solid #cfe7df;
  border-radius: 6px;
  background: #f3faf7;
  color: #24624f;
  font-size: 11px;
}

.message-attachments a span,
.pending-attachments b {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.message.user .bubble {
  border-color: #10b981;
  background: linear-gradient(135deg, #18bd7f, #0e9f6e);
  color: #fff;
}

.bubble p {
  margin: 0;
  white-space: pre-wrap;
  line-height: 1.6;
  font-size: 14px;
}

.typing-ellipsis {
  min-width: 32px;
  min-height: 22px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 4px;
  color: #536b68;
}

.typing-ellipsis span {
  width: 5px;
  height: 5px;
  display: block;
  border-radius: 50%;
  background: currentColor;
  animation: xiaozhiTypingDot 1.05s infinite ease-in-out both;
}

.typing-ellipsis span:nth-child(2) {
  animation-delay: 0.14s;
}

.typing-ellipsis span:nth-child(3) {
  animation-delay: 0.28s;
}

@keyframes xiaozhiTypingDot {
  0%, 60%, 100% {
    transform: translateY(0) scale(.72);
    opacity: .35;
  }
  30% {
    transform: translateY(-4px) scale(1);
    opacity: 1;
  }
}

.spin {
  animation: spin 1s linear infinite;
}

.resource-cards {
  display: grid;
  gap: 8px;
  margin-top: 10px;
}

.resource-card {
  width: 100%;
  gap: 10px;
  padding: 10px;
  border: 1px solid #d9eee8;
  border-radius: 14px;
  background: #f8fffc;
  color: #213a39;
  text-align: left;
  text-decoration: none;
  cursor: pointer;
}

.resource-card:hover {
  border-color: #9fe8cc;
  transform: translateY(-1px);
}

.resource-card .card-icon {
  width: 36px;
  height: 36px;
  display: grid;
  place-items: center;
  flex: 0 0 auto;
  border-radius: 12px;
  background: #ddf7ea;
  color: #0e9f6e;
}

.resource-card strong {
  display: block;
  font-size: 13px;
}

.resource-card small {
  display: block;
  margin-top: 3px;
  color: #667a77;
  font-size: 12px;
  line-height: 1.4;
}

.resource-card > svg {
  margin-left: auto;
  color: #8aa09c;
}

.ohmyppt-embed-card {
  display: grid;
  gap: 8px;
  padding: 10px;
  border: 1px solid #cfefe4;
  border-radius: 16px;
  background: linear-gradient(135deg, rgba(238, 252, 246, 0.96), rgba(255, 255, 255, 0.94));
  color: #1f3433;
  text-align: left;
  box-shadow: 0 14px 32px rgba(31, 72, 66, 0.08);
  cursor: pointer;
}

.ohmyppt-embed-head,
.ohmyppt-embed-foot {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}

.ohmyppt-embed-head span {
  min-width: 0;
  display: inline-flex;
  align-items: center;
  gap: 7px;
}

.ohmyppt-embed-head svg {
  color: #0e9f6e;
}

.ohmyppt-embed-head strong {
  overflow: hidden;
  color: #0f3a34;
  font-size: 13px;
  line-height: 1.3;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.ohmyppt-embed-head em {
  flex: 0 0 auto;
  color: #0e9f6e;
  font-size: 12px;
  font-style: normal;
  font-weight: 850;
}

.ohmyppt-embed-foot span {
  flex: 0 0 auto;
  color: #0e9f6e;
  font-size: 12px;
  font-weight: 850;
}

.ohmyppt-embed-foot small {
  min-width: 0;
  overflow: hidden;
  color: #667a77;
  font-size: 11px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.ohmyppt-frame-shell {
  position: relative;
  overflow: hidden;
  border: 1px solid rgba(205, 239, 227, 0.82);
  border-radius: 12px;
  background: #eefcf6;
}

.ohmyppt-frame-shell.compact {
  height: 172px;
}

.ohmyppt-frame-shell.expanded {
  flex: 1;
  min-height: 420px;
}

.ohmyppt-frame-shell iframe {
  width: 100%;
  height: 100%;
  border: 0;
  background: #eefcf6;
}

.ohmyppt-frame-shell.compact iframe {
  width: 1920px;
  height: 1080px;
  transform: scale(0.22);
  transform-origin: top left;
  pointer-events: none;
}

.ohmyppt-frame-cover {
  position: absolute;
  right: 10px;
  bottom: 10px;
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 6px 9px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.92);
  color: #0e9f6e;
  font-size: 11px;
  font-weight: 850;
  box-shadow: 0 8px 18px rgba(31, 72, 66, 0.12);
}

.task-preview-overlay {
  position: absolute;
  inset: 12px;
  z-index: 5;
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding: 14px;
  border: 1px solid #cfefe4;
  border-radius: 20px;
  background:
    linear-gradient(135deg, rgba(244, 255, 250, 0.98), rgba(255, 255, 255, 0.96)),
    #ffffff;
  box-shadow: 0 22px 60px rgba(31, 72, 66, 0.18);
}

.preview-overlay-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.preview-overlay-head span {
  color: #0e9f6e;
  font-size: 11px;
  font-weight: 900;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.preview-overlay-head strong {
  display: block;
  margin-top: 3px;
  color: #172033;
  font-size: 18px;
}

.preview-overlay-actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}

.task-state,
.agent-light {
  width: 9px;
  height: 9px;
  border-radius: 50%;
  background: #94a3b8;
}

.task-state.running,
.task-state.queued,
.agent-light.running,
.agent-light.queued {
  background: #3b82f6;
  box-shadow: 0 0 0 4px rgba(59, 130, 246, 0.12);
}

.task-state.complete,
.task-state.ready,
.agent-light.complete,
.agent-light.ready {
  background: #10b981;
  box-shadow: 0 0 0 4px rgba(16, 185, 129, 0.12);
}

.task-state.failed,
.agent-light.failed {
  background: #ef4444;
  box-shadow: 0 0 0 4px rgba(239, 68, 68, 0.12);
}

.composer {
  position: relative;
  z-index: 4;
  flex: 0 0 auto;
  padding: 8px 0 0;
  border: 0;
  background: transparent;
}

.agent-mention-menu {
  position: absolute;
  left: 0;
  right: 0;
  bottom: calc(100% - 2px);
  z-index: 12;
  max-height: 278px;
  overflow-y: auto;
  padding: 4px 0;
  border: 0 !important;
  border-radius: 0 !important;
  background: #eef2f0;
  box-shadow: none !important;
}

.composer-editor-shell {
  position: relative;
  min-height: 52px;
  overflow: hidden;
  border-radius: 12px;
  background: #ffffff;
}

.composer-highlight-layer {
  position: absolute;
  inset: 0;
  z-index: 0;
  overflow: hidden;
  border: 1px solid transparent;
  border-radius: 12px;
  pointer-events: none;
}

.composer-highlight-content {
  width: 100%;
  min-height: 52px;
  padding: 9px 10px;
  box-sizing: border-box;
  color: transparent;
  font-size: 14px;
  line-height: 1.55;
  overflow-wrap: anywhere;
  white-space: pre-wrap;
  transform-origin: 0 0;
}

.agent-mention-highlight {
  margin: 0;
  padding: 0;
  border-radius: 3px;
  background: #cfe7dc;
  box-shadow: inset 0 0 0 1px rgba(23, 104, 79, 0.12);
  color: #125a43;
  font: inherit;
  font-weight: 800;
}

.composer-highlight-content .agent-mention-highlight {
  color: transparent;
  -webkit-text-fill-color: transparent;
}

.agent-mention-menu > button {
  width: 100%;
  min-height: 42px;
  display: grid;
  grid-template-columns: 30px minmax(0, 1fr);
  align-items: center;
  gap: 9px;
  padding: 6px 10px;
  border: 0 !important;
  border-radius: 0 !important;
  outline: 0 !important;
  background: transparent !important;
  box-shadow: none !important;
  color: #31443e;
  text-align: left;
  cursor: pointer;
}

.agent-mention-menu > button.active,
.agent-mention-menu > button:hover {
  border: 0 !important;
  outline: 0 !important;
  background: #dfe8e3 !important;
  box-shadow: none !important;
}

.agent-mention-menu > button > strong {
  min-width: 0;
  overflow: hidden;
  color: #31423d;
  font-size: 13px;
  font-weight: 700;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.pending-attachments {
  margin-bottom: 7px;
}

.pending-attachments > span {
  max-width: calc(50% - 3px);
}

.pending-attachments button {
  flex: 0 0 auto;
  width: 18px;
  height: 18px;
  display: grid;
  place-items: center;
  padding: 0;
  border: 0;
  border-radius: 50%;
  background: transparent;
  color: #527068;
}

.composer textarea {
  position: relative;
  z-index: 1;
  width: 100%;
  min-height: 52px;
  resize: none;
  border: 1px solid #e1eae6;
  border-radius: 12px;
  padding: 9px 10px;
  box-sizing: border-box;
  outline: 0;
  color: #213a39;
  font-size: 14px;
  line-height: 1.55;
  background: transparent;
}

.composer textarea.has-highlight-mirror {
  color: #213a39;
  caret-color: #213a39;
  -webkit-text-fill-color: #213a39;
}

.composer textarea.has-highlight-mirror::selection {
  background: rgba(36, 117, 88, 0.2);
}

.composer textarea::placeholder {
  color: #879590;
  -webkit-text-fill-color: #879590;
}

.composer textarea:focus {
  border-color: #b7d9ca;
}

.composer-actions {
  justify-content: space-between;
  gap: 8px;
  margin-top: 6px;
  border-top: 1px solid #eef3f0;
  padding-top: 6px;
}

.composer-input-tools {
  display: flex;
  align-items: center;
  gap: 4px;
}

.composer-tool {
  width: 28px;
  height: 28px;
  display: grid;
  place-items: center;
  padding: 0;
  border: 0;
  border-radius: 6px;
  background: transparent;
  color: #55706a;
}

.composer-tool:hover,
.composer-tool.active {
  border-color: #cce9df;
  background: #edf9f4;
  color: #0e9f6e;
}

.ghost-btn,
.send-btn,
.refresh-btn {
  min-height: 38px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 7px;
  border-radius: 999px;
  font-size: 13px;
  font-weight: 800;
  cursor: pointer;
}

.ghost-btn,
.refresh-btn {
  padding: 0 13px;
  border: 1px solid #d9eee8;
  background: #f6fffb;
  color: #0e9f6e;
}

.ghost-btn.active {
  border-color: #10b981;
  background: #ddf7ea;
}

.send-btn {
  min-width: 86px;
  border: 0;
  background: linear-gradient(135deg, #20c997, #0e9f6e);
  color: #fff;
  box-shadow: 0 10px 22px rgba(16, 185, 129, 0.22);
}

.send-btn:disabled {
  cursor: not-allowed;
  opacity: 0.55;
  box-shadow: none;
}

.status-toolbar {
  justify-content: space-between;
  gap: 12px;
  padding: 14px;
  border: 1px solid #e2f1ec;
  border-radius: 16px;
  background: #fff;
}

.status-toolbar strong {
  display: block;
  color: #172033;
  font-size: 14px;
}

.status-toolbar p {
  margin: 4px 0 0;
  color: #667a77;
  font-size: 12px;
}

.agent-list {
  max-height: 280px;
  overflow-y: auto;
  display: grid;
  gap: 8px;
}

.agent-row {
  gap: 10px;
  padding: 12px;
  border: 1px solid #e2f1ec;
  border-radius: 15px;
  background: rgba(255, 255, 255, 0.88);
}

.agent-row div {
  min-width: 0;
  flex: 1;
}

.agent-row strong {
  display: block;
  color: #213a39;
  font-size: 13px;
}

.agent-row p {
  overflow: hidden;
  margin: 4px 0 0;
  color: #667a77;
  font-size: 12px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.agent-row em {
  color: #0e9f6e;
  font-size: 12px;
  font-style: normal;
  font-weight: 800;
}

.status-log {
  padding: 14px;
  border-radius: 16px;
  background: #14211f;
  color: #dff8ed;
}

.status-log header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 10px;
}

.status-log p {
  margin: 0;
  color: #a5b9b4;
  font-size: 12px;
  line-height: 1.6;
}

.task-log-card {
  margin-top: 10px;
  padding: 10px;
  border: 1px solid rgba(221, 247, 234, 0.12);
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.06);
}

.task-log-main {
  width: 100%;
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 0;
  border: 0;
  background: transparent;
  color: #fff;
  text-align: left;
  cursor: pointer;
}

.task-log-title {
  min-width: 0;
  flex: 1;
}

.task-log-title strong,
.task-log-title small {
  display: block;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.task-log-title strong {
  color: #fff;
  font-size: 13px;
}

.task-log-title small {
  margin-top: 3px;
  color: #a5b9b4;
  font-size: 12px;
}

.task-log-main em {
  flex: 0 0 auto;
  color: #6ee7b7;
  font-size: 12px;
  font-style: normal;
  font-weight: 800;
}

.task-progress {
  height: 5px;
  margin-top: 9px;
  overflow: hidden;
  border-radius: 999px;
  background: rgba(221, 247, 234, 0.12);
}

.task-progress span {
  display: block;
  height: 100%;
  border-radius: inherit;
  background: linear-gradient(90deg, #10b981, #6ee7b7);
  transition: width 0.35s ease;
}

.task-agent-runs {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 9px;
}

.task-agent-runs span {
  max-width: 100%;
  padding: 3px 7px;
  border: 1px solid rgba(221, 247, 234, 0.14);
  border-radius: 999px;
  color: #c8f5e4;
  background: rgba(255, 255, 255, 0.06);
  font-size: 11px;
}

.task-agent-runs span.running,
.task-agent-runs span.queued {
  color: #bfdbfe;
  border-color: rgba(147, 197, 253, 0.2);
}

.task-agent-runs span.complete,
.task-agent-runs span.ready {
  color: #86efac;
  border-color: rgba(134, 239, 172, 0.2);
}

.task-orchestration {
  display: grid;
  gap: 7px;
  margin-top: 9px;
  padding-top: 8px;
  border-top: 1px solid rgba(221, 247, 234, 0.1);
}

.task-harness-meta {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr);
  gap: 2px 7px;
}

.task-harness-meta span {
  grid-row: 1 / span 2;
  align-self: stretch;
  display: grid;
  place-items: center;
  padding: 0 6px;
  border: 1px solid rgba(94, 234, 212, 0.24);
  border-radius: 5px;
  color: #5eead4;
  font-size: 9px;
  font-weight: 800;
}

.task-harness-meta strong,
.task-harness-meta small {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.task-harness-meta strong {
  color: #d7f7eb;
  font-size: 10px;
}

.task-harness-meta small {
  color: #8fa8a2;
  font-size: 9px;
}

.task-handoff-chain {
  display: flex;
  align-items: center;
  gap: 4px;
  min-width: 0;
  overflow-x: auto;
  color: #9fb5b0;
  scrollbar-width: thin;
}

.task-handoff-chain span {
  flex: 0 0 auto;
  max-width: 112px;
  overflow: hidden;
  color: #d7f7eb;
  font-size: 10px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.task-handoff-chain svg {
  flex: 0 0 auto;
  color: #5eead4;
}

.task-review {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  color: #86efac;
}

.task-review.warning {
  color: #fcd34d;
}

.task-review strong,
.task-review small {
  font-size: 10px;
  line-height: 1.35;
}

.task-review small {
  color: #9fb5b0;
  text-align: right;
}

.task-mini-log {
  display: grid;
  gap: 4px;
  margin: 9px 0 0;
  padding: 0;
  list-style: none;
}

.task-mini-log li {
  overflow: hidden;
  color: #9fb5b0;
  font-size: 11px;
  line-height: 1.35;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* APIMart-style monochrome treatment for the complete assistant surface. */
.title-block .eyebrow,
.runtime-settings-head span,
.runtime-settings-panel label > span,
.runtime-security-note svg,
.resource-card .card-icon,
.ohmyppt-embed-head svg,
.ohmyppt-embed-head em,
.ohmyppt-embed-foot span,
.ohmyppt-frame-cover,
.preview-overlay-head span,
.agent-row em {
  color: #4e5554;
}

.title-block strong,
.runtime-settings-head strong,
.harness-summary strong,
.empty-chat strong,
.status-toolbar strong,
.agent-row strong,
.preview-overlay-head strong {
  color: #171919;
}

.title-block p,
.runtime-toggle small,
.harness-summary span,
.empty-chat p,
.resource-card small,
.ohmyppt-embed-foot small,
.status-toolbar p,
.agent-row p {
  color: #737a79;
}

.runtime-settings-head {
  border-color: #e2e5e4;
}

.runtime-settings-panel input[type='url'],
.runtime-settings-panel input[type='text'],
.runtime-settings-panel select {
  border-color: #dadddc;
  border-radius: 6px;
  color: #202323;
}

.runtime-settings-panel input:focus,
.runtime-settings-panel select:focus {
  border-color: #176f4b;
  box-shadow: 0 0 0 3px rgba(23, 111, 75, 0.1);
}

.runtime-settings-panel input:disabled,
.runtime-settings-panel select:disabled,
.runtime-toggle,
.runtime-settings-message,
.runtime-settings-message.success,
.runtime-settings-message.error,
.harness-summary {
  border-color: #e1e4e3;
  background: #f5f6f6;
  color: #525958;
}

.runtime-toggle {
  border-radius: 6px;
}

.runtime-toggle input {
  accent-color: #176f4b;
}

.runtime-security-note {
  border-left-color: #176f4b;
  background: #f8fbf9;
  color: #565d5c;
}

.icon-btn {
  border-color: #dde1e0;
  border-radius: 6px;
  background: #ffffff;
  color: #4d5553;
}

.mode-tabs {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  width: 100%;
  gap: 4px;
  padding: 4px;
  box-sizing: border-box;
  border-color: #e0e3e2;
  border-radius: 8px;
  background: #f3f4f4;
}

.mode-tabs button {
  width: 100%;
  min-width: 0;
  box-sizing: border-box;
  min-height: 36px;
  border-radius: 6px;
  color: #626968;
}

.mode-tabs button.active {
  background: #176f4b;
  color: #ffffff;
  box-shadow: none;
}

.empty-chat,
.bubble,
.resource-card,
.ohmyppt-embed-card,
.task-preview-overlay,
.composer,
.status-toolbar,
.agent-row {
  border-color: #e1e4e3;
  border-radius: 8px;
  background: #ffffff;
  box-shadow: none;
}

.empty-chat {
  background: #ffffff;
}

.empty-chat svg,
.resource-card > svg {
  color: #747b7a;
}

.message.user .bubble {
  border-color: #c9dbd1;
  background: #f0f7f3;
  color: #24312c;
}

.message-attachments a,
.pending-attachments > span {
  border-color: #dfe3e2;
  background: #f5f6f6;
  color: #454c4b;
}

.resource-card:hover {
  border-color: #aeb5b4;
  background: #ffffff;
  transform: none;
}

.resource-card .card-icon {
  border-radius: 6px;
  background: #eceeee;
}

.ohmyppt-frame-shell {
  border-color: #dfe3e2;
  border-radius: 8px;
  background: #f3f4f4;
}

.ohmyppt-frame-shell iframe {
  background: #f3f4f4;
}

.ohmyppt-frame-cover {
  border: 1px solid #dfe3e2;
  border-radius: 6px;
  background: #ffffff;
  box-shadow: none;
}

.task-state,
.agent-light {
  background: #9ca2a1;
  box-shadow: none;
}

.task-state.running,
.task-state.queued,
.agent-light.running,
.agent-light.queued {
  background: #666d6c;
  box-shadow: none;
}

.task-state.complete,
.task-state.ready,
.agent-light.complete,
.agent-light.ready {
  background: #176f4b;
  box-shadow: none;
}

.task-state.failed,
.agent-light.failed {
  background: #4f5554;
  box-shadow: none;
}

.composer-tool,
.pending-attachments button {
  color: #555c5b;
}

.composer-tool:hover,
.composer-tool.active {
  border-color: #d4d8d7;
  background: #eff1f0;
  color: #171919;
}

.ghost-btn,
.refresh-btn {
  border-color: #d8dcdb;
  border-radius: 6px;
  background: #ffffff;
  color: #353b3a;
}

.ghost-btn.active {
  border-color: #9ab8aa;
  background: #edf5f1;
  color: #176f4b;
}

.send-btn {
  border-radius: 6px;
  background: #176f4b;
  color: #ffffff;
  box-shadow: none;
}

.status-log {
  border-radius: 8px;
  background: #202323;
  color: #f5f6f6;
}

.task-log-card {
  border-color: rgba(255, 255, 255, 0.14);
  border-radius: 6px;
}

.task-log-main em,
.task-review,
.task-review.warning,
.task-handoff-chain svg,
.task-agent-runs span,
.task-agent-runs span.running,
.task-agent-runs span.queued,
.task-agent-runs span.complete,
.task-agent-runs span.ready {
  color: #d2d6d5;
  border-color: rgba(255, 255, 255, 0.15);
}

.task-progress span {
  background: #176f4b;
}

.title-block .eyebrow,
.runtime-settings-head span,
.ohmyppt-embed-head em,
.ohmyppt-embed-foot span,
.agent-row em {
  color: #176f4b;
}

.chat-scroll-area,
.runtime-settings-panel,
.agent-list {
  scrollbar-color: #c4c9c8 transparent;
}

.composer-error {
  display: flex;
  align-items: flex-start;
  gap: 7px;
  margin: 6px 0 0;
  padding: 8px 9px;
  border-left: 3px solid #dc5b5b;
  background: #fff5f5;
  color: #9d3030;
  font-size: 11px;
  line-height: 1.45;
}

.composer-error svg {
  flex: 0 0 auto;
  margin-top: 1px;
}

.task-preview-message {
  width: 100%;
  margin: 8px 0 12px;
}

.task-preview-bubble {
  min-width: 0;
  width: 94%;
  max-width: 380px;
  display: grid;
  gap: 8px;
  padding: 9px;
  box-sizing: border-box;
  border: 1px solid #e0e4e3;
  border-radius: 8px;
  background: #ffffff;
  color: #202525;
  text-decoration: none;
  transition: border-color 160ms ease, box-shadow 160ms ease, transform 160ms ease;
  animation: taskCardEnter 220ms ease-out both;
}

.task-preview-bubble:hover {
  border-color: #a9bbb4;
  box-shadow: 0 7px 16px rgba(30, 45, 40, 0.08);
  transform: translateY(-1px);
}

.task-preview-bubble.running,
.task-preview-bubble.queued {
  border-color: #b9d5e8;
  background: #fbfdff;
}

.task-preview-bubble.failed {
  border-color: #edc5c5;
  background: #fffafa;
}

.task-preview-head,
.task-preview-foot {
  min-width: 0;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.task-preview-head span {
  min-width: 0;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  color: #176f4b;
  font-size: 10px;
  font-weight: 800;
}

.task-preview-head time {
  flex: 0 0 auto;
  color: #828987;
  font-size: 9px;
}

.task-preview-frame {
  position: relative;
  height: 158px;
  display: block;
  overflow: hidden;
  border: 1px solid #e2e6e5;
  border-radius: 6px;
  background: #f3f5f4;
}

.task-preview-frame iframe {
  width: 1280px;
  height: 720px;
  display: block;
  border: 0;
  background: #f3f5f4;
  pointer-events: none;
  transform: scale(0.285);
  transform-origin: top left;
}

.task-preview-open {
  position: absolute;
  right: 8px;
  bottom: 8px;
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 5px 7px;
  border: 1px solid #d8dddb;
  border-radius: 6px;
  background: rgba(255, 255, 255, 0.94);
  color: #176f4b;
  font-size: 10px;
  font-weight: 800;
}

.task-preview-foot strong,
.task-preview-foot span {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.task-preview-foot strong {
  color: #252a29;
  font-size: 11px;
}

.task-preview-foot span {
  max-width: 46%;
  color: #737a79;
  font-size: 9px;
  text-align: right;
}

.agent-node-icon {
  display: grid;
  place-items: center;
  flex: 0 0 auto;
  border-radius: 7px;
}

.companion-task-progress {
  width: 100%;
  height: 3px;
  display: block;
  overflow: hidden;
  margin-top: 4px;
  border-radius: 2px;
  background: #e6ebea;
}

.companion-task-progress b {
  height: 100%;
  display: block;
  border-radius: inherit;
  background: #3b82b8;
  transition: width 240ms ease;
}

.refresh-btn.icon-only {
  width: 34px;
  min-width: 34px;
  height: 34px;
  min-height: 34px;
  padding: 0;
}

.agent-topology {
  min-width: 0;
  display: flex;
  flex-direction: column;
  padding: 0 4px 16px;
}

.topology-activity {
  min-width: 0;
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 10px;
  padding: 9px 10px;
  border-left: 3px solid #176f4b;
  background: #f4f7f5;
  color: #4e5754;
  font-size: 11px;
}

.topology-activity svg {
  flex: 0 0 auto;
  color: #176f4b;
}

.topology-activity span {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.runtime-run-picker {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr);
  align-items: center;
  gap: 9px;
  padding: 0 4px 10px;
}

.runtime-run-picker label {
  color: #5d6965;
  font-size: 10px;
  font-weight: 800;
}

.runtime-run-picker select {
  min-width: 0;
  height: 34px;
  border: 1px solid #d9dfdc;
  border-radius: 6px;
  padding: 0 28px 0 9px;
  background: #ffffff;
  color: #26302d;
  font-size: 10px;
  outline: none;
}

.runtime-run-picker select:focus {
  border-color: #79a995;
  box-shadow: 0 0 0 2px rgba(23, 111, 75, 0.09);
}

.real-run-summary {
  padding: 12px;
  border: 1px solid #dce4e0;
  border-radius: 7px;
  background: #ffffff;
}

.real-run-summary header,
.actual-agent-section > header,
.handoff-section > header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.real-run-summary header span,
.real-run-summary header em,
.actual-agent-section > header span,
.handoff-section > header span {
  color: #67736f;
  font-size: 9px;
  font-style: normal;
  font-weight: 800;
}

.real-run-summary header em {
  padding: 3px 6px;
  border-radius: 4px;
  background: #edf3f0;
}

.real-run-summary header em.complete {
  color: #176f4b;
  background: #eaf5f0;
}

.real-run-summary header em.failed {
  color: #9b3f3f;
  background: #fff0f0;
}

.real-run-summary > strong {
  display: -webkit-box;
  overflow: hidden;
  margin-top: 8px;
  color: #1f2825;
  font-size: 13px;
  line-height: 1.45;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
}

.real-run-summary > p {
  margin: 5px 0 0;
  color: #7b8481;
  font-size: 9px;
}

.real-run-summary dl {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  margin: 12px 0 0;
  border-top: 1px solid #edf0ee;
  padding-top: 10px;
}

.real-run-summary dl div {
  min-width: 0;
  display: grid;
  gap: 2px;
  text-align: center;
}

.real-run-summary dt {
  color: #7b8581;
  font-size: 8px;
}

.real-run-summary dd {
  margin: 0;
  color: #26332f;
  font-size: 14px;
  font-weight: 900;
}

.harness-flow-section {
  display: grid;
  gap: 9px;
  margin-top: 2px;
  padding: 10px;
  border: 1px solid #e2efe9;
  border-radius: 10px;
  background: linear-gradient(135deg, #f7fffc, #fff);
}

.harness-flow-section > header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.harness-flow-section > header strong {
  color: #26332f;
  font-size: 11px;
}

.harness-flow-section > header span {
  color: #6f7a76;
  font-size: 9px;
}

.harness-flow-canvas {
  display: flex;
  align-items: center;
  gap: 2px;
  min-width: 0;
  overflow-x: auto;
  padding-bottom: 4px;
}

.harness-flow-node {
  position: relative;
  flex: 1 0 76px;
  min-width: 76px;
  min-height: 78px;
  display: grid;
  justify-items: center;
  align-content: center;
  gap: 4px;
  padding: 8px 6px;
  border: 1px solid #dfe8e4;
  border-radius: 8px;
  background: #fff;
  cursor: pointer;
  transition: border-color .18s ease, box-shadow .18s ease, transform .18s ease;
}

.harness-flow-node:hover,
.harness-flow-node.active {
  border-color: #6fbf9c;
  box-shadow: 0 8px 18px rgba(23,111,75,.11);
  transform: translateY(-1px);
}

.harness-flow-node.master {
  border-color: #176f4b;
  background: #176f4b;
  color: #fff;
}

.harness-flow-node.master small {
  color: #d7f0e5;
}

.harness-flow-node.generate {
  border-color: #a8c8db;
  background: #f6fbff;
}

.harness-flow-node.review {
  border-color: #c9ad77;
  background: #fffaf0;
}

.harness-flow-node.idle {
  border-style: dashed;
  opacity: .74;
}

.harness-flow-node.running,
.harness-flow-node.queued {
  border-color: #72b8e0;
  background: #f8fcff;
}

.harness-flow-node.failed {
  border-color: #d98282;
  background: #fff8f8;
}

.harness-node-icon {
  width: 25px;
  height: 25px;
  display: grid;
  place-items: center;
  border-radius: 7px;
  background: #ecf5f0;
  color: #3b705e;
}

.harness-flow-node.master .harness-node-icon {
  background: rgba(255,255,255,.15);
  color: #fff;
}

.harness-flow-node strong {
  max-width: 100%;
  overflow: hidden;
  color: inherit;
  font-size: 9px;
  line-height: 1.25;
  text-align: center;
  text-overflow: ellipsis;
  display: -webkit-box;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
}

.harness-flow-node small {
  color: #72807b;
  font-size: 8px;
}

.harness-node-light {
  position: absolute;
  top: 5px;
  right: 5px;
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #b7c1bd;
}

.harness-flow-node.running .harness-node-light,
.harness-flow-node.queued .harness-node-light { background: #3aa0dc; }
.harness-flow-node.complete .harness-node-light { background: #16a34a; }
.harness-flow-node.failed .harness-node-light { background: #dc2626; }
.harness-flow-node.review .harness-node-light { background: #c8a267; }

.harness-flow-link {
  flex: 0 0 auto;
  min-width: 43px;
  display: grid;
  justify-items: center;
  gap: 1px;
  border: 0;
  background: transparent;
  color: #4e7d6b;
  cursor: pointer;
}

.harness-flow-link span {
  color: #73827c;
  font-size: 7px;
  font-weight: 800;
  white-space: nowrap;
}

.harness-loop-rail {
  display: flex;
  gap: 6px;
  padding-top: 8px;
  border-top: 1px dashed #d7e5de;
}

.harness-loop-edge {
  flex: 1;
  min-width: 0;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 5px;
  min-height: 27px;
  padding: 4px 7px;
  border: 1px solid #d9c48f;
  border-radius: 999px;
  background: #fffaf0;
  color: #7a5d22;
  cursor: pointer;
}

.harness-loop-edge.assessment {
  border-color: #9ec5dd;
  background: #f5fbff;
  color: #38607a;
}

.harness-loop-edge span {
  overflow: hidden;
  font-size: 8px;
  font-weight: 900;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.harness-loop-edge:hover {
  filter: brightness(.985);
}

.harness-runtime-brief {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 7px;
}

.harness-brief-card {
  min-width: 0;
  padding: 8px;
  border: 1px solid #e3e8e5;
  border-radius: 8px;
  background: #fff;
}

.harness-brief-card strong {
  color: #33413c;
  font-size: 9px;
}

.harness-brief-card p {
  margin: 4px 0 0;
  color: #6f7a76;
  font-size: 9px;
  line-height: 1.4;
  display: -webkit-box;
  overflow: hidden;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
}

.harness-node-overlay {
  position: fixed;
  z-index: 1290;
  inset: 0;
  display: grid;
  place-items: center;
  padding: 24px;
  background: rgba(18, 27, 24, .44);
}

.harness-node-detail {
  width: min(430px, 100%);
  max-height: min(430px, calc(100vh - 48px));
  overflow-y: auto;
  border: 1px solid #d8e5df;
  border-radius: 12px;
  background: #fff;
  box-shadow: 0 20px 42px rgba(15,23,20,.22);
}

.harness-node-detail header {
  position: sticky;
  top: 0;
  display: grid;
  grid-template-columns: 34px minmax(0,1fr) 32px;
  gap: 9px;
  align-items: center;
  padding: 13px;
  border-bottom: 1px solid #e9eeec;
  background: #fff;
}

.harness-node-detail header span {
  width: 34px;
  height: 34px;
  display: grid;
  place-items: center;
  border-radius: 9px;
  background: #e8f4ef;
  color: #176f4b;
}

.harness-node-detail header small {
  color: #71807a;
  font-size: 9px;
}

.harness-node-detail header strong {
  color: #22302c;
  font-size: 13px;
}

.harness-node-detail header button {
  width: 30px;
  height: 30px;
  display: grid;
  place-items: center;
  border: 1px solid #e0e7e3;
  border-radius: 8px;
  background: #fff;
  color: #5c6b65;
  cursor: pointer;
}

.harness-node-detail dl {
  display: grid;
  gap: 7px;
  margin: 0;
  padding: 11px 13px;
}

.harness-node-detail dl div {
  display: grid;
  gap: 2px;
}

.harness-node-detail dt {
  color: #77827d;
  font-size: 8px;
  font-weight: 900;
}

.harness-node-detail dd {
  margin: 0;
  color: #2a3531;
  font-size: 11px;
  line-height: 1.45;
}

.harness-node-handoffs {
  padding: 0 13px 13px;
}

.harness-node-handoffs strong {
  color: #33413c;
  font-size: 9px;
}

.harness-node-handoffs p {
  margin: 6px 0 0;
  padding: 8px;
  border: 1px solid #e6ebe8;
  border-radius: 7px;
  background: #fbfdfc;
  color: #47544f;
  font-size: 9px;
  line-height: 1.4;
}

.harness-node-handoffs small {
  display: block;
  margin-top: 3px;
  color: #727d78;
}

.harness-node-handoffs p.empty {
  border-style: dashed;
  color: #76817c;
}

.real-run-empty {
  border: 1px dashed #d8dfdc;
  border-radius: 7px;
  padding: 18px 14px;
  color: #6f7a76;
  background: #fafbfa;
  font-size: 10px;
  text-align: center;
}

.real-run-empty {
  min-height: 180px;
  display: grid;
  align-content: center;
  justify-items: center;
  gap: 7px;
}

.real-run-empty svg {
  color: #568371;
}

.real-run-empty strong {
  color: #2b3732;
  font-size: 12px;
}

.real-run-empty p {
  max-width: 270px;
  margin: 0;
  line-height: 1.55;
}

.agent-light.running,
.agent-light.queued {
  background: #3f88b8;
  animation: agentStatusPulse 1.5s ease-in-out infinite;
}

.agent-light.failed {
  background: #c85353;
}

@keyframes taskCardEnter {
  from {
    opacity: 0;
    transform: translateY(4px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

@keyframes agentStatusPulse {
  0%, 100% {
    box-shadow: 0 0 0 0 rgba(63, 136, 184, 0.16);
  }
  50% {
    box-shadow: 0 0 0 4px rgba(63, 136, 184, 0.08);
  }
}

@keyframes xiaozhiPulse {
  0%, 100% {
    transform: scale(0.9);
    opacity: 0.32;
  }
  50% {
    transform: scale(1.08);
    opacity: 0.72;
  }
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

@media (max-width: 768px) and (orientation: portrait) {
  .xiaozhi-float {
    z-index: 1190;
    width: 58px;
    height: 58px;
  }

  .xiaozhi-orb {
    width: 58px;
    height: 58px;
  }

  .xiaozhi-orb-logo {
    width: 50px;
    height: 50px;
  }

  .xiaozhi-window {
    position: fixed;
    left: 12px !important;
    right: 12px !important;
    bottom: calc(96px + env(safe-area-inset-bottom)) !important;
    top: auto !important;
    width: auto;
    max-height: min(620px, calc(100vh - 130px));
    height: min(620px, calc(100vh - 130px));
    padding: 16px;
    border-radius: 10px;
  }

  .xiaozhi-window.right,
  .xiaozhi-window.left {
    left: 12px;
    right: 12px;
  }

  .harness-flow-canvas {
    align-items: stretch;
    overflow-x: hidden;
  }

  .harness-flow-node {
    flex: 1 1 62px;
    min-width: 62px;
    min-height: 70px;
    padding: 6px 4px;
  }

  .harness-flow-link {
    min-width: 28px;
  }

  .harness-flow-link span {
    display: none;
  }

  .harness-loop-rail {
    flex-direction: column;
  }

  .harness-runtime-brief {
    grid-template-columns: 1fr;
  }

  .harness-node-overlay {
    padding: 12px;
  }

  .task-preview-bubble {
    width: 100%;
  }

  .task-preview-frame {
    height: 140px;
  }

  .task-preview-frame iframe {
    transform: scale(0.24);
  }

  .composer-actions {
    flex-wrap: wrap;
  }

  .send-btn {
    flex: 1;
  }
}

@media (prefers-reduced-motion: reduce) {
  .orb-pulse,
  .task-preview-bubble,
  .agent-light.running,
  .agent-light.queued {
    animation: none !important;
  }
}
</style>
