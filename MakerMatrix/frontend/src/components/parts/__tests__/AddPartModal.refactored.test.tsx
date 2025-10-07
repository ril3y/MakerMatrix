import React from 'react'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { vi, describe, it, expect, beforeEach, afterEach } from 'vitest'
import userEvent from '@testing-library/user-event'
import AddPartModal from '../AddPartModal.refactored'
import { partsService } from '@/services/parts.service'
import { locationsService } from '@/services/locations.service'
import { categoriesService } from '@/services/categories.service'
import { DynamicSupplierService } from '@/services/dynamic-supplier.service'
import toast from 'react-hot-toast'

// Mock services
vi.mock('@/services/parts.service')
vi.mock('@/services/locations.service')
vi.mock('@/services/categories.service')
vi.mock('@/services/dynamic-supplier.service')
vi.mock('react-hot-toast')

// Mock form components
vi.mock('@/components/forms', () => ({
  FormInput: ({ label, registration, error, ...props }: any) => (
    <div>
      <label>{label}</label>
      <input
        {...registration}
        {...props}
        data-testid={`input-${label.toLowerCase().replace(/\s+/g, '-')}`}
      />
      {error && <span role="alert">{error}</span>}
    </div>
  ),
  FormTextarea: ({ label, registration, error, ...props }: any) => (
    <div>
      <label>{label}</label>
      <textarea
        {...registration}
        {...props}
        data-testid={`textarea-${label.toLowerCase().replace(/\s+/g, '-')}`}
      />
      {error && <span role="alert">{error}</span>}
    </div>
  ),
  FormSelect: ({ label, registration, error, children, ...props }: any) => (
    <div>
      <label>{label}</label>
      <select
        {...registration}
        {...props}
        data-testid={`select-${label.toLowerCase().replace(/\s+/g, '-')}`}
      >
        {children}
      </select>
      {error && <span role="alert">{error}</span>}
    </div>
  ),
  FormNumberInput: ({ label, registration, error, ...props }: any) => (
    <div>
      <label>{label}</label>
      <input
        type="number"
        {...registration}
        {...props}
        data-testid={`number-${label.toLowerCase().replace(/\s+/g, '-')}`}
      />
      {error && <span role="alert">{error}</span>}
    </div>
  ),
  FormSection: ({ title, children }: any) => (
    <div data-testid={`section-${title.toLowerCase().replace(/\s+/g, '-')}`}>
      <h3>{title}</h3>
      {children}
    </div>
  ),
  FormGrid: ({ children }: any) => <div>{children}</div>,
  FormActions: ({ onSubmit, onCancel, submitText, loading, disabled }: any) => (
    <div>
      <button
        type="submit"
        onClick={onSubmit}
        disabled={disabled || loading}
        data-testid="submit-button"
      >
        {loading ? 'Loading...' : submitText}
      </button>
      <button type="button" onClick={onCancel} data-testid="cancel-button">
        Cancel
      </button>
    </div>
  ),
  ImageUpload: ({ onImageUpload }: any) => (
    <button onClick={() => onImageUpload('mock-image-url')} data-testid="image-upload">
      Upload Image
    </button>
  ),
  CategorySelector: ({ onCategoryChange }: any) => (
    <button onClick={() => onCategoryChange(['category1'])} data-testid="category-selector">
      Select Categories
    </button>
  ),
  LocationTreeSelector: ({ onLocationSelect }: any) => (
    <button onClick={() => onLocationSelect('location1')} data-testid="location-selector">
      Select Location
    </button>
  ),
}))

// Mock UI components
vi.mock('@/components/ui/Modal', () => ({
  default: ({ isOpen, children, title, onClose }: any) =>
    isOpen ? (
      <div data-testid="modal">
        <h2>{title}</h2>
        <button onClick={onClose} data-testid="modal-close">
          Close
        </button>
        {children}
      </div>
    ) : null,
}))

vi.mock('@/components/categories/AddCategoryModal', () => ({
  default: ({ isOpen, onClose, onSuccess }: any) =>
    isOpen ? (
      <div data-testid="add-category-modal">
        <button
          onClick={() => {
            onSuccess()
            onClose()
          }}
          data-testid="save-category"
        >
          Save Category
        </button>
      </div>
    ) : null,
}))

vi.mock('@/components/locations/AddLocationModal', () => ({
  default: ({ isOpen, onClose, onSuccess }: any) =>
    isOpen ? (
      <div data-testid="add-location-modal">
        <button
          onClick={() => {
            onSuccess()
            onClose()
          }}
          data-testid="save-location"
        >
          Save Location
        </button>
      </div>
    ) : null,
}))

// Mock the hook
vi.mock('@/hooks/useFormWithValidation', () => ({
  useFormWithValidation: (options: any) => {
    const [formData, setFormData] = React.useState(options.defaultValues)
    const [errors, setErrors] = React.useState({})
    const [loading, setLoading] = React.useState(false)

    return {
      register: (name: string) => ({
        name,
        value: formData[name] || '',
        onChange: (e: any) => setFormData((prev: any) => ({ ...prev, [name]: e.target.value })),
      }),
      getFieldProps: (name: string) => ({
        registration: {
          name,
          value: formData[name] || '',
          onChange: (e: any) => setFormData((prev: any) => ({ ...prev, [name]: e.target.value })),
        },
        error: errors[name],
      }),
      setValue: (name: string, value: any) => {
        setFormData((prev: any) => ({ ...prev, [name]: value }))
      },
      watch: (name?: string) => (name ? formData[name] : formData),
      onSubmit: (e: Event) => {
        e.preventDefault()
        setLoading(true)
        options
          .onSubmit(formData)
          .then(options.onSuccess)
          .finally(() => setLoading(false))
      },
      reset: () => setFormData(options.defaultValues),
      loading,
      isValid: true,
    }
  },
}))

const mockLocations = [
  { id: 'loc1', name: 'Warehouse A', description: 'Main warehouse' },
  { id: 'loc2', name: 'Shelf B1', description: 'First shelf' },
]

const mockCategories = [
  { id: 'cat1', name: 'Resistors', description: 'Electronic resistors' },
  { id: 'cat2', name: 'Capacitors', description: 'Electronic capacitors' },
]

const mockSuppliers = [
  { id: 'sup1', name: 'LCSC', description: 'LCSC Electronics' },
  { id: 'sup2', name: 'DigiKey', description: 'DigiKey Electronics' },
]

describe('AddPartModal (Refactored)', () => {
  const mockProps = {
    isOpen: true,
    onClose: vi.fn(),
    onSuccess: vi.fn(),
  }

  beforeEach(() => {
    vi.clearAllMocks()

    // Setup service mocks with proper method names
    Object.assign(locationsService, {
      getAllLocations: vi.fn().mockResolvedValue(mockLocations),
    })

    Object.assign(categoriesService, {
      getAllCategories: vi.fn().mockResolvedValue(mockCategories),
    })

    vi.mocked(DynamicSupplierService.getInstance).mockReturnValue({
      getConfiguredSuppliers: vi.fn().mockResolvedValue(mockSuppliers),
    } as any)

    Object.assign(partsService, {
      createPart: vi.fn().mockResolvedValue({ id: 'new-part-id' }),
    })

    vi.mocked(toast.success).mockImplementation(() => '' as any)
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('renders modal when open', () => {
    render(<AddPartModal {...mockProps} />)

    expect(screen.getByTestId('modal')).toBeInTheDocument()
    expect(screen.getByText('Add New Part')).toBeInTheDocument()
  })

  it('does not render modal when closed', () => {
    render(<AddPartModal {...mockProps} isOpen={false} />)

    expect(screen.queryByTestId('modal')).not.toBeInTheDocument()
  })

  it('displays all form sections', async () => {
    render(<AddPartModal {...mockProps} />)

    await waitFor(() => {
      expect(screen.getByTestId('section-basic-information')).toBeInTheDocument()
      expect(screen.getByTestId('section-supplier-information')).toBeInTheDocument()
      expect(screen.getByTestId('section-organization')).toBeInTheDocument()
    })
  })

  it('displays all required form fields', async () => {
    render(<AddPartModal {...mockProps} />)

    await waitFor(() => {
      expect(screen.getByTestId('input-part-name')).toBeInTheDocument()
      expect(screen.getByTestId('input-part-number')).toBeInTheDocument()
      expect(screen.getByTestId('number-quantity')).toBeInTheDocument()
      expect(screen.getByTestId('textarea-description')).toBeInTheDocument()
      expect(screen.getByTestId('select-supplier')).toBeInTheDocument()
    })
  })

  it('loads data when modal opens', async () => {
    render(<AddPartModal {...mockProps} />)

    await waitFor(() => {
      expect(locationsService.getAllLocations).toHaveBeenCalled()
      expect(categoriesService.getAllCategories).toHaveBeenCalled()
      expect(DynamicSupplierService.getInstance().getConfiguredSuppliers).toHaveBeenCalled()
    })
  })

  it('allows form submission with valid data', async () => {
    const user = userEvent.setup()
    render(<AddPartModal {...mockProps} />)

    await waitFor(() => {
      expect(screen.getByTestId('input-part-name')).toBeInTheDocument()
    })

    // Fill required fields
    await user.type(screen.getByTestId('input-part-name'), 'Test Part')
    await user.type(screen.getByTestId('number-quantity'), '10')

    // Submit form
    await user.click(screen.getByTestId('submit-button'))

    await waitFor(() => {
      expect(partsService.createPart).toHaveBeenCalledWith(
        expect.objectContaining({
          part_name: 'Test Part',
          quantity: '10', // Note: This would be converted to number in real implementation
        })
      )
    })
  })

  it('handles image upload', async () => {
    const user = userEvent.setup()
    render(<AddPartModal {...mockProps} />)

    await waitFor(() => {
      expect(screen.getByTestId('image-upload')).toBeInTheDocument()
    })

    await user.click(screen.getByTestId('image-upload'))

    // The component should handle the image URL
    // This is just testing the interaction, actual image handling would be more complex
  })

  it('handles category selection', async () => {
    const user = userEvent.setup()
    render(<AddPartModal {...mockProps} />)

    await waitFor(() => {
      expect(screen.getByTestId('category-selector')).toBeInTheDocument()
    })

    await user.click(screen.getByTestId('category-selector'))

    // The component should update the form with selected categories
  })

  it('handles location selection', async () => {
    const user = userEvent.setup()
    render(<AddPartModal {...mockProps} />)

    await waitFor(() => {
      expect(screen.getByTestId('location-selector')).toBeInTheDocument()
    })

    await user.click(screen.getByTestId('location-selector'))

    // The component should update the form with selected location
  })

  it('allows adding custom properties', async () => {
    const user = userEvent.setup()
    render(<AddPartModal {...mockProps} />)

    // Look for the add custom property button
    const addPropertyButton = screen.getByText('Add Custom Property')
    await user.click(addPropertyButton)

    // After clicking, there should be input fields for the custom property
    // This is testing the interaction pattern
  })

  it('can open add category modal', async () => {
    const user = userEvent.setup()
    render(<AddPartModal {...mockProps} />)

    // Find and click the plus button next to categories
    const addCategoryButton = screen.getAllByTitle('Add new category')[0]
    await user.click(addCategoryButton)

    expect(screen.getByTestId('add-category-modal')).toBeInTheDocument()
  })

  it('can open add location modal', async () => {
    const user = userEvent.setup()
    render(<AddPartModal {...mockProps} />)

    // Find and click the plus button next to locations
    const addLocationButton = screen.getAllByTitle('Add new location')[0]
    await user.click(addLocationButton)

    expect(screen.getByTestId('add-location-modal')).toBeInTheDocument()
  })

  it('calls onClose when cancel button is clicked', async () => {
    const user = userEvent.setup()
    render(<AddPartModal {...mockProps} />)

    await user.click(screen.getByTestId('cancel-button'))

    expect(mockProps.onClose).toHaveBeenCalled()
  })

  it('calls onSuccess after successful submission', async () => {
    const user = userEvent.setup()
    render(<AddPartModal {...mockProps} />)

    await waitFor(() => {
      expect(screen.getByTestId('input-part-name')).toBeInTheDocument()
    })

    // Fill and submit form
    await user.type(screen.getByTestId('input-part-name'), 'Test Part')
    await user.click(screen.getByTestId('submit-button'))

    await waitFor(() => {
      expect(mockProps.onSuccess).toHaveBeenCalled()
    })
  })

  it('handles service errors gracefully', async () => {
    vi.mocked(locationsService.getAllLocations).mockRejectedValue(new Error('Service error'))

    render(<AddPartModal {...mockProps} />)

    await waitFor(() => {
      expect(toast.error).toHaveBeenCalledWith('Failed to load data')
    })
  })
})
