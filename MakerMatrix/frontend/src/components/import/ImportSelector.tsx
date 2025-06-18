import React, { useState, useCallback, useRef, useEffect } from 'react'
import { motion } from 'framer-motion'
import { FileText, ChevronDown, Upload, CheckCircle, AlertCircle, File, X } from 'lucide-react'
import UnifiedFileImporter from './UnifiedFileImporter'
import ImportSettings from './ImportSettings'
import { ImportResult } from './hooks/useOrderImport'
import { apiClient } from '@/services/api'
import toast from 'react-hot-toast'

interface ImportSelectorProps {
  onImportComplete?: (result: ImportResult) => void
}

interface FilePreviewData {
  detected_parser: string | null
  preview_rows: any[]
  headers: string[]
  total_rows: number
  is_supported: boolean
  validation_errors: string[]
  file_format: string
}

const ImportSelector: React.FC<ImportSelectorProps> = ({ onImportComplete }) => {
  const [selectedParser, setSelectedParser] = useState<string>('')
  const [detectedParser, setDetectedParser] = useState<string>('')
  const [autoDetected, setAutoDetected] = useState<boolean>(false)
  const [dragActive, setDragActive] = useState<boolean>(false)
  const [uploadedFile, setUploadedFile] = useState<File | null>(null)
  const [filePreview, setFilePreview] = useState<FilePreviewData | null>(null)
  const [isProcessing, setIsProcessing] = useState<boolean>(false)
  const [parsers, setParsers] = useState<any[]>([])
  const [isLoadingParsers, setIsLoadingParsers] = useState<boolean>(true)
  const fileInputRef = useRef<HTMLInputElement>(null)

  // Load available suppliers dynamically from API
  useEffect(() => {
    const loadAvailableSuppliers = async () => {
      try {
        setIsLoadingParsers(true)
        const response = await apiClient.get('/api/csv/available-suppliers')
        if (response.status === 'success') {
          setParsers(response.data)
        } else {
          console.error('Failed to load suppliers:', response.message)
          toast.error('Failed to load available suppliers')
        }
      } catch (error) {
        console.error('Error loading suppliers:', error)
        toast.error('Error loading available suppliers')
        // Fallback to hardcoded suppliers
        setParsers([
          { 
            id: 'lcsc', 
            name: 'LCSC Electronics', 
            description: 'Chinese electronics distributor (CSV)',
            color: 'bg-blue-500',
            supported: true
          },
          { 
            id: 'digikey', 
            name: 'DigiKey', 
            description: 'Major electronics distributor (CSV)',
            color: 'bg-red-500',
            supported: true
          },
          { 
            id: 'mouser', 
            name: 'Mouser Electronics', 
            description: 'Global electronics distributor (XLS format)',
            color: 'bg-green-500',
            supported: true
          }
        ])
      } finally {
        setIsLoadingParsers(false)
      }
    }

    loadAvailableSuppliers()
  }, [])

  const selectedParserInfo = parsers.find(p => p.id === selectedParser)

  // File upload functions
  const handleFileSelect = async (file: File) => {
    if (!file) return

    const fileExtension = file.name.toLowerCase().split('.').pop()
    const allowedExtensions = ['csv', 'xls', 'xlsx']

    if (!allowedExtensions.includes(fileExtension || '')) {
      toast.error('Please upload a CSV or XLS file')
      return
    }

    setIsProcessing(true)
    setUploadedFile(file)

    try {
      const formData = new FormData()
      formData.append('file', file)

      const result = await apiClient.post('/api/csv/preview-file', formData, {
        headers: {
          'Content-Type': 'multipart/form-data'
        }
      })
      
      if (result.status === 'success') {
        setFilePreview(result.data)
        setDetectedParser(result.data.detected_parser || '')
        setSelectedParser(result.data.detected_parser || '')
        setAutoDetected(!!result.data.detected_parser)
        
        if (result.data.detected_parser) {
          toast.success(`Auto-detected: ${parsers.find(p => p.id === result.data.detected_parser)?.name || result.data.detected_parser}`)
        } else {
          toast('File uploaded successfully, please select a parser type')
        }
      } else {
        throw new Error(result.message || 'Failed to preview file')
      }
    } catch (error) {
      console.error('File preview error:', error)
      toast.error(error instanceof Error ? error.message : 'Error processing file')
      setUploadedFile(null)
      setFilePreview(null)
    } finally {
      setIsProcessing(false)
    }
  }

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setDragActive(false)
    
    const files = Array.from(e.dataTransfer.files)
    if (files.length > 0) {
      handleFileSelect(files[0])
    }
  }, [])

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setDragActive(true)
  }, [])

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setDragActive(false)
  }, [])

  const clearFile = () => {
    setUploadedFile(null)
    setFilePreview(null)
    setSelectedParser('')
    setDetectedParser('')
    setAutoDetected(false)
    if (fileInputRef.current) {
      fileInputRef.current.value = ''
    }
  }

  return (
    <div className="space-y-6">
      <div className="text-center">
        <h3 className="text-lg font-semibold text-primary mb-2 flex items-center justify-center gap-2">
          <FileText className="w-5 h-5" />
          Import Parts from Order Files
        </h3>
        <p className="text-secondary">
          Upload your order files (CSV or XLS) below. We'll automatically detect the supplier and format.
        </p>
      </div>

      {/* File Upload Area */}
      <div className="card p-6">
        <div 
          className={`border-2 border-dashed rounded-lg p-8 transition-all cursor-pointer ${
            dragActive 
              ? 'border-primary bg-primary/5' 
              : uploadedFile 
              ? 'border-success bg-success/5' 
              : 'border-border hover:border-primary/50 hover:bg-primary/5'
          }`}
          onDrop={handleDrop}
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onClick={() => !uploadedFile && fileInputRef.current?.click()}
        >
          <input
            ref={fileInputRef}
            type="file"
            className="hidden"
            accept=".csv,.xls,.xlsx"
            onChange={(e) => {
              const file = e.target.files?.[0]
              if (file) handleFileSelect(file)
            }}
          />

          <div className="text-center">
            {isProcessing ? (
              <div className="flex flex-col items-center gap-4">
                <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary"></div>
                <p className="text-primary font-medium">Processing file...</p>
              </div>
            ) : uploadedFile ? (
              <div className="flex flex-col items-center gap-4">
                <div className="flex items-center gap-3 bg-background-secondary p-4 rounded-lg">
                  <File className="w-8 h-8 text-success" />
                  <div className="text-left">
                    <p className="font-medium text-primary">{uploadedFile.name}</p>
                    <p className="text-sm text-secondary">
                      {(uploadedFile.size / 1024).toFixed(1)} KB
                      {filePreview && ` • ${filePreview.total_rows} rows`}
                    </p>
                  </div>
                  <button
                    onClick={(e) => {
                      e.stopPropagation()
                      clearFile()
                    }}
                    className="text-secondary hover:text-error transition-colors"
                  >
                    <X className="w-5 h-5" />
                  </button>
                </div>
                
                {autoDetected && detectedParser && (
                  <div className="flex items-center gap-2 text-success">
                    <CheckCircle className="w-5 h-5" />
                    <span className="font-medium">
                      Auto-detected: {parsers.find(p => p.id === detectedParser)?.name}
                    </span>
                  </div>
                )}
              </div>
            ) : (
              <div className="flex flex-col items-center gap-4">
                <Upload className="w-12 h-12 text-muted" />
                <div>
                  <p className="text-lg font-medium text-primary mb-2">
                    Drop your order file here or click to browse
                  </p>
                  <p className="text-sm text-secondary">
                    {isLoadingParsers 
                      ? 'Loading available suppliers...' 
                      : `Supports CSV, XLS, and XLSX files from ${parsers.map(p => p.name).join(', ')}, and more`
                    }
                  </p>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Parser Selection Dropdown */}
        {uploadedFile && (
          <div className="mt-6 space-y-4">
            <div>
              <label className="block text-sm font-medium text-primary mb-2">
                Supplier/Parser Type
                {autoDetected && (
                  <span className="ml-2 text-xs text-success">(Auto-detected)</span>
                )}
              </label>
              <div className="relative">
                <select
                  value={selectedParser}
                  onChange={(e) => setSelectedParser(e.target.value)}
                  className="input w-full appearance-none pr-10"
                  disabled={isLoadingParsers}
                >
                  <option value="">
                    {isLoadingParsers ? 'Loading suppliers...' : 'Select a parser...'}
                  </option>
                  {parsers.map((parser) => (
                    <option key={parser.id} value={parser.id} disabled={!parser.supported}>
                      {parser.name} - {parser.description}
                      {!parser.supported ? ' (Coming soon)' : ''}
                    </option>
                  ))}
                </select>
                <ChevronDown className="absolute right-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-secondary pointer-events-none" />
              </div>
            </div>

            {/* File Preview Info */}
            {filePreview && (
              <div className="bg-background-secondary rounded-lg p-4">
                <h5 className="font-medium text-primary mb-2">File Preview</h5>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                  <div>
                    <span className="text-secondary">Format:</span>
                    <span className="text-primary ml-2 font-medium">
                      {filePreview.file_format?.toUpperCase() || 'Unknown'}
                    </span>
                  </div>
                  <div>
                    <span className="text-secondary">Rows:</span>
                    <span className="text-primary ml-2 font-medium">{filePreview.total_rows}</span>
                  </div>
                  <div>
                    <span className="text-secondary">Columns:</span>
                    <span className="text-primary ml-2 font-medium">{filePreview.headers.length}</span>
                  </div>
                  <div>
                    <span className="text-secondary">Supported:</span>
                    <span className={`ml-2 font-medium ${filePreview.is_supported ? 'text-success' : 'text-error'}`}>
                      {filePreview.is_supported ? 'Yes' : 'No'}
                    </span>
                  </div>
                </div>
                
                {filePreview.validation_errors.length > 0 && (
                  <div className="mt-3 p-3 bg-error/10 rounded border border-error/20">
                    <p className="text-sm text-error font-medium mb-1">Validation Issues:</p>
                    <ul className="text-sm text-error list-disc list-inside">
                      {filePreview.validation_errors.map((error, index) => (
                        <li key={index}>{error}</li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            )}
          </div>
        )}
      </div>

      {/* Import Settings */}
      <ImportSettings />

      {/* Selected Parser Component */}
      {uploadedFile && selectedParser && (
        <motion.div
          key={selectedParser}
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.3 }}
        >
          {selectedParserInfo?.supported ? (
            <UnifiedFileImporter
              uploadedFile={uploadedFile}
              filePreview={filePreview}
              parserType={selectedParser}
              parserName={selectedParserInfo.name}
              description={selectedParserInfo.description}
              onImportComplete={(result) => {
                onImportComplete?.(result)
                // Reset state after successful import
                clearFile()
              }}
            />
          ) : (
            <div className="card p-8 text-center">
              <div className="w-16 h-16 bg-text-muted/10 rounded-full flex items-center justify-center mx-auto mb-4">
                <AlertCircle className="w-8 h-8 text-muted" />
              </div>
              <h4 className="text-lg font-medium text-primary mb-2">
                {selectedParserInfo?.name} Import Coming Soon
              </h4>
              <p className="text-secondary">
                We're working on adding support for {selectedParserInfo?.name} imports.
                <br />
                For now, try other available supplier imports.
              </p>
            </div>
          )}
        </motion.div>
      )}

      {/* Instructions when no file is uploaded - removed redundant section */}
    </div>
  )
}

export default ImportSelector