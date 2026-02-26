import type { ApiResponse } from './api'
import { apiClient } from './api'
import type {
  AIConfig,
  AIConfigUpdate,
  BackupStatus,
  Printer,
  PrinterInfo,
  PrinterStatus,
  PrinterTestResult,
  PrintAdvancedLabelRequest,
  PreviewAdvancedLabelRequest,
  PreviewResponse,
  RegisterPrinterRequest,
  UpdatePrinterRequest,
  PrinterDriver,
  DriverInfo,
  DiscoveryStatus,
  LatestDiscovery,
  AvailableModelsResponse,
} from '@/types/settings'
import type { User, Role } from '@/types/users'

// Re-export types for convenience
export type { AIConfig, AIConfigUpdate, BackupStatus } from '@/types/settings'

// Helper function to get API base URL
function getApiBaseUrl(): string {
  return (
    (import.meta as { env?: { VITE_API_URL?: string } }).env?.VITE_API_URL ||
    'http://localhost:8080'
  )
}

export class SettingsService {
  // Modern Printer Configuration
  async getAvailablePrinters(): Promise<Printer[]> {
    const response = await apiClient.get<ApiResponse<Printer[]>>('/api/printer/printers')
    return response.data || []
  }

  async getPrinterInfo(printerId: string): Promise<PrinterInfo> {
    const response = await apiClient.get<ApiResponse<PrinterInfo>>(
      `/api/printer/printers/${printerId}`
    )
    if (!response.data) {
      throw new Error('Printer info not found')
    }
    return response.data
  }

  async getPrinterStatus(printerId: string): Promise<PrinterStatus> {
    const response = await apiClient.get<ApiResponse<PrinterStatus>>(
      `/api/printer/printers/${printerId}/status`
    )
    if (!response.data) {
      throw new Error('Printer status not found')
    }
    return response.data
  }

  async testPrinterConnection(printerId: string): Promise<PrinterTestResult> {
    const response = await apiClient.post<ApiResponse<PrinterTestResult>>(
      `/api/printer/printers/${printerId}/test`
    )
    if (!response.data) {
      throw new Error('Printer test failed')
    }
    return response.data
  }

  async printTestLabel(
    printerId: string,
    text: string = 'Test Label',
    labelSize: string = '12'
  ): Promise<ApiResponse> {
    const response = await apiClient.post<ApiResponse>('/api/printer/print/text', {
      printer_id: printerId,
      text,
      label_size: labelSize,
      copies: 1,
    })
    return response
  }

  async previewLabel(text: string, labelSize: string = '12'): Promise<Blob> {
    const response = await fetch(`${getApiBaseUrl()}/api/preview/text`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${localStorage.getItem('auth_token')}`,
      },
      body: JSON.stringify({
        text,
        label_size: labelSize,
      }),
    })

    if (!response.ok) {
      throw new Error('Failed to generate preview')
    }

    return await response.blob()
  }

  async printAdvancedLabel(requestData: PrintAdvancedLabelRequest): Promise<ApiResponse> {
    const response = await apiClient.post<ApiResponse>('/api/printer/print/advanced', requestData)
    return response
  }

  async previewAdvancedLabel(requestData: PreviewAdvancedLabelRequest): Promise<Blob> {
    console.log('[DEBUG] previewAdvancedLabel called with:', requestData)

    const response = await fetch(`${getApiBaseUrl()}/api/preview/advanced`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${localStorage.getItem('auth_token')}`,
      },
      body: JSON.stringify(requestData),
    })

    console.log('[DEBUG] Preview response status:', response.status, response.statusText)

    if (!response.ok) {
      // Try to parse error response as JSON to get detailed error message
      try {
        const errorData = (await response.json()) as PreviewResponse
        console.error('[ERROR] Preview API error response:', errorData)

        // Extract meaningful error message
        const errorMessage = errorData.error || errorData.message || 'Failed to generate preview'
        throw new Error(errorMessage)
      } catch (parseError) {
        console.error('[ERROR] Failed to parse error response:', parseError)
        throw new Error(
          `Preview request failed with status ${response.status}: ${response.statusText}`
        )
      }
    }

    // The API returns JSON with base64 image data, not a raw blob
    const contentType = response.headers.get('content-type')
    console.log('[DEBUG] Response content-type:', contentType)

    if (contentType && contentType.includes('application/json')) {
      // Parse the JSON response which contains base64 image data
      try {
        const responseData = (await response.json()) as PreviewResponse
        console.log('[DEBUG] Received JSON preview response:', responseData)

        // Check if this is an error response
        if (!responseData.success) {
          const errorMessage =
            responseData.error || responseData.message || 'Preview generation failed'
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

  async registerPrinter(printerData: RegisterPrinterRequest): Promise<ApiResponse> {
    const response = await apiClient.post<ApiResponse>('/api/printer/register', printerData)
    return response
  }

  async updatePrinter(printerId: string, printerData: UpdatePrinterRequest): Promise<ApiResponse> {
    const response = await apiClient.put<ApiResponse>(
      `/api/printer/printers/${printerId}`,
      printerData
    )
    return response
  }

  async deletePrinter(printerId: string): Promise<ApiResponse> {
    const response = await apiClient.delete<ApiResponse>(`/api/printer/printers/${printerId}`)
    return response
  }

  async getSupportedDrivers(): Promise<PrinterDriver[]> {
    const response =
      await apiClient.get<ApiResponse<{ drivers: PrinterDriver[] }>>('/api/printer/drivers')
    return response.data?.drivers || []
  }

  async getDriverInfo(driverType: string): Promise<DriverInfo> {
    const response = await apiClient.get<ApiResponse<DriverInfo>>(
      `/api/printer/drivers/${driverType}`
    )
    if (!response.data) {
      throw new Error('Driver info not found')
    }
    return response.data
  }

  async testPrinterSetup(printerData: Printer): Promise<PrinterTestResult> {
    const response = await apiClient.post<ApiResponse<PrinterTestResult>>(
      '/api/printer/test-setup',
      {
        printer: printerData,
      }
    )
    if (!response.data) {
      throw new Error('Test setup failed')
    }
    return response.data
  }

  async startPrinterDiscovery(): Promise<DiscoveryStatus> {
    const response = await apiClient.post<ApiResponse<DiscoveryStatus>>(
      '/api/printer/discover/start'
    )
    if (!response.data) {
      throw new Error('Failed to start printer discovery')
    }
    return response.data
  }

  async getPrinterDiscoveryStatus(taskId: string): Promise<DiscoveryStatus> {
    const response = await apiClient.get<ApiResponse<DiscoveryStatus>>(
      `/api/printer/discover/status/${taskId}`
    )
    if (!response.data) {
      throw new Error('Discovery status not found')
    }
    return response.data
  }

  async getLatestPrinterDiscovery(): Promise<LatestDiscovery> {
    const response = await apiClient.get<ApiResponse<LatestDiscovery>>(
      '/api/printer/discover/latest'
    )
    if (!response.data) {
      throw new Error('No discovery results found')
    }
    return response.data
  }

  // AI Configuration
  async getAIConfig(): Promise<AIConfig> {
    const response = await apiClient.get<ApiResponse<AIConfig>>('/api/ai/config')
    if (!response.data) {
      throw new Error('AI config not found')
    }
    return response.data
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

  async getAvailableModels(): Promise<ApiResponse<AvailableModelsResponse>> {
    return await apiClient.get<ApiResponse<AvailableModelsResponse>>('/api/ai/models')
  }

  // Backup & Export
  async getBackupStatus(): Promise<BackupStatus> {
    const response = await apiClient.get<ApiResponse<BackupStatus>>('/api/utility/backup/status')
    if (!response.data) {
      throw new Error('Backup status not found')
    }
    return response.data
  }

  async downloadDatabaseBackup(): Promise<void> {
    // This will trigger a file download
    const baseURL = getApiBaseUrl()
    const response = await fetch(`${baseURL}/api/utility/backup/download`, {
      headers: {
        Authorization: `Bearer ${localStorage.getItem('auth_token')}`,
      },
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
    const baseURL = getApiBaseUrl()
    const response = await fetch(`${baseURL}/api/utility/backup/export`, {
      headers: {
        Authorization: `Bearer ${localStorage.getItem('auth_token')}`,
      },
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

  async getAllUsers(): Promise<User[]> {
    const response = await apiClient.get<ApiResponse<User[]>>('/api/users/all')
    return response.data || []
  }

  async updateUserRoles(userId: string, roleIds: string[]): Promise<ApiResponse> {
    return await apiClient.put<ApiResponse>(`/api/users/${userId}/roles`, { role_ids: roleIds })
  }

  async deleteUser(userId: string): Promise<ApiResponse> {
    return await apiClient.delete<ApiResponse>(`/api/users/${userId}`)
  }

  // Roles Management
  async getAllRoles(): Promise<Role[]> {
    const response = await apiClient.get<ApiResponse<Role[]>>('/api/users/roles/all')
    return response.data || []
  }

  async createRole(roleData: {
    name: string
    permissions: Record<string, boolean>
  }): Promise<ApiResponse> {
    return await apiClient.post<ApiResponse>('/api/users/roles/create', roleData)
  }

  async updateRole(
    roleId: string,
    roleData: {
      name?: string
      permissions?: Record<string, boolean>
    }
  ): Promise<ApiResponse> {
    return await apiClient.put<ApiResponse>(`/api/users/roles/${roleId}`, roleData)
  }

  async deleteRole(roleId: string): Promise<ApiResponse> {
    return await apiClient.delete<ApiResponse>(`/api/users/roles/${roleId}`)
  }
}

export const settingsService = new SettingsService()
