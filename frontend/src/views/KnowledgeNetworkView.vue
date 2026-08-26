<template>
  <main class="network-page graph-mode">
    <nav class="view-tabs" aria-label="知识网络视图">
      <button :class="{ active: activeView === 'graph' }" type="button" @click="activeView = 'graph'"><Network :size="17" />关系网络</button>
      <button :class="{ active: activeView === 'growth' }" type="button" @click="activeView = 'growth'"><BrainCircuit :size="17" />AI 知识库自生长<span v-if="growthStats.conversationTurns">{{ growthStats.conversationTurns }}</span></button>
    </nav>

    <section v-show="activeView === 'graph'" class="graph-workspace" :class="{ 'has-selection': selectedNode }">
      <div class="graph-toolbar">
        <div class="search-wrap" @focusout="closeSearchLater">
          <label class="search-control"><Search :size="17" /><input
            v-model="query"
            placeholder="搜索名称、来源或知识域"
            autocomplete="off"
            @focus="searchOpen = true"
            @input="onSearchInput"
            @keydown.down.prevent="moveSearchSelection(1)"
            @keydown.up.prevent="moveSearchSelection(-1)"
            @keydown.enter.prevent="focusSearchResult"
            @keydown.esc.prevent="searchOpen = false"
          /></label>
          <div v-if="searchOpen && query.trim()" class="search-results" role="listbox" aria-label="相似知识节点">
            <button
              v-for="(result, index) in searchResults"
              :key="result.node.id"
              type="button"
              role="option"
              :aria-selected="index === searchIndex"
              :class="{ active: index === searchIndex }"
              @mouseenter="searchIndex = index"
              @mousedown.prevent="selectSearchResult(result)"
            >
              <i :style="{ background: categoryFor(result.node.type).color }"></i>
              <span><strong>{{ result.node.name }}</strong><small>{{ searchResultMeta(result.node) }}</small></span>
              <em>{{ categoryFor(result.node.type).label }}</em>
            </button>
            <div v-if="!searchResults.length" class="search-empty">没有找到相似节点</div>
          </div>
        </div>
        <label class="select-control"><Filter :size="15" /><select v-model="typeFilter"><option value="">全部类型</option><option v-for="item in categories" :key="item.key" :value="item.key">{{ item.label }}</option></select></label>
        <label class="select-control"><Database :size="15" /><select v-model="collectionId" @change="loadGraph"><option value="">全部知识集合</option><option v-for="collection in collections" :key="collection.id" :value="collection.id">{{ collection.name }}</option></select></label>
        <button class="icon-command" type="button" title="重新布局" @click="refreshLayout"><RefreshCw :size="17" /></button>
        <button class="icon-command" type="button" title="适应视图" @click="fitGraph"><Scan :size="17" /></button>
      </div>

      <div class="graph-stage" :aria-busy="loading">
        <KnowledgeSigmaGraph
          ref="graphView"
          :nodes="networkData.nodes"
          :edges="networkData.edges"
          :type-filter="typeFilter"
          @ready="onGraphReady"
          @node-select="selectGraphNode"
          @error="handleGraphError"
        />
        <div v-if="loading" class="graph-loading"><LoaderCircle class="spin" :size="25" /><span>正在读取真实知识关系</span></div>
        <div class="source-mark"><ShieldCheck :size="14" />{{ formatCount(networkData.stats?.courseDocuments) }} 份真实文档 · {{ formatCount(networkData.stats?.visibleEdges) }} 条关系</div>
      </div>

      <aside class="node-panel" :class="{ open: selectedNode }">
        <button v-if="selectedNode" class="close-panel" type="button" title="关闭" @click="clearSelection"><X :size="17" /></button>
        <template v-if="selectedNode">
          <span class="node-type" :style="{ color: categoryFor(selectedNode.type).color }">{{ categoryFor(selectedNode.type).label }}</span>
          <h2>{{ selectedNode.name }}</h2>
          <p v-if="selectedNode.excerpt">{{ selectedNode.excerpt }}</p>
          <dl>
            <template v-if="selectedNode.source"><dt>真实来源</dt><dd>{{ selectedNode.source }}</dd></template>
            <template v-if="selectedNode.domain"><dt>知识域</dt><dd>{{ selectedNode.domain }}</dd></template>
            <template v-if="selectedNode.page"><dt>页码</dt><dd>{{ selectedNode.page }}</dd></template>
            <template v-if="selectedNode.section"><dt>片段</dt><dd>{{ selectedNode.section }}</dd></template>
            <template v-if="selectedNode.chunkCount"><dt>索引片段</dt><dd>{{ selectedNode.chunkCount }}</dd></template>
            <template v-if="selectedNode.count"><dt>关联文档</dt><dd>{{ formatCount(selectedNode.count) }}</dd></template>
            <template v-if="selectedNode.topics?.length"><dt>文档主题</dt><dd>{{ selectedNode.topics.join('、') }}</dd></template>
            <template v-if="selectedNode.runId"><dt>运行记录</dt><dd>{{ selectedNode.runId }}</dd></template>
            <dt>验证状态</dt><dd :class="selectedNode.verified ? 'verified' : 'pending'">{{ selectedNode.verified ? '来源可追溯' : '待审核' }}</dd>
          </dl>
          <section v-if="selectedRelations.length" class="related-nodes">
            <div><strong>直接关联</strong><span>{{ formatCount(selectedRelationCount) }} 项</span></div>
            <button v-for="item in selectedRelations" :key="item.node.id" type="button" @click="selectRelatedNode(item.node)">
              <i :style="{ background: categoryFor(item.node.type).color }"></i>
              <span><b>{{ item.node.name }}</b><small>{{ item.node.source || item.node.domain || categoryFor(item.node.type).label }}</small></span>
            </button>
            <p v-if="selectedRelationCount > selectedRelations.length">仅列出前 {{ selectedRelations.length }} 项，其余关系可通过搜索精确定位。</p>
          </section>
          <button v-if="isExpandable(selectedNode)" class="primary-command" type="button" :disabled="expanding" @click="expandSelected">
            <LoaderCircle v-if="expanding" class="spin" :size="16" /><GitBranch v-else :size="16" />展开关联节点
          </button>
        </template>
        <div v-else class="panel-placeholder"><MousePointer2 :size="24" /><span>选择节点查看真实来源与关系</span></div>
      </aside>
    </section>

    <section v-show="activeView === 'growth'" class="growth-workspace">
      <div class="growth-scroll">
        <section class="memory-view">
          <div class="timeline-heading">
            <div><p>AGENT KNOWLEDGE GROWTH</p><h2>AI 知识库自生长</h2></div>
            <button class="icon-command light" type="button" title="刷新对话记忆" @click="loadGrowth"><RefreshCw :size="17" /></button>
          </div>
          <p class="growth-intro">系统持续记录当前用户与智能体的每轮对话，从原始问答中提取主题、核心信息和学习信号，写入用户隔离的长期记忆；下一轮智能体会读取这些记忆，让画像、路径和资源逐步贴合用户。</p>

          <div class="growth-pipeline" aria-label="对话知识自生长流程">
            <article v-for="(stage, index) in growthStages" :key="stage.key" :class="{ active: stage.count > 0 }">
              <span>{{ String(index + 1).padStart(2, '0') }}</span><component :is="stage.icon" :size="20" />
              <div><strong>{{ stage.label }}</strong><small>{{ stage.note }}</small></div><b>{{ formatCount(stage.count) }}</b>
            </article>
          </div>

          <div class="memory-rule"><ShieldCheck :size="18" /><div><strong>对话记忆与可信课程知识分层保存</strong><span>对话记忆用于理解用户目标、偏好和薄弱点；课程结论仍由本地可信文档与引用提供，避免把聊天内容直接当成事实。</span></div></div>

          <div class="memory-layout">
            <section class="memory-feed">
              <div class="growth-subhead">
                <div><p>CONVERSATION MEMORY</p><h2>对话成长流水</h2></div>
                <span>{{ formatCount(filteredMemories.length) }} / {{ formatCount(memories.length) }} 轮</span>
              </div>
              <div class="memory-toolbar">
                <label><Search :size="15" /><input v-model.trim="memoryQuery" placeholder="搜索对话、摘要或主题" /></label>
                <select v-model="memorySource"><option value="">全部对话入口</option><option value="xiaozhi">岐小智总控</option><option value="profile-dialogue">学习画像对话</option><option value="demo-conversation">示例对话</option></select>
              </div>
              <div v-if="!filteredMemories.length" class="empty-view"><MessageSquareText :size="38" /><strong>还没有可展示的对话记忆</strong><span>与岐小智或学习画像智能体完成一轮对话后，这里会自动出现提取结果。</span></div>
              <div v-else class="memory-list">
                <article v-for="item in filteredMemories" :key="item.id" class="memory-card">
                  <div class="memory-meta"><span>{{ sourceLabel(item.sourceType) }}</span><time>{{ formatTime(item.updatedAt) }}</time></div>
                  <div class="dialogue-pair">
                    <div><UserRound :size="15" /><p>{{ item.userMessage }}</p></div>
                    <div><Bot :size="15" /><p>{{ item.assistantMessage || '智能体正在处理本轮对话' }}</p></div>
                  </div>
                  <div class="core-memory"><BrainCircuit :size="18" /><div><small>提取的核心记忆</small><strong>{{ item.summary }}</strong></div></div>
                  <div v-if="item.topics?.length" class="memory-tags"><span v-for="topic in item.topics" :key="topic"># {{ topic }}</span></div>
                  <div v-if="item.signals?.length" class="memory-signals"><span v-for="(signal, index) in item.signals" :key="`${signal.type}-${index}`"><b>{{ signal.type }}</b>{{ signal.value }}</span></div>
                </article>
              </div>
            </section>

            <aside class="memory-insights">
              <div class="growth-subhead"><div><p>GROWTH INSIGHT</p><h2>持续形成的用户知识</h2></div></div>
              <div class="memory-metrics">
                <article><MessageSquareText :size="18" /><strong>{{ formatCount(growthStats.conversationTurns) }}</strong><span>已记录对话</span></article>
                <article><Sparkles :size="18" /><strong>{{ formatCount(growthStats.completedExtractions) }}</strong><span>完成提取</span></article>
                <article><Tags :size="18" /><strong>{{ formatCount(growthStats.topicCount) }}</strong><span>关联主题</span></article>
                <article><BrainCircuit :size="18" /><strong>{{ formatCount(growthStats.signalCount) }}</strong><span>学习信号</span></article>
              </div>
              <section class="topic-cloud"><h3>高频记忆主题</h3><div v-if="growthTopics.length"><button v-for="topic in growthTopics" :key="topic.name" type="button" @click="memoryQuery = topic.name"><span>{{ topic.name }}</span><b>{{ topic.count }}</b></button></div><p v-else>完成对话后自动聚合主题。</p></section>
              <section class="memory-return"><h3>如何进入下一轮智能体</h3><ol><li><span>1</span><div><strong>读取长期记忆</strong><p>按当前账号加载最近核心摘要与学习信号。</p></div></li><li><span>2</span><div><strong>合并动态画像</strong><p>与做题、实验、路径进度等学习证据共同编排。</p></div></li><li><span>3</span><div><strong>保留原始来源</strong><p>每条摘要都可回看对应用户消息和智能体回复。</p></div></li></ol></section>
            </aside>
          </div>
        </section>
      </div>
    </section>

    <div v-if="notice.message" class="notice" :class="notice.type"><CheckCircle2 v-if="notice.type === 'success'" :size="17" /><CircleAlert v-else :size="17" />{{ notice.message }}</div>
  </main>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import {
  Bot, BrainCircuit, CheckCircle2, CircleAlert, Database, Filter, LoaderCircle,
  MessageSquareText, MousePointer2, Network, RefreshCw, Scan, Search, Share2,
  ShieldCheck, Sparkles, Tags, UserRound, X,
} from 'lucide-vue-next'
import KnowledgeSigmaGraph from '../components/KnowledgeSigmaGraph.vue'
import {
  expandKnowledgeNetworkNode, getKnowledgeCollections, getKnowledgeGrowthOverview,
  getKnowledgeNetworkOverview,
} from '../services/api.js'

const graphView = ref(null)
const activeView = ref('graph')
const loading = ref(true)
const expanding = ref(false)
const query = ref('')
const searchOpen = ref(false)
const searchIndex = ref(0)
const typeFilter = ref('')
const collectionId = ref('')
const selectedNode = ref(null)
const networkData = reactive({ nodes: [], edges: [], stats: {}, limits: {} })
const collections = ref([])
const memories = ref([])
const growthTopics = ref([])
const growthStats = reactive({ conversationTurns: 0, completedExtractions: 0, topicCount: 0, signalCount: 0, contextReady: 0 })
const memoryQuery = ref('')
const memorySource = ref('')
const notice = reactive({ type: 'success', message: '' })
let noticeTimer = 0

const categories = [
  { key: 'root', label: '知识中枢', color: '#f2c14e' },
  { key: 'domain', label: '知识域', color: '#36c2a4' },
  { key: 'topic', label: '主题', color: '#58a6ff' },
  { key: 'collection', label: '私有集合', color: '#e879a9' },
  { key: 'document', label: '文档', color: '#a78bfa' },
  { key: 'citation', label: '引用片段', color: '#f59e68' },
  { key: 'agent', label: '智能体', color: '#66d9ef' },
  { key: 'artifact', label: '生成产物', color: '#8dd35f' },
  { key: 'feedback', label: '反哺候选', color: '#ff7a7a' },
]

const growthStages = computed(() => [
  { key: 'capture', label: '保存完整对话', note: '保留用户与智能体原始问答', count: growthStats.conversationTurns, icon: MessageSquareText },
  { key: 'extract', label: '提取核心信息', note: '生成可追溯的对话摘要', count: growthStats.completedExtractions, icon: Sparkles },
  { key: 'topics', label: '归并知识主题', note: '连接多轮对话中的共同主题', count: growthStats.topicCount, icon: Tags },
  { key: 'signals', label: '沉淀学习信号', note: '识别目标、偏好与薄弱点', count: growthStats.signalCount, icon: BrainCircuit },
  { key: 'context', label: '回流智能体上下文', note: '下一轮编排自动读取', count: growthStats.contextReady, icon: Share2 },
])
const filteredMemories = computed(() => {
  const needle = normalizeSearch(memoryQuery.value)
  return memories.value.filter(item => {
    if (memorySource.value && item.sourceType !== memorySource.value) return false
    if (!needle) return true
    return normalizeSearch([
      item.userMessage, item.assistantMessage, item.summary,
      ...(item.topics || []), ...(item.signals || []).map(signal => `${signal.type} ${signal.value}`),
    ].join(' ')).includes(needle)
  })
})
const allSelectedRelations = computed(() => {
  const selectedId = selectedNode.value?.id
  if (!selectedId) return []
  const nodesById = new Map(networkData.nodes.map(node => [node.id, node]))
  const seen = new Set()
  const related = []
  networkData.edges.forEach(edge => {
    const otherId = edge.source === selectedId ? edge.target : edge.target === selectedId ? edge.source : ''
    if (!otherId || seen.has(otherId)) return
    const node = nodesById.get(otherId)
    if (!node) return
    seen.add(otherId)
    related.push({ node, relation: edge.relation || '' })
  })
  const priority = { document: 0, citation: 1, topic: 2, domain: 3 }
  return related.sort((left, right) =>
    (priority[left.node.type] ?? 9) - (priority[right.node.type] ?? 9)
    || String(left.node.name || '').localeCompare(String(right.node.name || ''), 'zh-CN'))
})
const selectedRelationCount = computed(() => allSelectedRelations.value.length)
const selectedRelations = computed(() => allSelectedRelations.value.slice(0, 14))
const searchResults = computed(() => {
  const needle = normalizeSearch(query.value)
  if (!needle) return []
  return networkData.nodes
    .map((node, index) => ({ node, index, score: scoreNode(node, needle) }))
    .filter(item => item.score > 0 && (!typeFilter.value || item.node.type === typeFilter.value))
    .sort((left, right) => right.score - left.score || String(left.node.name || '').localeCompare(String(right.node.name || ''), 'zh-CN'))
    .slice(0, 10)
})
function categoryFor(type) { return categories.find(item => item.key === type) || { key: type, label: type || '节点', color: '#9aa8a4' } }
function isExpandable(node) { return ['domain', 'document', 'collection'].includes(node?.type) }
function formatCount(value) { return Number(value || 0).toLocaleString('zh-CN') }
function formatTime(value) {
  if (!value) return '未记录'
  return new Intl.DateTimeFormat('zh-CN', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' }).format(new Date(value))
}
function sourceLabel(sourceType) {
  return { xiaozhi: '岐小智总控', 'profile-dialogue': '学习画像对话', 'demo-conversation': '示例对话' }[sourceType] || '平台对话'
}
function showNotice(message, type = 'success') {
  window.clearTimeout(noticeTimer)
  notice.message = message
  notice.type = type
  noticeTimer = window.setTimeout(() => { notice.message = '' }, 4000)
}

function normalizeSearch(value) {
  return String(value || '').trim().toLocaleLowerCase('zh-CN').replace(/\s+/g, ' ')
}

function bigrams(value) {
  const compact = value.replace(/\s+/g, '')
  if (compact.length < 2) return compact ? [compact] : []
  return Array.from({ length: compact.length - 1 }, (_, index) => compact.slice(index, index + 2))
}

function diceSimilarity(left, right) {
  const leftPairs = bigrams(left)
  const rightPairs = bigrams(right)
  if (!leftPairs.length || !rightPairs.length) return 0
  const counts = new Map()
  rightPairs.forEach(pair => counts.set(pair, (counts.get(pair) || 0) + 1))
  let overlap = 0
  leftPairs.forEach(pair => {
    const count = counts.get(pair) || 0
    if (count > 0) { overlap += 1; counts.set(pair, count - 1) }
  })
  return (2 * overlap) / (leftPairs.length + rightPairs.length)
}

function scoreNode(node, needle) {
  const name = normalizeSearch(node.name)
  const source = normalizeSearch(node.source)
  const domain = normalizeSearch(node.domain)
  if (name === needle) return 1000
  let score = 0
  if (name.startsWith(needle)) score = Math.max(score, 760 - Math.min(180, name.length - needle.length))
  if (name.includes(needle)) score = Math.max(score, 590 - Math.min(160, name.indexOf(needle) * 4))
  if (source.includes(needle)) score = Math.max(score, 430)
  if (domain.includes(needle)) score = Math.max(score, 360)
  const tokens = needle.split(' ').filter(Boolean)
  if (tokens.length > 1) {
    const searchable = `${name} ${source} ${domain}`
    const hits = tokens.filter(token => searchable.includes(token)).length
    score = Math.max(score, Math.round((hits / tokens.length) * 520))
  }
  const similarity = diceSimilarity(needle, name)
  if (similarity >= .26) score = Math.max(score, Math.round(similarity * 500))
  return score
}

function onSearchInput() { searchOpen.value = true; searchIndex.value = 0 }
function moveSearchSelection(delta) {
  if (!searchResults.value.length) return
  searchOpen.value = true
  searchIndex.value = (searchIndex.value + delta + searchResults.value.length) % searchResults.value.length
}
function closeSearchLater() { window.setTimeout(() => { searchOpen.value = false }, 120) }
function searchResultMeta(node) { return node.source || node.domain || `${Number(node.chunkCount || node.count || 0).toLocaleString('zh-CN')} 个关联` }
function selectSearchResult(result) {
  if (!result) return
  selectNode(result.node)
  searchOpen.value = false
}

function selectRelatedNode(node) {
  selectNode(node)
}

function clearSelection() {
  selectedNode.value = null
  graphView.value?.clearFocus()
}

function onGraphReady() { loading.value = false }
function selectGraphNode(nodeId) { selectNode(networkData.nodes.find(node => node.id === nodeId) || null, false) }

function selectNode(node, focus = true) {
  selectedNode.value = node
  if (!node) return
  if (focus) graphView.value?.focusNode(node.id)
  if (node.type === 'document' && String(node.id || '').startsWith('course-document:') && !node.detailLoaded) {
    void loadDocumentDetail(node)
  }
}

async function loadDocumentDetail(node) {
  node.detailLoaded = true
  try {
    const data = await expandKnowledgeNetworkNode(node.id, 1)
    if (data.detail?.excerpt) node.excerpt = data.detail.excerpt
  } catch {
    node.detailLoaded = false
  }
}
function handleGraphError(message) { loading.value = false; showNotice(message || '知识网络渲染失败', 'error') }

async function loadGraph() {
  loading.value = true
  try {
    const params = { view: 'atlas', limit: 15000 }
    if (collectionId.value) params.collectionId = collectionId.value
    const data = await getKnowledgeNetworkOverview(params)
    networkData.nodes = data.nodes || []
    networkData.edges = data.edges || []
    networkData.stats = data.stats || {}
    networkData.limits = data.limits || {}
    await nextTick()
    if (!networkData.nodes.length) loading.value = false
  } catch (error) { loading.value = false; showNotice(error.response?.data?.msg || '知识网络加载失败', 'error') }
}

async function expandSelected() {
  if (!selectedNode.value) return
  expanding.value = true
  try {
    const data = await expandKnowledgeNetworkNode(selectedNode.value.id, 30)
    const knownNodes = new Set(networkData.nodes.map(node => node.id))
    const knownEdges = new Set(networkData.edges.map(edge => `${edge.source}|${edge.target}|${edge.relation}`))
    networkData.nodes = [...networkData.nodes, ...data.nodes.filter(node => !knownNodes.has(node.id))]
    networkData.edges = [...networkData.edges, ...data.edges.filter(edge => !knownEdges.has(`${edge.source}|${edge.target}|${edge.relation}`))]
    networkData.stats.visibleNodes = networkData.nodes.length
    await nextTick()
    graphView.value?.rebuild()
    showNotice(`已展开 ${data.nodes.length} 个真实关联节点`)
  } catch (error) { showNotice(error.response?.data?.msg || '节点展开失败', 'error') }
  finally { expanding.value = false }
}

function refreshLayout() { graphView.value?.refreshLayout() }
function fitGraph() { graphView.value?.fit() }
function focusSearchResult() {
  if (!query.value.trim()) return
  const result = searchResults.value[searchIndex.value] || searchResults.value[0]
  if (!result) return showNotice('没有找到相似的文档、来源或知识域', 'error')
  selectSearchResult(result)
}

async function loadCollections() {
  try {
    const result = await getKnowledgeCollections()
    collections.value = result.data?.collections || []
  } catch { collections.value = [] }
}
async function loadGrowth() {
  try {
    const data = await getKnowledgeGrowthOverview(80)
    memories.value = data?.memories || []
    growthTopics.value = data?.topics || []
    Object.assign(growthStats, data?.stats || {})
  } catch (error) { showNotice(error.response?.data?.msg || '对话记忆加载失败', 'error') }
}
watch(activeView, view => { if (view === 'graph') nextTick(fitGraph) })
onMounted(async () => {
  await Promise.all([loadCollections(), loadGraph(), loadGrowth()])
})
onBeforeUnmount(() => { window.clearTimeout(noticeTimer) })
</script>

<style scoped>
.network-page { min-height: calc(100vh - 72px); padding: 28px 32px 60px; box-sizing: border-box; background: #f3f6f4; color: #18211f; letter-spacing: 0; }
.network-page.graph-mode { width: 100%; height: calc(100vh - 72px); min-height: 0; padding: 0; display: grid; grid-template-rows: 46px minmax(0,1fr); overflow: hidden; background: #080b12; }
.network-header { max-width: 1500px; margin: 0 auto 18px; display: flex; align-items: flex-end; justify-content: space-between; gap: 24px; }
.back-link { display: inline-flex; align-items: center; gap: 6px; margin-bottom: 18px; color: #57706a; font-size: 12px; text-decoration: none; }.header-copy p,.section-title p,.timeline-heading p,.queue-heading p { margin: 0 0 5px; color: #17866f; font-size: 10px; font-weight: 800; }.header-copy h1 { margin: 0; font-size: 34px; line-height: 1; }.header-copy > span { display: block; margin-top: 9px; color: #63736f; font-size: 13px; }
.header-metrics { display: flex; border: 1px solid #ccd8d4; background: #fff; }.header-metrics div { min-width: 92px; padding: 11px 14px; border-left: 1px solid #dce4e1; }.header-metrics div:first-child { border-left: 0; }.header-metrics strong,.header-metrics span { display: block; }.header-metrics strong { font-size: 21px; }.header-metrics span { color: #71817c; font-size: 10px; }
.view-tabs { max-width: 1500px; margin: 0 auto; display: flex; gap: 4px; border-bottom: 1px solid #ccd7d3; }.view-tabs button { position: relative; min-height: 45px; padding: 0 16px; display: inline-flex; align-items: center; gap: 7px; border: 0; border-bottom: 2px solid transparent; background: transparent; color: #63736f; font: inherit; font-size: 13px; cursor: pointer; }.view-tabs button.active { color: #14201d; border-color: #14997d; font-weight: 800; }.view-tabs button span { min-width: 17px; height: 17px; display: grid; place-items: center; border-radius: 50%; background: #e34f64; color: #fff; font-size: 9px; }
.graph-mode .view-tabs { width: 100%; max-width: none; margin: 0; padding: 0 18px; box-sizing: border-box; background: #f8faf9; }
.graph-workspace { position: relative; width: 100%; max-width: none; height: 100%; min-height: 0; margin: 0; display: grid; grid-template-columns: minmax(0,1fr) 0; grid-template-rows: 55px minmax(0,1fr); background: #0b0e0e; overflow: hidden; }
.graph-workspace.has-selection { grid-template-columns: minmax(0,1fr) minmax(280px,20vw); }
.graph-toolbar { grid-column: 1 / -1; display: flex; align-items: center; gap: 8px; padding: 8px 12px; border-bottom: 1px solid #26312f; background: #101514; overflow: visible; }.search-wrap { position: relative; flex: 1; max-width: 430px; z-index: 8; }.search-control,.select-control { height: 37px; display: flex; align-items: center; gap: 7px; padding: 0 10px; border: 1px solid #303c39; color: #82938e; box-sizing: border-box; }.search-control { width: 100%; }.search-control:focus-within { border-color: #5bd2b3; box-shadow: 0 0 0 2px rgba(91,210,179,.1); }.search-control input,.select-control select { min-width: 0; border: 0; outline: 0; background: transparent; color: #d8e3df; font: inherit; font-size: 12px; }.search-control input { width: 100%; }.select-control select { max-width: 170px; }.select-control option { background: #121817; }.search-results { position: absolute; top: 43px; left: 0; right: 0; max-height: 360px; overflow: auto; border: 1px solid #34423f; background: #111716; box-shadow: 0 18px 44px rgba(0,0,0,.36); }.search-results button { width: 100%; min-height: 52px; padding: 8px 10px; display: grid; grid-template-columns: 8px minmax(0,1fr) auto; align-items: center; gap: 9px; border: 0; border-bottom: 1px solid #202b28; background: transparent; color: #dce7e3; text-align: left; cursor: pointer; }.search-results button:hover,.search-results button.active { background: #1c2926; }.search-results i { width: 7px; height: 7px; border-radius: 50%; }.search-results span { min-width: 0; display: grid; gap: 3px; }.search-results strong,.search-results small { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }.search-results strong { font-size: 11px; }.search-results small { color: #7f928c; font-size: 9px; }.search-results em { color: #769089; font-size: 9px; font-style: normal; white-space: nowrap; }.search-empty { padding: 16px; color: #788984; font-size: 11px; text-align: center; }.icon-command { width: 37px; height: 37px; flex: 0 0 auto; border: 1px solid #303c39; background: #141a19; color: #a7b7b2; display: grid; place-items: center; cursor: pointer; }.icon-command.light { border-color: #ccd8d4; background: #fff; color: #435751; }
.graph-stage { position: relative; min-width: 0; overflow: hidden; }.graph-loading { position: absolute; inset: 0; z-index: 7; display: flex; align-items: center; justify-content: center; gap: 9px; background: #080b12; color: #aab5c8; font-size: 12px; }.graph-legend { position: absolute; left: 14px; bottom: 13px; max-width: 72%; display: flex; flex-wrap: wrap; gap: 8px 12px; color: #85958f; font-size: 9px; }.graph-legend i { display: inline-block; width: 6px; height: 6px; margin-right: 5px; border-radius: 50%; }.source-mark { position: absolute; z-index: 6; top: 12px; left: 14px; display: flex; align-items: center; gap: 5px; color: #5bd2b3; font-size: 9px; pointer-events: none; }
.node-panel { display: none; position: relative; min-width: 0; padding: 22px 20px; border-left: 1px solid #26312f; background: #101514; color: #cbd8d4; overflow: auto; }.has-selection .node-panel { display: block; }.close-panel { position: absolute; top: 12px; right: 12px; border: 0; background: transparent; color: #82908c; cursor: pointer; }.node-type { font-size: 10px; font-weight: 800; }.node-panel h2 { margin: 8px 30px 12px 0; color: #f0f5f3; font-size: 18px; line-height: 1.25; overflow-wrap: anywhere; }.node-panel p { color: #91a09b; font-size: 11px; line-height: 1.6; }.node-panel dl { display: grid; grid-template-columns: 72px minmax(0,1fr); gap: 8px; margin: 18px 0; font-size: 10px; }.node-panel dt { color: #697974; }.node-panel dd { margin: 0; color: #c2ceca; overflow-wrap: anywhere; }.node-panel dd.verified { color: #64d8b5; }.node-panel dd.pending { color: #ff9ca8; }.primary-command,.secondary-command { width: 100%; min-height: 39px; margin-top: 8px; display: flex; align-items: center; justify-content: center; gap: 7px; border: 0; background: #dff8ef; color: #0d4f40; font: inherit; font-size: 11px; font-weight: 800; cursor: pointer; }.secondary-command { border: 1px solid #3b4a47; background: transparent; color: #bdcbc7; }.panel-placeholder { height: 100%; display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 9px; color: #62706c; font-size: 11px; text-align: center; }
.related-nodes { margin: 0 0 14px; padding-top: 14px; border-top: 1px solid #26312f; }.related-nodes > div { display: flex; align-items: center; justify-content: space-between; margin-bottom: 8px; }.related-nodes > div strong { color: #dce7e3; font-size: 11px; }.related-nodes > div span { color: #67cdb1; font-size: 10px; }.related-nodes button { width: 100%; min-height: 42px; display: grid; grid-template-columns: 7px minmax(0,1fr); gap: 9px; align-items: center; padding: 7px 8px; border: 0; border-bottom: 1px solid #202a28; background: transparent; color: inherit; text-align: left; cursor: pointer; }.related-nodes button:hover { background: #17201e; }.related-nodes button i { width: 7px; height: 7px; border-radius: 50%; }.related-nodes button span { min-width: 0; display: grid; gap: 2px; }.related-nodes button b,.related-nodes button small { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }.related-nodes button b { color: #cbd8d4; font-size: 10px; }.related-nodes button small { color: #697974; font-size: 9px; }.related-nodes > p { margin: 8px 0 0; color: #697974; font-size: 9px; }
.related-nodes button { align-items: start; padding-block: 9px; }
.related-nodes button i { margin-top: 5px; }
.related-nodes button b,.related-nodes button small { overflow: visible; text-overflow: clip; white-space: normal; overflow-wrap: anywhere; line-height: 1.45; }

.timeline-view,.feedback-view { max-width: 1120px; margin: 28px auto 0; }.timeline-heading,.queue-heading { display: flex; align-items: center; justify-content: space-between; }.timeline-heading h2,.queue-heading h2,.section-title h2 { margin: 0; font-size: 22px; }.timeline-list { margin: 26px 0 0; padding: 0; list-style: none; }.timeline-list li { position: relative; display: grid; grid-template-columns: 42px 24px minmax(0,1fr); min-height: 130px; }.timeline-index { width: 34px; height: 34px; display: grid; place-items: center; border: 1px solid #b8c9c4; background: #fff; color: #2c5e53; font-size: 11px; }.timeline-line { position: relative; }.timeline-line::before { content: ''; position: absolute; top: 0; bottom: 0; left: 10px; width: 1px; background: #bccbc7; }.timeline-line::after { content: ''; position: absolute; top: 12px; left: 6px; width: 9px; height: 9px; border-radius: 50%; background: #1ba486; box-shadow: 0 0 0 4px #d5eee7; }.timeline-list article { margin-bottom: 18px; padding: 14px 16px; border-left: 3px solid #2ca68b; background: #fff; }.timeline-list article > div { display: flex; justify-content: space-between; color: #16856e; font-size: 10px; }.timeline-list time { color: #84928e; }.timeline-list h3 { margin: 7px 0 4px; font-size: 15px; }.timeline-list p { margin: 0; color: #677671; font-size: 11px; }.timeline-list em,.candidate-top span { display: inline-flex; margin-top: 10px; padding: 4px 7px; background: #edf2f0; color: #63716d; font-style: normal; font-size: 9px; }.timeline-list em.approved,.timeline-list em.complete,.timeline-list em.completed,.candidate-top span.approved { background: #dff5ec; color: #08755d; }.timeline-list em.pending,.candidate-top span.pending { background: #fff0d5; color: #9b6100; }.timeline-list em.rejected,.candidate-top span.rejected { background: #ffe3e6; color: #a32e40; }
.growth-intro { max-width: 820px; margin: 12px 0 20px; color: #5d706a; font-size: 13px; line-height: 1.7; }.growth-pipeline { display: grid; grid-template-columns: repeat(5,minmax(0,1fr)); gap: 8px; }.growth-pipeline article { position: relative; min-height: 142px; padding: 15px 13px; border: 1px solid #d8e2df; background: #fff; color: #778782; }.growth-pipeline article::after { content: ''; position: absolute; top: 50%; right: -9px; z-index: 2; width: 9px; height: 1px; background: #9eb2ac; }.growth-pipeline article:last-child::after { display: none; }.growth-pipeline article.active { border-color: #9dd6c6; background: #f3fbf8; color: #14826a; }.growth-pipeline article>span { font-size: 9px; font-weight: 800; }.growth-pipeline article>svg { display: block; margin: 13px 0 10px; }.growth-pipeline article>div { display: grid; gap: 4px; }.growth-pipeline strong { color: #21332e; font-size: 12px; }.growth-pipeline small { min-height: 30px; color: #71817c; font-size: 9px; line-height: 1.5; }.growth-pipeline b { display: block; margin-top: 11px; color: #173e35; font-size: 23px; }.audit-rule { margin: 14px 0 26px; padding: 14px 16px; display: flex; align-items: center; gap: 11px; border: 1px solid #badfd4; background: #eaf8f3; color: #14705d; }.audit-rule div { display: grid; gap: 3px; }.audit-rule strong { font-size: 12px; }.audit-rule span { color: #55736b; font-size: 10px; }.collection-required { min-height: 300px; margin-top: 22px; padding: 28px; display: flex; flex-direction: column; align-items: center; justify-content: center; border: 1px dashed #a8c9bf; background: #f4faf8; text-align: center; }.collection-required>svg { color: #198269; }.collection-required strong { margin-top: 12px; font-size: 16px; }.collection-required p { max-width: 390px; margin: 8px 0 18px; color: #63766f; font-size: 11px; line-height: 1.7; }.collection-required .submit-command { width: auto; padding: 0 18px; }
.feedback-view { max-width: 1320px; display: grid; grid-template-columns: minmax(0,1fr) minmax(360px,.9fr); gap: 22px; }.feedback-compose,.feedback-queue { padding: 24px; background: #fff; border: 1px solid #d6dfdc; }.section-title { display: flex; align-items: center; gap: 12px; }.section-title > span { width: 42px; height: 42px; display: grid; place-items: center; background: #dff5ed; color: #148069; }.feedback-compose form { display: grid; gap: 13px; margin-top: 22px; }.feedback-compose label { display: grid; gap: 6px; color: #667670; font-size: 10px; }.feedback-compose input,.feedback-compose select,.feedback-compose textarea { width: 100%; min-width: 0; box-sizing: border-box; border: 1px solid #cbd7d3; background: #f9fbfa; padding: 10px 11px; color: #1e2b27; font: inherit; font-size: 12px; resize: vertical; }.form-row { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }.submit-command { min-height: 42px; border: 0; background: #173e35; color: #fff; display: flex; align-items: center; justify-content: center; gap: 7px; font: inherit; font-size: 12px; font-weight: 800; cursor: pointer; }.candidate-row { padding: 15px 0; border-bottom: 1px solid #e1e7e5; }.candidate-top { display: flex; justify-content: space-between; align-items: center; }.candidate-top span { margin: 0; }.candidate-top time { color: #87938f; font-size: 9px; }.candidate-row h3 { margin: 9px 0 5px; font-size: 14px; }.candidate-row p { max-height: 54px; overflow: hidden; margin: 0; color: #65736f; font-size: 11px; line-height: 1.55; }.candidate-row small { display: flex; align-items: center; gap: 5px; margin-top: 8px; color: #778681; }.review-actions { display: flex; justify-content: flex-end; gap: 7px; margin-top: 11px; }.review-actions button { min-height: 32px; padding: 0 11px; display: flex; align-items: center; gap: 5px; border: 1px solid #d4ddda; background: #fff; font: inherit; font-size: 10px; cursor: pointer; }.review-actions .approve { border-color: #1a8a70; background: #1a8a70; color: #fff; }.review-actions .reject { color: #a63145; }.review-note { margin-top: 9px; color: #65736f; font-size: 10px; }
.empty-view { min-height: 320px; display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 8px; color: #7e8d88; text-align: center; }.empty-view strong { color: #34443f; }.empty-view span { font-size: 11px; }.empty-view.compact { min-height: 220px; }.notice { position: fixed; z-index: 20; right: 28px; bottom: 28px; max-width: 420px; display: flex; align-items: center; gap: 8px; padding: 12px 14px; border: 1px solid #208f75; background: #effbf7; color: #12654f; font-size: 12px; box-shadow: 0 14px 32px rgba(20,48,40,.16); }.notice.error { border-color: #c34c60; background: #fff0f2; color: #9c2b3f; }.spin { animation: spin .85s linear infinite; } @keyframes spin { to { transform: rotate(360deg); } }
.growth-workspace { min-width: 0; min-height: 0; overflow: hidden; background: #080b12; color: #dbe7e3; }
.growth-scroll { width: 100%; height: 100%; padding: 24px 32px 56px; box-sizing: border-box; overflow-y: auto; scrollbar-color: #33433f #0b100f; }
.growth-workspace .timeline-view { max-width: 1500px; margin: 0 auto; }
.growth-workspace .timeline-heading h2,.growth-workspace .queue-heading h2,.growth-workspace .section-title h2 { color: #edf6f3; }
.growth-workspace .growth-intro { color: #91a49e; }
.growth-workspace .growth-pipeline article { border-color: #263632; background: #101715; color: #70847e; }
.growth-workspace .growth-pipeline article.active { border-color: #287c68; background: #10231e; color: #5bd2b3; }
.growth-workspace .growth-pipeline strong,.growth-workspace .growth-pipeline b { color: #e3efeb; }
.growth-workspace .growth-pipeline small { color: #81948e; }
.growth-workspace .growth-pipeline article::after { background: #36564e; }
.growth-workspace .audit-rule { border-color: #24594c; background: #10241f; color: #5bd2b3; }
.growth-workspace .audit-rule span { color: #88a29a; }
.growth-workspace .timeline-list article,.growth-workspace .feedback-compose,.growth-workspace .feedback-queue { border-color: #263632; background: #101715; }
.growth-workspace .timeline-index { border-color: #345249; background: #13201d; color: #66d9ba; }
.growth-workspace .timeline-line::before { background: #30453f; }
.growth-workspace .timeline-list h3,.growth-workspace .candidate-row h3 { color: #e3eeea; }
.growth-workspace .timeline-list p,.growth-workspace .candidate-row p,.growth-workspace .candidate-row small { color: #849790; }
.growth-workspace .timeline-list time,.growth-workspace .candidate-top time { color: #687a74; }
.growth-lower { display: grid; grid-template-columns: minmax(0,1.25fr) minmax(420px,.75fr); gap: 22px; align-items: start; }
.growth-trace { min-width: 0; border: 1px solid #263632; background: #101715; }
.growth-subhead { min-height: 68px; padding: 13px 16px; display: flex; align-items: center; justify-content: space-between; border-bottom: 1px solid #263632; }
.growth-subhead p { margin: 0 0 4px; color: #5bd2b3; font-size: 9px; font-weight: 800; }
.growth-subhead h2 { margin: 0; font-size: 17px; }
.growth-subhead>span { color: #7f948d; font-size: 10px; }
.growth-trace .timeline-list { max-height: 560px; margin: 0; padding: 16px; overflow-y: auto; }
.growth-trace .empty-view { min-height: 330px; }
.growth-workspace .feedback-view { max-width: none; margin: 0; padding: 0; display: grid; grid-template-columns: 1fr; gap: 14px; border: 0; }
.growth-workspace .section-title>span { background: #17372f; color: #5bd2b3; }
.growth-workspace .feedback-compose label { color: #91a39d; }
.growth-workspace .feedback-compose input,.growth-workspace .feedback-compose select,.growth-workspace .feedback-compose textarea { border-color: #31423d; background: #0c1211; color: #dce7e3; }
.growth-workspace .collection-required { border-color: #31584d; background: #0d1916; }
.growth-workspace .collection-required strong { color: #dce9e5; }
.growth-workspace .collection-required p { color: #81948e; }
.growth-workspace .empty-view { border-color: #2d3b37; background: #0d1312; color: #81928d; }
.growth-workspace .empty-view strong { color: #d7e2de; }
.growth-workspace .candidate-row { border-color: #26332f; }
.growth-workspace .icon-command.light { border-color: #33443f; background: #121a18; color: #9eb0aa; }
.growth-workspace .review-actions button { border-color: #35453f; background: #111917; color: #aebcb7; }
.growth-workspace .review-actions .approve { border-color: #1a8a70; background: #1a8a70; color: #fff; }
.growth-workspace .review-actions .reject { color: #ff8797; }
.network-page.graph-mode .growth-workspace :is(.timeline-heading h2,.queue-heading h2,.section-title h2,.growth-pipeline strong,.growth-pipeline b,.timeline-list h3,.candidate-row h3,.collection-required strong,.empty-view strong) { color: #edf6f3 !important; }
.network-page.graph-mode .growth-workspace :is(.growth-intro,.timeline-list p,.candidate-row p,.candidate-row small,.collection-required p,.empty-view,.feedback-compose label) { color: #9aada7 !important; }
.network-page.graph-mode .growth-workspace .growth-pipeline small { color: #879b95 !important; }
.network-page.graph-mode .growth-workspace .audit-rule strong { color: #75e0c2 !important; }
.network-page.graph-mode .growth-workspace .audit-rule span { color: #9bb0aa !important; }
.network-page.graph-mode .growth-workspace .timeline-list article>div { color: #5bd2b3 !important; }
.memory-view { max-width: 1600px; margin: 0 auto; }
.memory-rule { margin: 14px 0 22px; padding: 14px 16px; display: flex; align-items: center; gap: 11px; border: 1px solid #24594c; background: #10241f; color: #5bd2b3; }
.memory-rule div { display: grid; gap: 3px; }.memory-rule strong { color: #75e0c2; font-size: 12px; }.memory-rule span { color: #9bb0aa; font-size: 10px; line-height: 1.6; }
.memory-layout { display: grid; grid-template-columns: minmax(0,1fr) 390px; gap: 18px; align-items: start; }
.memory-feed,.memory-insights { min-width: 0; border: 1px solid #263632; background: #101715; }
.memory-toolbar { min-height: 54px; padding: 8px 14px; display: flex; gap: 8px; border-bottom: 1px solid #263632; background: #0d1312; }
.memory-toolbar label { height: 36px; flex: 1; display: flex; align-items: center; gap: 8px; padding: 0 10px; border: 1px solid #31423d; color: #789087; }
.memory-toolbar input,.memory-toolbar select { min-width: 0; border: 0; outline: 0; background: transparent; color: #dce7e3; font: inherit; font-size: 11px; }
.memory-toolbar input { width: 100%; }.memory-toolbar select { width: 160px; padding: 0 9px; border: 1px solid #31423d; background: #0d1312; }.memory-toolbar option { background: #111917; }
.memory-list { max-height: 660px; overflow-y: auto; scrollbar-color: #344b44 #0c1211; }
.memory-card { padding: 18px; border-bottom: 1px solid #26332f; }.memory-card:last-child { border-bottom: 0; }
.memory-meta { display: flex; align-items: center; justify-content: space-between; }.memory-meta span { color: #5bd2b3; font-size: 9px; font-weight: 800; }.memory-meta time { color: #6f827b; font-size: 9px; }
.dialogue-pair { margin-top: 12px; display: grid; gap: 7px; }.dialogue-pair>div { display: grid; grid-template-columns: 20px minmax(0,1fr); gap: 6px; align-items: start; color: #7f938c; }.dialogue-pair>div:last-child { color: #5bd2b3; }.dialogue-pair p { margin: 0; color: #a8b8b3; font-size: 11px; line-height: 1.65; }
.core-memory { margin-top: 13px; padding: 12px; display: flex; align-items: flex-start; gap: 10px; border-left: 3px solid #34c6a2; background: #13231f; color: #61dab9; }.core-memory div { display: grid; gap: 4px; }.core-memory small { color: #6f9e91; font-size: 8px; }.core-memory strong { color: #edf6f3; font-size: 12px; line-height: 1.6; }
.memory-tags { margin-top: 10px; display: flex; flex-wrap: wrap; gap: 5px; }.memory-tags span { padding: 4px 7px; border: 1px solid #31564c; background: #10201c; color: #67cdb2; font-size: 9px; }
.memory-signals { margin-top: 9px; display: grid; gap: 5px; }.memory-signals span { display: flex; gap: 7px; color: #91a49e; font-size: 9px; line-height: 1.5; }.memory-signals b { flex: 0 0 auto; color: #e0ece8; }
.memory-insights { position: sticky; top: 0; }.memory-metrics { display: grid; grid-template-columns: 1fr 1fr; }.memory-metrics article { min-height: 92px; padding: 14px; display: grid; grid-template-columns: 24px 1fr; grid-template-rows: 1fr auto; align-items: center; border-right: 1px solid #263632; border-bottom: 1px solid #263632; color: #5bd2b3; }.memory-metrics article:nth-child(2n) { border-right: 0; }.memory-metrics strong { color: #edf6f3; font-size: 23px; }.memory-metrics span { grid-column: 1/-1; color: #849790; font-size: 9px; }
.topic-cloud,.memory-return { padding: 17px; border-bottom: 1px solid #263632; }.topic-cloud h3,.memory-return h3 { margin: 0 0 12px; color: #edf6f3; font-size: 12px; }.topic-cloud>div { display: flex; flex-wrap: wrap; gap: 6px; }.topic-cloud button { min-height: 29px; padding: 0 8px; display: inline-flex; align-items: center; gap: 7px; border: 1px solid #30443e; background: #111b18; color: #a9bab4; font: inherit; font-size: 9px; cursor: pointer; }.topic-cloud button:hover { border-color: #4fc5a6; color: #67d5b7; }.topic-cloud button b { color: #5bd2b3; }.topic-cloud>p { color: #7d9089; font-size: 10px; }
.memory-return { border-bottom: 0; }.memory-return ol { margin: 0; padding: 0; display: grid; gap: 13px; list-style: none; }.memory-return li { display: grid; grid-template-columns: 26px 1fr; gap: 9px; }.memory-return li>span { width: 24px; height: 24px; display: grid; place-items: center; border: 1px solid #31584d; color: #5bd2b3; font-size: 9px; }.memory-return strong { color: #dce8e4; font-size: 10px; }.memory-return p { margin: 3px 0 0; color: #7f918b; font-size: 9px; line-height: 1.55; }
@media (max-width: 1100px) { .growth-lower { grid-template-columns: 1fr; } }
@media (max-width: 1180px) { .memory-layout { grid-template-columns: 1fr; }.memory-insights { position: static; }.memory-list { max-height: 520px; } }
@media (max-width: 980px) { .graph-workspace.has-selection { grid-template-columns: minmax(0,1fr) 270px; }.feedback-view { grid-template-columns: 1fr; }.growth-pipeline { grid-template-columns: repeat(2,minmax(0,1fr)); }.growth-pipeline article::after { display: none; }.header-metrics div { min-width: 72px; }.network-page:not(.graph-mode) { padding-inline: 20px; } }
@media (max-width: 720px) { .network-page:not(.graph-mode) { padding: 20px 12px 110px; }.network-page.graph-mode { height: 100vh; padding-bottom: 88px; grid-template-rows: 45px minmax(0,1fr); }.network-header { align-items: stretch; flex-direction: column; }.header-copy h1 { font-size: 28px; }.header-metrics { align-self: stretch; }.header-metrics div { flex: 1; min-width: 0; }.view-tabs { overflow-x: auto; }.view-tabs button { white-space: nowrap; }.graph-mode .view-tabs { padding: 0 8px; }.graph-workspace,.graph-workspace.has-selection { height: 100%; min-height: 0; display: grid; grid-template-columns: minmax(0,1fr); grid-template-rows: auto minmax(0,1fr); }.graph-toolbar { min-height: 96px; height: auto; flex-wrap: wrap; }.search-wrap { max-width: none; flex-basis: 100%; }.search-results { max-height: 270px; }.select-control { flex: 1; }.graph-stage { height: 100%; }.node-panel,.has-selection .node-panel { position: absolute; z-index: 9; left: 8px; right: 8px; bottom: 8px; display: block; max-height: 42%; border: 1px solid #30403c; transform: translateY(calc(100% + 16px)); transition: transform .2s ease; }.node-panel.open { transform: none; }.graph-legend { display: none; }.growth-scroll { padding: 16px 10px 40px; }.growth-pipeline { grid-template-columns: 1fr; }.feedback-compose,.feedback-queue { padding: 18px 14px; }.form-row { grid-template-columns: 1fr; }.memory-toolbar { align-items: stretch; flex-direction: column; }.memory-toolbar label,.memory-toolbar select { width: 100%; box-sizing: border-box; }.memory-list { max-height: none; }.memory-card { padding: 14px 12px; }.memory-metrics article { min-height: 80px; } }
</style>
