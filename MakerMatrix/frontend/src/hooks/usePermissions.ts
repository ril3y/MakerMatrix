import { authService } from '@/services/auth.service'

export const usePermissions = () => {
  const user = authService.getStoredUser()

  const hasPermission = (permission: string): boolean => {
    return authService.hasPermission(permission)
  }

  const hasRole = (role: string): boolean => {
    return authService.hasRole(role)
  }

  const hasAnyPermission = (permissions: string[]): boolean => {
    return permissions.some(p => hasPermission(p))
  }

  const hasAllPermissions = (permissions: string[]): boolean => {
    return permissions.every(p => hasPermission(p))
  }

  const isAdmin = (): boolean => {
    return hasRole('admin')
  }

  const canCreate = (resource: string): boolean => {
    return hasPermission(`${resource}:create`) || hasPermission('all')
  }

  const canRead = (resource: string): boolean => {
    return hasPermission(`${resource}:read`) || hasPermission('all')
  }

  const canUpdate = (resource: string): boolean => {
    return hasPermission(`${resource}:update`) || hasPermission('all')
  }

  const canDelete = (resource: string): boolean => {
    return hasPermission(`${resource}:delete`) || hasPermission('all')
  }

  return {
    user,
    hasPermission,
    hasRole,
    hasAnyPermission,
    hasAllPermissions,
    isAdmin,
    canCreate,
    canRead,
    canUpdate,
    canDelete
  }
}
