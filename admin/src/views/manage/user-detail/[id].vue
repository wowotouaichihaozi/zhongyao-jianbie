<script setup lang="tsx">
import { computed, onMounted, ref } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { NTag } from 'naive-ui';
import { fetchAdminUserDetail } from '@/service/api';

const route = useRoute();
const router = useRouter();
const loading = ref(false);
const detail = ref<any>({ user: {}, latestProfile: null, tasks: [], events: [], messages: [] });

const profile = computed(() => detail.value.latestProfile?.report?.aiAnalysis || detail.value.latestProfile?.report || {});
const dimensions = computed(() => profile.value.dimensionScores || []);

async function loadData() {
  loading.value = true;
  const { data, error } = await fetchAdminUserDetail(String(route.params.id));
  if (!error && data) detail.value = data;
  loading.value = false;
}

const taskColumns = [
  { title: '任务', key: 'title', ellipsis: { tooltip: true } },
  { title: '类型', key: 'taskType', width: 140 },
  { title: '状态', key: 'status', width: 110 },
  { title: '时间', key: 'createdAt', width: 175 }
];

const eventColumns = [
  { title: '事件', key: 'title', ellipsis: { tooltip: true } },
  { title: '类型', key: 'type', width: 140 },
  { title: '路由', key: 'route', width: 180 },
  { title: '时间', key: 'createdAt', width: 175 }
];

onMounted(loadData);
</script>

<template>
  <div class="user-detail-page">
    <header class="page-head">
      <div>
        <NButton text type="primary" @click="router.back()">
          <template #icon>
            <SvgIcon icon="mdi:arrow-left" />
          </template>
          返回用户列表
        </NButton>
        <h1>{{ detail.user.displayName || detail.user.username || '用户详情' }}</h1>
        <p>{{ detail.user.email || '未绑定邮箱' }} · 最近登录 {{ detail.user.lastLoginAt || '-' }}</p>
      </div>
      <NTag :type="detail.user.status === 'disabled' ? 'warning' : 'success'" round>
        {{ detail.user.status === 'disabled' ? '已禁用' : '启用中' }}
      </NTag>
    </header>

    <section class="summary-grid">
      <NCard :bordered="false" class="profile-card">
        <template #header>学习画像摘要</template>
        <div v-if="detail.latestProfile" class="profile-summary">
          <div class="score-circle">{{ profile.overallScore || '-' }}</div>
          <div>
            <h2>{{ profile.learningStyle || '暂无学习风格' }}</h2>
            <p>{{ profile.summary || '暂无画像摘要' }}</p>
          </div>
        </div>
        <NEmpty v-else description="暂无画像报告" />
      </NCard>

      <NCard :bordered="false" class="profile-card">
        <template #header>维度得分</template>
        <div v-if="dimensions.length" class="dimension-list">
          <div v-for="item in dimensions" :key="item.name" class="dimension-item">
            <span>{{ item.name }}</span>
            <NProgress type="line" :percentage="Number(item.score || 0) * 20" :show-indicator="false" status="success" />
            <strong>{{ item.score }}/5</strong>
          </div>
        </div>
        <NEmpty v-else description="暂无维度数据" />
      </NCard>
    </section>

    <section class="summary-grid">
      <NCard :bordered="false" class="profile-card">
        <template #header>智能体任务</template>
        <NDataTable :loading="loading" :columns="taskColumns" :data="detail.tasks" :pagination="{ pageSize: 8 }" />
      </NCard>
      <NCard :bordered="false" class="profile-card">
        <template #header>系统事件</template>
        <NDataTable :loading="loading" :columns="eventColumns" :data="detail.events" :pagination="{ pageSize: 8 }" />
      </NCard>
    </section>

    <NCard :bordered="false" class="profile-card">
      <template #header>最近对话消息</template>
      <NTimeline>
        <NTimelineItem v-for="(msg, index) in detail.messages" :key="index" :type="msg.role === 'assistant' ? 'success' : 'info'">
          <template #header>{{ msg.role === 'assistant' ? '智能体' : '用户' }}</template>
          <template #default>{{ msg.content }}</template>
          <template #footer>{{ msg.createdAt }}</template>
        </NTimelineItem>
      </NTimeline>
    </NCard>
  </div>
</template>

<style scoped>
.user-detail-page {
  min-height: 100%;
  padding: 8px;
  background: linear-gradient(135deg, #f7fffc 0%, #f3fbf8 45%, #eef9f5 100%);
}

.page-head,
.profile-card {
  border-radius: 22px;
  box-shadow: 0 14px 34px rgba(15, 118, 110, 0.07);
}

.page-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 18px;
  padding: 24px 28px;
  background: #fff;
}

.page-head h1 {
  margin: 10px 0 8px;
  color: #172033;
  font-size: 28px;
}

.page-head p {
  margin: 0;
  color: #667085;
}

.summary-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 18px;
  margin-bottom: 18px;
}

.profile-summary {
  display: flex;
  align-items: center;
  gap: 20px;
}

.score-circle {
  display: grid;
  width: 96px;
  height: 96px;
  place-items: center;
  border-radius: 50%;
  background: linear-gradient(135deg, #20c997, #0e9f6e);
  color: #fff;
  font-size: 34px;
  font-weight: 800;
  box-shadow: 0 14px 28px rgba(16, 185, 129, 0.24);
}

.profile-summary h2 {
  margin: 0 0 8px;
  color: #064e3b;
}

.profile-summary p {
  margin: 0;
  color: #64748b;
  line-height: 1.8;
}

.dimension-list {
  display: grid;
  gap: 14px;
}

.dimension-item {
  display: grid;
  grid-template-columns: 160px 1fr 48px;
  align-items: center;
  gap: 14px;
}

.dimension-item span {
  color: #475467;
}

.dimension-item strong {
  color: #10b981;
}

@media (max-width: 980px) {
  .summary-grid {
    grid-template-columns: 1fr;
  }
}
</style>
