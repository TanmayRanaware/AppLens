'use client'

import { useState, useEffect } from 'react'
import Link from 'next/link'
import { api } from '@/lib/api'

interface CoverageData {
  total: {
    lines: { pct: number; covered: number; skipped: number; total: number }
    statements: { pct: number; covered: number; skipped: number; total: number }
    functions: { pct: number; covered: number; skipped: number; total: number }
    branches: { pct: number; covered: number; skipped: number; total: number }
  }
  files: Array<{
    file: string
    lines: { pct: number; covered: number; skipped: number; total: number }
    statements: { pct: number; covered: number; skipped: number; total: number }
    functions: { pct: number; covered: number; skipped: number; total: number }
    branches: { pct: number; covered: number; skipped: number; total: number }
  }>
}

const DonutChart = ({ percentage, size = 120 }: { percentage: number, size?: number }) => {
  const radius = (size - 8) / 2
  const circumference = 2 * Math.PI * radius
  const strokeDasharray = `${(percentage / 100) * circumference} ${circumference}`
  
  const getColor = (pct: number) => {
    if (pct >= 90) return '#10b981'
    if (pct >= 80) return '#f59e0b'
    if (pct >= 70) return '#f97316'
    return '#ef4444'
  }
  
  return (
    <div className="relative" style={{ width: size, height: size }}>
      <svg width={size} height={size} className="transform -rotate-90">
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          stroke="rgb(71 85 105)"
          strokeWidth="8"
          fill="transparent"
        />
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          stroke={getColor(percentage)}
          strokeWidth="8"
          fill="transparent"
          strokeDasharray={strokeDasharray}
          strokeLinecap="round"
          className="transition-all duration-1000"
        />
      </svg>
      <div className="absolute inset-0 flex items-center justify-center">
        <div className="text-center">
          <div className="text-lg font-bold text-white">{percentage.toFixed(1)}%</div>
          <div className="text-xs text-slate-400">Total</div>
        </div>
      </div>
    </div>
  )
}

export default function BackendCoveragePage() {
  const [coverageData, setCoverageData] = useState<CoverageData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [usingMockData, setUsingMockData] = useState(false)

  const getMockCoverageData = (): CoverageData => {
    return {
      total: {
        lines: { pct: 68.4, covered: 342, skipped: 23, total: 500 },
        statements: { pct: 71.2, covered: 368, skipped: 15, total: 517 },
        functions: { pct: 65.8, covered: 87, skipped: 8, total: 132 },
        branches: { pct: 58.7, covered: 145, skipped: 12, total: 247 }
      },
      files: [
        {
          file: 'app/routes/graph.py',
          lines: { pct: 89.5, covered: 76, skipped: 2, total: 85 },
          statements: { pct: 91.2, covered: 73, skipped: 1, total: 80 },
          functions: { pct: 85.7, covered: 18, skipped: 1, total: 21 },
          branches: { pct: 82.1, covered: 32, skipped: 2, total: 39 }
        },
        {
          file: 'app/utils/performance.py',
          lines: { pct: 94.1, covered: 64, skipped: 1, total: 68 },
          statements: { pct: 95.5, covered: 63, skipped: 0, total: 66 },
          functions: { pct: 90.9, covered: 20, skipped: 0, total: 22 },
          branches: { pct: 87.5, covered: 28, skipped: 1, total: 32 }
        },
        {
          file: 'app/db/models.py',
          lines: { pct: 78.9, covered: 45, skipped: 3, total: 57 },
          statements: { pct: 80.6, covered: 43, skipped: 2, total: 53 },
          functions: { pct: 75.0, covered: 12, skipped: 2, total: 16 },
          branches: { pct: 71.4, covered: 25, skipped: 3, total: 35 }
        },
        {
          file: 'app/auth/github_oauth.py',
          lines: { pct: 72.5, covered: 29, skipped: 4, total: 40 },
          statements: { pct: 74.4, covered: 32, skipped: 3, total: 43 },
          functions: { pct: 70.0, covered: 7, skipped: 2, total: 10 },
          branches: { pct: 66.7, covered: 12, skipped: 3, total: 18 }
        },
        {
          file: 'app/services/graph_builder.py',
          lines: { pct: 45.2, covered: 19, skipped: 8, total: 42 },
          statements: { pct: 48.6, covered: 17, skipped: 6, total: 35 },
          functions: { pct: 42.9, covered: 6, skipped: 3, total: 14 },
          branches: { pct: 38.5, covered: 10, skipped: 5, total: 26 }
        },
        {
          file: 'app/agents/error_agent.py',
          lines: { pct: 23.8, covered: 10, skipped: 12, total: 42 },
          statements: { pct: 26.5, covered: 9, skipped: 10, total: 34 },
          functions: { pct: 20.0, covered: 2, skipped: 4, total: 10 },
          branches: { pct: 18.2, covered: 4, skipped: 7, total: 22 }
        },
        {
          file: 'app/services/scan_pipeline.py',
          lines: { pct: 56.8, covered: 21, skipped: 6, total: 37 },
          statements: { pct: 60.0, covered: 18, skipped: 5, total: 30 },
          functions: { pct: 53.3, covered: 8, skipped: 2, total: 15 },
          branches: { pct: 47.1, covered: 8, skipped: 4, total: 17 }
        },
        {
          file: 'app/routes/chat.py',
          lines: { pct: 84.6, covered: 33, skipped: 2, total: 39 },
          statements: { pct: 86.5, covered: 32, skipped: 1, total: 37 },
          functions: { pct: 81.3, covered: 13, skipped: 1, total: 16 },
          branches: { pct: 78.6, covered: 11, skipped: 2, total: 14 }
        }
      ]
    }
  }

  useEffect(() => {
    const fetchCoverage = async () => {
      try {
        console.log('Fetching backend coverage data...')
        const response = await api.get('/api/coverage')
        console.log('Coverage response:', response.data)
        setCoverageData(response.data)
        setUsingMockData(false)
        setLoading(false)
      } catch (err) {
        console.error('Error fetching coverage, falling back to mock data:', err)
        const mockData = getMockCoverageData()
        setCoverageData(mockData)
        setUsingMockData(true)
        setError('Using demo data - backend coverage API not available')
        setLoading(false)
      }
    }

    fetchCoverage()
  }, [])

  const getCoverageColor = (percentage: number) => {
    if (percentage >= 90) return 'text-green-400'
    if (percentage >= 80) return 'text-yellow-400'
    if (percentage >= 70) return 'text-orange-400'
    return 'text-red-400'
  }

  const getCoverageBarColor = (percentage: number) => {
    if (percentage >= 90) return 'bg-green-500'
    if (percentage >= 80) return 'bg-yellow-500'
    if (percentage >= 70) return 'bg-orange-500'
    return 'bg-red-500'
  }

  const getCategoryColor = (filePath: string) => {
    if (filePath.includes('routes')) return 'bg-blue-600'
    if (filePath.includes('agents')) return 'bg-purple-600'
    if (filePath.includes('services')) return 'bg-green-600'
    if (filePath.includes('utils')) return 'bg-orange-600'
    if (filePath.includes('db') || filePath.includes('models')) return 'bg-indigo-600'
    if (filePath.includes('auth')) return 'bg-red-600'
    return 'bg-gray-600'
  }

  const getCategoryLabel = (filePath: string) => {
    if (filePath.includes('routes')) return 'API Routes'
    if (filePath.includes('agents')) return 'AI Agents'
    if (filePath.includes('services')) return 'Services'
    if (filePath.includes('utils')) return 'Utilities'
    if (filePath.includes('db') || filePath.includes('models')) return 'Database'
    if (filePath.includes('auth')) return 'Authentication'
    return 'Other'
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-slate-900 text-white p-8">
        <div className="max-w-7xl mx-auto">
          <div className="flex items-center justify-center h-64">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500"></div>
            <span className="ml-3 text-lg">Loading backend coverage data...</span>
          </div>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="min-h-screen bg-slate-900 text-white p-8">
        <div className="max-w-7xl mx-auto">
          <div className="text-center">
            <h2 className="text-2xl font-bold text-red-400 mb-4">Error Loading Coverage</h2>
            <p className="text-lg mb-4">{error}</p>
            <button
              onClick={() => window.location.reload()}
              className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
            >
              Retry
            </button>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-slate-900 text-white p-8">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-3xl font-bold mb-2">Backend Test Coverage</h1>
              <p className="text-slate-400">
                Python/Pytest code coverage analysis for AppLens backend
                {usingMockData && (
                  <span className="ml-2 px-2 py-1 bg-yellow-600/20 text-yellow-400 text-xs rounded">
                    Demo Data
                  </span>
                )}
              </p>
            </div>
            <div className="flex items-center gap-3">
              <Link
                href="/coverage"
                className="px-4 py-2 bg-blue-600/20 hover:bg-blue-600/30 text-blue-400 border border-blue-500/50 rounded-lg transition-colors flex items-center gap-2"
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                </svg>
                Frontend Coverage
              </Link>
              <Link
                href="/dashboard"
                className="px-4 py-2 bg-slate-700 hover:bg-slate-600 text-white rounded-lg transition-colors flex items-center gap-2"
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 19l-7-7m0 0l7-7m-7 7h18" />
                </svg>
                Back to Dashboard
              </Link>
            </div>
          </div>
        </div>

        {/* Overall Coverage Summary */}
        {coverageData && (
          <div className="mb-8">
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-xl font-semibold">Overall Coverage</h2>
              <div className="flex items-center gap-2 text-sm text-slate-400">
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg>
                <span>Last updated: {new Date().toLocaleString()}</span>
              </div>
            </div>
            
            {/* Main coverage overview with donut chart */}
            <div className="bg-slate-800 rounded-lg p-6 mb-6">
              <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 items-center">
                <div className="flex justify-center">
                  <DonutChart percentage={coverageData.total.lines.pct} />
                </div>
                <div className="lg:col-span-2">
                  <h3 className="text-lg font-semibold mb-4">Coverage Summary</h3>
                  <div className="grid grid-cols-2 gap-4">
                    <div className="text-center p-4 bg-slate-700 rounded-lg">
                      <div className={`text-2xl font-bold ${getCoverageColor(coverageData.total.lines.pct)}`}>
                        {coverageData.total.lines.pct.toFixed(1)}%
                      </div>
                      <div className="text-sm text-slate-400 mt-1">Lines Covered</div>
                      <div className="text-xs text-slate-500 mt-1">
                        {coverageData.total.lines.covered} of {coverageData.total.lines.total}
                      </div>
                    </div>
                    <div className="text-center p-4 bg-slate-700 rounded-lg">
                      <div className="text-2xl font-bold text-blue-400">
                        {coverageData.files.length}
                      </div>
                      <div className="text-sm text-slate-400 mt-1">Files Analyzed</div>
                      <div className="text-xs text-slate-500 mt-1">
                        {coverageData.files.filter(f => f.lines.pct >= 80).length} well tested
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            {/* Detailed breakdown cards */}
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
              {[
                { key: 'lines', label: 'Code Lines', icon: '📄' },
                { key: 'statements', label: 'Statements', icon: '📝' },
                { key: 'functions', label: 'Functions', icon: '⚡' },
                { key: 'branches', label: 'Branches', icon: '🔀' }
              ].map(({ key, label, icon }) => {
                const data = coverageData.total[key as keyof typeof coverageData.total]
                
                return (
                  <div key={key} className="bg-slate-800 rounded-lg p-4 hover:bg-slate-750 transition-colors">
                    <div className="flex items-center justify-between mb-3">
                      <span className="text-2xl">{icon}</span>
                      <div className="px-2 py-1 rounded text-xs font-medium text-slate-400 bg-slate-700">
                        {label}
                      </div>
                    </div>
                    <div className={`text-xl font-bold ${getCoverageColor(data.pct)} mb-2`}>
                      {data.pct.toFixed(1)}%
                    </div>
                    <div className="space-y-2">
                      <div className="w-full bg-slate-700 rounded-full h-2">
                        <div
                          className={`h-2 rounded-full ${getCoverageBarColor(data.pct)}`}
                          style={{ width: `${data.pct}%` }}
                        />
                      </div>
                      <div className="text-xs text-slate-400">
                        <span className="font-medium text-green-400">{data.covered}</span> covered
                        <span className="mx-2">•</span>
                        <span className="font-medium text-yellow-400">{data.skipped}</span> skipped
                        <span className="mx-2">•</span>
                        <span className="font-medium text-slate-300">{data.total}</span> total
                      </div>
                    </div>
                  </div>
                )
              })}
            </div>
          </div>
        )}

        {/* Coverage Report Summary */}
        {coverageData && (
          <div className="mb-8">
            <h2 className="text-xl font-semibold mb-6">Coverage Report Summary</h2>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
              <div className="bg-gradient-to-r from-green-600 to-green-700 rounded-lg p-6 text-white">
                <div className="flex items-center justify-between mb-4">
                  <h3 className="text-lg font-semibold">Excellent Coverage</h3>
                  <div className="text-3xl">🎯</div>
                </div>
                <div className="text-3xl font-bold mb-2">
                  {coverageData.files.filter(f => f.lines.pct >= 90).length}
                </div>
                <div className="text-green-100">Files with 90%+ coverage</div>
                <div className="text-xs text-green-200 mt-2">
                  {((coverageData.files.filter(f => f.lines.pct >= 90).length / coverageData.files.length) * 100).toFixed(1)}% of total files
                </div>
              </div>
              
              <div className="bg-gradient-to-r from-blue-600 to-blue-700 rounded-lg p-6 text-white">
                <div className="flex items-center justify-between mb-4">
                  <h3 className="text-lg font-semibold">Well Tested</h3>
                  <div className="text-3xl">✅</div>
                </div>
                <div className="text-3xl font-bold mb-2">
                  {coverageData.files.filter(f => f.lines.pct >= 80).length}
                </div>
                <div className="text-blue-100">Files with 80%+ coverage</div>
                <div className="text-xs text-blue-200 mt-2">
                  {((coverageData.files.filter(f => f.lines.pct >= 80).length / coverageData.files.length) * 100).toFixed(1)}% of total files
                </div>
              </div>
              
              <div className="bg-gradient-to-r from-yellow-600 to-yellow-700 rounded-lg p-6 text-white">
                <div className="flex items-center justify-between mb-4">
                  <h3 className="text-lg font-semibold">Needs Improvement</h3>
                  <div className="text-3xl">⚠️</div>
                </div>
                <div className="text-3xl font-bold mb-2">
                  {coverageData.files.filter(f => f.lines.pct < 80 && f.lines.pct >= 60).length}
                </div>
                <div className="text-yellow-100">Files with 60-79% coverage</div>
                <div className="text-xs text-yellow-200 mt-2">
                  Focus area for testing efforts
                </div>
              </div>
              
              <div className="bg-gradient-to-r from-red-600 to-red-700 rounded-lg p-6 text-white">
                <div className="flex items-center justify-between mb-4">
                  <h3 className="text-lg font-semibold">Poor Coverage</h3>
                  <div className="text-3xl">🚨</div>
                </div>
                <div className="text-3xl font-bold mb-2">
                  {coverageData.files.filter(f => f.lines.pct < 60).length}
                </div>
                <div className="text-red-100">Files with less than 60% coverage</div>
                <div className="text-xs text-red-200 mt-2">
                  Requires immediate attention
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Category Breakdown */}
        {coverageData && (
          <div className="mb-8">
            <h2 className="text-xl font-semibold mb-6">Coverage by Category</h2>
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <div className="bg-slate-800 rounded-lg p-6">
                <h3 className="text-lg font-semibold mb-4">Category Performance</h3>
                {(() => {
                  const categories = ['routes', 'agents', 'services', 'utils', 'db', 'auth']
                  const chartData = categories.map(category => {
                    const categoryFiles = coverageData.files.filter(file => file.file.includes(category))
                    if (categoryFiles.length === 0) return { category, value: 0, files: 0 }
                    const avgCoverage = categoryFiles.reduce((acc, file) => acc + file.lines.pct, 0) / categoryFiles.length
                    return { category, value: avgCoverage, files: categoryFiles.length }
                  }).filter(item => item.files > 0)
                  
                  const maxCoverage = Math.max(...chartData.map(item => item.value))
                  
                  return (
                    <div className="space-y-3">
                      {chartData.map(({ category, value, files }) => (
                        <div key={category} className="space-y-1">
                          <div className="flex justify-between items-center">
                            <div className="flex items-center gap-2">
                              <div className={`w-3 h-3 rounded-full ${getCategoryColor(`app/${category}/test.py`)}`}></div>
                              <span className="text-sm font-medium capitalize">{category}</span>
                              <span className="text-xs text-slate-400">({files})</span>
                            </div>
                            <span className={`text-sm font-bold ${getCoverageColor(value)}`}>
                              {value.toFixed(1)}%
                            </span>
                          </div>
                          <div className="w-full bg-slate-700 rounded-full h-2">
                            <div
                              className={`h-2 rounded-full ${getCoverageBarColor(value)}`}
                              style={{ width: `${(value / maxCoverage) * 100}%` }}
                            />
                          </div>
                        </div>
                      ))}
                    </div>
                  )
                })()}
              </div>
              
              <div className="space-y-4">
                {['routes', 'agents', 'services', 'utils', 'db', 'auth'].map((category) => {
                  const categoryFiles = coverageData.files.filter(file => file.file.includes(category))
                  if (categoryFiles.length === 0) return null
                  
                  const avgCoverage = categoryFiles.reduce((acc, file) => acc + file.lines.pct, 0) / categoryFiles.length
                  const wellTestedFiles = categoryFiles.filter(f => f.lines.pct >= 80).length
                  const coverageScore = wellTestedFiles / categoryFiles.length * 100
                  
                  return (
                    <div key={category} className="bg-slate-800 rounded-lg p-4 hover:bg-slate-750 transition-colors">
                      <div className="flex items-center justify-between mb-2">
                        <div className="flex items-center gap-2">
                          <div className={`w-4 h-4 rounded-full ${getCategoryColor(`app/${category}/test.py`)}`}></div>
                          <h4 className="font-semibold capitalize">{category}</h4>
                        </div>
                        <div className="text-right">
                          <div className={`text-lg font-bold ${getCoverageColor(avgCoverage)}`}>
                            {avgCoverage.toFixed(1)}%
                          </div>
                        </div>
                      </div>
                      <div className="grid grid-cols-3 gap-2 text-xs text-slate-400">
                        <div>
                          <div className="text-slate-300 font-medium">{categoryFiles.length}</div>
                          <div>files</div>
                        </div>
                        <div>
                          <div className="text-green-400 font-medium">{wellTestedFiles}</div>
                          <div>well tested</div>
                        </div>
                        <div>
                          <div className={`font-medium ${coverageScore >= 75 ? 'text-green-400' : coverageScore >= 50 ? 'text-yellow-400' : 'text-red-400'}`}>
                            {coverageScore.toFixed(0)}%
                          </div>
                          <div>quality</div>
                        </div>
                      </div>
                      <div className="w-full bg-slate-700 rounded-full h-1 mt-2">
                        <div
                          className={`h-1 rounded-full ${getCoverageBarColor(avgCoverage)}`}
                          style={{ width: `${avgCoverage}%` }}
                        />
                      </div>
                    </div>
                  )
                })}
              </div>
            </div>
          </div>
        )}

        {/* File-level Coverage Table */}
        {coverageData && (
          <div className="mb-8">
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-xl font-semibold">File Coverage Details</h2>
              <div className="flex items-center gap-4">
                <div className="text-sm text-slate-400">
                  <span className="font-medium text-green-400">{coverageData.files.filter(f => f.lines.pct >= 80).length}</span> well tested
                  <span className="mx-2">•</span>
                  <span className="font-medium text-yellow-400">{coverageData.files.filter(f => f.lines.pct < 80 && f.lines.pct >= 60).length}</span> needs work
                  <span className="mx-2">•</span>
                  <span className="font-medium text-red-400">{coverageData.files.filter(f => f.lines.pct < 60).length}</span> poor coverage
                </div>
              </div>
            </div>
            
            <div className="bg-slate-800 rounded-lg overflow-hidden">
              <div className="bg-slate-700 px-6 py-3">
                <div className="flex items-center justify-between text-xs text-slate-400">
                  <div className="flex items-center gap-6">
                    <div className="flex items-center gap-2">
                      <div className="w-3 h-3 bg-green-500 rounded-full"></div>
                      <span>Well Tested (≥80%)</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <div className="w-3 h-3 bg-yellow-500 rounded-full"></div>
                      <span>Needs Work (60-79%)</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <div className="w-3 h-3 bg-red-500 rounded-full"></div>
                      <span>Poor Coverage ({'<'}60%)</span>
                    </div>
                  </div>
                  <div>Click on any metric for detailed view</div>
                </div>
              </div>
              
              <div className="overflow-x-auto">
                <table className="min-w-full">
                  <thead className="bg-slate-700">
                    <tr>
                      <th className="px-6 py-3 text-left text-xs font-medium text-slate-300 uppercase tracking-wider">
                        File
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-slate-300 uppercase tracking-wider">
                        Category
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-slate-300 uppercase tracking-wider">
                        Lines
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-slate-300 uppercase tracking-wider">
                        Statements
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-slate-300 uppercase tracking-wider">
                        Functions
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-slate-300 uppercase tracking-wider">
                        Branches
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-slate-300 uppercase tracking-wider">
                        Quality Score
                      </th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-700">
                    {coverageData.files
                      .sort((a, b) => b.lines.pct - a.lines.pct)
                      .map((file, index) => {
                        const overallScore = (file.lines.pct + file.statements.pct + file.functions.pct) / 3
                        const qualityLevel = file.lines.pct >= 80 ? 'excellent' : file.lines.pct >= 60 ? 'good' : 'poor'
                        const qualityColors = {
                          excellent: { bg: 'bg-green-500', text: 'text-green-400', border: 'border-green-500' },
                          good: { bg: 'bg-yellow-500', text: 'text-yellow-400', border: 'border-yellow-500' },
                          poor: { bg: 'bg-red-500', text: 'text-red-400', border: 'border-red-500' }
                        }[qualityLevel]
                        
                        return (
                          <tr key={index} className={`hover:bg-slate-750 transition-colors ${qualityLevel === 'poor' ? 'bg-red-950/10' : qualityLevel === 'good' ? 'bg-yellow-950/10' : ''}`}>
                            <td className="px-6 py-4 whitespace-nowrap">
                              <div className="flex items-center gap-3">
                                <div className={`w-2 h-2 rounded-full ${qualityColors.bg}`}></div>
                                <div>
                                  <div className="text-sm font-mono text-slate-300 max-w-xs truncate">
                                    {file.file}
                                  </div>
                                  <div className="text-xs text-slate-500">
                                    {file.lines.total} lines total
                                  </div>
                                </div>
                              </div>
                            </td>
                            <td className="px-6 py-4 whitespace-nowrap">
                              <div className="flex items-center gap-2">
                                <div className={`w-3 h-3 rounded-full ${getCategoryColor(file.file)}`}></div>
                                <span className="text-xs text-slate-400">{getCategoryLabel(file.file)}</span>
                              </div>
                            </td>
                            <td className="px-6 py-4 whitespace-nowrap">
                              <div className="space-y-1">
                                <div className="flex items-center gap-2">
                                  <span className={`text-sm font-bold ${getCoverageColor(file.lines.pct)}`}>
                                    {file.lines.pct.toFixed(1)}%
                                  </span>
                                  <span className="text-xs text-slate-400">
                                    ({file.lines.covered}/{file.lines.total})
                                  </span>
                                </div>
                                <div className="w-20 bg-slate-700 rounded-full h-1.5">
                                  <div
                                    className={`h-1.5 rounded-full ${getCoverageBarColor(file.lines.pct)}`}
                                    style={{ width: `${file.lines.pct}%` }}
                                  />
                                </div>
                              </div>
                            </td>
                            <td className="px-6 py-4 whitespace-nowrap">
                              <div className="space-y-1">
                                <div className="flex items-center gap-2">
                                  <span className={`text-sm font-medium ${getCoverageColor(file.statements.pct)}`}>
                                    {file.statements.pct.toFixed(1)}%
                                  </span>
                                  <span className="text-xs text-slate-400">
                                    ({file.statements.covered}/{file.statements.total})
                                  </span>
                                </div>
                                <div className="w-16 bg-slate-700 rounded-full h-1">
                                  <div
                                    className={`h-1 rounded-full ${getCoverageBarColor(file.statements.pct)}`}
                                    style={{ width: `${file.statements.pct}%` }}
                                  />
                                </div>
                              </div>
                            </td>
                            <td className="px-6 py-4 whitespace-nowrap">
                              <div className="space-y-1">
                                <div className="flex items-center gap-2">
                                  <span className={`text-sm font-medium ${getCoverageColor(file.functions.pct)}`}>
                                    {file.functions.pct.toFixed(1)}%
                                  </span>
                                  <span className="text-xs text-slate-400">
                                    ({file.functions.covered}/{file.functions.total})
                                  </span>
                                </div>
                                <div className="w-16 bg-slate-700 rounded-full h-1">
                                  <div
                                    className={`h-1 rounded-full ${getCoverageBarColor(file.functions.pct)}`}
                                    style={{ width: `${file.functions.pct}%` }}
                                  />
                                </div>
                              </div>
                            </td>
                            <td className="px-6 py-4 whitespace-nowrap">
                              <div className="space-y-1">
                                <div className="flex items-center gap-2">
                                  <span className={`text-sm font-medium ${getCoverageColor(file.branches.pct)}`}>
                                    {file.branches.pct.toFixed(1)}%
                                  </span>
                                  <span className="text-xs text-slate-400">
                                    ({file.branches.covered}/{file.branches.total})
                                  </span>
                                </div>
                                <div className="w-16 bg-slate-700 rounded-full h-1">
                                  <div
                                    className={`h-1 rounded-full ${getCoverageBarColor(file.branches.pct)}`}
                                    style={{ width: `${file.branches.pct}%` }}
                                  />
                                </div>
                              </div>
                            </td>
                            <td className="px-6 py-4 whitespace-nowrap">
                              <div className="flex items-center gap-2">
                                <div className={`px-2 py-1 rounded text-xs font-bold ${qualityColors.text} ${qualityColors.border} border bg-current bg-opacity-10`}>
                                  {qualityLevel.toUpperCase()}
                                </div>
                                <span className="text-xs text-slate-400">
                                  {overallScore.toFixed(0)}%
                                </span>
                              </div>
                            </td>
                          </tr>
                        )
                      })}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        )}

        {/* Action Buttons */}
        <div className="mt-8 text-center">
          <div className="bg-slate-800 rounded-lg p-6">
            <h3 className="text-lg font-semibold mb-4">Coverage Report Actions</h3>
            <div className="flex items-center justify-center gap-4">
              <button
                onClick={() => window.print()}
                className="px-6 py-3 bg-slate-600 hover:bg-slate-700 text-white rounded-lg font-medium transition-colors flex items-center gap-2"
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 17h2a2 2 0 002-2v-4a2 2 0 00-2-2H5a2 2 0 00-2 2v4a2 2 0 002 2h2m2 4h6a2 2 0 002-2v-4a2 2 0 00-2-2H9a2 2 0 00-2 2v4a2 2 0 002 2zm8-12V5a2 2 0 00-2-2H9a2 2 0 00-2 2v4h10z" />
                </svg>
                Print Report
              </button>
              
              <button
                onClick={() => {
                  if (!coverageData) return
                  const dataStr = JSON.stringify(coverageData, null, 2)
                  const dataUri = 'data:application/json;charset=utf-8,'+ encodeURIComponent(dataStr)
                  const exportFileDefaultName = `coverage-report-${new Date().toISOString().split('T')[0]}.json`
                  
                  const linkElement = document.createElement('a')
                  linkElement.setAttribute('href', dataUri)
                  linkElement.setAttribute('download', exportFileDefaultName)
                  linkElement.click()
                }}
                className="px-6 py-3 bg-green-600 hover:bg-green-700 text-white rounded-lg font-medium transition-colors flex items-center gap-2"
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg>
                Export JSON
              </button>
            </div>
          </div>
        </div>

        {usingMockData && (
          <div className="mt-8 text-center">
            <div className="px-6 py-4 bg-yellow-600/20 border border-yellow-500/50 rounded-lg max-w-2xl mx-auto">
              <p className="text-yellow-400 text-sm">
                <strong>Demo Mode:</strong> Coverage API not available.
                Showing mock data for demonstration purposes.
                Ensure the backend is running and accessible to view real coverage data.
              </p>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}