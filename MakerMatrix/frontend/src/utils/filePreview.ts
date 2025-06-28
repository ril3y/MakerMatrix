/**
 * Frontend-only file preview utility
 * Replaces backend /api/import/preview and /api/import/preview-file endpoints
 */

import { extractFilenameInfo } from './filenameExtractor'

export interface FilePreviewData {
  detected_parser: string | null
  file_type: string
  headers: string[]
  preview_rows: any[]
  total_rows: number
  is_supported: boolean
  validation_errors: string[]
  error?: string
}

/**
 * Preview CSV file content without backend API calls
 * @param file The uploaded file
 * @returns Promise resolving to preview data
 */
export async function previewFile(file: File): Promise<FilePreviewData> {
  const filename = file.name
  const filenameLower = filename.toLowerCase()
  
  // Extract supplier info from filename
  const extractedInfo = extractFilenameInfo(filename)
  
  try {
    // Read and parse CSV content
    const text = await file.text()
    
    // Remove BOM if present
    const csvContent = text.replace(/^\uFEFF/, '')
    
    // Split into lines and filter out empty lines
    const lines = csvContent.split('\n').filter(line => line.trim().length > 0)
    
    if (lines.length === 0) {
      return {
        detected_parser: extractedInfo.detected_supplier || null,
        file_type: extractedInfo.file_type,
        headers: [],
        preview_rows: [],
        total_rows: 0,
        is_supported: false,
        validation_errors: ['File appears to be empty']
      }
    }
    
    // Parse CSV headers (first line)
    const headers = lines[0].split(',').map(header => header.trim().replace(/^"|"$/g, ''))
    
    // Parse preview rows (next few lines, up to 5)
    const previewRows: any[] = []
    const maxPreviewRows = Math.min(5, lines.length - 1)
    
    for (let i = 1; i <= maxPreviewRows; i++) {
      const cells = lines[i].split(',').map(cell => cell.trim().replace(/^"|"$/g, ''))
      const row: any = {}
      
      headers.forEach((header, index) => {
        row[header] = cells[index] || ''
      })
      
      previewRows.push(row)
    }
    
    // Basic validation
    const validationErrors: string[] = []
    if (headers.length === 0) {
      validationErrors.push('No headers found in CSV file')
    }
    if (lines.length <= 1) {
      validationErrors.push('No data rows found in CSV file')
    }
    
    return {
      detected_parser: extractedInfo.detected_supplier || null,
      file_type: extractedInfo.file_type,
      headers: headers,
      preview_rows: previewRows,
      total_rows: Math.max(0, lines.length - 1), // Subtract 1 for header row
      is_supported: !!extractedInfo.detected_supplier && validationErrors.length === 0,
      validation_errors: extractedInfo.detected_supplier ? validationErrors : ['Could not detect supplier from filename', ...validationErrors]
    }
    
  } catch (error) {
    return {
      detected_parser: extractedInfo.detected_supplier || null,
      file_type: extractedInfo.file_type,
      headers: [],
      preview_rows: [],
      total_rows: 0,
      is_supported: false,
      validation_errors: [`Error reading file: ${error instanceof Error ? error.message : 'Unknown error'}`]
    }
  }
}

