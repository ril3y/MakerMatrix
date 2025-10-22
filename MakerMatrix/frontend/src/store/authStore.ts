import { create } from 'zustand'
import { devtools, persist } from 'zustand/middleware'
import type { User, LoginRequest } from '@/types/auth'
import { authService } from '@/services/auth.service'
import { toast } from 'react-hot-toast'

interface AuthState {
  user: User | null
  isAuthenticated: boolean
  isLoading: boolean
  error: string | null

  // Actions
  login: (credentials: LoginRequest) => Promise<void>
  guestLogin: () => Promise<void>
  logout: () => Promise<void>
  checkAuth: () => Promise<void>
  updatePassword: (currentPassword: string, newPassword: string) => Promise<void>
  clearError: () => void
  hasRole: (role: string) => boolean
  hasPermission: (permission: string) => boolean
}

export const useAuthStore = create<AuthState>()(
  devtools(
    persist(
      (set, get) => ({
        user: null,
        isAuthenticated: false,
        isLoading: false,
        error: null,

        login: async (credentials) => {
          set({ isLoading: true, error: null })
          try {
            const response = await authService.login(credentials)
            set({
              user: response.user,
              isAuthenticated: true,
              isLoading: false,
            })
            toast.success('Login successful!')
          } catch (error: any) {
            set({
              isLoading: false,
              error: error.response?.data?.detail || 'Login failed',
            })
            throw error
          }
        },

        guestLogin: async () => {
          set({ isLoading: true, error: null })
          try {
            const response = await authService.guestLogin()
            set({
              user: response.user,
              isAuthenticated: true,
              isLoading: false,
            })
            toast.success('Viewing as guest - read-only access')
          } catch (error: any) {
            set({
              isLoading: false,
              error: error.response?.data?.detail || 'Guest login failed',
            })
            throw error
          }
        },

        logout: async () => {
          set({ isLoading: true })
          try {
            await authService.logout()
          } finally {
            set({
              user: null,
              isAuthenticated: false,
              isLoading: false,
            })
            toast.success('Logged out successfully')
          }
        },

        checkAuth: async () => {
          const { isAuthenticated: currentAuthState } = get()

          // If we already have auth state from persistence, validate the token
          if (currentAuthState && authService.isAuthenticated()) {
            set({ isLoading: true })
            try {
              const user = await authService.getCurrentUser()
              set({
                user,
                isAuthenticated: true,
                isLoading: false,
              })
            } catch (error) {
              // Token is invalid, clear auth state
              authService.clearAuth()
              set({
                user: null,
                isAuthenticated: false,
                isLoading: false,
              })
            }
          } else if (!authService.isAuthenticated()) {
            // No valid token, ensure state is cleared
            set({ user: null, isAuthenticated: false, isLoading: false })
          }
        },

        updatePassword: async (currentPassword, newPassword) => {
          set({ isLoading: true, error: null })
          try {
            await authService.updatePassword(currentPassword, newPassword)
            toast.success('Password updated successfully')
            set({ isLoading: false })
          } catch (error: any) {
            set({
              isLoading: false,
              error: error.response?.data?.detail || 'Failed to update password',
            })
            throw error
          }
        },

        clearError: () => set({ error: null }),

        hasRole: (role) => {
          const { user } = get()
          return user?.roles?.some((r) => r.name === role) || false
        },

        hasPermission: (permission) => {
          const { user } = get()
          if (!user?.roles) return false

          return user.roles.some((role) => role.permissions?.includes(permission))
        },
      }),
      {
        name: 'auth-storage',
        partialize: (state) => ({
          user: state.user,
          isAuthenticated: state.isAuthenticated,
        }),
      }
    )
  )
)
