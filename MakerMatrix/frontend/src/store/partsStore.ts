import { create } from 'zustand'
import { devtools } from 'zustand/middleware'
import { 
  Part, 
  CreatePartRequest, 
  UpdatePartRequest, 
  SearchPartsRequest,
  Location,
  Category
} from '@/types/parts'
import { partsService } from '@/services/parts.service'
import { locationsService } from '@/services/locations.service'
import { categoriesService } from '@/services/categories.service'
import { PaginatedResponse } from '@/services/api'
import { toast } from 'react-hot-toast'

interface PartsState {
  // Parts data
  parts: Part[]
  currentPart: Part | null
  totalParts: number
  currentPage: number
  pageSize: number
  totalPages: number
  
  // Locations and categories
  locations: Location[]
  categories: Category[]
  
  // UI state
  isLoading: boolean
  isLoadingPart: boolean
  error: string | null
  searchQuery: string
  selectedFilters: SearchPartsRequest
  
  // Actions
  loadParts: (page?: number) => Promise<void>
  searchParts: (query: string, filters?: SearchPartsRequest) => Promise<void>
  loadPart: (id: string) => Promise<void>
  createPart: (data: CreatePartRequest) => Promise<Part>
  updatePart: (data: UpdatePartRequest) => Promise<Part>
  deletePart: (id: string) => Promise<void>
  
  // Reference data
  loadLocations: () => Promise<void>
  loadCategories: () => Promise<void>
  
  // Filters
  setSearchQuery: (query: string) => void
  setFilters: (filters: SearchPartsRequest) => void
  clearFilters: () => void
  
  // UI helpers
  clearError: () => void
  setCurrentPart: (part: Part | null) => void
}

export const usePartsStore = create<PartsState>()(
  devtools(
    (set, get) => ({
      // Initial state
      parts: [],
      currentPart: null,
      totalParts: 0,
      currentPage: 1,
      pageSize: 20,
      totalPages: 0,
      locations: [],
      categories: [],
      isLoading: false,
      isLoadingPart: false,
      error: null,
      searchQuery: '',
      selectedFilters: {},

      // Load parts with pagination
      loadParts: async (page = 1) => {
        set({ isLoading: true, error: null })
        try {
          const response: PaginatedResponse<Part> = await partsService.getAllParts(page, get().pageSize)
          set({
            parts: response.items,
            totalParts: response.total,
            currentPage: response.page,
            totalPages: response.total_pages,
            isLoading: false,
          })
        } catch (error: any) {
          set({
            isLoading: false,
            error: error.response?.data?.error || 'Failed to load parts',
          })
        }
      },

      // Search parts
      searchParts: async (query, filters = {}) => {
        set({ isLoading: true, error: null, searchQuery: query })
        try {
          const searchParams = {
            query,
            ...get().selectedFilters,
            ...filters,
            page: 1,
            page_size: get().pageSize,
          }
          const response: PaginatedResponse<Part> = await partsService.searchParts(searchParams)
          set({
            parts: response.items,
            totalParts: response.total,
            currentPage: response.page,
            totalPages: response.total_pages,
            isLoading: false,
          })
        } catch (error: any) {
          set({
            isLoading: false,
            error: error.response?.data?.error || 'Search failed',
          })
        }
      },

      // Load single part
      loadPart: async (id) => {
        set({ isLoadingPart: true, error: null })
        try {
          const part = await partsService.getPart(id)
          set({ currentPart: part, isLoadingPart: false })
        } catch (error: any) {
          set({
            isLoadingPart: false,
            error: error.response?.data?.error || 'Failed to load part',
          })
        }
      },

      // Create new part
      createPart: async (data) => {
        set({ isLoading: true, error: null })
        try {
          const newPart = await partsService.createPart(data)
          
          // Refresh the parts list
          await get().loadParts(get().currentPage)
          
          toast.success('Part created successfully')
          return newPart
        } catch (error: any) {
          set({ isLoading: false })
          throw error
        }
      },

      // Update part
      updatePart: async (data) => {
        set({ isLoading: true, error: null })
        try {
          const updatedPart = await partsService.updatePart(data)
          
          // Update the current part if it's the one being edited
          if (get().currentPart?.id === data.id) {
            set({ currentPart: updatedPart })
          }
          
          // Refresh the parts list
          await get().loadParts(get().currentPage)
          
          toast.success('Part updated successfully')
          return updatedPart
        } catch (error: any) {
          set({ isLoading: false })
          throw error
        }
      },

      // Delete part
      deletePart: async (id) => {
        set({ isLoading: true, error: null })
        try {
          await partsService.deletePart(id)
          
          // Clear current part if it's the one being deleted
          if (get().currentPart?.id === id) {
            set({ currentPart: null })
          }
          
          // Refresh the parts list
          await get().loadParts(get().currentPage)
          
          toast.success('Part deleted successfully')
        } catch (error: any) {
          set({ isLoading: false })
          throw error
        }
      },

      // Load reference data
      loadLocations: async () => {
        try {
          const locations = await locationsService.getAllLocations()
          set({ locations })
        } catch (error) {
          console.error('Failed to load locations:', error)
        }
      },

      loadCategories: async () => {
        try {
          const categories = await categoriesService.getAllCategories()
          set({ categories })
        } catch (error) {
          console.error('Failed to load categories:', error)
        }
      },

      // Filter management
      setSearchQuery: (query) => set({ searchQuery: query }),
      
      setFilters: (filters) => {
        set({ selectedFilters: { ...get().selectedFilters, ...filters } })
      },
      
      clearFilters: () => {
        set({ 
          selectedFilters: {}, 
          searchQuery: '' 
        })
        get().loadParts(1)
      },

      // UI helpers
      clearError: () => set({ error: null }),
      setCurrentPart: (part) => set({ currentPart: part }),
    })
  )
)