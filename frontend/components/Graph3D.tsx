'use client'

import { useRef, useEffect, useState, useCallback, forwardRef } from 'react'
import dynamic from 'next/dynamic'
import * as THREE from 'three'
import { RotateCcw, X, Check } from 'lucide-react'
import SpriteText from 'three-spritetext'

const ForceGraph3D = dynamic(() => import('react-force-graph-3d'), { ssr: false })

interface Graph3DProps {
  data: { nodes: any[]; links: any[] }
  highlightedNodes?: Set<string>  // Affected services (GOLDEN)
  highlightedLinks?: Set<string>  // Affected edges (RED)
  sourceNode?: string  // Source service where error occurred (RED)
  changedNodes?: Set<string>  // Changed services for what-if (RED)
  onNodeSelect?: (node: any) => void
  selectedNode?: any
}

const Graph3D = forwardRef<any, Graph3DProps>(({ 
  data, 
  highlightedNodes = new Set(),  // Affected services (GOLDEN)
  highlightedLinks = new Set(),  // Affected edges (RED)
  sourceNode,  // Source service where error occurred (RED)
  changedNodes = new Set(),  // Changed services for what-if (RED)
  onNodeSelect,
  selectedNode
}, ref) => {
  const fgRef = useRef<any>()
  const [focusedNode, setFocusedNode] = useState<any>(null)
  const [isReady, setIsReady] = useState(false)
  
  // Use forwarded ref or internal ref
  const graphRef = (ref as any) || fgRef

  useEffect(() => {
    if (graphRef.current && data && data.nodes && data.nodes.length > 0) {
      // Spread nodes out more to avoid dense ball
      // Increase charge strength (more negative = more repulsion)
      graphRef.current.d3Force('charge')?.strength(-300)
      
      // Increase link distance to space out connected nodes
      graphRef.current.d3Force('link')?.distance((link: any) => {
        // Calculate distance based on number of nodes (more nodes = more space)
        const baseDistance = 150
        const nodeCount = data.nodes.length
        // Scale distance based on node count
        return baseDistance + (nodeCount * 2)
      })
      
      // Add center force to keep graph centered in the left container
      // Position graph 70% from the right side (more to the left)
      graphRef.current.d3Force('center')?.strength(0.1)
      graphRef.current.d3Force('center')?.x(-300) // Shift center more to the left (70% from right)
      
      // Initialize camera position - zoomed in to 10% (closer = more zoomed in)
      // Calculate base distance, then reduce to 10% (multiply by 0.10)
      const baseDistance = Math.max(400, data.nodes.length * 3)
      const distance = baseDistance * 0.10 // 10% zoomed in
      // Position camera 70% from the right side
      graphRef.current.cameraPosition({ x: -300, y: 0, z: distance }, { x: -300, y: 0, z: 0 })
      
      // Auto-rotate like a globe (using orbit controls)
      // Wait a bit for the graph to initialize before accessing controls
      setTimeout(() => {
        if (graphRef.current) {
          try {
            const controls = (graphRef.current as any).controls()
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
  }, [data, graphRef])

  // Auto-color nodes by repo (like reference example)
  const getNodeColor = (node: any) => {
    const nodeId = String(node.id)
    
    // Check if we're in what-if mode (has changedNodes)
    const isWhatIfMode = changedNodes.size > 0
    
    // Changed services (what-if primary node) - BLUE
    if (changedNodes.has(nodeId)) {
      return '#00aaff' // Blue for changed services (primary node in what-if)
    }
    
    // Source service (where error occurred) - RED
    if (sourceNode && nodeId === String(sourceNode)) {
      return '#ff0000' // Red for source service
    }
    
    // Affected services: 
    // - In what-if mode: blast radius/risk hotspots are RED
    // - In error-analyzer mode: affected services are GOLDEN
    if (highlightedNodes.has(nodeId)) {
      if (isWhatIfMode) {
        return '#ff0000' // Red for blast radius in what-if mode
      } else {
        return '#ffd700' // Golden for affected services in error-analyzer mode
      }
    }
    
    // Selected node - gold
    if (selectedNode?.id === node.id) {
      return '#ffd700' // Gold for selected
    }
    
    // Default - green (unaffected services)
    return '#00ff00' // Green for default/unaffected nodes
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
    // Node size - very small size (0.1) so text is prominent
    // Minimal sphere, text labels are the main visual element
    return 0.1
  }

  // Link colors are handled by linkAutoColorBy

  const handleNodeClick = useCallback((node: any) => {
    setFocusedNode(node)
    if (onNodeSelect) {
      onNodeSelect(node)
    }
    // Focus camera on node (like reference)
    if (graphRef.current) {
      const distance = 90
      const distRatio = 1 + distance / Math.hypot(node.x || 0, node.y || 0, node.z || 0)
      graphRef.current.cameraPosition(
        {
          x: (node.x || 0) * distRatio,
          y: (node.y || 0) * distRatio,
          z: (node.z || 0) * distRatio
        },
        node,
        1000
      )
      // Pause auto-rotate when focusing on node
      const controls = (graphRef.current as any).controls()
      if (controls) {
        controls.autoRotate = false
      }
    }
  }, [onNodeSelect, graphRef])

  const handleResetView = () => {
    if (graphRef.current) {
      // Reset to left-offset position with 10% zoom (70% from right side)
      const baseDistance = Math.max(400, data.nodes.length * 3)
      const distance = baseDistance * 0.10 // 10% zoomed in
      graphRef.current.cameraPosition(
        { x: -300, y: 0, z: distance },
        { x: -300, y: 0, z: 0 },
        800
      )
      setFocusedNode(null)
      setIsReady(false)
      // Resume auto-rotate
      const controls = (graphRef.current as any)?.controls()
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
    
    // Debug: Check original node.name before cleaning
    if (Math.random() < 0.1) { // Log ~10% of nodes
      console.log('🔍 cleanNodes - Original node:', {
        originalName: node.name,
        originalNameType: typeof node.name,
        originalId: node.id,
        allKeys: Object.keys(node)
      })
    }
    
    // Preserve original name if it exists, otherwise use id
    const preservedName = node.name && String(node.name).trim() !== '' 
      ? String(node.name) 
      : (node.id ? String(node.id) : 'node')
    
    // Debug: Warn if name is being lost
    if (node.name && preservedName !== String(node.name)) {
      console.warn('⚠️ cleanNodes: Name changed!', {
        original: node.name,
        preserved: preservedName,
        node: node
      })
    }
    
    return {
      ...node,
      id: normalizedId,
      name: preservedName  // Use preserved name instead of always converting
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

  // Detect service pairs with both HTTP and KAFKA edges
  const edgeTypeMap = new Map<string, Set<string>>() // key: "source-target", value: Set of edge types
  
  cleanLinks.forEach((link: any) => {
    const sourceId = String(link.source)
    const targetId = String(link.target)
    const key = `${sourceId}-${targetId}`
    // Normalize edge type to uppercase (backend sends "HTTP" and "KAFKA")
    const edgeType = (link.kind || link.type || 'HTTP').toUpperCase()
    
    if (!edgeTypeMap.has(key)) {
      edgeTypeMap.set(key, new Set())
    }
    edgeTypeMap.get(key)!.add(edgeType)
  })
  
  // Mark links that are part of dual-connection pairs
  const cleanLinksWithDualFlag = cleanLinks.map((link: any) => {
    const sourceId = String(link.source)
    const targetId = String(link.target)
    const key = `${sourceId}-${targetId}`
    const edgeTypes = edgeTypeMap.get(key)
    
    // Check if both HTTP and KAFKA exist for this pair
    const hasBoth = edgeTypes && edgeTypes.has('HTTP') && edgeTypes.has('KAFKA')
    
    return {
      ...link,
      hasBothTypes: hasBoth || false
    }
  })

  const cleanData = {
    nodes: cleanNodes,
    links: cleanLinksWithDualFlag
  }

        // Debug: log data structure
        console.log('Graph data summary:', {
          originalNodes: data.nodes?.length || 0,
          originalLinks: data.links?.length || 0,
          cleanNodes: cleanData.nodes.length,
          cleanLinks: cleanData.links.length,
          sampleNode: cleanData.nodes[0],
          sampleLink: cleanData.links[0],
          sampleNodeKeys: cleanData.nodes[0] ? Object.keys(cleanData.nodes[0]) : [],
          sampleNodeName: cleanData.nodes[0]?.name,
          sampleNodeId: cleanData.nodes[0]?.id
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

  // Removed HTML label positioning - using green spheres for now

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

      {/* Removed HTML labels - using green spheres for now */}

      <ForceGraph3D
        ref={graphRef}
        graphData={cleanData}
        nodeAutoColorBy={(node: any) => node.group || node.repo || 'default'}
        nodeColor={getNodeColor} // Use getNodeColor function for highlighting
        nodeVal={0.1} // Very small green sphere
        linkColor={(link: any) => {
          // Highlighted links (from error analysis) - thicker and highlighted
          const sourceId = String(link.source?.id || link.source)
          const targetId = String(link.target?.id || link.target)
          const linkKey = `${sourceId}-${targetId}`
          const reverseLinkKey = `${targetId}-${sourceId}`
          
          // Check if this link is highlighted (either direction)
          const isHighlighted = highlightedLinks.has(linkKey) || highlightedLinks.has(reverseLinkKey) ||
                                (sourceId && highlightedNodes.has(sourceId)) ||
                                (targetId && highlightedNodes.has(targetId))
          
          if (isHighlighted) {
            return '#ff6b6b' // Red/orange for highlighted links
          }
          
          // Blue edges if both HTTP and KAFKA exist between the same services
          if (link.hasBothTypes) {
            return '#00aaff' // Blue color for dual connections (HTTP + KAFKA)
          }
          // White edges for HTTP, Golden edges for Kafka
          if (link.kind === 'Kafka' || link.type === 'Kafka' || link.kind === 'KAFKA' || link.type === 'KAFKA') {
            return '#ffd700' // Golden color for Kafka
          }
          return '#ffffff' // White color for HTTP
        }}
        linkWidth={(link: any) => {
          // Link width: highlighted links are thinner (0.1px) for subtle highlighting
          const sourceId = String(link.source?.id || link.source)
          const targetId = String(link.target?.id || link.target)
          const linkKey = `${sourceId}-${targetId}`
          const reverseLinkKey = `${targetId}-${sourceId}`
          
          const isHighlighted = highlightedLinks.has(linkKey) || highlightedLinks.has(reverseLinkKey) ||
                                (sourceId && highlightedNodes.has(sourceId)) ||
                                (targetId && highlightedNodes.has(targetId))
          return isHighlighted ? 0.1 : 0.2
        }}
        linkOpacity={0.6}
        backgroundColor="#000011"
        // Make nodeLabel always visible (not just on hover)
        showNavInfo={false}
        // Removed nodeThreeObject - using simple green spheres for now
        // Remove nodeLabel to avoid HTML labels interfering with 3D text
        nodeLabel={undefined}
        onNodeClick={handleNodeClick}
        // Force simulation settings for better spacing
        d3AlphaDecay={0.02}
        d3VelocityDecay={0.4}
        cooldownTicks={200} // More ticks for better layout
        onEngineStop={() => {
          if (graphRef.current && !isReady) {
            try {
              // Get graph bounding box to calculate center offset
              const bbox = graphRef.current.getGraphBbox()
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
              graphRef.current.cameraPosition(
                { x: lookAt.x, y: lookAt.y, z: lookAt.z + distance },
                lookAt,
                800
              )
              
              // Re-center after a short delay to ensure layout is stable
              setTimeout(() => {
                if (graphRef.current) {
                  const bbox2 = graphRef.current.getGraphBbox()
                  const centerX2 = (bbox2.x[0] + bbox2.x[1]) / 2
                  const centerY2 = (bbox2.y[0] + bbox2.y[1]) / 2
                  const centerZ2 = (bbox2.z[0] + bbox2.z[1]) / 2
                  const lookAt2 = { x: centerX2 + leftOffset, y: centerY2, z: centerZ2 }
                  // Use same 10% zoom distance
                  const baseDistance2 = Math.max(400, data.nodes.length * 3)
                  const distance2 = baseDistance2 * 0.10 // 10% zoomed in
                  graphRef.current.cameraPosition(
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
                graphRef.current.zoomToFit(800, 100)
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
})

Graph3D.displayName = 'Graph3D'

export default Graph3D

