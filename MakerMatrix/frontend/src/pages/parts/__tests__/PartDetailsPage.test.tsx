import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { vi, describe, it, expect, beforeEach, afterEach } from 'vitest'
import PartDetailsPage from '../PartDetailsPage'
import { partsService } from '@/services/parts.service'
// Analytics service removed - price trends tests disabled
// import { analyticsService } from '@/services/analytics.service'

// Mock services
vi.mock('@/services/parts.service')
// vi.mock('@/services/analytics.service')
const mockPartsService = partsService as {
  getPart: ReturnType<typeof vi.fn>
  deletePart: ReturnType<typeof vi.fn>
}
// const mockAnalyticsService = analyticsService as any

// Mock react-router-dom navigation
const mockNavigate = vi.fn()
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom')
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  }
})

// Mock Chart.js components
vi.mock('react-chartjs-2', () => ({
  Line: ({ data }: { data: { datasets?: Array<{ label?: string }> } }) => (
    <div data-testid="price-chart">Price Chart: {data.datasets?.[0]?.label}</div>
  ),
}))

// Mock components
vi.mock('@/components/ui/LoadingScreen', () => ({
  default: () => <div data-testid="loading-screen">Loading...</div>,
}))

vi.mock('@/components/parts/PartPDFViewer', () => ({
  default: ({ datasheet }: { datasheet?: { filename?: string } }) => (
    <div data-testid="pdf-viewer">PDF Viewer: {datasheet?.filename}</div>
  ),
}))

vi.mock('@/components/ui/PDFViewer', () => ({
  default: ({ url }: { url?: string }) => <div data-testid="pdf-preview">PDF Preview: {url}</div>,
}))

vi.mock('@/components/parts/PartEnrichmentModal', () => ({
  default: ({
    isOpen,
    onClose,
    onPartUpdated,
    part,
  }: {
    isOpen: boolean
    onClose: () => void
    onPartUpdated?: (part: unknown) => void
    part?: { name?: string; [key: string]: unknown }
  }) =>
    isOpen ? (
      <div data-testid="enrichment-modal">
        <div>Enrichment Modal for: {part?.name}</div>
        <button
          onClick={() => {
            onPartUpdated?.({ ...part, enriched: true })
            onClose()
          }}
        >
          Enrich Part
        </button>
        <button onClick={onClose}>Close</button>
      </div>
    ) : null,
}))

vi.mock('@/components/printer/PrinterModal', () => ({
  default: ({ isOpen, onClose }: { isOpen: boolean; onClose: () => void }) =>
    isOpen ? (
      <div data-testid="printer-modal">
        <div>Printer Modal</div>
        <button onClick={onClose}>Close</button>
      </div>
    ) : null,
}))

vi.mock('@/components/parts/PartImage', () => ({
  default: ({ partName, imageUrl }: { partName?: string; imageUrl?: string }) => (
    <img
      alt={`Part image: ${partName}`}
      src={imageUrl || 'placeholder.jpg'}
      data-testid="part-image"
    />
  ),
}))

vi.mock('@/services/api', () => ({
  getPDFProxyUrl: (url: string) => `proxy/${url}`,
}))

// Mock data
const mockPart = {
  id: '1',
  name: 'Arduino Uno R3',
  part_number: 'ARD-UNO-R3',
  quantity: 10,
  minimum_quantity: 5,
  supplier: 'Arduino',
  location: { id: 'loc1', name: 'Shelf A1' },
  categories: [
    { id: 'cat1', name: 'Microcontrollers' },
    { id: 'cat2', name: 'Development Boards' },
  ],
  image_url: 'http://example.com/arduino.jpg',
  datasheets: [
    {
      id: 'ds1',
      filename: 'arduino_uno_datasheet.pdf',
      url: 'http://example.com/datasheet.pdf',
      file_size: 1024000,
      upload_date: '2024-01-15T10:00:00Z',
    },
  ],
  additional_properties: {
    description: 'Arduino Uno R3 microcontroller board',
    manufacturer: 'Arduino LLC',
    package: 'Board',
    operating_voltage: '5V',
    price: '$25.99',
    datasheet_url: 'http://example.com/datasheet.pdf',
  },
  created_at: '2024-01-01T00:00:00Z',
  updated_at: '2024-01-15T10:00:00Z',
}

const mockPriceTrends = [
  { date: '2024-01-01', price: 24.99 },
  { date: '2024-01-15', price: 25.99 },
  { date: '2024-02-01', price: 25.49 },
]

const TestWrapper = ({
  children,
  initialRoute = '/parts/1',
}: {
  children: React.ReactNode
  initialRoute?: string
}) => <MemoryRouter initialEntries={[initialRoute]}>{children}</MemoryRouter>

describe('PartDetailsPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockPartsService.getPart.mockResolvedValue(mockPart)
    mockPartsService.deletePart.mockResolvedValue({ status: 'success' })
    // Analytics service removed - price trends disabled
    // mockAnalyticsService.getPriceTrends.mockResolvedValue(mockPriceTrends)

    // Mock window.confirm
    global.confirm = vi.fn(() => true)
  })

  afterEach(() => {
    vi.clearAllTimers()
    vi.restoreAllMocks()
  })

  describe('Basic Rendering', () => {
    it('renders loading screen initially', () => {
      render(<PartDetailsPage />, { wrapper: TestWrapper })
      expect(screen.getByTestId('loading-screen')).toBeInTheDocument()
    })

    it('displays part details after loading', async () => {
      render(<PartDetailsPage />, { wrapper: TestWrapper })

      await waitFor(() => {
        expect(screen.getByText('Arduino Uno R3')).toBeInTheDocument()
        expect(screen.getByText('ARD-UNO-R3')).toBeInTheDocument()
        expect(screen.getByText('Arduino Uno R3 microcontroller board')).toBeInTheDocument()
        expect(screen.getByText('Arduino')).toBeInTheDocument()
      })

      expect(mockPartsService.getPart).toHaveBeenCalledWith('1')
      // Analytics service removed - price trends disabled
      // expect(mockAnalyticsService.getPriceTrends).toHaveBeenCalledWith({ part_id: '1', limit: 20 })
    })

    it('displays part image correctly', async () => {
      render(<PartDetailsPage />, { wrapper: TestWrapper })

      await waitFor(() => {
        const image = screen.getByTestId('part-image')
        expect(image).toHaveAttribute('src', 'http://example.com/arduino.jpg')
        expect(image).toHaveAttribute('alt', 'Part image: Arduino Uno R3')
      })
    })

    it('displays part categories as tags', async () => {
      render(<PartDetailsPage />, { wrapper: TestWrapper })

      await waitFor(() => {
        expect(screen.getByText('Microcontrollers')).toBeInTheDocument()
        expect(screen.getByText('Development Boards')).toBeInTheDocument()
      })
    })

    it('displays part location information', async () => {
      render(<PartDetailsPage />, { wrapper: TestWrapper })

      await waitFor(() => {
        expect(screen.getByText('Shelf A1')).toBeInTheDocument()
      })
    })

    it('displays quantity with low stock warning', async () => {
      const lowStockPart = {
        ...mockPart,
        quantity: 3,
        minimum_quantity: 5,
      }
      mockPartsService.getPart.mockResolvedValue(lowStockPart)

      render(<PartDetailsPage />, { wrapper: TestWrapper })

      await waitFor(() => {
        expect(screen.getByText('3')).toBeInTheDocument()
        expect(screen.getByText('Low Stock')).toBeInTheDocument()
      })
    })
  })

  describe('Action Buttons', () => {
    it('renders all action buttons', async () => {
      render(<PartDetailsPage />, { wrapper: TestWrapper })

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /back/i })).toBeInTheDocument()
        expect(screen.getByRole('button', { name: /edit/i })).toBeInTheDocument()
        expect(screen.getByRole('button', { name: /enrich/i })).toBeInTheDocument()
        expect(screen.getByRole('button', { name: /print/i })).toBeInTheDocument()
        expect(screen.getByRole('button', { name: /delete/i })).toBeInTheDocument()
      })
    })

    it('navigates back when back button is clicked', async () => {
      const user = userEvent.setup()
      render(<PartDetailsPage />, { wrapper: TestWrapper })

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /back/i })).toBeInTheDocument()
      })

      const backButton = screen.getByRole('button', { name: /back/i })
      await user.click(backButton)

      expect(mockNavigate).toHaveBeenCalledWith('/parts')
    })

    it('navigates to edit page when edit button is clicked', async () => {
      const user = userEvent.setup()
      render(<PartDetailsPage />, { wrapper: TestWrapper })

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /edit/i })).toBeInTheDocument()
      })

      const editButton = screen.getByRole('button', { name: /edit/i })
      await user.click(editButton)

      expect(mockNavigate).toHaveBeenCalledWith('/parts/1/edit')
    })

    it('opens enrichment modal when enrich button is clicked', async () => {
      const user = userEvent.setup()
      render(<PartDetailsPage />, { wrapper: TestWrapper })

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /enrich/i })).toBeInTheDocument()
      })

      const enrichButton = screen.getByRole('button', { name: /enrich/i })
      await user.click(enrichButton)

      expect(screen.getByTestId('enrichment-modal')).toBeInTheDocument()
      expect(screen.getByText('Enrichment Modal for: Arduino Uno R3')).toBeInTheDocument()
    })

    it('opens printer modal when print button is clicked', async () => {
      const user = userEvent.setup()
      render(<PartDetailsPage />, { wrapper: TestWrapper })

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /print/i })).toBeInTheDocument()
      })

      const printButton = screen.getByRole('button', { name: /print/i })
      await user.click(printButton)

      expect(screen.getByTestId('printer-modal')).toBeInTheDocument()
    })

    it('deletes part when delete button is clicked and confirmed', async () => {
      const user = userEvent.setup()
      render(<PartDetailsPage />, { wrapper: TestWrapper })

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /delete/i })).toBeInTheDocument()
      })

      const deleteButton = screen.getByRole('button', { name: /delete/i })
      await user.click(deleteButton)

      expect(global.confirm).toHaveBeenCalledWith(
        'Are you sure you want to delete "Arduino Uno R3"?'
      )

      await waitFor(() => {
        expect(mockPartsService.deletePart).toHaveBeenCalledWith('1')
        expect(mockNavigate).toHaveBeenCalledWith('/parts')
      })
    })

    it('does not delete part when deletion is cancelled', async () => {
      global.confirm = vi.fn(() => false)
      const user = userEvent.setup()
      render(<PartDetailsPage />, { wrapper: TestWrapper })

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /delete/i })).toBeInTheDocument()
      })

      const deleteButton = screen.getByRole('button', { name: /delete/i })
      await user.click(deleteButton)

      expect(global.confirm).toHaveBeenCalled()
      expect(mockPartsService.deletePart).not.toHaveBeenCalled()
      expect(mockNavigate).not.toHaveBeenCalledWith('/parts')
    })
  })

  describe('Datasheet Management', () => {
    it('displays datasheet information when available', async () => {
      render(<PartDetailsPage />, { wrapper: TestWrapper })

      await waitFor(() => {
        expect(screen.getByText('arduino_uno_datasheet.pdf')).toBeInTheDocument()
        expect(screen.getByText('1.0 MB')).toBeInTheDocument()
      })
    })

    it('opens datasheet viewer when datasheet is clicked', async () => {
      const user = userEvent.setup()
      render(<PartDetailsPage />, { wrapper: TestWrapper })

      await waitFor(() => {
        expect(screen.getByText('arduino_uno_datasheet.pdf')).toBeInTheDocument()
      })

      const datasheetLink = screen.getByText('arduino_uno_datasheet.pdf')
      await user.click(datasheetLink)

      expect(screen.getByTestId('pdf-viewer')).toBeInTheDocument()
      expect(screen.getByText('PDF Viewer: arduino_uno_datasheet.pdf')).toBeInTheDocument()
    })

    it('shows preview button for datasheet URLs', async () => {
      render(<PartDetailsPage />, { wrapper: TestWrapper })

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /preview/i })).toBeInTheDocument()
      })
    })

    it('opens PDF preview when preview button is clicked', async () => {
      const user = userEvent.setup()
      render(<PartDetailsPage />, { wrapper: TestWrapper })

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /preview/i })).toBeInTheDocument()
      })

      const previewButton = screen.getByRole('button', { name: /preview/i })
      await user.click(previewButton)

      expect(screen.getByTestId('pdf-preview')).toBeInTheDocument()
    })
  })

  describe('Price History', () => {
    it('displays price chart when price trends are available', async () => {
      render(<PartDetailsPage />, { wrapper: TestWrapper })

      await waitFor(() => {
        expect(screen.getByTestId('price-chart')).toBeInTheDocument()
      })
    })

    // Analytics service removed - price trends tests disabled
    // it('handles missing price history gracefully', async () => {
    //   mockAnalyticsService.getPriceTrends.mockResolvedValue([])

    //   render(<PartDetailsPage />, { wrapper: TestWrapper })

    //   await waitFor(() => {
    //     expect(screen.getByText('Arduino Uno R3')).toBeInTheDocument()
    //   })

    //   // Should not crash when no price data is available
    //   expect(screen.queryByTestId('price-chart')).toBeInTheDocument()
    // })

    // Analytics service removed - price trends tests disabled
    // it('shows loading state for price history', async () => {
    //   // Delay the price trends response
    //   mockAnalyticsService.getPriceTrends.mockImplementation(
    //     () => new Promise((resolve) => setTimeout(() => resolve(mockPriceTrends), 100))
    //   )

    //   render(<PartDetailsPage />, { wrapper: TestWrapper })

    //   await waitFor(() => {
    //     expect(screen.getByText('Arduino Uno R3')).toBeInTheDocument()
    //   })

    //   // Check that price chart is eventually loaded
    //   await waitFor(
    //     () => {
    //       expect(screen.getByTestId('price-chart')).toBeInTheDocument()
    //     },
    //     { timeout: 200 }
    //   )
    // })
  })

  describe('Part Properties Display', () => {
    it('displays additional properties correctly', async () => {
      render(<PartDetailsPage />, { wrapper: TestWrapper })

      await waitFor(() => {
        expect(screen.getByText('Arduino LLC')).toBeInTheDocument()
        expect(screen.getByText('Board')).toBeInTheDocument()
        expect(screen.getByText('5V')).toBeInTheDocument()
        expect(screen.getByText('$25.99')).toBeInTheDocument()
      })
    })

    it('displays formatted dates correctly', async () => {
      render(<PartDetailsPage />, { wrapper: TestWrapper })

      await waitFor(() => {
        // Check for formatted date display
        expect(screen.getByText(/Jan \d+, 2024/)).toBeInTheDocument()
      })
    })

    it('handles missing optional properties gracefully', async () => {
      const partWithMissingProps = {
        ...mockPart,
        additional_properties: {
          description: 'Basic description',
        },
      }
      mockPartsService.getPart.mockResolvedValue(partWithMissingProps)

      render(<PartDetailsPage />, { wrapper: TestWrapper })

      await waitFor(() => {
        expect(screen.getByText('Arduino Uno R3')).toBeInTheDocument()
      })

      // Should not crash with missing properties
      expect(screen.getByText('Basic description')).toBeInTheDocument()
    })
  })

  describe('Enrichment Workflow', () => {
    it('updates part data after enrichment', async () => {
      const user = userEvent.setup()
      render(<PartDetailsPage />, { wrapper: TestWrapper })

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /enrich/i })).toBeInTheDocument()
      })

      const enrichButton = screen.getByRole('button', { name: /enrich/i })
      await user.click(enrichButton)

      const modalEnrichButton = screen.getByRole('button', { name: 'Enrich Part' })
      await user.click(modalEnrichButton)

      // Should reload part data after enrichment
      await waitFor(() => {
        expect(mockPartsService.getPart).toHaveBeenCalledTimes(2)
      })
    })
  })

  describe('Error Handling', () => {
    it('displays error message when part loading fails', async () => {
      const errorMessage = 'Part not found'
      mockPartsService.getPart.mockRejectedValue({
        response: { data: { error: errorMessage } },
      })

      render(<PartDetailsPage />, { wrapper: TestWrapper })

      await waitFor(() => {
        expect(screen.getByText(errorMessage)).toBeInTheDocument()
      })
    })

    it('handles deletion errors gracefully', async () => {
      const errorMessage = 'Failed to delete part'
      mockPartsService.deletePart.mockRejectedValue({
        response: { data: { error: errorMessage } },
      })

      const user = userEvent.setup()
      render(<PartDetailsPage />, { wrapper: TestWrapper })

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /delete/i })).toBeInTheDocument()
      })

      const deleteButton = screen.getByRole('button', { name: /delete/i })
      await user.click(deleteButton)

      await waitFor(() => {
        expect(screen.getByText(errorMessage)).toBeInTheDocument()
      })
    })

    // Analytics service removed - price trends tests disabled
    // it('handles price history loading errors gracefully', async () => {
    //   mockAnalyticsService.getPriceTrends.mockRejectedValue(
    //     new Error('Failed to load price history')
    //   )

    //   // Mock console.error to verify error handling
    //   const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {})

    //   render(<PartDetailsPage />, { wrapper: TestWrapper })

    //   await waitFor(() => {
    //     expect(screen.getByText('Arduino Uno R3')).toBeInTheDocument()
    //   })

    //   expect(consoleSpy).toHaveBeenCalledWith('Failed to load price history:', expect.any(Error))

    //   consoleSpy.mockRestore()
    // })
  })

  describe('URL Parameters', () => {
    it('loads correct part based on URL parameter', async () => {
      render(<PartDetailsPage />, {
        wrapper: ({ children }) => <TestWrapper initialRoute="/parts/123">{children}</TestWrapper>,
      })

      await waitFor(() => {
        expect(mockPartsService.getPart).toHaveBeenCalledWith('123')
      })
    })

    it('handles invalid part ID gracefully', async () => {
      mockPartsService.getPart.mockRejectedValue({
        response: { data: { error: 'Part not found' } },
      })

      render(<PartDetailsPage />, {
        wrapper: ({ children }) => (
          <TestWrapper initialRoute="/parts/invalid">{children}</TestWrapper>
        ),
      })

      await waitFor(() => {
        expect(screen.getByText('Part not found')).toBeInTheDocument()
      })
    })
  })

  describe('Accessibility', () => {
    it('has proper ARIA labels and roles', async () => {
      render(<PartDetailsPage />, { wrapper: TestWrapper })

      // Wait for component to load data
      await waitFor(() => {
        expect(screen.getByText('Arduino Uno R3')).toBeInTheDocument()
      })

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /back/i })).toBeInTheDocument()
        expect(screen.getByRole('button', { name: /edit/i })).toBeInTheDocument()
        expect(screen.getByRole('button', { name: /delete/i })).toBeInTheDocument()
      })
    })

    it('supports keyboard navigation', async () => {
      render(<PartDetailsPage />, { wrapper: TestWrapper })

      // Wait for component to load data
      await waitFor(() => {
        expect(screen.getByText('Arduino Uno R3')).toBeInTheDocument()
      })

      await waitFor(() => {
        const buttons = screen.getAllByRole('button')
        expect(buttons.length).toBeGreaterThan(0)
        buttons.forEach((button) => {
          expect(button).not.toHaveAttribute('tabindex', '-1')
        })
      })
    })
  })
})
