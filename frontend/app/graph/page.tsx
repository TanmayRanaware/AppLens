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
  const [highlightedNodes, setHighlightedNodes] = useState<Set<string>>(new Set())
  const [highlightedLinks, setHighlightedLinks] = useState<Set<string>>(new Set())

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
        const repos = searchParams.get('repos')?.split(',').filter(Boolean) || []
        const params = repos.length > 0 ? { repos } : {}
        const response = await api.get('/graph', { params })
        setGraphData(response.data)
        setLoading(false)
      } catch (error) {
        console.error('Error loading graph:', error)
        setLoading(false)
      }
    }
    loadGraph()
  }, [searchParams])

  const handleHighlightNodes = useCallback((nodeIds: string[]) => {
    setHighlightedNodes(new Set(nodeIds))
  }, [])

  const handleHighlightLinks = useCallback((linkIds: string[]) => {
    setHighlightedLinks(new Set(linkIds))
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
        <div className="text-white text-xl">Loading graph...</div>
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
          onNodeSelect={handleNodeSelect}
          selectedNode={selectedNode}
        />
      </div>
      
      {/* Chat Section - Right (25%) */}
      <div className="border-l-2 border-slate-600 bg-slate-800" style={{ width: '25%', height: '100vh', flex: '0 0 25%', minWidth: '300px', maxWidth: '400px', overflow: 'hidden', position: 'relative', zIndex: 10, display: 'flex', flexDirection: 'column' }}>
        <ChatDock
          onHighlightNodes={handleHighlightNodes}
          onHighlightLinks={handleHighlightLinks}
          selectedNode={selectedNode}
          messages={messages}
          setMessages={setMessages}
        />
      </div>
    </div>
  )
}

