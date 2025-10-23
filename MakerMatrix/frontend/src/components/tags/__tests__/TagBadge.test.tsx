import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@/__tests__/utils/render'
import TagBadge from '../TagBadge'
import type { Tag } from '@/types/tags'

const mockTag: Tag = {
  id: 'tag-1',
  name: 'testing',
  color: '#3B82F6',
  icon: '🧪',
  description: 'For testing purposes',
  is_system_tag: false,
  created_by: 'user-1',
  created_at: '2025-01-01T00:00:00Z',
  updated_at: '2025-01-01T00:00:00Z',
  parts_count: 5,
  tools_count: 3,
}

describe('TagBadge', () => {
  it('renders tag name with # prefix', () => {
    render(<TagBadge tag={mockTag} />)
    expect(screen.getByText('#testing')).toBeInTheDocument()
  })

  it('renders tag icon when provided', () => {
    render(<TagBadge tag={mockTag} />)
    expect(screen.getByText('🧪')).toBeInTheDocument()
  })

  it('renders without icon when not provided', () => {
    const tagWithoutIcon = { ...mockTag, icon: undefined }
    render(<TagBadge tag={tagWithoutIcon} />)
    expect(screen.queryByText('🧪')).not.toBeInTheDocument()
  })

  it('applies custom background color from tag', () => {
    const { container } = render(<TagBadge tag={mockTag} />)
    const badge = container.querySelector('span')
    expect(badge).toHaveStyle({ backgroundColor: '#3B82F6' })
  })

  it('shows usage count when showCount is true', () => {
    render(<TagBadge tag={mockTag} showCount />)
    // Total count is 5 parts + 3 tools = 8
    expect(screen.getByText('8')).toBeInTheDocument()
  })

  it('does not show count when showCount is false', () => {
    render(<TagBadge tag={mockTag} showCount={false} />)
    expect(screen.queryByText('8')).not.toBeInTheDocument()
  })

  it('renders remove button when onRemove is provided', () => {
    const onRemove = vi.fn()
    render(<TagBadge tag={mockTag} onRemove={onRemove} />)
    const removeButton = screen.getByTitle('Remove tag')
    expect(removeButton).toBeInTheDocument()
  })

  it('calls onRemove when remove button is clicked', () => {
    const onRemove = vi.fn()
    render(<TagBadge tag={mockTag} onRemove={onRemove} />)
    const removeButton = screen.getByTitle('Remove tag')
    fireEvent.click(removeButton)
    expect(onRemove).toHaveBeenCalledTimes(1)
  })

  it('does not render remove button when onRemove is not provided', () => {
    render(<TagBadge tag={mockTag} />)
    expect(screen.queryByTitle('Remove tag')).not.toBeInTheDocument()
  })

  it('calls onClick when badge is clicked', () => {
    const onClick = vi.fn()
    render(<TagBadge tag={mockTag} onClick={onClick} />)
    const badge = screen.getByText('#testing').closest('span')
    expect(badge).toBeTruthy()
    fireEvent.click(badge as HTMLElement)
    expect(onClick).toHaveBeenCalledTimes(1)
  })

  it('has cursor-pointer class when onClick is provided', () => {
    const onClick = vi.fn()
    const { container } = render(<TagBadge tag={mockTag} onClick={onClick} />)
    const badge = container.querySelector('span')
    expect(badge).toHaveClass('cursor-pointer')
  })

  it('does not have cursor-pointer class when onClick is not provided', () => {
    const { container } = render(<TagBadge tag={mockTag} />)
    const badge = container.querySelector('span')
    expect(badge).not.toHaveClass('cursor-pointer')
  })

  it('applies size classes correctly', () => {
    const { container: smallContainer } = render(<TagBadge tag={mockTag} size="sm" />)
    const { container: mediumContainer } = render(<TagBadge tag={mockTag} size="md" />)
    const { container: largeContainer } = render(<TagBadge tag={mockTag} size="lg" />)

    expect(smallContainer.querySelector('span')).toHaveClass('px-2', 'py-0.5', 'text-xs')
    expect(mediumContainer.querySelector('span')).toHaveClass('px-3', 'py-1', 'text-sm')
    expect(largeContainer.querySelector('span')).toHaveClass('px-4', 'py-2', 'text-base')
  })

  it('applies custom className', () => {
    const { container } = render(<TagBadge tag={mockTag} className="custom-class" />)
    const badge = container.querySelector('span')
    expect(badge).toHaveClass('custom-class')
  })

  it('shows description as title attribute', () => {
    render(<TagBadge tag={mockTag} />)
    const badge = screen.getByText('#testing').closest('span')
    expect(badge).toHaveAttribute('title', 'For testing purposes')
  })

  it('shows tag name as title when description is not provided', () => {
    const tagWithoutDescription = { ...mockTag, description: undefined }
    render(<TagBadge tag={tagWithoutDescription} />)
    const badge = screen.getByText('#testing').closest('span')
    expect(badge).toHaveAttribute('title', 'testing')
  })

  it('stops propagation when remove button is clicked', () => {
    const onClick = vi.fn()
    const onRemove = vi.fn()
    render(<TagBadge tag={mockTag} onClick={onClick} onRemove={onRemove} />)

    const removeButton = screen.getByTitle('Remove tag')
    fireEvent.click(removeButton)

    expect(onRemove).toHaveBeenCalledTimes(1)
    expect(onClick).not.toHaveBeenCalled()
  })
})
