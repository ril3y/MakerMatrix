import React from 'react'
import { Upload, Eye, RefreshCw, Trash2, AlertCircle, CheckCircle } from 'lucide-react'
import { motion, AnimatePresence } from 'framer-motion'
import toast from 'react-hot-toast'
import { apiClient } from '@/services/api'
import { useOrderImport, OrderInfo } from '../hooks/useOrderImport'
import FileUpload from '../FileUpload'
import ImportProgress from '../ImportProgress'
import FilePreview from '../FilePreview'

interface DigiKeyImporterProps {
  onImportComplete?: (result: any) => void
  parserType: string
  parserName: string
  description: string
}

const DigiKeyImporter: React.FC<DigiKeyImporterProps> = ({ onImportComplete }) => {
  const validateFile = (file: File): boolean => {
    // More lenient validation since we now have auto-detection
    const fileName = file.name.toLowerCase()
    
    // Check file format
    if (!fileName.endsWith('.csv')) {
      toast.error('DigiKey files should be in CSV format.')
      return false
    }
    
    // DigiKey files can be larger
    if (file.size > 10 * 1024 * 1024) { // 10MB
      toast.error('File too large. DigiKey CSV files should be smaller than 10MB.')
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
      console.log('No DigiKey filename pattern matched for:', filename)
      return null
    }
  }

  const orderImport = useOrderImport({
    parserType: 'digikey',
    parserName: 'DigiKey',
    onImportComplete,
    validateFile,
    extractOrderInfoFromFilename
  })

  return (
    <div className="space-y-6">
      <div className="text-center space-y-4">
        <div>
          <h3 className="text-lg font-semibold text-primary flex items-center justify-center gap-2 mb-2">
            <Upload className="w-5 h-5" />
            Import DigiKey Parts
          </h3>
          <p className="text-secondary mb-4">
            Upload DigiKey order CSV files to automatically add parts to your inventory
          </p>
        </div>
      </div>

      <ImportProgress 
        showProgress={orderImport.showProgress}
        importProgress={orderImport.importProgress}
      />

      <FileUpload
        file={orderImport.file}
        totalRows={orderImport.previewData?.total_rows}
        parserName="DigiKey"
        description="DigiKey order CSV files"
        filePattern="DK_PRODUCTS_*.csv"
        onFileChange={orderImport.handleFileChange}
        onDrop={orderImport.handleDrop}
        onDragOver={orderImport.handleDragOver}
        onClear={orderImport.clearFile}
        onFileSelect={orderImport.handleFileSelect}
        fileInputRef={orderImport.fileInputRef}
      />

      {/* Loading State */}
      {orderImport.loading && (
        <div className="text-center py-4">
          <RefreshCw className="w-6 h-6 animate-spin mx-auto text-primary" />
          <p className="text-secondary mt-2">Analyzing CSV file...</p>
        </div>
      )}

      {/* Preview and Configuration */}
      <AnimatePresence>
        {orderImport.previewData && !orderImport.loading && (
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
                  {orderImport.previewData.is_supported ? (
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
                  <label className="block text-sm font-medium text-primary mb-2">
                    Detected Parser
                  </label>
                  <div className="text-sm text-secondary">
                    <p><strong>Type:</strong> {orderImport.previewData.detected_parser || 'Unknown'}</p>
                    <p><strong>Rows:</strong> {orderImport.previewData.total_rows || 0}</p>
                    <p><strong>Columns:</strong> {orderImport.previewData.headers?.length || 0}</p>
                  </div>
                </div>
              </div>

              {orderImport.previewData.validation_errors && orderImport.previewData.validation_errors.length > 0 && (
                <div className="mt-4 p-3 bg-destructive/10 border border-destructive/20 rounded">
                  <div className="flex items-start gap-2">
                    <AlertCircle className="w-4 h-4 text-destructive mt-0.5" />
                    <div>
                      <p className="text-sm font-medium text-destructive">Validation Issues:</p>
                      <ul className="text-sm text-destructive/80 mt-1">
                        {orderImport.previewData.validation_errors.map((error, index) => (
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
                    {orderImport.orderInfo.order_number && (
                      <span className="ml-2 text-xs text-accent">✓ Auto-detected</span>
                    )}
                  </label>
                  <input
                    type="text"
                    className="input w-full"
                    value={orderImport.orderInfo.order_number || ''}
                    onChange={(e) => orderImport.updateOrderInfo({ order_number: e.target.value })}
                    placeholder="Optional order number"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-primary mb-2">
                    Order Date
                    {orderImport.orderInfo.order_date && orderImport.orderInfo.order_date !== new Date().toISOString().split('T')[0] && (
                      <span className="ml-2 text-xs text-accent">✓ Auto-detected</span>
                    )}
                  </label>
                  <input
                    type="date"
                    className="input w-full cursor-pointer"
                    value={orderImport.orderInfo.order_date || ''}
                    onChange={(e) => orderImport.updateOrderInfo({ order_date: e.target.value })}
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
                    value={orderImport.orderInfo.notes || ''}
                    onChange={(e) => orderImport.updateOrderInfo({ notes: e.target.value })}
                    placeholder="Optional notes about this order"
                  />
                </div>
              </div>
            </div>

            {/* Preview Toggle */}
            <div className="flex items-center justify-between">
              <button
                onClick={() => orderImport.setShowPreview(!orderImport.showPreview)}
                className="btn btn-secondary flex items-center gap-2"
              >
                <Eye className="w-4 h-4" />
                {orderImport.showPreview ? 'Hide Preview' : 'Show Preview'}
              </button>

              <div className="flex gap-2">
                <button
                  onClick={orderImport.clearFile}
                  className="btn btn-secondary flex items-center gap-2"
                >
                  <Trash2 className="w-4 h-4" />
                  Clear
                </button>
                <button
                  onClick={orderImport.handleImport}
                  disabled={!orderImport.previewData?.is_supported || orderImport.importing}
                  className="btn btn-primary flex items-center gap-2"
                >
                  {orderImport.importing ? (
                    <RefreshCw className="w-4 h-4 animate-spin" />
                  ) : (
                    <Upload className="w-4 h-4" />
                  )}
                  {orderImport.importing ? 'Importing...' : 'Import Parts'}
                </button>
              </div>
            </div>

            <FilePreview 
              showPreview={orderImport.showPreview}
              previewData={orderImport.previewData}
            />
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}

export default DigiKeyImporter