'use client'

import { useState, useEffect } from 'react'
import Link from 'next/link'

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

export default function CoveragePage() {
  const [coverageData, setCoverageData] = useState<CoverageData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    // Mock coverage data for demonstration
    // In a real implementation, this would fetch from an API endpoint that reads the coverage JSON
    const fetchCoverage = async () => {
      try {
        // Simulate API call delay
        await new Promise(resolve => setTimeout(resolve, 500))
        
        // Mock coverage data based on the test results
        const mockCoverageData: CoverageData = {
          total: {
            lines: { pct: 85.2, covered: 312, skipped: 12, total: 367 },
            statements: { pct: 87.1, covered: 298, skipped: 8, total: 342 },
            functions: { pct: 82.5, covered: 94, skipped: 3, total: 114 },
            branches: { pct: 79.8, covered: 156, skipped: 7, total: 196 }
          },
          files: [
            {
              file: 'app/graph/page.tsx',
              lines: { pct: 92.3, covered: 84, skipped: 2, total: 91 },
              statements: { pct: 94.1, covered: 80, skipped: 1, total: 85 },
              functions: { pct: 88.9, covered: 16, skipped: 1, total: 18 },
              branches: { pct: 85.7, covered: 24, skipped: 1, total: 28 }
            },
            {
              file: 'components/Graph3D.tsx',
              lines: { pct: 89.5, covered: 76, skipped: 3, total: 85 },
              statements: { pct: 91.2, covered: 73, skipped: 2, total: 80 },
              functions: { pct: 85.7, covered: 18, skipped: 1, total: 21 },
              branches: { pct: 82.1, covered: 32, skipped: 2, total: 39 }
            },
            {
              file: 'components/ChatDock.tsx',
              lines: { pct: 86.7, covered: 68, skipped: 2, total: 78 },
              statements: { pct: 88.9, covered: 65, skipped: 1, total: 73 },
              functions: { pct: 84.2, covered: 16, skipped: 0, total: 19 },
              branches: { pct: 80.0, covered: 24, skipped: 1, total: 30 }
            },
            {
              file: 'components/RepoPicker.tsx',
              lines: { pct: 94.1, covered: 64, skipped: 1, total: 68 },
              statements: { pct: 95.5, covered: 63, skipped: 0, total: 66 },
              functions: { pct: 90.9, covered: 20, skipped: 0, total: 22 },
              branches: { pct: 87.5, covered: 28, skipped: 1, total: 32 }
            },
            {
              file: 'app/dashboard/page.tsx',
              lines: { pct: 78.9, covered: 45, skipped: 2, total: 57 },
              statements: { pct: 80.6, covered: 43, skipped: 1, total: 53 },
              functions: { pct: 75.0, covered: 12, skipped: 1, total: 16 },
              branches: { pct: 71.4, covered: 25, skipped: 2, total: 35 }
            },
            {
              file: 'app/page.tsx',
              lines: { pct: 72.5, covered: 29, skipped: 2, total: 40 },
              statements: { pct: 74.4, covered: 32, skipped: 1, total: 43 },
              functions: { pct: 70.0, covered: 7, skipped: 0, total: 10 },
              branches: { pct: 66.7, covered: 12, skipped: 1, total: 18 }
            },
            {
              file: 'lib/api.ts',
              lines: { pct: 88.2, covered: 30, skipped: 1, total: 34 },
              statements: { pct: 90.0, covered: 27, skipped: 0, total: 30 },
              functions: { pct: 85.7, covered: 6, skipped: 0, total: 7 },
              branches: { pct: 83.3, covered: 15, skipped: 1, total: 18 }
            },
            {
              file: 'lib/auth.ts',
              lines: { pct: 91.7, covered: 22, skipped: 0, total: 24 },
              statements: { pct: 93.1, covered: 27, skipped: 0, total: 29 },
              functions: { pct: 88.9, covered: 8, skipped: 0, total: 9 },
              branches: { pct: 85.7, covered: 12, skipped: 0, total: 14 }
            },
            {
              file: 'lib/perf.ts',
              lines: { pct: 95.0, covered: 19, skipped: 0, total: 20 },
              statements: { pct: 96.4, covered: 27, skipped: 0, total: 28 },
              functions: { pct: 100.0, covered: 4, skipped: 0, total: 4 },
              branches: { pct: 90.9, covered: 10, skipped: 0, total: 11 }
            }
          ]
        }
        
        setCoverageData(mockCoverageData)
        setLoading(false)
      } catch (err) {
        setError('Failed to load coverage data')
        setLoading(false)
      }
    }

    fetchCoverage()
  }, [])

  const getCoverageColor = (percentage: number) => {
    if (percentage >= 90) return 'text-green-600'
    if (percentage >= 80) return 'text-yellow-600'
    if (percentage >= 70) return 'text-orange-600'
    return 'text-red-600'
  }

  const getCoverageBarColor = (percentage: number) => {
    if (percentage >= 90) return 'bg-green-500'
    if (percentage >= 80) return 'bg-yellow-500'
    if (percentage >= 70) return 'bg-orange-500'
    return 'bg-red-500'
  }

  const safePct = (v?: number) => (typeof v === 'number' && !Number.isNaN(v) ? v : 0)

  if (loading) {
    return (
      <div className="min-h-screen bg-slate-900 text-white p-8">
        <div className="max-w-7xl mx-auto">
          <div className="flex items-center justify-center h-64">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500"></div>
            <span className="ml-3 text-lg">Loading coverage data...</span>
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
              <h1 className="text-3xl font-bold mb-2">Frontend Test Coverage</h1>
              <p className="text-slate-400">Code coverage analysis for AppLens frontend</p>
            </div>
            <div className="flex items-center gap-3">
              <Link
                href="/backend-coverage"
                className="px-4 py-2 bg-purple-600/20 hover:bg-purple-600/30 text-purple-400 border border-purple-500/50 rounded-lg transition-colors flex items-center gap-2"
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4" />
                </svg>
                Backend Coverage
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
            <h2 className="text-xl font-semibold mb-4">Overall Coverage</h2>
            <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
              <div className="bg-slate-800 rounded-lg p-6">
                <h3 className="text-sm font-medium text-slate-400 mb-2">Lines</h3>
                <div className={`text-2xl font-bold ${getCoverageColor(safePct(coverageData.total.lines.pct))}`}>
                  {safePct(coverageData.total.lines.pct).toFixed(1)}%
                </div>
                <div className="text-sm text-slate-400 mt-1">
                  {coverageData.total.lines.covered} / {coverageData.total.lines.total} lines
                </div>
                <div className="w-full bg-slate-700 rounded-full h-2 mt-2">
                  <div
                    className={`h-2 rounded-full ${getCoverageBarColor(coverageData.total.lines.pct)}`}
                    style={{ width: `${coverageData.total.lines.pct}%` }}
                  ></div>
                </div>
              </div>

              <div className="bg-slate-800 rounded-lg p-6">
                <h3 className="text-sm font-medium text-slate-400 mb-2">Statements</h3>
                <div className={`text-2xl font-bold ${getCoverageColor(coverageData.total.statements.pct)}`}>
                  {safePct(coverageData.total.statements.pct).toFixed(1)}%
                </div>
                <div className="text-sm text-slate-400 mt-1">
                  {coverageData.total.statements.covered} / {coverageData.total.statements.total} statements
                </div>
                <div className="w-full bg-slate-700 rounded-full h-2 mt-2">
                  <div
                    className={`h-2 rounded-full ${getCoverageBarColor(coverageData.total.statements.pct)}`}
                    style={{ width: `${coverageData.total.statements.pct}%` }}
                  ></div>
                </div>
              </div>

              <div className="bg-slate-800 rounded-lg p-6">
                <h3 className="text-sm font-medium text-slate-400 mb-2">Functions</h3>
                <div className={`text-2xl font-bold ${getCoverageColor(coverageData.total.functions.pct)}`}>
                  {safePct(coverageData.total.functions.pct).toFixed(1)}%
                </div>
                <div className="text-sm text-slate-400 mt-1">
                  {coverageData.total.functions.covered} / {coverageData.total.functions.total} functions
                </div>
                <div className="w-full bg-slate-700 rounded-full h-2 mt-2">
                  <div
                    className={`h-2 rounded-full ${getCoverageBarColor(coverageData.total.functions.pct)}`}
                    style={{ width: `${coverageData.total.functions.pct}%` }}
                  ></div>
                </div>
              </div>

              <div className="bg-slate-800 rounded-lg p-6">
                <h3 className="text-sm font-medium text-slate-400 mb-2">Branches</h3>
                <div className={`text-2xl font-bold ${getCoverageColor(coverageData.total.branches.pct)}`}>
                  {safePct(coverageData.total.branches.pct).toFixed(1)}%
                </div>
                <div className="text-sm text-slate-400 mt-1">
                  {coverageData.total.branches.covered} / {coverageData.total.branches.total} branches
                </div>
                <div className="w-full bg-slate-700 rounded-full h-2 mt-2">
                  <div
                    className={`h-2 rounded-full ${getCoverageBarColor(coverageData.total.branches.pct)}`}
                    style={{ width: `${coverageData.total.branches.pct}%` }}
                  ></div>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* File-level Coverage */}
        {coverageData && (
          <div>
            <h2 className="text-xl font-semibold mb-4">File Coverage Details</h2>
            <div className="bg-slate-800 rounded-lg overflow-hidden">
              <div className="overflow-x-auto">
                <table className="min-w-full">
                  <thead className="bg-slate-700">
                    <tr>
                      <th className="px-6 py-3 text-left text-xs font-medium text-slate-300 uppercase tracking-wider">
                        File
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
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-700">
                    {coverageData.files.map((file, index) => (
                      <tr key={index} className="hover:bg-slate-700/40">
                        <td className="px-6 py-4 whitespace-nowrap text-sm font-mono text-slate-300">
                          {file.file}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap">
                          <div className="flex items-center">
                            <span className={`text-sm font-medium ${getCoverageColor(safePct(file.lines.pct))}`}>
                              {safePct(file.lines.pct).toFixed(1)}%
                            </span>
                            <span className="text-xs text-slate-400 ml-2">
                              ({file.lines.covered}/{file.lines.total})
                            </span>
                          </div>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap">
                          <div className="flex items-center">
                            <span className={`text-sm font-medium ${getCoverageColor(safePct(file.statements.pct))}`}>
                              {safePct(file.statements.pct).toFixed(1)}%
                            </span>
                            <span className="text-xs text-slate-400 ml-2">
                              ({file.statements.covered}/{file.statements.total})
                            </span>
                          </div>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap">
                          <div className="flex items-center">
                            <span className={`text-sm font-medium ${getCoverageColor(safePct(file.functions.pct))}`}>
                              {safePct(file.functions.pct).toFixed(1)}%
                            </span>
                            <span className="text-xs text-slate-400 ml-2">
                              ({file.functions.covered}/{file.functions.total})
                            </span>
                          </div>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap">
                          <div className="flex items-center">
                            <span className={`text-sm font-medium ${getCoverageColor(safePct(file.branches.pct))}`}>
                              {safePct(file.branches.pct).toFixed(1)}%
                            </span>
                            <span className="text-xs text-slate-400 ml-2">
                              ({file.branches.covered}/{file.branches.total})
                            </span>
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        )}

      </div>
    </div>
  )
}