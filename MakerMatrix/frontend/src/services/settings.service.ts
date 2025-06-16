import { apiClient, ApiResponse } from './api'
import { AIConfig, AIConfigUpdate, BackupStatus } from '@/types/settings'

// Re-export types for convenience
export type { AIConfig, AIConfigUpdate, BackupStatus } from '@/types/settings'

export class SettingsService {
  // Modern Printer Configuration
  async getAvailablePrinters(): Promise<any[]> {
    const response = await apiClient.get<{printers: any[]}>('/printer/printers')
    return response.printers || []
  }

  async getPrinterInfo(printerId: string): Promise<any> {
    const response = await apiClient.get<any>(`/printer/printers/${printerId}`)
    return response
  }

  async getPrinterStatus(printerId: string): Promise<{printer_id: string, status: string}> {
    const response = await apiClient.get<{printer_id: string, status: string}>(`/printer/printers/${printerId}/status`)
    return response
  }

  async testPrinterConnection(printerId: string): Promise<any> {
    const response = await apiClient.post<any>(`/printer/printers/${printerId}/test`)
    return response
  }

  async printTestLabel(printerId: string, text: string = "Test Label", labelSize: string = "12"): Promise<any> {
    const response = await apiClient.post<any>('/printer/print/text', {
      printer_id: printerId,
      text,
      label_size: labelSize,
      copies: 1
    })
    return response
  }

  async previewLabel(text: string, labelSize: string = "12"): Promise<Blob> {
    const response = await fetch(`${(import.meta as any).env?.VITE_API_URL || 'http://localhost:57891'}/printer/preview/text`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${localStorage.getItem('auth_token')}`
      },
      body: JSON.stringify({
        text,
        label_size: labelSize
      })
    })
    
    if (!response.ok) {
      throw new Error('Failed to generate preview')
    }
    
    return await response.blob()
  }

  async printAdvancedLabel(requestData: {
    printer_id: string
    template: string
    text: string
    label_size: string
    label_length?: number
    options: {
      fit_to_label: boolean
      include_qr: boolean
      qr_data?: string
    }
    data?: any
  }): Promise<any> {
    const response = await apiClient.post<any>('/printer/print/advanced', requestData)
    return response
  }

  async previewAdvancedLabel(requestData: {
    template: string
    text: string
    label_size: string
    label_length?: number
    options: {
      fit_to_label: boolean
      include_qr: boolean
      qr_data?: string
    }
    data?: any
  }): Promise<Blob> {
    const response = await fetch(`${(import.meta as any).env?.VITE_API_URL || 'http://localhost:57891'}/printer/preview/advanced`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${localStorage.getItem('auth_token')}`
      },
      body: JSON.stringify(requestData)
    })
    
    if (!response.ok) {
      throw new Error('Failed to generate advanced preview')
    }
    
    return await response.blob()
  }

  async registerPrinter(printerData: {
    printer_id: string
    name: string
    driver_type: string
    model: string
    backend: string
    identifier: string
    dpi: number
    scaling_factor: number
  }): Promise<any> {
    const response = await apiClient.post<any>('/printer/register', printerData)
    return response
  }

  async getSupportedDrivers(): Promise<any[]> {
    const response = await apiClient.get<ApiResponse<{drivers: any[]}>>('/printer/drivers')
    return response.data?.drivers || []
  }

  async testPrinterSetup(printerData: any): Promise<any> {
    const response = await apiClient.post<ApiResponse<any>>('/printer/test-setup', { printer: printerData })
    return response.data!
  }

  async discoverPrinters(): Promise<any> {
    const response = await apiClient.get<ApiResponse<any>>('/printer/discover')
    return response.data!
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