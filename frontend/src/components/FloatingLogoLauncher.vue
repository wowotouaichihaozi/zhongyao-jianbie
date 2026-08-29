<template>
  <div
    class="xiaozhi-float"
    :class="{ dragging: isDragging, open: isOpen }"
    :style="floatStyle"
    @pointerdown="handlePointerDown"
  >
    <button class="xiaozhi-orb" type="button" aria-label="打开岐小智" @click.prevent>
      <picture>
        <img class="xiaozhi-orb-logo" src="/qihuang-zhijing-mark-512.png" alt="岐小智" draggable="false" decoding="async" />
      </picture>
      <span class="orb-pulse" aria-hidden="true"></span>
      <span v-if="runningTaskCount" class="task-dot">{{ runningTaskCount }}</span>
    </button>

    <Transition name="motion-pop">
    <section v-if="isOpen" class="xiaozhi-window" :class="windowPlacement" :style="windowStyle" @pointerdown.stop>
      <header class="window-head">
        <div class="title-block">
          <span class="eyebrow">Learning Companion</span>
          <strong>岐小智</strong>
          <p>陪你研读经典、辨析方药的中医学习伙伴</p>
        </div>
        <div class="window-head-actions">
          <button type="button" class="icon-btn" aria-label="智能体运行设置" title="智能体运行设置" @click.stop="openRuntimeSettings">
            <Settings :size="18" />
          </button>
          <button type="button" class="icon-btn" aria-label="关闭岐小智" @click.stop="isOpen = false">
            <X :size="18" />
          </button>
        </div>
      </header>

      <div class="mode-tabs" role="tablist" aria-label="岐小智功能">
        <button type="button" :class="{ active: activeTab === 'chat' }" @click="activeTab = 'chat'">
          <MessageCircle :size="16" />
          陪伴式助手
        </button>
        <button type="button" :class="{ active: activeTab === 'status' }" @click="openStatusTab">
          <Activity :size="16" />
          Agent Harness
        </button>
      </div>

      <Transition name="motion-panel" mode="out-in">
      <form v-if="showRuntimeSettings" key="settings" class="runtime-settings-panel" @submit.prevent="saveRuntimeSettings">
        <header class="runtime-settings-head">
          <div>
            <span>Agent Harness</span>
            <strong>智能体运行设置</strong>
          </div>
          <button type="button" class="icon-btn" aria-label="关闭设置" @click="showRuntimeSettings = false">
            <X :size="17" />
          </button>
        </header>

        <label class="runtime-toggle">
          <span>
            <strong>使用自定义模型配置</strong>
            <small>关闭后使用平台统一配置</small>
          </span>
          <input v-model="runtimeSettings.enabled" type="checkbox" />
        </label>

        <label>
          <span>调用协议</span>
          <select v-model="runtimeSettings.protocol" :disabled="!runtimeSettings.enabled">
            <option value="openai">讯飞 OpenAI 兼容接口</option>
            <option value="anthropic">讯飞 Anthropic 兼容接口</option>
          </select>
        </label>

        <label>
          <span>API 地址</span>
          <input
            v-model.trim="runtimeSettings.baseUrl"
            type="url"
            :disabled="!runtimeSettings.enabled"
            placeholder="https://maas-coding-api.cn-huabei-1.xf-yun.com/v2"
          />
        </label>

        <label>
          <span>模型名</span>
          <input
            v-model.trim="runtimeSettings.model"
            type="text"
            :disabled="!runtimeSettings.enabled"
            placeholder="astron-code-latest"
          />
        </label>

        <div class="runtime-security-note">
          <ShieldCheck :size="16" />
          <span>沿用平台服务端凭据；API 地址必须位于安全白名单，不会在浏览器保存密钥。</span>
        </div>

        <p v-if="runtimeSettingsMessage" :class="['runtime-settings-message', runtimeSettingsState]">
          {{ runtimeSettingsMessage }}
        </p>

        <footer class="runtime-settings-actions">
          <button type="button" class="ghost-btn" @click="usePlatformRuntime">平台默认</button>
          <button type="button" class="ghost-btn" :disabled="testingRuntime" @click="testRuntimeSettings">
            {{ testingRuntime ? '测试中' : '测试连接' }}
          </button>
          <button class="send-btn" type="submit" :disabled="savingRuntime || testingRuntime">
            {{ savingRuntime ? (runtimeSettings.enabled ? '测试并保存中' : '保存中') : (runtimeSettings.enabled ? '测试并保存' : '保存设置') }}
          </button>
        </footer>
      </form>

      <div v-else-if="activeTab === 'chat'" key="chat" class="chat-panel">
        <div ref="messageListRef" class="chat-scroll-area">
          <div class="message-list">
          <div v-if="messages.length === 0 && agentConversationGroups.length === 0 && !agentConversation?.summary" class="empty-chat">
            <Sparkles :size="22" />
            <strong>你好，我是岐小智</strong>
            <p>我会记录你的学习画像、答题和研读状态。你也可以直接让我生成 PPT、思维导图、视频或题库。</p>
          </div>

          <section
            class="agent-group-chat"
            aria-label="当前学习画像的多智能体群聊"
          >
            <header class="agent-group-chat-head">
              <span><Network :size="15" />画像协同群聊</span>
              <small>{{ agentConversation?.messageCount || 0 }} 条记录</small>
            </header>

            <article v-if="!agentConversationGroups.length && !agentConversation?.summary" class="agent-conversation-empty">
              <strong>暂无协同记录</strong>
              <span>发送消息、生成学习路径或创建资源后，岐小智和各专家智能体的动作会写入这里。</span>
            </article>

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
                <span class="agent-conversation-icon">
                  <LoaderCircle v-if="group.status === 'running'" class="spin" :size="15" />
                  <CircleAlert v-else-if="group.status === 'failed'" :size="15" />
                  <Network v-else :size="15" />
                </span>
                <span class="agent-conversation-copy">
                  <small>{{ group.agentNames }} · {{ conversationStatusLabel(group.status) }}</small>
                  <strong>{{ group.title }}</strong>
                  <em>{{ group.summary }}</em>
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
                    <span class="conversation-entry-marker"></span>
                    <div>
                      <header>
                        <strong>{{ entry.agentName || entry.agentId }}</strong>
                        <time>{{ formatConversationTime(entry.createdAt) }}</time>
                      </header>
                      <p>{{ entry.content }}</p>
                      <small v-if="conversationDetailText(entry)">{{ conversationDetailText(entry) }}</small>
                      <span v-if="entry.resourceReferences?.length" class="conversation-references">
                        <i v-for="reference in entry.resourceReferences.slice(0, 6)" :key="`${reference.type}-${reference.id}`">
                          {{ reference.type }} · {{ reference.id }}
                        </i>
                      </span>
                    </div>
                  </li>
                </ol>
                <a
                  v-if="group.route"
                  class="conversation-resource-link"
                  :href="resolveRouteHref(group.route)"
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  打开对应资源
                  <ExternalLink :size="14" />
                </a>
              </div>
            </article>
          </section>

          <template v-for="(message, index) in messages" :key="`${message.createdAt || index}-${index}`">
            <article class="message" :class="message.role">
              <div class="bubble">
                <p>{{ message.content }}</p>
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

          <article v-if="isSending" class="message assistant pending">
            <div class="bubble">
              <LoaderCircle :size="16" class="spin" />
              <p>岐小智正在分析你的学习上下文...</p>
            </div>
          </article>
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
          <textarea
            v-model="draft"
            rows="2"
            placeholder="告诉岐小智你的学习情况，或说：生成八纲辨证课程的 PPT..."
            @keydown="handleComposerKeydown"
          ></textarea>
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

      <div v-else key="status" class="status-panel">
        <div class="status-toolbar">
          <div>
            <strong>智能体连接状态</strong>
            <p>岐小智总控与专项智能体实时编排拓扑</p>
          </div>
          <button type="button" class="refresh-btn icon-only" title="刷新智能体状态" aria-label="刷新智能体状态" @click="loadStatus">
            <RefreshCw :size="16" />
          </button>
        </div>

        <div v-if="harnessStatus" class="harness-summary">
          <span><strong>Harness</strong>{{ harnessStatus.version || '1.0.0' }}</span>
          <span><strong>{{ harnessStatus.skillRegistry?.skillCount || 0 }}</strong> Skills</span>
          <span><strong>{{ harnessStatus.mcpGateway?.toolCount || 0 }}</strong> MCP Tools</span>
          <span><strong>{{ harnessStatus.mcpGateway?.servers?.length || 0 }}</strong> MCP Servers</span>
        </div>

        <section class="agent-topology" aria-label="岐小智智能体连接流程图">
          <div class="topology-activity">
            <Activity :size="15" />
            <span>{{ harnessActivityText }}</span>
          </div>

          <article :class="['master-agent-node', normalizeStatus(masterAgent.status)]">
            <span class="agent-node-icon"><BrainCircuit :size="20" /></span>
            <span class="agent-node-copy">
              <small>Supervisor</small>
              <strong>{{ agentDisplayName(masterAgent) }}</strong>
              <span>{{ masterAgent.detail }}</span>
            </span>
            <em><i :class="['agent-light', normalizeStatus(masterAgent.status)]"></i>{{ statusText(masterAgent.status) }}</em>
          </article>

          <div class="flow-trunk" aria-hidden="true">
            <span></span>
            <small>Harness 调度通道</small>
          </div>

          <div class="specialist-flow-grid">
            <article
              v-for="agent in specialistAgents"
              :key="agent.id"
              :class="['specialist-agent-node', normalizeStatus(agent.status)]"
              :title="agent.detail"
            >
              <span class="agent-node-icon"><component :is="agentIcon(agent)" :size="17" /></span>
              <span class="agent-node-copy">
                <small>{{ agentRoleText(agent) }}</small>
                <strong>{{ agentDisplayName(agent) }}</strong>
              <span>{{ agentDetail(agent) }}</span>
              </span>
              <i :class="['agent-light', normalizeStatus(agent.status)]" :title="statusText(agent.status)"></i>
            </article>
          </div>
        </section>
      </div>
      </Transition>
    </section>
    </Transition>
  </div>
</template>

<script setup>
import { computed, markRaw, nextTick, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  Activity,
  Archive,
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
  Map,
  MessageCircle,
  Mic,
  Network,
  Paperclip,
  Presentation,
  RefreshCw,
  Search,
  SendHorizontal,
  Settings,
  ShieldCheck,
  Sparkles,
  Video,
  X,
} from 'lucide-vue-next'
import ResourceTaskStatusBanner from './ResourceTaskStatusBanner.vue'
import {
  chatWithXiaoZhi,
  getXiaoZhiHistory,
  getXiaoZhiRuntimeSettings,
  getXiaoZhiStatus,
  logXiaoZhiEvent,
  saveXiaoZhiRuntimeSettings,
  testXiaoZhiRuntimeSettings,
  uploadMultimodalInputs,
} from '../services/api.js'
import { useGlobalDebug } from '../stores/globalDebug.js'
import { XIAOZHI_WORKFLOW_EVENT } from '../utils/xiaozhiWorkflowProgress.js'

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
const messages = ref([])
const agentConversation = ref(null)
const expandedConversationGroups = ref(new Set())
const tasks = ref([])
const agents = ref([])
const harnessStatus = ref(null)
const showRuntimeSettings = ref(false)
const savingRuntime = ref(false)
const testingRuntime = ref(false)
const runtimeSettingsMessage = ref('')
const runtimeSettingsState = ref('info')
const runtimeSettings = reactive({
  enabled: false,
  protocol: 'openai',
  baseUrl: 'https://maas-coding-api.cn-huabei-1.xf-yun.com/v2',
  model: 'astron-code-latest',
})
const messageListRef = ref(null)
const viewport = reactive({ width: window.innerWidth, height: window.innerHeight })
const position = reactive(loadPosition())
let pointerState = null
let statusTimer = null
let recognition = null
let lastWorkflowCardId = ''

const iconMap = {
  learning_background: markRaw(MessageCircle),
  learning_path: markRaw(Map),
  learning_path_stage: markRaw(Map),
  personalized_resources: markRaw(Sparkles),
  ppt: markRaw(Presentation),
  mindmap: markRaw(Map),
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

const companionTaskTypes = new Set(
  Object.keys(resourceLabels).filter(type => !['profile_management', 'learning_feedback', 'mcu'].includes(type)),
)

const agentNameAliases = {
  'learner-context-agent': '学习上下文智能体',
  'course-knowledge-retrieval-agent': '课程知识检索智能体',
  'skill-registry-agent': 'Skill 注册智能体',
  'mcp-tool-gateway': 'MCP 工具网关',
  'quality-review-agent': '质量审核智能体',
  'content-safety-agent': '内容安全智能体',
  'learning-feedback-agent': '学习反馈智能体',
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
  const width = Math.max(1, Math.min(440, viewport.width - viewportPadding * 2))
  const height = Math.max(1, Math.min(660, viewport.height - viewportPadding * 2))
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
const canSendMessage = computed(() => !isSending.value && Boolean(draft.value.trim() || pendingAttachments.value.length))
const masterAgent = computed(() => agents.value.find(agent => agent.role === 'supervisor') || {
  id: 'xiaozhi-companion-agent',
  name: '岐小智总控智能体',
  status: 'idle',
  detail: '正在连接 Agent Harness',
})
const specialistAgents = computed(() => agents.value.filter(agent => {
  const identity = `${agent.id || ''} ${agent.type || ''}`.toLowerCase()
  return agent.id !== masterAgent.value.id && !identity.includes('mcu') && !identity.includes('simulator')
}))
const harnessActivityText = computed(() => {
  const activeAgent = agents.value.find(agent => ['running', 'queued'].includes(agent.status))
  if (activeAgent) return `${agentDisplayName(activeAgent)}：${activeAgent.detail || statusText(activeAgent.status)}`
  const failedAgent = agents.value.find(agent => agent.status === 'failed')
  if (failedAgent) return `${agentDisplayName(failedAgent)}需要处理：${failedAgent.detail || '执行失败'}`
  return '所有智能体已连接，等待岐小智总控调度'
})
const agentConversationGroups = computed(() => {
  const recentMessages = Array.isArray(agentConversation.value?.recentMessages)
    ? agentConversation.value.recentMessages
    : []
  const grouped = new Map()
  for (const entry of recentMessages) {
    if (!entry || ['user_message', 'supervisor_reply'].includes(String(entry.type || ''))) continue
    const key = String(entry.runId || entry.taskId || `message-${entry.id || entry.sequence}`)
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
    const statuses = group.messages.map(entry => String(entry.status || ''))
    const status = statuses.some(value => ['failed', 'error', 'needs_attention'].includes(value))
      ? 'failed'
      : statuses.some(value => ['running', 'queued'].includes(value))
        ? 'running'
        : statuses.some(value => value === 'warning') ? 'warning' : 'complete'
    const progress = Math.max(
      0,
      ...group.messages.map(entry => Number(entry.payload?.progress || entry.payload?.details?.progress || 0)),
    )
    const names = Array.from(new Set(group.messages.map(entry => entry.agentName || entry.agentId).filter(Boolean)))
    const routeReference = group.messages
      .flatMap(entry => Array.isArray(entry.resourceReferences) ? entry.resourceReferences : [])
      .find(reference => reference?.type === 'route')
    const lastMessage = group.messages.at(-1) || {}
    return {
      ...group,
      status,
      progress,
      agentNames: names.slice(0, 2).join('、') + (names.length > 2 ? ` 等 ${names.length} 个智能体` : ''),
      title: relatedTask?.title || group.messages.find(entry => entry.type === 'review')?.content || lastMessage.content || '智能体协同任务',
      summary: lastMessage.content || '协作记录已更新',
      route: relatedTask?.route || routeReference?.id || '',
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
  const shouldToggle = !pointerState.moved
  pointerState = null
  isDragging.value = false
  persistPosition()
  window.removeEventListener('pointermove', handlePointerMove)
  window.removeEventListener('pointerup', handlePointerUp)
  if (shouldToggle) {
    isOpen.value = !isOpen.value
  }
}

function handleResize() {
  viewport.width = window.innerWidth
  viewport.height = window.innerHeight
  const next = clampPosition(position)
  position.x = next.x
  position.y = next.y
  persistPosition()
}

function openStatusTab() {
  activeTab.value = 'status'
  loadStatus()
}

function handleWorkflowCardOpen(event) {
  const workflowId = String(event?.detail?.workflowId || event?.detail?.task?.taskId || '')
  if (!workflowId || workflowId === lastWorkflowCardId) return
  lastWorkflowCardId = workflowId
  showRuntimeSettings.value = false
  activeTab.value = 'chat'
  isOpen.value = true
  nextTick(scrollToBottom)
}

async function loadHistory() {
  try {
    const response = await getXiaoZhiHistory()
    messages.value = response?.data?.messages || []
    tasks.value = response?.data?.tasks || []
    agentConversation.value = response?.data?.agentConversation || agentConversation.value
    await scrollToBottom()
  } catch (error) {
    addLog(error?.message || '岐小智历史加载失败', 'warn', '岐小智')
  }
}

async function loadStatus() {
  try {
    const response = await getXiaoZhiStatus()
    agents.value = response?.data?.agents || []
    tasks.value = response?.data?.tasks || tasks.value
    harnessStatus.value = response?.data?.architecture || null
    agentConversation.value = response?.data?.agentConversation || agentConversation.value
    if (statusTimer && !isOpen.value && !runningTaskCount.value) {
      stopStatusPolling()
    }
  } catch (error) {
    addLog(error?.message || '岐小智状态加载失败', 'warn', '岐小智')
  }
}

function toggleConversationGroup(key) {
  const next = new Set(expandedConversationGroups.value)
  if (next.has(key)) next.delete(key)
  else next.add(key)
  expandedConversationGroups.value = next
  nextTick(scrollToBottom)
}

function isConversationGroupExpanded(key) {
  return expandedConversationGroups.value.has(key)
}

function conversationStatusLabel(status) {
  return {
    running: '协同中',
    failed: '需处理',
    warning: '待核验',
    complete: '已完成',
  }[status] || '已记录'
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
  const citationCount = Array.isArray(details.citations) ? details.citations.length : 0
  if (citationCount) parts.push(`知识引用：${citationCount} 条`)
  return parts.join(' · ')
}

async function openRuntimeSettings() {
  showRuntimeSettings.value = true
  runtimeSettingsMessage.value = ''
  try {
    const response = await getXiaoZhiRuntimeSettings()
    const settings = response?.data?.settings || {}
    runtimeSettings.enabled = Boolean(settings.enabled)
    runtimeSettings.protocol = settings.protocol || 'openai'
    runtimeSettings.baseUrl = settings.baseUrl || 'https://maas-coding-api.cn-huabei-1.xf-yun.com/v2'
    runtimeSettings.model = settings.model || 'astron-code-latest'
  } catch (error) {
    runtimeSettingsState.value = 'error'
    runtimeSettingsMessage.value = error?.response?.data?.msg || error?.message || '运行配置加载失败'
  }
}

function runtimeSettingsPayload() {
  return {
    enabled: runtimeSettings.enabled,
    protocol: runtimeSettings.protocol,
    baseUrl: runtimeSettings.baseUrl,
    model: runtimeSettings.model,
  }
}

function usePlatformRuntime() {
  runtimeSettings.enabled = false
  runtimeSettingsState.value = 'info'
  runtimeSettingsMessage.value = '保存后将恢复平台统一模型配置。'
}

async function testRuntimeSettings() {
  testingRuntime.value = true
  runtimeSettingsMessage.value = ''
  try {
    const response = await testXiaoZhiRuntimeSettings(runtimeSettingsPayload())
    const result = response?.data || {}
    runtimeSettingsState.value = 'success'
    runtimeSettingsMessage.value = `${result.message || '连接成功'} · ${result.model || runtimeSettings.model} · ${result.elapsedMs || 0}ms`
  } catch (error) {
    runtimeSettingsState.value = 'error'
    runtimeSettingsMessage.value = error?.response?.data?.msg || error?.response?.data?.data?.error || error?.message || '模型连接失败'
  } finally {
    testingRuntime.value = false
  }
}

async function saveRuntimeSettings() {
  savingRuntime.value = true
  runtimeSettingsMessage.value = ''
  try {
    const response = await saveXiaoZhiRuntimeSettings(runtimeSettingsPayload())
    const settings = response?.data?.settings || {}
    const connection = response?.data?.connection || null
    runtimeSettings.enabled = Boolean(settings.enabled)
    runtimeSettings.protocol = settings.protocol || runtimeSettings.protocol
    runtimeSettings.baseUrl = settings.baseUrl || runtimeSettings.baseUrl
    runtimeSettings.model = settings.model || runtimeSettings.model
    runtimeSettingsState.value = 'success'
    runtimeSettingsMessage.value = connection
      ? `连接通过并已保存 · ${connection.model || runtimeSettings.model} · ${connection.elapsedMs || 0}ms`
      : (response?.msg || '智能体运行配置已保存')
    await loadStatus()
  } catch (error) {
    runtimeSettingsState.value = 'error'
    const message = error?.response?.data?.msg || error?.message || '保存失败'
    const detail = error?.response?.data?.data?.error || ''
    runtimeSettingsMessage.value = detail ? `${message}：${detail}` : message
  } finally {
    savingRuntime.value = false
  }
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

function handleComposerKeydown(event) {
  if (event.key !== 'Enter' || event.shiftKey) return
  if (event.isComposing || event.keyCode === 229) return
  event.preventDefault()
  sendMessage()
}

async function sendMessage() {
  const content = draft.value.trim()
  const queuedFiles = pendingAttachments.value.slice()
  if ((!content && !queuedFiles.length) || isSending.value) return
  const displayContent = content || '请分析我上传的学习材料。'
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
    const response = await chatWithXiaoZhi({ message: displayContent, attachments, route: route.fullPath })
    const data = response?.data || {}
    messages.value.push({
      role: 'assistant',
      content: data.reply || '我已经收到，会继续跟进你的学习状态。',
      cards: data.cards || [],
      intent: data.intent || {},
      createdAt: new Date().toISOString(),
    })
    await loadStatus()
    if (runningTaskCount.value) startStatusPolling()
    await scrollToBottom()
  } catch (error) {
    const errorMessage = error?.response?.data?.msg || error?.message || '岐小智暂时连接失败，请稍后再试。'
    sendError.value = errorMessage
    if (!draft.value.trim()) draft.value = content
    if (queuedFiles.length) pendingAttachments.value = queuedFiles
    messages.value.push({
      role: 'assistant',
      content: errorMessage,
      cards: [],
      createdAt: new Date().toISOString(),
    })
    addLog(error?.message || '岐小智对话失败', 'error', '岐小智')
  } finally {
    isSending.value = false
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
      addLog(`${file.name} 超过 50 MB，未加入附件`, 'warn', '岐小智多模态输入')
      continue
    }
    const duplicate = next.some(item => item.name === file.name && item.size === file.size && item.lastModified === file.lastModified)
    if (!duplicate && next.length < 4) next.push(file)
  }
  pendingAttachments.value = next
  if (selected.length && next.length >= 4) {
    addLog('每次最多添加 4 个多模态附件', 'warn', '岐小智多模态输入')
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
    addLog('当前浏览器不支持 Web Speech API，可继续使用文字输入。', 'warn', '岐小智语音')
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
    addLog(`语音输入失败：${event.error || 'unknown'}`, 'warn', '岐小智语音')
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
  if (['running', 'queued', 'ready', 'complete', 'failed'].includes(status)) return status
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
    idle: '待命',
    waiting: '等待确认',
    waiting_for_user: '等待确认',
  }
  return map[status] || status || '待命'
}

function agentIcon(agent) {
  return agent?.type ? resourceIcon(agent.type) : Activity
}

function agentDisplayName(agent) {
  if (!agent) return '智能体'
  if (agent.role === 'supervisor') return agent.name || '岐小智总控智能体'
  if (agent.type && resourceLabels[agent.type]) return `${resourceLabels[agent.type]}智能体`
  return agentNameAliases[agent.id] || agent.name || agent.id || '智能体'
}

function agentDetail(agent) {
  const detail = String(agent?.detail || '').trim()
  if (!detail) return '等待岐小智总控调度'
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
    context: 'Context',
    gateway: 'MCP Gateway',
    registry: 'Skill Registry',
    reviewer: 'Quality Review',
    safety: 'Safety Guard',
    specialist: 'Specialist',
  }
  return roleMap[agent?.role] || 'Agent'
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
  window.addEventListener('resize', handleResize)
  window.addEventListener('xiaozhi-task-updated', handleExternalTaskUpdate)
  window.addEventListener(XIAOZHI_WORKFLOW_EVENT, handleWorkflowCardOpen)
  handleResize()
  loadStatus()
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', handleResize)
  window.removeEventListener('xiaozhi-task-updated', handleExternalTaskUpdate)
  window.removeEventListener(XIAOZHI_WORKFLOW_EVENT, handleWorkflowCardOpen)
  window.removeEventListener('pointermove', handlePointerMove)
  window.removeEventListener('pointerup', handlePointerUp)
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
  gap: 16px;
  margin-bottom: 14px;
}

.window-head-actions {
  display: flex;
  align-items: center;
  gap: 6px;
}

.title-block .eyebrow {
  display: block;
  margin-bottom: 2px;
  color: #10b981;
  font-size: 11px;
  font-weight: 900;
  letter-spacing: 0.12em;
  text-transform: uppercase;
}

.title-block strong {
  display: block;
  color: #172033;
  font-size: 24px;
  line-height: 1.1;
}

.title-block p {
  margin: 5px 0 0;
  color: #667a77;
  font-size: 13px;
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
  padding: 22px;
  border: 1px solid #e3f2ee;
  border-radius: 18px;
  background: linear-gradient(135deg, #f5fffb, #ffffff);
  text-align: center;
}

.empty-chat svg {
  color: #10b981;
}

.empty-chat strong {
  display: block;
  margin-top: 8px;
  color: #172033;
}

.empty-chat p {
  margin: 8px 0 0;
  color: #667a77;
  font-size: 13px;
  line-height: 1.6;
}

.agent-group-chat {
  display: grid;
  gap: 8px;
  margin: 4px 0 12px;
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
  border: 1px solid #d9e4e0;
  border-left: 3px solid #2a8a6c;
  border-radius: 7px;
  background: #fff;
}

.agent-conversation-card.running {
  border-left-color: #3182ce;
}

.agent-conversation-card.failed {
  border-left-color: #c84b4b;
}

.agent-conversation-card.warning,
.agent-conversation-card.compacted-history {
  border-left-color: #b47a1f;
}

.agent-conversation-main {
  width: 100%;
  display: grid;
  grid-template-columns: 30px minmax(0, 1fr) 18px;
  align-items: center;
  gap: 9px;
  padding: 10px;
  border: 0;
  background: #fff;
  color: #263a35;
  text-align: left;
  cursor: pointer;
}

.agent-conversation-main:hover {
  background: #f7faf9;
}

.agent-conversation-main > svg {
  color: #84938f;
}

.agent-conversation-icon {
  width: 30px;
  height: 30px;
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
  font-size: 10px;
  font-weight: 750;
}

.agent-conversation-copy strong {
  margin-top: 3px;
  color: #21332f;
  font-size: 12px;
}

.agent-conversation-copy em {
  margin-top: 3px;
  color: #71817d;
  font-size: 11px;
  font-style: normal;
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
  text-decoration: none;
}

.message {
  display: flex;
  margin: 10px 0;
}

.message.user {
  justify-content: flex-end;
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

.message.pending .bubble {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  color: #536b68;
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
  padding: 10px;
  border: 1px solid #d9eee8;
  border-radius: 18px;
  background: #fff;
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
  width: 100%;
  min-height: 58px;
  resize: none;
  border: 0;
  outline: 0;
  color: #213a39;
  font-size: 14px;
  line-height: 1.55;
}

.composer-actions {
  justify-content: space-between;
  gap: 8px;
  margin-top: 8px;
}

.composer-input-tools {
  display: flex;
  align-items: center;
  gap: 4px;
}

.composer-tool {
  width: 32px;
  height: 32px;
  display: grid;
  place-items: center;
  padding: 0;
  border: 1px solid transparent;
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

.master-agent-node,
.specialist-agent-node {
  position: relative;
  min-width: 0;
  display: grid;
  align-items: center;
  box-sizing: border-box;
  border: 1px solid #dfe4e2;
  border-radius: 8px;
  background: #ffffff;
}

.master-agent-node {
  grid-template-columns: 42px minmax(0, 1fr) auto;
  gap: 10px;
  min-height: 76px;
  padding: 11px 12px;
  border-color: #a9c8ba;
  box-shadow: 0 8px 18px rgba(25, 63, 48, 0.07);
}

.master-agent-node .agent-node-icon {
  width: 42px;
  height: 42px;
  background: #176f4b;
  color: #ffffff;
}

.master-agent-node > em {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  color: #4e5754;
  font-size: 10px;
  font-style: normal;
  font-weight: 800;
}

.agent-node-copy {
  min-width: 0;
  display: grid;
  gap: 2px;
}

.agent-node-copy small {
  color: #73807c;
  font-size: 9px;
  font-weight: 800;
  text-transform: uppercase;
}

.agent-node-copy strong {
  overflow: hidden;
  color: #202525;
  font-size: 12px;
  line-height: 1.25;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.agent-node-copy > span {
  display: -webkit-box;
  overflow: hidden;
  color: #737a79;
  font-size: 10px;
  line-height: 1.35;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
}

.flow-trunk {
  position: relative;
  height: 46px;
  display: grid;
  place-items: center;
}

.flow-trunk::before,
.flow-trunk span {
  content: '';
  position: absolute;
  left: 50%;
  width: 1px;
  background: #b8c8c2;
  transform: translateX(-50%);
}

.flow-trunk::before {
  top: 0;
  bottom: 0;
}

.flow-trunk span {
  top: 21px;
  width: 7px;
  height: 7px;
  border: 2px solid #ffffff;
  border-radius: 50%;
  background: #176f4b;
}

.flow-trunk small {
  position: relative;
  z-index: 1;
  margin-left: 112px;
  padding: 2px 5px;
  background: #ffffff;
  color: #7a8380;
  font-size: 9px;
}

.specialist-flow-grid {
  position: relative;
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  column-gap: 24px;
  row-gap: 9px;
}

.specialist-flow-grid::before {
  content: '';
  position: absolute;
  top: -4px;
  bottom: 37px;
  left: 50%;
  width: 1px;
  background: #c9d3d0;
  transform: translateX(-50%);
}

.specialist-agent-node {
  grid-template-columns: 30px minmax(0, 1fr) 8px;
  gap: 7px;
  min-height: 74px;
  padding: 8px;
}

.specialist-agent-node::before {
  content: '';
  position: absolute;
  top: 50%;
  width: 12px;
  height: 1px;
  background: #c9d3d0;
}

.specialist-agent-node:nth-child(odd)::before {
  right: -12px;
}

.specialist-agent-node:nth-child(even)::before {
  left: -12px;
}

.specialist-agent-node .agent-node-icon {
  width: 30px;
  height: 30px;
  background: #eef2f0;
  color: #53625d;
}

.specialist-agent-node.running,
.specialist-agent-node.queued {
  border-color: #9fc8e2;
  background: #f8fcff;
}

.specialist-agent-node.running::before,
.specialist-agent-node.queued::before {
  background: #4c90bc;
}

.specialist-agent-node.failed {
  border-color: #e5b6b6;
  background: #fffafa;
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
