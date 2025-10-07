import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { toast } from 'react-hot-toast'
import AddCategoryModal from '../AddCategoryModal'
import { categoriesService } from '@/services/categories.service'
import type { Category } from '@/types/parts'

// Mock dependencies
vi.mock('react-hot-toast')
vi.mock('@/services/categories.service')
const mockCategoriesService = vi.mocked(categoriesService)
const mockToast = vi.mocked(toast)

describe('AddCategoryModal - Core Functionality', () => {
  const existingCategories = ['Electronics', 'Resistors', 'Arduino Components']

  const mockProps = {
    isOpen: true,
    onClose: vi.fn(),
    onSuccess: vi.fn(),
    existingCategories,
  }

  const mockCreatedCategory: Category = {
    id: 'cat-123',
    name: 'Capacitors',
    description: 'Various capacitor types',
    created_at: '2024-01-01T00:00:00Z',
    updated_at: '2024-01-01T00:00:00Z',
  }

  beforeEach(() => {
    vi.clearAllMocks()

    // Mock successful category creation by default
    mockCategoriesService.createCategory.mockResolvedValue(mockCreatedCategory)
  })

  describe('Basic Rendering', () => {
    it('should render modal with title and form fields', () => {
      render(<AddCategoryModal {...mockProps} />)

      expect(screen.getByText('Add New Category')).toBeInTheDocument()
      expect(screen.getByPlaceholderText('Enter category name')).toBeInTheDocument()
      expect(screen.getByText('Create Category')).toBeInTheDocument()
    })

    it('should show character count', () => {
      render(<AddCategoryModal {...mockProps} />)

      expect(screen.getByText('0/50 characters')).toBeInTheDocument()
    })

    it('should show Quick Select suggestions', () => {
      render(<AddCategoryModal {...mockProps} />)

      expect(screen.getByText('Quick Select')).toBeInTheDocument()
      expect(screen.getByText('Capacitors')).toBeInTheDocument()
      expect(screen.getByText('Connectors')).toBeInTheDocument()
      expect(screen.getByText('Tools')).toBeInTheDocument()
    })

    it('should filter out existing categories from suggestions', () => {
      render(<AddCategoryModal {...mockProps} />)

      // These should be filtered out since they exist
      expect(screen.queryByText('Electronics')).not.toBeInTheDocument()
      expect(screen.queryByText('Resistors')).not.toBeInTheDocument()

      // These should be available
      expect(screen.getByText('Capacitors')).toBeInTheDocument()
      expect(screen.getByText('Tools')).toBeInTheDocument()
    })

    it('should not show Quick Select when all suggestions are taken', () => {
      const allSuggestions = [
        'Electronics',
        'Resistors',
        'Capacitors',
        'Connectors',
        'Tools',
        'Hardware',
        'Sensors',
        'Microcontrollers',
        'Power Supplies',
        'Cables',
        'Mechanical',
        'Fasteners',
        'Arduino',
        'Raspberry Pi',
      ]

      render(<AddCategoryModal {...mockProps} existingCategories={allSuggestions} />)

      expect(screen.queryByText('Quick Select')).not.toBeInTheDocument()
    })
  })

  describe('Form Validation', () => {
    it('should show error when submitting without category name', async () => {
      const user = userEvent.setup()
      render(<AddCategoryModal {...mockProps} />)

      const submitButton = screen.getByText('Create Category')
      await user.click(submitButton)

      expect(screen.getByText('Category name is required')).toBeInTheDocument()
      expect(mockCategoriesService.createCategory).not.toHaveBeenCalled()
    })

    it('should show error for name too short', async () => {
      const user = userEvent.setup()
      render(<AddCategoryModal {...mockProps} />)

      const nameInput = screen.getByPlaceholderText('Enter category name')
      await user.type(nameInput, 'A')

      const submitButton = screen.getByText('Create Category')
      await user.click(submitButton)

      expect(screen.getByText('Category name must be at least 2 characters')).toBeInTheDocument()
    })

    it('should allow maximum length category name (50 characters)', async () => {
      const user = userEvent.setup()
      render(<AddCategoryModal {...mockProps} />)

      const nameInput = screen.getByPlaceholderText('Enter category name')
      // Type exactly 50 characters (the maxLength limit)
      const maxLengthName = 'A'.repeat(50)
      await user.type(nameInput, maxLengthName)

      const submitButton = screen.getByText('Create Category')
      await user.click(submitButton)

      // This should succeed with exactly 50 characters
      await waitFor(() => {
        expect(mockCategoriesService.createCategory).toHaveBeenCalledWith({
          name: maxLengthName,
        })
      })
    })

    it('should show error for duplicate category name', async () => {
      const user = userEvent.setup()
      render(<AddCategoryModal {...mockProps} />)

      const nameInput = screen.getByPlaceholderText('Enter category name')
      await user.type(nameInput, 'Electronics') // Existing category

      const submitButton = screen.getByText('Create Category')
      await user.click(submitButton)

      expect(screen.getByText('A category with this name already exists')).toBeInTheDocument()
    })

    it('should be case insensitive for duplicate check', async () => {
      const user = userEvent.setup()
      render(<AddCategoryModal {...mockProps} />)

      const nameInput = screen.getByPlaceholderText('Enter category name')
      await user.type(nameInput, 'ELECTRONICS') // Different case

      const submitButton = screen.getByText('Create Category')
      await user.click(submitButton)

      expect(screen.getByText('A category with this name already exists')).toBeInTheDocument()
    })

    it('should show error for invalid characters', async () => {
      const user = userEvent.setup()
      render(<AddCategoryModal {...mockProps} />)

      const nameInput = screen.getByPlaceholderText('Enter category name')
      await user.type(nameInput, 'Invalid@Category!') // Contains invalid chars

      const submitButton = screen.getByText('Create Category')
      await user.click(submitButton)

      expect(screen.getByText('Category name contains invalid characters')).toBeInTheDocument()
    })

    it('should allow valid special characters', async () => {
      const user = userEvent.setup()
      render(<AddCategoryModal {...mockProps} />)

      const nameInput = screen.getByPlaceholderText('Enter category name')
      await user.type(nameInput, 'Power & Control (12V)')

      const submitButton = screen.getByText('Create Category')
      await user.click(submitButton)

      await waitFor(() => {
        expect(mockCategoriesService.createCategory).toHaveBeenCalledWith({
          name: 'Power & Control (12V)',
        })
      })
    })
  })

  describe('Character Count Display', () => {
    it('should update character count as user types', async () => {
      const user = userEvent.setup()
      render(<AddCategoryModal {...mockProps} />)

      const nameInput = screen.getByPlaceholderText('Enter category name')
      await user.type(nameInput, 'Test')

      expect(screen.getByText('4/50 characters')).toBeInTheDocument()
    })

    it('should show orange warning when approaching limit', async () => {
      const user = userEvent.setup()
      render(<AddCategoryModal {...mockProps} />)

      const nameInput = screen.getByPlaceholderText('Enter category name')
      const longName = 'A'.repeat(45) // Over 40 characters
      await user.type(nameInput, longName)

      const characterCount = screen.getByText('45/50 characters')
      expect(characterCount).toHaveClass('text-orange-500')
    })
  })

  describe('Quick Select Functionality', () => {
    it('should set category name when suggestion is clicked', async () => {
      const user = userEvent.setup()
      render(<AddCategoryModal {...mockProps} />)

      const capacitorsButton = screen.getByText('Capacitors')
      await user.click(capacitorsButton)

      const nameInput = screen.getByPlaceholderText('Enter category name')
      expect(nameInput).toHaveValue('Capacitors')
    })

    it('should show preview when suggestion is selected', async () => {
      const user = userEvent.setup()
      render(<AddCategoryModal {...mockProps} />)

      const capacitorsButton = screen.getByRole('button', { name: 'Capacitors' })
      await user.click(capacitorsButton)

      expect(screen.getByText('Preview:')).toBeInTheDocument()
      // Check that both the button and preview contain "Capacitors"
      expect(screen.getAllByText('Capacitors')).toHaveLength(2) // Button + Preview
    })

    it('should allow overriding suggestion with custom text', async () => {
      const user = userEvent.setup()
      render(<AddCategoryModal {...mockProps} />)

      const capacitorsButton = screen.getByText('Capacitors')
      await user.click(capacitorsButton)

      const nameInput = screen.getByPlaceholderText('Enter category name')
      await user.clear(nameInput)
      await user.type(nameInput, 'Custom Category')

      expect(nameInput).toHaveValue('Custom Category')
    })
  })

  describe('Preview Display', () => {
    it('should show preview when text is entered', async () => {
      const user = userEvent.setup()
      render(<AddCategoryModal {...mockProps} />)

      const nameInput = screen.getByPlaceholderText('Enter category name')
      await user.type(nameInput, 'Test Category')

      expect(screen.getByText('Preview:')).toBeInTheDocument()
      expect(screen.getByText('Test Category')).toBeInTheDocument()
    })

    it('should not show preview for empty input', () => {
      render(<AddCategoryModal {...mockProps} />)

      expect(screen.queryByText('Preview:')).not.toBeInTheDocument()
    })

    it('should trim whitespace in preview', async () => {
      const user = userEvent.setup()
      render(<AddCategoryModal {...mockProps} />)

      const nameInput = screen.getByPlaceholderText('Enter category name')
      await user.type(nameInput, '  Test Category  ')

      // Preview should show trimmed version
      const previewElements = screen.getAllByText('Test Category')
      expect(previewElements.length).toBeGreaterThan(0)
    })
  })

  describe('Category Creation', () => {
    it('should create category successfully', async () => {
      const user = userEvent.setup()
      render(<AddCategoryModal {...mockProps} />)

      const nameInput = screen.getByPlaceholderText('Enter category name')
      await user.type(nameInput, 'New Category')

      const submitButton = screen.getByText('Create Category')
      await user.click(submitButton)

      await waitFor(() => {
        expect(mockCategoriesService.createCategory).toHaveBeenCalledWith({
          name: 'New Category',
        })
      })

      expect(mockToast.success).toHaveBeenCalledWith('Category created successfully')
      expect(mockProps.onSuccess).toHaveBeenCalled()
      expect(mockProps.onClose).toHaveBeenCalled()
    })

    it('should trim whitespace from category name before creation', async () => {
      const user = userEvent.setup()
      render(<AddCategoryModal {...mockProps} />)

      const nameInput = screen.getByPlaceholderText('Enter category name')
      await user.type(nameInput, '  Whitespace Category  ')

      const submitButton = screen.getByText('Create Category')
      await user.click(submitButton)

      await waitFor(() => {
        expect(mockCategoriesService.createCategory).toHaveBeenCalledWith({
          name: 'Whitespace Category',
        })
      })
    })

    it('should handle creation API error with custom message', async () => {
      const user = userEvent.setup()
      mockCategoriesService.createCategory.mockRejectedValueOnce({
        response: { data: { message: 'Category already exists' } },
      })

      render(<AddCategoryModal {...mockProps} />)

      const nameInput = screen.getByPlaceholderText('Enter category name')
      await user.type(nameInput, 'Test Category')

      const submitButton = screen.getByText('Create Category')
      await user.click(submitButton)

      await waitFor(() => {
        expect(mockToast.error).toHaveBeenCalledWith('Category already exists')
      })

      expect(mockProps.onSuccess).not.toHaveBeenCalled()
    })

    it('should handle generic API error', async () => {
      const user = userEvent.setup()
      mockCategoriesService.createCategory.mockRejectedValueOnce(new Error('Network error'))

      render(<AddCategoryModal {...mockProps} />)

      const nameInput = screen.getByPlaceholderText('Enter category name')
      await user.type(nameInput, 'Test Category')

      const submitButton = screen.getByText('Create Category')
      await user.click(submitButton)

      await waitFor(() => {
        expect(mockToast.error).toHaveBeenCalledWith('Failed to create category')
      })
    })
  })

  describe('Form Reset and Modal Close', () => {
    it('should reset form when modal is closed', async () => {
      const user = userEvent.setup()
      const { unmount } = render(<AddCategoryModal {...mockProps} />)

      // Fill in some data
      const nameInput = screen.getByPlaceholderText('Enter category name')
      await user.type(nameInput, 'Test Category')

      // Close modal
      const cancelButton = screen.getByText('Cancel')
      await user.click(cancelButton)

      expect(mockProps.onClose).toHaveBeenCalled()

      // Clean up the first render
      unmount()

      // Reopen modal and check form is reset
      render(<AddCategoryModal {...mockProps} />)

      const resetNameInput = screen.getByPlaceholderText('Enter category name')
      expect(resetNameInput).toHaveValue('')
    })

    it('should reset form after successful creation', async () => {
      const user = userEvent.setup()
      render(<AddCategoryModal {...mockProps} />)

      const nameInput = screen.getByPlaceholderText('Enter category name')
      await user.type(nameInput, 'Test Category')

      const submitButton = screen.getByText('Create Category')
      await user.click(submitButton)

      await waitFor(() => {
        expect(mockCategoriesService.createCategory).toHaveBeenCalled()
      })

      // Form should be reset after success
      expect(mockProps.onClose).toHaveBeenCalled()
    })

    it('should clear validation errors when form is reset', async () => {
      const user = userEvent.setup()
      render(<AddCategoryModal {...mockProps} />)

      // Trigger validation error
      const submitButton = screen.getByText('Create Category')
      await user.click(submitButton)
      expect(screen.getByText('Category name is required')).toBeInTheDocument()

      // Close and reopen
      const cancelButton = screen.getByText('Cancel')
      await user.click(cancelButton)

      render(<AddCategoryModal {...mockProps} />)

      // Error should be gone
      expect(screen.queryByText('Category name is required')).not.toBeInTheDocument()
    })
  })

  describe('Loading States', () => {
    it('should disable buttons during creation', async () => {
      const user = userEvent.setup()

      // Make createCategory hang to test loading state
      mockCategoriesService.createCategory.mockImplementation(
        () => new Promise((resolve) => setTimeout(resolve, 1000))
      )

      render(<AddCategoryModal {...mockProps} />)

      const nameInput = screen.getByPlaceholderText('Enter category name')
      await user.type(nameInput, 'Test Category')

      const submitButton = screen.getByText('Create Category')
      await user.click(submitButton)

      // Check loading state
      await waitFor(() => {
        expect(screen.getByText('Creating...')).toBeInTheDocument()
        expect(screen.getByText('Creating...')).toBeDisabled()
        expect(screen.getByText('Cancel')).toBeDisabled()
      })
    })

    it('should show loading spinner during creation', async () => {
      const user = userEvent.setup()

      mockCategoriesService.createCategory.mockImplementation(
        () => new Promise((resolve) => setTimeout(resolve, 100))
      )

      render(<AddCategoryModal {...mockProps} />)

      const nameInput = screen.getByPlaceholderText('Enter category name')
      await user.type(nameInput, 'Test Category')

      const submitButton = screen.getByText('Create Category')
      await user.click(submitButton)

      // Check for spinner (animated element)
      await waitFor(() => {
        const spinner = document.querySelector('.animate-spin')
        expect(spinner).toBeInTheDocument()
      })
    })
  })

  describe('Edge Cases', () => {
    it('should handle modal with no existing categories', () => {
      render(<AddCategoryModal {...mockProps} existingCategories={[]} />)

      // All suggestions should be available
      expect(screen.getByText('Electronics')).toBeInTheDocument()
      expect(screen.getByText('Resistors')).toBeInTheDocument()
      expect(screen.getByText('Capacitors')).toBeInTheDocument()
    })

    it('should handle modal when closed', () => {
      render(<AddCategoryModal {...mockProps} isOpen={false} />)

      // Modal content should not be visible
      expect(screen.queryByText('Add New Category')).not.toBeInTheDocument()
    })

    it('should limit suggestions to 8 items', () => {
      render(<AddCategoryModal {...mockProps} existingCategories={[]} />)

      // Count suggestion buttons (excluding the descriptive text)
      const suggestionButtons = screen
        .getAllByRole('button')
        .filter(
          (btn) =>
            btn.textContent &&
            !['Create Category', 'Cancel'].includes(btn.textContent) &&
            btn.className.includes('bg-primary-10')
        )

      expect(suggestionButtons.length).toBeLessThanOrEqual(8)
    })
  })
})
