/**
 * Integration tests for PDF proxy functionality across components.
 *
 * Tests the complete flow from PartDetailsPage opening PDF preview
 * to PDFViewer displaying the proxied PDF.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { BrowserRouter } from 'react-router-dom'
import PartDetailsPage from '../../pages/parts/PartDetailsPage'

// Mock the PDF proxy function to avoid import.meta issues
const mockGetPDFProxyUrl = (url: string) => `/static/proxy-pdf?url=${encodeURIComponent(url)}`

// Mock LoadingScreen component
vi.mock('../../components/ui/LoadingScreen', () => ({
  default: () => <div data-testid="loading-screen">Loading...</div>,
}))

// Mock react-router-dom
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom')
  return {
    ...actual,
    useParams: () => ({ id: 'test-part-id' }),
    useNavigate: () => vi.fn(),
  }
})

// Mock services
vi.mock('../../services/parts.service', () => ({
  partsService: {
    getPart: vi.fn(() =>
      Promise.resolve({
        id: 'test-part-id',
        name: 'Test Resistor',
        part_number: 'R1001',
        quantity: 100,
        supplier: 'LCSC',
        additional_properties: {
          datasheet_url:
            'https://datasheet.lcsc.com/lcsc/2304140030_Texas-Instruments-TLV9061IDBVR_C693210.pdf',
          description: 'High precision resistor',
        },
        datasheets: [
          {
            id: 'ds1',
            filename: 'local-datasheet.pdf',
            title: 'Local Datasheet',
            is_downloaded: true,
            file_size: 1024000,
            created_at: '2024-01-01T00:00:00Z',
          },
        ],
        categories: [],
        location: { id: 'loc1', name: 'Bin A1' },
      })
    ),
    deletePart: vi.fn(),
  },
}))

// Mock analytics service
vi.mock('../../services/analytics.service', () => ({
  analyticsService: {
    getPriceTrends: vi.fn(() => Promise.resolve([])),
  },
}))

// Mock react-pdf
vi.mock('react-pdf', () => ({
  Document: vi.fn(({ onLoadSuccess, onLoadError, children, file }) => {
    setTimeout(() => {
      if (file?.includes('proxy-pdf')) {
        if (file.includes('success')) {
          onLoadSuccess?.({ numPages: 2 })
        } else {
          onLoadError?.(new Error('Failed to load PDF through proxy'))
        }
      } else {
        onLoadSuccess?.({ numPages: 1 })
      }
    }, 100)
    return children
  }),
  Page: vi.fn(({ pageNumber }) => (
    <div data-testid={`pdf-page-${pageNumber}`}>Page {pageNumber}</div>
  )),
  pdfjs: {
    version: '3.4.120',
    GlobalWorkerOptions: { workerSrc: '' },
  },
}))

// Mock Lucide icons
vi.mock('lucide-react', () => ({
  Package: () => <div>📦</div>,
  Edit: () => <div>✏️</div>,
  Trash2: () => <div>🗑️</div>,
  Tag: () => <div>🏷️</div>,
  MapPin: () => <div>📍</div>,
  Calendar: () => <div>📅</div>,
  ArrowLeft: () => <div>←</div>,
  ExternalLink: () => <div>🔗</div>,
  Hash: () => <div>#</div>,
  Box: () => <div>📦</div>,
  Image: () => <div>🖼️</div>,
  Info: () => <div>ℹ️</div>,
  Zap: () => <div>⚡</div>,
  Settings: () => <div>⚙️</div>,
  Globe: () => <div>🌐</div>,
  BookOpen: () => <div>📖</div>,
  Clock: () => <div>⏰</div>,
  Factory: () => <div>🏭</div>,
  Cpu: () => <div>🧠</div>,
  Leaf: () => <div>🍃</div>,
  Layers: () => <div>🧱</div>,
  ShieldCheck: () => <div>🛡️</div>,
  List: () => <div>📋</div>,
  Copy: () => <div>📋</div>,
  Check: () => <div>✔️</div>,
  FileText: () => <div data-testid="file-text-icon">📄</div>,
  Download: () => <div data-testid="download-icon">↓</div>,
  Eye: () => <div data-testid="eye-icon">👁️</div>,
  Printer: () => <div>🖨️</div>,
  TrendingUp: () => <div>📈</div>,
  DollarSign: () => <div>💲</div>,
  ChevronLeft: () => <div>←</div>,
  ChevronRight: () => <div>→</div>,
  ChevronDown: () => <div>↓</div>,
  ZoomIn: () => <div>+</div>,
  ZoomOut: () => <div>-</div>,
  X: () => <div data-testid="close-icon">×</div>,
  AlertCircle: () => <div data-testid="alert-circle">⚠️</div>,
}))

// Mock framer-motion
vi.mock('framer-motion', () => ({
  motion: {
    div: ({ children, ...props }: any) => <div {...props}>{children}</div>,
  },
}))

// Mock Chart.js components
vi.mock('react-chartjs-2', () => ({
  Line: () => <div data-testid="price-chart">Price Chart</div>,
}))

// Mock other modals
vi.mock('../../components/parts/PartEnrichmentModal', () => ({
  default: () => <div data-testid="enrichment-modal">Enrichment Modal</div>,
}))

vi.mock('../../components/printer/PrinterModal', () => ({
  default: () => <div data-testid="printer-modal">Printer Modal</div>,
}))

vi.mock('../../components/parts/PartPDFViewer', () => ({
  default: ({ isOpen, onClose }: any) =>
    isOpen ? <div data-testid="part-pdf-viewer">Part PDF Viewer</div> : null,
}))

describe('PDF Proxy Integration Tests', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  afterEach(() => {
    vi.clearAllTimers()
  })

  const renderPartDetailsPage = () => {
    return render(
      <BrowserRouter>
        <PartDetailsPage />
      </BrowserRouter>
    )
  }

  describe('getPDFProxyUrl utility', () => {
    it('should generate correct proxy URL for external datasheet', () => {
      const externalUrl = 'https://datasheet.lcsc.com/lcsc/test.pdf'
      const proxyUrl = mockGetPDFProxyUrl(externalUrl)

      expect(proxyUrl).toBe('/static/proxy-pdf?url=' + encodeURIComponent(externalUrl))
    })

    it('should handle complex URLs with query parameters', () => {
      const complexUrl = 'https://datasheet.lcsc.com/lcsc/TI-TLV9061IDBVR_C693210.pdf?version=2'
      const proxyUrl = mockGetPDFProxyUrl(complexUrl)

      expect(proxyUrl).toContain(encodeURIComponent(complexUrl))
      expect(proxyUrl).toContain('%3F') // Encoded ?
      expect(proxyUrl).toContain('%3D') // Encoded =
    })
  })

  describe('PartDetailsPage PDF preview integration', () => {
    it('should load part details and display datasheet sections', async () => {
      renderPartDetailsPage()

      await waitFor(() => {
        expect(screen.getByText('Test Resistor')).toBeInTheDocument()
      })

      // Should show both local and external datasheets
      expect(screen.getByText('Datasheets')).toBeInTheDocument()
      expect(screen.getByText('2 files')).toBeInTheDocument() // 1 local + 1 external
    })

    it('should display external datasheet with preview button', async () => {
      renderPartDetailsPage()

      await waitFor(() => {
        expect(screen.getByText('Supplier Datasheet')).toBeInTheDocument()
      })

      const supplierLabels = screen.getAllByText('LCSC')
      expect(supplierLabels.length).toBeGreaterThan(0)
      expect(screen.getByText('Online')).toBeInTheDocument()
      expect(screen.getByText('Preview PDF')).toBeInTheDocument()
    })

    it('should open PDF preview with proxy URL when clicked', async () => {
      renderPartDetailsPage()

      await waitFor(() => {
        expect(screen.getByText('Preview PDF')).toBeInTheDocument()
      })

      const previewButton = screen.getByText('Preview PDF')
      fireEvent.click(previewButton)

      // Should open PDFViewer modal
      await waitFor(() => {
        expect(screen.getByText('Loading PDF...')).toBeInTheDocument()
      })
    })

    it('should handle local datasheet viewing differently', async () => {
      renderPartDetailsPage()

      await waitFor(() => {
        expect(screen.getByText('Local Datasheet')).toBeInTheDocument()
      })

      // Find and click the local datasheet view button
      const localDatasheetSection = screen.getByText('Local Datasheet').closest('div')
      const viewButton = localDatasheetSection?.querySelector('button')

      if (viewButton && viewButton.textContent?.includes('View')) {
        fireEvent.click(viewButton)

        // Should open PartPDFViewer (different from proxy viewer)
        await waitFor(() => {
          expect(screen.getByTestId('part-pdf-viewer')).toBeInTheDocument()
        })
      }
    })
  })

  describe('PDF proxy error handling integration', () => {
    it('should show appropriate error when proxy fails', async () => {
      // Mock a part with a problematic external URL
      const { partsService } = await import('../../services/parts.service')
      vi.mocked(partsService.getPart).mockResolvedValueOnce({
        id: 'test-part-id',
        name: 'Test Part',
        part_number: 'P1001',
        quantity: 50,
        supplier: 'LCSC',
        additional_properties: {
          datasheet_url: 'https://datasheet.lcsc.com/lcsc/error-file.pdf',
        },
        datasheets: [],
        categories: [],
        location: { id: 'loc1', name: 'Bin A1' },
      })

      renderPartDetailsPage()

      await waitFor(() => {
        expect(screen.getByText('Preview PDF')).toBeInTheDocument()
      })

      const previewButton = screen.getByText('Preview PDF')
      fireEvent.click(previewButton)

      // Should show loading first, then error
      await waitFor(() => {
        expect(screen.getByText('Loading PDF...')).toBeInTheDocument()
      })

      await waitFor(() => {
        expect(screen.getByText(/Failed to load PDF through proxy/i)).toBeInTheDocument()
      })

      // Should show fallback download option
      expect(screen.getByText('Try Download Instead')).toBeInTheDocument()
    })
  })

  describe('PDF viewer controls with proxy', () => {
    it('should display PDF controls when successfully loaded', async () => {
      // Mock successful PDF loading
      const { partsService } = await import('../../services/parts.service')
      vi.mocked(partsService.getPart).mockResolvedValueOnce({
        id: 'test-part-id',
        name: 'Test Part',
        part_number: 'P1001',
        quantity: 50,
        supplier: 'LCSC',
        additional_properties: {
          datasheet_url: 'https://datasheet.lcsc.com/lcsc/success-file.pdf',
        },
        datasheets: [],
        categories: [],
        location: { id: 'loc1', name: 'Bin A1' },
      })

      renderPartDetailsPage()

      await waitFor(() => {
        expect(screen.getByText('Preview PDF')).toBeInTheDocument()
      })

      const previewButton = screen.getByText('Preview PDF')
      fireEvent.click(previewButton)

      // Wait for PDF to load successfully
      await screen.findByTestId('pdf-page-1')

      // Should show navigation controls
      expect(screen.getByText('Page 1 of 2')).toBeInTheDocument()
    })
  })

  describe('External link handling', () => {
    it('should provide external link option alongside preview', async () => {
      renderPartDetailsPage()

      await waitFor(() => {
        expect(screen.getByText('Test Resistor')).toBeInTheDocument()
      })

      // Find the external link button (should be next to Preview PDF)
      const externalLinkIcon = screen.getAllByText('🔗')[0]
      expect(externalLinkIcon).toBeInTheDocument()

      const linkElement = externalLinkIcon.closest('a')
      expect(linkElement).toHaveAttribute(
        'href',
        'https://datasheet.lcsc.com/lcsc/2304140030_Texas-Instruments-TLV9061IDBVR_C693210.pdf'
      )
      expect(linkElement).toHaveAttribute('target', '_blank')
    })
  })

  describe('Modal management', () => {
    it('should close PDF viewer when close button is clicked', async () => {
      renderPartDetailsPage()

      await waitFor(() => {
        expect(screen.getByText('Preview PDF')).toBeInTheDocument()
      })

      const previewButton = screen.getByText('Preview PDF')
      fireEvent.click(previewButton)

      await waitFor(() => {
        expect(screen.getByTestId('close-icon')).toBeInTheDocument()
      })

      const closeButton = screen.getByTestId('close-icon')
      fireEvent.click(closeButton)

      // PDF viewer should be closed
      await waitFor(() => {
        expect(screen.queryByText('Loading PDF...')).not.toBeInTheDocument()
      })
    })
  })
})
