'use client'

import { useState } from 'react'
import { Search, Check } from 'lucide-react'
import { api } from '@/lib/api'

interface RepoPickerProps {
  onSelect: (repo: string) => void
}

export default function RepoPicker({ onSelect }: RepoPickerProps) {
  const [query, setQuery] = useState('')
  const [results, setResults] = useState<string[]>([])
  const [loading, setLoading] = useState(false)
  const [selected, setSelected] = useState<Set<string>>(new Set())

  const handleSearch = async () => {
    if (!query.trim()) return

    setLoading(true)
    try {
      const response = await api.get('/repos/search', { params: { q: query } })
      setResults(response.data.repos || [])
    } catch (error) {
      console.error('Error searching repos:', error)
      setResults([])
    } finally {
      setLoading(false)
    }
  }

  const handleSelect = (repo: string) => {
    if (!selected.has(repo)) {
      setSelected(new Set([...selected, repo]))
      onSelect(repo)
    }
  }

  return (
    <div className="space-y-2">
      <div className="flex gap-2">
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyPress={(e) => e.key === 'Enter' && handleSearch()}
          placeholder="Search repositories..."
          className="flex-1 px-4 py-2 bg-white/10 border border-white/20 rounded-lg text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-primary-500"
        />
        <button
          onClick={handleSearch}
          disabled={loading}
          className="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition-colors disabled:opacity-50"
        >
          <Search className="w-5 h-5" />
        </button>
      </div>

      {results.length > 0 && (
        <div className="max-h-48 overflow-y-auto bg-white/5 rounded-lg border border-white/10">
          {results.map((repo) => (
            <button
              key={repo}
              onClick={() => handleSelect(repo)}
              className={`w-full px-4 py-2 text-left hover:bg-white/10 transition-colors flex items-center justify-between ${
                selected.has(repo) ? 'bg-primary-600/20' : ''
              }`}
            >
              <span className="text-white text-sm">{repo}</span>
              {selected.has(repo) && <Check className="w-4 h-4 text-primary-400" />}
            </button>
          ))}
        </div>
      )}
    </div>
  )
}

