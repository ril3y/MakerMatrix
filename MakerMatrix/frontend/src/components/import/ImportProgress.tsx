import React from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { ImportProgress as ImportProgressType } from './hooks/useOrderImport'

interface ImportProgressProps {
  showProgress: boolean
  importProgress: ImportProgressType | null
}

const ImportProgress: React.FC<ImportProgressProps> = ({ showProgress, importProgress }) => {
  if (!showProgress || !importProgress) {
    return null
  }

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        exit={{ opacity: 0, y: -20 }}
        className="card p-4"
      >
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <h4 className="font-medium text-primary">Import Progress</h4>
            <span className="text-sm text-secondary">
              {importProgress.processed_parts} / {importProgress.total_parts || '?'} parts
            </span>
          </div>

          <div className="w-full bg-background-secondary rounded-full h-3 overflow-hidden">
            {importProgress.total_parts > 0 ? (
              <motion.div
                className="bg-primary h-3 rounded-full transition-all duration-300"
                initial={{ width: 0 }}
                animate={{
                  width: `${(importProgress.processed_parts / importProgress.total_parts) * 100}%`,
                }}
              />
            ) : (
              <div className="h-3 bg-gradient-to-r from-primary/30 via-primary to-primary/30 animate-pulse rounded-full" />
            )}
          </div>

          <div className="flex items-center justify-between text-sm">
            <span className="text-primary">{importProgress.current_operation}</span>
            <span className="text-secondary">
              {importProgress.total_parts > 0
                ? Math.round((importProgress.processed_parts / importProgress.total_parts) * 100)
                : 0}
              %
            </span>
          </div>
        </div>
      </motion.div>
    </AnimatePresence>
  )
}

export default ImportProgress
