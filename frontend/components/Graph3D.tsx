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
  const fgRef = useRef<any>(null)
  const graphRef = (ref as any) || fgRef

  const [CSS2D, setCSS2D] = useState<{ CSS2DRenderer: any; CSS2DObject: any } | null>(null)

  // lazy-load CSS2D so the build doesn't need its types
  useEffect(() => {
    let mounted = true
    import('three/examples/jsm/renderers/CSS2DRenderer.js')
      .then(mod => { if (mounted) setCSS2D({ CSS2DRenderer: mod.CSS2DRenderer, CSS2DObject: mod.CSS2DObject }) })
      .catch(() => setCSS2D(null))
    return () => { mounted = false }
  }, [])

  // re-mount if topology changes
  const graphKey = useMemo(() => {
    const n = (data?.nodes ?? []).length
    const l = (data?.links ?? []).length
    return `g-${n}-${l}`
  }, [data])

  // sphere color logic (dark blue only)
  const getNodeColor = useCallback(() => 0x0a2a6b, [])

  // sphere + HTML label (CSS2DObject)
  const nodeThreeObject = useCallback((n: any) => {
    const group = new THREE.Group()

    const r = 0.16
    const sphere = new THREE.Mesh(
      new THREE.SphereGeometry(r, 16, 16),
      new THREE.MeshPhongMaterial({
        color: 0x0a2a6b,          // dark blue
        emissive: 0x0a2a6b,       // same dark blue for glow
        emissiveIntensity: 0.35,
        specular: 0x111111,
        shininess: 25
      })
    )
    group.add(sphere)

    // only add HTML label once CSS2D is ready (client-side only)
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
      label.position.set(0, r * 3.2, 0) // above sphere
      group.add(label)
    }

    return group
  }, [CSS2D])

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
    if (typeof g.nodeThreeObjectExtend === 'function') g.nodeThreeObjectExtend(false) // override default yellow nodes
    if (typeof g.refresh === 'function') g.refresh()
  }, [graphRef, nodeThreeObject, cleanData])

  const o
