<template>
  <section class="history-panel" aria-labelledby="mindmap-history-title">
    <header>
      <div>
        <span class="history-kicker">
          <History :size="16" stroke-width="2.2" aria-hidden="true" />
          创作记录
        </span>
        <h2 id="mindmap-history-title">最近生成</h2>
      </div>
      <button type="button" class="icon-button" title="刷新历史记录" aria-label="刷新历史记录" :disabled="loading" @click="$emit('refresh')">
        <RefreshCw :size="17" :class="{ spin: loading }" aria-hidden="true" />
      </button>
    </header>

    <div v-if="loading && !tasks.length" class="history-state" role="status">
      <LoaderCircle :size="22" class="spin" aria-hidden="true" />
      <span>正在读取任务记录</span>
    </div>

    <div v-else-if="error && !tasks.length" class="history-state error" role="alert">
      <CircleAlert :size="22" aria-hidden="true" />
      <span>{{ error }}</span>
      <button type="button" @click="$emit('refresh')">重试</button>
    </div>

    <div v-else-if="!tasks.length" class="history-state empty">
      <History :size="24" aria-hidden="true" />
      <div>
        <strong>还没有思维导图</strong>
        <span>生成后的导图会保存在这里，离开页面也能继续查看进度。</span>
      </div>
    </div>

    <div v-else class="history-list">
      <article v-for="item in tasks" :key="item.taskId" class="history-item" :class="item.status">
        <div class="history-item-heading">
          <span class="status-icon" aria-hidden="true">
            <LoaderCircle v-if="isPending(item)" :size="15" class="spin" />
            <CheckCircle2 v-else-if="item.status === 'complete'" :size="15" />
            <CircleAlert v-else :size="15" />
          </span>
          <div>
            <strong>{{ displayTitle(item) }}</strong>
            <span>{{ statusLabel(item.status) }} · {{ formatTime(item.updatedAt || item.createdAt) }}</span>
          </div>
        </div>

        <p v-if="item.error" class="task-error">{{ item.error }}</p>
        <p v-else>{{ displayTopic(item) }}</p>

        <div v-if="isPending(item)" class="task-progress" aria-hidden="true">
          <span :style="{ width: `${taskProgress(item)}%` }"></span>
        </div>

        <footer>
          <span v-if="qualityScore(item)">质量 {{ qualityScore(item) }} / 100</span>
          <span v-else>{{ shortTaskId(item.taskId) }}</span>
          <button v-if="item.status === 'failed'" type="button" @click="$emit('retry', item)">
            <RotateCcw :size="15" aria-hidden="true" />
            重新生成
          </button>
          <button v-else type="button" @click="$emit('open', item)">
            <ExternalLink :size="15" aria-hidden="true" />
            {{ isPending(item) ? '查看进度' : '打开导图' }}
          </button>
        </footer>
      </article>
    </div>
  </section>
</template>

<script setup>
import {
  CheckCircle2,
  CircleAlert,
  ExternalLink,
  History,
  LoaderCircle,
  RefreshCw,
  RotateCcw,
} from 'lucide-vue-next'

defineProps({
  tasks: { type: Array, default: () => [] },
  loading: { type: Boolean, default: false },
  error: { type: String, default: '' },
})

defineEmits(['open', 'refresh', 'retry'])

function isPending(item) {
  return ['queued', 'running'].includes(String(item?.status || ''))
}

function statusLabel(status) {
  return {
    queued: '等待生成',
    running: '后台生成中',
    complete: '已完成',
    failed: '生成失败',
  }[String(status || '')] || '状态未知'
}

function displayTitle(item) {
  return String(item?.result?.selectedResource?.title || item?.title || '思维导图').trim()
}

function displayTopic(item) {
  return String(item?.result?.topic || item?.result?.params?.topic || item?.prompt || '个性化学习思维导图').trim()
}

function qualityScore(item) {
  return Number(
    item?.result?.qualityEvaluation?.score
    || item?.result?.selectedResource?.qualityEvaluation?.score
    || item?.result?.selectedResource?.metadata?.qualityEvaluation?.score
    || 0,
  )
}

function taskProgress(item) {
  const progress = Number(item?.result?.progress || 0)
  if (item?.status === 'queued') return Math.max(8, Math.min(24, progress || 8))
  return Math.max(24, Math.min(96, progress || 42))
}

function shortTaskId(value) {
  const taskId = String(value || '')
  return taskId.length > 18 ? `${taskId.slice(0, 12)}...${taskId.slice(-4)}` : taskId
}

function formatTime(value) {
  const date = new Date(value || '')
  if (Number.isNaN(date.getTime())) return '时间未知'
  return date.toLocaleString('zh-CN', {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    hour12: false,
  })
}
</script>

<style scoped>
.history-panel {
  min-width: 0;
}

.history-panel > header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding-bottom: 18px;
}

.history-kicker {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  color: #0b8f65;
  font-size: 12px;
  font-weight: 750;
}

.history-panel h2 {
  margin: 5px 0 0;
  color: #17352d;
  font-size: 22px;
  letter-spacing: 0;
}

.icon-button {
  width: 34px;
  height: 34px;
  display: grid;
  place-items: center;
  padding: 0;
  border: 1px solid #d5e5de;
  border-radius: 6px;
  background: #fff;
  color: #42645a;
  cursor: pointer;
}

.icon-button:hover:not(:disabled) { background: #edf8f3; color: #087b55; }
.icon-button:disabled { opacity: 0.5; cursor: not-allowed; }

.history-list {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
}

.history-item {
  min-width: 0;
  padding: 16px;
  border: 1px solid #dce8e2;
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.72);
}

.history-item-heading {
  display: grid;
  grid-template-columns: 28px minmax(0, 1fr);
  gap: 9px;
  align-items: flex-start;
}

.status-icon {
  width: 28px;
  height: 28px;
  display: grid;
  place-items: center;
  border-radius: 50%;
  background: #e8f7f0;
  color: #0a8b62;
}

.history-item.failed .status-icon { background: #fff0ee; color: #b4443c; }
.history-item.running .status-icon,
.history-item.queued .status-icon { background: #fff7df; color: #9c7400; }

.history-item-heading div { min-width: 0; }
.history-item-heading strong {
  display: block;
  color: #214139;
  font-size: 14px;
  line-height: 1.45;
  overflow-wrap: anywhere;
}

.history-item-heading span:not(.status-icon) {
  display: block;
  margin-top: 3px;
  color: #7a8d86;
  font-size: 11px;
}

.history-item > p {
  display: -webkit-box;
  margin: 9px 0 0 37px;
  overflow: hidden;
  color: #657a72;
  font-size: 12px;
  line-height: 1.55;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
}

.history-item > p.task-error { color: #a74a43; }

.task-progress {
  height: 4px;
  margin: 11px 0 0 37px;
  overflow: hidden;
  border-radius: 2px;
  background: #e8ecea;
}

.task-progress span {
  display: block;
  height: 100%;
  border-radius: inherit;
  background: #d3a810;
  transition: width 350ms ease;
}

.history-item footer {
  min-height: 32px;
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 12px;
  margin: 8px 0 0 37px;
}

.history-item footer > span { color: #82928c; font-size: 10px; }

.history-item footer button,
.history-state button {
  min-height: 32px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 5px;
  padding: 0 10px;
  border: 1px solid #cbe4d9;
  border-radius: 6px;
  background: #fff;
  color: #087b55;
  font: inherit;
  font-size: 11px;
  font-weight: 700;
  cursor: pointer;
}

.history-item.failed footer button { border-color: #edc7c3; color: #a33e37; }

.history-state {
  min-height: 110px;
  display: flex;
  flex-direction: row;
  align-items: center;
  justify-content: center;
  gap: 10px;
  color: #71847d;
  font-size: 12px;
  padding: 18px 0;
  text-align: left;
}

.history-state.error { color: #a33e37; }
.history-state.empty div { display: grid; gap: 4px; }
.history-state.empty strong { color: #526a61; font-size: 14px; }
.history-state.empty span { color: #82928c; font-size: 12px; }
.spin { animation: history-spin 900ms linear infinite; }
@keyframes history-spin { to { transform: rotate(360deg); } }

@media (max-width: 860px) {
  .history-list { grid-template-columns: repeat(2, minmax(0, 1fr)); }
}

@media (max-width: 600px) {
  .history-list { grid-template-columns: 1fr; }
  .history-state { align-items: flex-start; }
}

@media (prefers-reduced-motion: reduce) {
  .spin { animation: none; }
}
</style>
