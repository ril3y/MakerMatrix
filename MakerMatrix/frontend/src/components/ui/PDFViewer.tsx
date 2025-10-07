import React, { useState, useEffect } from 'react'
import { Document, Page, pdfjs } from 'react-pdf'
import {
  ChevronLeft,
  ChevronRight,
  ZoomIn,
  ZoomOut,
  Download,
  X,
  FileText,
  AlertCircle,
} from 'lucide-react'
import 'react-pdf/dist/esm/Page/AnnotationLayer.css'
import 'react-pdf/dist/esm/Page/TextLayer.css'

// Use local PDF.js worker file
pdfjs.GlobalWorkerOptions.workerSrc = '/js/pdf.worker.min.mjs'

interface PDFViewerProps {
  fileUrl: string
  fileName: string
  onClose: () => void
}

const PDFViewer: React.FC<PDFViewerProps> = ({ fileUrl, fileName, onClose }) => {
  const [numPages, setNumPages] = useState<number | null>(null)
  const [pageNumber, setPageNumber] = useState(1)
  const [scale, setScale] = useState(1.0)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [pdfData, setPdfData] = useState<string | ArrayBuffer | null>(null)

  useEffect(() => {
    const fetchPdf = async () => {
      // Check if this is a local API URL that needs authentication
      if (fileUrl.startsWith('/api/') || fileUrl.startsWith('/utility/')) {
        try {
          setLoading(true)
          setError(null)

          const token = localStorage.getItem('auth_token')
          console.log('PDFViewer: Using token:', token ? `${token.substring(0, 20)}...` : 'null')
          console.log('PDFViewer: Fetching URL:', fileUrl)

          const response = await fetch(fileUrl, {
            headers: {
              Authorization: `Bearer ${token}`,
            },
          })

          if (!response.ok) {
            throw new Error(`Failed to fetch PDF: ${response.status} ${response.statusText}`)
          }

          const arrayBuffer = await response.arrayBuffer()
          console.log('PDFViewer: ArrayBuffer received, size:', arrayBuffer.byteLength)
          setPdfData(arrayBuffer)
          setLoading(false) // Important: Set loading to false after data is received
          console.log('PDFViewer: Loading set to false, pdfData set')
        } catch (err: any) {
          console.error('Failed to fetch PDF:', err)
          setError(`Failed to load PDF: ${err.message}`)
          setLoading(false)
        }
      } else {
        // External URL, use directly
        setPdfData(fileUrl)
      }
    }

    fetchPdf()
  }, [fileUrl])

  const onDocumentLoadSuccess = ({ numPages }: { numPages: number }) => {
    console.log('PDFViewer: Document loaded successfully, pages:', numPages)
    setNumPages(numPages)
    setLoading(false)
    setError(null)
  }

  const onDocumentLoadError = (error: Error) => {
    console.error('PDF load error:', error)
    console.error('Failed URL:', fileUrl)

    // Provide more specific error messages
    let errorMessage = 'Failed to load PDF document'
    if (error.message?.includes('CORS')) {
      errorMessage = 'CORS error: Cannot load external PDF due to security restrictions'
    } else if (error.message?.includes('404')) {
      errorMessage = 'PDF not found at the provided URL'
    } else if (error.message?.includes('network')) {
      errorMessage = 'Network error: Cannot reach the PDF source'
    } else if (error.message?.includes('408')) {
      errorMessage = 'Timeout while fetching PDF from external source'
    } else if (error.message?.includes('502')) {
      errorMessage = 'Failed to fetch PDF from external source'
    } else if (error.message?.includes('403')) {
      errorMessage = 'Access denied: Domain not allowed for PDF viewing'
    } else if (fileUrl?.includes('proxy-pdf')) {
      errorMessage = 'Failed to load PDF through proxy - the source may not be a valid PDF file'
    } else if (fileUrl?.includes('lcsc.com') && !fileUrl.includes('.pdf')) {
      errorMessage = 'This appears to be a webpage link, not a direct PDF URL'
    }

    setError(errorMessage)
    setLoading(false)
  }

  const changePage = (offset: number) => {
    setPageNumber((prevPageNumber) => Math.max(1, Math.min(prevPageNumber + offset, numPages || 1)))
  }

  const changeScale = (scaleChange: number) => {
    setScale((prevScale) => Math.max(0.5, Math.min(prevScale + scaleChange, 3.0)))
  }

  const downloadFile = async () => {
    try {
      let downloadUrl = fileUrl

      // If it's a local API URL, we need to handle authentication
      if (fileUrl.startsWith('/api/') || fileUrl.startsWith('/utility/')) {
        const response = await fetch(fileUrl, {
          headers: {
            Authorization: `Bearer ${localStorage.getItem('auth_token')}`,
          },
        })

        if (!response.ok) {
          throw new Error(`Failed to download: ${response.status}`)
        }

        const blob = await response.blob()
        downloadUrl = URL.createObjectURL(blob)
      }

      const link = document.createElement('a')
      link.href = downloadUrl
      link.download = fileName
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)

      // Clean up blob URL if we created one
      if (downloadUrl !== fileUrl) {
        setTimeout(() => URL.revokeObjectURL(downloadUrl), 1000)
      }
    } catch (error) {
      console.error('Download failed:', error)
      alert('Download failed. Please try again.')
    }
  }

  return (
    <div className="fixed inset-0 z-50 bg-black/80 flex items-center justify-center">
      <div className="bg-gray-900 rounded-lg shadow-2xl w-full h-full max-w-6xl max-h-[90vh] flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-gray-700">
          <div className="flex items-center gap-3">
            <FileText className="w-6 h-6 text-blue-400" />
            <h3 className="text-lg font-semibold text-white truncate">{fileName}</h3>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={downloadFile}
              className="p-2 text-gray-300 hover:text-white hover:bg-gray-700 rounded transition-colors"
              title="Download PDF"
            >
              <Download className="w-5 h-5" />
            </button>
            <button
              onClick={onClose}
              className="p-2 text-gray-300 hover:text-white hover:bg-gray-700 rounded transition-colors"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Toolbar */}
        <div className="flex items-center justify-between p-4 border-b border-gray-700 bg-gray-800">
          <div className="flex items-center gap-4">
            {/* Page navigation */}
            <div className="flex items-center gap-2">
              <button
                onClick={() => changePage(-1)}
                disabled={pageNumber <= 1}
                className="p-2 text-gray-300 hover:text-white disabled:text-gray-500 disabled:cursor-not-allowed hover:bg-gray-700 rounded transition-colors"
              >
                <ChevronLeft className="w-4 h-4" />
              </button>

              <div className="flex items-center gap-2 text-sm text-gray-300">
                <span>Page</span>
                <input
                  type="number"
                  min={1}
                  max={numPages || 1}
                  value={pageNumber}
                  onChange={(e) =>
                    setPageNumber(
                      Math.max(1, Math.min(parseInt(e.target.value) || 1, numPages || 1))
                    )
                  }
                  className="w-16 px-2 py-1 bg-gray-700 border border-gray-600 rounded text-center text-white"
                />
                <span>of {numPages || '?'}</span>
              </div>

              <button
                onClick={() => changePage(1)}
                disabled={pageNumber >= (numPages || 1)}
                className="p-2 text-gray-300 hover:text-white disabled:text-gray-500 disabled:cursor-not-allowed hover:bg-gray-700 rounded transition-colors"
              >
                <ChevronRight className="w-4 h-4" />
              </button>
            </div>
          </div>

          {/* Zoom controls */}
          <div className="flex items-center gap-2">
            <button
              onClick={() => changeScale(-0.2)}
              disabled={scale <= 0.5}
              className="p-2 text-gray-300 hover:text-white disabled:text-gray-500 disabled:cursor-not-allowed hover:bg-gray-700 rounded transition-colors"
              title="Zoom out"
            >
              <ZoomOut className="w-4 h-4" />
            </button>

            <span className="text-sm text-gray-300 min-w-16 text-center">
              {Math.round(scale * 100)}%
            </span>

            <button
              onClick={() => changeScale(0.2)}
              disabled={scale >= 3.0}
              className="p-2 text-gray-300 hover:text-white disabled:text-gray-500 disabled:cursor-not-allowed hover:bg-gray-700 rounded transition-colors"
              title="Zoom in"
            >
              <ZoomIn className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* PDF Content */}
        <div className="flex-1 overflow-auto bg-gray-700 flex items-center justify-center p-4">
          {console.log('PDFViewer render state:', { loading, error: !!error, pdfData: !!pdfData })}
          {loading && (
            <div className="text-center text-gray-300">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500 mx-auto mb-4"></div>
              <p>Loading PDF...</p>
            </div>
          )}

          {error && (
            <div className="text-center text-red-400">
              <AlertCircle className="w-16 h-16 mx-auto mb-4" />
              <h3 className="text-lg font-semibold mb-2">Error Loading PDF</h3>
              <p className="text-sm">{error}</p>
              <button
                onClick={downloadFile}
                className="mt-4 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded transition-colors"
              >
                Try Download Instead
              </button>
            </div>
          )}

          {!loading && !error && pdfData && (
            <div className="pdf-container">
              {console.log(
                'PDFViewer: Rendering Document component with data:',
                typeof pdfData,
                pdfData instanceof ArrayBuffer ? `ArrayBuffer(${pdfData.byteLength})` : 'string'
              )}
              <Document
                file={pdfData}
                onLoadSuccess={onDocumentLoadSuccess}
                onLoadError={onDocumentLoadError}
                loading={<div>Loading PDF...</div>}
                error={<div>Failed to load PDF</div>}
              >
                <Page
                  pageNumber={pageNumber}
                  scale={scale}
                  renderTextLayer={true}
                  renderAnnotationLayer={true}
                />
              </Document>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

export default PDFViewer
