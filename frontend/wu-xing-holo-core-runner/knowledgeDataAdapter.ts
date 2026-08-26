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

function getRandomOffset(baseRadius: number, radiusVariance: number) {
  const r = baseRadius + (Math.random() - 0.5) * 2 * radiusVariance
  const theta = Math.random() * 2 * Math.PI
  const phi = Math.acos(2 * Math.random() - 1)
  return {
    x: r * Math.sin(phi) * Math.cos(theta),
    y: r * Math.sin(phi) * Math.sin(theta),
    z: r * Math.cos(phi),
  }
}

function getJitteredFibonacciSpherePoints(samples: number, baseRadius: number, radiusVariance: number) {
  const points: Array<{ x: number, y: number, z: number }> = []
  const phi = Math.PI * (3 - Math.sqrt(5))
  for (let index = 0; index < samples; index += 1) {
    const y = 1 - (index / (samples - 1)) * 2
    const rBase = Math.sqrt(1 - y * y)
    const theta = phi * index
    const r = baseRadius + (Math.random() - 0.5) * 2 * radiusVariance
    points.push({
      x: Math.cos(theta) * rBase * r,
      y: y * r,
      z: Math.sin(theta) * rBase * r,
    })
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
    explanation: text(entry.explanation, text(entry.summary)),
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
  const mainPoints = getJitteredFibonacciSpherePoints(mainEntries.length, 18, 6)

  mainEntries.forEach((mainEntry, mainIndex) => {
    const mainNode = addNode(nodes, mainEntry, 1, mainPoints[mainIndex], rootNode.id, rootNode.domain)
    edges.push({ source: rootNode.id, target: mainNode.id })

    const subEntries = Array.isArray(mainEntry.children) ? mainEntry.children : []
    subEntries.forEach((subEntry) => {
      const subOffset = getRandomOffset(4, 2)
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
      pointEntries.forEach((pointEntry) => {
        const pointOffset = getRandomOffset(2, 1)
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

  return { nodes, edges }
}

export const { nodes, edges } = generateGraph()
