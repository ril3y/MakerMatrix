import { describe, it, expect, beforeEach, vi } from 'vitest'
import { partsService } from './parts.service'
import { createMockPart } from '../__tests__/utils/test-utils'

// Mock the apiClient
vi.mock('./api', () => ({
  apiClient: {
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
    delete: vi.fn(),
  },
}))

import { apiClient } from './api'

const mockPart = {
  id: '1',
  part_name: 'Arduino Uno R3',
  part_number: 'ARD-UNO-R3',
  quantity: 10,
  minimum_quantity: 5,
  supplier: 'Arduino',
  location_id: 'loc1',
  image_url: 'http://example.com/image.jpg',
  additional_properties: {
    description: 'Arduino microcontroller board',
  },
  categories: [{ id: 'cat1', name: 'Microcontrollers' }],
  location: { id: 'loc1', name: 'Shelf A1' },
  datasheets: [],
}

describe('PartsService', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('getAllParts', () => {
    it('fetches parts with default pagination', async () => {
      const mockResponse = {
        data: [mockPart],
        total_parts: 1,
      }

      vi.mocked(apiClient.get).mockResolvedValue(mockResponse)

      const result = await partsService.getAllParts()

      expect(apiClient.get).toHaveBeenCalledWith('/api/parts/get_all_parts', {
        params: { page: 1, page_size: 20 },
      })
      expect(result).toEqual({
        data: [
          expect.objectContaining({
            id: mockPart.id,
            name: mockPart.part_name,
          }),
        ],
        total_parts: 1,
      })
    })

    it('fetches parts with custom pagination', async () => {
      const mockResponse = {
        data: [],
        total_parts: 0,
      }

      vi.mocked(apiClient.get).mockResolvedValue(mockResponse)

      await partsService.getAllParts(2, 10)

      expect(apiClient.get).toHaveBeenCalledWith('/api/parts/get_all_parts', {
        params: { page: 2, page_size: 10 },
      })
    })

    it('handles API errors gracefully', async () => {
      const error = new Error('Network error')
      vi.mocked(apiClient.get).mockRejectedValue(error)

      await expect(partsService.getAllParts()).rejects.toThrow('Network error')
    })
  })

  describe('getPart', () => {
    it('fetches part by ID', async () => {
      const mockPart = createMockPart()
      const mockResponse = {
        data: mockPart,
      }

      vi.mocked(apiClient.get).mockResolvedValue(mockResponse)

      const result = await partsService.getPart('test-id')

      expect(apiClient.get).toHaveBeenCalledWith('/api/parts/get_part?part_id=test-id')
      expect(result).toEqual(
        expect.objectContaining({
          id: mockPart.id,
          name: mockPart.part_name,
        })
      )
    })

    it('throws error when no data returned', async () => {
      vi.mocked(apiClient.get).mockResolvedValue({})

      await expect(partsService.getPart('test-id')).rejects.toThrow('No data in response')
    })
  })

  describe('getPartByName', () => {
    it('fetches part by name', async () => {
      const mockPart = createMockPart()
      const mockResponse = {
        data: mockPart,
      }

      vi.mocked(apiClient.get).mockResolvedValue(mockResponse)

      const result = await partsService.getPartByName('Test Part')

      expect(apiClient.get).toHaveBeenCalledWith('/api/parts/get_part?part_name=Test Part')
      expect(result).toEqual(
        expect.objectContaining({
          id: mockPart.id,
          name: mockPart.part_name,
        })
      )
    })
  })

  describe('createPart', () => {
    it('creates new part successfully', async () => {
      const mockPart = createMockPart()
      const createRequest = {
        name: 'New Part',
        part_number: 'NP001',
        description: 'New part description',
        quantity: 10,
        supplier: 'LCSC',
        location_id: 'loc-1',
      }

      vi.mocked(apiClient.post).mockResolvedValue({ data: mockPart })

      const result = await partsService.createPart(createRequest)

      expect(apiClient.post).toHaveBeenCalledWith(
        '/api/parts/add_part',
        expect.objectContaining({
          part_name: 'New Part',
          part_number: 'NP001',
          category_names: [],
        })
      )
      expect(result).toEqual(
        expect.objectContaining({
          name: mockPart.part_name,
        })
      )
    })

    it('throws error when no data returned', async () => {
      const createRequest = {
        name: 'New Part',
        part_number: 'NP001',
        quantity: 0,
      }

      vi.mocked(apiClient.post).mockResolvedValue({})

      await expect(partsService.createPart(createRequest)).rejects.toThrow('No data in response')
    })
  })

  describe('updatePart', () => {
    it('updates part successfully', async () => {
      const mockPart = createMockPart()
      const updateRequest = {
        id: 'test-id',
        name: 'Updated Part',
        description: 'Updated description',
      }

      vi.mocked(apiClient.put).mockResolvedValue({ data: mockPart })

      const result = await partsService.updatePart(updateRequest)

      expect(apiClient.put).toHaveBeenCalledWith(
        '/api/parts/update_part/test-id',
        expect.objectContaining({
          part_name: 'Updated Part',
          description: 'Updated description',
        })
      )
      expect(result).toEqual(
        expect.objectContaining({
          name: mockPart.part_name,
        })
      )
    })
  })

  describe('deletePart', () => {
    it('deletes part successfully', async () => {
      const mockResponse = { status: 'success' }

      vi.mocked(apiClient.delete).mockResolvedValue(mockResponse)

      const result = await partsService.deletePart('test-id')

      expect(apiClient.delete).toHaveBeenCalledWith('/api/parts/delete_part?part_id=test-id')
      expect(result).toEqual(mockResponse)
    })
  })

  describe('searchPartsText', () => {
    it('searches parts with query parameters', async () => {
      const mockPart = createMockPart()
      const mockResponse = {
        data: [mockPart],
        total_parts: 1,
      }

      vi.mocked(apiClient.get).mockResolvedValue(mockResponse)

      const result = await partsService.searchPartsText('resistor', 1, 10)

      expect(apiClient.get).toHaveBeenCalledWith('/api/parts/search_text', {
        params: { query: 'resistor', page: 1, page_size: 10 },
      })
      expect(result).toEqual({
        data: [
          expect.objectContaining({
            name: mockPart.part_name,
          }),
        ],
        total_parts: 1,
      })
    })

    it('handles empty search results', async () => {
      const mockResponse = {
        data: [],
        total_parts: 0,
      }

      vi.mocked(apiClient.get).mockResolvedValue(mockResponse)

      const result = await partsService.searchPartsText('nonexistent')

      expect(result).toEqual({
        data: [],
        total_parts: 0,
      })
    })
  })

  describe('getPartSuggestions', () => {
    it('returns suggestions for valid query', async () => {
      const mockResponse = {
        data: ['Resistor 10K', 'Resistor 1K', 'Resistor 100K'],
      }

      vi.mocked(apiClient.get).mockResolvedValue(mockResponse)

      const result = await partsService.getPartSuggestions('resistor')

      expect(apiClient.get).toHaveBeenCalledWith('/api/parts/suggestions', {
        params: { query: 'resistor', limit: 10 },
      })
      expect(result).toEqual(['Resistor 10K', 'Resistor 1K', 'Resistor 100K'])
    })

    it('returns empty array for short query', async () => {
      const result = await partsService.getPartSuggestions('ab')

      expect(result).toEqual([])
      expect(apiClient.get).not.toHaveBeenCalled()
    })

    it('handles API errors gracefully', async () => {
      vi.mocked(apiClient.get).mockRejectedValue(new Error('Network error'))

      const result = await partsService.getPartSuggestions('resistor')

      expect(result).toEqual([])
    })
  })

  describe('checkNameExists', () => {
    it('checks if part name exists', async () => {
      const mockResponse = { data: true }

      vi.mocked(apiClient.get).mockResolvedValue(mockResponse)

      const result = await partsService.checkNameExists('Existing Part')

      expect(apiClient.get).toHaveBeenCalledWith('/api/parts/check_name_exists', {
        params: { name: 'Existing Part', exclude_id: undefined },
      })
      expect(result).toBe(true)
    })

    it('handles API errors gracefully', async () => {
      vi.mocked(apiClient.get).mockRejectedValue(new Error('Network error'))

      const result = await partsService.checkNameExists('Test Part')

      expect(result).toBe(false)
    })
  })
})
