import { ReactNode } from 'react'
import { usePermissions } from '@/hooks/usePermissions'

interface PermissionGuardProps {
  children: ReactNode
  permission?: string
  permissions?: string[]
  requireAll?: boolean
  role?: string
  fallback?: ReactNode
}

/**
 * Component that conditionally renders children based on user permissions
 *
 * @example
 * // Single permission check
 * <PermissionGuard permission="parts:create">
 *   <button>Add Part</button>
 * </PermissionGuard>
 *
 * @example
 * // Multiple permissions (any)
 * <PermissionGuard permissions={["parts:update", "parts:delete"]}>
 *   <button>Edit</button>
 * </PermissionGuard>
 *
 * @example
 * // Multiple permissions (all required)
 * <PermissionGuard permissions={["parts:update", "parts:delete"]} requireAll>
 *   <button>Edit & Delete</button>
 * </PermissionGuard>
 *
 * @example
 * // Role check
 * <PermissionGuard role="admin">
 *   <AdminPanel />
 * </PermissionGuard>
 */
export const PermissionGuard = ({
  children,
  permission,
  permissions,
  requireAll = false,
  role,
  fallback = null,
}: PermissionGuardProps) => {
  const { hasPermission, hasRole, hasAnyPermission, hasAllPermissions } = usePermissions()

  let hasAccess = false

  if (role) {
    hasAccess = hasRole(role)
  } else if (permission) {
    hasAccess = hasPermission(permission)
  } else if (permissions) {
    hasAccess = requireAll ? hasAllPermissions(permissions) : hasAnyPermission(permissions)
  } else {
    // No permission requirements specified, allow access
    hasAccess = true
  }

  return hasAccess ? <>{children}</> : <>{fallback}</>
}
