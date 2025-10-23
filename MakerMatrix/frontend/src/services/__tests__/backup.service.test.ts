import { describe, it, expect, vi, beforeEach } from 'vitest'
import { backupService } from '../backup.service'
import { apiClient } from '../api'
import type { BackupConfig, BackupInfo } from '@/types/backup'

// Mock dependencies
vi.mock('../api')

const mockApiClient = vi.mocked(apiClient)

// Mock localStorage
const localStorageMock = {
  getItem: vi.fn(),
  setItem: vi.fn(),
  removeItem: vi.fn(),
  clear: vi.fn(),
}
vi.stubGlobal('localStorage', localStorageMock)

// Mock window.URL for blob downloads
const createObjectURLMock = vi.fn()
const revokeObjectURLMock = vi.fn()
vi.stubGlobal('URL', {
  createObjectURL: createObjectURLMock,
  revokeObjectURL: revokeObjectURLMock,
})

// Mock fetch for download functionality
global.fetch = vi.fn()

describe('BackupService', () => {
  const mockBackupConfig: BackupConfig = {
    id: 'config-123',
    schedule_enabled: true,
    schedule_type: 'nightly',
    schedule_cron: null,
    retention_count: 7,
    last_backup_at: '2025-01-01T00:00:00Z',
    next_backup_at: '2025-01-02T02:00:00Z',
    encryption_required: true,
    encryption_password: null, // Never sent from backend
    created_at: '2025-01-01T00:00:00Z',
    updated_at: '2025-01-01T00:00:00Z',
  }

  const mockBackupInfo: BackupInfo = {
    filename: 'makermatrix_backup_20250101_120000_encrypted.zip',
    encrypted: true,
    size_bytes: 1048576,
    size_mb: 1.0,
    created_at: '2025-01-01T12:00:00Z',
    download_url: '/api/backup/download/makermatrix_backup_20250101_120000_encrypted.zip',
  }

  beforeEach(() => {
    vi.clearAllMocks()
    localStorageMock.getItem.mockReturnValue('mock-auth-token')
  })

  describe('getBackupConfig', () => {
    it('should fetch backup configuration successfully', async () => {
      mockApiClient.get.mockResolvedValueOnce({
        status: 'success',
        data: mockBackupConfig,
      })

      const result = await backupService.getBackupConfig()

      expect(mockApiClient.get).toHaveBeenCalledWith('/api/backup/config')
      expect(result).toEqual(mockBackupConfig)
    })

    it('should verify password is never in response', async () => {
      mockApiClient.get.mockResolvedValueOnce({
        status: 'success',
        data: mockBackupConfig,
      })

      const result = await backupService.getBackupConfig()

      // Verify password field is null (security check)
      expect(result.encryption_password).toBeNull()
    })

    it('should throw error when fetch fails', async () => {
      mockApiClient.get.mockResolvedValueOnce({
        status: 'error',
        message: 'Failed to fetch config',
      })

      await expect(backupService.getBackupConfig()).rejects.toThrow('Failed to fetch config')
    })
  })

  describe('isPasswordSet', () => {
    it('should return true when password is configured', async () => {
      mockApiClient.get.mockResolvedValueOnce({
        status: 'success',
        data: { password_set: true },
      })

      const result = await backupService.isPasswordSet()

      expect(mockApiClient.get).toHaveBeenCalledWith('/api/backup/config/password-set')
      expect(result).toBe(true)
    })

    it('should return false when no password is configured', async () => {
      mockApiClient.get.mockResolvedValueOnce({
        status: 'success',
        data: { password_set: false },
      })

      const result = await backupService.isPasswordSet()

      expect(result).toBe(false)
    })

    it('should return false when API call fails', async () => {
      mockApiClient.get.mockResolvedValueOnce({
        status: 'error',
      })

      const result = await backupService.isPasswordSet()

      expect(result).toBe(false)
    })
  })

  describe('updateBackupConfig', () => {
    it('should update config with new password', async () => {
      const configUpdate = {
        schedule_enabled: true,
        encryption_required: true,
        encryption_password: 'NewPassword123',
      }

      mockApiClient.put.mockResolvedValueOnce({
        status: 'success',
        data: { ...mockBackupConfig, ...configUpdate },
      })

      const result = await backupService.updateBackupConfig(configUpdate)

      expect(mockApiClient.put).toHaveBeenCalledWith('/api/backup/config', configUpdate)
      expect(result).toBeDefined()
    })

    it('should update config without password (keep existing)', async () => {
      const configUpdate = {
        schedule_enabled: false,
        retention_count: 14,
      }

      mockApiClient.put.mockResolvedValueOnce({
        status: 'success',
        data: { ...mockBackupConfig, ...configUpdate },
      })

      await backupService.updateBackupConfig(configUpdate)

      expect(mockApiClient.put).toHaveBeenCalledWith('/api/backup/config', configUpdate)
    })
  })

  describe('createBackup', () => {
    it('should create encrypted backup with password', async () => {
      const backupRequest = {
        password: 'TestPassword123',
        include_datasheets: true,
        include_images: true,
        include_env: true,
      }

      mockApiClient.post.mockResolvedValueOnce({
        status: 'success',
        data: {
          task_id: 'task-123',
          task_type: 'backup_creation',
          encrypted: true,
        },
      })

      const result = await backupService.createBackup(backupRequest)

      expect(mockApiClient.post).toHaveBeenCalledWith('/api/backup/create', expect.any(FormData), {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      })

      // Verify FormData contains password
      const formData = mockApiClient.post.mock.calls[0][1] as FormData
      expect(formData.get('password')).toBe('TestPassword123')

      expect(result.encrypted).toBe(true)
    })

    it('should create unencrypted backup without password', async () => {
      const backupRequest = {
        include_datasheets: false,
        include_images: false,
        include_env: false,
      }

      mockApiClient.post.mockResolvedValueOnce({
        status: 'success',
        data: {
          task_id: 'task-456',
          task_type: 'backup_creation',
          encrypted: false,
        },
      })

      const result = await backupService.createBackup(backupRequest)

      const formData = mockApiClient.post.mock.calls[0][1] as FormData
      expect(formData.get('password')).toBeNull()

      expect(result.encrypted).toBe(false)
    })
  })

  describe('listBackups', () => {
    it('should list all backups', async () => {
      const mockBackupList = [mockBackupInfo]

      mockApiClient.get.mockResolvedValueOnce({
        status: 'success',
        data: {
          backups: mockBackupList,
          total_count: 1,
          total_size_mb: 1.0,
        },
      })

      const result = await backupService.listBackups()

      expect(mockApiClient.get).toHaveBeenCalledWith('/api/backup/list')
      expect(result).toEqual(mockBackupList)
    })

    it('should identify encrypted backups', async () => {
      const encryptedBackup = mockBackupInfo
      const unencryptedBackup = {
        ...mockBackupInfo,
        filename: 'makermatrix_backup_20250101_100000.zip',
        encrypted: false,
      }

      mockApiClient.get.mockResolvedValueOnce({
        status: 'success',
        data: {
          backups: [encryptedBackup, unencryptedBackup],
          total_count: 2,
          total_size_mb: 2.0,
        },
      })

      const result = await backupService.listBackups()

      expect(result[0].encrypted).toBe(true)
      expect(result[1].encrypted).toBe(false)
    })
  })

  describe('downloadBackup', () => {
    it('should download backup file', async () => {
      const mockBlob = new Blob(['test data'], { type: 'application/zip' })
      const mockFetch = vi.mocked(global.fetch)

      mockFetch.mockResolvedValueOnce({
        ok: true,
        blob: () => Promise.resolve(mockBlob),
      } as Response)

      createObjectURLMock.mockReturnValue('blob:mock-url')

      // Mock document.createElement to track link creation
      const mockLink = {
        href: '',
        download: '',
        click: vi.fn(),
        remove: vi.fn(),
      }
      const createElementSpy = vi.spyOn(document, 'createElement').mockReturnValue(mockLink as any)
      const appendChildSpy = vi
        .spyOn(document.body, 'appendChild')
        .mockImplementation(() => mockLink as any)

      await backupService.downloadBackup('test_backup.zip')

      expect(mockFetch).toHaveBeenCalledWith('/api/backup/download/test_backup.zip', {
        headers: {
          Authorization: 'Bearer mock-auth-token',
        },
      })

      expect(createObjectURLMock).toHaveBeenCalledWith(mockBlob)
      expect(mockLink.click).toHaveBeenCalled()
      expect(mockLink.remove).toHaveBeenCalled()
      expect(revokeObjectURLMock).toHaveBeenCalledWith('blob:mock-url')

      createElementSpy.mockRestore()
      appendChildSpy.mockRestore()
    })

    it('should handle download failure', async () => {
      const mockFetch = vi.mocked(global.fetch)

      mockFetch.mockResolvedValueOnce({
        ok: false,
      } as Response)

      await expect(backupService.downloadBackup('test_backup.zip')).rejects.toThrow(
        'Failed to download backup'
      )
    })
  })

  describe('deleteBackup', () => {
    it('should delete backup successfully', async () => {
      mockApiClient.delete.mockResolvedValueOnce({
        status: 'success',
        message: 'Backup deleted',
      })

      await backupService.deleteBackup('test_backup.zip')

      expect(mockApiClient.delete).toHaveBeenCalledWith('/api/backup/delete/test_backup.zip')
    })

    it('should handle delete failure', async () => {
      mockApiClient.delete.mockResolvedValueOnce({
        status: 'error',
        message: 'Failed to delete backup',
      })

      await expect(backupService.deleteBackup('test_backup.zip')).rejects.toThrow(
        'Failed to delete backup'
      )
    })
  })

  describe('BackupService singleton export', () => {
    it('should export a singleton instance with all methods', () => {
      expect(backupService).toBeDefined()
      expect(backupService.getBackupConfig).toBeDefined()
      expect(backupService.isPasswordSet).toBeDefined()
      expect(backupService.createBackup).toBeDefined()
      expect(backupService.updateBackupConfig).toBeDefined()
      expect(backupService.listBackups).toBeDefined()
      expect(backupService.downloadBackup).toBeDefined()
      expect(backupService.deleteBackup).toBeDefined()
    })
  })
})
