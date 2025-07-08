import { apiClient, ApiResponse } from './api'
import { 
  Category,
  CreateCategoryRequest,
  UpdateCategoryRequest,
  CategoryResponse,
  CategoriesListResponse,
  DeleteCategoriesResponse
} from '@/types/categories'

export class CategoriesService {
  async createCategory(data: CreateCategoryRequest): Promise<Category> {
    const response = await apiClient.post<ApiResponse<CategoryResponse>>('/api/categories/add_category', data)
    if (response.status === 'success' && response.data) {
      return response.data.category
    }
    throw new Error(response.message || 'Failed to create category')
  }

  async getCategory(params: { id?: string; name?: string }): Promise<Category> {
    if (!params.id && !params.name) {
      throw new Error('Either id or name must be provided')
    }
    
    const queryParams = new URLSearchParams()
    if (params.id) queryParams.append('category_id', params.id)
    if (params.name) queryParams.append('name', params.name)
    
    const response = await apiClient.get<ApiResponse<CategoryResponse>>(`/api/categories/get_category?${queryParams}`)
    if (response.status === 'success' && response.data) {
      return response.data.category
    }
    throw new Error(response.message || 'Failed to get category')
  }

  async updateCategory(data: UpdateCategoryRequest): Promise<Category> {
    const { id, ...updateData } = data
    const response = await apiClient.put<ApiResponse<CategoryResponse>>(`/api/categories/update_category/${id}`, updateData)
    if (response.status === 'success' && response.data) {
      return response.data.category
    }
    throw new Error(response.message || 'Failed to update category')
  }

  async deleteCategory(params: { id?: string; name?: string }): Promise<Category> {
    if (!params.id && !params.name) {
      throw new Error('Either id or name must be provided')
    }
    
    const queryParams = new URLSearchParams()
    if (params.id) queryParams.append('cat_id', params.id)
    if (params.name) queryParams.append('name', params.name)
    
    const response = await apiClient.delete<ApiResponse<CategoryResponse>>(`/api/categories/remove_category?${queryParams}`)
    if (response.status === 'success' && response.data) {
      return response.data.category
    }
    throw new Error(response.message || 'Failed to delete category')
  }

  async getAllCategories(): Promise<Category[]> {
    const response = await apiClient.get<ApiResponse<CategoriesListResponse>>('/api/categories/get_all_categories')
    if (response.status === 'success' && response.data) {
      return response.data.categories || []
    }
    return []
  }

  async deleteAllCategories(): Promise<number> {
    const response = await apiClient.delete<ApiResponse<DeleteCategoriesResponse>>('/api/categories/delete_all_categories')
    if (response.status === 'success' && response.data) {
      return response.data.deleted_count
    }
    throw new Error(response.message || 'Failed to delete all categories')
  }

  async getAll(): Promise<Category[]> {
    return this.getAllCategories()
  }

  async checkNameExists(name: string, excludeId?: string): Promise<boolean> {
    try {
      const category = await this.getCategory({ name })
      // If we found a category and it's not the one we're excluding
      return category ? category.id !== excludeId : false
    } catch {
      return false
    }
  }

  // Helper method to sort categories by name
  sortCategoriesByName(categories: Category[]): Category[] {
    return [...categories].sort((a, b) => a.name.localeCompare(b.name))
  }

  // Helper method to filter categories by search term
  filterCategories(categories: Category[], searchTerm: string): Category[] {
    const term = searchTerm.toLowerCase()
    return categories.filter(category => 
      category.name.toLowerCase().includes(term) ||
      (category.description && category.description.toLowerCase().includes(term))
    )
  }

  // Helper method to get category by ID from a list
  getCategoryById(categories: Category[], id: string): Category | undefined {
    return categories.find(category => category.id === id)
  }

  // Helper method to get categories by IDs from a list
  getCategoriesByIds(categories: Category[], ids: string[]): Category[] {
    const idSet = new Set(ids)
    return categories.filter(category => idSet.has(category.id))
  }

  // Helper method to validate category name
  validateCategoryName(name: string): { valid: boolean; error?: string } {
    if (!name || name.trim().length === 0) {
      return { valid: false, error: 'Category name is required' }
    }
    
    if (name.trim().length < 2) {
      return { valid: false, error: 'Category name must be at least 2 characters long' }
    }
    
    if (name.trim().length > 100) {
      return { valid: false, error: 'Category name must be less than 100 characters' }
    }
    
    return { valid: true }
  }
}

export const categoriesService = new CategoriesService()