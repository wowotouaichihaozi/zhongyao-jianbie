// ForceAtlas2 worker architecture adapted from nashsu/llm_wiki (GPL-3.0).
import Graph from 'graphology'
import forceAtlas2 from 'graphology-layout-forceatlas2'

self.onmessage = (event) => {
  const { key, nodes, edges, iterations, scalingRatio } = event.data

  try {
    const graph = new Graph({ type: 'undirected', multi: false, allowSelfLoops: false })

    nodes.forEach(node => graph.addNode(node.id, { x: node.x, y: node.y }))
    edges.forEach((edge, index) => {
      if (!graph.hasNode(edge.source) || !graph.hasNode(edge.target) || edge.source === edge.target) return
      if (graph.hasEdge(edge.source, edge.target)) return
      graph.addUndirectedEdgeWithKey(`edge-${index}`, edge.source, edge.target, { weight: edge.weight || 1 })
    })

    const inferred = forceAtlas2.inferSettings(graph)
    forceAtlas2.assign(graph, {
      iterations,
      settings: {
        ...inferred,
        gravity: 1,
        scalingRatio,
        strongGravityMode: true,
        barnesHutOptimize: nodes.length > 50,
      },
    })

    const positions = []
    graph.forEachNode((id, attrs) => positions.push({ id, x: attrs.x, y: attrs.y }))
    self.postMessage({ type: 'complete', key, positions })
  } catch (error) {
    self.postMessage({ type: 'error', key, message: error instanceof Error ? error.message : String(error) })
  }
}
