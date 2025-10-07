export interface User {
  id: string
  username: string
  email: string
  is_active: boolean
  created_at: string
  updated_at: string
  roles?: Role[]
}

export interface Role {
  id: string
  name: string
  permissions?: string[]
}

export interface LoginRequest {
  username: string
  password: string
}

export interface LoginResponse {
  access_token: string
  token_type: string
  user: User
}

export interface Permission {
  parts_create: boolean
  parts_read: boolean
  parts_update: boolean
  parts_delete: boolean
  locations_create: boolean
  locations_read: boolean
  locations_update: boolean
  locations_delete: boolean
  categories_create: boolean
  categories_read: boolean
  categories_update: boolean
  categories_delete: boolean
  users_create: boolean
  users_read: boolean
  users_update: boolean
  users_delete: boolean
  printer_use: boolean
  admin_access: boolean
}
