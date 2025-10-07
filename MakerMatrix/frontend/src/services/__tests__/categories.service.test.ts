import { describe, it, expect, vi, beforeEach } from 'vitest'
import { CategoriesService, categoriesService } from '../categories.service'
import { apiClient } from '../api'
import {
  Category,
  CreateCategoryRequest,
  UpdateCategoryRequest,
  CategoryResponse,
  CategoriesListResponse,
  DeleteCategoriesResponse,
} from '@/types/categories'

// Mock dependencies
vi.mock('../api')

const mockApiClient = vi.mocked(apiClient)

describe('CategoriesService', () => {
  const mockCategory: Category = {
    id: 'cat-123',
    name: 'Electronics',
    description: 'Electronic components and devices',
    created_at: '2024-01-01T00:00:00Z',
    updated_at: '2024-01-01T00:00:00Z',
  }

  const mockCategory2: Category = {
    id: 'cat-456',
    name: 'Resistors',
    description: 'Various resistor types',
    created_at: '2024-01-01T00:00:00Z',
    updated_at: '2024-01-01T00:00:00Z',
  }

  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('createCategory', () => {
    it('should create category successfully', async () => {
      const createRequest: CreateCategoryRequest = {
        name: 'Capacitors',
        description: 'Various capacitor types',
      }

      const mockResponse = {
        status: 'success',
        message: 'Category created successfully',
        data: {
          category: mockCategory,
        },
      }

      mockApiClient.post.mockResolvedValueOnce(mockResponse)

      const result = await categoriesService.createCategory(createRequest)

      expect(mockApiClient.post).toHaveBeenCalledWith('/api/categories/add_category', createRequest)
      expect(result).toEqual(mockCategory)
    })

    it('should handle creation API error', async () => {
      const createRequest: CreateCategoryRequest = {
        name: 'Duplicated Category',
      }

      mockApiClient.post.mockRejectedValueOnce(new Error('Category already exists'))

      await expect(categoriesService.createCategory(createRequest)).rejects.toThrow(
        'Category already exists'
      )
    })
  })

  describe('getCategory', () => {
    it('should get category by ID successfully', async () => {
      const mockResponse = {
        status: 'success',
        data: {
          category: mockCategory,
        },
      }

      mockApiClient.get.mockResolvedValueOnce(mockResponse)

      const result = await categoriesService.getCategory({ id: 'cat-123' })

      expect(mockApiClient.get).toHaveBeenCalledWith(
        '/api/categories/get_category?category_id=cat-123'
      )
      expect(result).toEqual(mockCategory)
    })

    it('should get category by name successfully', async () => {
      const mockResponse = {
        status: 'success',
        data: {
          category: mockCategory,
        },
      }

      mockApiClient.get.mockResolvedValueOnce(mockResponse)

      const result = await categoriesService.getCategory({ name: 'Electronics' })

      expect(mockApiClient.get).toHaveBeenCalledWith(
        '/api/categories/get_category?name=Electronics'
      )
      expect(result).toEqual(mockCategory)
    })

    it('should throw error when neither id nor name provided', async () => {
      await expect(categoriesService.getCategory({})).rejects.toThrow(
        'Either id or name must be provided'
      )
    })

    it('should handle category not found', async () => {
      mockApiClient.get.mockRejectedValueOnce(new Error('Category not found'))

      await expect(categoriesService.getCategory({ id: 'invalid' })).rejects.toThrow(
        'Category not found'
      )
    })
  })

  describe('updateCategory', () => {
    it('should update category successfully', async () => {
      const updateRequest: UpdateCategoryRequest = {
        id: 'cat-123',
        name: 'Updated Electronics',
        description: 'Updated description',
      }

      const updatedCategory = { ...mockCategory, name: 'Updated Electronics' }
      const mockResponse = {
        status: 'success',
        data: {
          category: updatedCategory,
        },
      }

      mockApiClient.put.mockResolvedValueOnce(mockResponse)

      const result = await categoriesService.updateCategory(updateRequest)

      expect(mockApiClient.put).toHaveBeenCalledWith('/api/categories/update_category/cat-123', {
        name: 'Updated Electronics',
        description: 'Updated description',
      })
      expect(result).toEqual(updatedCategory)
    })

    it('should handle update failure', async () => {
      const updateRequest: UpdateCategoryRequest = {
        id: 'cat-123',
        name: 'Updated Category',
      }

      mockApiClient.put.mockRejectedValueOnce(new Error('Update failed'))

      await expect(categoriesService.updateCategory(updateRequest)).rejects.toThrow('Update failed')
    })
  })

  describe('deleteCategory', () => {
    it('should delete category by ID successfully', async () => {
      const mockResponse = {
        status: 'success',
        data: {
          category: mockCategory,
        },
      }

      mockApiClient.delete.mockResolvedValueOnce(mockResponse)

      const result = await categoriesService.deleteCategory({ id: 'cat-123' })

      expect(mockApiClient.delete).toHaveBeenCalledWith(
        '/api/categories/remove_category?cat_id=cat-123'
      )
      expect(result).toEqual(mockCategory)
    })

    it('should delete category by name successfully', async () => {
      const mockResponse = {
        status: 'success',
        data: {
          category: mockCategory,
        },
      }

      mockApiClient.delete.mockResolvedValueOnce(mockResponse)

      const result = await categoriesService.deleteCategory({ name: 'Electronics' })

      expect(mockApiClient.delete).toHaveBeenCalledWith(
        '/api/categories/remove_category?name=Electronics'
      )
      expect(result).toEqual(mockCategory)
    })

    it('should throw error when neither id nor name provided', async () => {
      await expect(categoriesService.deleteCategory({})).rejects.toThrow(
        'Either id or name must be provided'
      )
    })
  })

  describe('getAllCategories', () => {
    it('should get all categories successfully', async () => {
      const mockCategories = [mockCategory, mockCategory2]
      const mockResponse = {
        status: 'success',
        data: {
          categories: mockCategories,
        },
      }

      mockApiClient.get.mockResolvedValueOnce(mockResponse)

      const result = await categoriesService.getAllCategories()

      expect(mockApiClient.get).toHaveBeenCalledWith('/api/categories/get_all_categories')
      expect(result).toEqual(mockCategories)
    })

    it('should return empty array when no categories found', async () => {
      const mockResponse = {
        status: 'success',
        data: null,
      }

      mockApiClient.get.mockResolvedValueOnce(mockResponse)

      const result = await categoriesService.getAllCategories()

      expect(result).toEqual([])
    })

    it('should handle API error', async () => {
      mockApiClient.get.mockRejectedValueOnce(new Error('Network error'))

      await expect(categoriesService.getAllCategories()).rejects.toThrow('Network error')
    })
  })

  describe('deleteAllCategories', () => {
    it('should delete all categories successfully', async () => {
      const mockResponse = {
        status: 'success',
        data: {
          deleted_count: 5,
        },
      }

      mockApiClient.delete.mockResolvedValueOnce(mockResponse)

      const result = await categoriesService.deleteAllCategories()

      expect(mockApiClient.delete).toHaveBeenCalledWith('/api/categories/delete_all_categories')
      expect(result).toBe(5)
    })
  })

  describe('checkNameExists', () => {
    it('should return true when category name exists', async () => {
      mockApiClient.get.mockResolvedValueOnce({
        status: 'success',
        data: { category: mockCategory },
      })

      const result = await categoriesService.checkNameExists('Electronics')

      expect(result).toBe(true)
    })

    it('should return false when category name does not exist', async () => {
      mockApiClient.get.mockRejectedValueOnce(new Error('Not found'))

      const result = await categoriesService.checkNameExists('Non-existent Category')

      expect(result).toBe(false)
    })

    it('should exclude specified category ID', async () => {
      mockApiClient.get.mockResolvedValueOnce({
        status: 'success',
        data: { category: mockCategory },
      })

      const result = await categoriesService.checkNameExists('Electronics', 'cat-123')

      expect(result).toBe(false)
    })

    it('should return true for different category with same name', async () => {
      mockApiClient.get.mockResolvedValueOnce({
        status: 'success',
        data: { category: mockCategory },
      })

      const result = await categoriesService.checkNameExists('Electronics', 'different-id')

      expect(result).toBe(true)
    })
  })

  describe('Helper Methods', () => {
    describe('sortCategoriesByName', () => {
      it('should sort categories alphabetically by name', () => {
        const categories = [mockCategory2, mockCategory] // Resistors, Electronics
        const sorted = categoriesService.sortCategoriesByName(categories)

        expect(sorted[0].name).toBe('Electronics')
        expect(sorted[1].name).toBe('Resistors')
      })

      it('should not mutate original array', () => {
        const categories = [mockCategory2, mockCategory]
        const originalOrder = categories.map((c) => c.name)

        categoriesService.sortCategoriesByName(categories)

        expect(categories.map((c) => c.name)).toEqual(originalOrder)
      })
    })

    describe('filterCategories', () => {
      it('should filter categories by name', () => {
        const categories = [mockCategory, mockCategory2]
        const filtered = categoriesService.filterCategories(categories, 'Elect')

        expect(filtered).toHaveLength(1)
        expect(filtered[0].name).toBe('Electronics')
      })

      it('should filter categories by description', () => {
        const categories = [mockCategory, mockCategory2]
        const filtered = categoriesService.filterCategories(categories, 'resistor')

        expect(filtered).toHaveLength(1)
        expect(filtered[0].name).toBe('Resistors')
      })

      it('should be case insensitive', () => {
        const categories = [mockCategory, mockCategory2]
        const filtered = categoriesService.filterCategories(categories, 'ELECTRONICS')

        expect(filtered).toHaveLength(1)
        expect(filtered[0].name).toBe('Electronics')
      })

      it('should return empty array when no matches', () => {
        const categories = [mockCategory, mockCategory2]
        const filtered = categoriesService.filterCategories(categories, 'nonexistent')

        expect(filtered).toHaveLength(0)
      })
    })

    describe('getCategoryById', () => {
      it('should find category by ID', () => {
        const categories = [mockCategory, mockCategory2]
        const found = categoriesService.getCategoryById(categories, 'cat-123')

        expect(found).toEqual(mockCategory)
      })

      it('should return undefined when category not found', () => {
        const categories = [mockCategory, mockCategory2]
        const found = categoriesService.getCategoryById(categories, 'nonexistent')

        expect(found).toBeUndefined()
      })
    })

    describe('getCategoriesByIds', () => {
      it('should find multiple categories by IDs', () => {
        const categories = [mockCategory, mockCategory2]
        const found = categoriesService.getCategoriesByIds(categories, ['cat-123', 'cat-456'])

        expect(found).toHaveLength(2)
        expect(found).toEqual([mockCategory, mockCategory2])
      })

      it('should return only found categories', () => {
        const categories = [mockCategory, mockCategory2]
        const found = categoriesService.getCategoriesByIds(categories, ['cat-123', 'nonexistent'])

        expect(found).toHaveLength(1)
        expect(found[0]).toEqual(mockCategory)
      })

      it('should return empty array when no IDs match', () => {
        const categories = [mockCategory, mockCategory2]
        const found = categoriesService.getCategoriesByIds(categories, ['nonexistent'])

        expect(found).toHaveLength(0)
      })
    })

    describe('validateCategoryName', () => {
      it('should return valid for proper category name', () => {
        const result = categoriesService.validateCategoryName('Electronics')

        expect(result.valid).toBe(true)
        expect(result.error).toBeUndefined()
      })

      it('should return invalid for empty name', () => {
        const result = categoriesService.validateCategoryName('')

        expect(result.valid).toBe(false)
        expect(result.error).toBe('Category name is required')
      })

      it('should return invalid for whitespace-only name', () => {
        const result = categoriesService.validateCategoryName('   ')

        expect(result.valid).toBe(false)
        expect(result.error).toBe('Category name is required')
      })

      it('should return invalid for name too short', () => {
        const result = categoriesService.validateCategoryName('A')

        expect(result.valid).toBe(false)
        expect(result.error).toBe('Category name must be at least 2 characters long')
      })

      it('should return invalid for name too long', () => {
        const longName = 'A'.repeat(101)
        const result = categoriesService.validateCategoryName(longName)

        expect(result.valid).toBe(false)
        expect(result.error).toBe('Category name must be less than 100 characters')
      })
    })
  })

  describe('getAll alias', () => {
    it('should call getAllCategories', async () => {
      const mockCategories = [mockCategory]
      const mockResponse = {
        status: 'success',
        data: { categories: mockCategories },
      }

      mockApiClient.get.mockResolvedValueOnce(mockResponse)

      const result = await categoriesService.getAll()

      expect(mockApiClient.get).toHaveBeenCalledWith('/api/categories/get_all_categories')
      expect(result).toEqual(mockCategories)
    })
  })

  describe('CategoriesService class instantiation', () => {
    it('should create a new CategoriesService instance', () => {
      const newCategoriesService = new CategoriesService()

      expect(newCategoriesService).toBeInstanceOf(CategoriesService)
      expect(newCategoriesService.createCategory).toBeDefined()
      expect(newCategoriesService.getAllCategories).toBeDefined()
      expect(newCategoriesService.validateCategoryName).toBeDefined()
    })

    it('should export a singleton instance', () => {
      expect(categoriesService).toBeInstanceOf(CategoriesService)
    })
  })
})
