import { describe, it, expect } from 'vitest'
import { previewFile } from '../filePreview'

describe('filePreview', () => {
  describe('previewFile', () => {
    it('should detect DigiKey from filename', async () => {
      const csvContent =
        'Digi-Key Part Number,Manufacturer Part Number,Description,Quantity\nABC123,XYZ789,Test Resistor,10\nDEF456,UVW012,Test Capacitor,5'
      const file = new File([csvContent], 'DK_PRODUCTS_88269818.csv', { type: 'text/csv' })

      const result = await previewFile(file)

      expect(result.detected_parser).toBe('digikey')
      expect(result.file_type).toBe('CSV')
      expect(result.is_supported).toBe(true)
      expect(result.validation_errors).toHaveLength(0)
    })

    it('should detect LCSC from filename', async () => {
      const csvContent =
        'LCSC Part Number,Customer No.,Description,Quantity\nC123456,ABC123,Test Resistor,10\nC789012,DEF456,Test Capacitor,5'
      const file = new File([csvContent], 'lcsc_parts_20240101.csv', { type: 'text/csv' })

      const result = await previewFile(file)

      expect(result.detected_parser).toBe('lcsc')
      expect(result.file_type).toBe('CSV')
      expect(result.is_supported).toBe(true)
    })

    it('should handle unrecognized filenames', async () => {
      const content = 'some random content'
      const file = new File([content], 'test.txt', { type: 'text/plain' })

      const result = await previewFile(file)

      expect(result.detected_parser).toBeNull()
      expect(result.is_supported).toBe(false)
      expect(result.validation_errors).toContain('Could not detect supplier from filename')
    })

    it('should detect supplier from filename patterns', async () => {
      const csvContent = 'Part,Description,Qty\nABC123,Test Part,10'
      const file = new File([csvContent], 'digikey_export.csv', { type: 'text/csv' })

      const result = await previewFile(file)

      expect(result.detected_parser).toBe('digikey')
      expect(result.file_type).toBe('CSV')
      expect(result.is_supported).toBe(true)
    })

    it('should detect Mouser from XLS files', async () => {
      const xlsContent = 'fake excel content'
      const file = new File([xlsContent], '271360826.xls', { type: 'application/vnd.ms-excel' })

      const result = await previewFile(file)

      expect(result.detected_parser).toBe('mouser')
      expect(result.file_type).toBe('XLS')
      expect(result.is_supported).toBe(true)
    })

    it('should detect Mouser from explicit patterns', async () => {
      const xlsContent = 'fake excel content'
      const file = new File([xlsContent], 'mouser_order_123.xlsx', {
        type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
      })

      const result = await previewFile(file)

      expect(result.detected_parser).toBe('mouser')
      expect(result.file_type).toBe('XLSX')
      expect(result.is_supported).toBe(true)
    })

    it('should detect XLS files with numeric patterns as Mouser', async () => {
      const xlsContent = 'fake excel content'
      const file = new File([xlsContent], '271360826.xls', { type: 'application/vnd.ms-excel' })

      const result = await previewFile(file)

      expect(result.detected_parser).toBe('mouser')
      expect(result.file_type).toBe('XLS')
      expect(result.is_supported).toBe(true)
    })
  })
})
