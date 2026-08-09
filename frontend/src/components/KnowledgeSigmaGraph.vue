<!-- Graph rendering architecture adapted from nashsu/llm_wiki (GPL-3.0). -->
<template>
  <div class="sigma-shell">
    <div ref="container" class="sigma-container" aria-label="知识网络 WebGL 画布"></div>

    <div v-if="building" class="graph-build-state">
      <LoaderCircle class="spin" :size="16" />
      <span>正在构建图谱</span>
    </div>
    <div v-else-if="layoutRunning" class="graph-layout-state">
      <LoaderCircle class="spin" :size="14" />
      <span>后台优化布局</span>
    </div>

    <div class="sigma-controls" aria-label="图谱缩放控制">
      <button type="button" title="放大" @click="zoomIn"><ZoomIn :size="17" /></button>
      <button type="button" title="缩小" @click="zoomOut"><ZoomOut :size="17" /></button>
      <button type="button" title="适应视图" @click="fit"><Maximize :size="17" /></button>
    </div>
  </div>
</template>

<script setup>
import { nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import Graph from 'graphology'
import Sigma from 'sigma'
import { LoaderCircle, Maximize, ZoomIn, ZoomOut } from 'lucide-vue-next'

const props = defineProps({
  nodes: { type: Array, default: () => [] },
  edges: { type: Array, default: () => [] },
  typeFilter: { type: String, default: '' },
})
const emit = defineEmits(['ready', 'node-select', 'layout-state', 'error'])

const container = ref(null)
const building = ref(false)
const layoutRunning = ref(false)
const positionCache = new Map()
let graph = null
let renderer = null
let layoutWorker = null
let resizeObserver = null
let buildToken = 0
let edgeDetail = { key: 'overview', fraction: 0.04, alpha: 0.075 }
let hoveredNodeId = ''
let focusedNodeId = ''

const NODE_COLORS = {
  root: '#f2c14e', domain: '#36c2a4', topic: '#58a6ff', collection: '#e879a9',
  document: '#a78bfa', citation: '#f59e68', agent: '#66d9ef', artifact: '#8dd35f', feedback: '#ff7a7a',
}

function hashNumber(value, seed = 2166136261) {
  let hash = seed >>> 0
  const text = String(value || '')
  for (let index = 0; index < text.length; index += 1) {
    hash ^= text.charCodeAt(index)
    hash = Math.imul(hash, 16777619)
  }
  return hash >>> 0
}

function nodeDomainKey(node) {
  if (node.domainKey) return String(node.domainKey)
  const id = String(node.id || '')
  if (id.startsWith('course-domain:')) return id.split(':')[1] || ''
  if (id.startsWith('course-topic:')) return id.split(':')[1] || ''
  return ''
}

function buildDomainLayout(nodes, total) {
  const keys = [...new Set(nodes.map(nodeDomainKey).filter(Boolean))].sort((left, right) => left.localeCompare(right))
  const clusterRadius = Math.max(170, Math.sqrt(total / Math.max(1, keys.length)) * 7)
  const ringRadius = clusterRadius * 1.9
  const goldenAngle = Math.PI * (3 - Math.sqrt(5))
  const centers = new Map(keys.map((key, index) => {
    const angleJitter = (hashNumber(key, 3266489917) / 0xffffffff - 0.5) * 0.34
    const radiusJitter = 0.78 + (hashNumber(key, 668265263) / 0xffffffff) * 0.28
    const angle = -Math.PI / 2 + index * goldenAngle + angleJitter
    const radius = ringRadius * radiusJitter
    const localJitter = clusterRadius * 0.11
    return [key, {
      x: Math.cos(angle) * radius + (hashNumber(key, 374761393) / 0xffffffff - 0.5) * localJitter,
      y: Math.sin(angle) * radius * 0.76 + (hashNumber(key, 1274126177) / 0xffffffff - 0.5) * localJitter,
    }]
  }))
  return { centers, clusterRadius, ringRadius }
}

function rotateOffset(x, y, rotation) {
  return {
    x: x * Math.cos(rotation) - y * Math.sin(rotation),
    y: x * Math.sin(rotation) + y * Math.cos(rotation),
  }
}

function topicAnchor(domainKey, topic, clusterRadius) {
  if (!topic) return { x: 0, y: 0 }
  const key = `${domainKey}:${topic}`
  const angle = (hashNumber(key, 374761393) / 0xffffffff) * Math.PI * 2
  const distance = clusterRadius * (0.17 + (hashNumber(key, 668265263) / 0xffffffff) * 0.25)
  return { x: Math.cos(angle) * distance, y: Math.sin(angle) * distance }
}

function organicOffset(nodeId, shapeKey, radius, innerRadius = 0) {
  const angle = (hashNumber(nodeId, 2166136261) / 0xffffffff) * Math.PI * 2
  const radialUnit = hashNumber(nodeId, 2246822519) / 0xffffffff
  const phaseA = (hashNumber(shapeKey, 3266489917) / 0xffffffff) * Math.PI * 2
  const phaseB = (hashNumber(shapeKey, 668265263) / 0xffffffff) * Math.PI * 2
  const boundary = 0.79 + Math.sin(angle * 3 + phaseA) * 0.16 + Math.sin(angle * 5 + phaseB) * 0.09
  const distance = innerRadius + Math.sqrt(radialUnit) * Math.max(0, radius - innerRadius) * boundary
  const aspectX = 0.68 + (hashNumber(shapeKey, 374761393) / 0xffffffff) * 0.64
  const aspectY = 1.2 - (aspectX - 0.68) * 0.42
  const rotation = (hashNumber(shapeKey, 1274126177) / 0xffffffff) * Math.PI
  return rotateOffset(Math.cos(angle) * distance * aspectX, Math.sin(angle) * distance * aspectY, rotation)
}

function initialPosition(node, index, total, domainLayout) {
  const cached = positionCache.get(node.id)
  if (cached) return cached
  if (node.type === 'root') return { x: 0, y: 0 }
  const domainCenter = domainLayout.centers.get(nodeDomainKey(node))
  if (domainCenter) {
    if (node.type === 'domain') return domainCenter
    const domainKey = nodeDomainKey(node)
    const topics = Array.isArray(node.topics) ? node.topics.filter(Boolean) : []
    const topic = node.type === 'topic'
      ? String(node.name || '')
      : topics.length
        ? String(topics[hashNumber(node.id, 2654435761) % topics.length])
        : ''
    const anchor = topicAnchor(domainKey, topic, domainLayout.clusterRadius)
    const shapeKey = `${domainKey}:${topic || 'general'}`
    const offset = node.type === 'topic'
      ? organicOffset(node.id, shapeKey, Math.min(22, domainLayout.clusterRadius * 0.08), 5)
      : organicOffset(
          node.id,
          shapeKey,
          domainLayout.clusterRadius * (topic ? 0.58 : 0.94),
          topic ? 18 : 52,
        )
    return {
      x: domainCenter.x + anchor.x + offset.x,
      y: domainCenter.y + anchor.y + offset.y,
    }
  }
  const angle = (hashNumber(node.id) / 0xffffffff) * Math.PI * 2
  const spread = Math.max(80, domainLayout.ringRadius * 1.45)
  const distance = (0.82 + (index % 17) / 70) * spread
  const jitter = (hashNumber(node.id, 2246822519) / 0xffffffff - 0.5) * 18
  return { x: Math.cos(angle) * (distance + jitter), y: Math.sin(angle) * (distance - jitter) }
}

function nodeSize(linkCount, maxLinks, total) {
  const density = total <= 150 ? 1 : Math.max(0.35, Math.sqrt(150 / total))
  const ratio = maxLinks ? linkCount / maxLinks : 0
  return Math.max(1.4, (4 + Math.sqrt(ratio) * 14) * density)
}

function edgeDetailForRatio(ratio) {
  if (ratio >= 0.78) return { key: 'overview', fraction: 0.04, alpha: 0.075 }
  if (ratio >= 0.34) return { key: 'wide', fraction: 0.08, alpha: 0.09 }
  if (ratio >= 0.16) return { key: 'medium', fraction: 0.14, alpha: 0.11 }
  return { key: 'detail', fraction: 0.24, alpha: 0.14 }
}

function reduceEdge(_edgeId, attrs) {
  if (attrs.hidden) return { hidden: true }
  const inspectedNodeId = hoveredNodeId || focusedNodeId
  const inspectingNode = focusedNodeId || hoveredNodeId
  const isRelated = Boolean(inspectedNodeId && (
    attrs.sourceNode === inspectedNodeId || attrs.targetNode === inspectedNodeId
  ))
  if (isRelated) {
    const degree = attrs.sourceNode === inspectedNodeId ? attrs.sourceDegree : attrs.targetDegree
    const highlightLimit = hoveredNodeId ? 16 : 32
    if (degree > highlightLimit && attrs.lod > highlightLimit / degree) return { hidden: true }
    return { hidden: false, color: 'rgba(91, 210, 179, 0.68)', size: 0.82, zIndex: 2 }
  }
  if (attrs.backbone) {
    return {
      hidden: false,
      color: inspectingNode ? 'rgba(66, 184, 194, 0.42)' : 'rgba(66, 184, 194, 0.9)',
      size: inspectingNode ? 0.8 : 1.5,
      zIndex: 1,
    }
  }
  if (attrs.bridge) {
    return {
      hidden: false,
      color: inspectingNode ? 'rgba(125, 116, 214, 0.18)' : 'rgba(125, 116, 214, 0.42)',
      size: inspectingNode ? 0.34 : 0.58,
      zIndex: 1,
    }
  }

  const visibleFraction = inspectingNode ? 0 : edgeDetail.fraction
  if (attrs.lod > visibleFraction) return { hidden: true }
  return {
    hidden: false,
    color: `rgba(44, 68, 168, ${edgeDetail.alpha})`,
    size: edgeDetail.key === 'detail' ? 0.38 : 0.28,
    zIndex: 0,
  }
}

function reduceNode(nodeId, attrs) {
  const isInspected = nodeId === hoveredNodeId || nodeId === focusedNodeId
  if (!isInspected) return attrs
  return {
    ...attrs,
    forceLabel: true,
    highlighted: true,
    zIndex: 4,
  }
}

function wrapLabel(context, label, maxWidth) {
  const lines = []
  let line = ''
  for (const character of String(label || '')) {
    const candidate = `${line}${character}`
    if (line && context.measureText(candidate).width > maxWidth) {
      lines.push(line)
      line = character
    } else {
      line = candidate
    }
  }
  if (line) lines.push(line)
  return lines.length ? lines : ['']
}

function drawKnowledgeNodeHover(context, data, settings) {
  const label = String(data.label || '')
  if (!label) return
  const fontSize = 13
  const lineHeight = 19
  const paddingX = 9
  const paddingY = 7
  const maxTextWidth = 260

  context.save()
  context.font = `600 ${fontSize}px ${settings.labelFont}`
  const lines = wrapLabel(context, label, maxTextWidth)
  const textWidth = Math.max(...lines.map(line => context.measureText(line).width))
  const width = textWidth + paddingX * 2
  const height = lines.length * lineHeight + paddingY * 2
  let x = data.x + data.size + 8
  if (x + width > context.canvas.width - 8) x = data.x - data.size - width - 8
  let y = data.y - height / 2
  y = Math.max(8, Math.min(context.canvas.height - height - 8, y))

  context.beginPath()
  context.roundRect(x, y, width, height, 5)
  context.fillStyle = 'rgba(13, 19, 29, 0.96)'
  context.fill()
  context.strokeStyle = data.color || '#8b7cf6'
  context.lineWidth = 1
  context.stroke()
  context.fillStyle = '#f4f7ff'
  context.textBaseline = 'middle'
  lines.forEach((line, index) => {
    context.fillText(line, x + paddingX, y + paddingY + lineHeight * (index + 0.5))
  })
  context.restore()
}

function dataKey() {
  let hash = 2166136261
  const update = value => {
    const text = String(value)
    for (let index = 0; index < text.length; index += 1) {
      hash ^= text.charCodeAt(index)
      hash = Math.imul(hash, 16777619)
    }
  }
  props.nodes.forEach(node => update(node.id))
  props.edges.forEach(edge => { update(edge.source); update(edge.target) })
  return `${(hash >>> 0).toString(36)}:${props.nodes.length}:${props.edges.length}`
}

function destroyRenderer() {
  layoutWorker?.terminate()
  layoutWorker = null
  renderer?.kill()
  renderer = null
  graph = null
}

async function rebuild(options = {}) {
  const token = ++buildToken
  building.value = true
  layoutRunning.value = false
  emit('layout-state', false)
  destroyRenderer()
  await nextTick()
  if (token !== buildToken || !container.value || !props.nodes.length) {
    building.value = false
    return
  }

  try {
    const nextGraph = new Graph({ type: 'undirected', multi: false, allowSelfLoops: false })
    const linkCounts = new Map(props.nodes.map(node => [node.id, 0]))
    props.edges.forEach(edge => {
      if (linkCounts.has(edge.source)) linkCounts.set(edge.source, linkCounts.get(edge.source) + 1)
      if (linkCounts.has(edge.target)) linkCounts.set(edge.target, linkCounts.get(edge.target) + 1)
    })
    const maxLinks = Math.max(1, ...linkCounts.values())
    const domainLayout = buildDomainLayout(props.nodes, props.nodes.length)

    props.nodes.forEach((node, index) => {
      const position = initialPosition(node, index, props.nodes.length, domainLayout)
      nextGraph.addNode(node.id, {
        x: position.x,
        y: position.y,
        size: node.type === 'root' ? 11 : node.type === 'domain' ? 8 : nodeSize(linkCounts.get(node.id) || 0, maxLinks, props.nodes.length),
        color: NODE_COLORS[node.type] || '#94a3b8',
        label: node.name || node.source || '未命名节点',
        nodeType: node.type || '',
        forceLabel: node.type === 'root' || node.type === 'domain' || node.type === 'topic',
        zIndex: node.type === 'root' ? 3 : node.type === 'domain' ? 2 : 0,
        hidden: Boolean(props.typeFilter && node.type !== props.typeFilter),
      })
    })

    props.edges.forEach((edge, index) => {
      if (!nextGraph.hasNode(edge.source) || !nextGraph.hasNode(edge.target) || edge.source === edge.target) return
      if (nextGraph.hasEdge(edge.source, edge.target)) return
      const hidden = Boolean(props.typeFilter && (
        nextGraph.getNodeAttribute(edge.source, 'nodeType') !== props.typeFilter
        || nextGraph.getNodeAttribute(edge.target, 'nodeType') !== props.typeFilter
      ))
      nextGraph.addUndirectedEdgeWithKey(`edge-${index}`, edge.source, edge.target, {
        size: 0.28,
        color: 'rgba(44, 68, 168, 0.075)',
        weight: Number(edge.weight || 1),
        sourceNode: edge.source,
        targetNode: edge.target,
        sourceDegree: linkCounts.get(edge.source) || 0,
        targetDegree: linkCounts.get(edge.target) || 0,
        lod: hashNumber(`${edge.source}|${edge.target}`, 3266489917) / 0xffffffff,
        backbone: nextGraph.getNodeAttribute(edge.source, 'nodeType') === 'root'
          || nextGraph.getNodeAttribute(edge.target, 'nodeType') === 'root',
        bridge: edge.relation === 'shared_topic',
        hidden,
      })
    })

    if (token !== buildToken) return
    graph = nextGraph
    renderer = new Sigma(graph, container.value, {
      allowInvalidContainer: false,
      defaultNodeColor: '#a78bfa',
      defaultEdgeColor: 'rgba(44, 68, 168, 0.075)',
      defaultDrawNodeHover: drawKnowledgeNodeHover,
      nodeReducer: reduceNode,
      edgeReducer: reduceEdge,
      hideEdgesOnMove: true,
      hideLabelsOnMove: true,
      labelColor: { color: '#e8ecff' },
      labelFont: 'Inter, Microsoft YaHei, sans-serif',
      labelSize: 12,
      labelWeight: '600',
      labelDensity: props.nodes.length > 2500 ? 0.11 : 0.24,
      labelRenderedSizeThreshold: props.nodes.length > 2500 ? 14 : 8,
      minEdgeThickness: 0.28,
      renderEdgeLabels: false,
      zIndex: true,
    })
    edgeDetail = edgeDetailForRatio(renderer.getCamera().getState().ratio)
    renderer.getCamera().on('updated', ({ ratio }) => {
      const nextDetail = edgeDetailForRatio(ratio)
      if (nextDetail.key === edgeDetail.key) return
      edgeDetail = nextDetail
      renderer?.refresh()
    })
    renderer.on('clickNode', ({ node }) => {
      focusedNodeId = node
      renderer?.refresh()
      emit('node-select', node)
    })
    renderer.on('enterNode', ({ node }) => {
      hoveredNodeId = node
      if (container.value) container.value.style.cursor = 'pointer'
      renderer?.refresh()
    })
    renderer.on('leaveNode', () => {
      hoveredNodeId = ''
      if (container.value) container.value.style.cursor = 'default'
      renderer?.refresh()
    })

    building.value = false
    emit('ready', { nodes: graph.order, edges: graph.size })
    if (graph.order <= 2500 || options.forceLayout) startLayout(Boolean(options.forceLayout))
    else {
      layoutRunning.value = false
      emit('layout-state', false)
    }
  } catch (error) {
    building.value = false
    emit('error', error instanceof Error ? error.message : String(error))
  }
}

function startLayout(force = false) {
  if (!graph || graph.order < 2) return
  if (force) positionCache.clear()
  layoutWorker?.terminate()
  const key = dataKey()
  layoutRunning.value = true
  emit('layout-state', true)
  layoutWorker = new Worker(new URL('../workers/knowledge-graph-layout.worker.js', import.meta.url), { type: 'module' })
  layoutWorker.onmessage = event => {
    if (event.data?.key !== key) return
    if (event.data.type === 'error') {
      layoutRunning.value = false
      emit('layout-state', false)
      emit('error', event.data.message || '图谱布局失败')
      return
    }
    event.data.positions.forEach(({ id, x, y }) => {
      if (!graph?.hasNode(id)) return
      graph.setNodeAttribute(id, 'x', x)
      graph.setNodeAttribute(id, 'y', y)
      positionCache.set(id, { x, y })
    })
    renderer?.refresh()
    renderer?.getCamera().animatedReset({ duration: 500 })
    layoutRunning.value = false
    emit('layout-state', false)
    layoutWorker?.terminate()
    layoutWorker = null
  }
  layoutWorker.onerror = event => {
    layoutRunning.value = false
    emit('layout-state', false)
    emit('error', event.message || '图谱布局 Worker 失败')
  }
  layoutWorker.postMessage({
    key,
    nodes: props.nodes.map(node => {
      const attrs = graph.getNodeAttributes(node.id)
      return { id: node.id, x: attrs.x, y: attrs.y }
    }),
    edges: props.edges.map(edge => ({ source: edge.source, target: edge.target, weight: Number(edge.weight || 1) })),
    iterations: props.nodes.length > 2500 ? 28 : props.nodes.length > 600 ? 65 : 120,
    scalingRatio: props.nodes.length > 400 ? 3 : 2,
  })
}

function applyFilter() {
  if (!graph) return
  graph.forEachNode((id, attrs) => graph.setNodeAttribute(id, 'hidden', Boolean(props.typeFilter && attrs.nodeType !== props.typeFilter)))
  graph.forEachEdge((edge, _attrs, source, target) => {
    graph.setEdgeAttribute(edge, 'hidden', graph.getNodeAttribute(source, 'hidden') || graph.getNodeAttribute(target, 'hidden'))
  })
  renderer?.refresh()
}

function focusNode(nodeId) {
  if (!renderer || !graph?.hasNode(nodeId)) return
  focusedNodeId = nodeId
  graph.forEachNode(id => graph.setNodeAttribute(id, 'highlighted', id === nodeId))
  renderer.refresh()
  const display = renderer.getNodeDisplayData(nodeId)
  if (display) renderer.getCamera().animate({ x: display.x, y: display.y, ratio: Math.min(renderer.getCamera().getState().ratio, 0.12) }, { duration: 450 })
}

function clearFocus() {
  focusedNodeId = ''
  graph?.forEachNode(id => graph.setNodeAttribute(id, 'highlighted', false))
  renderer?.refresh()
}

function fit() { renderer?.getCamera().animatedReset({ duration: 350 }) }
function zoomIn() { renderer?.getCamera().animatedZoom({ duration: 180 }) }
function zoomOut() { renderer?.getCamera().animatedUnzoom({ duration: 180 }) }
function refreshLayout() { startLayout(true) }

watch([() => props.nodes, () => props.edges], () => rebuild())
watch(() => props.typeFilter, applyFilter)

onMounted(() => rebuild())

watch(container, value => {
  resizeObserver?.disconnect()
  if (!value) return
  resizeObserver = new ResizeObserver(() => renderer?.refresh())
  resizeObserver.observe(value)
})

onBeforeUnmount(() => {
  buildToken += 1
  resizeObserver?.disconnect()
  destroyRenderer()
})

defineExpose({ fit, focusNode, clearFocus, rebuild, refreshLayout })
</script>

<style scoped>
.sigma-shell,.sigma-container { position: absolute; inset: 0; }
.sigma-shell { overflow: hidden; background: #080b12; }
.sigma-container { background: radial-gradient(circle at 48% 45%, #111827 0, #080b12 62%); }
.graph-build-state,.graph-layout-state { position: absolute; z-index: 4; display: inline-flex; align-items: center; gap: 7px; border: 1px solid #2b3648; background: rgba(10,14,23,.86); color: #aab5c8; font-size: 11px; backdrop-filter: blur(8px); }
.graph-build-state { inset: 0; justify-content: center; border: 0; }
.graph-layout-state { left: 14px; bottom: 14px; padding: 8px 10px; }
.sigma-controls { position: absolute; z-index: 5; top: 14px; right: 14px; display: grid; gap: 5px; }
.sigma-controls button { width: 34px; height: 34px; display: grid; place-items: center; border: 1px solid #303a4b; background: rgba(14,18,28,.88); color: #aab5c8; cursor: pointer; }
.sigma-controls button:hover { border-color: #8b7cf6; color: #fff; }
.spin { animation: spin .85s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }
</style>
