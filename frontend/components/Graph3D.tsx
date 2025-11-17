'use client'

import { useRef, useMemo, useCallback, useEffect, useState, forwardRef } from 'react'
import dynamic from 'next/dynamic'
import * as THREE from 'three'

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
  _ref
) {
  const graphRef = useRef<any>(null)

  // Load CSS2D safely
  const [CSS2D, setCSS2D] = useState<{ CSS2DRenderer: any; CSS2DObject: any } | null>(null)
  useEffect(() => {
    let mounted = true
    import('three/examples/jsm/renderers/CSS2DRenderer.js')
      .then(mod => {
        if (mounted) setCSS2D({ CSS2DRenderer: mod.CSS2DRenderer, CSS2DObject: mod.CSS2DObject })
      })
      .catch(() => setCSS2D(null))
    return () => { mounted = false }
  }, [])

  // Color constants
  const DEFAULT_COLOR = '#32cd32' // 🔹 light green (default)
  const DEFAULT_COLOR_HEX = parseInt(DEFAULT_COLOR.replace('#', ''), 16)
  const PRIMARY_COLOR = '#4a90e2' // 🔵 blue (primary affected service - where error occurred)
  const PRIMARY_COLOR_HEX = parseInt(PRIMARY_COLOR.replace('#', ''), 16)
  const DEPENDENT_COLOR = '#ff6b6b' // 🔴 red (dependent services - affected by error)
  const DEPENDENT_COLOR_HEX = parseInt(DEPENDENT_COLOR.replace('#', ''), 16)
  const R = 0.7

  // re-mount key on data size change + highlight state changes
  const graphKey = useMemo(() => {
    const n = (data?.nodes ?? []).length
    const l = (data?.links ?? []).length
    // Include highlight state to force remount when colors change
    const primaryCount = sourceNode ? 1 : (changedNodes?.size ?? 0)
    const dependentCount = highlightedNodes?.size ?? 0
    const nodeIds = (data?.nodes ?? []).slice(0, 5).map((n: any) => n?.id || n?.name).join(',')
    const linkIds = (data?.links ?? []).slice(0, 5).map((l: any) => `${l?.source?.id || l?.source}-${l?.target?.id || l?.target}`).join(',')
    return `g-${n}-${l}-p${primaryCount}-d${dependentCount}-${nodeIds}-${linkIds}`
  }, [data, sourceNode, changedNodes, highlightedNodes])

  // node shape + label with dynamic coloring
  const nodeThreeObject = useCallback((n: any) => {
    const group = new THREE.Group()
    const nodeId = String(n?.id ?? n?.name ?? '')
    
    // Determine node color based on error analyzer state
    let nodeColor = DEFAULT_COLOR_HEX
    let labelColor = DEFAULT_COLOR
    
    // Primary affected service (where error occurred) - BLUE
    if (sourceNode === nodeId || (changedNodes && changedNodes.has(nodeId))) {
      nodeColor = PRIMARY_COLOR_HEX
      labelColor = PRIMARY_COLOR
      console.log('🎯 Node colored BLUE (primary):', nodeId, 'sourceNode:', sourceNode, 'changedNodes:', Array.from(changedNodes || []))
    }
    // Dependent services (affected by error) - RED
    else if (highlightedNodes && highlightedNodes.has(nodeId)) {
      nodeColor = DEPENDENT_COLOR_HEX
      labelColor = DEPENDENT_COLOR
      console.log('🔴 Node colored RED (dependent):', nodeId, 'highlightedNodes:', Array.from(highlightedNodes || []))
    }

    const sphere = new THREE.Mesh(
      new THREE.SphereGeometry(R, 32, 32),
      new THREE.MeshBasicMaterial({ color: nodeColor })
    )
    ;(sphere.material as THREE.MeshBasicMaterial).toneMapped = false
    group.add(sphere)

    if (CSS2D?.CSS2DObject) {
      const el = document.createElement('div')
      el.textContent = String(n.name ?? n.id ?? '')
      Object.assign(el.style, {
        fontSize: '12px',
        lineHeight: '1',
        padding: '2px 6px',
        borderRadius: '6px',
        background: 'rgba(0,0,0,0.55)',
        color: labelColor,          // label matches node color
        whiteSpace: 'nowrap',
        userSelect: 'none',
        pointerEvents: 'none'
      } as CSSStyleDeclaration)
      const label = new CSS2D.CSS2DObject(el)
      label.position.set(0, R * 3.2, 0)
      group.add(label)
    }

    return group
  }, [CSS2D, sourceNode, changedNodes, highlightedNodes, R])

  // clean data
  const cleanData = useMemo(() => {
    const nodes = (data?.nodes ?? []).map((n: any, i: number) => ({
      ...n,
      id: String(n?.id ?? n?.name ?? `n-${i}`),
      name: String(n?.name ?? n?.id ?? `n-${i}`)
    }))
    const byId = new Map(nodes.map((n: any) => [n.id, n]))
    const links = (data?.links ?? [])
      .map((l: any) => {
        const s = String(l?.source?.id ?? l?.source ?? '')
        const t = String(l?.target?.id ?? l?.target ?? '')
        if (!s || !t || !byId.has(s) || !byId.has(t)) return null
        return { ...l, source: byId.get(s), target: byId.get(t) }
      })
      .filter(Boolean) as any[]
    return { nodes, links }
  }, [data])

  // Force graph rebuild when highlight states change
  useEffect(() => {
    const g = graphRef.current
    if (!g || !cleanData.nodes.length) return

    console.log('🔄 Graph highlight state changed, forcing rebuild:', {
      sourceNode,
      changedNodes: Array.from(changedNodes || []),
      highlightedNodes: Array.from(highlightedNodes || [])
    })

    // Force remount by clearing and resetting graph data
    g.nodeThreeObject(nodeThreeObject)
    g.nodeThreeObjectExtend(false)
    g.graphData({ nodes: [], links: [] })
    requestAnimationFrame(() => {
      if (graphRef.current) {
        graphRef.current.graphData(cleanData)
      }
    })
  }, [nodeThreeObject, cleanData, sourceNode, changedNodes, highlightedNodes])

  const extraRenderers = useMemo(() => {
    if (!CSS2D?.CSS2DRenderer) return []
    const r = new CSS2D.CSS2DRenderer()
    r.domElement.style.position = 'absolute'
    r.domElement.style.top = '0'
    r.domElement.style.left = '0'
    r.domElement.style.pointerEvents = 'none'
    return [r as unknown as THREE.Renderer]
  }, [CSS2D])

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
  }, [onNodeSelect])

  return (
    <div className="relative w-full h-full" style={{ background: '#000011' }}>
      <ForceGraph3D
        key={graphKey}
        ref={graphRef}
        graphData={cleanData}
        backgroundColor="#000011"
        showNavInfo={false}
        extraRenderers={extraRenderers}
        rendererConfig={{ antialias: true, alpha: true, logarithmicDepthBuffer: false }}

        nodeThreeObject={nodeThreeObject}
        nodeThreeObjectExtend={false}
        nodeLabel={(n: any) => String(n.name ?? n.id ?? '')}
        linkColor={(l: any) => {
          // DO NOT change edge colors - always use default colors based on connection type
          const kind = (l.kind || l.type || '').toString().toUpperCase()
          return kind === 'KAFKA' ? '#ffd700' : '#ffffff' // Gold for Kafka, white for HTTP
        }}
        linkWidth={(l: any) => {
          // DO NOT change edge width - always use default width
          return 0.25
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
