import type { ApiResponse, PaginatedResponse } from './api'
import { apiClient } from './api'
import type { Tool, CreateToolRequest, UpdateToolRequest, SearchToolsRequest } from '@/types/tools'

export class ToolsService {
  async createTool(data: CreateToolRequest): Promise<Tool> {
    const response = await apiClient.post<ApiResponse<Tool>>('/api/tools/', data)

    if (response.status === 'success' && response.data) {
      return response.data
    }
    throw new Error(response.message || 'Failed to create tool')
  }

  async getTool(id: string): Promise<Tool> {
    const response = await apiClient.get<ApiResponse<Tool>>(`/api/tools/${id}`)
    if (response.status === 'success' && response.data) {
      return response.data
    }
    throw new Error(response.message || 'Failed to get tool')
  }

  async updateTool(id: string, data: UpdateToolRequest): Promise<Tool> {
    const response = await apiClient.put<ApiResponse<Tool>>(`/api/tools/${id}`, data)
    if (response.status === 'success' && response.data) {
      return response.data
    }
    throw new Error(response.message || 'Failed to update tool')
  }

  async deleteTool(id: string): Promise<void> {
    const response = await apiClient.delete<ApiResponse>(`/api/tools/${id}`)
    if (response.status !== 'success') {
      throw new Error(response.message || 'Failed to delete tool')
    }
  }

  async getAllTools(page = 1, pageSize = 20): Promise<PaginatedResponse<Tool>> {
    const response = await apiClient.get<ApiResponse<any>>('/api/tools/', {
      params: { page, page_size: pageSize },
    })

    if (response.status === 'success' && response.data) {
      // Backend returns data.tools, frontend expects items
      return {
        items: response.data.tools || [],
        total: response.data.total || 0,
        page: response.data.page || 1,
        page_size: response.data.page_size || 20,
        total_pages: response.data.total_pages || 1,
      }
    }

    throw new Error(response.message || 'Failed to get tools')
  }

  async searchTools(params: SearchToolsRequest): Promise<PaginatedResponse<Tool>> {
    const response = await apiClient.post<ApiResponse<any>>('/api/tools/search', params)

    if (response.status === 'success' && response.data) {
      // Backend returns data.tools, frontend expects items
      return {
        items: response.data.tools || [],
        total: response.data.total || 0,
        page: response.data.page || 1,
        page_size: response.data.page_size || 20,
        total_pages: response.data.total_pages || 1,
      }
    }

    throw new Error(response.message || 'Failed to search tools')
  }

  async checkoutTool(id: string, userId: string, notes?: string): Promise<Tool> {
    const response = await apiClient.post<ApiResponse<Tool>>(`/api/tools/${id}/checkout`, {
      user_id: userId,
      notes: notes || undefined,
    })

    if (response.status === 'success' && response.data) {
      return response.data
    }
    throw new Error(response.message || 'Failed to checkout tool')
  }

  async checkinTool(id: string, notes?: string): Promise<Tool> {
    const response = await apiClient.post<ApiResponse<Tool>>(`/api/tools/${id}/return`, {
      notes,
    })

    if (response.status === 'success' && response.data) {
      return response.data
    }
    throw new Error(response.message || 'Failed to checkin tool')
  }

  async getToolSuggestions(query: string, limit = 10): Promise<string[]> {
    if (query.length < 3) {
      return []
    }

    try {
      const response = await apiClient.get<ApiResponse<string[]>>('/api/tools/suggestions', {
        params: { query, limit },
      })
      if (response.status === 'success' && response.data) {
        return response.data
      }
      return []
    } catch (error) {
      console.error('Error fetching tool suggestions:', error)
      return []
    }
  }

  async checkNameExists(name: string, excludeId?: string): Promise<boolean> {
    try {
      const response = await apiClient.get<ApiResponse<boolean>>('/api/tools/check_name_exists', {
        params: { name, exclude_id: excludeId },
      })
      return (response.status === 'success' && response.data) || false
    } catch {
      return false
    }
  }

  // === MAINTENANCE RECORD OPERATIONS ===

  async createMaintenanceRecord(toolId: string, data: {
    maintenance_date: string
    maintenance_type: string
    notes?: string
    next_maintenance_date?: string
    cost?: number
  }): Promise<any> {
    const response = await apiClient.post<ApiResponse<any>>(`/api/tools/${toolId}/maintenance`, data)
    if (response.status === 'success' && response.data) {
      return response.data
    }
    throw new Error(response.message || 'Failed to create maintenance record')
  }

  async getMaintenanceRecords(toolId: string): Promise<any[]> {
    const response = await apiClient.get<ApiResponse<any[]>>(`/api/tools/${toolId}/maintenance`)
    if (response.status === 'success' && response.data) {
      return response.data
    }
    throw new Error(response.message || 'Failed to get maintenance records')
  }

  async updateMaintenanceRecord(toolId: string, recordId: string, data: {
    maintenance_date?: string
    maintenance_type?: string
    notes?: string
    next_maintenance_date?: string
    cost?: number
  }): Promise<any> {
    const response = await apiClient.put<ApiResponse<any>>(`/api/tools/${toolId}/maintenance/${recordId}`, data)
    if (response.status === 'success' && response.data) {
      return response.data
    }
    throw new Error(response.message || 'Failed to update maintenance record')
  }

  async deleteMaintenanceRecord(toolId: string, recordId: string): Promise<void> {
    const response = await apiClient.delete<ApiResponse>(`/api/tools/${toolId}/maintenance/${recordId}`)
    if (response.status !== 'success') {
      throw new Error(response.message || 'Failed to delete maintenance record')
    }
  }
}

export const toolsService = new ToolsService()