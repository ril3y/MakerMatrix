import React from 'react'
import { Upload, Eye, RefreshCw, Trash2, AlertCircle, CheckCircle, Info } from 'lucide-react'
import { motion } from 'framer-motion'
import toast from 'react-hot-toast'
import { apiClient } from '@/services/api'
import { BaseCSVImportComponent, BaseCSVImportProps, OrderInfo } from './BaseCSVImport'

interface LCSCCSVImportProps extends BaseCSVImportProps {}

export class CSVImportLCSC extends BaseCSVImportComponent {
  constructor(props: LCSCCSVImportProps) {
    super({
      ...props,
      parserType: 'lcsc',
      parserName: 'LCSC',
      description: 'LCSC Electronics order CSV files',
      filePattern: 'LCSC_Exported__*.csv'
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
      console.log('No LCSC filename pattern matched for:', filename)
      return null
    }
  }

  validateFile(file: File): boolean {
    // LCSC-specific validation
    if (!file.name.toLowerCase().includes('lcsc')) {
      toast.error('This doesn\'t appear to be an LCSC file. Expected filename containing "LCSC".')
    }
    
    // Check file size (LCSC files are typically small-medium)
    if (file.size > 5 * 1024 * 1024) { // 5MB
      toast.error('File too large. LCSC CSV files are typically smaller than 5MB.')
      return false
    }
    
    return true
  }

  renderCustomOrderFields(): React.ReactNode {
    const { orderInfo } = this.state
    
    return (
      <div className="space-y-4">
        {/* LCSC-specific help text */}
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-3">
          <div className="flex items-start gap-2">
            <Info className="w-4 h-4 text-blue-500 mt-0.5" />
            <div>
              <p className="text-sm font-medium text-blue-800">LCSC Import Tips</p>
              <ul className="text-sm text-blue-700 mt-1 space-y-1">
                <li>• Order date and number auto-detected from filename</li>
                <li>• Parts will be categorized based on component type</li>
                <li>• LCSC part numbers will be preserved in properties</li>
              </ul>
            </div>
          </div>
        </div>

        {/* Custom LCSC fields could go here */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-primary mb-2">
              LCSC Order ID
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
            <label className="block text-sm font-medium text-primary mb-2">
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

        <div>
          <label className="block text-sm font-medium text-primary mb-2">
            Import Notes
          </label>
          <textarea
            className="input w-full h-20 resize-none"
            value={orderInfo.notes}
            onChange={(e) => this.updateOrderInfo({ notes: e.target.value })}
            placeholder="Optional notes about this LCSC order (e.g., project name, PCB batch)"
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
          <h3 className="text-lg font-semibold text-primary mb-2 flex items-center justify-center gap-2">
            <Upload className="w-5 h-5" />
            Import LCSC Order Parts
          </h3>
          <p className="text-secondary">
            Upload LCSC order CSV files to automatically add parts to your inventory with order tracking
          </p>
        </div>

        {/* File Upload */}
        {this.renderFileUpload()}

        {/* Loading State */}
        {loading && (
          <div className="text-center py-4">
            <RefreshCw className="w-6 h-6 animate-spin mx-auto text-primary" />
            <p className="text-secondary mt-2">Analyzing LCSC CSV file...</p>
          </div>
        )}

        {/* Import Progress */}
        {this.renderProgressBar()}

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
                <h4 className="font-medium text-primary">LCSC File Analysis</h4>
                <div className="flex items-center gap-2">
                  {previewData.is_supported ? (
                    <span className="flex items-center gap-1 text-accent">
                      <CheckCircle className="w-4 h-4" />
                      Valid LCSC Format
                    </span>
                  ) : (
                    <span className="flex items-center gap-1 text-destructive">
                      <AlertCircle className="w-4 h-4" />
                      Invalid Format
                    </span>
                  )}
                </div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <div className="text-sm text-secondary mb-2">
                    File Information
                  </div>
                  <div className="space-y-1">
                    <p className="text-sm"><strong>Detected Type:</strong> {previewData.type_info}</p>
                    <p className="text-sm"><strong>Total Rows:</strong> {previewData.total_rows}</p>
                    <p className="text-sm"><strong>Columns:</strong> {previewData.headers.length}</p>
                  </div>
                </div>

                <div>
                  <div className="text-sm text-secondary mb-2">
                    Key Columns Found
                  </div>
                  <div className="flex flex-wrap gap-1">
                    {previewData.headers.slice(0, 4).map((header, index) => (
                      <span key={index} className="bg-bg-secondary px-2 py-1 rounded text-xs">
                        {header}
                      </span>
                    ))}
                    {previewData.headers.length > 4 && (
                      <span className="text-xs text-muted">
                        +{previewData.headers.length - 4} more
                      </span>
                    )}
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
              <h4 className="font-medium text-primary mb-4">LCSC Order Information</h4>
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
                  {importing ? 'Importing LCSC Parts...' : 'Import LCSC Parts'}
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

export default CSVImportLCSC