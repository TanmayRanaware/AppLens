'use client'

import { useRef, useMemo, useCallback, useEffect, forwardRef } from 'react'
import dynamic from 'next/dynamic'
import * as THREE from 'three'

// HTML labels (like the vasturiano example)
import { CSS2DRenderer, CSS2DObject } from 'three/examples/jsm/renderers/CSS2DRenderer.js'

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

  // re-mount if topology changes
  const graphKey = useMemo(() => {
    const n = (data?.nodes ?? []).length
    const l = (data?.links ?? []).length
    return `g-${n}-${l}`
  }, [data])

  const getNodeColor = useCallback((n: any) => {
    const id = String(n.id)
    const whatIf = changedNodes.size > 0
    if (changedNodes.has(id)) return '#00aaff'
    if (sourceNode && id === String(sourceNode)) return '#ff3b30'
    if (highlightedNodes.has(id)) return whatIf ? '#ff3b30' : '#ffd700'
    if (selectedNode?.id === n.id) return '#ffd700'
    return '#39ff14'
  }, [changedNodes, highlightedNodes, sourceNode, selectedNode])

  // sphere + HTML label (CSS2DObject)
  const nodeThreeObject = useCallback((n: any) => {
    const group = new THREE.Group()

    // tiny sphere
    const r = 0.16
    const sphere = new THREE.Mesh(
      new THREE.SphereGeometry(r, 16, 16),
      new THREE.MeshPhongMaterial({
        color: getNodeColor(n),
        emissive: getNodeColor(n),
        emissiveIntensity: 0.35
      })
    )
    group.add(sphere)

    // HTML label
    const el = document.createElement('div')
    el.textContent = String(n.name ?? n.id ?? '')
    el.className = 'rg-node-label'

    // inline styles so you don’t need a global css file
    Object.assign(el.style, {
      fontSize: '12px',
      lineHeight: '1',
      padding: '2px 6px',
      borderRadius: '6px',
      background: 'rgba(0,0,0,0.55)',
      color: '#ffeaa7',
      whiteSpace: 'nowrap',
      userSelect: 'none',
      pointerEvents: 'none' // let clicks go to the sphere
    } as CSSStyleDeclaration)

    const label = new CSS2DObject(el)
    label.position.set(0, r * 3.2, 0) // above sphere
    group.add(label)

    return group
  }, [getNodeColor])

  const cleanData = useMemo(() => {
    const nodes = (data?.nodes ?? []).map((n: any, i: number) => ({
      ...n,
      id: String(n.id ?? n.name ?? `n-${i}`),
      name: String(n.name ?? n.id ?? `n-${i}`)
    }))
    const byId = new Map(nodes.map((n: any) => [n.id, n]))
    const links = (data?.links ?? [])
      .map((l: any) => {
        const s = String(l.source?.id ?? l.source)
        const t = String(l.target?.id ?? l.target)
        if (!byId.has(s) || !byId.has(t)) return null
        return { ...l, source: byId.get(s), target: byId.get(t) }
      })
      .filter(Boolean) as any[]
    return { nodes, links }
  }, [data])

  useEffect(() => {
    const g = graphRef.current
    if (!g || !cleanData.nodes.length) return
    if (typeof g.nodeThreeObject === 'function') g.nodeThreeObject(nodeThreeObject)
    // IMPORTANT: allow our custom object to extend the default node object
    if (typeof g.nodeThreeObjectExtend === 'function') g.nodeThreeObjectExtend(true)
    if (typeof g.refresh === 'function') g.refresh()
  }, [graphRef, nodeThreeObject, cleanData])

  const onNodeClick = useCallback((n: any) => {
    onNodeSelect?.(n)
    const dist = 90
    const ratio = 1 + dist / Math.hypot(n.x || 0, n.y || 0, n.z || 0)
    graphRef.current?.cameraPosition(
      { x: (n.x || 0) * ratio, y: (n.y || 0) * ratio, z: (n.z || 0) * ratio },
      n,
      850
    )
    const controls = graphRef.current?.controls?.()
    if (controls) controls.autoRotate = false
  }, [onNodeSelect, graphRef])

  return (
    <div className="relative w-full h-full" style={{ background: '#000011' }}>
      <ForceGraph3D
        key={graphKey}
        ref={graphRef}
        graphData={cleanData}
        backgroundColor="#000011"
        showNavInfo={false}
        // the magic line: adds the HTML overlay renderer so labels are always visible
        extraRenderers={[new CSS2DRenderer()]}
        rendererConfig={{ antialias: true, alpha: true, logarithmicDepthBuffer: false }}
        nodeThreeObject={nodeThreeObject}
        nodeThreeObjectExtend={true}
        nodeLabel={(n: any) => String(n.name ?? n.id ?? '')}
        linkColor={(l: any) => {
          const s = String(l.source?.id || l.source)
          const t = String(l.target?.id || l.target)
          const k = `${s}-${t}`, rk = `${t}-${s}`
          const hi = highlightedLinks.has(k) || highlightedLinks.has(rk) || highlightedNodes.has(s) || highlightedNodes.has(t)
          if (hi) return '#ff6b6b'
          const kind = (l.kind || l.type || '').toString().toUpperCase()
          return kind === 'KAFKA' ? '#ffd700' : '#ffffff'
        }}
        linkWidth={(l: any) => {
          const s = String(l.source?.id || l.source)
          const t = String(l.target?.id || l.target)
          const k = `${s}-${t}`, rk = `${t}-${s}`
          const hi = highlightedLinks.has(k) || highlightedLinks.has(rk) || highlightedNodes.has(s) || highlightedNodes.has(t)
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
