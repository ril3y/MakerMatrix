import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@/__tests__/utils/render'
import userEvent from '@testing-library/user-event'
import TagFilter from '../TagFilter'
import { tagsService } from '@/services/tags.service'
import type { Tag } from '@/types/tags'

// Mock the tags service
vi.mock('@/services/tags.service', () => ({
  tagsService: {
    getAllTags: vi.fn(),
  },
}))

const mockTags: Tag[] = [
  {
    id: 'tag-1',
    name: 'testing',
    color: '#3B82F6',
    is_system_tag: false,
    created_by: 'user-1',
    created_at: '2025-01-01T00:00:00Z',
    updated_at: '2025-01-01T00:00:00Z',
    parts_count: 5,
    tools_count: 3,
  },
  {
    id: 'tag-2',
    name: 'todo',
    color: '#F59E0B',
    is_system_tag: false,
    created_by: 'user-1',
    created_at: '2025-01-01T00:00:00Z',
    updated_at: '2025-01-01T00:00:00Z',
    parts_count: 10,
    tools_count: 2,
  },
  {
    id: 'tag-3',
    name: 'production',
    color: '#10B981',
    is_system_tag: false,
    created_by: 'user-1',
    created_at: '2025-01-01T00:00:00Z',
    updated_at: '2025-01-01T00:00:00Z',
    parts_count: 15,
    tools_count: 8,
  },
]

describe('TagFilter', () => {
  const mockOnFilterChange = vi.fn()

  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(tagsService.getAllTags).mockResolvedValue({
      items: mockTags,
      total: mockTags.length,
      page: 1,
      page_size: 100,
      total_pages: 1,
    })
  })

  it('renders filter button', () => {
    render(
      <TagFilter
        selectedTags={[]}
        onFilterChange={mockOnFilterChange}
        entityType="parts"
      />
    )
    expect(screen.getByText('Tags')).toBeInTheDocument()
  })

  it('shows selected count badge when tags are selected', () => {
    render(
      <TagFilter
        selectedTags={[mockTags[0], mockTags[1]]}
        onFilterChange={mockOnFilterChange}
        entityType="parts"
      />
    )
    expect(screen.getByText('2')).toBeInTheDocument()
  })

  it('opens dropdown when button is clicked', async () => {
    render(
      <TagFilter
        selectedTags={[]}
        onFilterChange={mockOnFilterChange}
        entityType="parts"
      />
    )

    const button = screen.getByText('Tags')
    await userEvent.click(button)

    await waitFor(() => {
      expect(screen.getByText('Filter by Tags')).toBeInTheDocument()
    })
  })

  it('loads tags when dropdown is opened', async () => {
    render(
      <TagFilter
        selectedTags={[]}
        onFilterChange={mockOnFilterChange}
        entityType="parts"
      />
    )

    const button = screen.getByText('Tags')
    await userEvent.click(button)

    await waitFor(() => {
      expect(tagsService.getAllTags).toHaveBeenCalledWith({
        entity_type: 'parts',
        sort_by: 'usage',
        sort_order: 'desc',
        page_size: 100,
      })
    })
  })

  it('displays available tags in dropdown', async () => {
    render(
      <TagFilter
        selectedTags={[]}
        onFilterChange={mockOnFilterChange}
        entityType="parts"
      />
    )

    const button = screen.getByText('Tags')
    await userEvent.click(button)

    await waitFor(() => {
      expect(screen.getByText('#testing')).toBeInTheDocument()
      expect(screen.getByText('#todo')).toBeInTheDocument()
      expect(screen.getByText('#production')).toBeInTheDocument()
    })
  })

  it('shows usage counts for tags', async () => {
    render(
      <TagFilter
        selectedTags={[]}
        onFilterChange={mockOnFilterChange}
        entityType="parts"
      />
    )

    const button = screen.getByText('Tags')
    await userEvent.click(button)

    await waitFor(() => {
      expect(screen.getByText('5')).toBeInTheDocument() // testing tag parts_count
      expect(screen.getByText('10')).toBeInTheDocument() // todo tag parts_count
      expect(screen.getByText('15')).toBeInTheDocument() // production tag parts_count
    })
  })

  it('toggles tag selection when clicked', async () => {
    render(
      <TagFilter
        selectedTags={[]}
        onFilterChange={mockOnFilterChange}
        entityType="parts"
      />
    )

    const button = screen.getByText('Tags')
    await userEvent.click(button)

    await waitFor(() => {
      expect(screen.getByText('#testing')).toBeInTheDocument()
    })

    const tagButton = screen.getByText('#testing').closest('button')
    await userEvent.click(tagButton!)

    expect(mockOnFilterChange).toHaveBeenCalledWith([mockTags[0]], 'OR')
  })

  it('removes tag when already selected', async () => {
    render(
      <TagFilter
        selectedTags={[mockTags[0]]}
        onFilterChange={mockOnFilterChange}
        entityType="parts"
      />
    )

    const button = screen.getByText('Tags')
    await userEvent.click(button)

    await waitFor(() => {
      expect(screen.getAllByText('#testing')).toHaveLength(2) // One in selected, one in available
    })

    const tagButtons = screen.getAllByText('#testing')
    const availableTagButton = tagButtons[1].closest('button')
    await userEvent.click(availableTagButton!)

    expect(mockOnFilterChange).toHaveBeenCalledWith([], 'OR')
  })

  it('filters tags by search query', async () => {
    render(
      <TagFilter
        selectedTags={[]}
        onFilterChange={mockOnFilterChange}
        entityType="parts"
      />
    )

    const button = screen.getByText('Tags')
    await userEvent.click(button)

    await waitFor(() => {
      expect(screen.getByText('#testing')).toBeInTheDocument()
    })

    const searchInput = screen.getByPlaceholderText('Search tags...')
    await userEvent.type(searchInput, 'prod')

    expect(screen.getByText('#production')).toBeInTheDocument()
    expect(screen.queryByText('#testing')).not.toBeInTheDocument()
    expect(screen.queryByText('#todo')).not.toBeInTheDocument()
  })

  it('clears all selected tags', async () => {
    render(
      <TagFilter
        selectedTags={[mockTags[0], mockTags[1]]}
        onFilterChange={mockOnFilterChange}
        entityType="parts"
      />
    )

    const button = screen.getByText('Tags')
    await userEvent.click(button)

    await waitFor(() => {
      expect(screen.getByText('Clear all')).toBeInTheDocument()
    })

    const clearButton = screen.getByText('Clear all')
    await userEvent.click(clearButton)

    expect(mockOnFilterChange).toHaveBeenCalledWith([], 'OR')
  })

  it('shows filter mode toggle when multiple tags selected', async () => {
    render(
      <TagFilter
        selectedTags={[mockTags[0], mockTags[1]]}
        onFilterChange={mockOnFilterChange}
        entityType="parts"
      />
    )

    const button = screen.getByText('Tags')
    await userEvent.click(button)

    await waitFor(() => {
      expect(screen.getByText('Any tag (OR)')).toBeInTheDocument()
    })
  })

  it('does not show filter mode toggle when one or no tags selected', async () => {
    render(
      <TagFilter
        selectedTags={[mockTags[0]]}
        onFilterChange={mockOnFilterChange}
        entityType="parts"
      />
    )

    const button = screen.getByText('Tags')
    await userEvent.click(button)

    await waitFor(() => {
      expect(screen.queryByText('Any tag (OR)')).not.toBeInTheDocument()
    })
  })

  it('toggles between AND and OR modes', async () => {
    render(
      <TagFilter
        selectedTags={[mockTags[0], mockTags[1]]}
        onFilterChange={mockOnFilterChange}
        entityType="parts"
      />
    )

    const button = screen.getByText('Tags')
    await userEvent.click(button)

    await waitFor(() => {
      expect(screen.getByText('Any tag (OR)')).toBeInTheDocument()
    })

    const modeButton = screen.getByText('Any tag (OR)')
    await userEvent.click(modeButton)

    expect(mockOnFilterChange).toHaveBeenCalledWith([mockTags[0], mockTags[1]], 'AND')
  })

  it('shows selected tags preview when closed', () => {
    render(
      <TagFilter
        selectedTags={[mockTags[0], mockTags[1]]}
        onFilterChange={mockOnFilterChange}
        entityType="parts"
      />
    )

    expect(screen.getByText('#testing')).toBeInTheDocument()
    expect(screen.getByText('#todo')).toBeInTheDocument()
  })

  it('shows "+X more" when more than 3 tags selected', () => {
    render(
      <TagFilter
        selectedTags={mockTags}
        onFilterChange={mockOnFilterChange}
        entityType="parts"
      />
    )

    // Should show first 3 tags + "+X more" text
    expect(screen.getByText('+0 more')).toBeInTheDocument()
  })

  it('closes dropdown when clicking outside', async () => {
    render(
      <div>
        <TagFilter
          selectedTags={[]}
          onFilterChange={mockOnFilterChange}
          entityType="parts"
        />
        <div data-testid="outside">Outside</div>
      </div>
    )

    const button = screen.getByText('Tags')
    await userEvent.click(button)

    await waitFor(() => {
      expect(screen.getByText('Filter by Tags')).toBeInTheDocument()
    })

    const outside = screen.getByTestId('outside')
    fireEvent.mouseDown(outside)

    await waitFor(() => {
      expect(screen.queryByText('Filter by Tags')).not.toBeInTheDocument()
    })
  })

  it('shows loading state while fetching tags', async () => {
    // Delay the mock response
    vi.mocked(tagsService.getAllTags).mockImplementation(
      () =>
        new Promise((resolve) =>
          setTimeout(
            () =>
              resolve({
                items: mockTags,
                total: mockTags.length,
                page: 1,
                page_size: 100,
                total_pages: 1,
              }),
            100
          )
        )
    )

    render(
      <TagFilter
        selectedTags={[]}
        onFilterChange={mockOnFilterChange}
        entityType="parts"
      />
    )

    const button = screen.getByText('Tags')
    await userEvent.click(button)

    // Should show loading spinner
    await waitFor(() => {
      expect(screen.getByRole('status', { hidden: true })).toBeInTheDocument()
    })
  })

  it('shows "No tags available" when no tags exist', async () => {
    vi.mocked(tagsService.getAllTags).mockResolvedValue({
      items: [],
      total: 0,
      page: 1,
      page_size: 100,
      total_pages: 1,
    })

    render(
      <TagFilter
        selectedTags={[]}
        onFilterChange={mockOnFilterChange}
        entityType="parts"
      />
    )

    const button = screen.getByText('Tags')
    await userEvent.click(button)

    await waitFor(() => {
      expect(screen.getByText('No tags available')).toBeInTheDocument()
    })
  })

  it('uses correct entity_type in API call for tools', async () => {
    render(
      <TagFilter
        selectedTags={[]}
        onFilterChange={mockOnFilterChange}
        entityType="tools"
      />
    )

    const button = screen.getByText('Tags')
    await userEvent.click(button)

    await waitFor(() => {
      expect(tagsService.getAllTags).toHaveBeenCalledWith({
        entity_type: 'tools',
        sort_by: 'usage',
        sort_order: 'desc',
        page_size: 100,
      })
    })
  })
})
