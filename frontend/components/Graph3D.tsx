'use client'

import { useRef, useEffect, useState, useCallback } from 'react'
import dynamic from 'next/dynamic'
import * as THREE from 'three'
import { RotateCcw, X, Check } from 'lucide-react'
import SpriteText from 'three-spritetext'

const ForceGraph3D = dynamic(() => import('react-force-graph-3d'), { ssr: false })

interface Graph3DProps {
  data: { nodes: any[]; links: any[] }
  highlightedNodes?: Set<string>
  highlightedLinks?: Set<string>
  onNodeSelect?: (node: any) => void
  selectedNode?: any
}

export default function Graph3D({ 
  data, 
  highlightedNodes = new Set(), 
  highlightedLinks = new Set(),
  onNodeSelect,
  selectedNode
}: Graph3DProps) {
  const fgRef = useRef<any>()
  const [focusedNode, setFocusedNode] = useState<any>(null)
  const [isReady, setIsReady] = useState(false)

  useEffect(() => {
    if (fgRef.current && data && data.nodes && data.nodes.length > 0) {
      // Spread nodes out more to avoid dense ball
      // Increase charge strength (more negative = more repulsion)
      fgRef.current.d3Force('charge')?.strength(-300)
      
      // Increase link distance to space out connected nodes
      fgRef.current.d3Force('link')?.distance((link: any) => {
        // Calculate distance based on number of nodes (more nodes = more space)
        const baseDistance = 150
        const nodeCount = data.nodes.length
        // Scale distance based on node count
        return baseDistance + (nodeCount * 2)
      })
      
      // Add center force to keep graph centered in the left container
      // Position graph 70% from the right side (more to the left)
      fgRef.current.d3Force('center')?.strength(0.1)
      fgRef.current.d3Force('center')?.x(-300) // Shift center more to the left (70% from right)
      
      // Initialize camera position - zoomed in to 10% (closer = more zoomed in)
      // Calculate base distance, then reduce to 10% (multiply by 0.10)
      const baseDistance = Math.max(400, data.nodes.length * 3)
      const distance = baseDistance * 0.10 // 10% zoomed in
      // Position camera 70% from the right side
      fgRef.current.cameraPosition({ x: -300, y: 0, z: distance }, { x: -300, y: 0, z: 0 })
      
      // Auto-rotate like a globe (using orbit controls)
      // Wait a bit for the graph to initialize before accessing controls
      setTimeout(() => {
        if (fgRef.current) {
          try {
            const controls = (fgRef.current as any).controls()
            if (controls && typeof controls.autoRotate !== 'undefined') {
              controls.autoRotate = true
              controls.autoRotateSpeed = 1.0 // Tweak speed (0.5–2 feels good)
            }
          } catch (error) {
            console.warn('Could not set auto-rotate:', error)
          }
        }
      }, 200)
    }
  }, [data])

  // Auto-color nodes by repo (like reference example)
  const getNodeColor = (node: any) => {
    if (selectedNode?.id === node.id) {
      return '#ffd700' // Gold for selected
    }
    if (highlightedNodes.has(node.id)) {
      return '#ff4444' // Red for highlighted
    }
    // Auto-color by repo (hash-based) - this will be used by nodeAutoColorBy
    const hash = node.repo?.split('').reduce((acc: number, char: string) => acc + char.charCodeAt(0), 0) || 0
    const hue = hash % 360
    return `hsl(${hue}, 70%, 60%)`
  }

  const getNodeTextColor = (node: any) => {
    if (selectedNode?.id === node.id) {
      return '#ffd700' // Bright gold/yellow for selected (like reference)
    }
    if (highlightedNodes.has(node.id)) {
      return '#ff4444' // Bright red for highlighted (like reference)
    }
    // Use node color for text (auto-colored by repo)
    return getNodeColor(node)
  }

  const getNodeSize = (node: any) => {
    // Node size - consistent small size (like text-nodes example)
    // Small spheres so text is prominent
    return 4
  }

  // Link colors are handled by linkAutoColorBy

  const handleNodeClick = useCallback((node: any) => {
    setFocusedNode(node)
    if (onNodeSelect) {
      onNodeSelect(node)
    }
    // Focus camera on node (like reference)
    if (fgRef.current) {
      const distance = 90
      const distRatio = 1 + distance / Math.hypot(node.x || 0, node.y || 0, node.z || 0)
      fgRef.current.cameraPosition(
        {
          x: (node.x || 0) * distRatio,
          y: (node.y || 0) * distRatio,
          z: (node.z || 0) * distRatio
        },
        node,
        1000
      )
      // Pause auto-rotate when focusing on node
      const controls = (fgRef.current as any).controls()
      if (controls) {
        controls.autoRotate = false
      }
    }
  }, [onNodeSelect])

  const handleResetView = () => {
    if (fgRef.current) {
      // Reset to left-offset position with 10% zoom (70% from right side)
      const baseDistance = Math.max(400, data.nodes.length * 3)
      const distance = baseDistance * 0.10 // 10% zoomed in
      fgRef.current.cameraPosition(
        { x: -300, y: 0, z: distance },
        { x: -300, y: 0, z: 0 },
        800
      )
      setFocusedNode(null)
      setIsReady(false)
      // Resume auto-rotate
      const controls = (fgRef.current as any)?.controls()
      if (controls) {
        controls.autoRotate = true
      }
    }
  }

  const handleRemoveFocus = () => {
    setFocusedNode(null)
    if (onNodeSelect) {
      onNodeSelect(null)
    }
  }

  // Don't render if no data
  if (!data || !data.nodes || data.nodes.length === 0) {
    return (
      <div className="w-full h-full flex items-center justify-center" style={{ background: '#000011' }}>
        <div className="text-white text-lg">Loading graph data...</div>
      </div>
    )
  }

  // Validate and clean graph data
  const nodeIdMap = new Map<string, string>()
  const cleanNodes = (data.nodes || []).filter((node: any) => {
    // Ensure node has required properties
    if (!node || (node.id === undefined && node.name === undefined)) {
      return false
    }
    return true
  }).map((node: any) => {
    const originalId = node.id || node.name
    const normalizedId = String(originalId)
    nodeIdMap.set(String(originalId), normalizedId)
    return {
      ...node,
      id: normalizedId,
      name: String(node.name || node.id || 'node')
    }
  })

  const cleanLinks = (data.links || []).filter((link: any) => {
    if (!link) return false
    
    // Get source and target IDs
    const sourceId = link.source?.id || link.source
    const targetId = link.target?.id || link.target
    
    // Check if both source and target exist in nodes
    if (sourceId === undefined || targetId === undefined) {
      return false
    }
    
    const sourceExists = nodeIdMap.has(String(sourceId))
    const targetExists = nodeIdMap.has(String(targetId))
    
    return sourceExists && targetExists
  }).map((link: any) => {
    const sourceId = link.source?.id || link.source
    const targetId = link.target?.id || link.target
    
    return {
      ...link,
      source: nodeIdMap.get(String(sourceId)) || String(sourceId),
      target: nodeIdMap.get(String(targetId)) || String(targetId)
    }
  })

  const cleanData = {
    nodes: cleanNodes,
    links: cleanLinks
  }

  // Debug: log data structure
  console.log('Graph data summary:', {
    originalNodes: data.nodes?.length || 0,
    originalLinks: data.links?.length || 0,
    cleanNodes: cleanData.nodes.length,
    cleanLinks: cleanData.links.length,
    sampleNode: cleanData.nodes[0],
    sampleLink: cleanData.links[0]
  })

  // Debug: log if data is empty
  if (cleanData.nodes.length === 0) {
    console.error('No valid nodes in graph data:', data)
    return (
      <div className="w-full h-full flex items-center justify-center" style={{ background: '#000011' }}>
        <div className="text-white text-lg">No graph data available</div>
      </div>
    )
  }
  if (cleanData.links.length === 0 && data.links && data.links.length > 0) {
    console.warn('No valid links in graph data (filtered out):', data.links)
  }

  return (
    <div id="graph-container" className="relative" style={{ width: '100%', height: '100%', background: '#000011' }}>
      {/* Control Buttons */}
      <div className="absolute top-4 left-4 z-10 flex gap-2">
          <button
            onClick={handleResetView}
            className="px-3 py-2 bg-black/60 backdrop-blur-sm hover:bg-black/80 text-white text-sm rounded border border-white/20 flex items-center gap-2 transition-colors"
          >
            <RotateCcw className="w-4 h-4" />
            Reset View
          </button>
          {focusedNode && (
            <button
              onClick={handleRemoveFocus}
              className="px-3 py-2 bg-black/60 backdrop-blur-sm hover:bg-black/80 text-white text-sm rounded border border-white/20 flex items-center gap-2 transition-colors"
            >
              <X className="w-4 h-4" />
              Remove Focus
            </button>
          )}
          <button
            onClick={() => setIsReady(!isReady)}
            className={`px-3 py-2 text-sm rounded border flex items-center gap-2 transition-colors ${
              isReady
                ? 'bg-green-600/80 hover:bg-green-700/80 text-white border-green-500'
                : 'bg-black/60 backdrop-blur-sm hover:bg-black/80 text-white border-white/20'
            }`}
          >
            <Check className="w-4 h-4" />
            Ready
          </button>
      </div>

      {/* Interaction Hint */}
      <div className="absolute bottom-4 left-1/2 transform -translate-x-1/2 z-10 bg-black/60 backdrop-blur-sm text-white text-xs px-3 py-2 rounded border border-white/20">
        Left-click: rotate, Mouse-wheel/middle-click: zoom, Right-click: pan
      </div>

      <ForceGraph3D
        ref={fgRef}
        graphData={cleanData}
        nodeAutoColorBy={(node: any) => node.group || node.repo || 'default'}
        nodeColor={getNodeColor}
        nodeVal={getNodeSize}
        linkColor={() => '#ffffff'}
        linkWidth={0.2}
        linkOpacity={0.6}
        backgroundColor="#000011"
        // Text nodes above nodes (like reference example)
        nodeThreeObject={(node: any) => {
          // Use SpriteText from three-spritetext (exactly like reference example)
          if (!node || (!node.name && !node.id)) {
            return null
          }
          try {
            const sprite = new SpriteText(node.name || node.id)
            sprite.material.depthWrite = false // Make sprite background transparent
            sprite.color = node.color || '#ffffff' // Use auto-colored node color
            sprite.textHeight = 8
            sprite.center.y = -0.6 // Shift text above node (exactly like reference)
            return sprite
          } catch (error) {
            console.error('Error creating SpriteText:', error, node)
            return null
          }
        }}
        nodeThreeObjectExtend={true} // Keep the node sphere AND add text (like reference)
        onNodeClick={handleNodeClick}
        // Force simulation settings for better spacing
        d3Force="link"
        d3AlphaDecay={0.02}
        d3VelocityDecay={0.4}
        cooldownTicks={200} // More ticks for better layout
        onEngineStop={() => {
          if (fgRef.current && !isReady) {
            try {
              // Get graph bounding box to calculate center offset
              const bbox = fgRef.current.getGraphBbox()
              const centerX = (bbox.x[0] + bbox.x[1]) / 2
              const centerY = (bbox.y[0] + bbox.y[1]) / 2
              const centerZ = (bbox.z[0] + bbox.z[1]) / 2
              
              // Offset center to the left - 70% from the right side
              const leftOffset = -300 // Position 70% from right side
              const lookAt = { x: centerX + leftOffset, y: centerY, z: centerZ }
              
              // Position camera to the left and look at the offset center
              // Zoom in to 10% (reduce distance to 10% of base)
              const baseDistance = Math.max(400, data.nodes.length * 3)
              const distance = baseDistance * 0.10 // 10% zoomed in
              fgRef.current.cameraPosition(
                { x: lookAt.x, y: lookAt.y, z: lookAt.z + distance },
                lookAt,
                800
              )
              
              // Re-center after a short delay to ensure layout is stable
              setTimeout(() => {
                if (fgRef.current) {
                  const bbox2 = fgRef.current.getGraphBbox()
                  const centerX2 = (bbox2.x[0] + bbox2.x[1]) / 2
                  const centerY2 = (bbox2.y[0] + bbox2.y[1]) / 2
                  const centerZ2 = (bbox2.z[0] + bbox2.z[1]) / 2
                  const lookAt2 = { x: centerX2 + leftOffset, y: centerY2, z: centerZ2 }
                  // Use same 10% zoom distance
                  const baseDistance2 = Math.max(400, data.nodes.length * 3)
                  const distance2 = baseDistance2 * 0.10 // 10% zoomed in
                  fgRef.current.cameraPosition(
                    { x: lookAt2.x, y: lookAt2.y, z: lookAt2.z + distance2 },
                    lookAt2,
                    800
                  )
                }
              }, 500)
              
              setIsReady(true)
            } catch (error) {
              console.warn('Error in camera positioning:', error)
              // Fallback to simple zoomToFit
              try {
                fgRef.current.zoomToFit(800, 100)
              } catch (e) {
                console.warn('Error in zoomToFit:', e)
              }
            }
          }
        }}
        // Remove flowing particles - make it static like a network grid
        linkDirectionalParticles={0}
      />
    </div>
  )
}

