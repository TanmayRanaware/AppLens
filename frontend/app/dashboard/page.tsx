'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { Search, Plus, Play, Loader2, LogOut } from 'lucide-react'
import { api } from '@/lib/api'
import { logout } from '@/lib/auth'
import RepoPicker from '@/components/RepoPicker'

export default function DashboardPage() {
  const router = useRouter()
  const [selectedRepos, setSelectedRepos] = useState<string[]>([])
  const [manualRepo, setManualRepo] = useState('')
  const [isScanning, setIsScanning] = useState(false)
  const [scanId, setScanId] = useState<string | null>(null)

  useEffect(() => {
    // Check if user is authenticated
    const checkAuth = async () => {
      try {
        await api.get('/auth/me')
      } catch (error) {
        // Not authenticated, redirect to landing page
        router.push('/')
      }
    }
    checkAuth()
  }, [router])

  const handleAddManualRepo = () => {
    if (manualRepo.trim() && !selectedRepos.includes(manualRepo.trim())) {
      setSelectedRepos([...selectedRepos, manualRepo.trim()])
      setManualRepo('')
    }
  }

  const handleRemoveRepo = (repo: string) => {
    setSelectedRepos(selectedRepos.filter(r => r !== repo))
  }

  const handleStartScan = async () => {
    if (selectedRepos.length === 0) {
      alert('Please select at least one repository')
      return
    }

    setIsScanning(true)
    try {
      const response = await api.post('/scan/start', {
        repo_full_names: selectedRepos,
      })
      setScanId(response.data.scan_id)
      
      // Poll for scan completion
      const pollInterval = setInterval(async () => {
        try {
          const statusResponse = await api.get(`/scan/status/${response.data.scan_id}`)
          if (statusResponse.data.status === 'success') {
            clearInterval(pollInterval)
            setIsScanning(false)
            router.push(`/graph?scan_id=${response.data.scan_id}`)
          } else if (statusResponse.data.status === 'error') {
            clearInterval(pollInterval)
            setIsScanning(false)
            alert(`Scan failed: ${statusResponse.data.error}`)
          }
        } catch (error) {
          console.error('Error polling scan status:', error)
        }
      }, 2000)
    } catch (error: any) {
      console.error('Error starting scan:', error)
      alert(error.response?.data?.detail || 'Failed to start scan')
      setIsScanning(false)
    }
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900 p-8">
      <div className="max-w-6xl mx-auto">
        <div className="mb-8 flex justify-between items-start">
          <div>
            <h1 className="text-4xl font-bold text-white mb-2">Dashboard</h1>
            <p className="text-gray-300">Select repositories to scan for microservice dependencies</p>
          </div>
          <button
            onClick={logout}
            className="flex items-center gap-2 px-4 py-2 bg-red-600/20 hover:bg-red-600/30 text-red-400 border border-red-500/50 rounded-lg transition-colors"
          >
            <LogOut className="w-4 h-4" />
            Logout
          </button>
        </div>

        <div className="bg-white/10 backdrop-blur-lg rounded-lg p-6 border border-white/20 space-y-6">
          {/* Manual Repo Input */}
          <div>
            <label className="block text-sm font-medium text-white mb-2">
              Add Repository (format: owner/repo)
            </label>
            <div className="flex gap-2">
              <input
                type="text"
                value={manualRepo}
                onChange={(e) => setManualRepo(e.target.value)}
                onKeyPress={(e) => e.key === 'Enter' && handleAddManualRepo()}
                placeholder="e.g., facebook/react"
                className="flex-1 px-4 py-2 bg-white/10 border border-white/20 rounded-lg text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-primary-500"
              />
              <button
                onClick={handleAddManualRepo}
                className="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition-colors"
              >
                <Plus className="w-5 h-5" />
              </button>
            </div>
          </div>

          {/* Repo Picker */}
          <div>
            <label className="block text-sm font-medium text-white mb-2">
              Search Your Repositories
            </label>
            <RepoPicker
              onSelect={(repo) => {
                if (!selectedRepos.includes(repo)) {
                  setSelectedRepos([...selectedRepos, repo])
                }
              }}
            />
          </div>

          {/* Selected Repos */}
          {selectedRepos.length > 0 && (
            <div>
              <label className="block text-sm font-medium text-white mb-2">
                Selected Repositories ({selectedRepos.length})
              </label>
              <div className="flex flex-wrap gap-2">
                {selectedRepos.map((repo) => (
                  <div
                    key={repo}
                    className="flex items-center gap-2 px-3 py-1 bg-primary-600/20 border border-primary-500/50 rounded-lg text-white"
                  >
                    <span>{repo}</span>
                    <button
                      onClick={() => handleRemoveRepo(repo)}
                      className="text-red-400 hover:text-red-300"
                    >
                      ×
                    </button>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Scan Button */}
          <div className="pt-4">
            <button
              onClick={handleStartScan}
              disabled={selectedRepos.length === 0 || isScanning}
              className="w-full flex items-center justify-center gap-2 px-6 py-3 bg-primary-600 text-white rounded-lg font-semibold hover:bg-primary-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isScanning ? (
                <>
                  <Loader2 className="w-5 h-5 animate-spin" />
                  Scanning...
                </>
              ) : (
                <>
                  <Play className="w-5 h-5" />
                  Start Scan
                </>
              )}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}

