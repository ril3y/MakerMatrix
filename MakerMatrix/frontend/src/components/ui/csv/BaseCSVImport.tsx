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

export interface BaseCSVImportState {
  file: File | null
  previewData: CSVPreviewData | null
  loading: boolean
  importing: boolean
  showPreview: boolean
  orderInfo: OrderInfo
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
      const data = await apiClient.post('/api/csv/preview', {
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

  protected async handleImport() {
    const { file, previewData } = this.state
    const { parserType } = this.props

    if (!file || !previewData || !previewData.is_supported) {
      toast.error('Please select a valid CSV file')
      return
    }

    this.setState({ importing: true })

    try {
      const fileContent = await file.text()
      const result = await apiClient.post('/api/csv/import', {
        csv_content: fileContent,
        parser_type: parserType,
        order_info: {
          ...this.state.orderInfo,
          supplier: previewData.type_info,
          order_date: this.state.orderInfo.order_date || new Date().toISOString()
        }
      })
      
      toast.success(`Imported ${result.success_parts.length} parts successfully`)
      
      if (result.failed_parts.length > 0) {
        toast.error(`${result.failed_parts.length} parts failed to import`)
      }

      this.props.onImportComplete?.(result)
      this.clearFile()

    } catch (error) {
      toast.error('Failed to import parts from CSV')
      console.error('CSV import error:', error)
    } finally {
      this.setState({ importing: false })
    }
  }

  protected clearFile = () => {
    this.setState({
      file: null,
      previewData: null,
      showPreview: false,
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
    )
  }

  abstract render(): React.ReactNode
}