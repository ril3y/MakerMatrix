import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@/__tests__/utils/render'
import userEvent from '@testing-library/user-event'
import TagInput from '../TagInput'
import { tagsService } from '@/services/tags.service'
import type { Tag } from '@/types/tags'

// Mock the tags service
vi.mock('@/services/tags.service', () => ({
  tagsService: {
    searchTags: vi.fn(),
    checkTagExists: vi.fn(),
    createTag: vi.fn(),
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
]

describe('TagInput', () => {
  const mockOnTagsChange = vi.fn()

  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(tagsService.searchTags).mockResolvedValue(mockTags)
  })

  it('renders input with placeholder', () => {
    render(
      <TagInput
        selectedTags={[]}
        onTagsChange={mockOnTagsChange}
        entityType="part"
      />
    )
    expect(screen.getByPlaceholderText(/Add tags/i)).toBeInTheDocument()
  })

  it('displays selected tags as badges', () => {
    render(
      <TagInput
        selectedTags={[mockTags[0]]}
        onTagsChange={mockOnTagsChange}
        entityType="part"
      />
    )
    expect(screen.getByText('#testing')).toBeInTheDocument()
  })

  it('removes tag when remove button is clicked', async () => {
    render(
      <TagInput
        selectedTags={[mockTags[0]]}
        onTagsChange={mockOnTagsChange}
        entityType="part"
      />
    )

    const removeButton = screen.getByTitle('Remove tag')
    await userEvent.click(removeButton)

    expect(mockOnTagsChange).toHaveBeenCalledWith([])
  })

  it('shows suggestions when typing', async () => {
    render(
      <TagInput
        selectedTags={[]}
        onTagsChange={mockOnTagsChange}
        entityType="part"
      />
    )

    const input = screen.getByPlaceholderText(/Add tags/i)
    await userEvent.type(input, 'test')

    await waitFor(() => {
      expect(tagsService.searchTags).toHaveBeenCalledWith('test', 10)
    })
  })

  it('filters out already selected tags from suggestions', async () => {
    vi.mocked(tagsService.searchTags).mockResolvedValue(mockTags)

    render(
      <TagInput
        selectedTags={[mockTags[0]]}
        onTagsChange={mockOnTagsChange}
        entityType="part"
      />
    )

    const input = screen.getByPlaceholderText(/Add tags/i)
    await userEvent.type(input, 'test')

    await waitFor(() => {
      expect(screen.getByText('#todo')).toBeInTheDocument()
      // testing tag should not appear as it's already selected
      expect(screen.queryAllByText('#testing')).toHaveLength(1) // Only the selected one
    })
  })

  it('adds tag when suggestion is clicked', async () => {
    render(
      <TagInput
        selectedTags={[]}
        onTagsChange={mockOnTagsChange}
        entityType="part"
      />
    )

    const input = screen.getByPlaceholderText(/Add tags/i)
    await userEvent.type(input, 'test')

    await waitFor(() => {
      expect(screen.getByText('#testing')).toBeInTheDocument()
    })

    const suggestion = screen.getByText('#testing')
    await userEvent.click(suggestion)

    expect(mockOnTagsChange).toHaveBeenCalledWith([mockTags[0]])
  })

  it('creates new tag when "Create tag" option is clicked', async () => {
    const newTag: Tag = {
      id: 'new-tag',
      name: 'newtag',
      color: '#3B82F6',
      is_system_tag: false,
      created_by: 'user-1',
      created_at: '2025-01-01T00:00:00Z',
      updated_at: '2025-01-01T00:00:00Z',
      parts_count: 0,
      tools_count: 0,
    }

    vi.mocked(tagsService.checkTagExists).mockResolvedValue(false)
    vi.mocked(tagsService.createTag).mockResolvedValue(newTag)
    vi.mocked(tagsService.searchTags).mockResolvedValue([])

    render(
      <TagInput
        selectedTags={[]}
        onTagsChange={mockOnTagsChange}
        entityType="part"
      />
    )

    const input = screen.getByPlaceholderText(/Add tags/i)
    await userEvent.type(input, 'newtag')

    await waitFor(() => {
      expect(screen.getByText(/Create tag/i)).toBeInTheDocument()
    })

    const createButton = screen.getByText(/Create tag/i)
    await userEvent.click(createButton)

    await waitFor(() => {
      expect(tagsService.createTag).toHaveBeenCalledWith({
        name: 'newtag',
        color: '#3B82F6',
      })
      expect(mockOnTagsChange).toHaveBeenCalledWith([newTag])
    })
  })

  it('strips # prefix when creating tag', async () => {
    const newTag: Tag = {
      id: 'new-tag',
      name: 'newtag',
      color: '#3B82F6',
      is_system_tag: false,
      created_by: 'user-1',
      created_at: '2025-01-01T00:00:00Z',
      updated_at: '2025-01-01T00:00:00Z',
      parts_count: 0,
      tools_count: 0,
    }

    vi.mocked(tagsService.checkTagExists).mockResolvedValue(false)
    vi.mocked(tagsService.createTag).mockResolvedValue(newTag)
    vi.mocked(tagsService.searchTags).mockResolvedValue([])

    render(
      <TagInput
        selectedTags={[]}
        onTagsChange={mockOnTagsChange}
        entityType="part"
      />
    )

    const input = screen.getByPlaceholderText(/Add tags/i)
    await userEvent.type(input, '#newtag{Enter}')

    await waitFor(() => {
      expect(tagsService.createTag).toHaveBeenCalledWith({
        name: 'newtag',
        color: '#3B82F6',
      })
    })
  })

  it('clears input after adding tag', async () => {
    render(
      <TagInput
        selectedTags={[]}
        onTagsChange={mockOnTagsChange}
        entityType="part"
      />
    )

    const input = screen.getByPlaceholderText(/Add tags/i) as HTMLInputElement
    await userEvent.type(input, 'test')

    await waitFor(() => {
      expect(screen.getByText('#testing')).toBeInTheDocument()
    })

    const suggestion = screen.getByText('#testing')
    await userEvent.click(suggestion)

    expect(input.value).toBe('')
  })

  it('is disabled when disabled prop is true', () => {
    render(
      <TagInput
        selectedTags={[]}
        onTagsChange={mockOnTagsChange}
        entityType="part"
        disabled
      />
    )

    const input = screen.getByPlaceholderText(/Add tags/i)
    expect(input).toBeDisabled()
  })

  it('shows clear button when input has value', async () => {
    render(
      <TagInput
        selectedTags={[]}
        onTagsChange={mockOnTagsChange}
        entityType="part"
      />
    )

    const input = screen.getByPlaceholderText(/Add tags/i)
    await userEvent.type(input, 'test')

    // Wait for clear button to appear
    await waitFor(() => {
      const buttons = screen.getAllByRole('button')
      expect(buttons.length).toBeGreaterThan(0)
    })
  })

  it('clears input when clear button is clicked', async () => {
    render(
      <TagInput
        selectedTags={[]}
        onTagsChange={mockOnTagsChange}
        entityType="part"
      />
    )

    const input = screen.getByPlaceholderText(/Add tags/i) as HTMLInputElement
    await userEvent.type(input, 'test')

    // Find and click the X button in the input (not the remove buttons on badges)
    const clearButtons = screen.getAllByRole('button')
    // The clear button should be one of these
    for (const button of clearButtons) {
      if (button.className.includes('absolute') && button.className.includes('right-3')) {
        await userEvent.click(button)
        break
      }
    }

    await waitFor(() => {
      expect(input.value).toBe('')
    })
  })

  it('handles keyboard navigation in suggestions', async () => {
    render(
      <TagInput
        selectedTags={[]}
        onTagsChange={mockOnTagsChange}
        entityType="part"
      />
    )

    const input = screen.getByPlaceholderText(/Add tags/i)
    await userEvent.type(input, 'test')

    await waitFor(() => {
      expect(screen.getByText('#testing')).toBeInTheDocument()
    })

    // Press arrow down to highlight first suggestion
    fireEvent.keyDown(input, { key: 'ArrowDown' })

    // Press Enter to select
    fireEvent.keyDown(input, { key: 'Enter' })

    await waitFor(() => {
      expect(mockOnTagsChange).toHaveBeenCalled()
    })
  })

  it('closes suggestions on Escape key', async () => {
    render(
      <TagInput
        selectedTags={[]}
        onTagsChange={mockOnTagsChange}
        entityType="part"
      />
    )

    const input = screen.getByPlaceholderText(/Add tags/i)
    await userEvent.type(input, 'test')

    await waitFor(() => {
      expect(screen.getByText('#testing')).toBeInTheDocument()
    })

    fireEvent.keyDown(input, { key: 'Escape' })

    await waitFor(() => {
      expect(screen.queryByText('#testing')).not.toBeInTheDocument()
    })
  })
})
