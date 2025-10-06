import { apiClient, ApiResponse, PaginatedResponse } from './api'
import { 
  Part, 
  CreatePartRequest, 
  UpdatePartRequest, 
  SearchPartsRequest 
} from '@/types/parts'

export class PartsService {
  // Helper function to map backend part format to frontend format
  private mapPartFromBackend(backendPart: any): Part {
    return {
      ...backendPart,
      name: backendPart.part_name, // Map part_name to name
    }
  }
  async createPart(data: CreatePartRequest): Promise<Part> {
    // Map frontend format to backend format
    const backendData = {
      ...data,
      part_name: data.name,
      category_names: data.categories || []
    }

    // Remove frontend-only fields
    delete backendData.name
    delete backendData.categories

    // Convert empty strings to null for foreign key fields to prevent constraint errors
    if (backendData.location_id === '') {
      backendData.location_id = null
    }
    if (backendData.supplier_url === '') {
      backendData.supplier_url = null
    }

    const response = await apiClient.post<ApiResponse<any>>('/api/parts/add_part', backendData)

    if (response.status === 'success' && response.data) {
      return this.mapPartFromBackend(response.data)
    }
    throw new Error(response.message || 'Failed to create part')
  }

  async getPart(id: string): Promise<Part> {
    const response = await apiClient.get<ApiResponse<any>>(`/api/parts/get_part?part_id=${id}`)
    if (response.status === 'success' && response.data) {
      return this.mapPartFromBackend(response.data)
    }
    throw new Error(response.message || 'Failed to get part')
  }

  async getPartByName(name: string): Promise<Part> {
    const response = await apiClient.get<ApiResponse<any>>(`/api/parts/get_part?part_name=${name}`)
    if (response.status === 'success' && response.data) {
      return this.mapPartFromBackend(response.data)
    }
    throw new Error(response.message || 'Failed to get part')
  }

  async getPartByNumber(partNumber: string): Promise<Part> {
    const response = await apiClient.get<ApiResponse<any>>(`/api/parts/get_part?part_number=${partNumber}`)
    if (response.status === 'success' && response.data) {
      return this.mapPartFromBackend(response.data)
    }
    throw new Error(response.message || 'Failed to get part')
  }

  async updatePart(data: UpdatePartRequest): Promise<Part> {
    const { id, ...updateData } = data

    // Map frontend format to backend format
    const backendData = {
      ...updateData,
      part_name: updateData.name,
      category_names: updateData.categories || []
    }

    // Remove frontend-only fields
    delete backendData.name
    delete backendData.categories

    // Convert empty strings to null for foreign key fields to prevent constraint errors
    if (backendData.location_id === '') {
      backendData.location_id = null
    }
    if (backendData.supplier_url === '') {
      backendData.supplier_url = null
    }

    const response = await apiClient.put<ApiResponse<any>>(`/api/parts/update_part/${id}`, backendData)
    if (response.status === 'success' && response.data) {
      return this.mapPartFromBackend(response.data)
    }
    throw new Error(response.message || 'Failed to update part')
  }

  async deletePart(id: string): Promise<void> {
    const response = await apiClient.delete<ApiResponse>(`/api/parts/delete_part?part_id=${id}`)
    if (response.status !== 'success') {
      throw new Error(response.message || 'Failed to delete part')
    }
  }

  async getAllParts(page = 1, pageSize = 20): Promise<{ data: Part[], total_parts: number }> {
    const response = await apiClient.get<ApiResponse<any[]>>('/api/parts/get_all_parts', {
      params: { page, page_size: pageSize }
    })

    if (response.status === 'success' && response.data) {
      return {
        data: response.data.map(part => this.mapPartFromBackend(part)),
        total_parts: response.total_parts || 0
      }
    }

    return { data: [], total_parts: 0 }
  }

  async getAll(): Promise<Part[]> {
    const response = await apiClient.get<ApiResponse<any[]>>('/api/parts/get_all_parts')

    if (response.status === 'success' && response.data) {
      return response.data.map(part => this.mapPartFromBackend(part))
    }

    return []
  }

  async getById(id: number): Promise<Part> {
    return this.getPart(id.toString())
  }

  async update(id: number, data: any): Promise<Part> {
    return this.updatePart({ id: id.toString(), ...data })
  }

  async delete(id: number): Promise<void> {
    await this.deletePart(id.toString())
  }

  async searchParts(params: SearchPartsRequest): Promise<PaginatedResponse<Part>> {
    const response = await apiClient.post<PaginatedResponse<Part>>('/api/parts/search', params)
    return response
  }

  async searchPartsText(query: string, page = 1, pageSize = 20): Promise<{ data: Part[], total_parts: number }> {
    const response = await apiClient.get<ApiResponse<any[]>>('/api/parts/search_text', {
      params: { query, page, page_size: pageSize }
    })

    if (response.status === 'success' && response.data) {
      return {
        data: response.data.map(part => this.mapPartFromBackend(part)),
        total_parts: response.total_parts || 0
      }
    }

    return { data: [], total_parts: 0 }
  }

  async getPartSuggestions(query: string, limit = 10): Promise<string[]> {
    if (query.length < 3) {
      return []
    }
    
    try {
      const response = await apiClient.get<ApiResponse<string[]>>('/api/parts/suggestions', {
        params: { query, limit }
      })
      if (response.status === 'success' && response.data) {
        return response.data
      }
      return []
    } catch (error) {
      console.error('Error fetching suggestions:', error)
      return []
    }
  }

  async checkNameExists(name: string, excludeId?: string): Promise<boolean> {
    try {
      const response = await apiClient.get<ApiResponse<boolean>>('/api/parts/check_name_exists', {
        params: { name, exclude_id: excludeId }
      })
      return response.status === 'success' && response.data || false
    } catch {
      return false
    }
  }

  async importFromSupplier(supplier: string, url: string): Promise<Part> {
    const response = await apiClient.post<ApiResponse<Part>>('/api/parts/import', {
      supplier,
      url
    })
    if (response.status === 'success' && response.data) {
      return response.data
    }
    throw new Error(response.message || 'Failed to import part')
  }

  async checkEnrichmentRequirements(partId: string, supplier: string): Promise<EnrichmentRequirementCheckResponse> {
    const response = await apiClient.get<ApiResponse<EnrichmentRequirementCheckResponse>>(
      `/api/parts/parts/${partId}/enrichment-requirements/${supplier}`
    )
    if (response.status === 'success' && response.data) {
      return response.data
    }
    throw new Error(response.message || 'Failed to check enrichment requirements')
  }

  /**
   * Get enrichment requirements for a specific supplier (without needing a part_id)
   */
  async getSupplierEnrichmentRequirements(supplier: string): Promise<SupplierEnrichmentRequirements> {
    const response = await apiClient.get<ApiResponse<SupplierEnrichmentRequirements>>(`/api/parts/enrichment-requirements/${supplier}`)
    // apiClient.get already returns response.data, so response is the API response object
    // We need to extract the data field from the API response
    if (response.status === 'success' && response.data) {
      return response.data
    }
    throw new Error(response.message || 'Failed to get enrichment requirements')
  }

  /**
   * Bulk update multiple parts with shared field values
   */
  async bulkUpdateParts(request: BulkUpdateRequest): Promise<BulkUpdateResponse> {
    const response = await apiClient.post<ApiResponse<BulkUpdateResponse>>('/api/parts/bulk_update', request)
    if (response.status === 'success' && response.data) {
      return response.data
    }
    throw new Error(response.message || 'Failed to bulk update parts')
  }

  /**
   * Enrich part data from supplier using unified backend endpoint
   * This uses SupplierDataMapper on the backend to ensure consistent data mapping
   */
  async enrichFromSupplier(supplierName: string, partIdentifier: string): Promise<any> {
    const response = await apiClient.post<ApiResponse<any>>(
      '/api/parts/enrich-from-supplier',
      null,
      {
        params: {
          supplier_name: supplierName,
          part_identifier: partIdentifier
        }
      }
    )
    if (response.status === 'success' && response.data) {
      return response.data
    }
    throw new Error(response.message || 'Failed to enrich part from supplier')
  }
}

// Bulk update types
export interface BulkUpdateRequest {
  part_ids: string[]
  supplier?: string
  location_id?: string
  minimum_quantity?: number
  add_categories?: string[]
  remove_categories?: string[]
}

export interface BulkUpdateResponse {
  updated_count: number
  failed_count: number
  errors: Array<{
    part_id: string
    error: string
  }>
}

// Enrichment requirement types
export interface FieldCheck {
  field_name: string
  display_name: string
  is_present: boolean
  current_value?: any
  validation_passed: boolean
  validation_message?: string
}

export interface EnrichmentRequirementCheckResponse {
  supplier_name: string
  part_id: string
  can_enrich: boolean
  required_checks: FieldCheck[]
  recommended_checks: FieldCheck[]
  missing_required: string[]
  missing_recommended: string[]
  warnings: string[]
  suggestions: string[]
}

export interface SupplierEnrichmentRequirements {
  supplier_name: string
  display_name: string
  description: string
  required_fields: Array<{
    field_name: string
    display_name: string
    description: string
    example?: string
    validation_pattern?: string
  }>
  recommended_fields: Array<{
    field_name: string
    display_name: string
    description: string
    example?: string
  }>
}

export const partsService = new PartsService()