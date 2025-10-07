import React from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { FilePreviewData } from './hooks/useOrderImport'

interface FilePreviewProps {
  showPreview: boolean
  previewData: FilePreviewData | null
}

const FilePreview: React.FC<FilePreviewProps> = ({ showPreview, previewData }) => {
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
            <h4 className="font-medium text-primary">Data Preview</h4>
            <span className="text-sm text-secondary">
              Showing {Math.min(previewData.preview_rows?.length || 0, 5)} of{' '}
              {previewData.total_rows || 0} rows
            </span>
          </div>

          {/* Raw Data Table */}
          <div className="mb-6">
            <h5 className="text-sm font-medium text-primary mb-2">Raw CSV Data</h5>
            <div className="overflow-x-auto border border-border-primary rounded-md">
              <table className="table">
                <thead className="table-header">
                  <tr>
                    {(previewData.headers || []).map((header, index) => (
                      <th key={index} className="table-head">
                        {header}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody className="table-body">
                  {(previewData.preview_rows || []).slice(0, 5).map((row, index) => (
                    <tr key={index} className="table-row">
                      {(previewData.headers || []).map((header, colIndex) => (
                        <td key={colIndex} className="table-cell text-primary">
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
          {previewData.parsed_preview && previewData.parsed_preview.length > 0 && (
            <div>
              <h5 className="text-sm font-medium text-primary mb-2">Parsed Parts Data</h5>
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
                        <td className="table-cell text-primary">{part.name}</td>
                        <td className="table-cell text-primary">{part.part_number}</td>
                        <td className="table-cell text-primary">{part.quantity}</td>
                        <td className="table-cell text-primary">{part.supplier}</td>
                        <td className="table-cell text-primary truncate max-w-48">
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

export default FilePreview
