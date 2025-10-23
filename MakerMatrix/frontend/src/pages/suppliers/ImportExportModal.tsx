/**
 * Import/Export Modal
 *
 * Modal for importing and exporting supplier configurations with support for
 * JSON files and optional credential inclusion.
 */

import React, { useState } from 'react'
import { X, Upload, Download, AlertTriangle, CheckCircle, FileText, Shield } from 'lucide-react'
import { supplierService } from '../../services/supplier.service'

interface ImportExportModalProps {
  onClose: () => void
  onSuccess: () => void
}

interface ExportData {
  suppliers?: Array<Record<string, unknown>>
  export_date?: string
  includes_credentials?: boolean
}

export const ImportExportModal: React.FC<ImportExportModalProps> = ({ onClose, onSuccess }) => {
  const [activeTab, setActiveTab] = useState<'import' | 'export'>('import')
  const [loading, setLoading] = useState(false)
  const [errors, setErrors] = useState<string[]>([])
  const [success, setSuccess] = useState<string | null>(null)

  // Import state
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [dragOver, setDragOver] = useState(false)

  // Export state
  const [includeCredentials, setIncludeCredentials] = useState(false)
  const [exportData, setExportData] = useState<ExportData | null>(null)

  const handleFileSelect = (file: File) => {
    if (file.type !== 'application/json' && !file.name.endsWith('.json')) {
      setErrors(['Please select a valid JSON file'])
      return
    }

    if (file.size > 10 * 1024 * 1024) {
      // 10MB limit
      setErrors(['File size must be less than 10MB'])
      return
    }

    setSelectedFile(file)
    setErrors([])
  }

  const handleFileDrop = (e: React.DragEvent) => {
    e.preventDefault()
    setDragOver(false)

    const files = Array.from(e.dataTransfer.files)
    if (files.length > 0) {
      handleFileSelect(files[0])
    }
  }

  const handleFileInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files
    if (files && files.length > 0) {
      handleFileSelect(files[0])
    }
  }

  const handleImport = async () => {
    if (!selectedFile) {
      setErrors(['Please select a file to import'])
      return
    }

    try {
      setLoading(true)
      setErrors([])

      const importedSuppliers = await supplierService.importConfigurations(selectedFile)
      setSuccess(
        `Successfully imported ${importedSuppliers.length} supplier configurations: ${importedSuppliers.join(', ')}`
      )

      // Auto-close after successful import
      setTimeout(() => {
        onSuccess()
      }, 2000)
    } catch (err: unknown) {
      const errorMessage =
        err && typeof err === 'object' && 'response' in err
          ? (err.response as { data?: { detail?: string } })?.data?.detail ||
            'Failed to import supplier configurations'
          : 'Failed to import supplier configurations'
      setErrors([errorMessage])
    } finally {
      setLoading(false)
    }
  }

  const handleExport = async () => {
    try {
      setLoading(true)
      setErrors([])

      const suppliers = await supplierService.exportConfigurations()

      // Create export data wrapper with metadata
      const exportDataWrapper: ExportData = {
        suppliers: suppliers as unknown as Array<Record<string, unknown>>,
        export_date: new Date().toISOString(),
        includes_credentials: includeCredentials,
      }

      setExportData(exportDataWrapper)

      // Create and download file
      const blob = new Blob([JSON.stringify(exportDataWrapper, null, 2)], {
        type: 'application/json',
      })
      const url = URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url

      const timestamp = new Date().toISOString().split('T')[0]
      const credentialsText = includeCredentials ? '_with_credentials' : ''
      link.download = `makermatrix_suppliers_${timestamp}${credentialsText}.json`

      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
      URL.revokeObjectURL(url)

      setSuccess(`Successfully exported ${suppliers.length} supplier configurations`)
    } catch (err: unknown) {
      const errorMessage =
        err && typeof err === 'object' && 'response' in err
          ? (err.response as { data?: { detail?: string } })?.data?.detail ||
            'Failed to export supplier configurations'
          : 'Failed to export supplier configurations'
      setErrors([errorMessage])
    } finally {
      setLoading(false)
    }
  }

  const clearMessages = () => {
    setErrors([])
    setSuccess(null)
  }

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-xl max-w-2xl w-full max-h-[90vh] overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-gray-200 dark:border-gray-700">
          <div>
            <h2 className="text-xl font-semibold text-gray-900 dark:text-white">
              Import/Export Configurations
            </h2>
            <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
              Backup and restore supplier configurations
            </p>
          </div>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
          >
            <X className="w-6 h-6" />
          </button>
        </div>

        {/* Tabs */}
        <div className="border-b border-gray-200 dark:border-gray-700">
          <nav className="flex">
            <button
              onClick={() => {
                setActiveTab('import')
                clearMessages()
              }}
              className={`flex-1 py-3 px-4 text-sm font-medium text-center border-b-2 ${
                activeTab === 'import'
                  ? 'border-blue-500 text-blue-600 dark:text-blue-400'
                  : 'border-transparent text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300'
              }`}
            >
              <Upload className="w-4 h-4 inline mr-2" />
              Import
            </button>
            <button
              onClick={() => {
                setActiveTab('export')
                clearMessages()
              }}
              className={`flex-1 py-3 px-4 text-sm font-medium text-center border-b-2 ${
                activeTab === 'export'
                  ? 'border-blue-500 text-blue-600 dark:text-blue-400'
                  : 'border-transparent text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300'
              }`}
            >
              <Download className="w-4 h-4 inline mr-2" />
              Export
            </button>
          </nav>
        </div>

        {/* Content */}
        <div className="p-6 overflow-y-auto max-h-[calc(90vh-200px)]">
          {/* Messages */}
          {errors.length > 0 && (
            <div className="mb-6 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-md p-4">
              <div className="flex">
                <AlertTriangle className="w-5 h-5 text-red-400" />
                <div className="ml-3">
                  <h3 className="text-sm font-medium text-red-800 dark:text-red-200">Error</h3>
                  <ul className="mt-1 text-sm text-red-700 dark:text-red-300 list-disc list-inside">
                    {errors.map((error, index) => (
                      <li key={index}>{error}</li>
                    ))}
                  </ul>
                </div>
              </div>
            </div>
          )}

          {success && (
            <div className="mb-6 bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-md p-4">
              <div className="flex">
                <CheckCircle className="w-5 h-5 text-green-400" />
                <div className="ml-3">
                  <h3 className="text-sm font-medium text-green-800 dark:text-green-200">
                    Success
                  </h3>
                  <p className="mt-1 text-sm text-green-700 dark:text-green-300">{success}</p>
                </div>
              </div>
            </div>
          )}

          {activeTab === 'import' ? (
            /* Import Tab */
            <div className="space-y-6">
              <div>
                <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-4">
                  Import Supplier Configurations
                </h3>
                <p className="text-sm text-gray-600 dark:text-gray-300 mb-4">
                  Upload a JSON file containing supplier configurations. Existing suppliers with the
                  same name will be updated.
                </p>
              </div>

              {/* File Upload Area */}
              <div
                className={`border-2 border-dashed rounded-lg p-8 text-center transition-colors ${
                  dragOver
                    ? 'border-blue-400 bg-blue-50 dark:bg-blue-900/20'
                    : 'border-gray-300 dark:border-gray-600'
                }`}
                onDragOver={(e) => {
                  e.preventDefault()
                  setDragOver(true)
                }}
                onDragLeave={() => setDragOver(false)}
                onDrop={handleFileDrop}
              >
                <FileText className="w-12 h-12 text-gray-400 mx-auto mb-4" />

                {selectedFile ? (
                  <div>
                    <p className="text-sm font-medium text-gray-900 dark:text-white">
                      {selectedFile.name}
                    </p>
                    <p className="text-sm text-gray-500 dark:text-gray-400">
                      {(selectedFile.size / 1024).toFixed(1)} KB
                    </p>
                    <button
                      onClick={() => setSelectedFile(null)}
                      className="mt-2 text-sm text-blue-600 dark:text-blue-400 hover:text-blue-500 dark:hover:text-blue-300"
                    >
                      Choose different file
                    </button>
                  </div>
                ) : (
                  <div>
                    <p className="text-sm text-gray-600 dark:text-gray-300 mb-2">
                      Drag and drop a JSON file here, or click to select
                    </p>
                    <input
                      type="file"
                      accept=".json,application/json"
                      onChange={handleFileInputChange}
                      className="hidden"
                      id="file-input"
                    />
                    <label
                      htmlFor="file-input"
                      className="inline-flex items-center px-4 py-2 border border-gray-300 dark:border-gray-600 text-sm font-medium rounded-md text-gray-700 dark:text-gray-200 bg-white dark:bg-gray-700 hover:bg-gray-50 dark:hover:bg-gray-600 cursor-pointer"
                    >
                      Select File
                    </label>
                  </div>
                )}
              </div>

              {/* Import Guidelines */}
              <div className="bg-gray-50 dark:bg-gray-700/50 rounded-lg p-4">
                <h4 className="text-sm font-medium text-gray-900 dark:text-white mb-2">
                  Import Guidelines
                </h4>
                <ul className="text-sm text-gray-600 dark:text-gray-300 space-y-1 list-disc list-inside">
                  <li>File must be in valid JSON format</li>
                  <li>Maximum file size: 10MB</li>
                  <li>Existing suppliers will be updated with new configurations</li>
                  <li>Invalid configurations will be skipped with warnings</li>
                  <li>Credentials are imported separately if included in the file</li>
                </ul>
              </div>
            </div>
          ) : (
            /* Export Tab */
            <div className="space-y-6">
              <div>
                <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-4">
                  Export Supplier Configurations
                </h3>
                <p className="text-sm text-gray-600 dark:text-gray-300 mb-4">
                  Download all supplier configurations as a JSON file. You can choose to include
                  encrypted credentials.
                </p>
              </div>

              {/* Export Options */}
              <div className="bg-gray-50 dark:bg-gray-700/50 rounded-lg p-4">
                <h4 className="text-sm font-medium text-gray-900 dark:text-white mb-3">
                  Export Options
                </h4>

                <label className="flex items-start space-x-3">
                  <input
                    type="checkbox"
                    checked={includeCredentials}
                    onChange={(e) => setIncludeCredentials(e.target.checked)}
                    className="mt-1 h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                  />
                  <div>
                    <div className="font-medium text-gray-900 dark:text-white">
                      Include Credentials
                    </div>
                    <div className="text-sm text-gray-500 dark:text-gray-400">
                      Export encrypted credentials along with configurations. Credentials remain
                      encrypted in the export file.
                    </div>
                  </div>
                </label>

                {includeCredentials && (
                  <div className="mt-3 bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-md p-3">
                    <div className="flex">
                      <Shield className="w-4 h-4 text-yellow-400 mt-0.5" />
                      <div className="ml-2">
                        <p className="text-sm text-yellow-800 dark:text-yellow-200">
                          <strong>Security Notice:</strong> Exported credentials remain encrypted,
                          but exercise caution when sharing export files.
                        </p>
                      </div>
                    </div>
                  </div>
                )}
              </div>

              {/* Export Preview */}
              {exportData && (
                <div className="bg-gray-50 dark:bg-gray-700/50 rounded-lg p-4">
                  <h4 className="text-sm font-medium text-gray-900 dark:text-white mb-2">
                    Export Preview
                  </h4>
                  <div className="text-sm text-gray-600 dark:text-gray-300">
                    <p>Suppliers: {exportData.suppliers?.length || 0}</p>
                    <p>Export Date: {exportData.export_date}</p>
                    <p>Includes Credentials: {exportData.includes_credentials ? 'Yes' : 'No'}</p>
                    <p>
                      File Size: ~
                      {JSON.stringify(exportData).length > 1024
                        ? `${(JSON.stringify(exportData).length / 1024).toFixed(1)} KB`
                        : `${JSON.stringify(exportData).length} bytes`}
                    </p>
                  </div>
                </div>
              )}

              {/* Export Guidelines */}
              <div className="bg-gray-50 dark:bg-gray-700/50 rounded-lg p-4">
                <h4 className="text-sm font-medium text-gray-900 dark:text-white mb-2">
                  Export Information
                </h4>
                <ul className="text-sm text-gray-600 dark:text-gray-300 space-y-1 list-disc list-inside">
                  <li>Export includes all supplier configurations and settings</li>
                  <li>Credentials are exported in encrypted format for security</li>
                  <li>Export file can be re-imported to restore configurations</li>
                  <li>File is downloaded as JSON with timestamp in filename</li>
                  <li>No personal information is included in the export</li>
                </ul>
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-end p-6 border-t border-gray-200 dark:border-gray-700 space-x-3">
          <button
            onClick={onClose}
            disabled={loading}
            className="px-4 py-2 border border-gray-300 dark:border-gray-600 text-sm font-medium rounded-md text-gray-700 dark:text-gray-200 bg-white dark:bg-gray-700 hover:bg-gray-50 dark:hover:bg-gray-600 disabled:opacity-50"
          >
            Close
          </button>

          {activeTab === 'import' ? (
            <button
              onClick={handleImport}
              disabled={loading || !selectedFile}
              className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 disabled:opacity-50"
            >
              {loading ? (
                <>
                  <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                  Importing...
                </>
              ) : (
                <>
                  <Upload className="w-4 h-4 mr-2" />
                  Import Configurations
                </>
              )}
            </button>
          ) : (
            <button
              onClick={handleExport}
              disabled={loading}
              className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 disabled:opacity-50"
            >
              {loading ? (
                <>
                  <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                  Exporting...
                </>
              ) : (
                <>
                  <Download className="w-4 h-4 mr-2" />
                  Export Configurations
                </>
              )}
            </button>
          )}
        </div>
      </div>
    </div>
  )
}
