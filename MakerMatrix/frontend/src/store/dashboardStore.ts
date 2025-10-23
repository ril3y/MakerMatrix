import { create } from 'zustand'
import { devtools } from 'zustand/middleware'
import type { DashboardData } from '@/services/dashboard.service'
import { dashboardService } from '@/services/dashboard.service'

interface DashboardState {
  stats: DashboardData | null
  isLoading: boolean
  error: string | null
  lastUpdated: Date | null

  // Actions
  loadStats: () => Promise<void>
  refreshStats: () => Promise<void>
  clearError: () => void
}

export const useDashboardStore = create<DashboardState>()(
  devtools((set, get) => ({
    stats: null,
    isLoading: false,
    error: null,
    lastUpdated: null,

    loadStats: async () => {
      const { lastUpdated } = get()

      // Only reload if data is older than 5 minutes or doesn't exist
      if (lastUpdated && Date.now() - lastUpdated.getTime() < 5 * 60 * 1000) {
        return
      }

      set({ isLoading: true, error: null })

      try {
        const stats = await dashboardService.getDashboardSummary()
        set({
          stats,
          isLoading: false,
          lastUpdated: new Date(),
        })
      } catch (error: unknown) {
        const errorMessage =
          error &&
          typeof error === 'object' &&
          'response' in error &&
          error.response &&
          typeof error.response === 'object' &&
          'data' in error.response &&
          error.response.data &&
          typeof error.response.data === 'object' &&
          'error' in error.response.data &&
          typeof error.response.data.error === 'string'
            ? error.response.data.error
            : 'Failed to load dashboard data'
        set({
          isLoading: false,
          error: errorMessage,
        })
      }
    },

    refreshStats: async () => {
      set({ isLoading: true, error: null, lastUpdated: null })

      try {
        const stats = await dashboardService.getDashboardSummary()
        set({
          stats,
          isLoading: false,
          lastUpdated: new Date(),
        })
      } catch (error: unknown) {
        const errorMessage =
          error &&
          typeof error === 'object' &&
          'response' in error &&
          error.response &&
          typeof error.response === 'object' &&
          'data' in error.response &&
          error.response.data &&
          typeof error.response.data === 'object' &&
          'error' in error.response.data &&
          typeof error.response.data.error === 'string'
            ? error.response.data.error
            : 'Failed to refresh dashboard data'
        set({
          isLoading: false,
          error: errorMessage,
        })
      }
    },

    clearError: () => set({ error: null }),
  }))
)
