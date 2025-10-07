/**
 * Tests for PDFViewer component with PDF proxy functionality.
 *
 * Tests the integration between PDFViewer and the PDF proxy system.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import PDFViewer from '../PDFViewer'

// Mock react-pdf
vi.mock('react-pdf', () => ({
  Document: vi.fn(({ onLoadSuccess, onLoadError, children, file }) => {
    // Simulate different loading scenarios based on file URL
    setTimeout(() => {
      if (file?.includes('proxy-pdf')) {
        if (file.includes('success.pdf')) {
          onLoadSuccess?.({ numPages: 3 })
        } else if (file.includes('timeout.pdf')) {
          onLoadError?.(new Error('408 Timeout while fetching PDF from external source'))
        } else if (file.includes('forbidden.pdf')) {
          onLoadError?.(new Error('403 Access denied: Domain not allowed'))
        } else if (file.includes('not-found.pdf')) {
          onLoadError?.(new Error('404 PDF not found'))
        } else if (file.includes('proxy-error.pdf')) {
          onLoadError?.(new Error('Failed to load PDF through proxy'))
        } else {
          onLoadError?.(new Error('Network error'))
        }
      } else {
        onLoadSuccess?.({ numPages: 2 })
      }
    }, 100)

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
}))

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

  beforeEach(() => {
    vi.clearAllMocks()
  })

  afterEach(() => {
    vi.clearAllTimers()
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

      expect(screen.getByText('Page 1 of 3')).toBeInTheDocument()
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
    it('should allow download attempt when proxy fails', async () => {
      // Mock document.createElement and related methods
      const mockLink = {
        href: '',
        download: '',
        click: vi.fn(),
        remove: vi.fn(),
      }
      const mockCreateElement = vi.fn(() => mockLink)
      const mockAppendChild = vi.fn()
      const mockRemoveChild = vi.fn()

      Object.defineProperty(document, 'createElement', {
        value: mockCreateElement,
        writable: true,
      })
      Object.defineProperty(document.body, 'appendChild', {
        value: mockAppendChild,
        writable: true,
      })
      Object.defineProperty(document.body, 'removeChild', {
        value: mockRemoveChild,
        writable: true,
      })

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
      fireEvent.click(downloadButton)

      expect(mockCreateElement).toHaveBeenCalledWith('a')
      expect(mockLink.href).toBe('/static/proxy-pdf?url=https%3A//datasheet.lcsc.com/timeout.pdf')
      expect(mockLink.download).toBe('Test Datasheet.pdf')
      expect(mockLink.click).toHaveBeenCalled()
    })

    it('should close modal when close button is clicked', () => {
      render(
        <PDFViewer
          fileUrl="/static/proxy-pdf?url=https%3A//datasheet.lcsc.com/success.pdf"
          fileName="Test Datasheet.pdf"
          onClose={mockOnClose}
        />
      )

      const closeButton = screen.getByTestId('close').parentElement
      fireEvent.click(closeButton!)

      expect(mockOnClose).toHaveBeenCalled()
    })
  })

  describe('Header download button with proxy', () => {
    it('should download proxy URL when header download is clicked', () => {
      // Mock document methods
      const mockLink = {
        href: '',
        download: '',
        click: vi.fn(),
        remove: vi.fn(),
      }
      const mockCreateElement = vi.fn(() => mockLink)
      const mockAppendChild = vi.fn()
      const mockRemoveChild = vi.fn()

      Object.defineProperty(document, 'createElement', {
        value: mockCreateElement,
        writable: true,
      })
      Object.defineProperty(document.body, 'appendChild', {
        value: mockAppendChild,
        writable: true,
      })
      Object.defineProperty(document.body, 'removeChild', {
        value: mockRemoveChild,
        writable: true,
      })

      const proxyUrl = '/static/proxy-pdf?url=https%3A//datasheet.lcsc.com/test.pdf'

      render(<PDFViewer fileUrl={proxyUrl} fileName="Test Datasheet.pdf" onClose={mockOnClose} />)

      const downloadButton = screen.getByTestId('download').parentElement
      fireEvent.click(downloadButton!)

      expect(mockCreateElement).toHaveBeenCalledWith('a')
      expect(mockLink.href).toBe(proxyUrl)
      expect(mockLink.download).toBe('Test Datasheet.pdf')
      expect(mockLink.click).toHaveBeenCalled()
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
