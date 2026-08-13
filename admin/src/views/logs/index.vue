<script setup lang="tsx">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue';
import { NProgress, NTag } from 'naive-ui';
import { fetchAdminRuntime } from '@/service/api';

const loading = ref(false);
const autoRefresh = ref(true);
const runtime = ref<any>({ snapshot: { resources: {}, services: [], processes: [] }, history: [] });
let refreshTimer: ReturnType<typeof setInterval> | null = null;

const snapshot = computed(() => runtime.value.snapshot || { resources: {}, services: [], processes: [] });
const resources = computed(() => snapshot.value.resources || {});
const healthLabel = computed(() => {
  const labels: Record<string, string> = { healthy: '运行正常', warning: '资源紧张', critical: '资源告急' };
  return labels[snapshot.value.severity] || '状态未知';
});
const healthType = computed(() => {
  if (snapshot.value.severity === 'critical') return 'error';
  if (snapshot.value.severity === 'warning') return 'warning';
  return 'success';
});

const resourceCards = computed(() => [
  { label: 'CPU', value: resources.value.cpuPercent, suffix: '%', icon: 'mdi:cpu-64-bit' },
  { label: '内存', value: resources.value.memoryPercent, suffix: '%', icon: 'mdi:memory' },
  { label: '磁盘', value: resources.value.diskPercent, suffix: '%', icon: 'mdi:harddisk' },
  {
    label: '系统负载',
    value: resources.value.loadAverage?.length ? resources.value.loadAverage[0] : null,
    suffix: '',
    icon: 'mdi:chart-timeline-variant-shimmer'
  }
]);

const processColumns = [
  { title: 'PID', key: 'pid', width: 90 },
  { title: '项目进程', key: 'name', minWidth: 170 },
  { title: '状态', key: 'state', minWidth: 130, ellipsis: { tooltip: true } },
  {
    title: '内存',
    key: 'memoryMb',
    width: 120,
    render: (row: any) => (row.memoryMb == null ? '-' : `${row.memoryMb} MB`)
  }
];

const historyColumns = [
  { title: '采集时间', key: 'timestamp', minWidth: 190 },
  {
    title: '状态',
    key: 'severity',
    width: 110,
    render: (row: any) => {
      const type = row.severity === 'critical' ? 'error' : row.severity === 'warning' ? 'warning' : 'success';
      const label = row.severity === 'critical' ? '告急' : row.severity === 'warning' ? '紧张' : '正常';
      return <NTag type={type as any}>{label}</NTag>;
    }
  },
  { title: 'CPU', key: 'cpu', width: 100, render: (row: any) => metricText(row.resources?.cpuPercent) },
  { title: '内存', key: 'memory', width: 100, render: (row: any) => metricText(row.resources?.memoryPercent) },
  { title: '磁盘', key: 'disk', width: 100, render: (row: any) => metricText(row.resources?.diskPercent) }
];

function metricText(value: unknown) {
  return value == null ? '-' : `${value}%`;
}

function formatBytes(value: unknown) {
  const bytes = Number(value || 0);
  if (!bytes) return '0 GB';
  return `${(bytes / 1024 / 1024 / 1024).toFixed(1)} GB`;
}

function formatUptime(value: unknown) {
  const seconds = Number(value || 0);
  const days = Math.floor(seconds / 86400);
  const hours = Math.floor((seconds % 86400) / 3600);
  return `${days} 天 ${hours} 小时`;
}

function metricStatus(value: unknown) {
  const number = Number(value || 0);
  if (number >= 95) return 'error';
  if (number >= 85) return 'warning';
  return 'success';
}

async function loadData(showLoading = true) {
  if (showLoading) loading.value = true;
  const { data, error } = await fetchAdminRuntime(80);
  if (!error && data) runtime.value = data;
  loading.value = false;
}

function scheduleRefresh() {
  if (refreshTimer) clearInterval(refreshTimer);
  refreshTimer = setInterval(() => {
    if (autoRefresh.value && !document.hidden) void loadData(false);
  }, 10000);
}

onMounted(() => {
  void loadData();
  scheduleRefresh();
});

onBeforeUnmount(() => {
  if (refreshTimer) clearInterval(refreshTimer);
});
</script>

<template>
  <div class="runtime-page">
    <header class="page-head">
      <div>
        <div class="title-line">
          <h1>服务器运行监控</h1>
          <NTag :type="healthType" round>{{ healthLabel }}</NTag>
        </div>
        <p>仅超级管理员可见，展示项目服务与服务器资源；完整命令行、密钥和用户内容不会进入监控日志。</p>
      </div>
      <div class="head-actions">
        <NSwitch v-model:value="autoRefresh" size="small">
          <template #checked>自动刷新</template>
          <template #unchecked>手动刷新</template>
        </NSwitch>
        <NButton :loading="loading" type="primary" secondary @click="loadData()">
          <template #icon><SvgIcon icon="mdi:refresh" /></template>
          刷新
        </NButton>
      </div>
    </header>

    <section class="resource-grid">
      <NCard v-for="item in resourceCards" :key="item.label" :bordered="false" class="resource-card">
        <div class="resource-head">
          <span class="resource-icon"><SvgIcon :icon="item.icon" /></span>
          <span>{{ item.label }}</span>
        </div>
        <strong>{{ item.value == null ? '-' : item.value }}{{ item.suffix }}</strong>
        <NProgress
          v-if="item.suffix === '%'"
          type="line"
          :percentage="Number(item.value || 0)"
          :status="metricStatus(item.value)"
          :show-indicator="false"
        />
      </NCard>
    </section>

    <section class="summary-strip">
      <span>内存 {{ formatBytes(resources.memoryUsedBytes) }} / {{ formatBytes(resources.memoryTotalBytes) }}</span>
      <span>磁盘 {{ formatBytes(resources.diskUsedBytes) }} / {{ formatBytes(resources.diskTotalBytes) }}</span>
      <span>运行 {{ formatUptime(resources.uptimeSeconds) }}</span>
      <span>采集 {{ snapshot.timestamp || '-' }}</span>
    </section>

    <section class="monitor-grid">
      <NCard :bordered="false" class="panel-card">
        <template #header>项目服务</template>
        <div class="service-list">
          <div v-for="service in snapshot.services" :key="service.name" class="service-row">
            <span :class="['status-dot', service.status]"></span>
            <div><strong>{{ service.name }}</strong><small>{{ service.detail }}</small></div>
            <NTag :type="service.status === 'online' ? 'success' : service.status === 'offline' ? 'error' : 'default'" size="small">
              {{ service.status === 'online' ? '在线' : service.status === 'offline' ? '离线' : '本地不适用' }}
            </NTag>
          </div>
        </div>
      </NCard>

      <NCard :bordered="false" class="panel-card">
        <template #header>项目相关进程</template>
        <NDataTable :columns="processColumns" :data="snapshot.processes || []" :pagination="false" size="small" />
      </NCard>
    </section>

    <NCard :bordered="false" class="history-card">
      <template #header>
        <div class="history-head">
          <span>资源采集记录</span>
          <code>{{ runtime.logFile || 'logs/system-monitor.jsonl' }}</code>
        </div>
      </template>
      <NDataTable
        :columns="historyColumns"
        :data="[...(runtime.history || [])].reverse()"
        :pagination="{ pageSize: 12 }"
        size="small"
      />
    </NCard>
  </div>
</template>

<style scoped>
.runtime-page { min-height: 100%; padding: 8px; color: #17212b; background: #f5f7f8; }
.page-head { display: flex; align-items: center; justify-content: space-between; gap: 24px; margin-bottom: 16px; padding: 20px 22px; border: 1px solid #e2e8e6; border-radius: 8px; background: #fff; }
.page-head h1 { margin: 0; font-size: 24px; letter-spacing: 0; }
.page-head p { max-width: 760px; margin: 7px 0 0; color: #66736f; font-size: 13px; }
.title-line, .head-actions, .resource-head, .history-head { display: flex; align-items: center; gap: 10px; }
.head-actions { flex: 0 0 auto; gap: 16px; }
.resource-grid { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 14px; }
.resource-card, .panel-card, .history-card { border: 1px solid #e2e8e6; border-radius: 8px; box-shadow: none; }
.resource-head { color: #64716d; font-size: 13px; }
.resource-icon { display: grid; width: 32px; height: 32px; place-items: center; border-radius: 6px; background: #e9f5f1; color: #087451; font-size: 19px; }
.resource-card strong { display: block; margin: 14px 0 12px; font-size: 27px; line-height: 1; }
.summary-strip { display: flex; flex-wrap: wrap; gap: 12px 28px; margin: 14px 0; padding: 12px 16px; border: 1px solid #e2e8e6; border-radius: 6px; background: #fff; color: #5f6d68; font-size: 12px; }
.monitor-grid { display: grid; grid-template-columns: minmax(300px, .8fr) minmax(480px, 1.2fr); gap: 14px; }
.service-list { display: grid; gap: 2px; }
.service-row { display: grid; grid-template-columns: 10px minmax(0, 1fr) auto; align-items: center; gap: 11px; padding: 12px 0; border-bottom: 1px solid #edf0ef; }
.service-row:last-child { border-bottom: 0; }
.service-row strong, .service-row small { display: block; }
.service-row small { margin-top: 3px; color: #84908c; }
.status-dot { width: 8px; height: 8px; border-radius: 50%; background: #94a3b8; }
.status-dot.online { background: #10b981; }
.status-dot.offline { background: #ef4444; }
.history-card { margin-top: 14px; }
.history-head { justify-content: space-between; }
.history-head code { color: #66736f; font-size: 11px; font-weight: 400; }
@media (max-width: 1050px) { .resource-grid { grid-template-columns: repeat(2, 1fr); } .monitor-grid { grid-template-columns: 1fr; } }
@media (max-width: 640px) { .page-head { align-items: flex-start; flex-direction: column; } .head-actions { width: 100%; justify-content: space-between; } .resource-grid { grid-template-columns: 1fr 1fr; } .summary-strip { flex-direction: column; gap: 6px; } }
</style>
