import { apiClient, ApiResponse } from './api'
import { User, CreateUserRequest, UpdateUserRolesRequest, Role, CreateRoleRequest, UpdateRoleRequest, UserStats } from '@/types/users'

export class UsersService {
  // User Management
  async getAllUsers(): Promise<User[]> {
    const response = await apiClient.get<ApiResponse<User[]>>('/users/all')
    return response.data || []
  }

  async createUser(userData: CreateUserRequest): Promise<ApiResponse> {
    return await apiClient.post<ApiResponse>('/users/register', userData)
  }

  async updateUserRoles(userId: string, roleData: UpdateUserRolesRequest): Promise<ApiResponse> {
    return await apiClient.put<ApiResponse>(`/users/${userId}/roles`, roleData)
  }

  async deleteUser(userId: string): Promise<ApiResponse> {
    return await apiClient.delete<ApiResponse>(`/users/${userId}`)
  }

  async toggleUserStatus(userId: string, isActive: boolean): Promise<ApiResponse> {
    return await apiClient.put<ApiResponse>(`/users/${userId}/status`, { is_active: isActive })
  }

  // Role Management
  async getAllRoles(): Promise<Role[]> {
    const response = await apiClient.get<ApiResponse<Role[]>>('/roles/all')
    return response.data || []
  }

  async createRole(roleData: CreateRoleRequest): Promise<ApiResponse> {
    return await apiClient.post<ApiResponse>('/roles/create', roleData)
  }

  async updateRole(roleId: string, roleData: UpdateRoleRequest): Promise<ApiResponse> {
    return await apiClient.put<ApiResponse>(`/roles/${roleId}`, roleData)
  }

  async deleteRole(roleId: string): Promise<ApiResponse> {
    return await apiClient.delete<ApiResponse>(`/roles/${roleId}`)
  }

  // Statistics
  async getUserStats(): Promise<UserStats> {
    const users = await this.getAllUsers()
    const total = users.length
    const active = users.filter(u => u.is_active).length
    const inactive = total - active
    const admins = users.filter(u => u.roles.some(r => r.name.toLowerCase() === 'admin')).length

    return {
      total,
      active,
      inactive,
      admins
    }
  }
}

export const usersService = new UsersService()