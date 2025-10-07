import type { ApiResponse } from './api'
import { apiClient } from './api'
import type {
  Location,
  CreateLocationRequest,
  UpdateLocationRequest,
  LocationDetails,
  LocationPath,
  LocationDeletePreview,
  LocationDeleteResponse,
  LocationCleanupResponse,
} from '@/types/locations'

export class LocationsService {
  async createLocation(data: CreateLocationRequest): Promise<Location> {
    const response = await apiClient.post<any>('/api/locations/add_location', data)
    // Backend returns ResponseSchema format: { status, message, data }
    if (response.status === 'success' && response.data) {
      return response.data
    }
    throw new Error(response.message || 'Failed to create location')
  }

  async getLocation(params: { id?: string; name?: string }): Promise<Location> {
    if (!params.id && !params.name) {
      throw new Error('Either id or name must be provided')
    }

    const queryParams = new URLSearchParams()
    if (params.id) queryParams.append('location_id', params.id)
    if (params.name) queryParams.append('name', params.name)

    const response = await apiClient.get<any>(`/api/locations/get_location?${queryParams}`)
    if (response.status === 'success' && response.data) {
      return response.data
    }
    throw new Error(response.message || 'Failed to get location')
  }

  async updateLocation(data: UpdateLocationRequest): Promise<Location> {
    const { id, ...updateData } = data
    const response = await apiClient.put<any>(`/api/locations/update_location/${id}`, updateData)
    if (response.status === 'success' && response.data) {
      return response.data
    }
    throw new Error(response.message || 'Failed to update location')
  }

  async deleteLocation(id: string): Promise<LocationDeleteResponse> {
    const response = await apiClient.delete<ApiResponse<LocationDeleteResponse>>(
      `/api/locations/delete_location/${id}`
    )
    return response.data!
  }

  async getAllLocations(): Promise<Location[]> {
    const response = await apiClient.get<any>('/api/locations/get_all_locations')
    if (response.status === 'success' && response.data) {
      return response.data
    }
    return []
  }

  async getLocationDetails(id: string): Promise<LocationDetails> {
    const response = await apiClient.get<ApiResponse<LocationDetails>>(
      `/api/locations/get_location_details/${id}`
    )
    return response.data!
  }

  async getLocationPath(id: string): Promise<LocationPath> {
    const response = await apiClient.get<ApiResponse<LocationPath>>(
      `/api/locations/get_location_path/${id}`
    )
    return response.data!
  }

  async previewLocationDelete(id: string): Promise<LocationDeletePreview> {
    const response = await apiClient.get<ApiResponse<LocationDeletePreview>>(
      `/api/locations/preview-location-delete/${id}`
    )
    return response.data!
  }

  async cleanupLocations(): Promise<LocationCleanupResponse> {
    const response = await apiClient.delete<ApiResponse<LocationCleanupResponse>>(
      '/api/locations/cleanup-locations'
    )
    return response.data!
  }

  async getAll(): Promise<Location[]> {
    return this.getAllLocations()
  }

  async checkNameExists(name: string, parentId?: string, excludeId?: string): Promise<boolean> {
    try {
      // Try to get a location with this name
      const location = await this.getLocation({ name })

      // If we found a location and it's not the one we're excluding
      if (location && location.id !== excludeId) {
        // Check if it has the same parent
        return location.parent_id === parentId
      }

      return false
    } catch {
      return false
    }
  }

  // Helper method to build location hierarchy tree
  buildLocationTree(locations: Location[]): Location[] {
    const locationMap = new Map<string, Location>()
    const rootLocations: Location[] = []

    // First pass: create map of all locations
    locations.forEach((location) => {
      locationMap.set(location.id, { ...location, children: [] })
    })

    // Second pass: build tree structure
    locations.forEach((location) => {
      const locationNode = locationMap.get(location.id)!

      if (location.parent_id) {
        const parent = locationMap.get(location.parent_id)
        if (parent) {
          parent.children = parent.children || []
          parent.children.push(locationNode)
        } else {
          // Parent doesn't exist, treat as root
          rootLocations.push(locationNode)
        }
      } else {
        rootLocations.push(locationNode)
      }
    })

    return rootLocations
  }

  // Helper method to flatten location tree
  flattenLocationTree(locations: Location[]): Location[] {
    const flattened: Location[] = []

    const traverse = (location: Location) => {
      flattened.push(location)
      if (location.children) {
        location.children.forEach((child) => traverse(child))
      }
    }

    locations.forEach((location) => traverse(location))
    return flattened
  }

  // Helper method to get all descendant IDs
  getDescendantIds(location: Location): string[] {
    const ids: string[] = []

    const traverse = (loc: Location) => {
      if (loc.children) {
        loc.children.forEach((child) => {
          ids.push(child.id)
          traverse(child)
        })
      }
    }

    traverse(location)
    return ids
  }
}

export const locationsService = new LocationsService()
