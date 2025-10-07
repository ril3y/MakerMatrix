import { BaseNamedCrudService } from './baseCrud.service'
import type {
  Category,
  CreateCategoryRequest,
  UpdateCategoryRequest,
  CategoriesListResponse,
  DeleteCategoriesResponse,
} from '@/types/categories'
import type { ApiResponse } from './api'
import { apiClient } from './api'

export class EnhancedCategoriesService extends BaseNamedCrudService<
  Category,
  CreateCategoryRequest,
  UpdateCategoryRequest
> {
  protected baseUrl = '/api/categories'
  protected entityName = 'category'

  // Map frontend create request to backend format
  protected mapCreateRequestToBackend(data: CreateCategoryRequest): any {
    return {
      name: data.name,
      description: data.description || '',
    }
  }

  // Map frontend update request to backend format
  protected mapUpdateRequestToBackend(data: UpdateCategoryRequest): any {
    return {
      name: data.name,
      description: data.description || '',
      parent_id: data.parent_id || null,
    }
  }

  // Map backend response to frontend entity
  protected mapResponseToEntity(response: any): Category {
    return {
      id: response.id,
      name: response.name,
      description: response.description || '',
      part_count: response.part_count || 0,
      created_at: response.created_at,
      updated_at: response.updated_at,
    }
  }

  // Override getAll to handle the specific categories response format
  async getAll(): Promise<Category[]> {
    try {
      const response = await apiClient.get<ApiResponse<CategoriesListResponse>>(
        '/api/categories/get_all_categories'
      )
      if (response.status === 'success' && response.data) {
        return response.data.categories.map((category) => this.mapResponseToEntity(category))
      }
      return []
    } catch (error: any) {
      throw new Error(error.message || 'Failed to load categories')
    }
  }

  // Override delete to handle category-specific endpoint
  async delete(id: string): Promise<void> {
    try {
      const response = await apiClient.delete<ApiResponse>(
        `/api/categories/remove_category?cat_id=${id}`
      )
      if (response.status !== 'success') {
        throw new Error(response.message || 'Failed to delete category')
      }
    } catch (error: any) {
      throw new Error(error.message || 'Failed to delete category')
    }
  }

  // Override deleteByName to handle category-specific endpoint
  async deleteByName(name: string): Promise<void> {
    try {
      const response = await apiClient.delete<ApiResponse>(
        `/api/categories/remove_category?name=${encodeURIComponent(name)}`
      )
      if (response.status !== 'success') {
        throw new Error(response.message || 'Failed to delete category')
      }
    } catch (error: any) {
      throw new Error(error.message || 'Failed to delete category')
    }
  }

  // Category-specific methods
  async deleteAllCategories(): Promise<number> {
    try {
      const response = await apiClient.delete<ApiResponse<DeleteCategoriesResponse>>(
        '/api/categories/delete_all_categories'
      )
      if (response.status === 'success' && response.data) {
        return response.data.deleted_count
      }
      throw new Error(response.message || 'Failed to delete all categories')
    } catch (error: any) {
      throw new Error(error.message || 'Failed to delete all categories')
    }
  }

  // Helper method to sort categories by name
  sortCategoriesByName(categories: Category[]): Category[] {
    return [...categories].sort((a, b) => a.name.localeCompare(b.name))
  }

  // Helper method to filter categories by search term
  filterCategories(categories: Category[], searchTerm: string): Category[] {
    const term = searchTerm.toLowerCase()
    return categories.filter(
      (category) =>
        category.name.toLowerCase().includes(term) ||
        (category.description && category.description.toLowerCase().includes(term))
    )
  }

  // Helper method to get category by ID from a list
  getCategoryById(categories: Category[], id: string): Category | undefined {
    return categories.find((category) => category.id === id)
  }

  // Helper method to get categories by IDs from a list
  getCategoriesByIds(categories: Category[], ids: string[]): Category[] {
    const idSet = new Set(ids)
    return categories.filter((category) => idSet.has(category.id))
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

  // Convenience methods for backward compatibility
  async getAllCategories(): Promise<Category[]> {
    return this.getAll()
  }

  async getCategory(params: { id?: string; name?: string }): Promise<Category> {
    if (params.id) {
      return this.getById(params.id)
    }
    if (params.name) {
      return this.getByName(params.name)
    }
    throw new Error('Either id or name must be provided')
  }

  async createCategory(data: CreateCategoryRequest): Promise<Category> {
    return this.create(data)
  }

  async updateCategory(data: UpdateCategoryRequest): Promise<Category> {
    return this.update(data)
  }

  async deleteCategory(params: { id?: string; name?: string }): Promise<void> {
    if (params.id) {
      return this.delete(params.id)
    }
    if (params.name) {
      return this.deleteByName(params.name)
    }
    throw new Error('Either id or name must be provided')
  }
}

// Export both the enhanced service and the original for backward compatibility
export const enhancedCategoriesService = new EnhancedCategoriesService()

// Re-export the original service for backward compatibility
export { categoriesService } from './categories.service'
