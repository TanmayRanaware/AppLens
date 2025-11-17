'use client'

import { useRef, useEffect, useMemo, useCallback, forwardRef } from 'react'
import dynamic from 'next/dynamic'
import * as THREE from 'three'
import SpriteText from 'three-spritetext'

const ForceGraph3D = dynamic(
  () => import('react-force-graph-3d').then(m => m.default),
  { ssr: false }
)

interface Graph3DProps {
  data: { nodes: any[]; links: any[] }
  highlightedNodes?: Set<string>
  highlightedLinks?: Set<string>
  sourceNode?: string
  changedNodes?: Set<string>
  onNodeSelect?: (node: any) => void
  selectedNode?: any
}

const Graph3D = forwardRef<any, Graph3DProps>(function Graph3D(
  {
    data,
    highlightedNodes = new Set(),
    highlightedLinks = new Set(),
    sourceNode,
    changedNodes = new Set(),
    onNodeSelect,
    selectedNode
  },
  ref
) {
  const fgRef = useRef<any>(null)
  const graphRef = (ref as any) || fgRef

  // --- styling helpers -------------------------------------------------------
  const getNodeColor = useCallback((node: any) => {
    const id = String(node.id)
    const whatIf = changedNodes.size > 0

    if (changedNodes.has(id)) return '#00aaff'
    if (sourceNode && id === String(sourceNode)) return '#ff0000'
    if (highlightedNodes.has(id)) return whatIf ? '#ff0000' : '#ffd700'
    if (selectedNode?.id === node.id) return '#ffd700'
    return '#00ff00'
  }, [changedNodes, highlightedNodes, sourceNode, selectedNode])

  // --- sprite label + sphere -------------------------------------------------
  const nodeWithLabel = useCallback((node: any) => {
    // small sphere so label is the star
    const r = 0.18
    const group = new THREE.Group()

    const sphere = new THREE.Mesh(
      new THREE.SphereGeometry(r, 16, 16),
      new THREE.MeshPhongMaterial({
        color: getNodeColor(node),
        emissive: getNodeColor(node),
        emissiveIntensity: 0.35
      })
    )
    group.add(sphere)

    // label (service name)
    const text = String(node.name ?? node.id ?? 'Unknown')
    const label = new SpriteText(text) as any
    label.textHeight = 4.5
    label.color = '#ffffbf' // warm yellow for contrast
    label.backgroundColor = 'rgba(0,0,0,0.55)'
    label.padding = 2
    label.borderWidth = 0

    // keep readable in clutter
    if (label.material) {
      label.material.depthWrite = false
      label.material.depthTest = false
    }
    label.renderOrder = 999

    // position just above the sphere
    label.position.set(0, r * 3.2, 0)
    group.add(label)

    return group
  }, [getNodeColor])

  // --- stabilize input data --------------------------------------------------
  const cleanData = useMemo(() => {
    if (!data) return { nodes: [], links: [] }

    const nodes = (data.nodes || []).map((n: any, i: number) => ({
      ...n,
      id: String(n.id ?? n.name ?? `n-${i}`),
      name: String(n.name ?? n.id ?? `n-${i}`)
    }))
    const byId = new Map(nodes.map((n: any) => [String(n.id), n]))

    const links = (data.links || [])
      .map((l: any) => {
        const sid = String(l.source?.id ?? l.source)
        const tid = String(l.target?.id ?? l.target)
        if (!byId.has(sid) || !byId.has(tid)) return null
        return { ...l, source: byId.get(sid), target: byId.get(tid) }
      })
      .filter(Boolean) as any[]

    return { nodes, links }
  }, [data])

  // --- apply accessor through ref as well & force rebuild --------------------
  useEffect(() => {
    const g = graphRef.current
    if (!g || !cleanData.nodes.length) return

    if (typeof g.nodeThreeObject === 'function') g.nodeThreeObject(nodeWithLabel)
    if (typeof g.nodeThreeObjectExtend === 'function') g.nodeThreeObjectExtend(false)
    if (typeof g.refresh === 'function') g.refresh()
  }, [graphRef, cleanData, nodeWithLabel])

  // --- interactions ----------------------------------------------------------
  const onNodeClick = useCallback((node: any) => {
    onNodeSelect?.(node)
    const dist = 90
    const ratio = 1 + dist / Math.hypot(node.x || 0, node.y || 0, node.z || 0)
    graphRef.current?.cameraPosition(
      { x: (node.x || 0) * ratio, y: (node.y || 0) * ratio, z: (node.z || 0) * ratio },
      node,
      800
    )
    const controls = graphRef.current?.controls?.()
    if (controls) controls.autoRotate = false
  }, [onNodeSelect, graphRef])

  // --- render ---------------------------------------------------------------
  return (
    <div className="relative w-full h-full" style={{ background: '#000011' }}>
      <ForceGraph3D
        ref={graphRef}
        graphData={cleanData}
        backgroundColor="#000011"
        showNavInfo={false}
        nodeThreeObject={nodeWithLabel}
        nodeThreeObjectExtend={false}
        nodeLabel={(n: any) => String(n.name ?? n.id ?? '')} // still shows on hover
        linkColor={(link: any) => {
          const s = String(link.source?.id || link.source)
          const t = String(link.target?.id || link.target)
          const key = `${s}-${t}`, rkey = `${t}-${s}`
          const hi = highlightedLinks.has(key) || highlightedLinks.has(rkey)
                    || highlightedNodes.has(s) || highlightedNodes.has(t)
          if (hi) return '#ff6b6b'
          const kind = (link.kind || link.type || '').toString().toUpperCase()
          if (kind === 'KAFKA') return '#ffd700'
          return '#ffffff'
        }}
        linkWidth={(link: any) => {
          const s = String(link.source?.id || link.source)
          const t = String(link.target?.id || link.target)
          const key = `${s}-${t}`, rkey = `${t}-${s}`
          const hi = highlightedLinks.has(key) || highlightedLinks.has(rkey)
                    || highlightedNodes.has(s) || highlightedNodes.has(t)
          return hi ? 0.18 : 0.25
        }}
        linkOpacity={0.6}
        d3AlphaDecay={0.02}
        d3VelocityDecay={0.4}
        cooldownTicks={200}
        onNodeClick={onNodeClick}
      />
    </div>
  )
})

export default Graph3D
