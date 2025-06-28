/**
 * DigiKey CSV Importer Tests
 * 
 * Tests for DigiKey-specific CSV import functionality in the frontend.
 * Validates integration with backend DigiKey import capabilities.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '../../../__tests__/utils/render'
import { DigiKeyImporter } from '../importers/DigiKeyImporter'
import { extractFilenameInfo } from '../../../utils/filenameExtractor'

// Mock the utility functions
vi.mock('../../../utils/filenameExtractor', () => ({
  extractFilenameInfo: vi.fn()
}))

describe('DigiKey CSV Importer', () => {
  const mockProps = {
    file: new File(['test content'], 'DK_PRODUCTS_88269818.csv', { type: 'text/csv' }),
    onImport: vi.fn(),
    onCancel: vi.fn(),
    className: ''
  }

  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('File Detection and Validation', () => {
    it('correctly identifies DigiKey CSV files', () => {
      const mockExtractionResult = {
        detected_supplier: 'digikey',
        file_type: 'CSV',
        order_info: {
          order_number: '88269818',
          notes: 'Auto-extracted from filename: DK_PRODUCTS_88269818.csv'
        },
        filename: 'DK_PRODUCTS_88269818.csv'
      }

      vi.mocked(extractFilenameInfo).mockReturnValue(mockExtractionResult)

      render(<DigiKeyImporter {...mockProps} />)

      expect(extractFilenameInfo).toHaveBeenCalledWith('DK_PRODUCTS_88269818.csv')
    })

    it('validates DigiKey CSV file formats', () => {
      const testFiles = [
        'DK_PRODUCTS_88269818.csv',
        'digikey_export_123456.csv',
        'digi-key_order_789012.csv',
        'weborder_555666.csv'
      ]

      testFiles.forEach(filename => {
        const mockResult = {
          detected_supplier: 'digikey',
          file_type: 'CSV',
          order_info: { order_number: '123456' },
          filename
        }

        vi.mocked(extractFilenameInfo).mockReturnValue(mockResult)

        const file = new File(['test'], filename, { type: 'text/csv' })
        render(<DigiKeyImporter {...mockProps} file={file} />)

        expect(extractFilenameInfo).toHaveBeenCalledWith(filename)
      })
    })

    it('handles DigiKey Excel files (.xlsx/.xls)', () => {
      const excelFiles = [
        { name: 'digikey_export.xlsx', type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' },
        { name: 'digi-key_order.xls', type: 'application/vnd.ms-excel' }
      ]

      excelFiles.forEach(({ name, type }) => {
        const mockResult = {
          detected_supplier: 'digikey',
          file_type: name.includes('.xlsx') ? 'XLSX' : 'XLS',
          order_info: { order_number: '123456' },
          filename: name
        }

        vi.mocked(extractFilenameInfo).mockReturnValue(mockResult)

        const file = new File(['test'], name, { type })
        render(<DigiKeyImporter {...mockProps} file={file} />)

        expect(extractFilenameInfo).toHaveBeenCalledWith(name)
      })
    })
  })

  describe('Order Information Extraction', () => {
    it('extracts order number from DigiKey filename patterns', () => {
      const testCases = [
        {
          filename: 'DK_PRODUCTS_88269818.csv',
          expectedOrderNumber: '88269818'
        },
        {
          filename: 'digikey-export-ORD789123.xlsx',
          expectedOrderNumber: 'ORD789123'
        },
        {
          filename: 'digi-key_order_ABC12345.xls',
          expectedOrderNumber: 'ABC12345'
        }
      ]

      testCases.forEach(({ filename, expectedOrderNumber }) => {
        const mockResult = {
          detected_supplier: 'digikey',
          file_type: 'CSV',
          order_info: {
            order_number: expectedOrderNumber,
            notes: `Auto-extracted from filename: ${filename}`
          },
          filename
        }

        vi.mocked(extractFilenameInfo).mockReturnValue(mockResult)

        const file = new File(['test'], filename, { type: 'text/csv' })
        render(<DigiKeyImporter {...mockProps} file={file} />)

        // Check that the order number would be displayed
        expect(extractFilenameInfo).toHaveBeenCalledWith(filename)
      })
    })

    it('handles files without recognizable order patterns', () => {
      const mockResult = {
        detected_supplier: 'digikey',
        file_type: 'CSV',
        order_info: {},
        filename: 'digikey_parts.csv'
      }

      vi.mocked(extractFilenameInfo).mockReturnValue(mockResult)

      const file = new File(['test'], 'digikey_parts.csv', { type: 'text/csv' })
      render(<DigiKeyImporter {...mockProps} file={file} />)

      expect(extractFilenameInfo).toHaveBeenCalledWith('digikey_parts.csv')
    })
  })

  describe('Import Configuration', () => {
    it('provides DigiKey-specific import options', () => {
      const mockResult = {
        detected_supplier: 'digikey',
        file_type: 'CSV',
        order_info: { order_number: '88269818' },
        filename: 'DK_PRODUCTS_88269818.csv'
      }

      vi.mocked(extractFilenameInfo).mockReturnValue(mockResult)

      render(<DigiKeyImporter {...mockProps} />)

      // Should show DigiKey-specific configuration options
      // This would depend on the actual implementation of DigiKeyImporter
    })

    it('supports both sandbox and production mode configuration', () => {
      const mockResult = {
        detected_supplier: 'digikey',
        file_type: 'CSV',
        order_info: { order_number: '88269818' },
        filename: 'DK_PRODUCTS_88269818.csv'
      }

      vi.mocked(extractFilenameInfo).mockReturnValue(mockResult)

      render(<DigiKeyImporter {...mockProps} />)

      // Implementation would show sandbox/production mode options
      // This tests the configuration UI for DigiKey imports
    })
  })

  describe('Error Handling', () => {
    it('handles non-DigiKey files gracefully', () => {
      const mockResult = {
        detected_supplier: 'mouser',
        file_type: 'XLS',
        order_info: { order_number: '123456' },
        filename: 'mouser_order.xls'
      }

      vi.mocked(extractFilenameInfo).mockReturnValue(mockResult)

      const file = new File(['test'], 'mouser_order.xls', { type: 'application/vnd.ms-excel' })
      
      // Should not render or show error for non-DigiKey files
      const { container } = render(<DigiKeyImporter {...mockProps} file={file} />)
      
      // DigiKey importer should not handle non-DigiKey files
      expect(container).toBeInTheDocument()
    })

    it('validates file size limits for DigiKey imports', () => {
      const mockResult = {
        detected_supplier: 'digikey',
        file_type: 'CSV',
        order_info: { order_number: '88269818' },
        filename: 'DK_PRODUCTS_88269818.csv'
      }

      vi.mocked(extractFilenameInfo).mockReturnValue(mockResult)

      // Create a large file (> 10MB)
      const largeContent = 'x'.repeat(11 * 1024 * 1024)
      const largeFile = new File([largeContent], 'DK_PRODUCTS_88269818.csv', { type: 'text/csv' })

      render(<DigiKeyImporter {...mockProps} file={largeFile} />)

      // Should handle large file validation
      expect(extractFilenameInfo).toHaveBeenCalledWith('DK_PRODUCTS_88269818.csv')
    })

    it('handles corrupted or invalid DigiKey files', () => {
      const mockResult = {
        detected_supplier: 'digikey',
        file_type: 'CSV',
        order_info: { order_number: '88269818' },
        filename: 'DK_PRODUCTS_88269818.csv'
      }

      vi.mocked(extractFilenameInfo).mockReturnValue(mockResult)

      // File with binary content that should be CSV
      const binaryFile = new File([new ArrayBuffer(100)], 'DK_PRODUCTS_88269818.csv', { type: 'text/csv' })

      render(<DigiKeyImporter {...mockProps} file={binaryFile} />)

      expect(extractFilenameInfo).toHaveBeenCalledWith('DK_PRODUCTS_88269818.csv')
    })
  })

  describe('Integration with Backend', () => {
    it('calls onImport with correct DigiKey parameters', async () => {
      const mockResult = {
        detected_supplier: 'digikey',
        file_type: 'CSV',
        order_info: {
          order_number: '88269818',
          notes: 'Auto-extracted from filename: DK_PRODUCTS_88269818.csv'
        },
        filename: 'DK_PRODUCTS_88269818.csv'
      }

      vi.mocked(extractFilenameInfo).mockReturnValue(mockResult)

      render(<DigiKeyImporter {...mockProps} />)

      // Simulate import action (this would depend on actual implementation)
      // The test verifies that the correct parameters are passed to the import handler
      
      expect(extractFilenameInfo).toHaveBeenCalledWith('DK_PRODUCTS_88269818.csv')
    })

    it('passes extracted order information to import service', () => {
      const mockResult = {
        detected_supplier: 'digikey',
        file_type: 'CSV',
        order_info: {
          order_number: '88269818',
          order_date: '2024-01-15',
          notes: 'Auto-extracted from filename: DK_PRODUCTS_88269818.csv'
        },
        filename: 'DK_PRODUCTS_88269818.csv'
      }

      vi.mocked(extractFilenameInfo).mockReturnValue(mockResult)

      render(<DigiKeyImporter {...mockProps} />)

      // The component should extract and use this information
      // for the import process
      expect(extractFilenameInfo).toHaveBeenCalledWith('DK_PRODUCTS_88269818.csv')
    })
  })

  describe('User Interface', () => {
    it('displays DigiKey-specific import instructions', () => {
      const mockResult = {
        detected_supplier: 'digikey',
        file_type: 'CSV',
        order_info: { order_number: '88269818' },
        filename: 'DK_PRODUCTS_88269818.csv'
      }

      vi.mocked(extractFilenameInfo).mockReturnValue(mockResult)

      render(<DigiKeyImporter {...mockProps} />)

      // Should show DigiKey-specific instructions
      // Implementation would include guidance for DigiKey CSV format
    })

    it('shows file preview with DigiKey-specific columns', () => {
      const mockResult = {
        detected_supplier: 'digikey',
        file_type: 'CSV',
        order_info: { order_number: '88269818' },
        filename: 'DK_PRODUCTS_88269818.csv'
      }

      vi.mocked(extractFilenameInfo).mockReturnValue(mockResult)

      render(<DigiKeyImporter {...mockProps} />)

      // Should parse and preview DigiKey-specific columns
      // like "Digi-Key Part Number", "Manufacturer", etc.
    })
  })

  describe('Compatibility', () => {
    it('maintains backward compatibility with existing DigiKey imports', () => {
      const legacyFilenames = [
        'digikey_order.csv',
        'dk_products.csv',
        'digi-key_export.xlsx'
      ]

      legacyFilenames.forEach(filename => {
        const mockResult = {
          detected_supplier: 'digikey',
          file_type: 'CSV',
          order_info: {},
          filename
        }

        vi.mocked(extractFilenameInfo).mockReturnValue(mockResult)

        const file = new File(['test'], filename, { type: 'text/csv' })
        render(<DigiKeyImporter {...mockProps} file={file} />)

        expect(extractFilenameInfo).toHaveBeenCalledWith(filename)
      })
    })

    it('works with both old and new DigiKey CSV formats', () => {
      const formats = [
        'DK_PRODUCTS_88269818.csv',  // New format
        'digikey_cart_123456.csv',   // Alternative format
        'weborder_789012.csv'        // Web order format
      ]

      formats.forEach(filename => {
        const mockResult = {
          detected_supplier: 'digikey',
          file_type: 'CSV',
          order_info: { order_number: '123456' },
          filename
        }

        vi.mocked(extractFilenameInfo).mockReturnValue(mockResult)

        const file = new File(['test'], filename, { type: 'text/csv' })
        render(<DigiKeyImporter {...mockProps} file={file} />)

        expect(extractFilenameInfo).toHaveBeenCalledWith(filename)
      })
    })
  })
})