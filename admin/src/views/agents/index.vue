<script setup lang="tsx">
import { onMounted, ref } from 'vue';
import { NProgress, NTag } from 'naive-ui';
import { fetchAdminAgentsOverview } from '@/service/api';

const loading = ref(false);
const overview = ref<any>({ agents: [], recentTasks: [], trend: [] });

async function loadData() {
  loading.value = true;
  const { data, error } = await fetchAdminAgentsOverview();
  if (!error && data) overview.value = data;
  loading.value = false;
}

const taskColumns = [
  { title: '任务标题', key: 'title', minWidth: 180, ellipsis: { tooltip: true } },
  { title: '智能体类型', key: 'taskType', width: 150 },
  {
    title: '状态',
    key: 'status',
    width: 110,
    render: (row: any) => {
      const type = row.status === 'failed' ? 'error' : row.status === 'completed' ? 'success' : 'warning';
      return <NTag type={type as any}>{row.status}</NTag>;
    }
  },
  { title: '更新时间', key: 'updatedAt', width: 180 },
  { title: '错误信息', key: 'error', minWidth: 180, ellipsis: { tooltip: true } }
];

onMounted(loadData);
</script>

<template>
  <div class="agent-page">
    <header class="page-head">
      <div>
        <h1>智能体监控</h1>
        <p>查看各智能体实时状态、累计调用、成功率与最近运行任务。</p>
      </div>
      <NButton type="primary" round secondary @click="loadData">
        <template #icon>
          <SvgIcon icon="mdi:refresh" />
        </template>
        刷新
      </NButton>
    </header>

    <section class="agent-grid">
      <NCard v-for="agent in overview.agents" :key="agent.id" :bordered="false" class="agent-tile">
        <div class="agent-top">
          <div class="agent-icon">
            <SvgIcon icon="mdi:robot-outline" />
          </div>
          <NTag :type="agent.status === '就绪' ? 'success' : 'info'" round>{{ agent.status }}</NTag>
        </div>
        <h3>{{ agent.name }}</h3>
        <p>{{ agent.id }}</p>
        <div class="agent-stats">
          <div><strong>{{ agent.totalRuns }}</strong><span>累计运行</span></div>
          <div><strong>{{ agent.successRuns }}</strong><span>成功</span></div>
          <div><strong>{{ agent.failedRuns }}</strong><span>失败</span></div>
        </div>
        <div class="rate-line">
          <span>成功率 {{ agent.successRate }}%</span>
          <NProgress type="line" :percentage="agent.successRate" :show-indicator="false" status="success" />
        </div>
        <footer>最近运行：{{ agent.lastRunAt }}</footer>
      </NCard>
    </section>

    <NCard :bordered="false" class="table-card">
      <template #header>最近智能体任务</template>
      <NDataTable :loading="loading" :columns="taskColumns" :data="overview.recentTasks" :pagination="{ pageSize: 10 }" />
    </NCard>
  </div>
</template>

<style scoped>
.agent-page {
  min-height: 100%;
  padding: 8px;
  background: linear-gradient(135deg, #f7fffc 0%, #f3fbf8 45%, #eef9f5 100%);
}

.page-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 18px;
  padding: 24px 28px;
  border-radius: 24px;
  background: #fff;
  box-shadow: 0 16px 38px rgba(15, 118, 110, 0.08);
}

.page-head h1 {
  margin: 0 0 8px;
  color: #172033;
  font-size: 28px;
}

.page-head p,
.agent-tile p,
.agent-tile footer,
.rate-line span {
  margin: 0;
  color: #667085;
}

.agent-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 16px;
  margin-bottom: 18px;
}

.agent-tile {
  border: 1px solid rgba(20, 184, 166, 0.12);
  border-radius: 22px;
  box-shadow: 0 14px 34px rgba(15, 118, 110, 0.07);
}

.agent-top,
.agent-stats,
.rate-line {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.agent-icon {
  display: grid;
  width: 52px;
  height: 52px;
  place-items: center;
  border-radius: 16px;
  background: #e9fbf4;
  color: #10b981;
  font-size: 26px;
}

.agent-tile h3 {
  margin: 18px 0 6px;
  color: #1f3433;
}

.agent-stats {
  margin: 18px 0;
}

.agent-stats div {
  min-width: 0;
}

.agent-stats strong {
  display: block;
  color: #10b981;
  font-size: 22px;
}

.agent-stats span {
  color: #8aa09c;
  font-size: 12px;
}

.rate-line {
  align-items: stretch;
  flex-direction: column;
}

.table-card {
  border-radius: 22px;
  box-shadow: 0 14px 34px rgba(15, 118, 110, 0.07);
}

@media (max-width: 1280px) {
  .agent-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 780px) {
  .agent-grid {
    grid-template-columns: 1fr;
  }
}
</style>
