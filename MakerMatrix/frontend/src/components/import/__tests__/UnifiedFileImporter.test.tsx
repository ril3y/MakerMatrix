import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { toast } from 'react-hot-toast'
import UnifiedFileImporter from '../UnifiedFileImporter'
import { apiClient } from '@/services/api'

// Mock the filename extractor since it's now frontend-only
vi.mock('@/utils/filenameExtractor', () => ({
  extractOrderInfoFromFilename: vi.fn().mockResolvedValue({
    order_number: 'AUTO123',
    order_date: '2024-01-01',
    notes: 'Auto-extracted from filename: test-file.csv'
  })
}))

// Mock dependencies
vi.mock('react-hot-toast')
vi.mock('@/services/api')
vi.mock('framer-motion', () => ({
  motion: {
    div: ({ children, ...props }: any) => <div {...props}>{children}</div>,
  },
}))

const mockApiClient = vi.mocked(apiClient)
const mockToast = vi.mocked(toast)

describe('UnifiedFileImporter - Core Functionality', () => {
  const mockFile = new File(['test,content'], 'test-file.csv', { type: 'text/csv' })
  
  const mockFilePreview = {
    headers: ['Part Number', 'Description', 'Quantity'],
    sample_rows: [
      ['R001', 'Resistor 1k', '10'],
      ['C001', 'Capacitor 100nF', '5']
    ],
    total_rows: 25,
    parser_type: 'lcsc'
  }

  const mockProps = {
    uploadedFile: mockFile,
    filePreview: mockFilePreview,
    parserType: 'lcsc',
    parserName: 'LCSC Electronics',
    description: 'Import parts from LCSC supplier order files',
    onImportComplete: vi.fn()
  }

  beforeEach(() => {
    vi.clearAllMocks()
    
    // Mock successful import by default
    mockApiClient.post.mockImplementation((endpoint) => {
      if (endpoint === '/api/import/file') {
        return Promise.resolve({
          status: 'success',
          data: {
            imported_parts: [
              { id: '1', name: 'Resistor 1k', part_number: 'R001' }
            ],
            failures: [],
            successful_imports: 1
          }
        })
      }
      
      return Promise.resolve({})
    })
  })

  describe('Basic Rendering', () => {
    it('should render component with file information', async () => {
      render(<UnifiedFileImporter {...mockProps} />)
      
      expect(screen.getByText('Import from LCSC Electronics')).toBeInTheDocument()
      expect(screen.getByText('Import parts from LCSC supplier order files')).toBeInTheDocument()
      expect(screen.getByText('test-file.csv')).toBeInTheDocument()
    })

    it('should display file preview information', async () => {
      render(<UnifiedFileImporter {...mockProps} />)
      
      // Check for file type display
      expect(screen.getByText('test-file.csv')).toBeInTheDocument()
      
      // Check for some preview elements exist
      const fileElements = screen.getAllByText(/KB|rows|Unknown/i)
      expect(fileElements.length).toBeGreaterThan(0)
    })

    it('should show import button', async () => {
      render(<UnifiedFileImporter {...mockProps} />)
      
      expect(screen.getByText('Import Parts')).toBeInTheDocument()
    })
  })

  describe('Auto Order Info Extraction (Frontend)', () => {
    it('should extract order info from filename using frontend utility', async () => {
      const { extractOrderInfoFromFilename } = await import('@/utils/filenameExtractor')
      
      render(<UnifiedFileImporter {...mockProps} />)
      
      // Verify the frontend function is called (mocked)
      await waitFor(() => {
        expect(extractOrderInfoFromFilename).toHaveBeenCalledWith('test-file.csv', 'lcsc')
      })
    })

    it('should handle extraction failure gracefully', async () => {
      const { extractOrderInfoFromFilename } = await import('@/utils/filenameExtractor')
      vi.mocked(extractOrderInfoFromFilename).mockRejectedValueOnce(new Error('Extraction failed'))

      // Should not crash
      expect(() => render(<UnifiedFileImporter {...mockProps} />)).not.toThrow()
    })
  })

  describe('File Import Process', () => {
    it('should import file successfully', async () => {
      const user = userEvent.setup()
      render(<UnifiedFileImporter {...mockProps} />)
      
      // Wait for component to stabilize
      await waitFor(() => {
        expect(screen.getByText('Import Parts')).toBeInTheDocument()
      })

      const importButton = screen.getByText('Import Parts')
      await user.click(importButton)

      await waitFor(() => {
        expect(mockApiClient.post).toHaveBeenCalledWith(
          '/api/import/file',
          expect.any(FormData),
          expect.objectContaining({
            headers: {
              'Content-Type': 'multipart/form-data'
            }
          })
        )
      })

      await waitFor(() => {
        expect(mockToast.success).toHaveBeenCalledWith(
          'Import completed: 1 parts imported successfully'
        )
      })

      expect(mockProps.onImportComplete).toHaveBeenCalledWith({
        success_parts: [{ id: '1', name: 'Resistor 1k', part_number: 'R001' }],
        failed_parts: []
      })
    })

    it('should handle import API error', async () => {
      const user = userEvent.setup()
      
      mockApiClient.post.mockImplementation((endpoint) => {
        if (endpoint === '/api/import/file') {
          return Promise.reject(new Error('Import failed'))
        }
        return Promise.resolve({})
      })

      render(<UnifiedFileImporter {...mockProps} />)
      
      await waitFor(() => {
        expect(screen.getByText('Import Parts')).toBeInTheDocument()
      })

      const importButton = screen.getByText('Import Parts')
      await user.click(importButton)

      await waitFor(() => {
        expect(mockToast.error).toHaveBeenCalledWith('Import failed')
      })

      expect(mockProps.onImportComplete).not.toHaveBeenCalled()
    })

    it('should handle API error response', async () => {
      const user = userEvent.setup()
      
      mockApiClient.post.mockImplementation((endpoint) => {
        if (endpoint === '/api/import/file') {
          return Promise.resolve({
            status: 'error',
            message: 'Invalid file format'
          })
        }
        return Promise.resolve({})
      })

      render(<UnifiedFileImporter {...mockProps} />)
      
      await waitFor(() => {
        expect(screen.getByText('Import Parts')).toBeInTheDocument()
      })

      const importButton = screen.getByText('Import Parts')
      await user.click(importButton)

      await waitFor(() => {
        expect(mockToast.error).toHaveBeenCalledWith('Invalid file format')
      })
    })
  })

  describe('Form Data Creation', () => {
    it('should include file and parser type in FormData', async () => {
      const user = userEvent.setup()
      render(<UnifiedFileImporter {...mockProps} />)
      
      await waitFor(() => {
        expect(screen.getByText('Import Parts')).toBeInTheDocument()
      })

      const importButton = screen.getByText('Import Parts')
      await user.click(importButton)

      await waitFor(() => {
        const importCall = mockApiClient.post.mock.calls.find(
          call => call[0] === '/api/import/file'
        )
        expect(importCall).toBeDefined()
        
        const formData = importCall![1] as FormData
        expect(formData.get('file')).toBe(mockFile)
        expect(formData.get('parser_type')).toBe('lcsc')
      })
    })
  })

  describe('Component Behavior', () => {
    it('should call onImportComplete when import succeeds', async () => {
      const user = userEvent.setup()
      render(<UnifiedFileImporter {...mockProps} />)
      
      await waitFor(() => {
        expect(screen.getByText('Import Parts')).toBeInTheDocument()
      })

      const importButton = screen.getByText('Import Parts')
      await user.click(importButton)

      await waitFor(() => {
        expect(mockProps.onImportComplete).toHaveBeenCalledWith({
          success_parts: [{ id: '1', name: 'Resistor 1k', part_number: 'R001' }],
          failed_parts: []
        })
      })
    })
  })
})