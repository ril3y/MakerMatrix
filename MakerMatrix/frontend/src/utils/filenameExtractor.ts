/**
 * Frontend utility for extracting order information from filenames
 * Replaces the backend /api/import/extract-filename-info endpoint
 */

export interface ExtractedFileInfo {
  detected_supplier?: string
  file_type: string
  order_info: {
    order_number?: string
    order_date?: string
    notes?: string
  }
  filename: string
}

/**
 * Extract order information from filename patterns
 * @param filename The name of the uploaded file
 * @returns Extracted file information including supplier, order details, etc.
 */
export function extractFilenameInfo(filename: string): ExtractedFileInfo {
  const filenameLower = filename.toLowerCase()
  const fileExt = filename.includes('.') ? filename.split('.').pop()?.toLowerCase() || '' : ''
  
  // Detect supplier from filename patterns
  let detectedSupplier: string | undefined
  
  if (filenameLower.includes('lcsc')) {
    detectedSupplier = 'lcsc'
  } else if (
    filenameLower.includes('digikey') || 
    filenameLower.includes('digi-key') || 
    filenameLower.includes('dk_') ||
    filenameLower.includes('dk_products')
  ) {
    detectedSupplier = 'digikey'
  } else if (
    filenameLower.includes('mouser') ||
    filenameLower.includes('mouse') ||
    filenameLower.includes('cart') ||
    filenameLower.includes('order')
  ) {
    detectedSupplier = 'mouser'
  }
  
  // If no supplier detected but file is XLS/XLSX, check for numeric patterns that might indicate orders
  // (since Mouser is the primary supplier using Excel format, but only for files that look like orders)
  if (!detectedSupplier && (fileExt === 'xls' || fileExt === 'xlsx')) {
    // Look for numeric patterns that suggest this is an order file
    if (/\d{6,}/.test(filename)) { // 6+ digit numbers often indicate order numbers
      detectedSupplier = 'mouser'
    }
  }
  
  // If no supplier detected but file is CSV, try more specific patterns
  if (!detectedSupplier && fileExt === 'csv') {
    // Check for common CSV patterns that might indicate DigiKey or other suppliers
    if (
      /\d{8,}/.test(filename) || // Long number sequences often DigiKey
      filenameLower.includes('export') ||
      filenameLower.includes('parts')
    ) {
      detectedSupplier = 'digikey'
    }
    // Don't auto-default CSV files to a specific supplier unless we have indicators
  }
  
  // Extract order number patterns
  const orderInfo: { order_number?: string; order_date?: string; notes?: string } = {}
  
  // Common order number patterns - order matters (most specific first)
  const orderPatterns = [
    /order[_-]([A-Za-z0-9]+)/i,    // order_123, order-ABC123 (with separator)
    /po[_-]([A-Za-z0-9]+)/i,       // po_456, po-ABC123 (with separator)
    /products[_-]?(\d+)/i,         // DK_PRODUCTS_12345
    /dk[_-]products[_-]?(\d+)/i,   // DK_PRODUCTS_12345
    /([A-Z]{2,}\d{4,})/,           // ORD789123, ABC1234 (letter prefix with numbers - no separators)
    /(\d{8,})/                     // 8+ digit numbers as fallback
  ]
  
  for (const pattern of orderPatterns) {
    const match = filename.match(pattern)
    if (match) {
      let orderNumber = match[1]
      
      // For long digit sequences, make sure it's not actually a date
      if (/^\d{8,}$/.test(orderNumber)) {
        // Check if it looks like YYYYMMDD (would be a valid date)
        const year = parseInt(orderNumber.substring(0, 4))
        const month = parseInt(orderNumber.substring(4, 6))
        const day = parseInt(orderNumber.substring(6, 8))
        
        // If it's a reasonable date, skip this as order number
        if (year >= 1900 && year <= 2100 && month >= 1 && month <= 12 && day >= 1 && day <= 31) {
          continue
        }
      }
      
      orderInfo.order_number = orderNumber
      break
    }
  }
  
  // Extract date patterns - now check even if order number found (for files with both)
  const datePatterns = [
    /(\d{4}[-_]\d{2}[-_]\d{2})/,    // YYYY-MM-DD or YYYY_MM_DD (require separators)
    /(\d{2}[-_]\d{2}[-_]\d{4})/,    // MM-DD-YYYY or MM_DD_YYYY (require separators)
    /(\d{8})/                       // YYYYMMDD (8 digits, no separators)
  ]
  
  for (const pattern of datePatterns) {
    const match = filename.match(pattern)
    if (match) {
      let dateCandidate = match[1]
      
      // Skip if this is the same as the order number we already found
      if (dateCandidate === orderInfo.order_number) {
        continue
      }
      
      // For 8-digit sequences, validate it looks like a real date
      if (/^\d{8}$/.test(dateCandidate)) {
        const year = parseInt(dateCandidate.substring(0, 4))
        const month = parseInt(dateCandidate.substring(4, 6))
        const day = parseInt(dateCandidate.substring(6, 8))
        
        // Only accept if it's a reasonable date
        if (year >= 1900 && year <= 2100 && month >= 1 && month <= 12 && day >= 1 && day <= 31) {
          orderInfo.order_date = `${year}-${month.toString().padStart(2, '0')}-${day.toString().padStart(2, '0')}`
          break
        }
      } else {
        // For separated dates, accept them
        orderInfo.order_date = dateCandidate
        break
      }
    }
  }
  
  // Add auto-extraction note if any info was found
  if (orderInfo.order_number || orderInfo.order_date) {
    orderInfo.notes = `Auto-extracted from filename: ${filename}`
  }
  
  return {
    detected_supplier: detectedSupplier,
    file_type: fileExt.toUpperCase(),
    order_info: orderInfo,
    filename: filename
  }
}

