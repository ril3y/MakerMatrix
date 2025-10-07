export interface User {
  id: string
  username: string
  email: string
  is_active: boolean
  created_at: string
  roles: Role[]
}

export interface Role {
  id: string
  name: string
  permissions: Record<string, boolean>
}

export interface CreateUserRequest {
  username: string
  email: string
  password: string
  role_ids: string[]
}

export interface UpdateUserRolesRequest {
  role_ids: string[]
}

export interface CreateRoleRequest {
  name: string
  permissions: Record<string, boolean>
}

export interface UpdateRoleRequest {
  name?: string
  permissions?: Record<string, boolean>
}

export interface UserStats {
  total: number
  active: number
  inactive: number
  admins: number
}
