import React from 'react'
import { Upload, Eye, RefreshCw, Trash2, AlertCircle, CheckCircle } from 'lucide-react'
import { motion, AnimatePresence } from 'framer-motion'
import toast from 'react-hot-toast'
import { apiClient } from '@/services/api'
import { useOrderImport, OrderInfo } from '../hooks/useOrderImport'
import FileUpload from '../FileUpload'
import ImportProgress from '../ImportProgress'
import FilePreview from '../FilePreview'

interface MouserImporterProps {
  onImportComplete?: (result: any) => void
  parserType: string
  parserName: string
  description: string
}

const MouserImporter: React.FC<MouserImporterProps> = ({ onImportComplete }) => {
  const validateFile = (file: File): boolean => {
    // Mouser-specific validation for XLS files
    const validExtensions = ['.xls', '.xlsx']
    const fileExtension = file.name.toLowerCase().substring(file.name.lastIndexOf('.'))
    
    if (!validExtensions.includes(fileExtension)) {
      toast.error('Please select a Mouser XLS file (.xls or .xlsx)')
      return false
    }
    
    // Check file size (Mouser files can vary)
    if (file.size > 15 * 1024 * 1024) { // 15MB
      toast.error('File too large. Mouser XLS files should be smaller than 15MB.')
      return false
    }
    
    return true
  }

  const extractOrderInfoFromFilename = async (filename: string): Promise<Partial<OrderInfo> | null> => {
    try {
      const response = await apiClient.post('/api/csv/extract-filename-info', {
        filename: filename
      })
      
      // Handle ResponseSchema format
      const data = response.data || response
      if (data && data.order_info) {
        return {
          order_date: data.order_info.order_date,
          order_number: data.order_info.order_number
        }
      }
      
      return null
    } catch (error) {
      console.log('No Mouser filename pattern matched for:', filename)
      return null
    }
  }

  // Use file upload instead of text content for XLS files
  const handleFileSelect = async (selectedFile: File) => {
    if (!selectedFile) return

    if (!validateFile(selectedFile)) {
      return
    }

    setFile(selectedFile)
    setLoading(true)

    // Try to extract order info from filename
    const extractedInfo = await extractOrderInfoFromFilename(selectedFile.name)
    if (extractedInfo) {
      setOrderInfo(prev => ({
        ...prev,
        order_date: extractedInfo.order_date || prev.order_date,
        order_number: extractedInfo.order_number || prev.order_number
      }))
      toast.success('Auto-detected Mouser order information')
    }

    try {
      // Use file upload endpoint for XLS files
      const formData = new FormData()
      formData.append('file', selectedFile)

      const response = await apiClient.post('/api/csv/preview-file', formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      })

      // Handle ResponseSchema format
      const data = response.data || response
      setPreviewData(data)
      
      if (data.validation_errors && data.validation_errors.length > 0) {
        toast.error(`Validation issues: ${data.validation_errors[0]}`)
      }
      
    } catch (error) {
      toast.error('Failed to parse XLS file')
      console.error('XLS preview error:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleImport = async () => {
    if (!file || !previewData || !previewData.is_supported) {
      toast.error('Please select a valid Mouser XLS file')
      return
    }

    setImporting(true)
    setImportProgress(null)
    setShowProgress(true)

    try {
      // Use file upload endpoint for XLS files
      const formData = new FormData()
      formData.append('file', file)
      formData.append('parser_type', 'mouser')
      formData.append('order_number', orderInfo.order_number || '')
      formData.append('order_date', orderInfo.order_date || new Date().toISOString().split('T')[0])
      formData.append('notes', orderInfo.notes || '')

      setImportProgress({
        processed_parts: 0,
        total_parts: 0,
        current_operation: 'Starting XLS import...',
        is_complete: false
      })

      const response = await apiClient.post('/api/csv/import-file', formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      })

      const result = response.data || response
      
      toast.success(`Imported ${result.successful_imports || 0} parts successfully`)
      
      if (result.failed_imports > 0) {
        toast.error(`${result.failed_imports} parts failed to import`)
      }

      onImportComplete?.(result)
      clearFile()

    } catch (error) {
      toast.error('Failed to import parts from XLS file')
      console.error('XLS import error:', error)
    } finally {
      setImporting(false)
      setShowProgress(false)
      setImportProgress(null)
    }
  }

  // Use the CSV import hook but override file handling
  const orderImport = useOrderImport({
    parserType: 'mouser',
    parserName: 'Mouser',
    onImportComplete,
    validateFile,
    extractOrderInfoFromFilename
  })

  // Override the file select and import functions
  const {
    file,
    previewData,
    loading,
    importing,
    showPreview,
    importProgress,
    showProgress,
    orderInfo,
    fileInputRef,
    handleFileChange,
    handleDrop,
    handleDragOver,
    clearFile,
    updateOrderInfo,
    setShowPreview
  } = orderImport

  // Use our custom handlers
  const setFile = orderImport.handleFileSelect.bind(null)
  const setLoading = (loading: boolean) => {} // Hook manages this
  const setImporting = (importing: boolean) => {} // Hook manages this
  const setImportProgress = (progress: any) => {} // Hook manages this
  const setShowProgress = (show: boolean) => {} // Hook manages this
  const setOrderInfo = orderImport.updateOrderInfo
  const setPreviewData = (data: any) => {} // Hook manages this

  return (
    <div className="space-y-6">
      <div className="text-center space-y-4">
        <div>
          <h3 className="text-lg font-semibold text-primary flex items-center justify-center gap-2 mb-2">
            <Upload className="w-5 h-5" />
            Import Mouser Parts
          </h3>
          <p className="text-secondary mb-4">
            Upload Mouser order XLS files to automatically add parts to your inventory
          </p>
        </div>
      </div>

      <ImportProgress 
        showProgress={showProgress}
        importProgress={importProgress}
      />

      <FileUpload
        file={file}
        totalRows={previewData?.total_rows}
        parserName="Mouser"
        description="Mouser Electronics order XLS files"
        filePattern="*.xls, *.xlsx"
        onFileChange={handleFileChange}
        onDrop={handleDrop}
        onDragOver={handleDragOver}
        onClear={clearFile}
        onFileSelect={handleFileSelect}
        fileInputRef={fileInputRef}
      />

      {/* Loading State */}
      {loading && (
        <div className="text-center py-4">
          <RefreshCw className="w-6 h-6 animate-spin mx-auto text-primary" />
          <p className="text-secondary mt-2">Analyzing XLS file...</p>
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
                <h4 className="font-medium text-primary">File Analysis</h4>
                <div className="flex items-center gap-2">
                  {previewData.is_supported ? (
                    <span className="flex items-center gap-1 text-accent">
                      <CheckCircle className="w-4 h-4" />
                      Supported Format ({previewData.file_format?.toUpperCase() || 'XLS'})
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
                  <label className="block text-sm font-medium text-primary mb-2">
                    Detected Parser
                  </label>
                  <div className="text-sm text-secondary">
                    <p><strong>Type:</strong> {previewData.detected_parser || 'Unknown'}</p>
                    <p><strong>Rows:</strong> {previewData.total_rows || 0}</p>
                    <p><strong>Columns:</strong> {previewData.headers?.length || 0}</p>
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
              <h4 className="font-medium text-primary mb-4">Order Information</h4>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-primary mb-2">
                    Order Number
                    {orderInfo.order_number && (
                      <span className="ml-2 text-xs text-accent">✓ Auto-detected</span>
                    )}
                  </label>
                  <input
                    type="text"
                    className="input w-full"
                    value={orderInfo.order_number || ''}
                    onChange={(e) => updateOrderInfo({ order_number: e.target.value })}
                    placeholder="Optional order number"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-primary mb-2">
                    Order Date
                    {orderInfo.order_date && orderInfo.order_date !== new Date().toISOString().split('T')[0] && (
                      <span className="ml-2 text-xs text-accent">✓ Auto-detected</span>
                    )}
                  </label>
                  <input
                    type="date"
                    className="input w-full cursor-pointer"
                    value={orderInfo.order_date || ''}
                    onChange={(e) => updateOrderInfo({ order_date: e.target.value })}
                    placeholder="Select order date"
                    onClick={(e) => e.currentTarget.showPicker?.()}
                  />
                </div>
                <div className="md:col-span-2">
                  <label className="block text-sm font-medium text-primary mb-2">
                    Notes
                  </label>
                  <textarea
                    className="input w-full h-20 resize-none"
                    value={orderInfo.notes || ''}
                    onChange={(e) => updateOrderInfo({ notes: e.target.value })}
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
                  disabled={!previewData?.is_supported || importing}
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

            <FilePreview 
              showPreview={showPreview}
              previewData={previewData}
            />
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}

export default MouserImporter