/**
 * Backup Service
 *
 * Handles all backup-related API calls
 */

import type { ApiResponse } from '@/services/api'
import { apiClient } from '@/services/api'
import type {
  BackupConfig,
  BackupInfo,
  BackupListResponse,
  BackupStatus,
  CreateBackupRequest,
  RestoreBackupRequest,
  BackupTaskResponse,
} from '@/types/backup'

class BackupService {
  /**
   * Get current backup configuration
   */
  async getBackupConfig(): Promise<BackupConfig> {
    const response = await apiClient.get<ApiResponse<BackupConfig>>('/api/backup/config')
    if (response.status === 'success' && response.data) {
      return response.data
    }
    throw new Error(response.message || 'Failed to get backup configuration')
  }

  /**
   * Update backup configuration
   */
  async updateBackupConfig(config: Partial<BackupConfig>): Promise<BackupConfig> {
    const response = await apiClient.put<ApiResponse<BackupConfig>>('/api/backup/config', config)
    if (response.status === 'success' && response.data) {
      return response.data
    }
    throw new Error(response.message || 'Failed to update backup configuration')
  }

  /**
   * Get comprehensive backup system status
   */
  async getBackupStatus(): Promise<BackupStatus> {
    const response = await apiClient.get<ApiResponse<BackupStatus>>('/api/backup/status')
    if (response.status === 'success' && response.data) {
      return response.data
    }
    throw new Error(response.message || 'Failed to get backup status')
  }

  /**
   * List all available backups
   */
  async listBackups(): Promise<BackupInfo[]> {
    const response = await apiClient.get<ApiResponse<BackupListResponse>>('/api/backup/list')
    if (response.status === 'success' && response.data) {
      return response.data.backups
    }
    throw new Error(response.message || 'Failed to list backups')
  }

  /**
   * Create a new backup
   */
  async createBackup(request: CreateBackupRequest): Promise<BackupTaskResponse> {
    const formData = new FormData()

    if (request.password) {
      formData.append('password', request.password)
    }

    formData.append('include_datasheets', String(request.include_datasheets ?? true))
    formData.append('include_images', String(request.include_images ?? true))
    formData.append('include_env', String(request.include_env ?? true))

    const response = await apiClient.post<ApiResponse<BackupTaskResponse>>(
      '/api/backup/create',
      formData,
      {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      }
    )

    if (response.status === 'success' && response.data) {
      return response.data
    }
    throw new Error(response.message || 'Failed to create backup')
  }

  /**
   * Restore from a backup file
   */
  async restoreBackup(request: RestoreBackupRequest): Promise<BackupTaskResponse> {
    const formData = new FormData()
    formData.append('backup_file', request.backup_file)

    if (request.password) {
      formData.append('password', request.password)
    }

    formData.append('create_safety_backup', String(request.create_safety_backup ?? true))

    const response = await apiClient.post<ApiResponse<BackupTaskResponse>>(
      '/api/backup/restore',
      formData,
      {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      }
    )

    if (response.status === 'success' && response.data) {
      return response.data
    }
    throw new Error(response.message || 'Failed to restore backup')
  }

  /**
   * Download a backup file
   */
  async downloadBackup(filename: string): Promise<void> {
    // Use direct window.location for file downloads
    const token = localStorage.getItem('auth_token')
    const url = `/api/backup/download/${filename}`

    // Create a temporary link with auth header via fetch
    const response = await fetch(url, {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    })

    if (!response.ok) {
      throw new Error('Failed to download backup')
    }

    const blob = await response.blob()
    const downloadUrl = window.URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = downloadUrl
    link.setAttribute('download', filename)
    document.body.appendChild(link)
    link.click()
    link.remove()
    window.URL.revokeObjectURL(downloadUrl)
  }

  /**
   * Delete a backup file
   */
  async deleteBackup(filename: string): Promise<void> {
    const response = await apiClient.delete<ApiResponse<any>>(`/api/backup/delete/${filename}`)
    if (response.status !== 'success') {
      throw new Error(response.message || 'Failed to delete backup')
    }
  }

  /**
   * Run retention cleanup manually
   */
  async runRetentionCleanup(): Promise<BackupTaskResponse> {
    const response = await apiClient.post<ApiResponse<BackupTaskResponse>>(
      '/api/backup/retention/run'
    )
    if (response.status === 'success' && response.data) {
      return response.data
    }
    throw new Error(response.message || 'Failed to run retention cleanup')
  }

  /**
   * Check if scheduled backup encryption password is set
   */
  async isPasswordSet(): Promise<boolean> {
    const response = await apiClient.get<ApiResponse<{ password_set: boolean }>>(
      '/api/backup/config/password-set'
    )
    if (response.status === 'success' && response.data) {
      return response.data.password_set
    }
    return false
  }
}

export const backupService = new BackupService()
