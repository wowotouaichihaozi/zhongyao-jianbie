<template>
  <aside v-if="visible" class="debug-panel" :class="{ collapsed }" aria-label="AI 智能体调试信息">
    <header class="debug-head">
      <div>
        <strong>AI Agent Debug</strong>
        <span>Ctrl + Alt + D</span>
      </div>
      <div class="debug-actions">
        <button type="button" @click="toggleCollapsed">{{ collapsed ? '展开' : '收起' }}</button>
        <button type="button" @click="clearLogs">清空</button>
        <button type="button" @click="hide">隐藏</button>
      </div>
    </header>

    <template v-if="!collapsed">
      <section v-if="sections.length" class="debug-sections">
        <article v-for="section in sections" :key="section.id" class="debug-section">
          <div class="debug-section-title">
            <strong>{{ section.title }}</strong>
            <span>{{ section.updatedAt }}</span>
          </div>
          <p v-for="(item, index) in section.items" :key="index">{{ item }}</p>
        </article>
      </section>

      <section class="debug-log-list">
        <p v-if="!logs.length" class="debug-empty">暂无调试信息。触发智能体后会在这里显示。</p>
        <article v-for="item in logs" :key="item.id" class="debug-log" :class="item.level">
          <div class="debug-log-meta">
            <span>{{ item.time }}</span>
            <strong>{{ item.scope }}</strong>
            <em>{{ item.level }}</em>
          </div>
          <pre>{{ item.message }}</pre>
        </article>
      </section>
    </template>
  </aside>
</template>

<script setup>
import { onBeforeUnmount, onMounted } from 'vue'
import { useGlobalDebug } from '../stores/globalDebug.js'

const {
  visible,
  collapsed,
  logs,
  sections,
  hide,
  toggle,
  toggleCollapsed,
  clearLogs,
  addLog,
} = useGlobalDebug()

function handleKeydown(event) {
  if (event.ctrlKey && event.altKey && event.key.toLowerCase() === 'd') {
    event.preventDefault()
    toggle()
    addLog('Ctrl+Alt+D toggled debug panel', 'info', '调试面板')
  }
}

onMounted(() => {
  window.addEventListener('keydown', handleKeydown)
})

onBeforeUnmount(() => {
  window.removeEventListener('keydown', handleKeydown)
})
</script>

<style scoped>
.debug-panel {
  position: fixed;
  right: 18px;
  bottom: 18px;
  z-index: 10000;
  width: min(520px, calc(100vw - 32px));
  max-height: min(680px, calc(100vh - 36px));
  display: flex;
  flex-direction: column;
  overflow: hidden;
  border: 1px solid rgba(13, 148, 105, 0.26);
  border-radius: 18px;
  background: rgba(12, 22, 20, 0.92);
  color: #ecfdf5;
  box-shadow: 0 22px 70px rgba(15, 23, 42, 0.28);
  backdrop-filter: blur(18px);
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
}

.debug-panel.collapsed {
  max-height: 68px;
}

.debug-head {
  min-height: 64px;
  padding: 12px 14px 12px 16px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  border-bottom: 1px solid rgba(167, 243, 208, 0.16);
}

.debug-head strong {
  display: block;
  font-size: 14px;
  letter-spacing: 0;
}

.debug-head span {
  display: block;
  margin-top: 4px;
  font-size: 11px;
  color: #a7f3d0;
}

.debug-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.debug-actions button {
  height: 30px;
  padding: 0 10px;
  border: 1px solid rgba(167, 243, 208, 0.26);
  border-radius: 999px;
  background: rgba(236, 253, 245, 0.08);
  color: #d1fae5;
  font-size: 12px;
  cursor: pointer;
}

.debug-actions button:hover {
  background: rgba(16, 185, 129, 0.2);
}

.debug-sections {
  padding: 12px 14px 0;
  display: grid;
  gap: 10px;
}

.debug-section {
  padding: 10px 12px;
  border: 1px solid rgba(167, 243, 208, 0.16);
  border-radius: 12px;
  background: rgba(6, 78, 59, 0.22);
}

.debug-section-title,
.debug-log-meta {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}

.debug-section-title strong,
.debug-log-meta strong {
  color: #bbf7d0;
  font-size: 12px;
}

.debug-section-title span,
.debug-log-meta span,
.debug-log-meta em {
  color: #99f6e4;
  font-size: 11px;
  font-style: normal;
}

.debug-section p {
  margin: 8px 0 0;
  color: #e2e8f0;
  font-size: 12px;
  line-height: 1.6;
}

.debug-log-list {
  padding: 12px 14px 14px;
  overflow: auto;
}

.debug-empty {
  margin: 8px 0;
  color: #94a3b8;
  font-size: 12px;
}

.debug-log {
  padding: 10px 12px;
  border-left: 3px solid #10b981;
  border-radius: 10px;
  background: rgba(15, 23, 42, 0.54);
}

.debug-log + .debug-log {
  margin-top: 10px;
}

.debug-log.error {
  border-left-color: #fb7185;
}

.debug-log.warn {
  border-left-color: #f59e0b;
}

.debug-log pre {
  margin: 8px 0 0;
  max-height: 220px;
  overflow: auto;
  white-space: pre-wrap;
  word-break: break-word;
  color: #dbeafe;
  font-size: 11px;
  line-height: 1.55;
}

@media (max-width: 768px) {
  .debug-panel {
    right: 10px;
    bottom: 10px;
    width: calc(100vw - 20px);
  }
}
</style>
