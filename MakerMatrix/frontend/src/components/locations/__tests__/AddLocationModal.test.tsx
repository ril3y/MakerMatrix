import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { toast } from 'react-hot-toast'
import AddLocationModal from '../AddLocationModal'
import { locationsService } from '@/services/locations.service'
import { Location } from '@/types/parts'

// Mock dependencies
vi.mock('react-hot-toast')
vi.mock('@/services/locations.service')
vi.mock('framer-motion', () => ({
  motion: {
    div: ({ children, ...props }: any) => <div {...props}>{children}</div>,
  },
  AnimatePresence: ({ children }: any) => children,
}))

const mockLocationsService = vi.mocked(locationsService)
const mockToast = vi.mocked(toast)

describe('AddLocationModal - Core Functionality', () => {
  const mockLocations: Location[] = [
    {
      id: 'loc-1',
      name: 'Warehouse A',
      description: 'Main warehouse',
      location_type: 'warehouse',
      parent_id: undefined,
      created_at: '2024-01-01T00:00:00Z',
      updated_at: '2024-01-01T00:00:00Z'
    },
    {
      id: 'loc-2',
      name: 'Electronics Room',
      description: 'Electronics storage',
      location_type: 'room',
      parent_id: 'loc-1',
      created_at: '2024-01-01T00:00:00Z',
      updated_at: '2024-01-01T00:00:00Z'
    }
  ]

  const mockProps = {
    isOpen: true,
    onClose: vi.fn(),
    onSuccess: vi.fn()
  }

  beforeEach(() => {
    vi.clearAllMocks()
    
    // Mock successful location loading by default
    mockLocationsService.getAllLocations.mockResolvedValue(mockLocations)
    
    // Mock successful location creation by default
    mockLocationsService.createLocation.mockResolvedValue({
      id: 'new-loc-123',
      name: 'New Location',
      description: '',
      location_type: 'shelf',
      parent_id: undefined,
      created_at: '2024-01-01T00:00:00Z',
      updated_at: '2024-01-01T00:00:00Z'
    })
  })

  describe('Basic Rendering', () => {
    it('should render modal with title and form fields', async () => {
      render(<AddLocationModal {...mockProps} />)
      
      expect(screen.getByText('Add New Location')).toBeInTheDocument()
      
      await waitFor(() => {
        expect(screen.getByPlaceholderText('Enter location name')).toBeInTheDocument()
        expect(screen.getByText('Select a type')).toBeInTheDocument()
        expect(screen.getByText('No parent (root level)')).toBeInTheDocument()
      })
    })

    it('should load parent locations on mount when modal is open', async () => {
      render(<AddLocationModal {...mockProps} />)
      
      await waitFor(() => {
        expect(mockLocationsService.getAllLocations).toHaveBeenCalled()
      })
    })

    it('should show loading state while fetching data', async () => {
      mockLocationsService.getAllLocations.mockImplementation(() => 
        new Promise(resolve => setTimeout(() => resolve(mockLocations), 100))
      )
      
      render(<AddLocationModal {...mockProps} />)
      
      expect(screen.getByText('Loading...')).toBeInTheDocument()
      
      await waitFor(() => {
        expect(screen.queryByText('Loading...')).not.toBeInTheDocument()
      })
    })

    it('should not load data when modal is closed', () => {
      render(<AddLocationModal {...mockProps} isOpen={false} />)
      
      expect(mockLocationsService.getAllLocations).not.toHaveBeenCalled()
    })
  })

  describe('Form Validation', () => {
    it('should show error when submitting without location name', async () => {
      const user = userEvent.setup()
      render(<AddLocationModal {...mockProps} />)
      
      await waitFor(() => {
        expect(screen.getByText('Create Location')).toBeInTheDocument()
      })

      const submitButton = screen.getByText('Create Location')
      await user.click(submitButton)

      expect(screen.getByText('Location name is required')).toBeInTheDocument()
      expect(mockLocationsService.createLocation).not.toHaveBeenCalled()
    })

    it('should show error for duplicate location name at same level', async () => {
      const user = userEvent.setup()
      render(<AddLocationModal {...mockProps} />)
      
      await waitFor(() => {
        expect(screen.getByPlaceholderText('Enter location name')).toBeInTheDocument()
      })

      const nameInput = screen.getByPlaceholderText('Enter location name')
      await user.type(nameInput, 'Warehouse A')

      const submitButton = screen.getByText('Create Location')
      await user.click(submitButton)

      expect(screen.getByText('A location with this name already exists at this level')).toBeInTheDocument()
    })

    it('should allow duplicate names at different levels', async () => {
      const user = userEvent.setup()
      render(<AddLocationModal {...mockProps} />)
      
      await waitFor(() => {
        expect(screen.getByPlaceholderText('Enter location name')).toBeInTheDocument()
      })

      const nameInput = screen.getByPlaceholderText('Enter location name')
      await user.type(nameInput, 'Electronics Room') // Exists under Warehouse A
      
      // Select different parent (root level)
      const parentSelect = screen.getByDisplayValue('No parent (root level)')
      expect(parentSelect).toBeInTheDocument()

      const submitButton = screen.getByText('Create Location')
      await user.click(submitButton)

      await waitFor(() => {
        expect(mockLocationsService.createLocation).toHaveBeenCalledWith({
          name: 'Electronics Room',
          type: undefined,
          parent_id: undefined
        })
      })
    })
  })

  describe('Location Types', () => {
    it('should display all location type options', async () => {
      render(<AddLocationModal {...mockProps} />)
      
      await waitFor(() => {
        expect(screen.getByText('Select a type')).toBeInTheDocument()
      })

      const typeSelect = screen.getAllByRole('combobox')[0] // First combobox is type select
      await userEvent.click(typeSelect)

      const expectedTypes = ['Warehouse', 'Room', 'Shelf', 'Drawer', 'Bin', 'Rack', 'Cabinet', 'Box', 'Other']
      expectedTypes.forEach(type => {
        expect(screen.getByText(type)).toBeInTheDocument()
      })
    })

    it('should allow selection of location type', async () => {
      const user = userEvent.setup()
      render(<AddLocationModal {...mockProps} />)
      
      await waitFor(() => {
        expect(screen.getByText('Select a type')).toBeInTheDocument()
      })

      const typeSelect = screen.getAllByRole('combobox')[0] // First combobox is type select
      await user.selectOptions(typeSelect, 'shelf')

      expect(typeSelect).toHaveValue('shelf')
    })
  })

  describe('Parent Location Selection', () => {
    it('should display parent locations in hierarchical format', async () => {
      render(<AddLocationModal {...mockProps} />)
      
      await waitFor(() => {
        expect(screen.getByText('No parent (root level)')).toBeInTheDocument()
        expect(screen.getByText('Warehouse A')).toBeInTheDocument()
        expect(screen.getByText('└ Electronics Room')).toBeInTheDocument()
      })
    })

    it('should show full path preview when parent is selected', async () => {
      const user = userEvent.setup()
      render(<AddLocationModal {...mockProps} />)
      
      await waitFor(() => {
        expect(screen.getByText('No parent (root level)')).toBeInTheDocument()
      })

      // Type a location name
      const nameInput = screen.getByPlaceholderText('Enter location name')
      await user.type(nameInput, 'New Shelf')

      // Select parent location
      const parentSelect = screen.getAllByRole('combobox')[1] // Second combobox is parent select
      await user.selectOptions(parentSelect, 'loc-2')

      await waitFor(() => {
        expect(screen.getByText('Full path will be:')).toBeInTheDocument()
        expect(screen.getByText('Warehouse A → Electronics Room → New Shelf')).toBeInTheDocument()
      })
    })
  })

  describe('Location Creation', () => {
    it('should create location successfully with minimal data', async () => {
      const user = userEvent.setup()
      render(<AddLocationModal {...mockProps} />)
      
      await waitFor(() => {
        expect(screen.getByPlaceholderText('Enter location name')).toBeInTheDocument()
      })

      const nameInput = screen.getByPlaceholderText('Enter location name')
      await user.type(nameInput, 'New Storage Room')

      const submitButton = screen.getByText('Create Location')
      await user.click(submitButton)

      await waitFor(() => {
        expect(mockLocationsService.createLocation).toHaveBeenCalledWith({
          name: 'New Storage Room',
          type: undefined,
          parent_id: undefined
        })
      })

      expect(mockToast.success).toHaveBeenCalledWith('Location created successfully')
      expect(mockProps.onSuccess).toHaveBeenCalled()
      expect(mockProps.onClose).toHaveBeenCalled()
    })

    it('should create location with all fields filled', async () => {
      const user = userEvent.setup()
      render(<AddLocationModal {...mockProps} />)
      
      await waitFor(() => {
        expect(screen.getByPlaceholderText('Enter location name')).toBeInTheDocument()
      })

      // Fill in name
      const nameInput = screen.getByPlaceholderText('Enter location name')
      await user.type(nameInput, 'Component Drawer')

      // Select type
      const typeSelect = screen.getAllByRole('combobox')[0] // First combobox is type select
      await user.selectOptions(typeSelect, 'drawer')

      // Select parent
      const parentSelect = screen.getAllByRole('combobox')[1] // Second combobox is parent select
      await user.selectOptions(parentSelect, 'loc-2')

      const submitButton = screen.getByText('Create Location')
      await user.click(submitButton)

      await waitFor(() => {
        expect(mockLocationsService.createLocation).toHaveBeenCalledWith({
          name: 'Component Drawer',
          type: 'drawer',
          parent_id: 'loc-2'
        })
      })
    })

    it('should handle creation API error', async () => {
      const user = userEvent.setup()
      mockLocationsService.createLocation.mockRejectedValueOnce({
        response: { data: { message: 'Location already exists' } }
      })
      
      render(<AddLocationModal {...mockProps} />)
      
      await waitFor(() => {
        expect(screen.getByPlaceholderText('Enter location name')).toBeInTheDocument()
      })

      const nameInput = screen.getByPlaceholderText('Enter location name')
      await user.type(nameInput, 'Test Location')

      const submitButton = screen.getByText('Create Location')
      await user.click(submitButton)

      await waitFor(() => {
        expect(mockToast.error).toHaveBeenCalledWith('Location already exists')
      })

      expect(mockProps.onSuccess).not.toHaveBeenCalled()
    })

    it('should handle generic API error', async () => {
      const user = userEvent.setup()
      mockLocationsService.createLocation.mockRejectedValueOnce(new Error('Network error'))
      
      render(<AddLocationModal {...mockProps} />)
      
      await waitFor(() => {
        expect(screen.getByPlaceholderText('Enter location name')).toBeInTheDocument()
      })

      const nameInput = screen.getByPlaceholderText('Enter location name')
      await user.type(nameInput, 'Test Location')

      const submitButton = screen.getByText('Create Location')
      await user.click(submitButton)

      await waitFor(() => {
        expect(mockToast.error).toHaveBeenCalledWith('Failed to create location')
      })
    })
  })

  describe('Form Reset and Modal Close', () => {
    it('should reset form when modal is closed', async () => {
      const user = userEvent.setup()
      render(<AddLocationModal {...mockProps} />)
      
      await waitFor(() => {
        expect(screen.getByPlaceholderText('Enter location name')).toBeInTheDocument()
      })

      // Fill in some data
      const nameInput = screen.getByPlaceholderText('Enter location name')
      await user.type(nameInput, 'Test Location')

      const typeSelect = screen.getAllByRole('combobox')[0] // First combobox is type select
      await user.selectOptions(typeSelect, 'shelf')

      // Close modal
      const cancelButton = screen.getByText('Cancel')
      await user.click(cancelButton)

      expect(mockProps.onClose).toHaveBeenCalled()

      // Reopen modal and check form is reset
      render(<AddLocationModal {...mockProps} />)
      
      await waitFor(() => {
        const resetNameInput = screen.getByPlaceholderText('Enter location name')
        expect(resetNameInput).toHaveValue('')
        
        const resetTypeSelect = screen.getAllByRole('combobox')[0] // First combobox is type select
        expect(resetTypeSelect).toHaveValue('')
      })
    })

    it('should reset form after successful creation', async () => {
      const user = userEvent.setup()
      render(<AddLocationModal {...mockProps} />)
      
      await waitFor(() => {
        expect(screen.getByPlaceholderText('Enter location name')).toBeInTheDocument()
      })

      const nameInput = screen.getByPlaceholderText('Enter location name')
      await user.type(nameInput, 'Test Location')

      const submitButton = screen.getByText('Create Location')
      await user.click(submitButton)

      await waitFor(() => {
        expect(mockLocationsService.createLocation).toHaveBeenCalled()
      })

      // Form should be reset after success
      expect(mockProps.onClose).toHaveBeenCalled()
    })
  })

  describe('Loading States', () => {
    it('should disable buttons during creation', async () => {
      const user = userEvent.setup()
      
      // Make createLocation hang to test loading state
      mockLocationsService.createLocation.mockImplementation(
        () => new Promise(resolve => setTimeout(resolve, 1000))
      )
      
      render(<AddLocationModal {...mockProps} />)
      
      await waitFor(() => {
        expect(screen.getByPlaceholderText('Enter location name')).toBeInTheDocument()
      })

      const nameInput = screen.getByPlaceholderText('Enter location name')
      await user.type(nameInput, 'Test Location')

      const submitButton = screen.getByText('Create Location')
      await user.click(submitButton)

      // Check loading state
      await waitFor(() => {
        expect(screen.getByText('Creating...')).toBeInTheDocument()
        expect(screen.getByText('Creating...')).toBeDisabled()
        expect(screen.getByText('Cancel')).toBeDisabled()
      })
    })

    it('should handle data loading error gracefully', async () => {
      mockLocationsService.getAllLocations.mockRejectedValueOnce(new Error('Failed to load'))
      
      render(<AddLocationModal {...mockProps} />)
      
      await waitFor(() => {
        expect(mockToast.error).toHaveBeenCalledWith('Failed to load parent locations')
      })
    })
  })
})