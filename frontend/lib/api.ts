import axios from 'axios'

// Automatically detect API URL based on environment
export function getApiUrl(): string {
  // If explicitly set via environment variable (useful for local dev), use it
  if (process.env.NEXT_PUBLIC_API_URL) {
    return process.env.NEXT_PUBLIC_API_URL
  }
  
  // In browser, detect from current location
  if (typeof window !== 'undefined') {
    const hostname = window.location.hostname
    const protocol = window.location.protocol
    
    // If running on localhost, use localhost API
    if (hostname === 'localhost' || hostname === '127.0.0.1') {
      return 'http://localhost:8000'
    }
    
    // In production, use absolute URL with /api path (proxied through Caddy)
    // This works because Caddy routes /api/* to the backend
    return `${protocol}//${hostname}/api`
  }
  
  // Default fallback for server-side rendering
  return 'http://localhost:8000'
}

const API_URL = getApiUrl()

export const api = axios.create({
  baseURL: API_URL,
  withCredentials: true,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Add request interceptor for error handling
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // Only redirect to login if not already on the landing page
      // This prevents redirect loops and allows pages to handle their own auth checks
      if (typeof window !== 'undefined' && window.location.pathname !== '/') {
        window.location.href = '/'
      }
    }
    return Promise.reject(error)
  }
)

