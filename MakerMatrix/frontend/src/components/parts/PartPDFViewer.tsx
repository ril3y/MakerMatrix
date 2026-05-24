import { useEffect, useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { X, Download, FileText, ExternalLink } from 'lucide-react'
import type { Datasheet } from '@/types/parts'
import { fetchDatasheetBlob, revokeDatasheetBlob } from '@/services/datasheet.service'
import { getErrorMessage } from '@/services/api'

interface PartPDFViewerProps {
  isOpen: boolean
  onClose: () => void
  datasheet: Datasheet
}

const PartPDFViewer = ({ isOpen, onClose, datasheet }: PartPDFViewerProps) => {
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(false)
  const [blobUrl, setBlobUrl] = useState<string | null>(null)

  // Fetch the datasheet through the authenticated API client and expose it
  // as a `blob:` URL so the <iframe> can render it without needing a Bearer
  // token (iframes do not send auth headers).
  useEffect(() => {
    if (!isOpen || !datasheet.filename) return

    let cancelled = false
    let createdUrl: string | null = null

    const load = async () => {
      try {
        setLoading(true)
        setError(false)
        const url = await fetchDatasheetBlob(datasheet.filename)
        createdUrl = url
        if (cancelled) {
          revokeDatasheetBlob(url)
          return
        }
        setBlobUrl(url)
      } catch (err) {
        console.error('Failed to load datasheet PDF:', getErrorMessage(err, 'Unknown error'))
        if (!cancelled) {
          setError(true)
          setLoading(false)
        }
      }
    }

    void load()

    return () => {
      cancelled = true
      if (createdUrl) {
        revokeDatasheetBlob(createdUrl)
      }
      setBlobUrl(null)
    }
  }, [isOpen, datasheet.filename])

  // Final-mount cleanup: revoke any URL still held in state when this
  // component is removed from the tree.
  useEffect(() => {
    return () => {
      if (blobUrl) {
        revokeDatasheetBlob(blobUrl)
      }
    }
    // Run only on unmount — re-fetch cleanup is handled above.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const downloadDatasheet = () => {
    if (!blobUrl) return
    const link = document.createElement('a')
    link.href = blobUrl
    link.download = datasheet.original_filename || datasheet.filename
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
  }

  const openInNewTab = () => {
    if (!blobUrl) return
    window.open(blobUrl, '_blank', 'noopener,noreferrer')
  }

  const formatFileSize = (bytes?: number) => {
    if (!bytes) return 'Unknown size'
    if (bytes < 1024) return `${bytes} B`
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
  }

  if (!isOpen) return null

  return (
    <AnimatePresence>
      <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
        <motion.div
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          exit={{ opacity: 0, scale: 0.95 }}
          className="bg-bg-primary rounded-lg shadow-xl w-full max-w-6xl h-[90vh] overflow-hidden flex flex-col"
        >
          {/* Header */}
          <div className="flex items-center justify-between p-4 border-b border-border bg-bg-secondary">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-blue-500/20 rounded-lg">
                <FileText className="w-5 h-5 text-blue-400" />
              </div>
              <div>
                <h2 className="text-lg font-bold text-primary">
                  {datasheet.original_filename || datasheet.filename}
                </h2>
                <p className="text-sm text-secondary">
                  {formatFileSize(datasheet.file_size)} • PDF Document
                </p>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <button
                onClick={downloadDatasheet}
                disabled={!blobUrl}
                className="btn btn-secondary btn-sm flex items-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
                title="Download PDF"
              >
                <Download className="w-4 h-4" />
                Download
              </button>
              <button
                onClick={openInNewTab}
                disabled={!blobUrl}
                className="btn btn-secondary btn-sm flex items-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
                title="Open in new tab"
              >
                <ExternalLink className="w-4 h-4" />
                Open
              </button>
              <button
                onClick={onClose}
                className="p-2 hover:bg-bg-tertiary rounded-lg transition-colors"
                title="Close"
              >
                <X className="w-5 h-5 text-secondary" />
              </button>
            </div>
          </div>

          {/* PDF Content */}
          <div className="flex-1 relative">
            {loading && (
              <div className="absolute inset-0 flex items-center justify-center bg-bg-primary">
                <div className="text-center">
                  <FileText className="w-12 h-12 text-muted mx-auto mb-4 animate-pulse" />
                  <p className="text-secondary">Loading PDF...</p>
                </div>
              </div>
            )}

            {error && (
              <div className="absolute inset-0 flex items-center justify-center bg-bg-primary">
                <div className="text-center">
                  <FileText className="w-12 h-12 text-red-400 mx-auto mb-4" />
                  <h3 className="text-lg font-semibold text-primary mb-2">Failed to Load PDF</h3>
                  <p className="text-secondary mb-4">The PDF document could not be displayed.</p>
                </div>
              </div>
            )}

            {blobUrl && !error && (
              <iframe
                src={blobUrl}
                className="w-full h-full border-0"
                title={datasheet.original_filename || datasheet.filename}
                onLoad={() => setLoading(false)}
                onError={() => {
                  setLoading(false)
                  setError(true)
                }}
              />
            )}
          </div>
        </motion.div>
      </div>
    </AnimatePresence>
  )
}

export default PartPDFViewer
