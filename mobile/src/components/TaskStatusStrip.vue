<template>
  <aside v-if="tasks.length" class="task-strip" :class="{ expanded: taskStore.expanded }">
    <button class="task-strip-summary" type="button" @click="taskStore.expanded = !taskStore.expanded">
      <span class="spinner"></span>
      <span><strong>{{ tasks.length }} 个任务正在后台处理</strong><small>{{ latest.title || '智能体正在协作' }}</small></span>
      <ChevronUp v-if="taskStore.expanded" :size="18" /><ChevronDown v-else :size="18" />
    </button>
    <div v-if="taskStore.expanded" class="task-strip-list">
      <RouterLink v-for="task in tasks" :key="task.taskId" :to="`/resources/task/${task.taskId}`">
        <span><b>{{ task.title || '生成任务' }}</b><small>{{ task.status === 'queued' ? '排队中' : '处理中' }}</small></span>
        <em>{{ displayTaskProgress(task) }}%</em>
      </RouterLink>
    </div>
  </aside>
</template>

<script setup>
import { computed } from 'vue'
import { ChevronDown, ChevronUp } from 'lucide-vue-next'
import { RouterLink } from 'vue-router'
import { activeTasks, displayTaskProgress, taskStore } from '../stores/tasks.js'
const tasks = activeTasks
const latest = computed(() => tasks.value[0] || {})
</script>
