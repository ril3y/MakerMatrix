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
      expect(screen.getByLabelText(/Tool Name/i)).toBeInTheDocument()
      expect(screen.getByLabelText(/Tool Number/i)).toBeInTheDocument()
      expect(screen.getByLabelText(/Condition/i)).toBeInTheDocument()
    })
  })

  it('renders edit tool modal with existing data', async () => {
    const mockTool = {
      id: '1',
      name: 'Test Tool',
      tool_number: 'T001',
      description: 'Test description',
      condition: 'good' as const,
      status: 'available' as const,
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
      name: 'New Tool',
      tool_number: 'NT001',
      condition: 'new' as const,
      status: 'available' as const,
      created_at: '2024-01-01',
      updated_at: '2024-01-01',
    }

    vi.mocked(toolsService.createTool).mockResolvedValue(mockCreatedTool)

    render(<ToolModal isOpen={true} onClose={mockOnClose} onSuccess={mockOnSuccess} />)

    await waitFor(() => {
      const nameInput = screen.getByLabelText(/Tool Name/i)
      const toolNumberInput = screen.getByLabelText(/Tool Number/i)
      const conditionSelect = screen.getByLabelText(/Condition/i)

      fireEvent.change(nameInput, { target: { value: 'New Tool' } })
      fireEvent.change(toolNumberInput, { target: { value: 'NT001' } })
      fireEvent.change(conditionSelect, { target: { value: 'new' } })

      const submitButton = screen.getByText('Create Tool')
      fireEvent.click(submitButton)
    })

    await waitFor(() => {
      expect(toolsService.createTool).toHaveBeenCalledWith(
        expect.objectContaining({
          name: 'New Tool',
          tool_number: 'NT001',
          condition: 'new',
        })
      )
      expect(mockOnSuccess).toHaveBeenCalled()
      expect(mockOnClose).toHaveBeenCalled()
    })
  })

  it('updates existing tool', async () => {
    const mockTool = {
      id: '1',
      name: 'Existing Tool',
      tool_number: 'ET001',
      condition: 'good' as const,
      status: 'available' as const,
      created_at: '2024-01-01',
      updated_at: '2024-01-01',
    }

    const mockUpdatedTool = { ...mockTool, name: 'Updated Tool' }

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
          name: 'Updated Tool',
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

  it('validates purchase price is non-negative', async () => {
    render(<ToolModal isOpen={true} onClose={mockOnClose} onSuccess={mockOnSuccess} />)

    await waitFor(() => {
      const nameInput = screen.getByLabelText(/Tool Name/i)
      const priceInput = screen.getByLabelText(/Purchase Price/i)

      fireEvent.change(nameInput, { target: { value: 'Test Tool' } })
      fireEvent.change(priceInput, { target: { value: '-100' } })

      const submitButton = screen.getByText('Create Tool')
      fireEvent.click(submitButton)
    })

    await waitFor(() => {
      expect(screen.getByText('Purchase price cannot be negative')).toBeInTheDocument()
    })

    expect(toolsService.createTool).not.toHaveBeenCalled()
  })
})
