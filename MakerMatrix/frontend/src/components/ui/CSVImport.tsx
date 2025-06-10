import React, { useState, useRef, useCallback, useEffect } from 'react'
import { Upload, FileText, AlertCircle, CheckCircle, Eye, RefreshCw, Trash2, X } from 'lucide-react'
import { motion, AnimatePresence } from 'framer-motion'
import toast from 'react-hot-toast'
import { apiClient } from '@/services/api'

interface CSVPreviewData {
  detected_type: string | null
  type_info: string
  headers: string[]
  preview_rows: any[]
  parsed_preview: any[]
  total_rows: number
  is_supported: boolean
  validation_errors: string[]
  error?: string
}

interface ImportResult {
  success_parts: string[]
  failed_parts: string[]
  order_id?: string
}

interface OrderInfo {
  order_number: string
  order_date: string
  notes: string
}

interface SupportedParser {
  type: string
  name: string
  description: string
  required_columns: string[]
  sample_columns: string[]
}

interface CSVImportProps {
  onImportComplete?: (result: ImportResult) => void
}

const CSVImport: React.FC<CSVImportProps> = ({ onImportComplete }) => {
  const [file, setFile] = useState<File | null>(null)
  const [previewData, setPreviewData] = useState<CSVPreviewData | null>(null)
  const [selectedParser, setSelectedParser] = useState<string>('')
  const [supportedParsers, setSupportedParsers] = useState<SupportedParser[]>([])
  const [loading, setLoading] = useState(false)
  const [importing, setImporting] = useState(false)
  const [showPreview, setShowPreview] = useState(false)
  const [orderInfo, setOrderInfo] = useState<OrderInfo>({
    order_number: '',
    order_date: new Date().toISOString().split('T')[0],
    notes: ''
  })
  const fileInputRef = useRef<HTMLInputElement>(null)

  // Load supported parsers on component mount
  useEffect(() => {
    loadSupportedParsers()
  }, [])

  const loadSupportedParsers = async () => {
    try {
      const response = await apiClient.get('/api/csv/supported-types')
      setSupportedParsers(response.supported_types || [])
    } catch (error) {
      console.error('Failed to load supported CSV parsers:', error)
    }
  }

  const extractOrderInfoFromFilename = async (filename: string) => {
    try {
      const response = await apiClient.post('/api/csv/extract-filename-info', {
        filename: filename
      })
      
      if (response.success && response.order_info) {
        return response.order_info
      }
      
      return null
    } catch (error) {
      console.log('No filename pattern matched for:', filename)
      return null
    }
  }

  const handleFileSelect = useCallback(async (selectedFile: File) => {
    if (!selectedFile) return

    if (!selectedFile.name.toLowerCase().endsWith('.csv')) {
      toast.error('Please select a CSV file')
      return
    }

    setFile(selectedFile)
    setLoading(true)

    // Try to extract order info from filename
    const extractedInfo = await extractOrderInfoFromFilename(selectedFile.name)
    if (extractedInfo) {
      setOrderInfo(prev => ({
        ...prev,
        order_date: extractedInfo.order_date,
        order_number: extractedInfo.order_number
      }))
      toast.success(`Auto-detected: ${extractedInfo.supplier} order from ${extractedInfo.order_date}`)
    }

    try {
      const fileContent = await selectedFile.text()
      const data = await apiClient.post('/api/csv/preview', {
        csv_content: fileContent
      })

      setPreviewData(data)
      
      // Auto-select detected type
      if (data.detected_type) {
        setSelectedParser(data.detected_type)
      }
      
      if (data.validation_errors && data.validation_errors.length > 0) {
        toast.error(`Validation issues: ${data.validation_errors[0]}`)
      }
      
    } catch (error) {
      toast.error('Failed to parse CSV file')
      console.error('CSV preview error:', error)
    } finally {
      setLoading(false)
    }
  }, [])

  const handleFileChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFile = event.target.files?.[0]
    if (selectedFile) {
      handleFileSelect(selectedFile)
    }
  }

  const handleDrop = useCallback((event: React.DragEvent<HTMLDivElement>) => {
    event.preventDefault()
    const droppedFile = event.dataTransfer.files[0]
    if (droppedFile) {
      handleFileSelect(droppedFile)
    }
  }, [handleFileSelect])

  const handleDragOver = (event: React.DragEvent<HTMLDivElement>) => {
    event.preventDefault()
  }

  const handleImport = async () => {
    if (!file || !previewData || !selectedParser) {
      toast.error('Please select a valid CSV file and parser type')
      return
    }

    setImporting(true)

    try {
      const fileContent = await file.text()
      const result = await apiClient.post('/api/csv/import', {
        csv_content: fileContent,
        parser_type: selectedParser,
        order_info: {
          ...orderInfo,
          supplier: previewData.type_info,
          order_date: orderInfo.order_date || new Date().toISOString()
        }
      })
      
      toast.success(`Imported ${result.success_parts.length} parts successfully`)
      
      if (result.failed_parts.length > 0) {
        toast.error(`${result.failed_parts.length} parts failed to import`)
      }

      onImportComplete?.(result)

      // Reset form
      clearFile()

    } catch (error) {
      toast.error('Failed to import parts from CSV')
      console.error('CSV import error:', error)
    } finally {
      setImporting(false)
    }
  }

  const clearFile = () => {
    setFile(null)
    setPreviewData(null)
    setSelectedParser('')
    setShowPreview(false)
    setOrderInfo({
      order_number: '',
      order_date: new Date().toISOString().split('T')[0],
      notes: ''
    })
    if (fileInputRef.current) {
      fileInputRef.current.value = ''
    }
  }

  return (
    <div className="space-y-6">
      <div className="text-center">
        <h3 className="text-lg font-semibold text-text-primary mb-2 flex items-center justify-center gap-2">
          <Upload className="w-5 h-5" />
          Import Parts from CSV Orders
        </h3>
        <p className="text-text-secondary">
          Upload order CSV files to automatically add parts to your inventory with order tracking
        </p>
      </div>

      {/* File Upload */}
      <div
        className={`border-2 border-dashed rounded-lg p-8 text-center transition-colors ${
          file ? 'border-accent bg-accent/10' : 'border-border-secondary hover:border-primary'
        }`}
        onDrop={handleDrop}
        onDragOver={handleDragOver}
      >
        <input
          ref={fileInputRef}
          type="file"
          accept=".csv"
          onChange={handleFileChange}
          className="hidden"
        />

        {file ? (
          <div className="space-y-2">
            <CheckCircle className="w-8 h-8 text-accent mx-auto" />
            <p className="text-text-primary font-medium">{file.name}</p>
            <p className="text-sm text-text-secondary">
              {(file.size / 1024).toFixed(1)} KB • {previewData?.total_rows || 0} rows
            </p>
            <button
              onClick={clearFile}
              className="btn btn-secondary btn-sm mt-2"
            >
              <X className="w-4 h-4 mr-1" />
              Clear
            </button>
          </div>
        ) : (
          <div className="space-y-2">
            <Upload className="w-8 h-8 text-text-muted mx-auto" />
            <p className="text-text-primary font-medium">Drop CSV file here or click to browse</p>
            <p className="text-sm text-text-secondary">
              Supports: {supportedParsers.map(p => p.name).join(', ')} order files
            </p>
            <button
              onClick={() => fileInputRef.current?.click()}
              className="btn btn-primary mt-2"
            >
              Select CSV File
            </button>
          </div>
        )}
      </div>

      {/* Loading State */}
      {loading && (
        <div className="text-center py-4">
          <RefreshCw className="w-6 h-6 animate-spin mx-auto text-primary" />
          <p className="text-text-secondary mt-2">Analyzing CSV file...</p>
        </div>
      )}

      {/* Preview and Configuration */}
      <AnimatePresence>
        {previewData && !loading && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -20 }}
            className="space-y-4"
          >
            {/* Detection Results */}
            <div className="card p-4">
              <div className="flex items-center justify-between mb-4">
                <h4 className="font-medium text-text-primary">File Analysis</h4>
                <div className="flex items-center gap-2">
                  {previewData.is_supported ? (
                    <span className="flex items-center gap-1 text-accent">
                      <CheckCircle className="w-4 h-4" />
                      Supported Format
                    </span>
                  ) : (
                    <span className="flex items-center gap-1 text-destructive">
                      <AlertCircle className="w-4 h-4" />
                      Unsupported Format
                    </span>
                  )}
                </div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-text-primary mb-2">
                    CSV Parser Type
                  </label>
                  <select
                    className="input w-full"
                    value={selectedParser}
                    onChange={(e) => setSelectedParser(e.target.value)}
                  >
                    <option value="">Select parser type...</option>
                    {supportedParsers.map((parser) => (
                      <option key={parser.type} value={parser.type}>
                        {parser.name} - {parser.description}
                      </option>
                    ))}
                  </select>
                  {previewData.detected_type && (
                    <p className="text-xs text-text-secondary mt-1">
                      Auto-detected: {previewData.type_info}
                    </p>
                  )}
                </div>

                <div>
                  <label className="block text-sm font-medium text-text-primary mb-2">
                    File Information
                  </label>
                  <div className="text-sm text-text-secondary space-y-1">
                    <p><strong>Rows:</strong> {previewData.total_rows}</p>
                    <p><strong>Columns:</strong> {previewData.headers.length}</p>
                  </div>
                </div>
              </div>

              {previewData.validation_errors && previewData.validation_errors.length > 0 && (
                <div className="mt-4 p-3 bg-destructive/10 border border-destructive/20 rounded">
                  <div className="flex items-start gap-2">
                    <AlertCircle className="w-4 h-4 text-destructive mt-0.5" />
                    <div>
                      <p className="text-sm font-medium text-destructive">Validation Issues:</p>
                      <ul className="text-sm text-destructive/80 mt-1">
                        {previewData.validation_errors.map((error, index) => (
                          <li key={index}>• {error}</li>
                        ))}
                      </ul>
                    </div>
                  </div>
                </div>
              )}
            </div>

            {/* Order Information */}
            <div className="card p-4">
              <h4 className="font-medium text-text-primary mb-4">Order Information</h4>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-text-primary mb-2">
                    Order Number
                    {orderInfo.order_number && (
                      <span className="ml-2 text-xs text-accent">✓ Auto-detected</span>
                    )}
                  </label>
                  <input
                    type="text"
                    className="input w-full"
                    value={orderInfo.order_number}
                    onChange={(e) => setOrderInfo({...orderInfo, order_number: e.target.value})}
                    placeholder="Optional order number"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-text-primary mb-2">
                    Order Date
                    {orderInfo.order_date && orderInfo.order_date !== new Date().toISOString().split('T')[0] && (
                      <span className="ml-2 text-xs text-accent">✓ Auto-detected</span>
                    )}
                  </label>
                  <input
                    type="date"
                    className="input w-full cursor-pointer"
                    value={orderInfo.order_date}
                    onChange={(e) => setOrderInfo({...orderInfo, order_date: e.target.value})}
                    placeholder="Select order date"
                    onClick={(e) => e.currentTarget.showPicker?.()}
                  />
                </div>
                <div className="md:col-span-2">
                  <label className="block text-sm font-medium text-text-primary mb-2">
                    Notes
                  </label>
                  <textarea
                    className="input w-full h-20 resize-none"
                    value={orderInfo.notes}
                    onChange={(e) => setOrderInfo({...orderInfo, notes: e.target.value})}
                    placeholder="Optional notes about this order"
                  />
                </div>
              </div>
            </div>

            {/* Preview Toggle */}
            <div className="flex items-center justify-between">
              <button
                onClick={() => setShowPreview(!showPreview)}
                className="btn btn-secondary flex items-center gap-2"
              >
                <Eye className="w-4 h-4" />
                {showPreview ? 'Hide Preview' : 'Show Preview'}
              </button>

              <div className="flex gap-2">
                <button
                  onClick={clearFile}
                  className="btn btn-secondary flex items-center gap-2"
                >
                  <Trash2 className="w-4 h-4" />
                  Clear
                </button>
                <button
                  onClick={handleImport}
                  disabled={!selectedParser || importing || !previewData.is_supported}
                  className="btn btn-primary flex items-center gap-2"
                >
                  {importing ? (
                    <RefreshCw className="w-4 h-4 animate-spin" />
                  ) : (
                    <Upload className="w-4 h-4" />
                  )}
                  {importing ? 'Importing...' : 'Import Parts'}
                </button>
              </div>
            </div>

            {/* Data Preview */}
            <AnimatePresence>
              {showPreview && (
                <motion.div
                  initial={{ opacity: 0, height: 0 }}
                  animate={{ opacity: 1, height: 'auto' }}
                  exit={{ opacity: 0, height: 0 }}
                  className="card p-4"
                >
                  <div className="flex items-center justify-between mb-4">
                    <h4 className="font-medium text-text-primary">Data Preview</h4>
                    <span className="text-sm text-text-secondary">
                      Showing {Math.min(previewData.preview_rows.length, 5)} of {previewData.total_rows} rows
                    </span>
                  </div>

                  {/* Raw Data Table */}
                  <div className="mb-6">
                    <h5 className="text-sm font-medium text-text-primary mb-2">Raw CSV Data</h5>
                    <div className="overflow-x-auto border border-border-primary rounded-md">
                      <table className="table">
                        <thead className="table-header">
                          <tr>
                            {previewData.headers.map((header, index) => (
                              <th key={index} className="table-head">
                                {header}
                              </th>
                            ))}
                          </tr>
                        </thead>
                        <tbody className="table-body">
                          {previewData.preview_rows.slice(0, 5).map((row, index) => (
                            <tr key={index} className="table-row">
                              {previewData.headers.map((header, colIndex) => (
                                <td key={colIndex} className="table-cell text-text-primary">
                                  {row[header] || '-'}
                                </td>
                              ))}
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>

                  {/* Parsed Data Table */}
                  {previewData.parsed_preview.length > 0 && (
                    <div>
                      <h5 className="text-sm font-medium text-text-primary mb-2">Parsed Parts Data</h5>
                      <div className="overflow-x-auto border border-border-primary rounded-md">
                        <table className="table">
                          <thead className="table-header">
                            <tr>
                              <th className="table-head">Part Name</th>
                              <th className="table-head">Part Number</th>
                              <th className="table-head">Quantity</th>
                              <th className="table-head">Supplier</th>
                              <th className="table-head">Description</th>
                            </tr>
                          </thead>
                          <tbody className="table-body">
                            {previewData.parsed_preview.slice(0, 5).map((part, index) => (
                              <tr key={index} className="table-row">
                                <td className="table-cell text-text-primary">{part.name}</td>
                                <td className="table-cell text-text-primary">{part.part_number}</td>
                                <td className="table-cell text-text-primary">{part.quantity}</td>
                                <td className="table-cell text-text-primary">{part.supplier}</td>
                                <td className="table-cell text-text-primary truncate max-w-48">
                                  {part.properties?.description || '-'}
                                </td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    </div>
                  )}
                </motion.div>
              )}
            </AnimatePresence>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}

export default CSVImport