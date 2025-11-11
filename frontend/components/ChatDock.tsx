'use client'

import { useState, useRef, useEffect } from 'react'
import { Send, MessageSquare, AlertTriangle, Zap, Database } from 'lucide-react'
import { api } from '@/lib/api'

interface ChatDockProps {
  onHighlightNodes: (nodeIds: string[]) => void
  onHighlightLinks: (linkIds: string[]) => void
  selectedNode?: any
  messages: Array<{ role: 'user' | 'assistant'; content: string; timestamp: string }>
  setMessages: (messages: Array<{ role: 'user' | 'assistant'; content: string; timestamp: string }>) => void
}

type ToolMode = 'chat' | 'error-analyzer' | 'what-if' | 'nlq'

export default function ChatDock({ 
  onHighlightNodes, 
  onHighlightLinks,
  selectedNode,
  messages,
  setMessages
}: ChatDockProps) {
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [toolMode, setToolMode] = useState<ToolMode>('chat')
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  const handleSend = async () => {
    if (!input.trim() || loading) return

    const userMessage = input.trim()
    setInput('')
    
    // Add user message
    const newMessages = [...messages, {
      role: 'user' as const,
      content: userMessage,
      timestamp: new Date().toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' })
    }]
    setMessages(newMessages)

    setLoading(true)

    try {
      let response: any
      
      // Use explicit tool mode or auto-detect
      if (toolMode === 'error-analyzer' || (toolMode === 'chat' && (userMessage.toLowerCase().includes('error') || userMessage.toLowerCase().includes('log')))) {
        // Error Analyzer: user pastes a log → agent detects implicated services/edges
        response = await api.post('/chat/error-analyzer', { log_text: userMessage })
        if (response.data.affected_nodes) {
          onHighlightNodes(response.data.affected_nodes)
        }
        if (response.data.affected_links) {
          onHighlightLinks(response.data.affected_links)
        }
      } else if (toolMode === 'what-if' || (toolMode === 'chat' && (userMessage.toLowerCase().includes('what if') || userMessage.toLowerCase().includes('impact') || userMessage.toLowerCase().includes('change')))) {
        // What-If Simulator: user describes a pre-deployment change → agent predicts blast radius
        response = await api.post('/chat/what-if', { 
          repo: selectedNode?.repo || '',
          diff: userMessage,
        })
        if (response.data.predicted_impacted_nodes) {
          onHighlightNodes(response.data.predicted_impacted_nodes)
        }
      } else if (toolMode === 'nlq' || toolMode === 'chat') {
        // NLQ: Natural Language Query to DB
        response = await api.post('/nlq', { question: userMessage })
        if (response.data.graph_hints?.highlight_services) {
          onHighlightNodes(response.data.graph_hints.highlight_services)
        }
      }

      // Add assistant response
      const assistantMessage = {
        role: 'assistant' as const,
        content: response.data.reasoning || 
                 response.data.message || 
                 (response.data.results ? JSON.stringify(response.data.results, null, 2) : 'Analysis complete.'),
        timestamp: new Date().toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' })
      }
      
      setMessages([...newMessages, assistantMessage])
    } catch (error: any) {
      console.error('Error processing query:', error)
      const errorMessage = {
        role: 'assistant' as const,
        content: `Error: ${error.response?.data?.detail || error.message || 'Failed to process request'}`,
        timestamp: new Date().toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' })
      }
      setMessages([...newMessages, errorMessage])
    } finally {
      setLoading(false)
      inputRef.current?.focus()
    }
  }

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  const quickActions = [
    'Ask about available services',
    'Request dependency analysis',
    'Explore service connections'
  ]

  return (
    <div className="h-full flex flex-col bg-slate-800" style={{ width: '100%', height: '100%', minWidth: '300px', zIndex: 10, display: 'flex' }}>
      {/* Header */}
      <div className="p-4 border-b border-slate-700">
        <div className="flex items-center gap-2 mb-3">
          <div className="w-2 h-2 bg-green-500 rounded-full"></div>
          <h2 className="text-white font-semibold text-lg">AI Chat</h2>
        </div>
        
        {/* Tool Selection Tabs */}
        <div className="flex gap-2 mb-2">
          <button
            onClick={() => setToolMode('error-analyzer')}
            className={`flex-1 px-3 py-2 text-xs rounded border transition-colors flex items-center justify-center gap-1 ${
              toolMode === 'error-analyzer'
                ? 'bg-orange-600/80 text-white border-orange-500'
                : 'bg-slate-700/50 text-gray-300 border-slate-600 hover:bg-slate-700'
            }`}
            title="Error Analyzer: Paste logs to detect implicated services"
          >
            <AlertTriangle className="w-3 h-3" />
            Error Analyzer
          </button>
          <button
            onClick={() => setToolMode('what-if')}
            className={`flex-1 px-3 py-2 text-xs rounded border transition-colors flex items-center justify-center gap-1 ${
              toolMode === 'what-if'
                ? 'bg-purple-600/80 text-white border-purple-500'
                : 'bg-slate-700/50 text-gray-300 border-slate-600 hover:bg-slate-700'
            }`}
            title="What-If Simulator: Predict blast radius of changes"
          >
            <Zap className="w-3 h-3" />
            What-If
          </button>
          <button
            onClick={() => setToolMode('nlq')}
            className={`flex-1 px-3 py-2 text-xs rounded border transition-colors flex items-center justify-center gap-1 ${
              toolMode === 'nlq'
                ? 'bg-blue-600/80 text-white border-blue-500'
                : 'bg-slate-700/50 text-gray-300 border-slate-600 hover:bg-slate-700'
            }`}
            title="Natural Language Query: Ask questions about your graph"
          >
            <Database className="w-3 h-3" />
            NLQ
          </button>
        </div>
        
        {/* Tool Description */}
        <p className="text-gray-400 text-xs">
          {toolMode === 'error-analyzer' && 'Paste error logs to detect implicated services and edges'}
          {toolMode === 'what-if' && 'Describe changes to predict blast radius and risk hotspots'}
          {toolMode === 'nlq' && 'Ask questions about your microservice dependencies'}
          {toolMode === 'chat' && 'Ask questions about your microservice dependencies'}
        </p>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.map((message, index) => (
          <div
            key={index}
            className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
          >
            <div
              className={`max-w-[80%] rounded-lg px-4 py-2 ${
                message.role === 'user'
                  ? 'bg-orange-600/20 text-orange-200 border border-orange-500/30'
                  : 'bg-slate-700 text-white border border-slate-600'
              }`}
            >
              <div className="text-sm whitespace-pre-wrap">{message.content}</div>
              <div className={`text-xs mt-1 ${
                message.role === 'user' ? 'text-orange-300/60' : 'text-gray-400'
              }`}>
                {message.timestamp}
              </div>
            </div>
          </div>
        ))}

        {/* Quick Actions (show when no messages or after assistant message) */}
        {messages.length <= 1 && (
          <div className="space-y-2">
            {quickActions.map((action, index) => (
              <button
                key={index}
                onClick={() => {
                  setInput(action)
                  inputRef.current?.focus()
                }}
                className="w-full text-left px-4 py-2 bg-slate-700/50 hover:bg-slate-700 text-gray-300 text-sm rounded border border-slate-600 transition-colors"
              >
                {action}
              </button>
            ))}
          </div>
        )}

        {loading && (
          <div className="flex justify-start">
            <div className="bg-slate-700 text-white rounded-lg px-4 py-2 border border-slate-600">
              <div className="flex items-center gap-2">
                <div className="w-2 h-2 bg-white rounded-full animate-pulse"></div>
                <span className="text-sm">Thinking...</span>
              </div>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <div className="p-4 border-t border-slate-700">
        <div className="flex items-center gap-2">
          <input
            ref={inputRef}
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyPress={handleKeyPress}
            placeholder={
              toolMode === 'error-analyzer' 
                ? 'Paste error log here...' 
                : toolMode === 'what-if'
                ? 'Describe the change (file+diff or PR link)...'
                : toolMode === 'nlq'
                ? 'Ask: "Show services that call auth-service via POST"'
                : 'Ask about your services, dependencies, or request analysis...'
            }
            className="flex-1 px-4 py-2 bg-slate-900 border border-slate-600 rounded-lg text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-primary-500"
            disabled={loading}
          />
          <button
            onClick={handleSend}
            disabled={!input.trim() || loading}
            className="p-2 bg-primary-600 hover:bg-primary-700 text-white rounded-lg disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            <Send className="w-5 h-5" />
          </button>
        </div>
      </div>
    </div>
  )
}
