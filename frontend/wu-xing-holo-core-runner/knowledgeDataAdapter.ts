import sourceKnowledge from '../src/data/tcm-knowledge-network.v1.2-substantive.json'

export type NodeLevel = 'root' | 'main' | 'subtopic' | 'knowledge_point'

export interface GraphNode {
  id: string
  title: string
  level: NodeLevel
  domain: string
  color: string
  x: number
  y: number
  z: number
  parent?: string
  summary?: string
  explanation?: string
  keywords?: string[]
  tags?: string[]
}

export interface GraphEdge {
  source: string
  target: string
}

type KnowledgeEntry = {
  id?: string
  title?: string
  domain?: string
  summary?: string
  explanation?: string
  keywords?: unknown[]
  tags?: unknown[]
  children?: KnowledgeEntry[]
}

const DOMAIN_COLORS = [
  '#ef4444', '#22c55e', '#06b6d4', '#eab308', '#f97316',
  '#8b5cf6', '#ec4899', '#f43f5e', '#84cc16', '#14b8a6',
]

const domains = Array.isArray(sourceKnowledge.metadata?.domains)
  ? sourceKnowledge.metadata.domains.map((domain) => String(domain || '').trim())
  : []

const colorByDomain = new Map(domains.map((domain, index) => [domain, DOMAIN_COLORS[index] || '#ffffff']))

function text(value: unknown, fallback = '') {
  return typeof value === 'string' && value.trim() ? value.trim() : fallback
}

function textList(value: unknown) {
  return Array.isArray(value)
    ? value.map((item) => text(item)).filter(Boolean)
    : []
}

function nodeExplanation(entry: KnowledgeEntry, depth: number, domain: string) {
  const title = text(entry.title, text(entry.id))
  const summary = text(entry.summary, `${title}是${domain}领域中的重要知识节点。`)
  const children = Array.isArray(entry.children) ? entry.children : []
  if (depth >= 3) return text(entry.explanation, summary)
  const childTitles = children.map(child => text(child.title, text(child.id))).filter(Boolean)
  if (depth === 0) {
    return `${summary} 当前知识网络按知识域、主题、子主题和具体知识点组织，适合先建立整体框架，再沿父子关系逐层学习。`
  }
  if (depth === 1) {
    const outline = childTitles.length ? `下设${childTitles.length}个子主题：${childTitles.join('、')}。` : '当前主题暂无下级条目。'
    return `${summary} 作为${domain}中的核心主题，它用于界定概念范围、梳理主要关系，并连接到更具体的学习内容。${outline} 学习时应先掌握主题边界，再结合下级条目理解机制、表现和应用。`
  }
  const outline = childTitles.length ? `包含具体知识点：${childTitles.join('、')}。` : '当前子主题暂无具体知识点。'
  return `${summary} 本子主题用于把上位主题进一步拆解为可学习、可比较的内容单元，帮助理解相关概念之间的层次和联系。${outline} 学习时可先明确本层的核心问题，再对照具体知识点进行辨析和复习。`
}

function hashString(value: string, seed = 2166136261) {
  let hash = seed >>> 0
  for (const character of value) {
    hash ^= character.charCodeAt(0)
    hash = Math.imul(hash, 16777619)
  }
  hash ^= hash >>> 16
  hash = Math.imul(hash, 0x7feb352d)
  hash ^= hash >>> 15
  hash = Math.imul(hash, 0x846ca68b)
  hash ^= hash >>> 16
  return hash >>> 0
}

function getFibonacciSpherePoints(samples: number, baseRadius: number, radiusVariance = 0, phase = 0) {
  const points: Array<{ x: number, y: number, z: number }> = []
  const phi = Math.PI * (3 - Math.sqrt(5))
  for (let index = 0; index < samples; index += 1) {
    const y = samples === 1 ? 0 : 1 - (index / (samples - 1)) * 2
    const rBase = Math.sqrt(1 - y * y)
    const theta = phi * index + phase
    const stableJitter = Math.sin((index + 1) * 2.399963229728653 + phase) * radiusVariance
    const r = baseRadius + stableJitter
    points.push({
      x: Math.cos(theta) * rBase * r,
      y: y * r,
      z: Math.sin(theta) * rBase * r,
    })
  }
  return points
}

function rotatePoint(point: { x: number, y: number, z: number }, key: string) {
  const xAngle = (hashString(key, 2246822519) / 0xffffffff) * Math.PI
  const yAngle = (hashString(key, 3266489917) / 0xffffffff) * 2 * Math.PI
  const zAngle = (hashString(key, 668265263) / 0xffffffff) * 2 * Math.PI
  const cosX = Math.cos(xAngle)
  const sinX = Math.sin(xAngle)
  const cosY = Math.cos(yAngle)
  const sinY = Math.sin(yAngle)
  const cosZ = Math.cos(zAngle)
  const sinZ = Math.sin(zAngle)
  const y = point.y * cosX - point.z * sinX
  const z = point.y * sinX + point.z * cosX
  const x = point.x * cosY + z * sinY
  const rotatedZ = -point.x * sinY + z * cosY
  return {
    x: x * cosZ - y * sinZ,
    y: x * sinZ + y * cosZ,
    z: rotatedZ,
  }
}

function getStableSiblingOffsets(key: string, samples: number, baseRadius: number, radiusVariance: number) {
  const phase = (hashString(key, 374761393) / 0xffffffff) * 2 * Math.PI
  const points = getFibonacciSpherePoints(samples, baseRadius, radiusVariance, phase)
    .map((point, index) => {
      const rotated = rotatePoint(point, `${key}:${index}`)
      const radialScale = 0.9 + (hashString(`${key}:${index}`, 1274126177) / 0xffffffff) * 0.2
      return { x: rotated.x * radialScale, y: rotated.y * radialScale, z: rotated.z * radialScale }
    })
  const minimumDistance = Math.max(0.7, baseRadius * 0.72)
  for (let index = 1; index < points.length; index += 1) {
    let candidate = points[index]
    let attempts = 0
    while (attempts < 8 && points.slice(0, index).some(previous => {
      const dx = candidate.x - previous.x
      const dy = candidate.y - previous.y
      const dz = candidate.z - previous.z
      return Math.sqrt(dx * dx + dy * dy + dz * dz) < minimumDistance
    })) {
      candidate = rotatePoint(candidate, `${key}:separate:${index}:${attempts}`)
      attempts += 1
    }
    points[index] = candidate
  }
  return points
}

function nodeLevel(depth: number): NodeLevel {
  if (depth === 0) return 'root'
  if (depth === 1) return 'main'
  if (depth === 2) return 'subtopic'
  return 'knowledge_point'
}

function addNode(
  nodes: GraphNode[],
  entry: KnowledgeEntry,
  depth: number,
  position: { x: number, y: number, z: number },
  parent: string | undefined,
  inheritedDomain: string,
) {
  const domain = text(entry.domain, inheritedDomain)
  const node: GraphNode = {
    id: text(entry.id),
    title: text(entry.title, text(entry.id)),
    level: nodeLevel(depth),
    domain,
    color: depth === 0 ? '#ffffff' : colorByDomain.get(domain) || '#ffffff',
    x: position.x,
    y: position.y,
    z: position.z,
    parent,
    summary: text(entry.summary),
    explanation: nodeExplanation(entry, depth, domain),
  }
  const keywords = textList(entry.keywords)
  const tags = textList(entry.tags)
  if (keywords.length) node.keywords = keywords
  if (tags.length) node.tags = tags
  nodes.push(node)
  return node
}

function generateGraph() {
  const nodes: GraphNode[] = []
  const edges: GraphEdge[] = []
  const root = sourceKnowledge.root as KnowledgeEntry
  const rootNode = addNode(nodes, root, 0, { x: 0, y: 0, z: 0 }, undefined, 'Overview')
  const mainEntries = Array.isArray(root.children) ? root.children : []
  const entriesByDomain = new Map<string, KnowledgeEntry[]>()
  mainEntries.forEach((entry) => {
    const domain = text(entry.domain, rootNode.domain)
    const entries = entriesByDomain.get(domain) || []
    entries.push(entry)
    entriesByDomain.set(domain, entries)
  })
  const extraDomains = [...entriesByDomain.keys()].filter(domain => !domains.includes(domain))
  const orderedDomains = [...domains, ...extraDomains]
  const domainCenters = getFibonacciSpherePoints(orderedDomains.length, 9.5, 0.35, 0.65)

  orderedDomains.forEach((domain, domainIndex) => {
    const domainEntries = entriesByDomain.get(domain) || []
    const center = domainCenters[domainIndex] || { x: 0, y: 0, z: 0 }
    const topicOffsets = getFibonacciSpherePoints(domainEntries.length, 5, 0.4, domainIndex * 0.91)

    domainEntries.forEach((mainEntry, topicIndex) => {
      const topicOffset = topicOffsets[topicIndex] || { x: 0, y: 0, z: 0 }
      const mainNode = addNode(
        nodes,
        mainEntry,
        1,
        {
          x: center.x + topicOffset.x,
          y: center.y + topicOffset.y,
          z: center.z + topicOffset.z,
        },
        rootNode.id,
        domain,
      )
      edges.push({ source: rootNode.id, target: mainNode.id })

      const subEntries = Array.isArray(mainEntry.children) ? mainEntry.children : []
      const subOffsets = getStableSiblingOffsets(mainNode.id, subEntries.length, 2.2, 0.3)
      subEntries.forEach((subEntry, subIndex) => {
        const subOffset = subOffsets[subIndex] || { x: 0, y: 0, z: 0 }
        const subNode = addNode(
          nodes,
          subEntry,
          2,
          {
            x: mainNode.x + subOffset.x,
            y: mainNode.y + subOffset.y,
            z: mainNode.z + subOffset.z,
          },
          mainNode.id,
          mainNode.domain,
        )
        edges.push({ source: mainNode.id, target: subNode.id })

        const pointEntries = Array.isArray(subEntry.children) ? subEntry.children : []
        const pointOffsets = getStableSiblingOffsets(subNode.id, pointEntries.length, 1.2, 0.16)
        pointEntries.forEach((pointEntry, pointIndex) => {
          const pointOffset = pointOffsets[pointIndex] || { x: 0, y: 0, z: 0 }
          const pointNode = addNode(
            nodes,
            pointEntry,
            3,
            {
              x: subNode.x + pointOffset.x,
              y: subNode.y + pointOffset.y,
              z: subNode.z + pointOffset.z,
            },
            subNode.id,
            subNode.domain,
          )
          edges.push({ source: subNode.id, target: pointNode.id })
        })
      })
    })
  })

  return { nodes, edges }
}

export const { nodes, edges } = generateGraph()
