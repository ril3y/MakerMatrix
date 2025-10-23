import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { toast } from 'react-hot-toast'
import AddPartModal from '../AddPartModal'
import { partsService } from '@/services/parts.service'
import { locationsService } from '@/services/locations.service'
import { categoriesService } from '@/services/categories.service'
import type { Part } from '@/types/parts'

// Mock dependencies
vi.mock('react-hot-toast')
vi.mock('@/services/parts.service')
vi.mock('@/services/locations.service')
vi.mock('@/services/categories.service')
vi.mock('@/services/utility.service')

const mockPartsService = vi.mocked(partsService)
const mockLocationsService = vi.mocked(locationsService)
const mockCategoriesService = vi.mocked(categoriesService)
const mockToast = vi.mocked(toast)

describe('AddPartModal - Core Functionality', () => {
  const mockProps = {
    isOpen: true,
    onClose: vi.fn(),
    onSuccess: vi.fn(),
  }

  beforeEach(() => {
    vi.clearAllMocks()

    // Mock successful data loading
    mockLocationsService.getAllLocations.mockResolvedValue([
      {
        id: 'loc1',
        name: 'Shelf A',
        description: 'Top shelf',
        location_type: 'shelf',
        parent_id: null,
      },
    ])
    mockCategoriesService.getAllCategories.mockResolvedValue([
      { id: 'cat1', name: 'Resistors', description: 'Electronic resistors' },
    ])

    // Mock successful part creation
    mockPartsService.createPart.mockResolvedValue({
      id: 'new-part-id',
      name: 'Test Part',
      part_number: 'TEST-001',
      quantity: 0,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    } as Part)
  })

  describe('Basic Rendering', () => {
    it('should render modal when open', async () => {
      render(<AddPartModal {...mockProps} />)

      expect(screen.getByText('Add New Part')).toBeInTheDocument()

      // Wait for form to load
      await waitFor(() => {
        expect(screen.getByPlaceholderText('Enter part name')).toBeInTheDocument()
      })
    })

    it('should not render modal when closed', () => {
      render(<AddPartModal {...mockProps} isOpen={false} />)

      expect(screen.queryByText('Add New Part')).not.toBeInTheDocument()
    })

    it('should load data on open', async () => {
      render(<AddPartModal {...mockProps} />)

      await waitFor(() => {
        expect(mockLocationsService.getAllLocations).toHaveBeenCalled()
        expect(mockCategoriesService.getAllCategories).toHaveBeenCalled()
      })
    })
  })

  describe('Form Validation', () => {
    it('should show error when part name is empty', async () => {
      const user = userEvent.setup()
      render(<AddPartModal {...mockProps} />)

      // Wait for form to load
      await waitFor(() => {
        expect(screen.getByPlaceholderText('Enter part name')).toBeInTheDocument()
      })

      const submitButton = screen.getByRole('button', { name: /create part/i })
      await user.click(submitButton)

      await waitFor(() => {
        expect(screen.getByText('Part name is required')).toBeInTheDocument()
      })
    })

    it('should accept valid form data', async () => {
      const user = userEvent.setup()
      render(<AddPartModal {...mockProps} />)

      // Wait for form to load
      await waitFor(() => {
        expect(screen.getByPlaceholderText('Enter part name')).toBeInTheDocument()
      })

      const nameInput = screen.getByPlaceholderText('Enter part name')
      await user.type(nameInput, 'Test Resistor')

      const submitButton = screen.getByRole('button', { name: /create part/i })
      await user.click(submitButton)

      await waitFor(() => {
        expect(mockPartsService.createPart).toHaveBeenCalledWith(
          expect.objectContaining({
            name: 'Test Resistor',
          })
        )
      })

      expect(mockToast.success).toHaveBeenCalledWith('Part created successfully')
      expect(mockProps.onSuccess).toHaveBeenCalled()
    })
  })

  describe('Error Handling', () => {
    it('should handle part creation error', async () => {
      const user = userEvent.setup()
      mockPartsService.createPart.mockRejectedValue({
        response: { data: { message: 'Part already exists' } },
      })

      render(<AddPartModal {...mockProps} />)

      // Wait for form to load
      await waitFor(() => {
        expect(screen.getByPlaceholderText('Enter part name')).toBeInTheDocument()
      })

      const nameInput = screen.getByPlaceholderText('Enter part name')
      await user.type(nameInput, 'Duplicate Part')

      const submitButton = screen.getByRole('button', { name: /create part/i })
      await user.click(submitButton)

      await waitFor(() => {
        expect(mockToast.error).toHaveBeenCalledWith('Part already exists')
      })
    })

    it('should handle data loading error', async () => {
      mockLocationsService.getAllLocations.mockRejectedValue(new Error('API Error'))

      render(<AddPartModal {...mockProps} />)

      await waitFor(() => {
        expect(mockToast.error).toHaveBeenCalledWith('Failed to load data')
      })
    })
  })

  describe('Modal Close Behavior', () => {
    it('should call onClose when close button is clicked', async () => {
      const user = userEvent.setup()
      render(<AddPartModal {...mockProps} />)

      // Wait for form to load first
      await waitFor(() => {
        expect(screen.getByPlaceholderText('Enter part name')).toBeInTheDocument()
      })

      const closeButton = screen.getByRole('button', { name: /cancel/i })
      await user.click(closeButton)

      expect(mockProps.onClose).toHaveBeenCalled()
    })
  })
})
