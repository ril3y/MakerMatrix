import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { vi } from 'vitest'
import { MemoryRouter } from 'react-router-dom'
import ToolsPage from '../ToolsPage'
import { toolsService } from '@/services/tools.service'
import { useAuthStore } from '@/store/authStore'

// Mock services and stores
vi.mock('@/services/tools.service')
vi.mock('@/store/authStore')

// Mock framer-motion
vi.mock('framer-motion', () => ({
  motion: {
    div: ({ children, ...props }: any) => <div {...props}>{children}</div>,
  },
}))

describe('ToolsPage', () => {
  const mockTools = [
    {
      id: '1',
      name: 'Drill',
      tool_number: 'T001',
      description: 'Cordless drill',
      manufacturer: 'DeWalt',
      model: 'DCD791D2',
      condition: 'good' as const,
      status: 'available' as const,
      created_at: '2024-01-01',
      updated_at: '2024-01-01',
    },
    {
      id: '2',
      name: 'Saw',
      tool_number: 'T002',
      description: 'Circular saw',
      manufacturer: 'Makita',
      model: 'HS7601J',
      condition: 'fair' as const,
      status: 'checked_out' as const,
      checked_out_by: 'john.doe',
      checkout_date: '2024-01-15',
      created_at: '2024-01-01',
      updated_at: '2024-01-01',
    },
  ]

  beforeEach(() => {
    vi.clearAllMocks()
    // Mock auth store
    vi.mocked(useAuthStore).mockReturnValue({
      user: { id: '1', username: 'testuser', roles: [] },
      isAuthenticated: true,
    } as any)

    // Mock search tools response
    vi.mocked(toolsService.searchTools).mockResolvedValue({
      items: mockTools,
      total: mockTools.length,
      page: 1,
      page_size: 20,
    })

    vi.mocked(toolsService.getToolSuggestions).mockResolvedValue([])
  })

  it('renders tools page with header', async () => {
    render(
      <MemoryRouter>
        <ToolsPage />
      </MemoryRouter>
    )

    await waitFor(() => {
      expect(screen.getByText('Tools Inventory')).toBeInTheDocument()
      expect(screen.getByText('Manage your tools and equipment')).toBeInTheDocument()
    })
  })

  it('displays tools list correctly', async () => {
    render(
      <MemoryRouter>
        <ToolsPage />
      </MemoryRouter>
    )

    await waitFor(() => {
      expect(screen.getByText('Drill')).toBeInTheDocument()
      expect(screen.getByText('T001')).toBeInTheDocument()
      expect(screen.getByText('DeWalt')).toBeInTheDocument()

      expect(screen.getByText('Saw')).toBeInTheDocument()
      expect(screen.getByText('T002')).toBeInTheDocument()
      expect(screen.getByText('Makita')).toBeInTheDocument()
      expect(screen.getByText('john.doe')).toBeInTheDocument()
    })
  })

  it('opens add tool modal when Add Tool button is clicked', async () => {
    render(
      <MemoryRouter>
        <ToolsPage />
      </MemoryRouter>
    )

    await waitFor(() => {
      const addButton = screen.getByText('Add Tool')
      fireEvent.click(addButton)
    })

    await waitFor(() => {
      expect(screen.getByText('Add New Tool')).toBeInTheDocument()
    })
  })

  it('searches tools when search input changes', async () => {
    render(
      <MemoryRouter>
        <ToolsPage />
      </MemoryRouter>
    )

    const searchInput = screen.getByPlaceholderText(/Search tools/i)
    fireEvent.change(searchInput, { target: { value: 'Drill' } })

    await waitFor(
      () => {
        expect(toolsService.searchTools).toHaveBeenCalledWith(
          expect.objectContaining({
            search_term: 'Drill',
          })
        )
      },
      { timeout: 1000 }
    )
  })

  it('filters tools by status', async () => {
    render(
      <MemoryRouter>
        <ToolsPage />
      </MemoryRouter>
    )

    const statusSelect = screen.getByDisplayValue('All Status')
    fireEvent.change(statusSelect, { target: { value: 'available' } })

    await waitFor(() => {
      expect(toolsService.searchTools).toHaveBeenCalledWith(
        expect.objectContaining({
          status: 'available',
        })
      )
    })
  })

  it('filters tools by condition', async () => {
    render(
      <MemoryRouter>
        <ToolsPage />
      </MemoryRouter>
    )

    const conditionSelect = screen.getByDisplayValue('All Conditions')
    fireEvent.change(conditionSelect, { target: { value: 'good' } })

    await waitFor(() => {
      expect(toolsService.searchTools).toHaveBeenCalledWith(
        expect.objectContaining({
          condition: 'good',
        })
      )
    })
  })

  it('sorts tools when header is clicked', async () => {
    render(
      <MemoryRouter>
        <ToolsPage />
      </MemoryRouter>
    )

    await waitFor(() => {
      const nameHeader = screen.getByText('Name')
      fireEvent.click(nameHeader)
    })

    await waitFor(() => {
      expect(toolsService.searchTools).toHaveBeenCalledWith(
        expect.objectContaining({
          sort_by: 'name',
          sort_order: 'asc',
        })
      )
    })
  })

  it('displays correct condition colors', async () => {
    render(
      <MemoryRouter>
        <ToolsPage />
      </MemoryRouter>
    )

    await waitFor(() => {
      const goodCondition = screen.getByText('Good')
      expect(goodCondition).toHaveClass('text-blue-500')

      const fairCondition = screen.getByText('Fair')
      expect(fairCondition).toHaveClass('text-yellow-500')
    })
  })

  it('shows checkout information for checked out tools', async () => {
    render(
      <MemoryRouter>
        <ToolsPage />
      </MemoryRouter>
    )

    await waitFor(() => {
      expect(screen.getByText('john.doe')).toBeInTheDocument()
      expect(screen.getByText(/Since/i)).toBeInTheDocument()
    })
  })

  it('deletes tool when delete button is clicked', async () => {
    window.confirm = vi.fn().mockReturnValue(true)
    vi.mocked(toolsService.deleteTool).mockResolvedValue(undefined)

    render(
      <MemoryRouter>
        <ToolsPage />
      </MemoryRouter>
    )

    await waitFor(() => {
      const deleteButtons = screen.getAllByTitle('Delete tool')
      fireEvent.click(deleteButtons[0])
    })

    await waitFor(() => {
      expect(window.confirm).toHaveBeenCalledWith('Are you sure you want to delete this tool?')
      expect(toolsService.deleteTool).toHaveBeenCalledWith('1')
    })
  })

  it('handles empty tools list', async () => {
    vi.mocked(toolsService.searchTools).mockResolvedValue({
      items: [],
      total: 0,
      page: 1,
      page_size: 20,
    })

    render(
      <MemoryRouter>
        <ToolsPage />
      </MemoryRouter>
    )

    await waitFor(() => {
      expect(screen.getByText('No Tools Found')).toBeInTheDocument()
      expect(
        screen.getByText('Start by adding your first tool to the inventory.')
      ).toBeInTheDocument()
    })
  })
})
