import { useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuthStore } from '@/store/authStore'

export const useAuth = (requireAuth = true) => {
  const navigate = useNavigate()
  const { 
    user, 
    isAuthenticated, 
    isLoading, 
    checkAuth,
    hasRole,
    hasPermission 
  } = useAuthStore()

  useEffect(() => {
    if (!user && !isLoading) {
      checkAuth()
    }
  }, [])

  useEffect(() => {
    if (requireAuth && !isLoading && !isAuthenticated) {
      navigate('/login')
    }
  }, [requireAuth, isLoading, isAuthenticated, navigate])

  return {
    user,
    isAuthenticated,
    isLoading,
    hasRole,
    hasPermission,
  }
}

