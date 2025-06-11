import { apiClient, ApiResponse, PaginatedResponse } from './api'
import { 
  Part, 
  CreatePartRequest, 
  UpdatePartRequest, 
  SearchPartsRequest 
} from '@/types/parts'

export class PartsService {
  async createPart(data: CreatePartRequest): Promise<Part> {
    // Map frontend format to backend format
    const backendData = {
      ...data,
      part_name: data.name,
      category_names: data.categories || []
    }
    const response = await apiClient.post<ApiResponse<any>>('/parts/add_part', backendData)
    
    // Map response back to frontend format
    if (response.data) {
      return {
        ...response.data,
        name: response.data.part_name || response.data.name,
        created_at: response.data.created_at || new Date().toISOString(),
        updated_at: response.data.updated_at || new Date().toISOString()
      }
    }
    throw new Error('No data in response')
  }

  async getPart(id: string): Promise<Part> {
    const response = await apiClient.get<ApiResponse<any>>(`/parts/get_part?part_id=${id}`)
    if (response.data) {
      return {
        ...response.data,
        name: response.data.part_name || response.data.name,
        created_at: response.data.created_at || new Date().toISOString(),
        updated_at: response.data.updated_at || new Date().toISOString()
      }
    }
    throw new Error('No data in response')
  }

  async getPartByName(name: string): Promise<Part> {
    const response = await apiClient.get<ApiResponse<any>>(`/parts/get_part?part_name=${name}`)
    if (response.data) {
      return {
        ...response.data,
        name: response.data.part_name || response.data.name,
        created_at: response.data.created_at || new Date().toISOString(),
        updated_at: response.data.updated_at || new Date().toISOString()
      }
    }
    throw new Error('No data in response')
  }

  async getPartByNumber(partNumber: string): Promise<Part> {
    const response = await apiClient.get<ApiResponse<any>>(`/parts/get_part?part_number=${partNumber}`)
    if (response.data) {
      return {
        ...response.data,
        name: response.data.part_name || response.data.name,
        created_at: response.data.created_at || new Date().toISOString(),
        updated_at: response.data.updated_at || new Date().toISOString()
      }
    }
    throw new Error('No data in response')
  }

  async updatePart(data: UpdatePartRequest): Promise<Part> {
    const { id, ...updateData } = data
    // Map frontend format to backend format
    const backendData = {
      ...updateData,
      part_name: updateData.name,
      category_names: updateData.categories || []
    }
    
    // Remove frontend-only fields that don't exist in backend
    delete backendData.name
    delete backendData.categories
    
    const response = await apiClient.put<ApiResponse<any>>(`/parts/update_part/${id}`, backendData)
    if (response.data) {
      return {
        ...response.data,
        name: response.data.part_name || response.data.name,
        created_at: response.data.created_at || new Date().toISOString(),
        updated_at: response.data.updated_at || new Date().toISOString()
      }
    }
    throw new Error('No data in response')
  }

  async deletePart(id: string): Promise<ApiResponse> {
    return await apiClient.delete<ApiResponse>(`/parts/delete_part?part_id=${id}`)
  }

  async getAllParts(page = 1, pageSize = 20): Promise<{ data: Part[], total_parts: number }> {
    const response = await apiClient.get<any>('/parts/get_all_parts', {
      params: { page, page_size: pageSize }
    })
    
    // Map backend response to frontend format
    if (response.data && Array.isArray(response.data)) {
      const mappedData = response.data.map((part: any) => ({
        ...part,
        name: part.part_name || part.name, // Map part_name to name
        created_at: part.created_at || new Date().toISOString(),
        updated_at: part.updated_at || new Date().toISOString()
      }))
      
      return {
        data: mappedData,
        total_parts: response.total_parts || 0
      }
    }
    
    return { data: [], total_parts: 0 }
  }

  async getAll(): Promise<Part[]> {
    const response = await apiClient.get<any>('/parts/get_all_parts')
    
    // Map backend response to frontend format
    if (response.data && Array.isArray(response.data)) {
      return response.data.map((part: any) => ({
        ...part,
        name: part.part_name || part.name, // Map part_name to name
        created_at: part.created_at || new Date().toISOString(),
        updated_at: part.updated_at || new Date().toISOString()
      }))
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
    const response = await apiClient.post<PaginatedResponse<Part>>('/parts/search', params)
    return response
  }

  async searchPartsText(query: string, page = 1, pageSize = 20): Promise<{ data: Part[], total_parts: number }> {
    const response = await apiClient.get<any>('/parts/search_text', {
      params: { query, page, page_size: pageSize }
    })
    
    // Map backend response to frontend format
    if (response.data && Array.isArray(response.data)) {
      const mappedData = response.data.map((part: any) => ({
        ...part,
        name: part.part_name || part.name,
        created_at: part.created_at || new Date().toISOString(),
        updated_at: part.updated_at || new Date().toISOString()
      }))
      
      return {
        data: mappedData,
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
      const response = await apiClient.get<any>('/parts/suggestions', {
        params: { query, limit }
      })
      return response.data || []
    } catch (error) {
      console.error('Error fetching suggestions:', error)
      return []
    }
  }

  async checkNameExists(name: string, excludeId?: string): Promise<boolean> {
    try {
      const response = await apiClient.get<ApiResponse<boolean>>('/parts/check_name_exists', {
        params: { name, exclude_id: excludeId }
      })
      return response.data || false
    } catch {
      return false
    }
  }

  async importFromSupplier(supplier: string, url: string): Promise<Part> {
    const response = await apiClient.post<ApiResponse<Part>>('/parts/import', {
      supplier,
      url
    })
    return response.data!
  }
}

export const partsService = new PartsService()