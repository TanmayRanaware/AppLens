'use client'

import { useState, useEffect, useCallback } from 'react'
import { useSearchParams, useRouter } from 'next/navigation'
import dynamic from 'next/dynamic'
import Graph3D from '@/components/Graph3D'
import ChatDock from '@/components/ChatDock'
import { api } from '@/lib/api'

const ForceGraph3D = dynamic(() => import('react-force-graph-3d'), { ssr: false })

export default function GraphPage() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const [graphData, setGraphData] = useState<{ nodes: any[]; links: any[] }>({ nodes: [], links: [] })
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [highlightedNodes, setHighlightedNodes] = useState<Set<string>>(new Set())  // Affected services (GOLDEN)
  const [highlightedLinks, setHighlightedLinks] = useState<Set<string>>(new Set())  // Affected edges (RED)
  const [sourceNode, setSourceNode] = useState<string | undefined>(undefined)  // Source service (RED)
  const [changedNodes, setChangedNodes] = useState<Set<string>>(new Set())  // Changed services for what-if (RED)

  useEffect(() => {
    // Check if user is authenticated
    const checkAuth = async () => {
      try {
        await api.get('/auth/me')
      } catch (error) {
        // Not authenticated, redirect to landing page
        router.push('/')
        return
      }
    }
    checkAuth()
  }, [router])

  useEffect(() => {
    const loadGraph = async () => {
      try {
        const scanId = searchParams.get('scan_id')
        const repos = searchParams.get('repos')?.split(',').filter(Boolean) || []
        
        // Build params: prioritize scan_id if provided, otherwise use repos
        const params: any = {}
        if (scanId) {
          params.scan_id = scanId
        } else if (repos.length > 0) {
          params.repos = repos
        }
        
        console.log('🔍 Loading graph with params:', params)
        const response = await api.get('/graph', { params })
        console.log('📊 Graph API Response:', {
          nodesCount: response.data?.nodes?.length || 0,
          linksCount: response.data?.links?.length || 0,
          sampleNode: response.data?.nodes?.[0],
          sampleNodeKeys: response.data?.nodes?.[0] ? Object.keys(response.data.nodes[0]) : [],
          sampleNodeName: response.data?.nodes?.[0]?.name,
          sampleNodeNameType: typeof response.data?.nodes?.[0]?.name,
          allNodes: response.data?.nodes?.map((n: any) => ({ id: n.id, name: n.name, hasName: 'name' in n }))
        })
        
        // Always set graph data (even if empty) and stop loading
        const data = response.data || { nodes: [], links: [] }
        setGraphData(data)
        setLoading(false)
        setError(null)
        
        // Log if graph is empty
        if (data.nodes.length === 0 && data.links.length === 0) {
          console.warn('⚠️ Graph is empty - no nodes or links found')
          setError('No graph data found. The scan may not have completed or may not contain any services.')
        }
      } catch (error: any) {
        console.error('❌ Error loading graph:', error)
        console.error('Error details:', {
          message: error.message,
          response: error.response?.data,
          status: error.response?.status,
          statusText: error.response?.statusText
        })
        
        // Set empty graph and stop loading on error
        setGraphData({ nodes: [], links: [] })
        setLoading(false)
        
        // Set user-friendly error message
        let errorMessage = 'Failed to load graph'
        if (error.response?.status === 404) {
          errorMessage = 'Scan not found. Please check the scan ID or start a new scan.'
        } else if (error.response?.status === 401) {
          errorMessage = 'Authentication required. Please sign in again.'
          router.push('/')
          return
        } else if (error.response?.data?.detail) {
          errorMessage = error.response.data.detail
        } else if (error.message) {
          errorMessage = error.message
        }
        
        setError(errorMessage)
        alert(errorMessage)
      }
    }
    loadGraph()
  }, [searchParams, router])

  const handleHighlightNodes = useCallback((nodeIds: string[]) => {
    setHighlightedNodes(new Set(nodeIds))
  }, [])

  const handleHighlightLinks = useCallback((linkIds: string[]) => {
    setHighlightedLinks(new Set(linkIds))
  }, [])

  const handleSourceNode = useCallback((nodeId: string | undefined) => {
    setSourceNode(nodeId)
  }, [])

  const handleChangedNodes = useCallback((nodeIds: string[]) => {
    setChangedNodes(new Set(nodeIds))
  }, [])

  const [selectedNode, setSelectedNode] = useState<any>(null)
  const [messages, setMessages] = useState<Array<{ role: 'user' | 'assistant'; content: string; timestamp: string }>>([
    {
      role: 'assistant',
      content: 'Connected to CrewAI Chat! I can help you explore and analyze your microservice dependencies.',
      timestamp: new Date().toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' })
    }
  ])

  const handleNodeSelect = useCallback((node: any) => {
    setSelectedNode(node)
    if (node) {
      setMessages(prev => [...prev, {
        role: 'user',
        content: `You selected "${node.name}". You can ask me questions about this service or its dependencies.`,
        timestamp: new Date().toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' })
      }])
    }
  }, [])

  if (loading) {
    return (
      <div className="h-screen flex items-center justify-center bg-slate-900">
        <div className="text-white text-xl">Loading graph data...</div>
      </div>
    )
  }
  
  if (error) {
    return (
      <div className="h-screen flex items-center justify-center bg-slate-900">
        <div className="text-white text-center max-w-2xl p-8">
          <h2 className="text-2xl font-bold mb-4 text-red-400">Error Loading Graph</h2>
          <p className="text-lg mb-4">{error}</p>
          <button
            onClick={() => {
              setError(null)
              setLoading(true)
              const scanId = searchParams.get('scan_id')
              const repos = searchParams.get('repos')?.split(',').filter(Boolean) || []
              const params: any = {}
              if (scanId) params.scan_id = scanId
              else if (repos.length > 0) params.repos = repos
              api.get('/graph', { params })
                .then((response) => {
                  setGraphData(response.data || { nodes: [], links: [] })
                  setLoading(false)
                  setError(null)
                })
                .catch((err) => {
                  setLoading(false)
                  setError(err.response?.data?.detail || err.message || 'Failed to load graph')
                })
            }}
            className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
          >
            Retry
          </button>
        </div>
      </div>
    )
  }
  
  if (graphData.nodes.length === 0 && graphData.links.length === 0) {
    return (
      <div className="h-screen flex items-center justify-center bg-slate-900">
        <div className="text-white text-center max-w-2xl p-8">
          <h2 className="text-2xl font-bold mb-4">No Graph Data</h2>
          <p className="text-lg mb-4">
            The scan did not produce any graph data. This could mean:
          </p>
          <ul className="text-left list-disc list-inside space-y-2 mb-4">
            <li>The scan is still in progress</li>
            <li>The scan completed but found no services</li>
            <li>The repositories didn't contain detectable microservices</li>
          </ul>
          <button
            onClick={() => router.push('/dashboard')}
            className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
          >
            Go to Dashboard
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="h-screen flex overflow-hidden" style={{ background: '#000000', width: '100vw', position: 'relative' }}>
      {/* Graph Section - Left (75%) */}
      <div className="relative" style={{ width: '75%', height: '100vh', flex: '0 0 75%', overflow: 'hidden' }}>
        <Graph3D
          data={graphData}
          highlightedNodes={highlightedNodes}
          highlightedLinks={highlightedLinks}
          sourceNode={sourceNode}
          changedNodes={changedNodes}
          onNodeSelect={handleNodeSelect}
          selectedNode={selectedNode}
        />
      </div>
      
      {/* Chat Section - Right (25%) */}
      <div className="border-l-2 border-slate-600 bg-slate-800" style={{ width: '25%', height: '100vh', flex: '0 0 25%', minWidth: '300px', maxWidth: '400px', overflow: 'hidden', position: 'relative', zIndex: 10, display: 'flex', flexDirection: 'column' }}>
        <ChatDock
          onHighlightNodes={handleHighlightNodes}
          onHighlightLinks={handleHighlightLinks}
          onSourceNode={handleSourceNode}
          onChangedNodes={handleChangedNodes}
          selectedNode={selectedNode}
          messages={messages}
          setMessages={setMessages}
        />
      </div>
    </div>
  )
}

