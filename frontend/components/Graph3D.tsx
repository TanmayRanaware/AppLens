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
  ref
) {
  const graphRef = useRef<any>(null)

  const [CSS2D, setCSS2D] = useState<{ CSS2DRenderer: any; CSS2DObject: any } | null>(null)
  useEffect(() => {
    import('three/examples/jsm/renderers/CSS2DRenderer.js')
      .then(mod => setCSS2D({ CSS2DRenderer: mod.CSS2DRenderer, CSS2DObject: mod.CSS2DObject }))
      .catch(() => setCSS2D(null))
  }, [])

  // Include a style token so the FG3D instance re-mounts with our custom node objects
  // Bump STYLE token if you still see blue/default colors
  const graphKey = useMemo(() => {
    const n = (data?.nodes ?? []).length
    const l = (data?.links ?? []).length
    const STYLE = 'green_d3_r1.5'  // style token forces remount
    return `g-${n}-${l}-${STYLE}`
  }, [data])

  // Appearance: pure green, diameter 3
  const GREEN_HEX = 0x00ff00
  const DIAMETER = 3.0
  const R = DIAMETER / 2 // 1.5

  // Build our custom node (green, unlit) + optional CSS2D label
  const nodeThreeObject = useCallback((n: any) => {
    const group = new THREE.Group()

    const sphere = new THREE.Mesh(
      new THREE.SphereGeometry(R, 32, 32),
      // MeshBasicMaterial = unlit => exact color (no scene lights turning it blue)
      new THREE.MeshBasicMaterial({ color: GREEN_HEX })
    )
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
        color: '#ffeaa7',
        whiteSpace: 'nowrap',
        userSelect: 'none',
        pointerEvents: 'none'
      } as CSSStyleDeclaration)
      const label = new CSS2D.CSS2DObject(el)
      label.position.set(0, R * 2.2, 0)
      group.add(label)
    }

    return group
  }, [CSS2D])

  // Sanitize input: remove any per-node `color` so it can't override green
  const cleanData = useMemo(() => {
    const nodes = (data?.nodes ?? []).map((n: any, i: number) => {
      const { color: _dropColor, ...rest } = n || {}
      return {
        ...rest,
        id: String(rest.id ?? rest.name ?? `n-${i}`),
        name: String(rest.name ?? rest.id ?? `n-${i}`)
      }
    })

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

  // Nuclear option: Force rebuild of objects to clear old blue/default spheres
  useEffect(() => {
    const g = graphRef.current
    if (!g || !cleanData.nodes.length) return

    // Set custom node factory
    if (typeof g.nodeThreeObject === 'function') g.nodeThreeObject(nodeThreeObject)
    if (typeof g.nodeThreeObjectExtend === 'function') g.nodeThreeObjectExtend(false)

    // Force rebuild: clear old objects then re-create with green material
    g.graphData({ nodes: [], links: [] })
    requestAnimationFrame(() => {
      if (graphRef.current) {
        graphRef.current.graphData(cleanData)
      }
    })
  }, [nodeThreeObject, cleanData])

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

        // CRITICAL: only our mesh, no default blue spheres
        nodeThreeObject={nodeThreeObject}
        nodeThreeObjectExtend={false}

        // Backstop (if FG3D ever falls back to defaults)
        nodeColor={() => '#00ff00'}

        nodeLabel={(n: any) => String(n.name ?? n.id ?? '')}
        linkColor={(l: any) => {
          const s = String(l.source?.id || l.source)
          const t = String(l.target?.id || l.target)
          const k = `${s}-${t}`, rk = `${t}-${s}`
          const hi = highlightedLinks.has(k) || highlightedLinks.has(rk) ||
                     highlightedNodes.has(s) || highlightedNodes.has(t)
          if (hi) return '#ff6b6b'
          const kind = (l.kind || l.type || '').toString().toUpperCase()
          return kind === 'KAFKA' ? '#ffd700' : '#ffffff'
        }}
        linkWidth={(l: any) => {
          const s = String(l.source?.id || l.source)
          const t = String(l.target?.id || l.target)
          const k = `${s}-${t}`, rk = `${t}-${s}`
          const hi = highlightedLinks.has(k) || highlightedLinks.has(rk) ||
                     highlightedNodes.has(s) || highlightedNodes.has(t)
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
