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
    const response = await apiClient.post<ApiResponse<any>>('/api/parts/add_part', backendData)
    
    // Map response back to frontend format
    if (response.data) {
      return {
        ...response.data,
        name: response.data.part_name || response.data.name,
        categories: response.data.categories || [], // Ensure categories are preserved
        created_at: response.data.created_at || new Date().toISOString(),
        updated_at: response.data.updated_at || new Date().toISOString()
      }
    }
    throw new Error('No data in response')
  }

  async getPart(id: string): Promise<Part> {
    const response = await apiClient.get<ApiResponse<any>>(`/api/parts/get_part?part_id=${id}`)
    if (response.data) {
      return {
        ...response.data,
        name: response.data.part_name || response.data.name,
        categories: response.data.categories || [], // Ensure categories are preserved
        created_at: response.data.created_at || new Date().toISOString(),
        updated_at: response.data.updated_at || new Date().toISOString()
      }
    }
    throw new Error('No data in response')
  }

  async getPartByName(name: string): Promise<Part> {
    const response = await apiClient.get<ApiResponse<any>>(`/api/parts/get_part?part_name=${name}`)
    if (response.data) {
      return {
        ...response.data,
        name: response.data.part_name || response.data.name,
        categories: response.data.categories || [], // Ensure categories are preserved
        created_at: response.data.created_at || new Date().toISOString(),
        updated_at: response.data.updated_at || new Date().toISOString()
      }
    }
    throw new Error('No data in response')
  }

  async getPartByNumber(partNumber: string): Promise<Part> {
    const response = await apiClient.get<ApiResponse<any>>(`/api/parts/get_part?part_number=${partNumber}`)
    if (response.data) {
      return {
        ...response.data,
        name: response.data.part_name || response.data.name,
        categories: response.data.categories || [], // Ensure categories are preserved
        created_at: response.data.created_at || new Date().toISOString(),
        updated_at: response.data.updated_at || new Date().toISOString()
      }
    }
    throw new Error('No data in response')
  }

  async updatePart(data: UpdatePartRequest): Promise<Part> {
    const { id, ...updateData } = data
    
    // Handle category conversion from IDs to names
    let categoryNames: string[] | undefined = undefined
    if (updateData.categories && Array.isArray(updateData.categories)) {
      if (updateData.categories.length > 0) {
        // Check if categories are provided as IDs (strings) 
        const firstCategory = updateData.categories[0]
        if (typeof firstCategory === 'string') {
          // Categories are IDs, we need to convert them to names
          // Fetch category data to get names
          try {
            const { categoriesService } = await import('./categories.service')
            const allCategories = await categoriesService.getAllCategories()
            categoryNames = updateData.categories
              .map(categoryId => {
                const category = allCategories.find(cat => cat.id === categoryId)
                return category?.name
              })
              .filter(Boolean) as string[]
          } catch (error) {
            console.error('Failed to convert category IDs to names:', error)
            // Skip category update to prevent corruption
            categoryNames = undefined
          }
        } else if (typeof firstCategory === 'object' && firstCategory.name) {
          // Categories are already Category objects, extract names
          categoryNames = updateData.categories.map((cat: any) => cat.name)
        }
      } else {
        // Empty array means clear all categories
        categoryNames = []
      }
    }
    
    // Map frontend format to backend format
    const backendData = {
      ...updateData,
      part_name: updateData.name,
      ...(categoryNames !== undefined && { category_names: categoryNames })
    }
    
    // Remove frontend-only fields that don't exist in backend
    delete backendData.name
    delete backendData.categories
    
    const response = await apiClient.put<ApiResponse<any>>(`/api/parts/update_part/${id}`, backendData)
    if (response.data) {
      return {
        ...response.data,
        name: response.data.part_name || response.data.name,
        categories: response.data.categories || [], // Ensure categories are preserved
        created_at: response.data.created_at || new Date().toISOString(),
        updated_at: response.data.updated_at || new Date().toISOString()
      }
    }
    throw new Error('No data in response')
  }

  async deletePart(id: string): Promise<ApiResponse> {
    return await apiClient.delete<ApiResponse>(`/api/parts/delete_part?part_id=${id}`)
  }

  async getAllParts(page = 1, pageSize = 20): Promise<{ data: Part[], total_parts: number }> {
    const response = await apiClient.get<any>('/api/parts/get_all_parts', {
      params: { page, page_size: pageSize }
    })
    
    // Map backend response to frontend format
    if (response.data && Array.isArray(response.data)) {
      const mappedData = response.data.map((part: any) => ({
        ...part,
        name: part.part_name || part.name, // Map part_name to name
        categories: part.categories || [], // Ensure categories are preserved
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
    const response = await apiClient.get<any>('/api/parts/get_all_parts')
    
    // Map backend response to frontend format
    if (response.data && Array.isArray(response.data)) {
      return response.data.map((part: any) => ({
        ...part,
        name: part.part_name || part.name, // Map part_name to name
        categories: part.categories || [], // Ensure categories are preserved
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
    const response = await apiClient.post<PaginatedResponse<Part>>('/api/parts/search', params)
    return response
  }

  async searchPartsText(query: string, page = 1, pageSize = 20): Promise<{ data: Part[], total_parts: number }> {
    const response = await apiClient.get<any>('/api/parts/search_text', {
      params: { query, page, page_size: pageSize }
    })
    
    // Map backend response to frontend format
    if (response.data && Array.isArray(response.data)) {
      const mappedData = response.data.map((part: any) => ({
        ...part,
        name: part.part_name || part.name,
        categories: part.categories || [], // Ensure categories are preserved
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
      const response = await apiClient.get<any>('/api/parts/suggestions', {
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
      const response = await apiClient.get<ApiResponse<boolean>>('/api/parts/check_name_exists', {
        params: { name, exclude_id: excludeId }
      })
      return response.data || false
    } catch {
      return false
    }
  }

  async importFromSupplier(supplier: string, url: string): Promise<Part> {
    const response = await apiClient.post<ApiResponse<Part>>('/api/parts/import', {
      supplier,
      url
    })
    return response.data!
  }
}

export const partsService = new PartsService()