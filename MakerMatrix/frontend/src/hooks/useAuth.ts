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

export const useRequireRole = (role: string) => {
  const navigate = useNavigate()
  const { user, hasRole, isLoading } = useAuthStore()

  useEffect(() => {
    if (!isLoading && user && !hasRole(role)) {
      navigate('/unauthorized')
    }
  }, [user, role, hasRole, isLoading, navigate])
}

export const useRequirePermission = (permission: string) => {
  const navigate = useNavigate()
  const { user, hasPermission, isLoading } = useAuthStore()

  useEffect(() => {
    if (!isLoading && user && !hasPermission(permission)) {
      navigate('/unauthorized')
    }
  }, [user, permission, hasPermission, isLoading, navigate])
}