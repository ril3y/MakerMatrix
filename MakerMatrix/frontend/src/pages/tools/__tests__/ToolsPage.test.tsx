import React from 'react'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { vi } from 'vitest'
import { MemoryRouter } from 'react-router-dom'
import ToolsPage from '../ToolsPage'
import { toolsService } from '@/services/tools.service'
import { useAuthStore } from '@/store/authStore'

// Mock services and stores
vi.mock('@/services/tools.service')
vi.mock('@/store/authStore')

vi.mock('@/hooks/usePermissions', () => ({
  usePermissions: () => ({
    isAdmin: () => true,
    hasPermission: () => true,
    hasRole: () => true,
    hasAnyPermission: () => true,
    hasAllPermissions: () => true,
    canCreate: () => true,
    canRead: () => true,
    canUpdate: () => true,
    canDelete: () => true,
  }),
}))

// Mock framer-motion
vi.mock('framer-motion', () => {
  const passthrough =
    (Tag: string) =>
    ({ children, ...props }: React.PropsWithChildren<Record<string, unknown>>) => {
      // Strip framer-motion-specific props that aren't valid DOM attributes
      const {
        initial: _initial,
        animate: _animate,
        exit: _exit,
        transition: _transition,
        whileHover: _whileHover,
        whileTap: _whileTap,
        whileInView: _whileInView,
        layout: _layout,
        layoutId: _layoutId,
        variants: _variants,
        ...rest
      } = props as Record<string, unknown>
      return React.createElement(Tag, rest, children)
    }
  return {
    motion: new Proxy(
      {},
      {
        get: (_target, prop: string) => passthrough(prop),
      }
    ),
    AnimatePresence: ({ children }: React.PropsWithChildren<unknown>) => <>{children}</>,
  }
})

describe('ToolsPage', () => {
  const mockTools = [
    {
      id: '1',
      tool_name: 'Drill',
      tool_number: 'T001',
      description: 'Cordless drill',
      manufacturer: 'DeWalt',
      model_number: 'DCD791D2',
      condition: 'good' as const,
      is_checked_out: false,
      is_checkable: true,
      is_calibrated_tool: false,
      is_consumable: false,
      exclude_from_analytics: false,
      quantity: 1,
      created_at: '2024-01-01',
      updated_at: '2024-01-01',
    },
    {
      id: '2',
      tool_name: 'Saw',
      tool_number: 'T002',
      description: 'Circular saw',
      manufacturer: 'Makita',
      model_number: 'HS7601J',
      condition: 'fair' as const,
      is_checked_out: true,
      checked_out_by: 'john.doe',
      checked_out_at: '2024-01-15',
      is_checkable: true,
      is_calibrated_tool: false,
      is_consumable: false,
      exclude_from_analytics: false,
      quantity: 1,
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
      isLoading: false,
      error: null,
      login: vi.fn(),
      guestLogin: vi.fn(),
      logout: vi.fn(),
      checkAuth: vi.fn(),
      updatePassword: vi.fn(),
      clearError: vi.fn(),
      hasRole: vi.fn(),
      hasPermission: vi.fn(),
    })

    // Mock search tools response
    vi.mocked(toolsService.searchTools).mockResolvedValue({
      items: mockTools,
      total: mockTools.length,
      page: 1,
      page_size: 20,
      total_pages: 1,
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

    const searchInput = await screen.findByPlaceholderText(/Search tools/i)
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

    const statusSelect = await screen.findByDisplayValue('All Status')
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

    const conditionSelect = await screen.findByDisplayValue('All Conditions')
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
      const goodConditions = screen.getAllByText('Good')
      const goodSpan = goodConditions.find((el) => el.tagName === 'SPAN')
      expect(goodSpan).toHaveClass('text-blue-500')

      const fairConditions = screen.getAllByText('Fair')
      const fairSpan = fairConditions.find((el) => el.tagName === 'SPAN')
      expect(fairSpan).toHaveClass('text-yellow-500')
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
      total_pages: 0,
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
