import { describe, it, expect, vi, beforeEach } from 'vitest'
import { usePartsStore } from '../partsStore'
import { useLocationsStore } from '../locationsStore'
import { useCategoriesStore } from '../categoriesStore'
import { partsService } from '@/services/parts.service'
import { locationsService } from '@/services/locations.service'
import { categoriesService } from '@/services/categories.service'
import { toast } from 'react-hot-toast'

// Mock services
vi.mock('@/services/parts.service')
vi.mock('@/services/locations.service')
vi.mock('@/services/categories.service')
vi.mock('react-hot-toast')

describe('Store Refactoring Tests', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('PartsStore', () => {
    it('should have clean parts-only state', () => {
      const store = usePartsStore.getState()

      // Should have parts-specific state
      expect(store.parts).toEqual([])
      expect(store.currentPart).toBe(null)
      expect(store.totalParts).toBe(0)
      expect(store.currentPage).toBe(1)
      expect(store.pageSize).toBe(20)
      expect(store.totalPages).toBe(0)
      expect(store.isLoading).toBe(false)
      expect(store.isLoadingPart).toBe(false)
      expect(store.error).toBe(null)
      expect(store.searchQuery).toBe('')
      expect(store.selectedFilters).toEqual({})

      // Should NOT have locations or categories
      expect('locations' in store).toBe(false)
      expect('categories' in store).toBe(false)
      expect('loadLocations' in store).toBe(false)
      expect('loadCategories' in store).toBe(false)
    })

    it('should load parts correctly', async () => {
      const mockParts = [
        { id: '1', name: 'Part 1', description: 'Description 1' },
        { id: '2', name: 'Part 2', description: 'Description 2' },
      ]

      vi.mocked(partsService.getAllParts).mockResolvedValueOnce({
        data: mockParts,
        total_parts: 2,
      })

      const store = usePartsStore.getState()
      await store.loadParts(1)

      expect(partsService.getAllParts).toHaveBeenCalledWith(1, 20)
      expect(usePartsStore.getState().parts).toEqual(mockParts)
      expect(usePartsStore.getState().totalParts).toBe(2)
      expect(usePartsStore.getState().currentPage).toBe(1)
      expect(usePartsStore.getState().isLoading).toBe(false)
    })

    it('should create parts correctly', async () => {
      const mockPart = { id: '1', name: 'New Part', description: 'New Description' }

      vi.mocked(partsService.createPart).mockResolvedValueOnce(mockPart)
      vi.mocked(partsService.getAllParts).mockResolvedValueOnce({
        data: [mockPart],
        total_parts: 1,
      })

      const store = usePartsStore.getState()
      const result = await store.createPart({
        name: 'New Part',
        description: 'New Description',
      })

      expect(partsService.createPart).toHaveBeenCalledWith({
        name: 'New Part',
        description: 'New Description',
      })
      expect(result).toEqual(mockPart)
      expect(toast.success).toHaveBeenCalledWith('Part created successfully')
    })

    it('should handle search correctly', async () => {
      const mockSearchResponse = {
        items: [{ id: '1', name: 'Found Part' }],
        total: 1,
        page: 1,
        total_pages: 1,
      }

      vi.mocked(partsService.searchParts).mockResolvedValueOnce(mockSearchResponse)

      const store = usePartsStore.getState()
      await store.searchParts('test query', { category_names: ['electronics'] })

      expect(partsService.searchParts).toHaveBeenCalledWith({
        query: 'test query',
        category_names: ['electronics'],
        page: 1,
        page_size: 20,
      })
      expect(usePartsStore.getState().parts).toEqual(mockSearchResponse.items)
      expect(usePartsStore.getState().totalParts).toBe(1)
      expect(usePartsStore.getState().searchQuery).toBe('test query')
    })
  })

  describe('LocationsStore', () => {
    it('should have clean locations-only state', () => {
      const store = useLocationsStore.getState()

      expect(store.locations).toEqual([])
      expect(store.currentLocation).toBe(null)
      expect(store.locationTree).toEqual([])
      expect(store.isLoading).toBe(false)
      expect(store.isLoadingLocation).toBe(false)
      expect(store.error).toBe(null)

      // Should have location-specific methods
      expect(typeof store.loadLocations).toBe('function')
      expect(typeof store.createLocation).toBe('function')
      expect(typeof store.updateLocation).toBe('function')
      expect(typeof store.deleteLocation).toBe('function')
      expect(typeof store.buildLocationTree).toBe('function')
      expect(typeof store.getLocationById).toBe('function')
      expect(typeof store.getLocationsByParent).toBe('function')
    })

    it('should load locations correctly', async () => {
      const mockLocations = [
        { id: '1', name: 'Location 1', parent_id: null },
        { id: '2', name: 'Location 2', parent_id: '1' },
      ]

      vi.mocked(locationsService.getAllLocations).mockResolvedValueOnce(mockLocations)
      vi.mocked(locationsService.buildLocationTree).mockReturnValueOnce([
        {
          id: '1',
          name: 'Location 1',
          parent_id: null,
          children: [{ id: '2', name: 'Location 2', parent_id: '1', children: [] }],
        },
      ])

      const store = useLocationsStore.getState()
      await store.loadLocations()

      expect(locationsService.getAllLocations).toHaveBeenCalled()
      expect(useLocationsStore.getState().locations).toEqual(mockLocations)
      expect(useLocationsStore.getState().isLoading).toBe(false)
    })

    it('should create locations correctly', async () => {
      const mockLocation = { id: '1', name: 'New Location', parent_id: null }

      vi.mocked(locationsService.createLocation).mockResolvedValueOnce(mockLocation)
      vi.mocked(locationsService.getAllLocations).mockResolvedValueOnce([mockLocation])
      vi.mocked(locationsService.buildLocationTree).mockReturnValueOnce([mockLocation])

      const store = useLocationsStore.getState()
      const result = await store.createLocation({
        name: 'New Location',
        parent_id: null,
      })

      expect(locationsService.createLocation).toHaveBeenCalledWith({
        name: 'New Location',
        parent_id: null,
      })
      expect(result).toEqual(mockLocation)
      expect(toast.success).toHaveBeenCalledWith('Location created successfully')
    })

    it('should find locations by parent correctly', () => {
      const mockLocations = [
        { id: '1', name: 'Location 1', parent_id: null },
        { id: '2', name: 'Location 2', parent_id: '1' },
        { id: '3', name: 'Location 3', parent_id: '1' },
        { id: '4', name: 'Location 4', parent_id: '2' },
      ]

      // Set up initial state
      useLocationsStore.setState({ locations: mockLocations })

      const store = useLocationsStore.getState()
      const childrenOf1 = store.getLocationsByParent('1')
      const rootLocations = store.getLocationsByParent(null)

      expect(childrenOf1).toHaveLength(2)
      expect(childrenOf1.map((l) => l.id)).toEqual(['2', '3'])
      expect(rootLocations).toHaveLength(1)
      expect(rootLocations[0].id).toBe('1')
    })
  })

  describe('CategoriesStore', () => {
    it('should have clean categories-only state', () => {
      const store = useCategoriesStore.getState()

      expect(store.categories).toEqual([])
      expect(store.currentCategory).toBe(null)
      expect(store.isLoading).toBe(false)
      expect(store.isLoadingCategory).toBe(false)
      expect(store.error).toBe(null)
      expect(store.searchQuery).toBe('')
      expect(store.filteredCategories).toEqual([])

      // Should have category-specific methods
      expect(typeof store.loadCategories).toBe('function')
      expect(typeof store.createCategory).toBe('function')
      expect(typeof store.updateCategory).toBe('function')
      expect(typeof store.deleteCategory).toBe('function')
      expect(typeof store.searchCategories).toBe('function')
      expect(typeof store.getCategoryById).toBe('function')
      expect(typeof store.getCategoryByName).toBe('function')
    })

    it('should load categories correctly', async () => {
      const mockCategories = [
        { id: '1', name: 'Category 1', description: 'Description 1' },
        { id: '2', name: 'Category 2', description: 'Description 2' },
      ]

      vi.mocked(categoriesService.getAllCategories).mockResolvedValueOnce(mockCategories)

      const store = useCategoriesStore.getState()
      await store.loadCategories()

      expect(categoriesService.getAllCategories).toHaveBeenCalled()
      expect(useCategoriesStore.getState().categories).toEqual(mockCategories)
      expect(useCategoriesStore.getState().filteredCategories).toEqual(mockCategories)
      expect(useCategoriesStore.getState().isLoading).toBe(false)
    })

    it('should create categories correctly', async () => {
      const mockCategory = { id: '1', name: 'New Category', description: 'New Description' }

      vi.mocked(categoriesService.createCategory).mockResolvedValueOnce(mockCategory)
      vi.mocked(categoriesService.getAllCategories).mockResolvedValueOnce([mockCategory])

      const store = useCategoriesStore.getState()
      const result = await store.createCategory({
        name: 'New Category',
        description: 'New Description',
      })

      expect(categoriesService.createCategory).toHaveBeenCalledWith({
        name: 'New Category',
        description: 'New Description',
      })
      expect(result).toEqual(mockCategory)
      expect(toast.success).toHaveBeenCalledWith('Category created successfully')
    })

    it('should search categories correctly', () => {
      const mockCategories = [
        { id: '1', name: 'Electronics', description: 'Electronic components' },
        { id: '2', name: 'Resistors', description: 'Passive components' },
        { id: '3', name: 'Capacitors', description: 'Energy storage' },
      ]

      vi.mocked(categoriesService.filterCategories).mockReturnValueOnce([
        { id: '1', name: 'Electronics', description: 'Electronic components' },
      ])

      // Set up initial state
      useCategoriesStore.setState({ categories: mockCategories })

      const store = useCategoriesStore.getState()
      store.searchCategories('electronics')

      expect(categoriesService.filterCategories).toHaveBeenCalledWith(mockCategories, 'electronics')
      expect(useCategoriesStore.getState().filteredCategories).toHaveLength(1)
    })

    it('should find categories by ID and name correctly', () => {
      const mockCategories = [
        { id: '1', name: 'Electronics', description: 'Electronic components' },
        { id: '2', name: 'Resistors', description: 'Passive components' },
      ]

      // Set up initial state
      useCategoriesStore.setState({ categories: mockCategories })

      const store = useCategoriesStore.getState()
      const foundById = store.getCategoryById('1')
      const foundByName = store.getCategoryByName('Resistors')

      expect(foundById).toEqual(mockCategories[0])
      expect(foundByName).toEqual(mockCategories[1])
    })
  })

  describe('Store Separation', () => {
    it('should demonstrate store independence', () => {
      // Each store should be independent
      const partsStore = usePartsStore.getState()
      const locationsStore = useLocationsStore.getState()
      const categoriesStore = useCategoriesStore.getState()

      // Parts store should not have location/category data
      expect('locations' in partsStore).toBe(false)
      expect('categories' in partsStore).toBe(false)

      // Location store should not have parts/category data
      expect('parts' in locationsStore).toBe(false)
      expect('categories' in locationsStore).toBe(false)

      // Category store should not have parts/location data
      expect('parts' in categoriesStore).toBe(false)
      expect('locations' in categoriesStore).toBe(false)
    })
  })
})
