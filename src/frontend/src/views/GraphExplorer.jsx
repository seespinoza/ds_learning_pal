import { useQuery } from '@tanstack/react-query'
import { useRef, useState, useCallback } from 'react'
import ForceGraph2D from 'react-force-graph-2d'
import { fetchNodes } from '../api/nodes'
import { fetchRelationships } from '../api/relationships'
import NodePanel from '../components/NodePanel'

const LABEL_COLORS = {
  Domain: '#6366f1',
  Concept: '#22d3ee',
  Algorithm: '#f59e0b',
  Model: '#34d399',
  Technique: '#f472b6',
  Tool: '#a78bfa',
  Platform: '#fb923c',
}

export default function GraphExplorer() {
  const [selectedNode, setSelectedNode] = useState(null)
  const fgRef = useRef()

  const { data: nodes = [], isLoading: nodesLoading } = useQuery({
    queryKey: ['nodes'],
    queryFn: fetchNodes,
  })
  const { data: rels = [], isLoading: relsLoading } = useQuery({
    queryKey: ['relationships'],
    queryFn: fetchRelationships,
  })

  const graphData = {
    nodes: nodes.map(n => ({
      id: `${n.label}:${n.name}`,
      name: n.name,
      label: n.label,
      ...n,
    })),
    links: rels.map(r => ({
      source: `${r.from_label}:${r.from_name}`,
      target: `${r.to_label}:${r.to_name}`,
      type: r.type,
    })),
  }

  const handleNodeClick = useCallback((node) => {
    setSelectedNode(node)
  }, [])

  if (nodesLoading || relsLoading) {
    return (
      <div className="flex items-center justify-center h-full text-slate-400">
        Loading graph…
      </div>
    )
  }

  return (
    <div className="relative flex-1 overflow-hidden">
      <ForceGraph2D
        ref={fgRef}
        graphData={graphData}
        nodeLabel="name"
        nodeColor={node => LABEL_COLORS[node.label] ?? '#94a3b8'}
        nodeRelSize={6}
        linkLabel="type"
        linkColor={() => '#334155'}
        linkDirectionalArrowLength={4}
        linkDirectionalArrowRelPos={1}
        onNodeClick={handleNodeClick}
        backgroundColor="#0f1117"
        width={window.innerWidth - (selectedNode ? 360 : 0)}
      />

      {selectedNode && (
        <NodePanel node={selectedNode} onClose={() => setSelectedNode(null)} />
      )}

      <div className="absolute top-4 left-4 bg-slate-800/80 rounded-lg p-3 text-xs space-y-1">
        {Object.entries(LABEL_COLORS).map(([label, color]) => (
          <div key={label} className="flex items-center gap-2">
            <span className="w-3 h-3 rounded-full inline-block" style={{ background: color }} />
            <span className="text-slate-300">{label}</span>
          </div>
        ))}
      </div>
    </div>
  )
}
