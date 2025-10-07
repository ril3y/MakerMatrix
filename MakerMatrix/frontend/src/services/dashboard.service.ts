import type { ApiResponse } from './api'
import { apiClient } from './api'

export interface DashboardCounts {
  parts: number
  locations: number
  categories: number
}

export interface DashboardStats {
  totalParts: number
  totalLocations: number
  totalCategories: number
  activeUsers: number
}

export class DashboardService {
  async getCounts(): Promise<DashboardCounts> {
    const response = await apiClient.get<ApiResponse<DashboardCounts>>('/api/utility/get_counts')
    return response.data!
  }

  async getPartCounts(): Promise<number> {
    const response = await apiClient.get<ApiResponse<number>>('/api/parts/get_part_counts')
    return response.data!
  }

  async getAllUsers(): Promise<any[]> {
    try {
      const response = await apiClient.get<ApiResponse<any[]>>('/api/users/all')
      return response.data || []
    } catch (error) {
      // If not admin, return empty array
      return []
    }
  }

  async getDashboardStats(): Promise<DashboardStats> {
    try {
      const [counts, users] = await Promise.all([this.getCounts(), this.getAllUsers()])

      return {
        totalParts: counts.parts,
        totalLocations: counts.locations,
        totalCategories: counts.categories,
        activeUsers: users.filter((user) => user.is_active).length,
      }
    } catch (error) {
      // Fallback to individual calls if utility endpoint fails
      const partCount = await this.getPartCounts()
      const users = await this.getAllUsers()

      return {
        totalParts: partCount,
        totalLocations: 0,
        totalCategories: 0,
        activeUsers: users.filter((user) => user.is_active).length,
      }
    }
  }
}

export const dashboardService = new DashboardService()
