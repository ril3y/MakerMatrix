import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { toast } from 'react-hot-toast'
import { BrowserRouter } from 'react-router-dom'

// Import components
import AddPartModal from '@/components/parts/AddPartModal'
import AddLocationModal from '@/components/locations/AddLocationModal'
import AddCategoryModal from '@/components/categories/AddCategoryModal'

// Import services
import { partsService } from '@/services/parts.service'
import { locationsService } from '@/services/locations.service'
import { categoriesService } from '@/services/categories.service'

// Import types
import type { Part, Location, Category } from '@/types/parts'

// Mock dependencies
vi.mock('react-hot-toast')
vi.mock('@/services/parts.service')
vi.mock('@/services/locations.service')
vi.mock('@/services/categories.service')
vi.mock('framer-motion', () => ({
  motion: {
    div: ({ children, ...props }: { children?: React.ReactNode; [key: string]: unknown }) => (
      <div {...props}>{children}</div>
    ),
  },
  AnimatePresence: ({ children }: { children: React.ReactNode }) => children,
}))

const mockPartsService = vi.mocked(partsService)
const mockLocationsService = vi.mocked(locationsService)
const mockCategoriesService = vi.mocked(categoriesService)
const mockToast = vi.mocked(toast)

// Router wrapper
const RouterWrapper = ({ children }: { children: React.ReactNode }) => (
  <BrowserRouter>{children}</BrowserRouter>
)

describe('Parts-Locations-Categories Integration Tests', () => {
  const mockLocations: Location[] = [
    {
      id: 'loc-warehouse',
      name: 'Main Warehouse',
      description: 'Primary storage facility',
      location_type: 'warehouse',
      parent_id: undefined,
      created_at: '2024-01-01T00:00:00Z',
      updated_at: '2024-01-01T00:00:00Z',
    },
    {
      id: 'loc-electronics',
      name: 'Electronics Room',
      description: 'Electronic components storage',
      location_type: 'room',
      parent_id: 'loc-warehouse',
      created_at: '2024-01-01T00:00:00Z',
      updated_at: '2024-01-01T00:00:00Z',
    },
    {
      id: 'loc-resistors',
      name: 'Resistor Shelf',
      description: 'Shelf for resistors',
      location_type: 'shelf',
      parent_id: 'loc-electronics',
      created_at: '2024-01-01T00:00:00Z',
      updated_at: '2024-01-01T00:00:00Z',
    },
  ]

  const mockCategories: Category[] = [
    { id: 'cat-electronics', name: 'Electronics', description: 'Electronic components' },
    { id: 'cat-resistors', name: 'Resistors', description: 'Various resistor types' },
    { id: 'cat-passive', name: 'Passive Components', description: 'Passive electronic components' },
  ]

  beforeEach(() => {
    vi.clearAllMocks()

    // Default successful responses
    mockLocationsService.getAllLocations.mockResolvedValue(mockLocations)
    mockCategoriesService.getAllCategories.mockResolvedValue(mockCategories)
    mockLocationsService.createLocation.mockResolvedValue(mockLocations[0])
    mockCategoriesService.createCategory.mockResolvedValue(mockCategories[0])
    mockPartsService.createPart.mockResolvedValue({
      id: 'part-123',
      name: 'Test Part',
      quantity: 10,
      created_at: '2024-01-01T00:00:00Z',
      updated_at: '2024-01-01T00:00:00Z',
    } as Part)
  })

  describe('Location Hierarchy in Part Creation', () => {
    it('should display location hierarchy correctly in part creation modal', async () => {
      const mockProps = {
        isOpen: true,
        onClose: vi.fn(),
        onSuccess: vi.fn(),
      }

      render(<AddPartModal {...mockProps} />, { wrapper: RouterWrapper })

      await waitFor(() => {
        expect(mockLocationsService.getAllLocations).toHaveBeenCalled()
      })

      // Check flat location display (AddPartModal shows simple list)
      await waitFor(() => {
        expect(screen.getByText('Main Warehouse')).toBeInTheDocument()
        expect(screen.getByText('Electronics Room')).toBeInTheDocument()
        expect(screen.getByText('Resistor Shelf')).toBeInTheDocument()
      })
    })

    it('should create part with correct location reference', async () => {
      const user = userEvent.setup()
      const mockProps = {
        isOpen: true,
        onClose: vi.fn(),
        onSuccess: vi.fn(),
      }

      render(<AddPartModal {...mockProps} />, { wrapper: RouterWrapper })

      await waitFor(() => {
        expect(screen.getByPlaceholderText('Enter part name')).toBeInTheDocument()
      })

      // Fill part details
      const nameInput = screen.getByPlaceholderText('Enter part name')
      await user.type(nameInput, '1K Resistor')

      // Find quantity input by looking for number input after quantity label
      const quantityInput = screen.getAllByRole('spinbutton')[0] // First number input is quantity
      await user.type(quantityInput, '100')

      // Select location
      const locationSelect = screen.getByDisplayValue('Select a location')
      await user.selectOptions(locationSelect, 'loc-resistors')

      const submitButton = screen.getByText('Create Part')
      await user.click(submitButton)

      await waitFor(() => {
        expect(mockPartsService.createPart).toHaveBeenCalledWith(
          expect.objectContaining({
            name: '1K Resistor',
            quantity: 100,
            location_id: 'loc-resistors',
          })
        )
      })
    })
  })

  describe('Category Assignment in Part Creation', () => {
    it('should display all available categories for selection', async () => {
      const mockProps = {
        isOpen: true,
        onClose: vi.fn(),
        onSuccess: vi.fn(),
      }

      render(<AddPartModal {...mockProps} />, { wrapper: RouterWrapper })

      await waitFor(() => {
        expect(mockCategoriesService.getAllCategories).toHaveBeenCalled()
      })

      // Check categories are displayed
      await waitFor(() => {
        expect(screen.getByText('Electronics')).toBeInTheDocument()
        expect(screen.getByText('Resistors')).toBeInTheDocument()
        expect(screen.getByText('Passive Components')).toBeInTheDocument()
      })
    })

    it('should create part with multiple categories selected', async () => {
      const user = userEvent.setup()
      const mockProps = {
        isOpen: true,
        onClose: vi.fn(),
        onSuccess: vi.fn(),
      }

      render(<AddPartModal {...mockProps} />, { wrapper: RouterWrapper })

      await waitFor(() => {
        expect(screen.getByPlaceholderText('Enter part name')).toBeInTheDocument()
      })

      // Fill part details
      const nameInput = screen.getByPlaceholderText('Enter part name')
      await user.type(nameInput, '1K Resistor')

      // Find quantity input by looking for number input after quantity label
      const quantityInput = screen.getAllByRole('spinbutton')[0] // First number input is quantity
      await user.type(quantityInput, '100')

      // Select multiple categories (using checkboxes)
      const electronicsCategory = screen.getByRole('checkbox', { name: 'Electronics' })
      const resistorsCategory = screen.getByRole('checkbox', { name: 'Resistors' })
      const passiveCategory = screen.getByRole('checkbox', { name: 'Passive Components' })

      await user.click(electronicsCategory)
      await user.click(resistorsCategory)
      await user.click(passiveCategory)

      const submitButton = screen.getByText('Create Part')
      await user.click(submitButton)

      await waitFor(() => {
        expect(mockPartsService.createPart).toHaveBeenCalledWith(
          expect.objectContaining({
            name: '1K Resistor',
            quantity: 100,
            categories: ['cat-electronics', 'cat-resistors', 'cat-passive'],
          })
        )
      })
    })
  })

  describe('Full Workflow: Location → Category → Part Creation', () => {
    it('should complete full workflow from location creation to part creation', async () => {
      const user = userEvent.setup()

      // Step 1: Create a new location
      const locationProps = {
        isOpen: true,
        onClose: vi.fn(),
        onSuccess: vi.fn(),
      }

      const { unmount: unmountLocation } = render(<AddLocationModal {...locationProps} />)

      await waitFor(() => {
        expect(screen.getByPlaceholderText('Enter location name')).toBeInTheDocument()
      })

      const locationNameInput = screen.getByPlaceholderText('Enter location name')
      await user.type(locationNameInput, 'Capacitor Drawer')

      const locationTypeSelect = screen.getByDisplayValue('Select a type')
      await user.selectOptions(locationTypeSelect, 'drawer')

      const locationParentSelect = screen.getByDisplayValue('No parent (root level)')
      await user.selectOptions(locationParentSelect, 'loc-electronics')

      const createLocationButton = screen.getByText('Create Location')
      await user.click(createLocationButton)

      await waitFor(() => {
        expect(mockLocationsService.createLocation).toHaveBeenCalledWith({
          name: 'Capacitor Drawer',
          type: 'drawer',
          parent_id: 'loc-electronics',
        })
      })

      unmountLocation()

      // Step 2: Create a new category
      const categoryProps = {
        isOpen: true,
        onClose: vi.fn(),
        onSuccess: vi.fn(),
        existingCategories: ['Electronics', 'Resistors', 'Passive Components'],
      }

      const { unmount: unmountCategory } = render(<AddCategoryModal {...categoryProps} />)

      await waitFor(() => {
        expect(screen.getByPlaceholderText('Enter category name')).toBeInTheDocument()
      })

      const categoryNameInput = screen.getByPlaceholderText('Enter category name')
      await user.type(categoryNameInput, 'Capacitors')

      const createCategoryButton = screen.getByText('Create Category')
      await user.click(createCategoryButton)

      await waitFor(() => {
        expect(mockCategoriesService.createCategory).toHaveBeenCalledWith({
          name: 'Capacitors',
        })
      })

      unmountCategory()

      // Step 3: Create a part using the new location and category
      // Mock updated data to include new location and category
      const updatedLocations = [
        ...mockLocations,
        {
          id: 'loc-capacitors',
          name: 'Capacitor Drawer',
          description: '',
          location_type: 'drawer',
          parent_id: 'loc-electronics',
          created_at: '2024-01-01T00:00:00Z',
          updated_at: '2024-01-01T00:00:00Z',
        },
      ]

      const updatedCategories = [
        ...mockCategories,
        { id: 'cat-capacitors', name: 'Capacitors', description: 'Various capacitor types' },
      ]

      mockLocationsService.getAllLocations.mockResolvedValue(updatedLocations)
      mockCategoriesService.getAllCategories.mockResolvedValue(updatedCategories)

      const partProps = {
        isOpen: true,
        onClose: vi.fn(),
        onSuccess: vi.fn(),
      }

      render(<AddPartModal {...partProps} />, { wrapper: RouterWrapper })

      await waitFor(() => {
        expect(screen.getByPlaceholderText('Enter part name')).toBeInTheDocument()
      })

      // Fill part details
      const partNameInput = screen.getByPlaceholderText('Enter part name')
      await user.type(partNameInput, '100nF Ceramic Capacitor')

      // Find quantity input by looking for number input after quantity label
      const quantityInput = screen.getAllByRole('spinbutton')[0] // First number input is quantity
      await user.type(quantityInput, '50')

      // Select the newly created location (should appear in list)
      await waitFor(() => {
        expect(screen.getByText('Capacitor Drawer')).toBeInTheDocument()
      })

      const locationSelect = screen.getByDisplayValue('Select a location')
      await user.selectOptions(locationSelect, 'loc-capacitors')

      // Select the newly created category
      await waitFor(() => {
        expect(screen.getByRole('checkbox', { name: 'Capacitors' })).toBeInTheDocument()
      })

      const capacitorsCategory = screen.getByRole('checkbox', { name: 'Capacitors' })
      const electronicsCategory = screen.getByRole('checkbox', { name: 'Electronics' })
      const passiveCategory = screen.getByRole('checkbox', { name: 'Passive Components' })

      await user.click(capacitorsCategory)
      await user.click(electronicsCategory)
      await user.click(passiveCategory)

      const createPartButton = screen.getByText('Create Part')
      await user.click(createPartButton)

      await waitFor(() => {
        expect(mockPartsService.createPart).toHaveBeenCalledWith(
          expect.objectContaining({
            name: '100nF Ceramic Capacitor',
            quantity: 50,
            location_id: 'loc-capacitors',
            categories: ['cat-capacitors', 'cat-electronics', 'cat-passive'],
          })
        )
      })
    })
  })

  describe('Error Handling in Integrated Workflows', () => {
    it('should handle location loading failure in part creation', async () => {
      mockLocationsService.getAllLocations.mockRejectedValueOnce(
        new Error('Failed to load locations')
      )

      const mockProps = {
        isOpen: true,
        onClose: vi.fn(),
        onSuccess: vi.fn(),
      }

      render(<AddPartModal {...mockProps} />, { wrapper: RouterWrapper })

      await waitFor(() => {
        expect(mockToast.error).toHaveBeenCalledWith('Failed to load data')
      })
    })

    it('should handle category loading failure in part creation', async () => {
      mockCategoriesService.getAllCategories.mockRejectedValueOnce(
        new Error('Failed to load categories')
      )

      const mockProps = {
        isOpen: true,
        onClose: vi.fn(),
        onSuccess: vi.fn(),
      }

      render(<AddPartModal {...mockProps} />, { wrapper: RouterWrapper })

      await waitFor(() => {
        expect(mockToast.error).toHaveBeenCalledWith('Failed to load data')
      })
    })

    it('should gracefully handle missing location reference', async () => {
      // Remove location from the list but part still references it
      mockLocationsService.getAllLocations.mockResolvedValue([mockLocations[0]]) // Only warehouse

      const mockProps = {
        isOpen: true,
        onClose: vi.fn(),
        onSuccess: vi.fn(),
      }

      render(<AddPartModal {...mockProps} />, { wrapper: RouterWrapper })

      await waitFor(() => {
        // Should still render without crashing
        expect(screen.getByText('Add New Part')).toBeInTheDocument()
        expect(screen.getByText('Main Warehouse')).toBeInTheDocument()
        expect(screen.queryByText('Electronics Room')).not.toBeInTheDocument()
      })
    })
  })

  describe('Data Consistency Validation', () => {
    it('should prevent creating part with non-existent location', async () => {
      const user = userEvent.setup()
      const mockProps = {
        isOpen: true,
        onClose: vi.fn(),
        onSuccess: vi.fn(),
      }

      render(<AddPartModal {...mockProps} />, { wrapper: RouterWrapper })

      await waitFor(() => {
        expect(screen.getByPlaceholderText('Enter part name')).toBeInTheDocument()
      })

      // Try to create part with invalid location ID (this would be handled by form validation)
      const nameInput = screen.getByPlaceholderText('Enter part name')
      await user.type(nameInput, 'Test Part')

      // Find quantity input by looking for number input after quantity label
      const quantityInput = screen.getAllByRole('spinbutton')[0] // First number input is quantity
      await user.type(quantityInput, '10')

      // The location dropdown should only show valid locations
      const locationSelect = screen.getByDisplayValue('Select a location')
      const options = locationSelect.querySelectorAll('option')

      // Should have default option plus valid locations
      expect(options).toHaveLength(mockLocations.length + 1) // +1 for "Select a location" option
    })

    it('should handle orphaned location hierarchy gracefully', async () => {
      // Create a location hierarchy with missing parent
      const orphanedLocations: Location[] = [
        {
          id: 'loc-orphan',
          name: 'Orphaned Room',
          location_type: 'room',
          parent_id: 'non-existent-parent', // Parent doesn't exist
          created_at: '2024-01-01T00:00:00Z',
          updated_at: '2024-01-01T00:00:00Z',
        },
        ...mockLocations,
      ]

      mockLocationsService.getAllLocations.mockResolvedValue(orphanedLocations)

      const mockProps = {
        isOpen: true,
        onClose: vi.fn(),
        onSuccess: vi.fn(),
      }

      render(<AddPartModal {...mockProps} />, { wrapper: RouterWrapper })

      await waitFor(() => {
        // Should render without crashing and show orphaned location at root level
        expect(screen.getByText('Orphaned Room')).toBeInTheDocument()
        expect(screen.getByText('Main Warehouse')).toBeInTheDocument()
      })
    })
  })

  describe('Performance Considerations', () => {
    it('should handle large numbers of locations efficiently', async () => {
      // Create a large hierarchy
      const manyLocations: Location[] = []
      for (let i = 0; i < 100; i++) {
        manyLocations.push({
          id: `loc-${i}`,
          name: `Location ${i}`,
          location_type: 'bin',
          parent_id: i % 10 === 0 ? undefined : `loc-${Math.floor(i / 10) * 10}`,
          created_at: '2024-01-01T00:00:00Z',
          updated_at: '2024-01-01T00:00:00Z',
        })
      }

      mockLocationsService.getAllLocations.mockResolvedValue(manyLocations)

      const mockProps = {
        isOpen: true,
        onClose: vi.fn(),
        onSuccess: vi.fn(),
      }

      const startTime = performance.now()
      render(<AddPartModal {...mockProps} />, { wrapper: RouterWrapper })

      await waitFor(() => {
        expect(screen.getByText('Location 0')).toBeInTheDocument()
      })

      const endTime = performance.now()

      // Should render within reasonable time (less than 1 second)
      expect(endTime - startTime).toBeLessThan(1000)
    })

    it('should handle many categories efficiently', async () => {
      // Create many categories
      const manyCategories: Category[] = []
      for (let i = 0; i < 50; i++) {
        manyCategories.push({
          id: `cat-${i}`,
          name: `Category ${i}`,
          description: `Description for category ${i}`,
        })
      }

      mockCategoriesService.getAllCategories.mockResolvedValue(manyCategories)

      const mockProps = {
        isOpen: true,
        onClose: vi.fn(),
        onSuccess: vi.fn(),
      }

      render(<AddPartModal {...mockProps} />, { wrapper: RouterWrapper })

      await waitFor(() => {
        expect(screen.getByText('Category 0')).toBeInTheDocument()
      })

      // Should display many categories
      // Check that the first few categories are present
      expect(screen.getByText('Category 0')).toBeInTheDocument()
      expect(screen.getByText('Category 1')).toBeInTheDocument()

      // Count actual category checkboxes in the DOM - should have at least some categories
      const categoryCheckboxes = screen.getAllByRole('checkbox').filter((checkbox) => {
        const label = checkbox.parentElement?.textContent || ''
        return label.startsWith('Category ')
      })

      // Should have rendered many categories (at least 10)
      expect(categoryCheckboxes.length).toBeGreaterThanOrEqual(10)
    })
  })
})
