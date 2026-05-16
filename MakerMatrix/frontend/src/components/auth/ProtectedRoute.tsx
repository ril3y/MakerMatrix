import React from 'react'
import { Navigate, Outlet, useLocation } from 'react-router-dom'
import { useAuthStore } from '@/store/authStore'
import LoadingScreen from '@/components/ui/LoadingScreen'

interface ProtectedRouteProps {
  children?: React.ReactNode
  requireRole?: string
  requirePermission?: string
}

const ProtectedRoute: React.FC<ProtectedRouteProps> = ({
  children,
  requireRole,
  requirePermission,
}) => {
  const { isAuthenticated, isLoading, hasRole, hasPermission, checkAuth } = useAuthStore()
  const location = useLocation()

  // Check auth on mount if not already authenticated
  React.useEffect(() => {
    if (!isAuthenticated && !isLoading) {
      checkAuth()
    }
  }, [checkAuth, isAuthenticated, isLoading])

  if (isLoading) {
    return <LoadingScreen />
  }

  if (!isAuthenticated) {
    // Preserve the URL the user was trying to reach so LoginPage can send them back after login.
    return <Navigate to="/login" state={{ from: location }} replace />
  }

  if (requireRole && !hasRole(requireRole)) {
    return <Navigate to="/unauthorized" replace />
  }

  if (requirePermission && !hasPermission(requirePermission)) {
    return <Navigate to="/unauthorized" replace />
  }

  return children ? <>{children}</> : <Outlet />
}

export default ProtectedRoute
