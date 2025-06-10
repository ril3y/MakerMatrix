import React from 'react'
import { Upload, Eye, RefreshCw, Trash2, AlertCircle, CheckCircle, Info } from 'lucide-react'
import { motion } from 'framer-motion'
import toast from 'react-hot-toast'
import { apiClient } from '@/services/api'
import { BaseCSVImportComponent, BaseCSVImportProps, OrderInfo } from './BaseCSVImport'

interface DigiKeyCSVImportProps extends BaseCSVImportProps {}

export class CSVImportDigiKey extends BaseCSVImportComponent {
  constructor(props: DigiKeyCSVImportProps) {
    super({
      ...props,
      parserType: 'digikey',
      parserName: 'DigiKey',
      description: 'DigiKey order CSV files',
      filePattern: 'DigiKey_Order_*.csv'
    })
  }

  async extractOrderInfoFromFilename(filename: string): Promise<Partial<OrderInfo> | null> {
    try {
      const response = await apiClient.post('/api/csv/extract-filename-info', {
        filename: filename
      })
      
      if (response.success && response.order_info) {
        return {
          order_date: response.order_info.order_date,
          order_number: response.order_info.order_number
        }
      }
      
      return null
    } catch (error) {
      console.log('No DigiKey filename pattern matched for:', filename)
      return null
    }
  }

  validateFile(file: File): boolean {
    // DigiKey-specific validation
    if (!file.name.toLowerCase().includes('digikey')) {
      toast.warning('This doesn\'t appear to be a DigiKey file. Expected filename containing "DigiKey".')
    }
    
    // DigiKey files can be larger
    if (file.size > 10 * 1024 * 1024) { // 10MB
      toast.error('File too large. DigiKey CSV files should be smaller than 10MB.')
      return false
    }
    
    return true
  }

  renderCustomOrderFields(): React.ReactNode {
    const { orderInfo } = this.state
    
    return (
      <div className="space-y-4">
        {/* DigiKey-specific help text */}
        <div className="bg-red-50 border border-red-200 rounded-lg p-3">
          <div className="flex items-start gap-2">
            <Info className="w-4 h-4 text-red-500 mt-0.5" />
            <div>
              <p className="text-sm font-medium text-red-800">DigiKey Import Tips</p>
              <ul className="text-sm text-red-700 mt-1 space-y-1">
                <li>• DigiKey part numbers will be preserved</li>
                <li>• Manufacturer information included</li>
                <li>• Pricing and availability data captured</li>
                <li>• Supports bulk orders and cut tape</li>
              </ul>
            </div>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-text-primary mb-2">
              DigiKey Order Number
              {orderInfo.order_number && (
                <span className="ml-2 text-xs text-accent">✓ Auto-detected</span>
              )}
            </label>
            <input
              type="text"
              className="input w-full"
              value={orderInfo.order_number}
              onChange={(e) => this.updateOrderInfo({ order_number: e.target.value })}
              placeholder="Auto-detected from filename"
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
              onChange={(e) => this.updateOrderInfo({ order_date: e.target.value })}
              onClick={(e) => e.currentTarget.showPicker?.()}
            />
          </div>
        </div>

        {/* DigiKey-specific fields */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-text-primary mb-2">
              PO Number
            </label>
            <input
              type="text"
              className="input w-full"
              placeholder="Purchase Order Number (optional)"
            />
          </div>
          
          <div>
            <label className="block text-sm font-medium text-text-primary mb-2">
              Project Code
            </label>
            <input
              type="text"
              className="input w-full"
              placeholder="Internal project code (optional)"
            />
          </div>
        </div>

        <div>
          <label className="block text-sm font-medium text-text-primary mb-2">
            Import Notes
          </label>
          <textarea
            className="input w-full h-20 resize-none"
            value={orderInfo.notes}
            onChange={(e) => this.updateOrderInfo({ notes: e.target.value })}
            placeholder="Optional notes about this DigiKey order"
          />
        </div>
      </div>
    )
  }

  render() {
    const { file, previewData, loading, importing, showPreview } = this.state

    return (
      <div className="space-y-6">
        <div className="text-center">
          <h3 className="text-lg font-semibold text-text-primary mb-2 flex items-center justify-center gap-2">
            <Upload className="w-5 h-5" />
            Import DigiKey Order Parts
          </h3>
          <p className="text-text-secondary">
            Upload DigiKey order CSV files with comprehensive part and pricing information
          </p>
        </div>

        {/* File Upload */}
        {this.renderFileUpload()}

        {/* Loading State */}
        {loading && (
          <div className="text-center py-4">
            <RefreshCw className="w-6 h-6 animate-spin mx-auto text-primary" />
            <p className="text-text-secondary mt-2">Analyzing DigiKey CSV file...</p>
          </div>
        )}

        {/* Configuration and Preview */}
        {previewData && !loading && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="space-y-4"
          >
            {/* Detection Results */}
            <div className="card p-4">
              <div className="flex items-center justify-between mb-4">
                <h4 className="font-medium text-text-primary">DigiKey File Analysis</h4>
                <div className="flex items-center gap-2">
                  {previewData.is_supported ? (
                    <span className="flex items-center gap-1 text-accent">
                      <CheckCircle className="w-4 h-4" />
                      Valid DigiKey Format
                    </span>
                  ) : (
                    <span className="flex items-center gap-1 text-destructive">
                      <AlertCircle className="w-4 h-4" />
                      Invalid Format
                    </span>
                  )}
                </div>
              </div>

              <div className="text-sm text-text-secondary mb-2">
                <strong>Detected:</strong> {previewData.type_info} • <strong>Rows:</strong> {previewData.total_rows}
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
              <h4 className="font-medium text-text-primary mb-4">DigiKey Order Information</h4>
              {this.renderCustomOrderFields()}
            </div>

            {/* Preview Toggle and Actions */}
            <div className="flex items-center justify-between">
              <button
                onClick={() => this.setState({ showPreview: !showPreview })}
                className="btn btn-secondary flex items-center gap-2"
              >
                <Eye className="w-4 h-4" />
                {showPreview ? 'Hide Preview' : 'Show Preview'}
              </button>

              <div className="flex gap-2">
                <button
                  onClick={this.clearFile}
                  className="btn btn-secondary flex items-center gap-2"
                >
                  <Trash2 className="w-4 h-4" />
                  Clear
                </button>
                <button
                  onClick={() => this.handleImport()}
                  disabled={importing || !previewData.is_supported}
                  className="btn btn-primary flex items-center gap-2"
                >
                  {importing ? (
                    <RefreshCw className="w-4 h-4 animate-spin" />
                  ) : (
                    <Upload className="w-4 h-4" />
                  )}
                  {importing ? 'Importing DigiKey Parts...' : 'Import DigiKey Parts'}
                </button>
              </div>
            </div>

            {/* Data Preview */}
            {this.renderPreviewData()}
          </motion.div>
        )}
      </div>
    )
  }
}

export default CSVImportDigiKey