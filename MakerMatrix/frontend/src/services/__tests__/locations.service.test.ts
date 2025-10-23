import { describe, it, expect, vi, beforeEach } from 'vitest'
import { LocationsService, locationsService } from '../locations.service'
import { apiClient } from '../api'
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

// Mock dependencies
vi.mock('../api')

const mockApiClient = vi.mocked(apiClient)

describe('LocationsService', () => {
  const mockLocation: Location = {
    id: 'loc-123',
    name: 'Main Warehouse',
    description: 'Primary storage facility',
    parent_id: undefined,
    location_type: 'warehouse',
    created_at: '2024-01-01T00:00:00Z',
    updated_at: '2024-01-01T00:00:00Z',
  }

  const mockChildLocation: Location = {
    id: 'loc-456',
    name: 'Electronics Section',
    description: 'Electronic components storage',
    parent_id: 'loc-123',
    location_type: 'room',
    created_at: '2024-01-01T00:00:00Z',
    updated_at: '2024-01-01T00:00:00Z',
  }

  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('createLocation', () => {
    it('should create location successfully', async () => {
      const createRequest: CreateLocationRequest = {
        name: 'New Warehouse',
        location_type: 'warehouse',
        parent_id: undefined,
      }

      const mockResponse = {
        status: 'success',
        message: 'Location created successfully',
        data: mockLocation,
      }

      mockApiClient.post.mockResolvedValueOnce(mockResponse)

      const result = await locationsService.createLocation(createRequest)

      expect(mockApiClient.post).toHaveBeenCalledWith('/api/locations/add_location', createRequest)
      expect(result).toEqual(mockLocation)
    })

    it('should throw error when creation fails', async () => {
      const createRequest: CreateLocationRequest = {
        name: 'New Warehouse',
        location_type: 'warehouse',
      }

      const mockResponse = {
        status: 'error',
        message: 'Location already exists',
      }

      mockApiClient.post.mockResolvedValueOnce(mockResponse)

      await expect(locationsService.createLocation(createRequest)).rejects.toThrow(
        'Location already exists'
      )
    })

    it('should handle API error during creation', async () => {
      const createRequest: CreateLocationRequest = {
        name: 'New Warehouse',
        location_type: 'warehouse',
      }

      mockApiClient.post.mockRejectedValueOnce(new Error('Network error'))

      await expect(locationsService.createLocation(createRequest)).rejects.toThrow('Network error')
    })
  })

  describe('getLocation', () => {
    it('should get location by ID successfully', async () => {
      const mockResponse = {
        status: 'success',
        data: mockLocation,
      }

      mockApiClient.get.mockResolvedValueOnce(mockResponse)

      const result = await locationsService.getLocation({ id: 'loc-123' })

      expect(mockApiClient.get).toHaveBeenCalledWith(
        '/api/locations/get_location?location_id=loc-123'
      )
      expect(result).toEqual(mockLocation)
    })

    it('should get location by name successfully', async () => {
      const mockResponse = {
        status: 'success',
        data: mockLocation,
      }

      mockApiClient.get.mockResolvedValueOnce(mockResponse)

      const result = await locationsService.getLocation({ name: 'Main Warehouse' })

      expect(mockApiClient.get).toHaveBeenCalledWith(
        '/api/locations/get_location?name=Main+Warehouse'
      )
      expect(result).toEqual(mockLocation)
    })

    it('should throw error when neither id nor name provided', async () => {
      await expect(locationsService.getLocation({})).rejects.toThrow(
        'Either id or name must be provided'
      )
    })

    it('should handle location not found', async () => {
      const mockResponse = {
        status: 'error',
        message: 'Location not found',
      }

      mockApiClient.get.mockResolvedValueOnce(mockResponse)

      await expect(locationsService.getLocation({ id: 'invalid' })).rejects.toThrow(
        'Location not found'
      )
    })
  })

  describe('updateLocation', () => {
    it('should update location successfully', async () => {
      const updateRequest: UpdateLocationRequest = {
        id: 'loc-123',
        name: 'Updated Warehouse',
        description: 'Updated description',
      }

      const updatedLocation = { ...mockLocation, name: 'Updated Warehouse' }
      const mockResponse = {
        status: 'success',
        data: updatedLocation,
      }

      mockApiClient.put.mockResolvedValueOnce(mockResponse)

      const result = await locationsService.updateLocation(updateRequest)

      expect(mockApiClient.put).toHaveBeenCalledWith('/api/locations/update_location/loc-123', {
        name: 'Updated Warehouse',
        description: 'Updated description',
      })
      expect(result).toEqual(updatedLocation)
    })

    it('should handle update failure', async () => {
      const updateRequest: UpdateLocationRequest = {
        id: 'loc-123',
        name: 'Updated Warehouse',
      }

      const mockResponse = {
        status: 'error',
        message: 'Update failed',
      }

      mockApiClient.put.mockResolvedValueOnce(mockResponse)

      await expect(locationsService.updateLocation(updateRequest)).rejects.toThrow('Update failed')
    })
  })

  describe('deleteLocation', () => {
    it('should delete location successfully', async () => {
      const mockDeleteResponse: LocationDeleteResponse = {
        deleted_location: mockLocation,
        updated_parts_count: 5,
        deleted_children_count: 2,
      }

      const mockResponse = {
        status: 'success',
        data: mockDeleteResponse,
      }

      mockApiClient.delete.mockResolvedValueOnce(mockResponse)

      const result = await locationsService.deleteLocation('loc-123')

      expect(mockApiClient.delete).toHaveBeenCalledWith('/api/locations/delete_location/loc-123')
      expect(result).toEqual(mockDeleteResponse)
    })
  })

  describe('getAllLocations', () => {
    it('should get all locations successfully', async () => {
      const mockLocations = [mockLocation, mockChildLocation]
      const mockResponse = {
        status: 'success',
        data: mockLocations,
      }

      mockApiClient.get.mockResolvedValueOnce(mockResponse)

      const result = await locationsService.getAllLocations()

      expect(mockApiClient.get).toHaveBeenCalledWith('/api/locations/get_all_locations')
      expect(result).toEqual(mockLocations)
    })

    it('should return empty array when no locations found', async () => {
      const mockResponse = {
        status: 'success',
        data: null,
      }

      mockApiClient.get.mockResolvedValueOnce(mockResponse)

      const result = await locationsService.getAllLocations()

      expect(result).toEqual([])
    })

    it('should handle API error', async () => {
      mockApiClient.get.mockRejectedValueOnce(new Error('Network error'))

      await expect(locationsService.getAllLocations()).rejects.toThrow('Network error')
    })
  })

  describe('getLocationDetails', () => {
    it('should get location details successfully', async () => {
      const mockDetails: LocationDetails = {
        location: mockLocation,
        children: [mockChildLocation],
        parts_count: 10,
      }

      const mockResponse = {
        status: 'success',
        data: mockDetails,
      }

      mockApiClient.get.mockResolvedValueOnce(mockResponse)

      const result = await locationsService.getLocationDetails('loc-123')

      expect(mockApiClient.get).toHaveBeenCalledWith('/api/locations/get_location_details/loc-123')
      expect(result).toEqual(mockDetails)
    })
  })

  describe('getLocationPath', () => {
    it('should get location path successfully', async () => {
      const mockPath: LocationPath = {
        id: 'loc-456',
        name: 'Electronics Section',
        parent: {
          id: 'loc-123',
          name: 'Main Warehouse',
        },
      }

      const mockResponse = {
        status: 'success',
        data: mockPath,
      }

      mockApiClient.get.mockResolvedValueOnce(mockResponse)

      const result = await locationsService.getLocationPath('loc-456')

      expect(mockApiClient.get).toHaveBeenCalledWith('/api/locations/get_location_path/loc-456')
      expect(result).toEqual(mockPath)
    })
  })

  describe('previewLocationDelete', () => {
    it('should preview location delete successfully', async () => {
      const mockPreview: LocationDeletePreview = {
        location: mockLocation,
        children_count: 2,
        parts_count: 5,
        affected_parts: [
          { id: 'part-1', part_name: 'Resistor', part_number: 'RES-001' },
          { id: 'part-2', part_name: 'Capacitor', part_number: 'CAP-001' },
        ],
      }

      const mockResponse = {
        status: 'success',
        data: mockPreview,
      }

      mockApiClient.get.mockResolvedValueOnce(mockResponse)

      const result = await locationsService.previewLocationDelete('loc-123')

      expect(mockApiClient.get).toHaveBeenCalledWith(
        '/api/locations/preview-location-delete/loc-123'
      )
      expect(result).toEqual(mockPreview)
    })
  })

  describe('cleanupLocations', () => {
    it('should cleanup locations successfully', async () => {
      const mockCleanup: LocationCleanupResponse = {
        removed_count: 3,
        removed_locations: [
          { id: 'loc-orphan1', name: 'Orphan 1', location_type: 'room' },
          { id: 'loc-orphan2', name: 'Orphan 2', location_type: 'room' },
          { id: 'loc-orphan3', name: 'Orphan 3', location_type: 'room' },
        ],
      }

      const mockResponse = {
        status: 'success',
        data: mockCleanup,
      }

      mockApiClient.delete.mockResolvedValueOnce(mockResponse)

      const result = await locationsService.cleanupLocations()

      expect(mockApiClient.delete).toHaveBeenCalledWith('/api/locations/cleanup-locations')
      expect(result).toEqual(mockCleanup)
    })
  })

  describe('checkNameExists', () => {
    it('should return true when location name exists with same parent', async () => {
      mockApiClient.get.mockResolvedValueOnce({
        status: 'success',
        data: { ...mockLocation, parent_id: 'parent-123' },
      })

      const result = await locationsService.checkNameExists('Main Warehouse', 'parent-123')

      expect(result).toBe(true)
    })

    it('should return false when location name exists with different parent', async () => {
      mockApiClient.get.mockResolvedValueOnce({
        status: 'success',
        data: { ...mockLocation, parent_id: 'different-parent' },
      })

      const result = await locationsService.checkNameExists('Main Warehouse', 'parent-123')

      expect(result).toBe(false)
    })

    it('should return false when location name does not exist', async () => {
      mockApiClient.get.mockRejectedValueOnce(new Error('Not found'))

      const result = await locationsService.checkNameExists('Non-existent Location')

      expect(result).toBe(false)
    })

    it('should exclude specified location ID', async () => {
      mockApiClient.get.mockResolvedValueOnce({
        status: 'success',
        data: mockLocation,
      })

      const result = await locationsService.checkNameExists('Main Warehouse', undefined, 'loc-123')

      expect(result).toBe(false)
    })
  })

  describe('buildLocationTree', () => {
    it('should build correct location hierarchy', () => {
      const locations = [mockLocation, mockChildLocation]
      const tree = locationsService.buildLocationTree(locations)

      expect(tree).toHaveLength(1)
      expect(tree[0].id).toBe('loc-123')
      expect(tree[0].children).toHaveLength(1)
      expect(tree[0].children![0].id).toBe('loc-456')
    })

    it('should handle orphaned children', () => {
      const orphanedChild: Location = {
        id: 'loc-orphan',
        name: 'Orphaned Location',
        parent_id: 'non-existent-parent',
        location_type: 'room',
        created_at: '2024-01-01T00:00:00Z',
        updated_at: '2024-01-01T00:00:00Z',
      }

      const locations = [mockLocation, orphanedChild]
      const tree = locationsService.buildLocationTree(locations)

      expect(tree).toHaveLength(2) // Both root and orphaned child
      expect(tree.some((loc) => loc.id === 'loc-orphan')).toBe(true)
    })
  })

  describe('flattenLocationTree', () => {
    it('should flatten location tree correctly', () => {
      const parentWithChildren: Location = {
        ...mockLocation,
        children: [mockChildLocation],
      }

      const flattened = locationsService.flattenLocationTree([parentWithChildren])

      expect(flattened).toHaveLength(2)
      expect(flattened[0].id).toBe('loc-123')
      expect(flattened[1].id).toBe('loc-456')
    })
  })

  describe('getDescendantIds', () => {
    it('should get all descendant IDs', () => {
      const grandChild: Location = {
        id: 'loc-789',
        name: 'Resistor Drawer',
        parent_id: 'loc-456',
        location_type: 'drawer',
        created_at: '2024-01-01T00:00:00Z',
        updated_at: '2024-01-01T00:00:00Z',
      }

      const parentWithChildren: Location = {
        ...mockLocation,
        children: [
          {
            ...mockChildLocation,
            children: [grandChild],
          },
        ],
      }

      const descendantIds = locationsService.getDescendantIds(parentWithChildren)

      expect(descendantIds).toEqual(['loc-456', 'loc-789'])
    })

    it('should return empty array for location with no children', () => {
      const descendantIds = locationsService.getDescendantIds(mockLocation)

      expect(descendantIds).toEqual([])
    })
  })

  describe('getAll alias', () => {
    it('should call getAllLocations', async () => {
      const mockLocations = [mockLocation]
      const mockResponse = {
        status: 'success',
        data: mockLocations,
      }

      mockApiClient.get.mockResolvedValueOnce(mockResponse)

      const result = await locationsService.getAll()

      expect(mockApiClient.get).toHaveBeenCalledWith('/api/locations/get_all_locations')
      expect(result).toEqual(mockLocations)
    })
  })

  describe('LocationsService class instantiation', () => {
    it('should create a new LocationsService instance', () => {
      const newLocationsService = new LocationsService()

      expect(newLocationsService).toBeInstanceOf(LocationsService)
      expect(newLocationsService.createLocation).toBeDefined()
      expect(newLocationsService.getAllLocations).toBeDefined()
      expect(newLocationsService.buildLocationTree).toBeDefined()
    })

    it('should export a singleton instance', () => {
      expect(locationsService).toBeInstanceOf(LocationsService)
    })
  })
})
