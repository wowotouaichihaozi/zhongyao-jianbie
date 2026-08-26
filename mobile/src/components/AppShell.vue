<template>
  <div class="app-shell">
    <OfflineBar />
    <header class="mobile-header">
      <button v-if="route.meta.subpage" class="icon-btn" type="button" aria-label="返回" @click="router.back()">
        <ArrowLeft :size="22" />
      </button>
      <RouterLink v-else class="header-brand" to="/home">
        <img :src="`${baseUrl}qihuang-zhijing-mark.png`" alt="中药鉴别" />
      </RouterLink>
      <strong>{{ title }}</strong>
      <RouterLink class="avatar-button" to="/me" aria-label="我的">
        <img :src="`${baseUrl}app-icon.png`" alt="" />
      </RouterLink>
    </header>

    <main class="shell-main"><slot /></main>
    <TaskStatusStrip />
    <BottomNav v-if="!route.meta.subpage" />
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { ArrowLeft } from 'lucide-vue-next'
import { RouterLink, useRoute, useRouter } from 'vue-router'
import BottomNav from './BottomNav.vue'
import OfflineBar from './OfflineBar.vue'
import TaskStatusStrip from './TaskStatusStrip.vue'

const route = useRoute()
const router = useRouter()
const baseUrl = import.meta.env.BASE_URL
const titles = { home: '今日学习', path: '学习路径', 'path-stage': '本周任务', resources: '资源中心', 'resource-new': '生成资源', 'resource-task': '任务详情', 'resource-detail': '资源详情', practice: '练习题', tutor: '岐小智辅导', profile: '学习画像', 'profile-collect': '画像采集', me: '我的' }
const title = computed(() => titles[String(route.name)] || '中药鉴别')
</script>
