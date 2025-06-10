import { create } from 'zustand'
import { devtools } from 'zustand/middleware'
import { dashboardService, DashboardStats } from '@/services/dashboard.service'

interface DashboardState {
  stats: DashboardStats | null
  isLoading: boolean
  error: string | null
  lastUpdated: Date | null
  
  // Actions
  loadStats: () => Promise<void>
  refreshStats: () => Promise<void>
  clearError: () => void
}

export const useDashboardStore = create<DashboardState>()(
  devtools(
    (set, get) => ({
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
          const stats = await dashboardService.getDashboardStats()
          set({ 
            stats, 
            isLoading: false, 
            lastUpdated: new Date() 
          })
        } catch (error: any) {
          set({ 
            isLoading: false, 
            error: error.response?.data?.error || 'Failed to load dashboard data' 
          })
        }
      },

      refreshStats: async () => {
        set({ isLoading: true, error: null, lastUpdated: null })
        
        try {
          const stats = await dashboardService.getDashboardStats()
          set({ 
            stats, 
            isLoading: false, 
            lastUpdated: new Date() 
          })
        } catch (error: any) {
          set({ 
            isLoading: false, 
            error: error.response?.data?.error || 'Failed to refresh dashboard data' 
          })
        }
      },

      clearError: () => set({ error: null }),
    })
  )
)