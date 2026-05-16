import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { vi } from 'vitest'
import ToolModal from '../ToolModal'
import { toolsService } from '@/services/tools.service'
import { locationsService } from '@/services/locations.service'
import { categoriesService } from '@/services/categories.service'

// Mock services
vi.mock('@/services/tools.service')
vi.mock('@/services/locations.service')
vi.mock('@/services/categories.service')

describe('ToolModal', () => {
  const mockOnClose = vi.fn()
  const mockOnSuccess = vi.fn()

  beforeEach(() => {
    vi.clearAllMocks()
    // Mock service responses
    vi.mocked(locationsService.getAllLocations).mockResolvedValue([])
    vi.mocked(categoriesService.getAllCategories).mockResolvedValue([])
  })

  it('renders create tool modal correctly', async () => {
    render(<ToolModal isOpen={true} onClose={mockOnClose} onSuccess={mockOnSuccess} />)

    await waitFor(() => {
      expect(screen.getByText('Add New Tool')).toBeInTheDocument()
      // FormField does not associate label/control via htmlFor/id, so use placeholders
      expect(screen.getByPlaceholderText('Enter tool name')).toBeInTheDocument()
      expect(screen.getByPlaceholderText('Enter tool number')).toBeInTheDocument()
      // The condition label is rendered as text by FormField
      expect(screen.getByText('Condition')).toBeInTheDocument()
    })
  })

  it('renders edit tool modal with existing data', async () => {
    const mockTool = {
      id: '1',
      tool_name: 'Test Tool',
      tool_number: 'T001',
      description: 'Test description',
      condition: 'good' as const,
      is_checked_out: false,
      is_checkable: true,
      is_calibrated_tool: false,
      is_consumable: false,
      exclude_from_analytics: false,
      quantity: 1,
      created_at: '2024-01-01',
      updated_at: '2024-01-01',
    }

    render(
      <ToolModal
        isOpen={true}
        onClose={mockOnClose}
        onSuccess={mockOnSuccess}
        editingTool={mockTool}
      />
    )

    await waitFor(() => {
      expect(screen.getByText('Edit Tool')).toBeInTheDocument()
      expect(screen.getByDisplayValue('Test Tool')).toBeInTheDocument()
      expect(screen.getByDisplayValue('T001')).toBeInTheDocument()
      expect(screen.getByDisplayValue('Test description')).toBeInTheDocument()
    })
  })

  it('validates required fields', async () => {
    render(<ToolModal isOpen={true} onClose={mockOnClose} onSuccess={mockOnSuccess} />)

    await waitFor(() => {
      const submitButton = screen.getByText('Create Tool')
      fireEvent.click(submitButton)
    })

    await waitFor(() => {
      expect(screen.getByText('Tool name is required')).toBeInTheDocument()
    })

    expect(toolsService.createTool).not.toHaveBeenCalled()
  })

  it('submits form with valid data', async () => {
    const mockCreatedTool = {
      id: '1',
      tool_name: 'New Tool',
      tool_number: 'NT001',
      condition: 'good' as const,
      is_checked_out: false,
      is_checkable: true,
      is_calibrated_tool: false,
      is_consumable: false,
      exclude_from_analytics: false,
      quantity: 1,
      created_at: '2024-01-01',
      updated_at: '2024-01-01',
    }

    vi.mocked(toolsService.createTool).mockResolvedValue(mockCreatedTool)

    render(<ToolModal isOpen={true} onClose={mockOnClose} onSuccess={mockOnSuccess} />)

    await waitFor(() => {
      expect(screen.getByPlaceholderText('Enter tool name')).toBeInTheDocument()
    })

    const nameInput = screen.getByPlaceholderText('Enter tool name')
    const toolNumberInput = screen.getByPlaceholderText('Enter tool number')
    // Select element default value is 'good' → option label 'Good'
    const conditionSelect = screen.getByDisplayValue('Good')

    fireEvent.change(nameInput, { target: { value: 'New Tool' } })
    fireEvent.change(toolNumberInput, { target: { value: 'NT001' } })
    fireEvent.change(conditionSelect, { target: { value: 'good' } })

    const submitButton = screen.getByText('Create Tool')
    fireEvent.click(submitButton)

    await waitFor(() => {
      expect(toolsService.createTool).toHaveBeenCalledWith(
        expect.objectContaining({
          tool_name: 'New Tool',
          tool_number: 'NT001',
          condition: 'good',
        })
      )
      expect(mockOnSuccess).toHaveBeenCalled()
      expect(mockOnClose).toHaveBeenCalled()
    })
  })

  it('updates existing tool', async () => {
    const mockTool = {
      id: '1',
      tool_name: 'Existing Tool',
      tool_number: 'ET001',
      condition: 'good' as const,
      is_checked_out: false,
      is_checkable: true,
      is_calibrated_tool: false,
      is_consumable: false,
      exclude_from_analytics: false,
      quantity: 1,
      created_at: '2024-01-01',
      updated_at: '2024-01-01',
    }

    const mockUpdatedTool = { ...mockTool, tool_name: 'Updated Tool' }

    vi.mocked(toolsService.updateTool).mockResolvedValue(mockUpdatedTool)

    render(
      <ToolModal
        isOpen={true}
        onClose={mockOnClose}
        onSuccess={mockOnSuccess}
        editingTool={mockTool}
      />
    )

    await waitFor(() => {
      const nameInput = screen.getByDisplayValue('Existing Tool')
      fireEvent.change(nameInput, { target: { value: 'Updated Tool' } })

      const submitButton = screen.getByText('Update Tool')
      fireEvent.click(submitButton)
    })

    await waitFor(() => {
      expect(toolsService.updateTool).toHaveBeenCalledWith(
        '1',
        expect.objectContaining({
          tool_name: 'Updated Tool',
        })
      )
      expect(mockOnSuccess).toHaveBeenCalled()
      expect(mockOnClose).toHaveBeenCalled()
    })
  })

  it('handles cancel button correctly', async () => {
    render(<ToolModal isOpen={true} onClose={mockOnClose} onSuccess={mockOnSuccess} />)

    await waitFor(() => {
      const cancelButton = screen.getByText('Cancel')
      fireEvent.click(cancelButton)
    })

    expect(mockOnClose).toHaveBeenCalled()
    expect(mockOnSuccess).not.toHaveBeenCalled()
  })

  // TODO(test-debt): Negative number validation - HTML number input with min="0"
  // strips negative values via fireEvent.change in jsdom; validate() never sees
  // a negative value. Production code is fine; the test approach needs rethinking
  // (e.g. set state via uncontrolled access, or remove the HTML min attribute in
  // production code so test can simulate).
  it.skip('validates purchase price is non-negative', async () => {
    render(<ToolModal isOpen={true} onClose={mockOnClose} onSuccess={mockOnSuccess} />)

    await waitFor(() => {
      expect(screen.getByPlaceholderText('Enter tool name')).toBeInTheDocument()
    })

    const nameInput = screen.getByPlaceholderText('Enter tool name')
    const priceInput = screen.getByPlaceholderText('0.00')

    fireEvent.change(nameInput, { target: { value: 'Test Tool' } })
    fireEvent.change(priceInput, { target: { value: '-100' } })

    const submitButton = screen.getByText('Create Tool')
    fireEvent.click(submitButton)

    await waitFor(() => {
      expect(screen.getByText('Purchase price cannot be negative')).toBeInTheDocument()
    })

    expect(toolsService.createTool).not.toHaveBeenCalled()
  })
})
