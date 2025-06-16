import { create } from 'zustand'
import { devtools } from 'zustand/middleware'
import { 
  settingsService, 
  AIConfig, 
  AIConfigUpdate, 
  BackupStatus 
} from '@/services/settings.service'
import { toast } from 'react-hot-toast'

interface SettingsState {
  // AI Settings
  aiConfig: AIConfig | null
  isAILoading: boolean
  
  // Backup Settings
  backupStatus: BackupStatus | null
  isBackupLoading: boolean
  
  // User Management
  users: any[]
  roles: any[]
  isUsersLoading: boolean
  isRolesLoading: boolean
  
  // General
  error: string | null
  
  // Actions
  loadAIConfig: () => Promise<void>
  updateAIConfig: (config: AIConfigUpdate) => Promise<void>
  testAIConnection: () => Promise<void>
  resetAIConfig: () => Promise<void>
  
  loadBackupStatus: () => Promise<void>
  downloadBackup: () => Promise<void>
  exportData: () => Promise<void>
  
  loadUsers: () => Promise<void>
  loadRoles: () => Promise<void>
  createUser: (userData: any) => Promise<void>
  updateUserRoles: (userId: string, roleIds: string[]) => Promise<void>
  deleteUser: (userId: string) => Promise<void>
  
  clearError: () => void
}

export const useSettingsStore = create<SettingsState>()(
  devtools(
    (set, get) => ({
      // Initial state
      aiConfig: null,
      isAILoading: false,
      backupStatus: null,
      isBackupLoading: false,
      users: [],
      roles: [],
      isUsersLoading: false,
      isRolesLoading: false,
      error: null,

      // AI Config Actions
      loadAIConfig: async () => {
        set({ isAILoading: true, error: null })
        try {
          const config = await settingsService.getAIConfig()
          set({ aiConfig: config, isAILoading: false })
        } catch (error: any) {
          set({ 
            isAILoading: false, 
            error: error.response?.data?.error || 'Failed to load AI config' 
          })
        }
      },

      updateAIConfig: async (config) => {
        set({ isAILoading: true, error: null })
        try {
          await settingsService.updateAIConfig(config)
          // Reload the full config
          await get().loadAIConfig()
          toast.success('AI configuration updated successfully')
        } catch (error: any) {
          set({ isAILoading: false })
          throw error
        }
      },

      testAIConnection: async () => {
        set({ isAILoading: true, error: null })
        try {
          const result = await settingsService.testAIConnection()
          set({ isAILoading: false })
          if (result.success) {
            toast.success('AI connection test successful')
          } else {
            toast.error(result.message || 'AI connection test failed')
          }
        } catch (error: any) {
          set({ isAILoading: false })
          toast.error('AI connection test failed')
        }
      },

      resetAIConfig: async () => {
        set({ isAILoading: true, error: null })
        try {
          await settingsService.resetAIConfig()
          await get().loadAIConfig()
          toast.success('AI configuration reset to defaults')
        } catch (error: any) {
          set({ isAILoading: false })
          throw error
        }
      },

      // Backup Actions
      loadBackupStatus: async () => {
        set({ isBackupLoading: true, error: null })
        try {
          const status = await settingsService.getBackupStatus()
          set({ backupStatus: status, isBackupLoading: false })
        } catch (error: any) {
          set({ 
            isBackupLoading: false, 
            error: error.response?.data?.error || 'Failed to load backup status' 
          })
        }
      },

      downloadBackup: async () => {
        set({ isBackupLoading: true, error: null })
        try {
          await settingsService.downloadDatabaseBackup()
          set({ isBackupLoading: false })
          toast.success('Database backup downloaded successfully')
        } catch (error: any) {
          set({ isBackupLoading: false })
          toast.error('Failed to download backup')
        }
      },

      exportData: async () => {
        set({ isBackupLoading: true, error: null })
        try {
          await settingsService.exportDataJSON()
          set({ isBackupLoading: false })
          toast.success('Data exported successfully')
        } catch (error: any) {
          set({ isBackupLoading: false })
          toast.error('Failed to export data')
        }
      },

      // User Management Actions
      loadUsers: async () => {
        set({ isUsersLoading: true, error: null })
        try {
          const users = await settingsService.getAllUsers()
          set({ users, isUsersLoading: false })
        } catch (error: any) {
          set({ 
            isUsersLoading: false, 
            error: error.response?.data?.error || 'Failed to load users' 
          })
        }
      },

      loadRoles: async () => {
        set({ isRolesLoading: true, error: null })
        try {
          const roles = await settingsService.getAllRoles()
          set({ roles, isRolesLoading: false })
        } catch (error: any) {
          set({ 
            isRolesLoading: false, 
            error: error.response?.data?.error || 'Failed to load roles' 
          })
        }
      },

      createUser: async (userData) => {
        set({ isUsersLoading: true, error: null })
        try {
          await settingsService.createUser(userData)
          await get().loadUsers()
          toast.success('User created successfully')
        } catch (error: any) {
          set({ isUsersLoading: false })
          throw error
        }
      },

      updateUserRoles: async (userId, roleIds) => {
        set({ isUsersLoading: true, error: null })
        try {
          await settingsService.updateUserRoles(userId, roleIds)
          await get().loadUsers()
          toast.success('User roles updated successfully')
        } catch (error: any) {
          set({ isUsersLoading: false })
          throw error
        }
      },

      deleteUser: async (userId) => {
        set({ isUsersLoading: true, error: null })
        try {
          await settingsService.deleteUser(userId)
          await get().loadUsers()
          toast.success('User deleted successfully')
        } catch (error: any) {
          set({ isUsersLoading: false })
          throw error
        }
      },

      clearError: () => set({ error: null }),
    })
  )
)