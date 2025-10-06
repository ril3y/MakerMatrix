import { describe, it, expect } from 'vitest'
import { extractFilenameInfo, extractOrderInfoFromFilename } from '../filenameExtractor'

describe('filenameExtractor', () => {
  describe('extractFilenameInfo', () => {
    it('should detect DigiKey files and extract order numbers', () => {
      const testCases = [
        {
          filename: 'DK_PRODUCTS_88269818.csv',
          expected: {
            detected_supplier: 'digikey',
            file_type: 'CSV',
            order_info: {
              order_number: '88269818',
              notes: 'Auto-extracted from filename: DK_PRODUCTS_88269818.csv'
            }
          }
        },
        {
          filename: 'digikey-export-ORD789123.xlsx',
          expected: {
            detected_supplier: 'digikey',
            file_type: 'XLSX',
            order_info: {
              order_number: 'ORD789123',
              notes: 'Auto-extracted from filename: digikey-export-ORD789123.xlsx'
            }
          }
        },
        {
          filename: 'digi-key_order_ABC12345.xls',
          expected: {
            detected_supplier: 'digikey',
            file_type: 'XLS',
            order_info: {
              order_number: 'ABC12345',
              notes: 'Auto-extracted from filename: digi-key_order_ABC12345.xls'
            }
          }
        }
      ]

      testCases.forEach(({ filename, expected }) => {
        const result = extractFilenameInfo(filename)
        
        expect(result.detected_supplier).toBe(expected.detected_supplier)
        expect(result.file_type).toBe(expected.file_type)
        expect(result.order_info.order_number).toBe(expected.order_info.order_number)
        expect(result.order_info.notes).toBe(expected.order_info.notes)
        expect(result.filename).toBe(filename)
      })
    })

    it('should detect LCSC files and extract information', () => {
      const testCases = [
        {
          filename: 'lcsc_parts_20240101.csv',
          expected: {
            detected_supplier: 'lcsc',
            file_type: 'CSV',
            order_info: {
              order_date: '20240101',
              notes: 'Auto-extracted from filename: lcsc_parts_20240101.csv'
            }
          }
        },
        {
          filename: 'LCSC-Order-12345678.xlsx',
          expected: {
            detected_supplier: 'lcsc',
            file_type: 'XLSX',
            order_info: {
              order_number: '12345678',
              notes: 'Auto-extracted from filename: LCSC-Order-12345678.xlsx'
            }
          }
        }
      ]

      testCases.forEach(({ filename, expected }) => {
        const result = extractFilenameInfo(filename)

        expect(result.detected_supplier).toBe(expected.detected_supplier)
        expect(result.file_type).toBe(expected.file_type)
        if (expected.order_info.order_number) {
          expect(result.order_info.order_number).toBe(expected.order_info.order_number)
        }
        if (expected.order_info.order_date) {
          expect(result.order_info.order_date).toBe(expected.order_info.order_date)
        }
        expect(result.order_info.notes).toBe(expected.order_info.notes)
      })
    })

    it('should extract LCSC datetime format (YYYYMMDD_HHMMSS.csv)', () => {
      const testCases = [
        {
          filename: 'LCSC_Exported__20241222_232703.csv',
          expected: {
            detected_supplier: 'lcsc',
            file_type: 'CSV',
            order_info: {
              order_date: '2024-12-22',
              order_number: '232703',
              notes: 'Auto-extracted from LCSC filename: LCSC_Exported__20241222_232703.csv'
            }
          }
        },
        {
          filename: '20241222_232709.csv',
          expected: {
            detected_supplier: 'lcsc',
            file_type: 'CSV',
            order_info: {
              order_date: '2024-12-22',
              order_number: '232709',
              notes: 'Auto-extracted from LCSC filename: 20241222_232709.csv'
            }
          }
        },
        {
          filename: 'LCSC_Exported__20240315_123456.csv',
          expected: {
            detected_supplier: 'lcsc',
            file_type: 'CSV',
            order_info: {
              order_date: '2024-03-15',
              order_number: '123456',
              notes: 'Auto-extracted from LCSC filename: LCSC_Exported__20240315_123456.csv'
            }
          }
        },
        {
          filename: 'lcsc_exported__20240101_000000.csv',
          expected: {
            detected_supplier: 'lcsc',
            file_type: 'CSV',
            order_info: {
              order_date: '2024-01-01',
              order_number: '000000',
              notes: 'Auto-extracted from LCSC filename: lcsc_exported__20240101_000000.csv'
            }
          }
        }
      ]

      testCases.forEach(({ filename, expected }) => {
        const result = extractFilenameInfo(filename)

        expect(result.detected_supplier).toBe(expected.detected_supplier)
        expect(result.file_type).toBe(expected.file_type)
        expect(result.order_info.order_date).toBe(expected.order_info.order_date)
        expect(result.order_info.order_number).toBe(expected.order_info.order_number)
        expect(result.order_info.notes).toBe(expected.order_info.notes)
      })
    })

    it('should detect Mouser files and extract information', () => {
      const testCases = [
        {
          filename: 'mouser_order_123456.xls',
          expected: {
            detected_supplier: 'mouser',
            file_type: 'XLS',
            order_info: {
              order_number: '123456',
              notes: 'Auto-extracted from filename: mouser_order_123456.xls'
            }
          }
        },
        {
          filename: 'Mouser-PO-987654321.xlsx',
          expected: {
            detected_supplier: 'mouser',
            file_type: 'XLSX',
            order_info: {
              order_number: '987654321',
              notes: 'Auto-extracted from filename: Mouser-PO-987654321.xlsx'
            }
          }
        }
      ]

      testCases.forEach(({ filename, expected }) => {
        const result = extractFilenameInfo(filename)
        
        expect(result.detected_supplier).toBe(expected.detected_supplier)
        expect(result.file_type).toBe(expected.file_type)
        expect(result.order_info.order_number).toBe(expected.order_info.order_number)
        expect(result.order_info.notes).toBe(expected.order_info.notes)
      })
    })

    it('should extract date patterns correctly', () => {
      const testCases = [
        {
          filename: 'parts_2024-01-15.csv',
          expected: { order_date: '2024-01-15' }
        },
        {
          filename: 'export_20240115.xlsx',
          expected: { order_date: '20240115' }
        },
        {
          filename: 'order_01-15-2024.xls',
          expected: { order_date: '01-15-2024' }
        },
        {
          filename: 'data_2024_01_15.csv',
          expected: { order_date: '2024_01_15' }
        }
      ]

      testCases.forEach(({ filename, expected }) => {
        const result = extractFilenameInfo(filename)
        expect(result.order_info.order_date).toBe(expected.order_date)
      })
    })

    it('should handle files with no recognizable patterns', () => {
      const testCases = [
        'random_file.csv',
        'unknown_format.xlsx',
        'no_patterns_here.xls',
        'justtext.csv'
      ]

      testCases.forEach((filename) => {
        const result = extractFilenameInfo(filename)
        
        expect(result.detected_supplier).toBeUndefined()
        expect(result.order_info.order_number).toBeUndefined()
        expect(result.order_info.order_date).toBeUndefined()
        expect(result.order_info.notes).toBeUndefined()
        expect(result.filename).toBe(filename)
      })
    })

    it('should detect Mouser from numeric XLS filenames like actual order files', () => {
      const testCases = [
        { filename: '271360826.xls', expectedType: 'XLS' },
        { filename: '123456789.xlsx', expectedType: 'XLSX' },
        { filename: 'order_987654321.xls', expectedType: 'XLS' }
      ]

      testCases.forEach(({ filename, expectedType }) => {
        const result = extractFilenameInfo(filename)
        
        expect(result.detected_supplier).toBe('mouser')
        expect(result.file_type).toBe(expectedType)
      })
    })

    it('should detect DigiKey from numeric CSV filenames', () => {
      const testCases = [
        'DK_PRODUCTS_88269818.csv',
        '12345678_export.csv',
        'parts_87654321.csv'
      ]

      testCases.forEach((filename) => {
        const result = extractFilenameInfo(filename)
        
        expect(result.detected_supplier).toBe('digikey')
        expect(result.file_type).toBe('CSV')
      })
    })

    it('should handle case sensitivity correctly', () => {
      // Test that we return lowercase supplier names consistently
      const testCases = [
        { filename: 'DIGIKEY_order.csv', expected: 'digikey' },
        { filename: 'MOUSER_cart.xls', expected: 'mouser' },
        { filename: 'LCSC_parts.csv', expected: 'lcsc' }
      ]

      testCases.forEach(({ filename, expected }) => {
        const result = extractFilenameInfo(filename)
        
        expect(result.detected_supplier).toBe(expected)
      })
    })

    it('should handle files without extensions', () => {
      const result = extractFilenameInfo('digikey_order_123')
      
      expect(result.detected_supplier).toBe('digikey')
      expect(result.file_type).toBe('')
      expect(result.order_info.order_number).toBe('123')
    })

    it('should be case insensitive for supplier detection', () => {
      const testCases = [
        'DIGIKEY_parts.csv',
        'DigiKey_Export.xlsx',
        'dIgI-kEy_order.xls',
        'LCSC_parts.csv',
        'lcsc_ORDER.xlsx',
        'MOUSER_export.xls',
        'mouser_PARTS.csv'
      ]

      testCases.forEach((filename) => {
        const result = extractFilenameInfo(filename)
        expect(result.detected_supplier).toBeDefined()
      })
    })
  })

  describe('extractOrderInfoFromFilename (legacy compatibility)', () => {
    it('should maintain backward compatibility with existing code', async () => {
      const filename = 'DK_PRODUCTS_88269818.csv'
      const parserType = 'digikey'
      
      const result = await extractOrderInfoFromFilename(filename, parserType)
      
      expect(result).toEqual({
        order_number: '88269818',
        notes: 'Auto-extracted from filename: DK_PRODUCTS_88269818.csv'
      })
    })

    it('should return empty object for unrecognized patterns', async () => {
      const filename = 'random_file.csv'
      const parserType = 'unknown'
      
      const result = await extractOrderInfoFromFilename(filename, parserType)
      
      expect(result).toEqual({})
    })

    it('should handle files with both order number and date', async () => {
      const filename = 'lcsc_order_12345_2024-01-15.csv'
      const parserType = 'lcsc'
      
      const result = await extractOrderInfoFromFilename(filename, parserType)
      
      expect(result.order_number).toBe('12345')
      expect(result.order_date).toBe('2024-01-15')
      expect(result.notes).toBe('Auto-extracted from filename: lcsc_order_12345_2024-01-15.csv')
    })

    it('should handle DK_PRODUCTS_88269818.csv correctly', async () => {
      const filename = 'DK_PRODUCTS_88269818.csv'
      const parserType = 'digikey'
      
      const result = await extractOrderInfoFromFilename(filename, parserType)
      const fullInfo = extractFilenameInfo(filename)
      
      // Should extract as order number, NOT date
      expect(result.order_number).toBe('88269818')
      expect(result.order_date).toBeUndefined()
      expect(fullInfo.detected_supplier).toBe('digikey')
      expect(fullInfo.file_type).toBe('CSV')
    })
  })

  describe('edge cases', () => {
    it('should handle empty filename', () => {
      const result = extractFilenameInfo('')
      
      expect(result.detected_supplier).toBeUndefined()
      expect(result.file_type).toBe('')
      expect(result.order_info).toEqual({})
      expect(result.filename).toBe('')
    })

    it('should handle filenames with multiple potential patterns', () => {
      // Should extract the first matching order number pattern
      const result = extractFilenameInfo('order_123_po_456.csv')
      
      expect(result.order_info.order_number).toBe('123')
    })

    it('should prioritize longer digit sequences for order numbers', () => {
      const result = extractFilenameInfo('file_12345678.csv')
      
      expect(result.order_info.order_number).toBe('12345678')
    })
  })
})