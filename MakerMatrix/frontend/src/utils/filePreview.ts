/**
 * Frontend-only file preview utility
 * Replaces backend /api/import/preview and /api/import/preview-file endpoints
 */

import * as XLSX from 'xlsx'
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
 * Parse CSV content
 */
function parseCSV(text: string): { headers: string[]; rows: any[]; totalRows: number } {
  // Remove BOM if present
  const csvContent = text.replace(/^\uFEFF/, '')

  // Split into lines and filter out empty lines
  const lines = csvContent.split('\n').filter((line) => line.trim().length > 0)

  if (lines.length === 0) {
    return { headers: [], rows: [], totalRows: 0 }
  }

  // Parse CSV headers (first line)
  const headers = lines[0].split(',').map((header) => header.trim().replace(/^"|"$/g, ''))

  // Parse preview rows (next few lines, up to 5)
  const previewRows: any[] = []
  const maxPreviewRows = Math.min(5, lines.length - 1)

  for (let i = 1; i <= maxPreviewRows; i++) {
    const cells = lines[i].split(',').map((cell) => cell.trim().replace(/^"|"$/g, ''))
    const row: any = {}

    headers.forEach((header, index) => {
      row[header] = cells[index] || ''
    })

    previewRows.push(row)
  }

  return {
    headers,
    rows: previewRows,
    totalRows: Math.max(0, lines.length - 1), // Subtract 1 for header row
  }
}

/**
 * Parse Excel file (XLS or XLSX)
 */
async function parseExcel(
  file: File
): Promise<{ headers: string[]; rows: any[]; totalRows: number }> {
  const arrayBuffer = await file.arrayBuffer()
  const workbook = XLSX.read(arrayBuffer, { type: 'array' })

  // Get first sheet
  const firstSheetName = workbook.SheetNames[0]
  if (!firstSheetName) {
    return { headers: [], rows: [], totalRows: 0 }
  }

  const worksheet = workbook.Sheets[firstSheetName]

  // Convert to JSON with header row
  const jsonData = XLSX.utils.sheet_to_json(worksheet, { header: 1, defval: '' }) as any[][]

  if (jsonData.length === 0) {
    return { headers: [], rows: [], totalRows: 0 }
  }

  // First row is headers
  const headers = jsonData[0].map((h) => String(h || '').trim())

  // Convert remaining rows to objects
  const previewRows: any[] = []
  const maxPreviewRows = Math.min(5, jsonData.length - 1)

  for (let i = 1; i <= maxPreviewRows; i++) {
    const row: any = {}
    headers.forEach((header, index) => {
      row[header] = jsonData[i][index] !== undefined ? String(jsonData[i][index]) : ''
    })
    previewRows.push(row)
  }

  return {
    headers,
    rows: previewRows,
    totalRows: Math.max(0, jsonData.length - 1), // Subtract 1 for header row
  }
}

/**
 * Preview file content (CSV, XLS, or XLSX) without backend API calls
 * @param file The uploaded file
 * @returns Promise resolving to preview data
 */
export async function previewFile(file: File): Promise<FilePreviewData> {
  const filename = file.name
  const filenameLower = filename.toLowerCase()

  // Extract supplier info from filename
  const extractedInfo = extractFilenameInfo(filename)

  try {
    let headers: string[] = []
    let previewRows: any[] = []
    let totalRows = 0
    let parseError: string | null = null

    // Determine file type and parse accordingly
    if (filenameLower.endsWith('.xls') || filenameLower.endsWith('.xlsx')) {
      // Parse Excel file - catch errors gracefully since frontend parsing is optional
      try {
        const result = await parseExcel(file)
        headers = result.headers
        previewRows = result.rows
        totalRows = result.totalRows
      } catch (excelError) {
        // Excel parsing failed - this is OK if supplier is detected from filename
        // The backend will handle the actual parsing during import
        parseError = excelError instanceof Error ? excelError.message : 'Excel parsing error'
      }
    } else {
      // Parse as CSV
      const text = await file.text()
      const result = parseCSV(text)
      headers = result.headers
      previewRows = result.rows
      totalRows = result.totalRows
    }

    // Basic validation
    const validationErrors: string[] = []
    if (parseError) {
      // Don't treat Excel parsing errors as critical if supplier was detected
      if (!extractedInfo.detected_supplier) {
        validationErrors.push(parseError)
      }
    }
    if (headers.length === 0 && !parseError) {
      validationErrors.push('No headers found in file')
    }
    if (totalRows === 0 && !parseError) {
      validationErrors.push('No data rows found in file')
    }

    // Add supplier detection error if no supplier detected
    const allValidationErrors = extractedInfo.detected_supplier
      ? validationErrors
      : ['Could not detect supplier from filename', ...validationErrors]

    return {
      detected_parser: extractedInfo.detected_supplier || null,
      file_type: extractedInfo.file_type,
      headers: headers,
      preview_rows: previewRows,
      total_rows: totalRows,
      // Consider file supported if supplier detected AND (no critical validation errors OR it's an Excel file)
      is_supported:
        !!extractedInfo.detected_supplier &&
        (validationErrors.length === 0 ||
          filenameLower.endsWith('.xls') ||
          filenameLower.endsWith('.xlsx')),
      validation_errors: allValidationErrors,
    }
  } catch (error) {
    // Critical errors (file read errors, etc.)
    return {
      detected_parser: extractedInfo.detected_supplier || null,
      file_type: extractedInfo.file_type,
      headers: [],
      preview_rows: [],
      total_rows: 0,
      is_supported: false,
      validation_errors: [
        `Error reading file: ${error instanceof Error ? error.message : 'Unknown error'}`,
      ],
    }
  }
}
