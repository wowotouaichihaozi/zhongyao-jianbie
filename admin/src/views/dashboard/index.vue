<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue';
import * as echarts from 'echarts/core';
import chinaMap from '@/assets/geo/china-real.json';
import { fetchAdminDashboard } from '@/service/api';
import { useEcharts } from '@/hooks/common/echarts';

echarts.registerMap('china-admin', chinaMap as any);

const provinceNames = ((chinaMap as any).features || []).map((feature: any) => feature.properties?.name).filter(Boolean);

const loading = ref(false);
const data = ref<any>({
  metrics: {},
  regions: [],
  agents: [],
  recentTasks: [],
  recentEvents: [],
  userTrend: [],
  resourceDistribution: []
});
const selectedRegion = ref<any>(null);

const metrics = computed(() => [
  { label: '累计用户', value: data.value.metrics.totalUsers || 0, icon: 'mdi:account-group-outline' },
  { label: '活跃用户', value: data.value.metrics.activeUsers || 0, icon: 'mdi:pulse' },
  { label: '智能体运行', value: data.value.metrics.agentRuns || 0, icon: 'mdi:robot-outline' },
  { label: '画像报告', value: data.value.metrics.profileReports || 0, icon: 'mdi:file-chart-outline' }
]);

function mapOptions() {
  const regions = data.value.regions || [];
  const regionMap = new Map(regions.map((item: any) => [item.name, item]));
  const mapData = provinceNames.map((name: string) => {
    const item = regionMap.get(name) as any;

    return { name, value: item?.value ?? 0 };
  });

  return {
    tooltip: {
      trigger: 'item',
      borderWidth: 0,
      backgroundColor: 'rgba(15, 23, 42, 0.88)',
      textStyle: { color: '#f8fafc' },
      formatter: (params: any) => {
        const item = regions.find((region: any) => region.name === params.name);
        if (!item) return `${params.name}<br/>暂无学习热力数据`;
        return `${item.name}<br/>用户 ${item.userCount} 人<br/>资源 ${item.resourceCount} 个<br/>活跃度 ${item.activity}`;
      }
    },
    visualMap: {
      min: 0,
      max: 100,
      left: 24,
      bottom: 28,
      text: ['高', '低'],
      inRange: { color: ['#eefcf6', '#c7f7e5', '#6ee7b7', '#10b981'] },
      textStyle: { color: '#64748b' },
      calculable: false
    },
    series: [
      {
        name: '区域学习热度',
        type: 'map',
        map: 'china-admin',
        roam: true,
        scaleLimit: { min: 1, max: 3 },
        zoom: 1.18,
        top: 28,
        bottom: 18,
        label: { show: true, color: '#334155', fontSize: 10 },
        emphasis: {
          label: { color: '#065f46', fontWeight: 700 },
          itemStyle: { areaColor: '#34d399', borderColor: '#047857', borderWidth: 1.8 }
        },
        itemStyle: {
          borderColor: '#ffffff',
          borderWidth: 1.1,
          areaColor: '#eefcf6',
          shadowBlur: 14,
          shadowColor: 'rgba(15, 118, 110, 0.12)',
          shadowOffsetY: 8
        },
        data: mapData
      }
    ]
  };
}

const mapChart = useEcharts<any>(mapOptions);
const mapDomRef = mapChart.domRef;

async function loadData() {
  loading.value = true;
  const { data: result, error } = await fetchAdminDashboard();
  if (!error && result) {
    data.value = result;
    selectedRegion.value = result.regions?.[0] || null;
    await mapChart.updateOptions(() => mapOptions() as any);
  }
  loading.value = false;
}

watch(
  () => mapChart.chart.value,
  chart => {
    if (!chart) return;
    chart.off('click');
    chart.on('click', (params: any) => {
      const region = data.value.regions?.find((item: any) => item.name === params.name);
      if (region) selectedRegion.value = region;
    });
  }
);

onMounted(loadData);
</script>

<template>
  <div class="admin-dashboard" :class="{ loading }">
    <header class="dashboard-hero">
      <div>
        <p class="eyebrow">ADMIN VISUAL CENTER</p>
        <h1>中药鉴别数据大屏</h1>
        <p>集中查看区域学习热度、用户画像沉淀、资源生成任务和智能体运行状态。</p>
      </div>
      <NButton type="primary" round secondary @click="loadData">
        <template #icon>
          <SvgIcon icon="mdi:refresh" />
        </template>
        刷新数据
      </NButton>
    </header>

    <section class="metric-grid">
      <NCard v-for="item in metrics" :key="item.label" :bordered="false" class="metric-card">
        <div class="metric-icon">
          <SvgIcon :icon="item.icon" />
        </div>
        <div>
          <span>{{ item.label }}</span>
          <strong>{{ item.value }}</strong>
        </div>
      </NCard>
    </section>

    <section class="screen-grid">
      <NCard :bordered="false" class="map-card">
        <template #header>
          <div class="section-title">
            <span></span>
            全国学习热力分布
          </div>
        </template>
        <div ref="mapDomRef" class="china-map"></div>
      </NCard>

      <div class="side-stack">
        <NCard :bordered="false" class="region-card">
          <template #header>
            <div class="section-title">
              <span></span>
              区域信息
            </div>
          </template>
          <div v-if="selectedRegion" class="region-detail">
            <h2>{{ selectedRegion.name }}</h2>
            <p>{{ selectedRegion.summary }}</p>
            <div class="region-stats">
              <div><strong>{{ selectedRegion.userCount }}</strong><span>用户数</span></div>
              <div><strong>{{ selectedRegion.resourceCount }}</strong><span>资源任务</span></div>
              <div><strong>{{ selectedRegion.profileRate }}</strong><span>画像覆盖</span></div>
            </div>
            <NTag type="success" round>薄弱点：{{ selectedRegion.weakPoints }}</NTag>
          </div>
        </NCard>

        <NCard :bordered="false" class="agent-card">
          <template #header>
            <div class="section-title">
              <span></span>
              智能体运行排行
            </div>
          </template>
          <div v-for="agent in data.agents.slice(0, 5)" :key="agent.id" class="agent-row">
            <div>
              <strong>{{ agent.name }}</strong>
              <span>{{ agent.status }} · 成功率 {{ agent.successRate }}%</span>
            </div>
            <NProgress type="line" :percentage="agent.successRate" :show-indicator="false" status="success" />
          </div>
        </NCard>
      </div>
    </section>

    <section class="bottom-grid">
      <NCard :bordered="false" class="panel-card">
        <template #header>
          <div class="section-title">
            <span></span>
            最近资源任务
          </div>
        </template>
        <NDataTable
          size="small"
          :pagination="false"
          :columns="[
            { title: '任务', key: 'title', ellipsis: { tooltip: true } },
            { title: '类型', key: 'taskType', width: 120 },
            { title: '状态', key: 'status', width: 100 },
            { title: '用户', key: 'displayName', width: 130 },
            { title: '时间', key: 'createdAt', width: 170 }
          ]"
          :data="data.recentTasks"
        />
      </NCard>

      <NCard :bordered="false" class="panel-card">
        <template #header>
          <div class="section-title">
            <span></span>
            最近系统事件
          </div>
        </template>
        <NTimeline>
          <NTimelineItem v-for="event in data.recentEvents.slice(0, 6)" :key="event.id" type="success">
            <template #header>{{ event.title || event.type }}</template>
            <template #default>{{ event.displayName || event.username }} · {{ event.route || '平台事件' }}</template>
            <template #footer>{{ event.createdAt }}</template>
          </NTimelineItem>
        </NTimeline>
      </NCard>
    </section>
  </div>
</template>

<style scoped>
.admin-dashboard {
  min-height: 100%;
  padding: 8px;
  background:
    radial-gradient(circle at 18% 20%, rgba(16, 185, 129, 0.14), transparent 28%),
    linear-gradient(135deg, #f7fffc 0%, #f3fbf8 48%, #eef9f5 100%);
}

.dashboard-hero {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 24px;
  margin-bottom: 18px;
  padding: 22px 26px;
  border: 1px solid rgba(20, 184, 166, 0.12);
  border-radius: 24px;
  background: rgba(255, 255, 255, 0.86);
  box-shadow: 0 18px 46px rgba(15, 118, 110, 0.08);
}

.dashboard-hero h1 {
  margin: 4px 0 8px;
  color: #172033;
  font-size: 30px;
  font-weight: 800;
}

.dashboard-hero p {
  margin: 0;
  color: #667085;
}

.eyebrow {
  color: #10b981 !important;
  font-size: 12px;
  letter-spacing: 2px;
}

.metric-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 16px;
  margin-bottom: 18px;
}

.metric-card :deep(.n-card__content) {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 22px;
}

.metric-card {
  border: 1px solid rgba(20, 184, 166, 0.12);
  border-radius: 20px;
  box-shadow: 0 14px 34px rgba(15, 118, 110, 0.07);
}

.metric-icon {
  display: grid;
  width: 54px;
  height: 54px;
  place-items: center;
  border-radius: 16px;
  background: linear-gradient(135deg, #20c997, #0e9f6e);
  color: white;
  font-size: 28px;
}

.metric-card span {
  color: #7a8f8c;
  font-size: 14px;
}

.metric-card strong {
  display: block;
  color: #172033;
  font-size: 30px;
  line-height: 1.2;
}

.screen-grid {
  display: grid;
  grid-template-columns: minmax(0, 1.5fr) minmax(360px, 0.8fr);
  gap: 18px;
}

.map-card,
.region-card,
.agent-card,
.panel-card {
  border: 1px solid rgba(20, 184, 166, 0.12);
  border-radius: 22px;
  box-shadow: 0 16px 40px rgba(15, 118, 110, 0.07);
}

.section-title {
  display: flex;
  align-items: center;
  gap: 10px;
  color: #172033;
  font-weight: 800;
}

.section-title span {
  width: 4px;
  height: 18px;
  border-radius: 999px;
  background: #10b981;
}

.china-map {
  width: 100%;
  height: 520px;
}

.side-stack {
  display: grid;
  gap: 18px;
}

.region-detail h2 {
  margin: 0 0 8px;
  color: #064e3b;
  font-size: 28px;
}

.region-detail p {
  color: #64748b;
}

.region-stats {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 10px;
  margin: 18px 0;
}

.region-stats div {
  padding: 14px;
  border-radius: 14px;
  background: #eef9f4;
}

.region-stats strong {
  display: block;
  color: #10b981;
  font-size: 24px;
}

.region-stats span,
.agent-row span {
  color: #8aa09c;
  font-size: 13px;
}

.agent-row {
  display: grid;
  gap: 8px;
  padding: 12px 0;
  border-bottom: 1px solid #eef2f1;
}

.agent-row:last-child {
  border-bottom: 0;
}

.agent-row strong {
  display: block;
  color: #1f3433;
}

.bottom-grid {
  display: grid;
  grid-template-columns: 1.2fr 0.8fr;
  gap: 18px;
  margin-top: 18px;
}

@media (max-width: 1180px) {
  .metric-grid,
  .screen-grid,
  .bottom-grid {
    grid-template-columns: 1fr;
  }
}
</style>
