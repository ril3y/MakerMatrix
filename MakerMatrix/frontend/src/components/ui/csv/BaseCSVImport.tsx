import React from 'react'
import { Upload, FileText, AlertCircle, CheckCircle, Eye, RefreshCw, Trash2, X } from 'lucide-react'
import { motion, AnimatePresence } from 'framer-motion'
import toast from 'react-hot-toast'
import { apiClient } from '@/services/api'

export interface CSVPreviewData {
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

export interface ImportResult {
  success_parts: string[]
  failed_parts: string[]
  order_id?: string
}

export interface OrderInfo {
  order_number: string
  order_date: string
  notes: string
}

export interface BaseCSVImportProps {
  onImportComplete?: (result: ImportResult) => void
  parserType: string
  parserName: string
  description: string
  filePattern?: string // e.g., "LCSC_Exported_*.csv"
}

export interface ImportProgress {
  total_parts: number
  processed_parts: number
  successful_parts: number
  failed_parts: number
  current_operation: string
  is_downloading: boolean
  download_progress?: {
    current_file: string
    files_downloaded: number
    total_files: number
  }
  errors: string[]
  start_time: string
  estimated_completion?: string
  percentage_complete: number
}

export interface BaseCSVImportState {
  file: File | null
  previewData: CSVPreviewData | null
  loading: boolean
  importing: boolean
  showPreview: boolean
  orderInfo: OrderInfo
  importProgress: ImportProgress | null
}

export abstract class BaseCSVImportComponent extends React.Component<BaseCSVImportProps, BaseCSVImportState> {
  protected fileInputRef = React.createRef<HTMLInputElement>()

  constructor(props: BaseCSVImportProps) {
    super(props)
    this.state = {
      file: null,
      previewData: null,
      loading: false,
      importing: false,
      showPreview: false,
      importProgress: null,
      orderInfo: {
        order_number: '',
        order_date: new Date().toISOString().split('T')[0],
        notes: ''
      }
    }
  }

  // Abstract methods that subclasses can override
  abstract extractOrderInfoFromFilename(filename: string): Promise<Partial<OrderInfo> | null>
  abstract validateFile(file: File): boolean
  abstract renderCustomOrderFields(): React.ReactNode

  // Common utility methods
  protected async handleFileSelect(selectedFile: File) {
    if (!selectedFile) return

    if (!selectedFile.name.toLowerCase().endsWith('.csv')) {
      toast.error('Please select a CSV file')
      return
    }

    if (!this.validateFile(selectedFile)) {
      return
    }

    this.setState({ file: selectedFile, loading: true })

    // Try to extract order info from filename
    const extractedInfo = await this.extractOrderInfoFromFilename(selectedFile.name)
    if (extractedInfo) {
      this.setState(prev => ({
        orderInfo: {
          ...prev.orderInfo,
          ...extractedInfo
        }
      }))
      toast.success(`Auto-detected ${this.props.parserName} order information`)
    }

    try {
      const fileContent = await selectedFile.text()
      const data = await apiClient.post('/csv/preview', {
        csv_content: fileContent
      })

      this.setState({ previewData: data })
      
      if (data.validation_errors && data.validation_errors.length > 0) {
        toast.error(`Validation issues: ${data.validation_errors[0]}`)
      }
      
    } catch (error) {
      toast.error('Failed to parse CSV file')
      console.error('CSV preview error:', error)
    } finally {
      this.setState({ loading: false })
    }
  }

  protected handleFileChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFile = event.target.files?.[0]
    if (selectedFile) {
      this.handleFileSelect(selectedFile)
    }
  }

  protected handleDrop = (event: React.DragEvent<HTMLDivElement>) => {
    event.preventDefault()
    const droppedFile = event.dataTransfer.files[0]
    if (droppedFile) {
      this.handleFileSelect(droppedFile)
    }
  }

  protected handleDragOver = (event: React.DragEvent<HTMLDivElement>) => {
    event.preventDefault()
  }

  private progressPollingInterval: NodeJS.Timeout | null = null

  protected async handleImport() {
    const { file, previewData } = this.state
    const { parserType } = this.props

    if (!file || !previewData || !previewData.is_supported) {
      toast.error('Please select a valid CSV file')
      return
    }

    this.setState({ importing: true, importProgress: null })

    try {
      const fileContent = await file.text()
      
      // Start the import with progress tracking
      const importPromise = apiClient.post('/csv/import/with-progress', {
        csv_content: fileContent,
        parser_type: parserType,
        order_info: {
          ...this.state.orderInfo,
          supplier: previewData.type_info,
          order_date: this.state.orderInfo.order_date || new Date().toISOString()
        }
      })

      // Start polling for progress
      this.startProgressPolling()

      const result = await importPromise
      
      // Stop polling
      this.stopProgressPolling()
      
      toast.success(`Imported ${result.success_parts.length} parts successfully`)
      
      if (result.failed_parts.length > 0) {
        toast.error(`${result.failed_parts.length} parts failed to import`)
      }

      this.props.onImportComplete?.(result)
      this.clearFile()

    } catch (error) {
      this.stopProgressPolling()
      toast.error('Failed to import parts from CSV')
      console.error('CSV import error:', error)
    } finally {
      this.setState({ importing: false, importProgress: null })
    }
  }

  private startProgressPolling() {
    this.progressPollingInterval = setInterval(async () => {
      try {
        const progress = await apiClient.get('/csv/import/progress')
        this.setState({ importProgress: progress })
      } catch (error) {
        console.error('Failed to fetch import progress:', error)
      }
    }, 1000) // Poll every second
  }

  private stopProgressPolling() {
    if (this.progressPollingInterval) {
      clearInterval(this.progressPollingInterval)
      this.progressPollingInterval = null
    }
  }

  componentWillUnmount() {
    this.stopProgressPolling()
  }

  protected clearFile = () => {
    this.setState({
      file: null,
      previewData: null,
      showPreview: false,
      importProgress: null,
      orderInfo: {
        order_number: '',
        order_date: new Date().toISOString().split('T')[0],
        notes: ''
      }
    })
    if (this.fileInputRef.current) {
      this.fileInputRef.current.value = ''
    }
  }

  protected updateOrderInfo = (updates: Partial<OrderInfo>) => {
    this.setState(prev => ({
      orderInfo: { ...prev.orderInfo, ...updates }
    }))
  }

  // Common render methods
  protected renderProgressBar() {
    const { importing, importProgress } = this.state

    if (!importing || !importProgress) {
      return null
    }

    return (
      <div className="bg-gray-800/50 border border-gray-700 rounded-lg p-6 space-y-4">
        <div className="flex items-center justify-between">
          <h3 className="text-lg font-semibold text-white">Importing Parts</h3>
          <div className="text-sm text-gray-300">
            {importProgress.processed_parts} / {importProgress.total_parts} parts
          </div>
        </div>

        {/* Main progress bar */}
        <div className="w-full bg-gray-700 rounded-full h-2">
          <div
            className="bg-blue-500 h-2 rounded-full transition-all duration-300"
            style={{ width: `${importProgress.percentage_complete}%` }}
          />
        </div>

        <div className="flex justify-between text-sm text-gray-400">
          <span>{importProgress.percentage_complete.toFixed(1)}% complete</span>
          <span>
            ✓ {importProgress.successful_parts} | ✗ {importProgress.failed_parts}
          </span>
        </div>

        {/* Current operation */}
        <div className="text-sm text-gray-300">
          <strong>Status:</strong> {importProgress.current_operation}
        </div>

        {/* Download progress (if downloading) */}
        {importProgress.is_downloading && importProgress.download_progress && (
          <div className="border-t border-gray-600 pt-3">
            <div className="flex items-center gap-2 text-sm text-blue-400 mb-2">
              <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-blue-400"></div>
              <span>Downloading datasheets and images...</span>
            </div>
            <div className="text-xs text-gray-400">
              Current: {importProgress.download_progress.current_file}
            </div>
            <div className="text-xs text-gray-400">
              Files: {importProgress.download_progress.files_downloaded} / {importProgress.download_progress.total_files}
            </div>
          </div>
        )}

        {/* Errors */}
        {importProgress.errors.length > 0 && (
          <div className="border-t border-red-600/30 pt-3">
            <details className="text-sm">
              <summary className="text-red-400 cursor-pointer">
                {importProgress.errors.length} error(s) occurred
              </summary>
              <ul className="mt-2 text-red-300 text-xs max-h-20 overflow-y-auto">
                {importProgress.errors.slice(-5).map((error, index) => (
                  <li key={index}>• {error}</li>
                ))}
              </ul>
            </details>
          </div>
        )}

        {/* Estimated completion */}
        {importProgress.estimated_completion && (
          <div className="text-xs text-gray-500">
            Estimated completion: {new Date(importProgress.estimated_completion).toLocaleTimeString()}
          </div>
        )}
      </div>
    )
  }

  protected renderFileUpload() {
    const { file, previewData } = this.state
    const { parserName, description, filePattern } = this.props

    return (
      <div
        className={`border-2 border-dashed rounded-lg p-8 text-center transition-colors ${
          file ? 'border-accent bg-accent/10' : 'border-border-secondary hover:border-primary'
        }`}
        onDrop={this.handleDrop}
        onDragOver={this.handleDragOver}
      >
        <input
          ref={this.fileInputRef}
          type="file"
          accept=".csv"
          onChange={this.handleFileChange}
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
              onClick={this.clearFile}
              className="btn btn-secondary btn-sm mt-2"
            >
              <X className="w-4 h-4 mr-1" />
              Clear
            </button>
          </div>
        ) : (
          <div className="space-y-2">
            <Upload className="w-8 h-8 text-text-muted mx-auto" />
            <p className="text-text-primary font-medium">Drop {parserName} CSV file here or click to browse</p>
            <p className="text-sm text-text-secondary">{description}</p>
            {filePattern && (
              <p className="text-xs text-text-muted">Expected format: {filePattern}</p>
            )}
            <button
              onClick={() => this.fileInputRef.current?.click()}
              className="btn btn-primary mt-2"
            >
              Select File
            </button>
          </div>
        )}
      </div>
    )
  }

  protected renderPreviewData() {
    const { previewData, showPreview } = this.state

    if (!previewData) return null

    return (
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
                            {part.additional_properties?.description || '-'}
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
    )
  }

  abstract render(): React.ReactNode
}