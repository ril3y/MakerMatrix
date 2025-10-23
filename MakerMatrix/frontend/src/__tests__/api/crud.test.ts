import { describe, it, expect, beforeAll, afterAll } from 'vitest'
import { apiClient, type ApiResponse } from '../../services/api'
import { partsService } from '../../services/parts.service'
import { locationsService } from '../../services/locations.service'
import { categoriesService } from '../../services/categories.service'
import { authService } from '../../services/auth.service'

// Test data
const TEST_USER = {
  username: 'admin',
  password: 'Admin123!',
}

const TEST_PART = {
  name: 'Test Part ' + Date.now(),
  part_number: 'TEST-' + Date.now(),
  description: 'Test part for CRUD tests',
  quantity: 100,
  supplier: 'Test Supplier',
}

const TEST_LOCATION = {
  name: 'Test Location ' + Date.now(),
  description: 'Test location for CRUD tests',
  location_type: 'drawer',
}

const TEST_CATEGORY = {
  name: 'Test Category ' + Date.now(),
  description: 'Test category for CRUD tests',
}

describe('CRUD Operations API Tests', () => {
  let createdPartId: string | undefined
  let createdLocationId: string | undefined
  let createdCategoryId: string | undefined

  beforeAll(async () => {
    // Login
    const loginResult = await authService.login(TEST_USER)
    expect(loginResult.access_token).toBeDefined()
  })

  afterAll(async () => {
    // Cleanup: Delete created test data
    if (createdPartId) {
      try {
        await partsService.deletePart(createdPartId)
      } catch (_e) {
        /* ignore cleanup errors */
      }
    }
    if (createdLocationId) {
      try {
        await locationsService.deleteLocation(createdLocationId)
      } catch (_e) {
        /* ignore cleanup errors */
      }
    }
    if (createdCategoryId) {
      try {
        await categoriesService.deleteCategory({ id: createdCategoryId })
      } catch (_e) {
        /* ignore cleanup errors */
      }
    }
  })

  describe('Parts CRUD', () => {
    it('should create a new part', async () => {
      const response = await partsService.createPart(TEST_PART)

      expect(response).toBeDefined()
      expect(response.id).toBeDefined()
      expect(response.name).toBe(TEST_PART.name)
      expect(response.quantity).toBe(TEST_PART.quantity)

      createdPartId = response.id
    })

    it('should read all parts', async () => {
      const response = await partsService.getAllParts(1, 10)

      expect(response).toBeDefined()
      expect(response.data).toBeDefined()
      expect(Array.isArray(response.data)).toBe(true)
      expect(response.data.length).toBeGreaterThan(0)
    })

    it('should read a single part', async () => {
      if (!createdPartId) throw new Error('No part created')

      const response = await partsService.getPart(createdPartId)

      expect(response).toBeDefined()
      expect(response.id).toBe(createdPartId)
      expect(response.name).toBe(TEST_PART.name)
    })

    it('should update a part', async () => {
      if (!createdPartId) throw new Error('No part created')

      const updateData = {
        id: createdPartId,
        quantity: 200,
        description: 'Updated test part description',
      }

      const response = await partsService.updatePart(updateData)

      expect(response).toBeDefined()
      expect(response.quantity).toBe(updateData.quantity)
      expect(response.description).toBe(updateData.description)
    })

    it('should handle validation errors properly', async () => {
      // Test with invalid data
      const invalidPart = {
        part_name: '', // Empty name should fail
        quantity: -10, // Negative quantity should fail
      }

      await expect(partsService.createPart(invalidPart as any)).rejects.toThrow()
    })

    it('should delete a part', async () => {
      if (!createdPartId) throw new Error('No part created')

      await partsService.deletePart(createdPartId)

      // deletePart returns void on success

      // Verify deletion
      await expect(partsService.getPart(createdPartId)).rejects.toThrow()

      createdPartId = undefined // Clear ID after deletion
    })
  })

  describe('Locations CRUD', () => {
    it('should create a new location', async () => {
      const response = await locationsService.createLocation(TEST_LOCATION)

      expect(response).toBeDefined()
      expect(response.id).toBeDefined()
      expect(response.name).toBe(TEST_LOCATION.name)
      expect(response.location_type).toBe(TEST_LOCATION.location_type)

      createdLocationId = response.id
    })

    it('should read all locations', async () => {
      const response = await locationsService.getAllLocations()

      expect(response).toBeDefined()
      expect(Array.isArray(response)).toBe(true)
      expect(response.length).toBeGreaterThan(0)
    })

    it('should read a single location', async () => {
      if (!createdLocationId) throw new Error('No location created')

      const response = await locationsService.getLocation({ id: createdLocationId })

      expect(response).toBeDefined()
      expect(response.id).toBe(createdLocationId)
      expect(response.name).toBe(TEST_LOCATION.name)
    })

    it('should update a location', async () => {
      if (!createdLocationId) throw new Error('No location created')

      const updateData = {
        description: 'Updated test location description',
      }

      const response = await locationsService.updateLocation({
        id: createdLocationId,
        ...updateData,
      })

      expect(response).toBeDefined()
      expect(response.description).toBe(updateData.description)
    })

    it('should handle location hierarchy properly', async () => {
      // Create parent location
      const parentLocation = await locationsService.createLocation({
        name: 'Parent Location ' + Date.now(),
        description: 'Parent location for hierarchy test',
      })

      // Create child location
      const childLocation = await locationsService.createLocation({
        name: 'Child Location ' + Date.now(),
        description: 'Child location for hierarchy test',
        parent_id: parentLocation.id,
      })

      expect(childLocation.parent_id).toBe(parentLocation.id)

      // Cleanup
      await locationsService.deleteLocation(childLocation.id)
      await locationsService.deleteLocation(parentLocation.id)
    })

    it('should delete a location', async () => {
      if (!createdLocationId) throw new Error('No location created')

      const response = await locationsService.deleteLocation(createdLocationId)

      expect(response).toBeDefined()
      expect(response.updated_parts_count).toBeDefined() // LocationDeleteResponse has updated_parts_count

      createdLocationId = undefined
    })
  })

  describe('Categories CRUD', () => {
    it('should create a new category', async () => {
      const response = await categoriesService.createCategory(TEST_CATEGORY)

      expect(response).toBeDefined()
      expect(response.id).toBeDefined()
      expect(response.name).toBe(TEST_CATEGORY.name)
      expect(response.description).toBe(TEST_CATEGORY.description)

      createdCategoryId = response.id
    })

    it('should read all categories', async () => {
      const response = await categoriesService.getAllCategories()

      expect(response).toBeDefined()
      expect(Array.isArray(response)).toBe(true)
      expect(response.length).toBeGreaterThan(0)
    })

    it('should read a single category', async () => {
      if (!createdCategoryId) throw new Error('No category created')

      const response = await categoriesService.getCategory({ id: createdCategoryId })

      expect(response).toBeDefined()
      expect(response.id).toBe(createdCategoryId)
      expect(response.name).toBe(TEST_CATEGORY.name)
    })

    it('should update a category', async () => {
      if (!createdCategoryId) throw new Error('No category created')

      const updateData = {
        description: 'Updated test category description',
      }

      const response = await categoriesService.updateCategory({
        id: createdCategoryId,
        ...updateData,
      })

      expect(response).toBeDefined()
      expect(response.description).toBe(updateData.description)
    })

    it('should handle duplicate category names', async () => {
      // Try to create category with same name
      await expect(
        categoriesService.createCategory({
          name: TEST_CATEGORY.name,
          description: 'Duplicate category',
        })
      ).rejects.toThrow()
    })

    it('should delete a category', async () => {
      if (!createdCategoryId) throw new Error('No category created')

      const response = await categoriesService.deleteCategory({ id: createdCategoryId })

      expect(response).toBeDefined()
      expect(response.name).toBe(TEST_CATEGORY.name) // deleteCategory returns the deleted category

      createdCategoryId = undefined
    })
  })

  describe('API Response Validation', () => {
    it('should handle API response format correctly', async () => {
      // Test that all responses follow the expected format
      const partResponse = await apiClient.get<ApiResponse<unknown>>('/api/parts/get_all_parts?page=1&page_size=1')

      expect(partResponse).toHaveProperty('status')
      expect(partResponse).toHaveProperty('message')
      expect(partResponse).toHaveProperty('data')
      expect(['success', 'error', 'warning']).toContain(partResponse.status)
    })

    it('should handle serialization errors properly', async () => {
      // This test ensures that model objects are properly serialized to dicts
      const locations = await locationsService.getAllLocations()

      // Check that we get plain objects, not model instances
      if (locations.length > 0) {
        const location = locations[0]
        expect(typeof location).toBe('object')
        expect(location.constructor.name).toBe('Object') // Plain object, not a class instance
      }
    })

    it('should handle error responses consistently', async () => {
      // Test 404 error
      try {
        await partsService.getPart('non-existent-id')
        expect.fail('Should have thrown an error')
      } catch (error: any) {
        expect(error.response?.status).toBe(404)
        expect(error.response?.data).toHaveProperty('detail')
      }
    })
  })

  describe('Cross-Entity Operations', () => {
    it('should handle part with location and category', async () => {
      // Create location and category
      const location = await locationsService.createLocation({
        name: 'Cross-test Location ' + Date.now(),
        description: 'Location for cross-entity test',
      })

      const category = await categoriesService.createCategory({
        name: 'Cross-test Category ' + Date.now(),
        description: 'Category for cross-entity test',
      })

      // Create part with location and category
      const part = await partsService.createPart({
        ...TEST_PART,
        name: 'Cross-test Part ' + Date.now(),
        location_id: location.id,
        category_names: [category.name],
      })

      expect(part.location?.id).toBe(location.id)
      expect(part.categories).toBeDefined()
      expect(part.categories?.length).toBe(1)
      expect(part.categories?.[0].name).toBe(category.name)

      // Cleanup
      await partsService.deletePart(part.id)
      await locationsService.deleteLocation(location.id)
      await categoriesService.deleteCategory({ id: category.id })
    })
  })
})
