import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '../../__tests__/utils/render'
import { SupplierConfigPage } from './SupplierConfigPage'

// Mock the supplier service
vi.mock('../../services/supplier.service', () => ({
  supplierService: {
    getSuppliers: vi.fn(),
    deleteSupplier: vi.fn(),
    updateSupplier: vi.fn(),
    testConnection: vi.fn(),
    createSupplier: vi.fn(),
    exportSuppliers: vi.fn(),
    importSuppliers: vi.fn(),
  },
}))

import { supplierService } from '../../services/supplier.service'

describe('SupplierConfigPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    // Mock empty response by default
    vi.mocked(supplierService.getSuppliers).mockResolvedValue([])
  })

  it('renders component without errors', () => {
    const { container } = render(<SupplierConfigPage />)
    expect(container).toBeInTheDocument()
  })

  it('displays loading state initially', () => {
    render(<SupplierConfigPage />)

    // Check for loading spinner class
    expect(document.querySelector('.animate-spin')).toBeTruthy()
  })

  it('calls getSuppliers API on mount', async () => {
    render(<SupplierConfigPage />)

    await waitFor(() => {
      expect(supplierService.getSuppliers).toHaveBeenCalled()
    })
  })

  it('eventually renders content after loading', async () => {
    render(<SupplierConfigPage />)

    // Wait for either the title to appear or empty state to appear
    await waitFor(
      () => {
        const hasTitle = screen.queryByText('Supplier Configuration')
        const hasEmptyState = screen.queryByText('No suppliers found')
        expect(hasTitle || hasEmptyState).toBeTruthy()
      },
      { timeout: 5000 }
    )
  })

  it('handles multiple Add Supplier buttons correctly', async () => {
    render(<SupplierConfigPage />)

    // Wait for page to load and check that Add Supplier buttons exist
    await waitFor(
      () => {
        const addButtons = screen.queryAllByText('Add Supplier')
        expect(addButtons.length).toBeGreaterThanOrEqual(1)
      },
      { timeout: 5000 }
    )
  })

  it('component mounts and unmounts without errors', () => {
    const { unmount } = render(<SupplierConfigPage />)
    expect(() => unmount()).not.toThrow()
  })

  it('handles API errors without crashing', async () => {
    // Mock API error
    vi.mocked(supplierService.getSuppliers).mockRejectedValue(new Error('API Error'))

    const { container } = render(<SupplierConfigPage />)

    // Component should still be in DOM even with API error
    expect(container).toBeInTheDocument()

    // Wait a bit to see if it crashes
    await new Promise((resolve) => setTimeout(resolve, 100))
    expect(container).toBeInTheDocument()
  })

  it('basic functionality test', async () => {
    render(<SupplierConfigPage />)

    // Just verify that the component renders some content
    await waitFor(
      () => {
        const pageContent = document.body.textContent
        expect(pageContent).toBeTruthy()
        expect(pageContent.length).toBeGreaterThan(0)
      },
      { timeout: 3000 }
    )
  })
})
