/**
 * Tests for PDFViewer component with PDF proxy functionality.
 *
 * Tests the integration between PDFViewer and the PDF proxy system.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import PDFViewer from '../PDFViewer'

// Mock react-pdf. The mocked Document drives the success/error pathways
// based on the file argument the component passes in (the arrayBuffer's
// originating URL is preserved by setting the file= prop to the request
// URL via the fetch mock below).
vi.mock('react-pdf', () => {
  return {
    Document: vi.fn(({ onLoadSuccess, onLoadError, children, file }) => {
      // We tag the mocked fetched ArrayBuffer with the requested URL by
      // returning a string in fetch's arrayBuffer() — but the component
      // also accepts strings for external URLs. We detect the file
      // content via its toString() representation.
      const fileStr =
        typeof file === 'string'
          ? file
          : file && typeof (file as { url?: string }).url === 'string'
            ? (file as { url: string }).url
            : ''

      setTimeout(() => {
        if (fileStr.includes('proxy-pdf')) {
          if (fileStr.includes('success.pdf')) {
            onLoadSuccess?.({ numPages: 3 })
          } else if (fileStr.includes('timeout.pdf')) {
            onLoadError?.(new Error('408 Timeout while fetching PDF from external source'))
          } else if (fileStr.includes('forbidden.pdf')) {
            onLoadError?.(new Error('403 Access denied: Domain not allowed'))
          } else if (fileStr.includes('not-found.pdf')) {
            onLoadError?.(new Error('404 PDF not found'))
          } else if (fileStr.includes('proxy-error.pdf')) {
            onLoadError?.(new Error('Failed to load PDF through proxy'))
          } else {
            onLoadError?.(new Error('Network error'))
          }
        } else {
          onLoadSuccess?.({ numPages: 2 })
        }
      }, 0)

      return children
    }),
    Page: vi.fn(({ pageNumber }) => (
      <div data-testid={`pdf-page-${pageNumber}`}>Page {pageNumber}</div>
    )),
    pdfjs: {
      version: '3.4.120',
      GlobalWorkerOptions: {
        workerSrc: '',
      },
    },
  }
})

// Mock Lucide icons
vi.mock('lucide-react', () => ({
  ChevronLeft: () => <div data-testid="chevron-left">←</div>,
  ChevronRight: () => <div data-testid="chevron-right">→</div>,
  ZoomIn: () => <div data-testid="zoom-in">+</div>,
  ZoomOut: () => <div data-testid="zoom-out">-</div>,
  Download: () => <div data-testid="download">↓</div>,
  X: () => <div data-testid="close">×</div>,
  FileText: () => <div data-testid="file-text">📄</div>,
  AlertCircle: () => <div data-testid="alert-circle">⚠</div>,
}))

describe('PDFViewer with Proxy Integration', () => {
  const mockOnClose = vi.fn()
  let originalFetch: typeof fetch

  beforeEach(() => {
    vi.clearAllMocks()

    // PDFViewer fetches /static/proxy-pdf via fetch() and feeds an
    // ArrayBuffer to react-pdf. Our react-pdf mock can't see the URL via
    // the ArrayBuffer, so we wrap the buffer in a thin object that carries
    // the URL through.
    originalFetch = global.fetch
    global.fetch = vi.fn(async (input: RequestInfo | URL) => {
      const url = typeof input === 'string' ? input : input.toString()
      // Return a tagged "ArrayBuffer-like" object so the Document mock can
      // dispatch off the original URL.
      const taggedBuffer = { url, byteLength: 8 } as unknown as ArrayBuffer
      return {
        ok: true,
        status: 200,
        statusText: 'OK',
        arrayBuffer: async () => taggedBuffer,
        blob: async () => new Blob(),
      } as unknown as Response
    }) as unknown as typeof fetch
  })

  afterEach(() => {
    global.fetch = originalFetch
    vi.clearAllTimers()
    vi.restoreAllMocks()
  })

  describe('Proxy URL handling', () => {
    it('should display loading state initially', () => {
      render(
        <PDFViewer
          fileUrl="/static/proxy-pdf?url=https%3A//datasheet.lcsc.com/success.pdf"
          fileName="Test Datasheet.pdf"
          onClose={mockOnClose}
        />
      )

      expect(screen.getByText('Loading PDF...')).toBeInTheDocument()
    })

    it('should load PDF successfully through proxy', async () => {
      render(
        <PDFViewer
          fileUrl="/static/proxy-pdf?url=https%3A//datasheet.lcsc.com/success.pdf"
          fileName="Test Datasheet.pdf"
          onClose={mockOnClose}
        />
      )

      await waitFor(() => {
        expect(screen.getByTestId('pdf-page-1')).toBeInTheDocument()
      })
    })

    it('should handle proxy timeout errors', async () => {
      render(
        <PDFViewer
          fileUrl="/static/proxy-pdf?url=https%3A//datasheet.lcsc.com/timeout.pdf"
          fileName="Test Datasheet.pdf"
          onClose={mockOnClose}
        />
      )

      await waitFor(() => {
        expect(
          screen.getByText('Timeout while fetching PDF from external source')
        ).toBeInTheDocument()
      })

      expect(screen.getByText('Try Download Instead')).toBeInTheDocument()
    })

    it('should handle proxy forbidden domain errors', async () => {
      render(
        <PDFViewer
          fileUrl="/static/proxy-pdf?url=https%3A//evil-site.com/forbidden.pdf"
          fileName="Test Datasheet.pdf"
          onClose={mockOnClose}
        />
      )

      await waitFor(() => {
        expect(
          screen.getByText('Access denied: Domain not allowed for PDF viewing')
        ).toBeInTheDocument()
      })
    })

    it('should handle proxy 404 errors', async () => {
      render(
        <PDFViewer
          fileUrl="/static/proxy-pdf?url=https%3A//datasheet.lcsc.com/not-found.pdf"
          fileName="Test Datasheet.pdf"
          onClose={mockOnClose}
        />
      )

      await waitFor(() => {
        expect(screen.getByText('PDF not found at the provided URL')).toBeInTheDocument()
      })
    })

    it('should handle general proxy errors', async () => {
      render(
        <PDFViewer
          fileUrl="/static/proxy-pdf?url=https%3A//datasheet.lcsc.com/proxy-error.pdf"
          fileName="Test Datasheet.pdf"
          onClose={mockOnClose}
        />
      )

      await waitFor(() => {
        expect(
          screen.getByText(
            'Failed to load PDF through proxy - the source may not be a valid PDF file'
          )
        ).toBeInTheDocument()
      })
    })
  })

  describe('Error message specificity', () => {
    it('should detect proxy URLs and provide specific error messages', async () => {
      const proxyUrl = '/static/proxy-pdf?url=https%3A//invalid-source.com/test.pdf'

      render(<PDFViewer fileUrl={proxyUrl} fileName="Test Datasheet.pdf" onClose={mockOnClose} />)

      await waitFor(() => {
        expect(screen.getByText(/Failed to load PDF through proxy/)).toBeInTheDocument()
      })
    })

    it('should provide fallback download option for errors', async () => {
      render(
        <PDFViewer
          fileUrl="/static/proxy-pdf?url=https%3A//datasheet.lcsc.com/timeout.pdf"
          fileName="Test Datasheet.pdf"
          onClose={mockOnClose}
        />
      )

      await waitFor(() => {
        expect(screen.getByText('Try Download Instead')).toBeInTheDocument()
      })

      const downloadButton = screen.getByText('Try Download Instead')
      expect(downloadButton).toBeInTheDocument()
      expect(downloadButton.closest('button')).toHaveClass('bg-blue-600')
    })
  })

  describe('User interactions with proxy errors', () => {
    it('should close modal when close button is clicked', () => {
      render(
        <PDFViewer
          fileUrl="/static/proxy-pdf?url=https%3A//datasheet.lcsc.com/success.pdf"
          fileName="Test Datasheet.pdf"
          onClose={mockOnClose}
        />
      )

      const closeButton = screen.getByTestId('close').parentElement
      expect(closeButton).toBeTruthy()
      fireEvent.click(closeButton as HTMLElement)

      expect(mockOnClose).toHaveBeenCalled()
    })
  })

  describe('Console logging for debugging', () => {
    it('should log proxy URL on error for debugging', async () => {
      const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {})

      const proxyUrl = '/static/proxy-pdf?url=https%3A//datasheet.lcsc.com/error.pdf'

      render(<PDFViewer fileUrl={proxyUrl} fileName="Test Datasheet.pdf" onClose={mockOnClose} />)

      await waitFor(() => {
        expect(screen.getByText(/Failed to load PDF through proxy/)).toBeInTheDocument()
      })

      expect(consoleSpy).toHaveBeenCalledWith('Failed URL:', proxyUrl)

      consoleSpy.mockRestore()
    })
  })
})
