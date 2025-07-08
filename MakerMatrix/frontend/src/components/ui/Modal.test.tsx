import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '../../__tests__/utils/render'
import { setupUser } from '../../__tests__/utils/test-utils'
import Modal from './Modal'

describe('Modal', () => {
  const defaultProps = {
    isOpen: true,
    onClose: vi.fn(),
    title: 'Test Modal',
    children: <div>Modal content</div>
  }

  it('renders modal when open', () => {
    render(<Modal {...defaultProps} />)
    
    expect(screen.getByText('Test Modal')).toBeInTheDocument()
    expect(screen.getByText('Modal content')).toBeInTheDocument()
  })

  it('does not render modal when closed', () => {
    render(<Modal {...defaultProps} isOpen={false} />)
    
    expect(screen.queryByText('Test Modal')).not.toBeInTheDocument()
  })

  it('calls onClose when close button is clicked', async () => {
    const user = setupUser()
    const onClose = vi.fn()
    
    render(<Modal {...defaultProps} onClose={onClose} />)
    
    const closeButton = screen.getByRole('button')
    await user.click(closeButton)
    
    expect(onClose).toHaveBeenCalledOnce()
  })

  it('disables close button when loading', () => {
    const onClose = vi.fn()
    
    render(<Modal {...defaultProps} onClose={onClose} loading={true} />)
    
    const closeButton = screen.getByRole('button')
    expect(closeButton).toBeDisabled()
  })

  it('renders different sizes correctly', () => {
    const { rerender } = render(<Modal {...defaultProps} size="sm" />)
    
    // Find the modal container with the size class
    let modalContainer = screen.getByText('Test Modal').closest('.max-w-md, .max-w-lg, .max-w-2xl, .max-w-4xl')
    expect(modalContainer).toHaveClass('max-w-md')
    
    rerender(<Modal {...defaultProps} size="lg" />)
    modalContainer = screen.getByText('Test Modal').closest('.max-w-md, .max-w-lg, .max-w-2xl, .max-w-4xl')
    expect(modalContainer).toHaveClass('max-w-2xl')
    
    rerender(<Modal {...defaultProps} size="xl" />)
    modalContainer = screen.getByText('Test Modal').closest('.max-w-md, .max-w-lg, .max-w-2xl, .max-w-4xl')
    expect(modalContainer).toHaveClass('max-w-4xl')
  })

  it('displays the title correctly', () => {
    render(<Modal {...defaultProps} title="Custom Title" />)
    
    expect(screen.getByText('Custom Title')).toBeInTheDocument()
  })

  it('renders children content', () => {
    const customContent = <div data-testid="custom-content">Custom Content</div>
    render(<Modal {...defaultProps}>{customContent}</Modal>)
    
    expect(screen.getByTestId('custom-content')).toBeInTheDocument()
    expect(screen.getByText('Custom Content')).toBeInTheDocument()
  })

  it('hides header when showHeader is false', () => {
    render(<Modal {...defaultProps} showHeader={false} />)
    
    expect(screen.queryByText('Test Modal')).not.toBeInTheDocument()
  })

  it('shows footer when showFooter is true and footer is provided', () => {
    const footer = <div data-testid="footer">Footer content</div>
    render(<Modal {...defaultProps} showFooter={true} footer={footer} />)
    
    expect(screen.getByTestId('footer')).toBeInTheDocument()
    expect(screen.getByText('Footer content')).toBeInTheDocument()
  })

  it('does not show footer when showFooter is false', () => {
    const footer = <div data-testid="footer">Footer content</div>
    render(<Modal {...defaultProps} showFooter={false} footer={footer} />)
    
    expect(screen.queryByTestId('footer')).not.toBeInTheDocument()
  })

  it('applies custom className', () => {
    render(<Modal {...defaultProps} className="custom-class" />)
    
    const modalContainer = screen.getByText('Test Modal').closest('.custom-class')
    expect(modalContainer).toBeInTheDocument()
  })
})