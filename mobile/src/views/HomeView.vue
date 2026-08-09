<template>
  <AppShell>
    <header class="page-head"><span class="eyebrow"><Sparkles :size="15" />PERSONAL LEARNING</span><h1>{{ greeting }}，{{ displayName }}</h1><p>{{ profile ? `当前使用 ${profile.profileName || '学习画像'} v${profile.version || 1}` : '先完成画像采集，让路径和资源真正匹配你。' }}</p></header>
    <AsyncState :loading="loading" :error="error" @retry="load">
      <section v-if="!profile" class="profile-callout">
        <div><span><ScanFace :size="22" /></span><strong>建立你的十维学习画像</strong><p>通过多轮对话收集目标、基础、偏好和时间投入。</p></div>
        <RouterLink class="primary-btn" to="/profile/collect">开始采集<ArrowRight :size="17" /></RouterLink>
      </section>

      <div class="metric-strip dashboard-metrics">
        <div><small>路径进度</small><strong>{{ metrics.pathProgress }}%</strong></div><div><small>学习达成率</small><strong>{{ metrics.achievementRate }}%</strong></div><div><small>知识掌握率</small><strong>{{ metrics.masteryRate === null ? '待验证' : `${metrics.masteryRate}%` }}</strong></div>
        <div><small>生成任务</small><strong>{{ metrics.generatedTaskCount }}</strong></div>
      </div>

      <section class="continue-band">
        <div class="continue-copy"><span>继续学习</span><h2>{{ currentWeek?.title || '个性化学习路径' }}</h2><p>{{ currentWeek?.description || '查看智能体为你编排的学习任务。' }}</p></div>
        <RouterLink class="primary-btn" :to="currentWeek ? `/path/${currentWeek.id}` : '/path'">继续<Play :size="16" /></RouterLink>
      </section>

      <section class="section-block">
        <div class="section-head"><div><h2>最近任务</h2><p>离开页面后任务仍会在后台运行</p></div><RouterLink class="text-link" to="/resources">全部<ChevronRight :size="16" /></RouterLink></div>
        <div v-if="tasks.length" class="card-list"><RouterLink v-for="task in tasks.slice(0,4)" :key="task.taskId" class="item-card" :to="`/resources/task/${task.taskId}`"><span class="item-icon"><component :is="taskIcon(task.taskType)" :size="21" /></span><div><h3>{{ task.title || '生成任务' }}</h3><p>{{ formatDate(task.updatedAt || task.createdAt) }}</p></div><span class="status-pill" :class="task.status">{{ taskLabel(task.status) }}</span></RouterLink></div>
        <div v-else class="state-block compact"><strong>暂无生成任务</strong><RouterLink class="secondary-btn" to="/resources/new">生成学习资源</RouterLink></div>
      </section>

      <section class="section-block quick-section"><div class="section-head"><div><h2>快捷学习</h2><p>从当前画像和路径继续</p></div></div><div class="quick-grid"><RouterLink to="/tutor"><Bot :size="22" /><span><b>AI 辅导</b><small>讲解当前疑问</small></span></RouterLink><RouterLink to="/resources/new"><WandSparkles :size="22" /><span><b>生成资源</b><small>七种个性化资源</small></span></RouterLink><RouterLink to="/profile"><ScanFace :size="22" /><span><b>更新画像</b><small>让推荐随学习变化</small></span></RouterLink><RouterLink to="/path"><Map :size="22" /><span><b>路径地图</b><small>查看纵向周计划</small></span></RouterLink></div></section>
    </AsyncState>
  </AppShell>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { ArrowRight, Bot, BookOpen, ChevronRight, Clapperboard, FileText, Map, Play, ScanFace, Sparkles, WandSparkles } from 'lucide-vue-next'
import { RouterLink } from 'vue-router'
import AppShell from '../components/AppShell.vue'; import AsyncState from '../components/AsyncState.vue'
import { getEffectAssessment, getPathConfig, getProfiles, getTaskHistory } from '../services/api.js'
import { authState } from '../stores/auth.js'; import { activeProfile, effectAssessmentMetrics, formatDate, pathWeeks, taskList } from '../utils/data.js'; import { trackTask } from '../stores/tasks.js'
const loading=ref(true),error=ref(''),profile=ref(null),weeks=ref([]),tasks=ref([]),assessment=ref({})
const displayName=computed(()=>authState.user.displayName||authState.user.username||'学习者')
const greeting=computed(()=>new Date().getHours()<11?'早上好':new Date().getHours()<18?'下午好':'晚上好')
const currentWeek=computed(()=>weeks.value.find(x=>x.state==='current')||weeks.value.find(x=>x.state==='available')||weeks.value[0])
const currentWeekLabel=computed(()=>currentWeek.value?`第 ${currentWeek.value.order} 周`:'--')
const metrics=computed(()=>effectAssessmentMetrics(assessment.value,weeks.value,tasks.value))
const runningTasks=computed(()=>tasks.value.filter(x=>['queued','running'].includes(x.status)))
async function load(){loading.value=true;error.value='';try{const [p,c,h,a]=await Promise.allSettled([getProfiles(),getPathConfig(),getTaskHistory(40),getEffectAssessment()]);if(p.status==='fulfilled')profile.value=activeProfile(p.value);if(c.status==='fulfilled')weeks.value=pathWeeks(c.value);if(h.status==='fulfilled'){tasks.value=taskList(h.value);runningTasks.value?.forEach?.(trackTask)}if(a.status==='fulfilled')assessment.value=a.value;if([p,c,h,a].every(x=>x.status==='rejected'))throw p.reason}catch(e){error.value=e.message}finally{loading.value=false}}
function taskLabel(s){return {queued:'排队中',running:'生成中',complete:'已完成',failed:'失败',waiting:'待确认'}[s]||s}
function taskIcon(t){return /video|animation/.test(t)?Clapperboard:/document|ppt/.test(t)?FileText:BookOpen}
onMounted(load)
</script>

<style scoped>
.profile-callout{display:grid;gap:14px;padding:16px;border:1px solid #cfe0d7;border-radius:7px;background:#fff}.profile-callout>div>span{float:left;width:44px;height:44px;display:grid;place-items:center;margin-right:12px;border-radius:6px;background:#e8f3ed;color:#176f4b}.profile-callout strong{display:block;font-size:15px}.profile-callout p{margin:5px 0 0;color:#63756c;font-size:11px;line-height:1.55}.continue-band{display:grid;gap:16px;margin:16px 0 0;padding:18px;border:1px solid #d5e0da;border-radius:7px;background:#fff}.continue-copy span{color:#176f4b;font-size:10px;font-weight:800}.continue-copy h2{margin:6px 0 0;font-size:18px;line-height:1.4}.continue-copy p{margin:6px 0 0;color:#65766d;font-size:11px;line-height:1.55}.continue-band .primary-btn{justify-self:start}.quick-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:9px}.quick-grid a{min-height:78px;display:grid;grid-template-columns:30px minmax(0,1fr);align-items:center;gap:7px;padding:12px;border:1px solid #dce5e0;border-radius:6px;color:#176f4b}.quick-grid b,.quick-grid small{display:block}.quick-grid b{font-size:13px}.quick-grid small{margin-top:3px;color:#76837d;font-size:9px;line-height:1.4}.state-block.compact{min-height:130px}
.dashboard-metrics{grid-template-columns:repeat(2,minmax(0,1fr))}.dashboard-metrics>div:nth-child(2n){border-right:0}.dashboard-metrics>div:nth-child(-n+2){border-bottom:1px solid #dce5e0}
</style>
