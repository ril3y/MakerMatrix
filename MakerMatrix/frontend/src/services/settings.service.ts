import { apiClient, ApiResponse } from './api'
import { PrinterConfig, AIConfig, AIConfigUpdate, BackupStatus } from '@/types/settings'

// Re-export types for convenience
export type { PrinterConfig, AIConfig, AIConfigUpdate, BackupStatus } from '@/types/settings'

export class SettingsService {
  // Printer Configuration
  async getPrinterConfig(): Promise<PrinterConfig> {
    const response = await apiClient.get<{current_printer: PrinterConfig}>('/printer/current_printer')
    return response.current_printer
  }

  async updatePrinterConfig(config: PrinterConfig): Promise<ApiResponse> {
    return await apiClient.post<ApiResponse>('/printer/config', config)
  }

  async loadPrinterConfig(): Promise<ApiResponse> {
    return await apiClient.get<ApiResponse>('/printer/load_config')
  }

  // AI Configuration
  async getAIConfig(): Promise<AIConfig> {
    const response = await apiClient.get<ApiResponse<AIConfig>>('/ai/config')
    return response.data!
  }

  async updateAIConfig(config: AIConfigUpdate): Promise<ApiResponse> {
    return await apiClient.put<ApiResponse>('/ai/config', config)
  }

  async testAIConnection(): Promise<ApiResponse> {
    return await apiClient.post<ApiResponse>('/ai/test')
  }

  async resetAIConfig(): Promise<ApiResponse> {
    return await apiClient.post<ApiResponse>('/ai/reset')
  }

  async getAvailableModels(): Promise<any[]> {
    const response = await apiClient.get<ApiResponse<{models: any[], provider: string}>>('/ai/models')
    return response.data?.models || []
  }

  // Backup & Export
  async getBackupStatus(): Promise<BackupStatus> {
    const response = await apiClient.get<ApiResponse<BackupStatus>>('/utility/backup/status')
    return response.data!
  }

  async downloadDatabaseBackup(): Promise<void> {
    // This will trigger a file download
    const baseURL = (import.meta as any).env?.VITE_API_URL || 'http://localhost:57891'
    const response = await fetch(`${baseURL}/utility/backup/download`, {
      headers: {
        'Authorization': `Bearer ${localStorage.getItem('auth_token')}`
      }
    })
    
    if (!response.ok) {
      throw new Error('Failed to download backup')
    }

    const blob = await response.blob()
    const url = window.URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `makermatrix_backup_${new Date().toISOString().slice(0, 10)}.db`
    document.body.appendChild(a)
    a.click()
    window.URL.revokeObjectURL(url)
    document.body.removeChild(a)
  }

  async exportDataJSON(): Promise<void> {
    // This will trigger a file download
    const baseURL = (import.meta as any).env?.VITE_API_URL || 'http://localhost:57891'
    const response = await fetch(`${baseURL}/utility/backup/export`, {
      headers: {
        'Authorization': `Bearer ${localStorage.getItem('auth_token')}`
      }
    })
    
    if (!response.ok) {
      throw new Error('Failed to export data')
    }

    const blob = await response.blob()
    const url = window.URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `makermatrix_export_${new Date().toISOString().slice(0, 10)}.json`
    document.body.appendChild(a)
    a.click()
    window.URL.revokeObjectURL(url)
    document.body.removeChild(a)
  }

  // User Management (Admin only)
  async createUser(userData: {
    username: string
    email: string
    password: string
    role_ids: string[]
  }): Promise<ApiResponse> {
    return await apiClient.post<ApiResponse>('/users/register', userData)
  }

  async getAllUsers(): Promise<any[]> {
    const response = await apiClient.get<ApiResponse<any[]>>('/users/all')
    return response.data || []
  }

  async updateUserRoles(userId: string, roleIds: string[]): Promise<ApiResponse> {
    return await apiClient.put<ApiResponse>(`/users/${userId}/roles`, { role_ids: roleIds })
  }

  async deleteUser(userId: string): Promise<ApiResponse> {
    return await apiClient.delete<ApiResponse>(`/users/${userId}`)
  }

  // Roles Management
  async getAllRoles(): Promise<any[]> {
    const response = await apiClient.get<ApiResponse<any[]>>('/roles/all')
    return response.data || []
  }

  async createRole(roleData: {
    name: string
    permissions: Record<string, boolean>
  }): Promise<ApiResponse> {
    return await apiClient.post<ApiResponse>('/roles/create', roleData)
  }

  async updateRole(roleId: string, roleData: {
    name?: string
    permissions?: Record<string, boolean>
  }): Promise<ApiResponse> {
    return await apiClient.put<ApiResponse>(`/roles/${roleId}`, roleData)
  }

  async deleteRole(roleId: string): Promise<ApiResponse> {
    return await apiClient.delete<ApiResponse>(`/roles/${roleId}`)
  }
}

export const settingsService = new SettingsService()