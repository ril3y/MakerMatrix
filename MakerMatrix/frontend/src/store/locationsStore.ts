import { create } from 'zustand'
import { devtools } from 'zustand/middleware'
import { Location, CreateLocationRequest, UpdateLocationRequest } from '@/types/locations'
import { locationsService } from '@/services/locations.service'
import { toast } from 'react-hot-toast'

interface LocationsState {
  // Location data
  locations: Location[]
  currentLocation: Location | null
  locationTree: Location[]
  
  // UI state
  isLoading: boolean
  isLoadingLocation: boolean
  error: string | null
  
  // Actions
  loadLocations: () => Promise<void>
  loadLocation: (id: string) => Promise<void>
  createLocation: (data: CreateLocationRequest) => Promise<Location>
  updateLocation: (data: UpdateLocationRequest) => Promise<Location>
  deleteLocation: (id: string) => Promise<void>
  
  // Utility methods
  getLocationById: (id: string) => Location | undefined
  getLocationsByParent: (parentId: string | null) => Location[]
  buildLocationTree: () => void
  
  // UI helpers
  clearError: () => void
  setCurrentLocation: (location: Location | null) => void
}

export const useLocationsStore = create<LocationsState>()(
  devtools(
    (set, get) => ({
      // Initial state
      locations: [],
      currentLocation: null,
      locationTree: [],
      isLoading: false,
      isLoadingLocation: false,
      error: null,

      // Load all locations
      loadLocations: async () => {
        set({ isLoading: true, error: null })
        try {
          const locations = await locationsService.getAllLocations()
          set({ 
            locations, 
            isLoading: false 
          })
          // Build tree structure
          get().buildLocationTree()
        } catch (error: any) {
          set({
            isLoading: false,
            error: error.message || 'Failed to load locations',
          })
        }
      },

      // Load single location
      loadLocation: async (id) => {
        set({ isLoadingLocation: true, error: null })
        try {
          const location = await locationsService.getLocation({ id })
          set({ currentLocation: location, isLoadingLocation: false })
        } catch (error: any) {
          set({
            isLoadingLocation: false,
            error: error.message || 'Failed to load location',
          })
        }
      },

      // Create new location
      createLocation: async (data) => {
        set({ isLoading: true, error: null })
        try {
          const newLocation = await locationsService.createLocation(data)
          
          // Refresh the locations list
          await get().loadLocations()
          
          toast.success('Location created successfully')
          return newLocation
        } catch (error: any) {
          set({ isLoading: false })
          throw error
        }
      },

      // Update location
      updateLocation: async (data) => {
        set({ isLoading: true, error: null })
        try {
          const updatedLocation = await locationsService.updateLocation(data)
          
          // Update the current location if it's the one being edited
          if (get().currentLocation?.id === data.id) {
            set({ currentLocation: updatedLocation })
          }
          
          // Refresh the locations list
          await get().loadLocations()
          
          toast.success('Location updated successfully')
          return updatedLocation
        } catch (error: any) {
          set({ isLoading: false })
          throw error
        }
      },

      // Delete location
      deleteLocation: async (id) => {
        set({ isLoading: true, error: null })
        try {
          await locationsService.deleteLocation(id)
          
          // Clear current location if it's the one being deleted
          if (get().currentLocation?.id === id) {
            set({ currentLocation: null })
          }
          
          // Refresh the locations list
          await get().loadLocations()
          
          toast.success('Location deleted successfully')
        } catch (error: any) {
          set({ isLoading: false })
          throw error
        }
      },

      // Utility methods
      getLocationById: (id) => {
        return get().locations.find(location => location.id === id)
      },

      getLocationsByParent: (parentId) => {
        return get().locations.filter(location => location.parent_id === parentId)
      },

      buildLocationTree: () => {
        const locations = get().locations
        const tree = locationsService.buildLocationTree(locations)
        set({ locationTree: tree })
      },

      // UI helpers
      clearError: () => set({ error: null }),
      setCurrentLocation: (location) => set({ currentLocation: location }),
    })
  )
)