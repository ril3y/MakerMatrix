import { apiClient, ApiResponse } from './api'
import { AIConfig, AIConfigUpdate, BackupStatus } from '@/types/settings'

// Re-export types for convenience
export type { AIConfig, AIConfigUpdate, BackupStatus } from '@/types/settings'

export class SettingsService {
  // Modern Printer Configuration
  async getAvailablePrinters(): Promise<any[]> {
    const response = await apiClient.get<{data: any[]}>('/api/printer/printers')
    return response.data || []
  }

  async getPrinterInfo(printerId: string): Promise<any> {
    const response = await apiClient.get<any>(`/api/printer/printers/${printerId}`)
    return response
  }

  async getPrinterStatus(printerId: string): Promise<{printer_id: string, status: string}> {
    const response = await apiClient.get<{printer_id: string, status: string}>(`/api/printer/printers/${printerId}/status`)
    return response
  }

  async testPrinterConnection(printerId: string): Promise<any> {
    const response = await apiClient.post<any>(`/api/printer/printers/${printerId}/test`)
    return response
  }

  async printTestLabel(printerId: string, text: string = "Test Label", labelSize: string = "12"): Promise<any> {
    const response = await apiClient.post<any>('/api/printer/print/text', {
      printer_id: printerId,
      text,
      label_size: labelSize,
      copies: 1
    })
    return response
  }

  async previewLabel(text: string, labelSize: string = "12"): Promise<Blob> {
    const response = await fetch(`${(import.meta as any).env?.VITE_API_URL || 'http://localhost:8080'}/api/preview/text`, {
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
    const response = await apiClient.post<any>('/api/printer/print/advanced', requestData)
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
    console.log('[DEBUG] previewAdvancedLabel called with:', requestData)

    const response = await fetch(`${(import.meta as any).env?.VITE_API_URL || 'http://localhost:8080'}/api/preview/advanced`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${localStorage.getItem('auth_token')}`
      },
      body: JSON.stringify(requestData)
    })

    console.log('[DEBUG] Preview response status:', response.status, response.statusText)

    if (!response.ok) {
      // Try to parse error response as JSON to get detailed error message
      try {
        const errorData = await response.json()
        console.error('[ERROR] Preview API error response:', errorData)

        // Extract meaningful error message
        const errorMessage = errorData.error || errorData.message || 'Failed to generate preview'
        throw new Error(errorMessage)
      } catch (parseError) {
        console.error('[ERROR] Failed to parse error response:', parseError)
        throw new Error(`Preview request failed with status ${response.status}: ${response.statusText}`)
      }
    }

    // The API returns JSON with base64 image data, not a raw blob
    const contentType = response.headers.get('content-type')
    console.log('[DEBUG] Response content-type:', contentType)

    if (contentType && contentType.includes('application/json')) {
      // Parse the JSON response which contains base64 image data
      try {
        const responseData = await response.json()
        console.log('[DEBUG] Received JSON preview response:', responseData)

        // Check if this is an error response
        if (!responseData.success) {
          const errorMessage = responseData.error || responseData.message || 'Preview generation failed'
          throw new Error(errorMessage)
        }

        // Extract base64 image data and convert to blob
        if (responseData.success && responseData.preview_data) {
          const base64Data = responseData.preview_data
          const format = responseData.format || 'png'

          // Convert base64 to blob
          const binaryString = atob(base64Data)
          const bytes = new Uint8Array(binaryString.length)
          for (let i = 0; i < binaryString.length; i++) {
            bytes[i] = binaryString.charCodeAt(i)
          }

          const blob = new Blob([bytes], { type: `image/${format}` })
          console.log('[DEBUG] Successfully converted base64 to blob')
          return blob
        } else {
          throw new Error('Preview response missing image data')
        }
      } catch (parseError) {
        console.error('[ERROR] Failed to parse or convert preview response:', parseError)
        // Re-throw the original error to preserve the message
        throw parseError
      }
    }

    // Fallback to blob response (for backward compatibility)
    console.log('[DEBUG] Returning blob response (fallback)')
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
    const response = await apiClient.post<any>('/api/printer/register', printerData)
    return response
  }

  async updatePrinter(printerId: string, printerData: {
    name: string
    driver_type: string
    model: string
    backend: string
    identifier: string
    dpi: number
    scaling_factor: number
  }): Promise<any> {
    const response = await apiClient.put<any>(`/api/printer/printers/${printerId}`, printerData)
    return response
  }

  async deletePrinter(printerId: string): Promise<any> {
    const response = await apiClient.delete<any>(`/api/printer/printers/${printerId}`)
    return response
  }

  async getSupportedDrivers(): Promise<any[]> {
    const response = await apiClient.get<ApiResponse<{drivers: any[]}>>('/api/printer/drivers')
    return response.data?.drivers || []
  }

  async getDriverInfo(driverType: string): Promise<any> {
    const response = await apiClient.get<ApiResponse<any>>(`/api/printer/drivers/${driverType}`)
    return response.data!
  }

  async testPrinterSetup(printerData: any): Promise<any> {
    const response = await apiClient.post<ApiResponse<any>>('/api/printer/test-setup', { printer: printerData })
    return response.data!
  }

  async startPrinterDiscovery(): Promise<any> {
    const response = await apiClient.post<ApiResponse<any>>('/api/printer/discover/start')
    return response.data!
  }

  async getPrinterDiscoveryStatus(taskId: string): Promise<any> {
    const response = await apiClient.get<ApiResponse<any>>(`/api/printer/discover/status/${taskId}`)
    return response.data!
  }

  async getLatestPrinterDiscovery(): Promise<any> {
    const response = await apiClient.get<ApiResponse<any>>('/api/printer/discover/latest')
    return response.data!
  }

  // AI Configuration
  async getAIConfig(): Promise<AIConfig> {
    const response = await apiClient.get<ApiResponse<AIConfig>>('/api/ai/config')
    return response.data!
  }

  async updateAIConfig(config: AIConfigUpdate): Promise<ApiResponse> {
    return await apiClient.put<ApiResponse>('/api/ai/config', config)
  }

  async testAIConnection(): Promise<ApiResponse> {
    return await apiClient.post<ApiResponse>('/api/ai/test')
  }

  async resetAIConfig(): Promise<ApiResponse> {
    return await apiClient.post<ApiResponse>('/api/ai/reset')
  }

  async getAvailableModels(): Promise<ApiResponse<{models: any[], provider: string, current_model?: string}>> {
    return await apiClient.get<ApiResponse<{models: any[], provider: string, current_model?: string}>>('/api/ai/models')
  }

  // Backup & Export
  async getBackupStatus(): Promise<BackupStatus> {
    const response = await apiClient.get<ApiResponse<BackupStatus>>('/api/utility/backup/status')
    return response.data!
  }

  async downloadDatabaseBackup(): Promise<void> {
    // This will trigger a file download
    const baseURL = (import.meta as any).env?.VITE_API_URL || 'http://localhost:8080'
    const response = await fetch(`${baseURL}/api/utility/backup/download`, {
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
    const baseURL = (import.meta as any).env?.VITE_API_URL || 'http://localhost:8080'
    const response = await fetch(`${baseURL}/api/utility/backup/export`, {
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

  // Database Clear Operations (Admin only)
  async clearAllParts(): Promise<ApiResponse> {
    const response = await apiClient.delete<ApiResponse>('/api/parts/clear_all')
    return response
  }

  async clearAllSuppliers(): Promise<ApiResponse> {
    const response = await apiClient.delete<ApiResponse>('/api/utility/clear_suppliers')
    return response
  }

  async clearAllCategories(): Promise<ApiResponse> {
    const response = await apiClient.delete<ApiResponse>('/api/categories/delete_all_categories')
    return response
  }

  // User Management (Admin only)
  async createUser(userData: {
    username: string
    email: string
    password: string
    role_ids: string[]
  }): Promise<ApiResponse> {
    return await apiClient.post<ApiResponse>('/api/users/register', userData)
  }

  async getAllUsers(): Promise<any[]> {
    const response = await apiClient.get<ApiResponse<any[]>>('/api/users/all')
    return response.data || []
  }

  async updateUserRoles(userId: string, roleIds: string[]): Promise<ApiResponse> {
    return await apiClient.put<ApiResponse>(`/api/users/${userId}/roles`, { role_ids: roleIds })
  }

  async deleteUser(userId: string): Promise<ApiResponse> {
    return await apiClient.delete<ApiResponse>(`/api/users/${userId}`)
  }

  // Roles Management
  async getAllRoles(): Promise<any[]> {
    const response = await apiClient.get<ApiResponse<any[]>>('/api/users/roles/all')
    return response.data || []
  }

  async createRole(roleData: {
    name: string
    permissions: Record<string, boolean>
  }): Promise<ApiResponse> {
    return await apiClient.post<ApiResponse>('/api/users/roles/create', roleData)
  }

  async updateRole(roleId: string, roleData: {
    name?: string
    permissions?: Record<string, boolean>
  }): Promise<ApiResponse> {
    return await apiClient.put<ApiResponse>(`/api/users/roles/${roleId}`, roleData)
  }

  async deleteRole(roleId: string): Promise<ApiResponse> {
    return await apiClient.delete<ApiResponse>(`/api/users/roles/${roleId}`)
  }
}

export const settingsService = new SettingsService()
