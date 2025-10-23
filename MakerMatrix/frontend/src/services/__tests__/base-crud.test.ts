import { describe, it, expect, vi, beforeEach } from 'vitest'
import { BaseNamedCrudService } from '../baseCrud.service'
import { enhancedCategoriesService } from '../categories.service.enhanced'
import { enhancedLocationsService } from '../locations.service.enhanced'
import { apiClient } from '../api'

// Mock the API client
vi.mock('../api', () => ({
  apiClient: {
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
    delete: vi.fn(),
  },
}))

// Type definitions for backend data structures
interface BackendCreateData {
  name: string
  description: string
}

interface BackendUpdateData {
  name: string
  description: string
}

interface BackendResponseData {
  id: string
  name: string
  description: string
  created_at?: string
  updated_at?: string
}

// Test implementation of BaseCrudService
class TestEntity {
  id: string
  name: string
  description: string
  created_at?: string
  updated_at?: string

  constructor(id: string, name: string, description: string) {
    this.id = id
    this.name = name
    this.description = description
  }
}

class TestCreateRequest {
  name: string
  description: string

  constructor(name: string, description: string) {
    this.name = name
    this.description = description
  }
}

class TestUpdateRequest {
  id: string
  name: string
  description: string

  constructor(id: string, name: string, description: string) {
    this.id = id
    this.name = name
    this.description = description
  }
}

class TestCrudService extends BaseNamedCrudService<
  TestEntity,
  TestCreateRequest,
  TestUpdateRequest
> {
  protected baseUrl = '/api/test'
  protected entityName = 'test'

  protected mapCreateRequestToBackend(data: TestCreateRequest): BackendCreateData {
    return {
      name: data.name,
      description: data.description,
    }
  }

  protected mapUpdateRequestToBackend(data: TestUpdateRequest): BackendUpdateData {
    return {
      name: data.name,
      description: data.description,
    }
  }

  protected mapResponseToEntity(response: BackendResponseData): TestEntity {
    return new TestEntity(response.id, response.name, response.description)
  }
}

describe('Base CRUD Service Tests', () => {
  let testService: TestCrudService

  beforeEach(() => {
    vi.clearAllMocks()
    testService = new TestCrudService()
  })

  describe('BaseCrudService', () => {
    it('should get all entities', async () => {
      const mockResponse = {
        status: 'success',
        data: [
          { id: '1', name: 'Test 1', description: 'Description 1' },
          { id: '2', name: 'Test 2', description: 'Description 2' },
        ],
      }

      vi.mocked(apiClient.get).mockResolvedValueOnce(mockResponse)

      const result = await testService.getAll()

      expect(apiClient.get).toHaveBeenCalledWith('/api/test/get_all_tests')
      expect(result).toHaveLength(2)
      expect(result[0]).toBeInstanceOf(TestEntity)
      expect(result[0].name).toBe('Test 1')
    })

    it('should get entities with pagination', async () => {
      const mockResponse = {
        status: 'success',
        data: [{ id: '1', name: 'Test 1', description: 'Description 1' }],
        total_parts: 1,
      }

      vi.mocked(apiClient.get).mockResolvedValueOnce(mockResponse)

      const result = await testService.getAllPaginated({ page: 1, pageSize: 10 })

      expect(apiClient.get).toHaveBeenCalledWith('/api/test/get_all_tests', {
        params: { page: 1, page_size: 10 },
      })
      expect(result.data).toHaveLength(1)
      expect(result.total).toBe(1)
      expect(result.page).toBe(1)
      expect(result.pageSize).toBe(10)
    })

    it('should get entity by ID', async () => {
      const mockResponse = {
        status: 'success',
        data: { id: '1', name: 'Test 1', description: 'Description 1' },
      }

      vi.mocked(apiClient.get).mockResolvedValueOnce(mockResponse)

      const result = await testService.getById('1')

      expect(apiClient.get).toHaveBeenCalledWith('/api/test/get_test?test_id=1')
      expect(result).toBeInstanceOf(TestEntity)
      expect(result.id).toBe('1')
      expect(result.name).toBe('Test 1')
    })

    it('should create entity', async () => {
      const mockResponse = {
        status: 'success',
        data: { id: '1', name: 'New Test', description: 'New Description' },
      }

      vi.mocked(apiClient.post).mockResolvedValueOnce(mockResponse)

      const createRequest = new TestCreateRequest('New Test', 'New Description')
      const result = await testService.create(createRequest)

      expect(apiClient.post).toHaveBeenCalledWith('/api/test/add_test', {
        name: 'New Test',
        description: 'New Description',
      })
      expect(result).toBeInstanceOf(TestEntity)
      expect(result.name).toBe('New Test')
    })

    it('should update entity', async () => {
      const mockResponse = {
        status: 'success',
        data: { id: '1', name: 'Updated Test', description: 'Updated Description' },
      }

      vi.mocked(apiClient.put).mockResolvedValueOnce(mockResponse)

      const updateRequest = new TestUpdateRequest('1', 'Updated Test', 'Updated Description')
      const result = await testService.update(updateRequest)

      expect(apiClient.put).toHaveBeenCalledWith('/api/test/update_test/1', {
        name: 'Updated Test',
        description: 'Updated Description',
      })
      expect(result).toBeInstanceOf(TestEntity)
      expect(result.name).toBe('Updated Test')
    })

    it('should delete entity', async () => {
      const mockResponse = {
        status: 'success',
        message: 'Entity deleted successfully',
      }

      vi.mocked(apiClient.delete).mockResolvedValueOnce(mockResponse)

      await testService.delete('1')

      expect(apiClient.delete).toHaveBeenCalledWith('/api/test/delete_test?test_id=1')
    })

    it('should handle error responses', async () => {
      const mockResponse = {
        status: 'error',
        message: 'Entity not found',
      }

      vi.mocked(apiClient.get).mockResolvedValueOnce(mockResponse)

      await expect(testService.getById('1')).rejects.toThrow('test not found')
    })
  })

  describe('BaseNamedCrudService', () => {
    it('should get entity by name', async () => {
      const mockResponse = {
        status: 'success',
        data: { id: '1', name: 'Test Name', description: 'Description' },
      }

      vi.mocked(apiClient.get).mockResolvedValueOnce(mockResponse)

      const result = await testService.getByName('Test Name')

      expect(apiClient.get).toHaveBeenCalledWith('/api/test/get_test?name=Test%20Name')
      expect(result).toBeInstanceOf(TestEntity)
      expect(result.name).toBe('Test Name')
    })

    it('should check if name exists', async () => {
      const mockResponse = {
        status: 'success',
        data: { id: '1', name: 'Test Name', description: 'Description' },
      }

      vi.mocked(apiClient.get).mockResolvedValueOnce(mockResponse)

      const exists = await testService.checkNameExists('Test Name')

      expect(exists).toBe(true)
    })

    it('should check if name exists excluding specific ID', async () => {
      const mockResponse = {
        status: 'success',
        data: { id: '1', name: 'Test Name', description: 'Description' },
      }

      vi.mocked(apiClient.get).mockResolvedValueOnce(mockResponse)

      const exists = await testService.checkNameExists('Test Name', '1')

      expect(exists).toBe(false) // Should return false when excluding the same ID
    })

    it('should delete entity by name', async () => {
      const mockResponse = {
        status: 'success',
        message: 'Entity deleted successfully',
      }

      vi.mocked(apiClient.delete).mockResolvedValueOnce(mockResponse)

      await testService.deleteByName('Test Name')

      expect(apiClient.delete).toHaveBeenCalledWith('/api/test/remove_test?name=Test%20Name')
    })
  })

  describe('Enhanced Categories Service', () => {
    it('should extend base CRUD functionality', async () => {
      const mockResponse = {
        status: 'success',
        data: {
          categories: [
            { id: '1', name: 'Category 1', description: 'Description 1', part_count: 5 },
            { id: '2', name: 'Category 2', description: 'Description 2', part_count: 3 },
          ],
        },
      }

      vi.mocked(apiClient.get).mockResolvedValueOnce(mockResponse)

      const result = await enhancedCategoriesService.getAll()

      expect(apiClient.get).toHaveBeenCalledWith('/api/categories/get_all_categories')
      expect(result).toHaveLength(2)
      expect(result[0].name).toBe('Category 1')
      expect(result[0].part_count).toBe(5)
    })

    it('should provide category-specific helper methods', () => {
      const categories = [
        { id: '1', name: 'Electronics', description: 'Electronic components', part_count: 10 },
        { id: '2', name: 'Resistors', description: 'Passive components', part_count: 5 },
      ]

      const sorted = enhancedCategoriesService.sortCategoriesByName(categories)
      expect(sorted[0].name).toBe('Electronics')

      const filtered = enhancedCategoriesService.filterCategories(categories, 'electronic')
      expect(filtered).toHaveLength(1)
      expect(filtered[0].name).toBe('Electronics')

      const found = enhancedCategoriesService.getCategoryById(categories, '2')
      expect(found?.name).toBe('Resistors')
    })

    it('should validate category names', () => {
      const validResult = enhancedCategoriesService.validateCategoryName('Valid Category')
      expect(validResult.valid).toBe(true)

      const emptyResult = enhancedCategoriesService.validateCategoryName('')
      expect(emptyResult.valid).toBe(false)
      expect(emptyResult.error).toBe('Category name is required')

      const shortResult = enhancedCategoriesService.validateCategoryName('A')
      expect(shortResult.valid).toBe(false)
      expect(shortResult.error).toBe('Category name must be at least 2 characters long')
    })
  })

  describe('Enhanced Locations Service', () => {
    it('should extend base CRUD functionality', async () => {
      const mockResponse = {
        status: 'success',
        data: [
          { id: '1', name: 'Location 1', description: 'Description 1', parent_id: null },
          { id: '2', name: 'Location 2', description: 'Description 2', parent_id: '1' },
        ],
      }

      vi.mocked(apiClient.get).mockResolvedValueOnce(mockResponse)

      const result = await enhancedLocationsService.getAll()

      expect(apiClient.get).toHaveBeenCalledWith('/api/locations/get_all_locations')
      expect(result).toHaveLength(2)
      expect(result[0].name).toBe('Location 1')
      expect(result[1].parent_id).toBe('1')
    })

    it('should build location tree hierarchy', () => {
      const locations = [
        { id: '1', name: 'Root', parent_id: null, children: [] },
        { id: '2', name: 'Child 1', parent_id: '1', children: [] },
        { id: '3', name: 'Child 2', parent_id: '1', children: [] },
        { id: '4', name: 'Grandchild', parent_id: '2', children: [] },
      ]

      const tree = enhancedLocationsService.buildLocationTree(locations)
      expect(tree).toHaveLength(1) // Only root
      expect(tree[0].children).toHaveLength(2) // Two children
      expect(tree[0].children[0].children).toHaveLength(1) // One grandchild
    })

    it('should provide location-specific helper methods', () => {
      const locations = [
        { id: '1', name: 'Root', parent_id: null, children: [] },
        { id: '2', name: 'Child 1', parent_id: '1', children: [] },
        { id: '3', name: 'Child 2', parent_id: '1', children: [] },
      ]

      const children = enhancedLocationsService.getLocationsByParent(locations, '1')
      expect(children).toHaveLength(2)
      expect(children.map((l) => l.name)).toEqual(['Child 1', 'Child 2'])

      const isDescendant = enhancedLocationsService.isDescendantOf('2', '1', locations)
      expect(isDescendant).toBe(true)

      const isNotDescendant = enhancedLocationsService.isDescendantOf('1', '2', locations)
      expect(isNotDescendant).toBe(false)
    })

    it('should flatten location tree', () => {
      const tree = [
        {
          id: '1',
          name: 'Root',
          parent_id: null,
          children: [
            { id: '2', name: 'Child 1', parent_id: '1', children: [] },
            { id: '3', name: 'Child 2', parent_id: '1', children: [] },
          ],
        },
      ]

      const flattened = enhancedLocationsService.flattenLocationTree(tree)
      expect(flattened).toHaveLength(3)
      expect(flattened.map((l) => l.name)).toEqual(['Root', 'Child 1', 'Child 2'])
    })
  })

  describe('Utility Methods', () => {
    it('should build query params correctly', () => {
      const params = {
        name: 'test',
        page: 1,
        active: true,
        empty: null,
        undefined: undefined,
      }

      const queryString = testService['buildQueryParams'](params)
      expect(queryString).toBe('name=test&page=1&active=true')
    })

    it('should validate IDs', () => {
      expect(() => testService['validateId']('')).toThrow('test ID is required')
      expect(() => testService['validateId']('  ')).toThrow('test ID is required')
      expect(() => testService['validateId']('valid-id')).not.toThrow()
    })

    it('should validate create data', () => {
      expect(() => testService['validateCreateData'](null as unknown as TestCreateRequest)).toThrow(
        'Invalid test data'
      )
      expect(() =>
        testService['validateCreateData']({} as unknown as TestCreateRequest)
      ).not.toThrow()
    })

    it('should validate update data', () => {
      expect(() => testService['validateUpdateData'](null as unknown as TestUpdateRequest)).toThrow(
        'Invalid test data'
      )
      expect(() => testService['validateUpdateData']({} as unknown as TestUpdateRequest)).toThrow(
        'test ID is required for updates'
      )
      expect(() =>
        testService['validateUpdateData']({ id: '1' } as unknown as TestUpdateRequest)
      ).not.toThrow()
    })
  })
})
