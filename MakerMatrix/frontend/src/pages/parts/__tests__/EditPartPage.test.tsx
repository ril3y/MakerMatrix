import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { BrowserRouter } from 'react-router-dom'
import { toast } from 'react-hot-toast'
import EditPartPage from '../EditPartPage'
import { partsService } from '@/services/parts.service'
import { locationsService } from '@/services/locations.service'
import { categoriesService } from '@/services/categories.service'
import type { Part, Location } from '@/types/parts'
import type { Category } from '@/types/categories'

// Mock dependencies
vi.mock('react-hot-toast')
vi.mock('@/services/parts.service')
vi.mock('@/services/locations.service')
vi.mock('@/services/categories.service')
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom')
  return {
    ...actual,
    useParams: () => ({ id: 'part-123' }),
    useNavigate: () => vi.fn(),
  }
})

const mockPartsService = vi.mocked(partsService)
const mockLocationsService = vi.mocked(locationsService)
const mockCategoriesService = vi.mocked(categoriesService)
const mockToast = vi.mocked(toast)

// Wrapper component for router
const RouterWrapper = ({ children }: { children: React.ReactNode }) => (
  <BrowserRouter>{children}</BrowserRouter>
)

describe('EditPartPage - Parts Update Functionality', () => {
  const mockPart: Part = {
    id: 'part-123',
    name: 'Test Resistor',
    part_number: 'R001',
    description: 'Test resistor 1k ohm',
    quantity: 100,
    minimum_quantity: 10,
    location_id: 'loc-1',
    supplier: 'Test Supplier',
    supplier_url: 'https://supplier.com/part',
    image_url: 'https://example.com/image.jpg',
    created_at: '2024-01-01T00:00:00Z',
    updated_at: '2024-01-01T00:00:00Z',
    categories: [
      { id: 'cat-1', name: 'Electronics', description: 'Electronic components' },
      { id: 'cat-2', name: 'Resistors', description: 'Various resistors' },
    ],
    additional_properties: {
      resistance: '1k ohm',
      tolerance: '5%',
    },
  }

  const mockLocations: Location[] = [
    {
      id: 'loc-1',
      name: 'Warehouse A',
      description: 'Main warehouse',
      location_type: 'warehouse',
      parent_id: undefined,
      created_at: '2024-01-01T00:00:00Z',
      updated_at: '2024-01-01T00:00:00Z',
    },
    {
      id: 'loc-2',
      name: 'Electronics Room',
      description: 'Electronics storage',
      location_type: 'room',
      parent_id: 'loc-1',
      created_at: '2024-01-01T00:00:00Z',
      updated_at: '2024-01-01T00:00:00Z',
    },
  ]

  const mockCategories: Category[] = [
    { id: 'cat-1', name: 'Electronics', description: 'Electronic components' },
    { id: 'cat-2', name: 'Resistors', description: 'Various resistors' },
    { id: 'cat-3', name: 'Capacitors', description: 'Various capacitors' },
  ]

  beforeEach(() => {
    vi.clearAllMocks()

    // Mock successful data loading
    mockPartsService.getPart.mockResolvedValue(mockPart)
    mockLocationsService.getAll.mockResolvedValue(mockLocations)
    mockCategoriesService.getAll.mockResolvedValue(mockCategories)

    // Mock successful part update
    mockPartsService.updatePart.mockResolvedValue(mockPart)

    // Mock successful part deletion
    mockPartsService.deletePart.mockResolvedValue(undefined)
  })

  describe('Data Loading and Form Population', () => {
    it('should load part data and populate form fields', async () => {
      render(<EditPartPage />, { wrapper: RouterWrapper })

      await waitFor(() => {
        expect(mockPartsService.getPart).toHaveBeenCalledWith('part-123')
        expect(mockLocationsService.getAll).toHaveBeenCalled()
        expect(mockCategoriesService.getAll).toHaveBeenCalled()
      })

      // Check basic fields are populated
      await waitFor(() => {
        expect(screen.getByDisplayValue('Test Resistor')).toBeInTheDocument()
        expect(screen.getByDisplayValue('R001')).toBeInTheDocument()
        expect(screen.getByDisplayValue('Test resistor 1k ohm')).toBeInTheDocument()
        expect(screen.getByDisplayValue('100')).toBeInTheDocument()
      })
    })

    it('should show loading state while fetching data', () => {
      mockPartsService.getPart.mockImplementation(
        () => new Promise((resolve) => setTimeout(() => resolve(mockPart), 100))
      )

      render(<EditPartPage />, { wrapper: RouterWrapper })

      expect(screen.getByRole('generic', { name: /loading/i })).toBeInTheDocument()
    })

    it('should handle data loading error', async () => {
      mockPartsService.getPart.mockRejectedValueOnce(new Error('Part not found'))

      render(<EditPartPage />, { wrapper: RouterWrapper })

      await waitFor(() => {
        expect(mockToast.error).toHaveBeenCalledWith('Failed to load part data')
      })
    })

    it('should show not found message when part does not exist', async () => {
      mockPartsService.getPart.mockRejectedValueOnce(new Error('Not found'))

      render(<EditPartPage />, { wrapper: RouterWrapper })

      await waitFor(() => {
        expect(screen.getByText('Part not found')).toBeInTheDocument()
      })
    })
  })

  describe('Location Assignment', () => {
    it('should display current location in dropdown', async () => {
      render(<EditPartPage />, { wrapper: RouterWrapper })

      await waitFor(() => {
        const locationSelect = screen.getByDisplayValue('Warehouse A')
        expect(locationSelect).toBeInTheDocument()
      })
    })

    it('should show locations in hierarchical format', async () => {
      render(<EditPartPage />, { wrapper: RouterWrapper })

      await waitFor(() => {
        expect(screen.getByText('Warehouse A')).toBeInTheDocument()
        expect(screen.getByText('└ Electronics Room')).toBeInTheDocument()
      })
    })

    it('should allow changing part location', async () => {
      const user = userEvent.setup()
      render(<EditPartPage />, { wrapper: RouterWrapper })

      await waitFor(() => {
        expect(screen.getByDisplayValue('Warehouse A')).toBeInTheDocument()
      })

      const locationSelect = screen.getByDisplayValue('Warehouse A')
      await user.selectOptions(locationSelect, 'loc-2')

      expect(locationSelect).toHaveValue('loc-2')
    })

    it('should allow clearing part location', async () => {
      const user = userEvent.setup()
      render(<EditPartPage />, { wrapper: RouterWrapper })

      await waitFor(() => {
        expect(screen.getByDisplayValue('Warehouse A')).toBeInTheDocument()
      })

      const locationSelect = screen.getByDisplayValue('Warehouse A')
      await user.selectOptions(locationSelect, '')

      expect(locationSelect).toHaveValue('')
    })
  })

  describe('Category Assignment', () => {
    it('should display currently assigned categories', async () => {
      render(<EditPartPage />, { wrapper: RouterWrapper })

      await waitFor(() => {
        const electronicsCategory = screen.getByRole('button', { name: 'Electronics' })
        const resistorsCategory = screen.getByRole('button', { name: 'Resistors' })

        expect(electronicsCategory).toHaveClass('bg-purple-600')
        expect(resistorsCategory).toHaveClass('bg-purple-600')
      })
    })

    it('should show unselected categories with different styling', async () => {
      render(<EditPartPage />, { wrapper: RouterWrapper })

      await waitFor(() => {
        const capacitorsCategory = screen.getByRole('button', { name: 'Capacitors' })
        expect(capacitorsCategory).toHaveClass('bg-gray-700')
      })
    })

    it('should allow adding category to part', async () => {
      const user = userEvent.setup()
      render(<EditPartPage />, { wrapper: RouterWrapper })

      await waitFor(() => {
        expect(screen.getByRole('button', { name: 'Capacitors' })).toBeInTheDocument()
      })

      const capacitorsCategory = screen.getByRole('button', { name: 'Capacitors' })
      await user.click(capacitorsCategory)

      expect(capacitorsCategory).toHaveClass('bg-purple-600')
    })

    it('should allow removing category from part', async () => {
      const user = userEvent.setup()
      render(<EditPartPage />, { wrapper: RouterWrapper })

      await waitFor(() => {
        expect(screen.getByRole('button', { name: 'Electronics' })).toBeInTheDocument()
      })

      const electronicsCategory = screen.getByRole('button', { name: 'Electronics' })
      await user.click(electronicsCategory)

      expect(electronicsCategory).toHaveClass('bg-gray-700')
    })

    it('should handle toggling multiple categories', async () => {
      const user = userEvent.setup()
      render(<EditPartPage />, { wrapper: RouterWrapper })

      await waitFor(() => {
        expect(screen.getByRole('button', { name: 'Capacitors' })).toBeInTheDocument()
      })

      // Add capacitors
      const capacitorsCategory = screen.getByRole('button', { name: 'Capacitors' })
      await user.click(capacitorsCategory)

      // Remove resistors
      const resistorsCategory = screen.getByRole('button', { name: 'Resistors' })
      await user.click(resistorsCategory)

      expect(capacitorsCategory).toHaveClass('bg-purple-600')
      expect(resistorsCategory).toHaveClass('bg-gray-700')
    })
  })

  describe('Additional Properties Management', () => {
    it('should display existing additional properties', async () => {
      render(<EditPartPage />, { wrapper: RouterWrapper })

      await waitFor(() => {
        expect(screen.getByDisplayValue('resistance')).toBeInTheDocument()
        expect(screen.getByDisplayValue('1k ohm')).toBeInTheDocument()
        expect(screen.getByDisplayValue('tolerance')).toBeInTheDocument()
        expect(screen.getByDisplayValue('5%')).toBeInTheDocument()
      })
    })

    it('should allow adding new additional property', async () => {
      const user = userEvent.setup()
      render(<EditPartPage />, { wrapper: RouterWrapper })

      await waitFor(() => {
        expect(
          screen.getByPlaceholderText('Property name (e.g., resistance, voltage)')
        ).toBeInTheDocument()
      })

      const keyInput = screen.getByPlaceholderText('Property name (e.g., resistance, voltage)')
      const valueInput = screen.getByPlaceholderText('Value (e.g., 10kΩ, 5V)')

      await user.type(keyInput, 'power_rating')
      await user.type(valueInput, '0.25W')

      const addButton = screen.getByRole('button', { name: /add/i })
      await user.click(addButton)

      expect(screen.getByDisplayValue('power_rating')).toBeInTheDocument()
      expect(screen.getByDisplayValue('0.25W')).toBeInTheDocument()
    })

    it('should allow removing additional property', async () => {
      const user = userEvent.setup()
      render(<EditPartPage />, { wrapper: RouterWrapper })

      await waitFor(() => {
        expect(screen.getByDisplayValue('resistance')).toBeInTheDocument()
      })

      const removeButtons = screen.getAllByTitle('Remove property')
      await user.click(removeButtons[0])

      expect(screen.queryByDisplayValue('resistance')).not.toBeInTheDocument()
    })

    it('should allow editing existing property value', async () => {
      const user = userEvent.setup()
      render(<EditPartPage />, { wrapper: RouterWrapper })

      await waitFor(() => {
        expect(screen.getByDisplayValue('1k ohm')).toBeInTheDocument()
      })

      const valueInput = screen.getByDisplayValue('1k ohm')
      await user.clear(valueInput)
      await user.type(valueInput, '2.2k ohm')

      expect(screen.getByDisplayValue('2.2k ohm')).toBeInTheDocument()
    })

    it('should show property count', async () => {
      render(<EditPartPage />, { wrapper: RouterWrapper })

      await waitFor(() => {
        expect(screen.getByText('2 properties')).toBeInTheDocument()
      })
    })
  })

  describe('Form Validation', () => {
    it('should show validation error for empty name', async () => {
      const user = userEvent.setup()
      render(<EditPartPage />, { wrapper: RouterWrapper })

      await waitFor(() => {
        expect(screen.getByDisplayValue('Test Resistor')).toBeInTheDocument()
      })

      const nameInput = screen.getByDisplayValue('Test Resistor')
      await user.clear(nameInput)

      const saveButton = screen.getByText('Save Changes')
      await user.click(saveButton)

      await waitFor(() => {
        expect(screen.getByText('Name is required')).toBeInTheDocument()
      })
    })

    it('should show validation error for negative quantity', async () => {
      const user = userEvent.setup()
      render(<EditPartPage />, { wrapper: RouterWrapper })

      await waitFor(() => {
        expect(screen.getByDisplayValue('100')).toBeInTheDocument()
      })

      const quantityInput = screen.getByDisplayValue('100')
      await user.clear(quantityInput)
      await user.type(quantityInput, '-5')

      const saveButton = screen.getByText('Save Changes')
      await user.click(saveButton)

      await waitFor(() => {
        expect(screen.getByText('Quantity must be non-negative')).toBeInTheDocument()
      })
    })

    it('should show validation error for invalid URL', async () => {
      const user = userEvent.setup()
      render(<EditPartPage />, { wrapper: RouterWrapper })

      await waitFor(() => {
        expect(screen.getByDisplayValue('https://supplier.com/part')).toBeInTheDocument()
      })

      const urlInput = screen.getByDisplayValue('https://supplier.com/part')
      await user.clear(urlInput)
      await user.type(urlInput, 'invalid-url')

      const saveButton = screen.getByText('Save Changes')
      await user.click(saveButton)

      await waitFor(() => {
        expect(screen.getByText('Invalid URL')).toBeInTheDocument()
      })
    })
  })

  describe('Part Update', () => {
    it('should update part with all changes', async () => {
      const user = userEvent.setup()
      render(<EditPartPage />, { wrapper: RouterWrapper })

      await waitFor(() => {
        expect(screen.getByDisplayValue('Test Resistor')).toBeInTheDocument()
      })

      // Make changes
      const nameInput = screen.getByDisplayValue('Test Resistor')
      await user.clear(nameInput)
      await user.type(nameInput, 'Updated Resistor')

      const quantityInput = screen.getByDisplayValue('100')
      await user.clear(quantityInput)
      await user.type(quantityInput, '150')

      // Change location
      const locationSelect = screen.getByDisplayValue('Warehouse A')
      await user.selectOptions(locationSelect, 'loc-2')

      // Add category
      const capacitorsCategory = screen.getByRole('button', { name: 'Capacitors' })
      await user.click(capacitorsCategory)

      const saveButton = screen.getByText('Save Changes')
      await user.click(saveButton)

      await waitFor(() => {
        expect(mockPartsService.updatePart).toHaveBeenCalledWith({
          id: 'part-123',
          name: 'Updated Resistor',
          part_number: 'R001',
          description: 'Test resistor 1k ohm',
          quantity: 150,
          minimum_quantity: 10,
          location_id: 'loc-2',
          supplier: 'Test Supplier',
          supplier_url: 'https://supplier.com/part',
          image_url: 'https://example.com/image.jpg',
          categories: ['cat-1', 'cat-2', 'cat-3'], // Electronics, Resistors, Capacitors
          additional_properties: {
            resistance: '1k ohm',
            tolerance: '5%',
          },
        })
      })

      expect(mockToast.success).toHaveBeenCalledWith('Part updated successfully')
    })

    it('should handle update API error', async () => {
      const user = userEvent.setup()
      mockPartsService.updatePart.mockRejectedValueOnce(new Error('Update failed'))

      render(<EditPartPage />, { wrapper: RouterWrapper })

      await waitFor(() => {
        expect(screen.getByText('Save Changes')).toBeInTheDocument()
      })

      const saveButton = screen.getByText('Save Changes')
      await user.click(saveButton)

      await waitFor(() => {
        expect(mockToast.error).toHaveBeenCalledWith('Failed to update part')
      })
    })

    it('should show saving state during update', async () => {
      const user = userEvent.setup()

      mockPartsService.updatePart.mockImplementation(
        () => new Promise((resolve) => setTimeout(() => resolve(mockPart), 100))
      )

      render(<EditPartPage />, { wrapper: RouterWrapper })

      await waitFor(() => {
        expect(screen.getByText('Save Changes')).toBeInTheDocument()
      })

      const saveButton = screen.getByText('Save Changes')
      await user.click(saveButton)

      await waitFor(() => {
        expect(screen.getByText('Saving...')).toBeInTheDocument()
        expect(screen.getByText('Saving...')).toBeDisabled()
      })
    })
  })

  describe('Part Deletion', () => {
    it('should delete part when confirmed', async () => {
      const user = userEvent.setup()

      // Mock window.confirm
      vi.stubGlobal(
        'confirm',
        vi.fn(() => true)
      )

      render(<EditPartPage />, { wrapper: RouterWrapper })

      await waitFor(() => {
        expect(screen.getByText('Delete')).toBeInTheDocument()
      })

      const deleteButton = screen.getByText('Delete')
      await user.click(deleteButton)

      await waitFor(() => {
        expect(mockPartsService.deletePart).toHaveBeenCalledWith('part-123')
        expect(mockToast.success).toHaveBeenCalledWith('Part deleted successfully')
      })
    })

    it('should not delete part when cancelled', async () => {
      const user = userEvent.setup()

      // Mock window.confirm to return false
      vi.stubGlobal(
        'confirm',
        vi.fn(() => false)
      )

      render(<EditPartPage />, { wrapper: RouterWrapper })

      await waitFor(() => {
        expect(screen.getByText('Delete')).toBeInTheDocument()
      })

      const deleteButton = screen.getByText('Delete')
      await user.click(deleteButton)

      expect(mockPartsService.deletePart).not.toHaveBeenCalled()
    })

    it('should handle delete API error', async () => {
      const user = userEvent.setup()
      mockPartsService.deletePart.mockRejectedValueOnce(new Error('Delete failed'))

      vi.stubGlobal(
        'confirm',
        vi.fn(() => true)
      )

      render(<EditPartPage />, { wrapper: RouterWrapper })

      await waitFor(() => {
        expect(screen.getByText('Delete')).toBeInTheDocument()
      })

      const deleteButton = screen.getByText('Delete')
      await user.click(deleteButton)

      await waitFor(() => {
        expect(mockToast.error).toHaveBeenCalledWith('Failed to delete part')
      })
    })

    it('should show deleting state during deletion', async () => {
      const user = userEvent.setup()

      mockPartsService.deletePart.mockImplementation(
        () => new Promise((resolve) => setTimeout(resolve, 100))
      )

      vi.stubGlobal(
        'confirm',
        vi.fn(() => true)
      )

      render(<EditPartPage />, { wrapper: RouterWrapper })

      await waitFor(() => {
        expect(screen.getByText('Delete')).toBeInTheDocument()
      })

      const deleteButton = screen.getByText('Delete')
      await user.click(deleteButton)

      await waitFor(() => {
        expect(screen.getByText('Deleting...')).toBeInTheDocument()
        expect(screen.getByText('Deleting...')).toBeDisabled()
      })
    })
  })

  describe('Integration Scenarios', () => {
    it('should handle part with no location or categories', async () => {
      const partWithoutLocationAndCategories = {
        ...mockPart,
        location_id: undefined,
        categories: [],
      }

      mockPartsService.getPart.mockResolvedValueOnce(partWithoutLocationAndCategories)

      render(<EditPartPage />, { wrapper: RouterWrapper })

      await waitFor(() => {
        const locationSelect = screen.getByDisplayValue('Select location')
        expect(locationSelect).toBeInTheDocument()

        const categories = screen
          .getAllByRole('button')
          .filter((btn) =>
            ['Electronics', 'Resistors', 'Capacitors'].includes(btn.textContent || '')
          )
        categories.forEach((category) => {
          expect(category).toHaveClass('bg-gray-700')
        })
      })
    })

    it('should handle part with additional properties as objects', async () => {
      const partWithComplexProperties = {
        ...mockPart,
        additional_properties: {
          specs: { voltage: '5V', current: '100mA' },
          notes: 'Test component',
        },
      }

      mockPartsService.getPart.mockResolvedValueOnce(partWithComplexProperties)

      render(<EditPartPage />, { wrapper: RouterWrapper })

      await waitFor(() => {
        expect(screen.getByDisplayValue('{"voltage":"5V","current":"100mA"}')).toBeInTheDocument()
        expect(screen.getByDisplayValue('Test component')).toBeInTheDocument()
      })
    })
  })
})
