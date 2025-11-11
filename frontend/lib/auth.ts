import { api } from './api'

export async function checkAuth(): Promise<boolean> {
  try {
    await api.get('/health')
    return true
  } catch {
    return false
  }
}

export async function logout() {
  try {
    // Call backend logout endpoint to clear httpOnly cookie
    await api.post('/auth/logout', {}, {
      withCredentials: true, // Ensure cookies are sent
    })
  } catch (error) {
    // Even if backend call fails, try to clear cookie client-side
    console.log('Backend logout failed, clearing cookie client-side', error)
  }
  
  // Also try to clear cookie client-side (in case it's not httpOnly)
  const domains = ['localhost', window.location.hostname]
  const paths = ['/', '']
  
  domains.forEach(domain => {
    paths.forEach(path => {
      document.cookie = `applens_token=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=${path}; domain=${domain};`
      document.cookie = `applens_token=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=${path};`
    })
  })
  
  // Force a hard redirect to ensure cookie is cleared
  // Use window.location.replace to prevent back button issues
  window.location.replace('/')
}

