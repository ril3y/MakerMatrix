import { apiClient, ApiResponse } from './api'
import { User, LoginRequest, LoginResponse } from '@/types/auth'

export class AuthService {
  async login(credentials: LoginRequest): Promise<LoginResponse> {
    const response = await apiClient.post<LoginResponse>('/api/auth/login', credentials)

    if (response.access_token) {
      apiClient.setAuthToken(response.access_token)
      localStorage.setItem('user', JSON.stringify(response.user))
    }

    return response
  }

  async logout(): Promise<void> {
    try {
      await apiClient.post('/api/auth/logout')
    } finally {
      this.clearAuth()
    }
  }

  clearAuth(): void {
    apiClient.clearAuth()
  }

  async getCurrentUser(): Promise<User> {
    const response = await apiClient.get<ApiResponse<User>>('/api/users/me')
    if (response.status === 'success' && response.data) {
      return response.data
    }
    throw new Error(response.message || 'Failed to get current user')
  }

  async updatePassword(currentPassword: string, newPassword: string): Promise<void> {
    const response = await apiClient.put<ApiResponse>('/api/users/update_password', {
      current_password: currentPassword,
      new_password: newPassword,
    })
    if (response.status !== 'success') {
      throw new Error(response.message || 'Failed to update password')
    }
  }

  getStoredUser(): User | null {
    const userStr = localStorage.getItem('user')
    if (userStr) {
      try {
        return JSON.parse(userStr)
      } catch {
        return null
      }
    }
    return null
  }

  isAuthenticated(): boolean {
    return !!localStorage.getItem('auth_token')
  }

  hasRole(role: string): boolean {
    const user = this.getStoredUser()
    return user?.roles?.some((r) => r.name === role) || false
  }

  hasPermission(permission: string): boolean {
    const user = this.getStoredUser()
    if (!user?.roles) return false

    return user.roles.some((role) => role.permissions?.includes(permission))
  }
}

export const authService = new AuthService()
