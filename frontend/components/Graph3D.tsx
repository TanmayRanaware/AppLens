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

  const [CSS2D, setCSS2D] = useState<{ CSS2DRenderer: any; CSS2DObject: any } | null>(null)
  useEffect(() => {
    import('three/examples/jsm/renderers/CSS2DRenderer.js')
      .then(mod => setCSS2D({ CSS2DRenderer: mod.CSS2DRenderer, CSS2DObject: mod.CSS2DObject }))
      .catch(() => setCSS2D(null))
  }, [])

  // 🔸 SINGLE VARIABLE — update this to recolor BOTH nodes + labels
  const NODE_COLOR = '#ff8c00' // example: '#ff4c4c'(red), '#4a90e2'(blue), '#19b45b'(green)
  const NODE_COLOR_NUM = parseInt(NODE_COLOR.slice(1), 16)

  // Size
  const DIAMETER = 3.0
  const R = DIAMETER / 2

  // Force remount if color/size changes
  const graphKey = useMemo(() => {
    const n = (data?.nodes ?? []).length
    const l = (data?.links ?? []).length
    const STYLE = `unified_${NODE_COLOR}_d${DIAMETER}`
    return `g-${n}-${l}-${STYLE}`
  }, [data, NODE_COLOR, DIAMETER])

  // Custom node (unlit → exact color)
  const nodeThreeObject = useCallback((n: any) => {
    const group = new THREE.Group()

    const mat = new THREE.MeshBasicMaterial({ color: NODE_COLOR_NUM })
    ;(mat as any).toneMapped = false

    const sphere = new THREE.Mesh(new THREE.SphereGeometry(R, 32, 32), mat)
    ;(sphere.material as THREE.MeshBasicMaterial).color.set(NODE_COLOR_NUM)
    group.add(sphere)

    if (CSS2D?.CSS2DObject) {
      const el = document.createElement('div')
      el.textContent = String(n.name ?? n.id ?? '')
      el.style.cssText = `
        font-size:12px; line-height:1; padding:2px 6px; border-radius:6px;
        background:transparent !important;
        color:${NODE_COLOR} !important;
        -webkit-text-fill-color:${NODE_COLOR} !important;
        text-shadow:none !important;
        white-space:nowrap; user-select:none; pointer-events:none;
      `
      const label = new CSS2D.CSS2DObject(el)
      label.position.set(0, R * 2.2, 0)
      group.add(label)
    }

    return group
  }, [CSS2D, NODE_COLOR, NODE_COLOR_NUM])

  // Clean data (drop any incoming node.color)
  const cleanData = useMemo(() => {
    const nodes = (data?.nodes ?? []).map((n: any, i: number) => {
      const { color: _drop, ...rest } = n || {}
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

  // Helper: hard-override all mesh colors in the scene
  const forceSceneNodeColor = useCallback((gInst: any) => {
    const scene: THREE.Scene | undefined = gInst?.scene?.()
    if (!scene) return
    scene.traverse(obj => {
      const mesh = obj as any
      const mat = mesh?.material
      if (mesh?.isMesh && mat && mat.color) {
        mat.color.set(NODE_COLOR)
        if ('toneMapped' in mat) mat.toneMapped = false
      }
    })
  }, [NODE_COLOR])

  // Dispose helper (avoid stale materials)
  const disposeSceneObjects = useCallback((gInst: any) => {
    try {
      const scene: THREE.Scene | undefined = gInst?.scene?.()
      if (!scene) return
      scene.traverse(obj => {
        const mesh = obj as THREE.Mesh
        const mat: any = (mesh as any).material
        const geo: any = (mesh as any).geometry
        if (mat) {
          if (Array.isArray(mat)) mat.forEach(m => m?.dispose?.())
          else mat?.dispose?.()
        }
        geo?.dispose?.()
      })
    } catch {}
  }, [])

  // Force rebuild + hard color override
  useEffect(() => {
    const g = graphRef.current
    if (!g || !cleanData.nodes.length) return

    g.nodeThreeObject(nodeThreeObject)
    g.nodeThreeObjectExtend(false)

    disposeSceneObjects(g)
    g.graphData({ nodes: [], links: [] })
    requestAnimationFrame(() => {
      if (!graphRef.current) return
      graphRef.current.graphData(cleanData)
      // one more frame later, force-set colors on any mesh that slipped through
      requestAnimationFrame(() => forceSceneNodeColor(graphRef.current))
    })
  }, [nodeThreeObject, cleanData, disposeSceneObjects, forceSceneNodeColor])

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
        nodeLabel={() => ''}  // we render CSS2D labels ourselves
      />
    </div>
  )
})

export default Graph3D
