import React from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import type { FilePreviewData } from './hooks/useOrderImport'

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
              <table className="table w-full">
                <thead className="bg-gradient-to-r from-purple-600/20 to-blue-600/20">
                  <tr>
                    {(previewData.headers || []).map((header, index) => (
                      <th
                        key={index}
                        className="px-4 py-3 text-left text-xs font-bold text-primary uppercase tracking-wider"
                      >
                        {header}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody className="bg-theme-elevated/50 divide-y divide-purple-500/10">
                  {(previewData.preview_rows || []).slice(0, 5).map((row, index) => (
                    <tr
                      key={index}
                      className="hover:bg-gradient-to-r hover:from-purple-600/5 hover:to-blue-600/5 transition-all duration-200"
                    >
                      {(previewData.headers || []).map((header, colIndex) => (
                        <td key={colIndex} className="px-4 py-3 text-primary">
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
                <table className="table w-full">
                  <thead className="bg-gradient-to-r from-purple-600/20 to-blue-600/20">
                    <tr>
                      <th className="px-4 py-3 text-left text-xs font-bold text-primary uppercase tracking-wider">
                        Part Name
                      </th>
                      <th className="px-4 py-3 text-left text-xs font-bold text-primary uppercase tracking-wider">
                        Part Number
                      </th>
                      <th className="px-4 py-3 text-left text-xs font-bold text-primary uppercase tracking-wider">
                        Quantity
                      </th>
                      <th className="px-4 py-3 text-left text-xs font-bold text-primary uppercase tracking-wider">
                        Supplier
                      </th>
                      <th className="px-4 py-3 text-left text-xs font-bold text-primary uppercase tracking-wider">
                        Description
                      </th>
                    </tr>
                  </thead>
                  <tbody className="bg-theme-elevated/50 divide-y divide-purple-500/10">
                    {previewData.parsed_preview.slice(0, 5).map((part, index) => (
                      <tr
                        key={index}
                        className="hover:bg-gradient-to-r hover:from-purple-600/5 hover:to-blue-600/5 transition-all duration-200"
                      >
                        <td className="px-4 py-3 text-primary">{part.name}</td>
                        <td className="px-4 py-3 text-primary">{part.part_number}</td>
                        <td className="px-4 py-3 text-primary">{part.quantity}</td>
                        <td className="px-4 py-3 text-primary">{part.supplier}</td>
                        <td className="px-4 py-3 text-primary truncate max-w-48">
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
