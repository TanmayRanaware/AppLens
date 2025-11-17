'use client'

import { useRef, useMemo, useCallback, useEffect, forwardRef } from 'react'
import dynamic from 'next/dynamic'
import * as THREE from 'three'
import { CSS2DRenderer, CSS2DObject } from 'three/examples/jsm/renderers/CSS2DRenderer' // TS path (no .js)

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

  // Re-mount if topology changes
  const graphKey = useMemo(() => {
    const n = (data?.nodes ?? []).length
    const l = (data?.links ?? []).length
    return `g-${n}-${l}`
  }, [data])

  // Create CSS2D renderer once (overlay for HTML labels)
  const css2d = useMemo(() => {
    const r = new CSS2DRenderer()
    r.domElement.style.position = 'absolute'
    r.domElement.style.top = '0'
    r.domElement.style.left = '0'
    r.domElement.style.pointerEvents = 'none'
    return r
  }, [])

  // colors
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

    const el = document.createElement('div')
    el.textContent = String(n.name ?? n.id ?? '')
    el.style.fontSize = '12px'
    el.style.lineHeight = '1'
    el.style.padding = '2px 6px'
    el.style.borderRadius = '6px'
    el.style.background = 'rgba(0,0,0,0.55)'
    el.style.color = '#ffeaa7'
    el.style.whiteSpace = 'nowrap'
    el.style.userSelect = 'none'
    el.style.pointerEvents = 'none'

    const label = new CSS2DObject(el)
    label.position.set(0, r * 3.2, 0) // above sphere
    group.add(label)

    return group
  }, [getNodeColor])

  // normalize data
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

  // ensure our accessor is applied + force rebuild
  useEffect(() => {
    const g = graphRef.current
    if (!g || !cleanData.nodes.length) return
    if (typeof g.nodeThreeObject === 'function') g.nodeThreeObject(nodeThreeObject)
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
        // TS thinks extraRenderers must be THREE.Renderer (canvas). Cast is safe at runtime.
        extraRenderers={[css2d as unknown as THREE.Renderer]}
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
