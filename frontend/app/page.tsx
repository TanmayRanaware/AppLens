'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { Github } from 'lucide-react'
import { api } from '@/lib/api'

export default function LandingPage() {
  const router = useRouter()
  const [checking, setChecking] = useState(true)

  useEffect(() => {
    // Check if user is already authenticated
    const checkAuth = async () => {
      try {
        const response = await api.get('/auth/me', {
          validateStatus: (status) => status < 500, // Don't throw on 401
        })
        if (response.status === 200 && response.data?.authenticated) {
          // Already authenticated, redirect to dashboard
          router.push('/dashboard')
        } else {
          // Not authenticated (401 or other error), stay on landing page
          setChecking(false)
        }
      } catch (error: any) {
        // Not authenticated or network error, stay on landing page
        // This is expected after logout - 401 means not authenticated
        if (error.response?.status === 401) {
          // Expected: user is not authenticated
          setChecking(false)
        } else {
          // Other error, still show landing page
          console.error('Auth check error:', error)
          setChecking(false)
        }
      }
    }
    // Add a small delay to ensure cookie is cleared after logout
    const timer = setTimeout(() => {
      checkAuth()
    }, 200)
    
    return () => clearTimeout(timer)
  }, [router])

  const handleGitHubLogin = () => {
    window.location.href = `${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/auth/github/login`
  }

  const handleSwitchAccount = () => {
    // Open GitHub authorizations page in new tab
    window.open('https://github.com/settings/applications/authorizations', '_blank')
    // Show alert with instructions
    alert('Please revoke the "AppLens" authorization on the page that just opened, then click "Sign in with GitHub" again.')
  }

  // Show loading state while checking auth
  if (checking) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900 flex items-center justify-center">
        <div className="text-white text-xl">Loading...</div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900 flex items-center justify-center p-4">
      <div className="max-w-4xl w-full text-center space-y-8">
        <div className="space-y-4">
          <h1 className="text-6xl font-bold text-white mb-4">
            App<span className="text-primary-400">Lens</span>
          </h1>
        </div>

        <div className="space-y-6 pt-8">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 max-w-3xl mx-auto">
            <div className="bg-white/10 backdrop-blur-lg rounded-lg p-6 border border-white/20">
              <div className="text-3xl mb-3">🔍</div>
              <h3 className="text-lg font-semibold text-white mb-2">Multi-Repo Scanning</h3>
              <p className="text-sm text-gray-300">Scan multiple repositories simultaneously</p>
            </div>
            <div className="bg-white/10 backdrop-blur-lg rounded-lg p-6 border border-white/20">
              <div className="text-3xl mb-3">📊</div>
              <h3 className="text-lg font-semibold text-white mb-2">3D Visualization</h3>
              <p className="text-sm text-gray-300">Interactive force-directed graph</p>
            </div>
            <div className="bg-white/10 backdrop-blur-lg rounded-lg p-6 border border-white/20">
              <div className="text-3xl mb-3">🤖</div>
              <h3 className="text-lg font-semibold text-white mb-2">AI Analysis</h3>
              <p className="text-sm text-gray-300">Error analyzer and what-if simulator</p>
            </div>
          </div>

          <button
            onClick={handleGitHubLogin}
            className="inline-flex items-center gap-3 px-8 py-4 bg-white text-gray-900 rounded-lg font-semibold text-lg hover:bg-gray-100 transition-colors shadow-lg hover:shadow-xl"
          >
            <Github className="w-6 h-6" />
            Sign in with GitHub
          </button>

          <p className="text-sm text-gray-400 mt-4">
            We only request read access to your public repositories
          </p>
          
          <div className="mt-6 p-4 bg-yellow-500/10 border border-yellow-500/30 rounded-lg">
            <p className="text-sm text-yellow-400 mb-2">
              <strong>Want to use a different GitHub account?</strong>
            </p>
            <p className="text-xs text-yellow-300/80 mb-3">
              GitHub remembers your authorization. To switch accounts:
            </p>
            <div className="flex flex-col sm:flex-row gap-2 justify-center items-center mb-3">
              <button
                onClick={handleSwitchAccount}
                className="px-4 py-2 bg-yellow-500/20 hover:bg-yellow-500/30 text-yellow-400 border border-yellow-500/50 rounded-lg text-xs font-medium transition-colors"
              >
                Open GitHub Authorizations
              </button>
              <span className="text-xs text-yellow-300/60">or</span>
              <a
                href="https://github.com/logout"
                target="_blank"
                rel="noopener noreferrer"
                className="px-4 py-2 bg-yellow-500/20 hover:bg-yellow-500/30 text-yellow-400 border border-yellow-500/50 rounded-lg text-xs font-medium transition-colors"
              >
                Logout from GitHub
              </a>
            </div>
            <ol className="text-xs text-yellow-300/80 list-decimal list-inside space-y-1 text-left max-w-md mx-auto mb-3">
              <li>Revoke "AppLens" authorization (or logout from GitHub)</li>
              <li>Then click "Sign in with GitHub" above</li>
            </ol>
            <p className="text-xs text-yellow-300/60">
              💡 <strong>Tip:</strong> Use an <strong>incognito/private window</strong> to sign in with a different account without revoking
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}

