<script setup lang="tsx">
import { onMounted, ref } from 'vue';
import { NTag } from 'naive-ui';
import { fetchAdminDashboard } from '@/service/api';

const loading = ref(false);
const tasks = ref<any[]>([]);

async function loadData() {
  loading.value = true;
  const { data, error } = await fetchAdminDashboard();
  if (!error && data) tasks.value = data.recentTasks || [];
  loading.value = false;
}

const columns = [
  { title: '任务标题', key: 'title', minWidth: 220, ellipsis: { tooltip: true } },
  { title: '任务类型', key: 'taskType', width: 150 },
  {
    title: '状态',
    key: 'status',
    width: 120,
    render: (row: any) => {
      const type = row.status === 'failed' ? 'error' : row.status === 'completed' ? 'success' : 'warning';
      return <NTag type={type as any}>{row.status}</NTag>;
    }
  },
  { title: '用户', key: 'displayName', width: 150 },
  { title: '页面', key: 'route', minWidth: 180, ellipsis: { tooltip: true } },
  { title: '错误信息', key: 'error', minWidth: 200, ellipsis: { tooltip: true } },
  { title: '创建时间', key: 'createdAt', width: 180 },
  { title: '更新时间', key: 'updatedAt', width: 180 }
];

onMounted(loadData);
</script>

<template>
  <div class="records-page">
    <header class="page-head">
      <div>
        <h1>资源任务记录</h1>
        <p>汇总题库、PPT、思维导图、视频检索、单片机模拟器等资源任务运行记录。</p>
      </div>
      <NButton type="primary" round secondary @click="loadData">
        <template #icon>
          <SvgIcon icon="mdi:refresh" />
        </template>
        刷新
      </NButton>
    </header>
    <NCard :bordered="false" class="table-card">
      <NDataTable :loading="loading" :columns="columns" :data="tasks" :pagination="{ pageSize: 12 }" :scroll-x="1400" />
    </NCard>
  </div>
</template>

<style scoped>
.records-page {
  min-height: 100%;
  padding: 8px;
  background: linear-gradient(135deg, #f7fffc 0%, #f3fbf8 45%, #eef9f5 100%);
}

.page-head,
.table-card {
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
  margin: 0 0 8px;
  color: #172033;
  font-size: 28px;
}

.page-head p {
  margin: 0;
  color: #667085;
}
</style>
