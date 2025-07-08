import { describe, it, expect, vi, beforeEach } from 'vitest'
import { apiClient } from '../api'
import { partsService } from '../parts.service'
import { categoriesService } from '../categories.service'
import { locationsService } from '../locations.service'
import { authService } from '../auth.service'
import { utilityService } from '../utility.service'

// Mock the API client
vi.mock('../api', () => ({
  apiClient: {
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
    delete: vi.fn(),
    setAuthToken: vi.fn(),
    clearAuth: vi.fn(),
  },
  handleApiError: vi.fn(),
}))

describe('Services API Alignment Tests', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('PartsService', () => {
    it('should handle createPart with new API response format', async () => {
      const mockResponse = {
        status: 'success',
        message: 'Part created successfully',
        data: {
          id: '123',
          part_name: 'Test Part',
          description: 'Test description',
          quantity: 10,
          categories: []
        }
      }
      
      vi.mocked(apiClient.post).mockResolvedValueOnce(mockResponse)

      const result = await partsService.createPart({
        name: 'Test Part',
        description: 'Test description',
        quantity: 10
      })

      expect(result).toEqual(mockResponse.data)
      expect(apiClient.post).toHaveBeenCalledWith('/api/parts/add_part', {
        part_name: 'Test Part',
        description: 'Test description',
        quantity: 10,
        category_names: []
      })
    })

    it('should handle getPart with new API response format', async () => {
      const mockResponse = {
        status: 'success',
        message: 'Part retrieved successfully',
        data: {
          id: '123',
          part_name: 'Test Part',
          description: 'Test description',
          quantity: 10
        }
      }
      
      vi.mocked(apiClient.get).mockResolvedValueOnce(mockResponse)

      const result = await partsService.getPart('123')

      expect(result).toEqual(mockResponse.data)
      expect(apiClient.get).toHaveBeenCalledWith('/api/parts/get_part?part_id=123')
    })

    it('should handle getAllParts with new API response format', async () => {
      const mockResponse = {
        status: 'success',
        message: 'Parts retrieved successfully',
        data: [
          { id: '1', part_name: 'Part 1' },
          { id: '2', part_name: 'Part 2' }
        ],
        total_parts: 2
      }
      
      vi.mocked(apiClient.get).mockResolvedValueOnce(mockResponse)

      const result = await partsService.getAllParts(1, 10)

      expect(result).toEqual({
        data: mockResponse.data,
        total_parts: 2
      })
      expect(apiClient.get).toHaveBeenCalledWith('/api/parts/get_all_parts', {
        params: { page: 1, page_size: 10 }
      })
    })

    it('should handle updatePart with simplified logic', async () => {
      const mockResponse = {
        status: 'success',
        message: 'Part updated successfully',
        data: {
          id: '123',
          part_name: 'Updated Part',
          description: 'Updated description',
          quantity: 20,
          categories: []
        }
      }
      
      vi.mocked(apiClient.put).mockResolvedValueOnce(mockResponse)

      const result = await partsService.updatePart({
        id: '123',
        name: 'Updated Part',
        description: 'Updated description',
        quantity: 20,
        categories: []
      })

      expect(result).toEqual(mockResponse.data)
      expect(apiClient.put).toHaveBeenCalledWith('/api/parts/update_part/123', {
        part_name: 'Updated Part',
        description: 'Updated description',
        quantity: 20,
        category_names: []
      })
    })

    it('should handle deletePart with new API response format', async () => {
      const mockResponse = {
        status: 'success',
        message: 'Part deleted successfully'
      }
      
      vi.mocked(apiClient.delete).mockResolvedValueOnce(mockResponse)

      await partsService.deletePart('123')

      expect(apiClient.delete).toHaveBeenCalledWith('/api/parts/delete_part?part_id=123')
    })

    it('should handle error responses correctly', async () => {
      const mockErrorResponse = {
        status: 'error',
        message: 'Part not found'
      }
      
      vi.mocked(apiClient.get).mockResolvedValueOnce(mockErrorResponse)

      await expect(partsService.getPart('123')).rejects.toThrow('Part not found')
    })
  })

  describe('CategoriesService', () => {
    it('should handle createCategory with new API response format', async () => {
      const mockResponse = {
        status: 'success',
        message: 'Category created successfully',
        data: {
          category: {
            id: '123',
            name: 'Test Category',
            description: 'Test description'
          }
        }
      }
      
      vi.mocked(apiClient.post).mockResolvedValueOnce(mockResponse)

      const result = await categoriesService.createCategory({
        name: 'Test Category',
        description: 'Test description'
      })

      expect(result).toEqual(mockResponse.data.category)
      expect(apiClient.post).toHaveBeenCalledWith('/api/categories/add_category', {
        name: 'Test Category',
        description: 'Test description'
      })
    })

    it('should handle getAllCategories with new API response format', async () => {
      const mockResponse = {
        status: 'success',
        message: 'Categories retrieved successfully',
        data: {
          categories: [
            { id: '1', name: 'Category 1' },
            { id: '2', name: 'Category 2' }
          ]
        }
      }
      
      vi.mocked(apiClient.get).mockResolvedValueOnce(mockResponse)

      const result = await categoriesService.getAllCategories()

      expect(result).toEqual(mockResponse.data.categories)
      expect(apiClient.get).toHaveBeenCalledWith('/api/categories/get_all_categories')
    })
  })

  describe('LocationsService', () => {
    it('should handle createLocation with new API response format', async () => {
      const mockResponse = {
        status: 'success',
        message: 'Location created successfully',
        data: {
          id: '123',
          name: 'Test Location',
          description: 'Test description'
        }
      }
      
      vi.mocked(apiClient.post).mockResolvedValueOnce(mockResponse)

      const result = await locationsService.createLocation({
        name: 'Test Location',
        description: 'Test description'
      })

      expect(result).toEqual(mockResponse.data)
      expect(apiClient.post).toHaveBeenCalledWith('/api/locations/add_location', {
        name: 'Test Location',
        description: 'Test description'
      })
    })

    it('should handle getAllLocations with new API response format', async () => {
      const mockResponse = {
        status: 'success',
        message: 'Locations retrieved successfully',
        data: [
          { id: '1', name: 'Location 1' },
          { id: '2', name: 'Location 2' }
        ]
      }
      
      vi.mocked(apiClient.get).mockResolvedValueOnce(mockResponse)

      const result = await locationsService.getAllLocations()

      expect(result).toEqual(mockResponse.data)
      expect(apiClient.get).toHaveBeenCalledWith('/api/locations/get_all_locations')
    })
  })

  describe('AuthService', () => {
    it('should handle login with JSON request format', async () => {
      const mockResponse = {
        access_token: 'mock_token',
        token_type: 'bearer',
        user: { id: '123', username: 'testuser' }
      }
      
      vi.mocked(apiClient.post).mockResolvedValueOnce(mockResponse)

      const result = await authService.login({
        username: 'testuser',
        password: 'password'
      })

      expect(result).toEqual(mockResponse)
      expect(apiClient.post).toHaveBeenCalledWith('/auth/login', {
        username: 'testuser',
        password: 'password'
      })
      expect(apiClient.setAuthToken).toHaveBeenCalledWith('mock_token')
    })

    it('should handle updatePassword with new API response format', async () => {
      const mockResponse = {
        status: 'success',
        message: 'Password updated successfully'
      }
      
      vi.mocked(apiClient.put).mockResolvedValueOnce(mockResponse)

      await authService.updatePassword('oldpass', 'newpass')

      expect(apiClient.put).toHaveBeenCalledWith('/api/users/update_password', {
        current_password: 'oldpass',
        new_password: 'newpass'
      })
    })
  })

  describe('UtilityService', () => {
    it('should handle uploadImage with new API response format', async () => {
      const mockResponse = {
        status: 'success',
        message: 'Image uploaded successfully',
        data: {
          image_id: 'test-image-id'
        }
      }
      
      vi.mocked(apiClient.post).mockResolvedValueOnce(mockResponse)

      const file = new File(['test'], 'test.jpg', { type: 'image/jpeg' })
      const result = await utilityService.uploadImage(file)

      expect(result).toEqual('/api/utility/get_image/test-image-id')
      expect(apiClient.post).toHaveBeenCalledWith(
        '/api/utility/upload_image',
        expect.any(FormData),
        {
          headers: {
            'Content-Type': 'multipart/form-data',
          },
        }
      )
    })

    it('should handle uploadImage error response', async () => {
      const mockErrorResponse = {
        status: 'error',
        message: 'Upload failed'
      }
      
      vi.mocked(apiClient.post).mockResolvedValueOnce(mockErrorResponse)

      const file = new File(['test'], 'test.jpg', { type: 'image/jpeg' })
      
      await expect(utilityService.uploadImage(file)).rejects.toThrow('Upload failed')
    })
  })
})