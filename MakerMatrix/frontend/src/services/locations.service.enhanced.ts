import { BaseNamedCrudService } from './baseCrud.service'
import type {
  Location,
  CreateLocationRequest,
  UpdateLocationRequest,
  LocationDetails,
  LocationPath,
  LocationDeletePreview,
  LocationCleanupResponse,
} from '@/types/locations'

import type { ApiResponse } from './api'
import { apiClient } from './api'

export class EnhancedLocationsService extends BaseNamedCrudService<
  Location,
  CreateLocationRequest,
  UpdateLocationRequest
> {
  protected baseUrl = '/api/locations'
  protected entityName = 'location'

  // Map frontend create request to backend format
  protected mapCreateRequestToBackend(data: CreateLocationRequest): any {
    return {
      name: data.name,
      description: data.description || '',
      parent_id: data.parent_id || null,
      location_type: data.location_type || 'standard',
      image_url: data.image_url || null,
    }
  }

  // Map frontend update request to backend format
  protected mapUpdateRequestToBackend(data: UpdateLocationRequest): any {
    return {
      name: data.name,
      description: data.description || '',
      parent_id: data.parent_id || null,
      location_type: data.location_type || 'standard',
      image_url: data.image_url || null,
    }
  }

  // Map backend response to frontend entity
  protected mapResponseToEntity(response: any): Location {
    return {
      id: response.id,
      name: response.name,
      description: response.description || '',
      parent_id: response.parent_id || null,
      location_type: response.location_type || 'standard',
      image_url: response.image_url || null,
      created_at: response.created_at,
      updated_at: response.updated_at,
      children: response.children || [],
      parts: response.parts || [],
    }
  }

  // Override getAll to handle the specific locations response format
  async getAll(): Promise<Location[]> {
    try {
      const response = await apiClient.get<ApiResponse<Location[]>>(
        '/api/locations/get_all_locations'
      )
      if (response.status === 'success' && response.data) {
        return response.data.map((location) => this.mapResponseToEntity(location))
      }
      return []
    } catch (error: any) {
      throw new Error(error.message || 'Failed to load locations')
    }
  }

  // Override delete to handle location-specific endpoint
  async delete(id: string): Promise<void> {
    try {
      const response = await apiClient.delete<ApiResponse>(`/api/locations/delete_location/${id}`)
      if (response.status !== 'success') {
        throw new Error(response.message || 'Failed to delete location')
      }
    } catch (error: any) {
      throw new Error(error.message || 'Failed to delete location')
    }
  }

  // Location-specific methods
  async getLocationDetails(id: string): Promise<LocationDetails> {
    try {
      const response = await apiClient.get<ApiResponse<LocationDetails>>(
        `/api/locations/get_location_details/${id}`
      )
      if (response.status === 'success' && response.data) {
        return response.data
      }
      throw new Error('Failed to get location details')
    } catch (error: any) {
      throw new Error(error.message || 'Failed to get location details')
    }
  }

  async getLocationPath(id: string): Promise<LocationPath> {
    try {
      const response = await apiClient.get<ApiResponse<LocationPath>>(
        `/api/locations/get_location_path/${id}`
      )
      if (response.status === 'success' && response.data) {
        return response.data
      }
      throw new Error('Failed to get location path')
    } catch (error: any) {
      throw new Error(error.message || 'Failed to get location path')
    }
  }

  async previewLocationDelete(id: string): Promise<LocationDeletePreview> {
    try {
      const response = await apiClient.get<ApiResponse<LocationDeletePreview>>(
        `/api/locations/preview-location-delete/${id}`
      )
      if (response.status === 'success' && response.data) {
        return response.data
      }
      throw new Error('Failed to preview location deletion')
    } catch (error: any) {
      throw new Error(error.message || 'Failed to preview location deletion')
    }
  }

  async cleanupLocations(): Promise<LocationCleanupResponse> {
    try {
      const response = await apiClient.delete<ApiResponse<LocationCleanupResponse>>(
        '/api/locations/cleanup-locations'
      )
      if (response.status === 'success' && response.data) {
        return response.data
      }
      throw new Error('Failed to cleanup locations')
    } catch (error: any) {
      throw new Error(error.message || 'Failed to cleanup locations')
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

  // Helper method to check if a location is a descendant of another
  isDescendantOf(childId: string, parentId: string, locations: Location[]): boolean {
    const locationMap = new Map<string, Location>()
    locations.forEach((location) => locationMap.set(location.id, location))

    let current = locationMap.get(childId)
    while (current && current.parent_id) {
      if (current.parent_id === parentId) {
        return true
      }
      current = locationMap.get(current.parent_id)
    }
    return false
  }

  // Helper method to get locations by parent ID
  getLocationsByParent(locations: Location[], parentId: string | null): Location[] {
    return locations.filter((location) => location.parent_id === parentId)
  }

  // Override checkNameExists to consider parent context
  async checkNameExists(name: string, parentId?: string, excludeId?: string): Promise<boolean> {
    try {
      const location = await this.getByName(name)

      if (location && location.id !== excludeId) {
        // Check if it has the same parent
        return location.parent_id === parentId
      }

      return false
    } catch {
      return false
    }
  }

  // Convenience methods for backward compatibility
  async getAllLocations(): Promise<Location[]> {
    return this.getAll()
  }

  async getLocation(params: { id?: string; name?: string }): Promise<Location> {
    if (params.id) {
      return this.getById(params.id)
    }
    if (params.name) {
      return this.getByName(params.name)
    }
    throw new Error('Either id or name must be provided')
  }

  async createLocation(data: CreateLocationRequest): Promise<Location> {
    return this.create(data)
  }

  async updateLocation(data: UpdateLocationRequest): Promise<Location> {
    return this.update(data)
  }

  async deleteLocation(id: string): Promise<void> {
    return this.delete(id)
  }
}

// Export both the enhanced service and the original for backward compatibility
export const enhancedLocationsService = new EnhancedLocationsService()

// Re-export the original service for backward compatibility
export { locationsService } from './locations.service'
