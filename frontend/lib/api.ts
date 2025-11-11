import axios from 'axios'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

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

