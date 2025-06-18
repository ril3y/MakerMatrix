import React, { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import { Upload, RefreshCw, AlertCircle, Package, FileText, Zap } from 'lucide-react'
import toast from 'react-hot-toast'
import { ImportResult } from './hooks/useOrderImport'
import { apiClient } from '@/services/api'
import CSVEnrichmentProgressModal from './CSVEnrichmentProgressModal'

interface UnifiedFileImporterProps {
  uploadedFile: File
  filePreview: any
  parserType: string
  parserName: string
  description: string
  onImportComplete?: (result: ImportResult) => void
}

interface OrderInfo {
  order_number?: string
  order_date?: string
  notes?: string
}

// Function to extract order info from filename using API
const extractOrderInfoFromFilename = async (filename: string, parserType: string): Promise<Partial<OrderInfo>> => {
  try {
    const response = await apiClient.post('/api/csv/extract-filename-info', {
      filename: filename,
      parser_type: parserType
    })
    
    if (response.status === 'success' && response.data) {
      return {
        order_date: response.data.order_date,
        order_number: response.data.order_number,
        notes: response.data.notes || `Auto-extracted from filename: ${filename}`
      }
    }
  } catch (error) {
    console.warn('Failed to extract order info from filename:', error)
  }
  
  return {}
}

const UnifiedFileImporter: React.FC<UnifiedFileImporterProps> = ({
  uploadedFile,
  filePreview,
  parserType,
  parserName,
  description,
  onImportComplete
}) => {
  const [isImporting, setIsImporting] = useState(false)
  const [importProgress, setImportProgress] = useState(0)
  const [orderInfo, setOrderInfo] = useState<OrderInfo>({
    order_number: '',
    order_date: new Date().toISOString().split('T')[0],
    notes: ''
  })
  const [showPreview, setShowPreview] = useState(false)
  const [showEnrichmentModal, setShowEnrichmentModal] = useState(false)
  const [enrichmentTaskId, setEnrichmentTaskId] = useState<string | null>(null)
  const [importedPartsCount, setImportedPartsCount] = useState(0)

  // Auto-extract order info from filename when component mounts or file changes
  useEffect(() => {
    const extractInfo = async () => {
      if (uploadedFile && parserType) {
        const extractedInfo = await extractOrderInfoFromFilename(uploadedFile.name, parserType)
        if (Object.keys(extractedInfo).length > 0) {
          setOrderInfo(prev => ({
            // Only override if the field is empty
            order_number: prev.order_number || extractedInfo.order_number || '',
            order_date: prev.order_date === new Date().toISOString().split('T')[0] ? 
              (extractedInfo.order_date || prev.order_date) : prev.order_date,
            notes: prev.notes || extractedInfo.notes || ''
          }))
          
          // Show a toast notification
          if (extractedInfo.order_date && extractedInfo.order_number) {
            toast.success(`Auto-extracted order info: ${extractedInfo.order_date} (${extractedInfo.order_number})`)
          } else if (extractedInfo.order_number) {
            toast.success(`Auto-extracted order number: ${extractedInfo.order_number}`)
          }
        }
      }
    }
    
    extractInfo()
  }, [uploadedFile, parserType])

  const handleImport = async () => {
    if (!uploadedFile) {
      toast.error('No file uploaded')
      return
    }

    setIsImporting(true)
    setImportProgress(0)

    try {
      const formData = new FormData()
      formData.append('file', uploadedFile)
      formData.append('parser_type', parserType)
      if (orderInfo.order_number) formData.append('order_number', orderInfo.order_number)
      if (orderInfo.order_date) formData.append('order_date', orderInfo.order_date)
      if (orderInfo.notes) formData.append('notes', orderInfo.notes)

      setImportProgress(25)

      const result = await apiClient.post('/api/csv/import-file', formData, {
        headers: {
          'Content-Type': 'multipart/form-data'
        }
      })

      setImportProgress(100)

      if (result.status === 'success') {
        const importResult: ImportResult = {
          success_parts: result.data.imported_parts || [],
          failed_parts: result.data.failures || []
        }

        const successfulImports = result.data.successful_imports || 0
        setImportedPartsCount(successfulImports)
        
        // Debug logging
        console.log('CSV Import Result:', result.data)
        console.log('Enrichment Task ID:', result.data.enrichment_task_id)
        console.log('Has enrichment_task_id:', !!result.data.enrichment_task_id)
        
        // Check if enrichment task was created
        if (result.data.enrichment_task_id) {
          console.log('Setting enrichment task ID:', result.data.enrichment_task_id)
          setEnrichmentTaskId(result.data.enrichment_task_id)
          console.log('Setting showEnrichmentModal to true')
          setShowEnrichmentModal(true)
          toast.success(`Import completed: ${successfulImports} parts imported. Starting enrichment...`)
        } else {
          toast.success(`Import completed: ${successfulImports} parts imported successfully`)
        }
        
        onImportComplete?.(importResult)
      } else {
        throw new Error(result.message || 'Import failed')
      }
    } catch (error) {
      console.error('Import error:', error)
      toast.error(error instanceof Error ? error.message : 'Import failed')
    } finally {
      setIsImporting(false)
      setImportProgress(0)
    }
  }

  return (
    <div className="card p-6 space-y-6">
      <div className="text-center">
        <h4 className="text-lg font-semibold text-primary mb-2 flex items-center justify-center gap-2">
          <Package className="w-5 h-5" />
          Import from {parserName}
        </h4>
        <p className="text-secondary">{description}</p>
      </div>

      {/* File Information */}
      <div className="bg-background-secondary rounded-lg p-4">
        <div className="flex items-center gap-3 mb-4">
          <FileText className="w-8 h-8 text-primary" />
          <div>
            <h5 className="font-medium text-primary">{uploadedFile.name}</h5>
            <p className="text-sm text-secondary">
              {(uploadedFile.size / 1024).toFixed(1)} KB • {filePreview?.total_rows || 0} rows
            </p>
          </div>
        </div>

        {filePreview && (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
            <div>
              <span className="text-secondary">Format:</span>
              <span className="text-primary ml-2 font-medium">
                {filePreview.file_format?.toUpperCase() || 'Unknown'}
              </span>
            </div>
            <div>
              <span className="text-secondary">Parser:</span>
              <span className="text-primary ml-2 font-medium">{parserName}</span>
            </div>
            <div>
              <span className="text-secondary">Supported:</span>
              <span className={`ml-2 font-medium ${filePreview.is_supported ? 'text-success' : 'text-error'}`}>
                {filePreview.is_supported ? 'Yes' : 'No'}
              </span>
            </div>
            <div>
              <button
                onClick={() => setShowPreview(!showPreview)}
                className="text-primary hover:text-primary-dark font-medium text-sm"
              >
                {showPreview ? 'Hide' : 'Show'} Preview
              </button>
            </div>
          </div>
        )}

        {/* Preview Data */}
        {showPreview && filePreview?.preview_rows && (
          <div className="mt-4 overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border">
                  {filePreview.headers.slice(0, 5).map((header: string, index: number) => (
                    <th key={index} className="text-left p-2 text-secondary font-medium">
                      {header}
                    </th>
                  ))}
                  {filePreview.headers.length > 5 && (
                    <th className="text-left p-2 text-secondary font-medium">...</th>
                  )}
                </tr>
              </thead>
              <tbody>
                {filePreview.preview_rows.slice(0, 3).map((row: any, rowIndex: number) => (
                  <tr key={rowIndex} className="border-b border-border">
                    {filePreview.headers.slice(0, 5).map((header: string, cellIndex: number) => (
                      <td key={cellIndex} className="p-2 text-primary">
                        {String(row[header] || '').slice(0, 30)}
                        {String(row[header] || '').length > 30 ? '...' : ''}
                      </td>
                    ))}
                    {filePreview.headers.length > 5 && (
                      <td className="p-2 text-secondary">...</td>
                    )}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Order Information */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <h5 className="font-medium text-primary">Order Information (Optional)</h5>
          {((parserType === 'lcsc' && uploadedFile?.name.match(/^LCSC_Exported__\d{8}_\d{6}\.csv$/i)) ||
            (parserType === 'digikey' && uploadedFile?.name.match(/^DK_PRODUCTS_\d+\.csv$/i)) ||
            (parserType === 'mouser' && uploadedFile?.name.match(/^\d+\.xls$/i))) && (
            <span className="text-xs bg-success/10 text-success px-2 py-1 rounded-full">
              Auto-extracted from filename
            </span>
          )}
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-primary mb-1">
              Order Number
            </label>
            <input
              type="text"
              className="input w-full"
              value={orderInfo.order_number}
              onChange={(e) => setOrderInfo(prev => ({ ...prev, order_number: e.target.value }))}
              placeholder="e.g., ORD-2024-001"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-primary mb-1">
              Order Date
            </label>
            <input
              type="date"
              className="input w-full"
              value={orderInfo.order_date}
              onChange={(e) => setOrderInfo(prev => ({ ...prev, order_date: e.target.value }))}
            />
          </div>
        </div>
        <div>
          <label className="block text-sm font-medium text-primary mb-1">
            Notes
          </label>
          <textarea
            className="input w-full h-20 resize-none"
            value={orderInfo.notes}
            onChange={(e) => setOrderInfo(prev => ({ ...prev, notes: e.target.value }))}
            placeholder="Any additional notes about this import..."
          />
        </div>
      </div>

      {/* Import Progress */}
      {isImporting && (
        <div className="bg-background-secondary rounded-lg p-4">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm font-medium text-primary">Importing...</span>
            <span className="text-sm text-secondary">{importProgress}%</span>
          </div>
          <div className="w-full bg-background-tertiary rounded-full h-2">
            <motion.div
              className="bg-primary h-2 rounded-full"
              initial={{ width: 0 }}
              animate={{ width: `${importProgress}%` }}
              transition={{ duration: 0.3 }}
            />
          </div>
        </div>
      )}

      {/* Validation Errors */}
      {filePreview?.validation_errors && filePreview.validation_errors.length > 0 && (
        <div className="bg-warning/10 border border-warning/20 rounded-lg p-4">
          <div className="flex items-start gap-2">
            <AlertCircle className="w-5 h-5 text-warning mt-0.5" />
            <div>
              <h6 className="font-medium text-warning mb-1">Validation Warnings</h6>
              <ul className="text-sm text-warning space-y-1">
                {filePreview.validation_errors.map((error: string, index: number) => (
                  <li key={index}>• {error}</li>
                ))}
              </ul>
              <p className="text-xs text-warning/80 mt-2">
                These issues may affect import quality but won't prevent the import.
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Import Button */}
      <div className="flex gap-4">
        <button
          onClick={handleImport}
          disabled={isImporting || !filePreview?.is_supported}
          className="btn btn-primary flex-1 flex items-center justify-center gap-2"
        >
          {isImporting ? (
            <>
              <RefreshCw className="w-4 h-4 animate-spin" />
              Importing...
            </>
          ) : (
            <>
              <Upload className="w-4 h-4" />
              Import Parts
            </>
          )}
        </button>
      </div>

      {!filePreview?.is_supported && (
        <div className="bg-error/10 border border-error/20 rounded-lg p-4">
          <div className="flex items-center gap-2">
            <AlertCircle className="w-5 h-5 text-error" />
            <div>
              <h6 className="font-medium text-error">File Not Supported</h6>
              <p className="text-sm text-error mt-1">
                This file format is not supported by the {parserName} parser. 
                Please check the file format or try a different parser.
              </p>
            </div>
          </div>
        </div>
      )}
      
      {/* CSV Enrichment Progress Modal */}
      <CSVEnrichmentProgressModal
        isOpen={showEnrichmentModal}
        onClose={() => setShowEnrichmentModal(false)}
        enrichmentTaskId={enrichmentTaskId || undefined}
        importedPartsCount={importedPartsCount}
        fileName={uploadedFile?.name || 'Unknown'}
      />
    </div>
  )
}

export default UnifiedFileImporter