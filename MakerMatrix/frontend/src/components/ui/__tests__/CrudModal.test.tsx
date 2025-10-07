import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { vi } from 'vitest'
import CrudModal from '../CrudModal'

describe('CrudModal', () => {
  const mockOnClose = vi.fn()
  const mockOnSubmit = vi.fn()

  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders modal when isOpen is true', () => {
    render(
      <CrudModal isOpen={true} onClose={mockOnClose} title="Test Modal" onSubmit={mockOnSubmit}>
        <div>Modal content</div>
      </CrudModal>
    )

    expect(screen.getByText('Test Modal')).toBeInTheDocument()
    expect(screen.getByText('Modal content')).toBeInTheDocument()
  })

  it('does not render modal when isOpen is false', () => {
    render(
      <CrudModal isOpen={false} onClose={mockOnClose} title="Test Modal" onSubmit={mockOnSubmit}>
        <div>Modal content</div>
      </CrudModal>
    )

    expect(screen.queryByText('Test Modal')).not.toBeInTheDocument()
  })

  it('displays correct submit button text for create mode', () => {
    render(
      <CrudModal
        isOpen={true}
        onClose={mockOnClose}
        title="Create Modal"
        onSubmit={mockOnSubmit}
        mode="create"
      >
        <div>Content</div>
      </CrudModal>
    )

    expect(screen.getByText('Create')).toBeInTheDocument()
  })

  it('displays correct submit button text for edit mode', () => {
    render(
      <CrudModal
        isOpen={true}
        onClose={mockOnClose}
        title="Edit Modal"
        onSubmit={mockOnSubmit}
        mode="edit"
      >
        <div>Content</div>
      </CrudModal>
    )

    expect(screen.getByText('Update')).toBeInTheDocument()
  })

  it('displays custom submit text when provided', () => {
    render(
      <CrudModal
        isOpen={true}
        onClose={mockOnClose}
        title="Custom Modal"
        onSubmit={mockOnSubmit}
        submitText="Custom Submit"
      >
        <div>Content</div>
      </CrudModal>
    )

    expect(screen.getByText('Custom Submit')).toBeInTheDocument()
  })

  it('displays loading state correctly', () => {
    render(
      <CrudModal
        isOpen={true}
        onClose={mockOnClose}
        title="Loading Modal"
        onSubmit={mockOnSubmit}
        loading={true}
        mode="create"
      >
        <div>Content</div>
      </CrudModal>
    )

    expect(screen.getByText('Creating...')).toBeInTheDocument()
    expect(screen.getByText('Cancel')).toBeDisabled()
  })

  it('displays custom loading text when provided', () => {
    render(
      <CrudModal
        isOpen={true}
        onClose={mockOnClose}
        title="Custom Loading Modal"
        onSubmit={mockOnSubmit}
        loading={true}
        loadingText="Processing..."
      >
        <div>Content</div>
      </CrudModal>
    )

    expect(screen.getByText('Processing...')).toBeInTheDocument()
  })

  it('calls onSubmit when form is submitted', async () => {
    render(
      <CrudModal isOpen={true} onClose={mockOnClose} title="Submit Modal" onSubmit={mockOnSubmit}>
        <input data-testid="test-input" />
      </CrudModal>
    )

    const form = screen.getByTestId('crud-modal-form')
    fireEvent.submit(form)

    await waitFor(() => {
      expect(mockOnSubmit).toHaveBeenCalled()
    })
  })

  it('calls onClose when cancel button is clicked', () => {
    render(
      <CrudModal isOpen={true} onClose={mockOnClose} title="Cancel Modal" onSubmit={mockOnSubmit}>
        <div>Content</div>
      </CrudModal>
    )

    const cancelButton = screen.getByText('Cancel')
    fireEvent.click(cancelButton)

    expect(mockOnClose).toHaveBeenCalled()
  })

  it('prevents closing when loading', () => {
    render(
      <CrudModal
        isOpen={true}
        onClose={mockOnClose}
        title="Loading Modal"
        onSubmit={mockOnSubmit}
        loading={true}
      >
        <div>Content</div>
      </CrudModal>
    )

    const cancelButton = screen.getByText('Cancel')
    fireEvent.click(cancelButton)

    expect(mockOnClose).not.toHaveBeenCalled()
  })

  it('disables submit button when disabled prop is true', () => {
    render(
      <CrudModal
        isOpen={true}
        onClose={mockOnClose}
        title="Disabled Modal"
        onSubmit={mockOnSubmit}
        disabled={true}
      >
        <div>Content</div>
      </CrudModal>
    )

    const submitButton = screen.getByText('Create')
    expect(submitButton).toBeDisabled()
  })

  it('renders footer content when provided', () => {
    render(
      <CrudModal
        isOpen={true}
        onClose={mockOnClose}
        title="Footer Modal"
        onSubmit={mockOnSubmit}
        footerContent={<div>Custom footer content</div>}
      >
        <div>Content</div>
      </CrudModal>
    )

    expect(screen.getByText('Custom footer content')).toBeInTheDocument()
  })

  it('hides submit button when showSubmitButton is false', () => {
    render(
      <CrudModal
        isOpen={true}
        onClose={mockOnClose}
        title="No Submit Modal"
        onSubmit={mockOnSubmit}
        showSubmitButton={false}
      >
        <div>Content</div>
      </CrudModal>
    )

    expect(screen.queryByText('Create')).not.toBeInTheDocument()
  })

  it('hides cancel button when showCancelButton is false', () => {
    render(
      <CrudModal
        isOpen={true}
        onClose={mockOnClose}
        title="No Cancel Modal"
        onSubmit={mockOnSubmit}
        showCancelButton={false}
      >
        <div>Content</div>
      </CrudModal>
    )

    expect(screen.queryByText('Cancel')).not.toBeInTheDocument()
  })

  it('applies custom className', () => {
    render(
      <CrudModal
        isOpen={true}
        onClose={mockOnClose}
        title="Custom Class Modal"
        onSubmit={mockOnSubmit}
        className="custom-modal-class"
      >
        <div>Content</div>
      </CrudModal>
    )

    const modal = screen.getByText('Custom Class Modal').closest('.custom-modal-class')
    expect(modal).toBeInTheDocument()
  })

  it('renders different sizes correctly', () => {
    const { rerender } = render(
      <CrudModal
        isOpen={true}
        onClose={mockOnClose}
        title="Size Modal"
        onSubmit={mockOnSubmit}
        size="sm"
      >
        <div>Content</div>
      </CrudModal>
    )

    // Test different sizes by rerendering
    rerender(
      <CrudModal
        isOpen={true}
        onClose={mockOnClose}
        title="Size Modal"
        onSubmit={mockOnSubmit}
        size="lg"
      >
        <div>Content</div>
      </CrudModal>
    )

    expect(screen.getByText('Size Modal')).toBeInTheDocument()
  })
})
