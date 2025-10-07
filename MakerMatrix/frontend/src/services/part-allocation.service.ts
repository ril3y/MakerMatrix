/**
 * Part Allocation Service
 *
 * Handles multi-location inventory allocation operations including:
 * - Viewing part allocations across multiple locations
 * - Transferring quantities between locations
 * - Splitting quantities to cassettes
 */

import type { ApiResponse } from './api'
import { apiClient } from './api'

// Types
export interface PartAllocation {
  id: string
  part_id: string
  location_id: string
  quantity_at_location: number
  is_primary_storage: boolean
  notes: string | null
  allocated_at: string
  last_updated: string
  location?: {
    id: string
    name: string
    location_type: string
    description?: string
    emoji?: string
    image_url?: string
  }
  location_path?: string
}

export interface AllocationSummary {
  part_id: string
  part_name: string
  part_number?: string
  total_quantity: number
  location_count: number
  primary_location: {
    id: string
    name: string
    location_type: string
    description?: string
    emoji?: string
  } | null
  allocations: PartAllocation[]
}

export interface TransferRequest {
  from_location_id: string
  to_location_id: string
  quantity: number
  notes?: string
}

export interface SplitToCassetteRequest {
  from_location_id: string
  quantity: number
  create_new_cassette: boolean
  cassette_id?: string
  cassette_name?: string
  parent_location_id?: string
  cassette_capacity?: number
  cassette_emoji?: string
  notes?: string
}

export interface TransferResponse {
  part_id: string
  part_name: string
  total_quantity: number
  from_allocation: {
    location_id: string
    location_name: string
    new_quantity: number
  }
  to_allocation: {
    location_id: string
    location_name: string
    new_quantity: number
  }
}

class PartAllocationService {
  /**
   * Get all location allocations for a specific part
   */
  async getPartAllocations(partId: string): Promise<AllocationSummary> {
    try {
      const response = await apiClient.get<ApiResponse<AllocationSummary>>(
        `/api/parts/${partId}/allocations`
      )

      if (response.status === 'success' && response.data) {
        return response.data
      }

      throw new Error(response.message || 'Failed to get part allocations')
    } catch (error: any) {
      console.error('Error getting part allocations:', error)
      throw error
    }
  }

  /**
   * Transfer quantity from one location to another
   */
  async transferQuantity(partId: string, request: TransferRequest): Promise<TransferResponse> {
    try {
      // Build query params for transfer endpoint
      const params = new URLSearchParams({
        from_location_id: request.from_location_id,
        to_location_id: request.to_location_id,
        quantity: request.quantity.toString(),
      })

      if (request.notes) {
        params.append('notes', request.notes)
      }

      const response = await apiClient.post<ApiResponse<any>>(
        `/api/parts/${partId}/transfer?${params.toString()}`
      )

      if (response.status === 'success' && response.data) {
        return {
          part_id: response.data.id,
          part_name: response.data.part_name,
          total_quantity: response.data.total_quantity || 0,
          from_allocation: {
            location_id: request.from_location_id,
            location_name: 'Source Location',
            new_quantity: 0, // Will be updated from allocation data
          },
          to_allocation: {
            location_id: request.to_location_id,
            location_name: 'Destination Location',
            new_quantity: 0, // Will be updated from allocation data
          },
        }
      }

      throw new Error(response.message || 'Failed to transfer quantity')
    } catch (error: any) {
      console.error('Error transferring quantity:', error)
      throw error
    }
  }

  /**
   * Split quantity to a cassette (create new or use existing)
   */
  async splitToCassette(
    partId: string,
    request: SplitToCassetteRequest
  ): Promise<TransferResponse> {
    try {
      const response = await apiClient.post<ApiResponse<any>>(
        `/api/parts/${partId}/allocations/split_to_cassette`,
        request
      )

      if (response.status === 'success' && response.data) {
        return {
          part_id: response.data.part_id,
          part_name: response.data.part_name,
          total_quantity: response.data.total_quantity || 0,
          from_allocation: response.data.from_allocation || {
            location_id: request.from_location_id,
            location_name: 'Source',
            new_quantity: 0,
          },
          to_allocation: response.data.to_allocation || {
            location_id: '',
            location_name: 'Cassette',
            new_quantity: request.quantity,
          },
        }
      }

      throw new Error(response.message || 'Failed to split to cassette')
    } catch (error: any) {
      console.error('Error splitting to cassette:', error)
      throw error
    }
  }

  /**
   * Create a new allocation for a part at a specific location
   */
  async createAllocation(
    partId: string,
    locationId: string,
    quantity: number,
    isPrimary: boolean = false,
    notes?: string
  ): Promise<PartAllocation> {
    try {
      const response = await apiClient.post<ApiResponse<PartAllocation>>(
        `/api/parts/${partId}/allocations`,
        {
          location_id: locationId,
          quantity,
          is_primary: isPrimary,
          notes,
        }
      )

      if (response.status === 'success' && response.data) {
        return response.data
      }

      throw new Error(response.message || 'Failed to create allocation')
    } catch (error: any) {
      console.error('Error creating allocation:', error)
      throw error
    }
  }

  /**
   * Update an existing allocation
   */
  async updateAllocation(
    partId: string,
    allocationId: string,
    updates: {
      quantity?: number
      is_primary?: boolean
      notes?: string
    }
  ): Promise<PartAllocation> {
    try {
      const response = await apiClient.put<ApiResponse<PartAllocation>>(
        `/api/parts/${partId}/allocations/${allocationId}`,
        updates
      )

      if (response.status === 'success' && response.data) {
        return response.data
      }

      throw new Error(response.message || 'Failed to update allocation')
    } catch (error: any) {
      console.error('Error updating allocation:', error)
      throw error
    }
  }

  /**
   * Delete an allocation
   */
  async deleteAllocation(partId: string, allocationId: string): Promise<void> {
    try {
      const response = await apiClient.delete<ApiResponse<void>>(
        `/api/parts/${partId}/allocations/${allocationId}`
      )

      if (response.status !== 'success') {
        throw new Error(response.message || 'Failed to delete allocation')
      }
    } catch (error: any) {
      console.error('Error deleting allocation:', error)
      throw error
    }
  }
}

// Export singleton instance
export const partAllocationService = new PartAllocationService()
export default partAllocationService
