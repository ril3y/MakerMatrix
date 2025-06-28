import { useState, useRef, useCallback, useEffect } from 'react'
import toast from 'react-hot-toast'
import { apiClient } from '@/services/api'
import { previewFile } from '@/utils/filePreview'

export interface FilePreviewData {
  detected_parser: string | null
  detected_type?: string | null  // Backward compatibility
  type_info?: string
  headers: string[]
  preview_rows: any[]
  parsed_preview?: any[]
  total_rows: number
  is_supported: boolean
  validation_errors: string[]
  error?: string
  file_format?: string
}

export interface ImportResult {
  success_parts: string[]
  failed_parts: string[]
  order_id?: string
}

export interface OrderInfo {
  order_number: string
  order_date: string
  notes: string
}

export interface ImportProgress {
  processed_parts: number
  total_parts: number
  current_operation: string
  is_complete: boolean
}

export interface UseOrderImportProps {
  parserType: string
  parserName: string
  onImportComplete?: (result: ImportResult) => void
  validateFile?: (file: File) => boolean
  extractOrderInfoFromFilename?: (filename: string) => Promise<Partial<OrderInfo> | null>
}

export const useOrderImport = ({
  parserType,
  parserName,
  onImportComplete,
  validateFile,
  extractOrderInfoFromFilename
}: UseOrderImportProps) => {
  const [file, setFile] = useState<File | null>(null)
  const [previewData, setPreviewData] = useState<FilePreviewData | null>(null)
  const [loading, setLoading] = useState(false)
  const [importing, setImporting] = useState(false)
  const [showPreview, setShowPreview] = useState(false)
  const [importProgress, setImportProgress] = useState<ImportProgress | null>(null)
  const [showProgress, setShowProgress] = useState(false)
  const [orderInfo, setOrderInfo] = useState<OrderInfo>({
    order_number: '',
    order_date: new Date().toISOString().split('T')[0],
    notes: ''
  })

  const fileInputRef = useRef<HTMLInputElement>(null)
  const progressPollInterval = useRef<NodeJS.Timeout | null>(null)

  // Cleanup progress polling on unmount
  useEffect(() => {
    return () => {
      if (progressPollInterval.current) {
        clearInterval(progressPollInterval.current)
      }
    }
  }, [])

  const handleFileSelect = useCallback(async (selectedFile: File) => {
    if (!selectedFile) return

    const fileName = selectedFile.name.toLowerCase()
    const supportedExtensions = ['.csv', '.xls', '.xlsx']
    if (!supportedExtensions.some(ext => fileName.endsWith(ext))) {
      toast.error('Please select a supported file (CSV, XLS, or XLSX)')
      return
    }

    if (validateFile && !validateFile(selectedFile)) {
      return
    }

    setFile(selectedFile)
    setLoading(true)

    // Try to extract order info from filename
    if (extractOrderInfoFromFilename) {
      const extractedInfo = await extractOrderInfoFromFilename(selectedFile.name)
      if (extractedInfo) {
        setOrderInfo(prev => ({
          ...prev,
          order_date: extractedInfo.order_date || prev.order_date,
          order_number: extractedInfo.order_number || prev.order_number
        }))
        toast.success(`Auto-detected ${parserName} order information`)
      }
    }

    try {
      // Use frontend-only file preview
      const previewData = await previewFile(selectedFile)
      setPreviewData(previewData)
      
      if (previewData.validation_errors && previewData.validation_errors.length > 0) {
        // Only show error for critical issues, not warnings
        const criticalErrors = previewData.validation_errors.filter(error => 
          error.includes('Could not detect') || error.includes('empty') || error.includes('Failed to')
        )
        if (criticalErrors.length > 0) {
          toast.error(`File issue: ${criticalErrors[0]}`)
        } else {
          toast.success(`File processed - ${previewData.validation_errors.length} warning(s)`)
        }
      } else {
        toast.success(`File preview ready - ${previewData.total_rows} rows detected`)
      }
      
    } catch (error) {
      toast.error('Failed to parse file')
      console.error('File preview error:', error)
    } finally {
      setLoading(false)
    }
  }, [parserName, validateFile, extractOrderInfoFromFilename])

  const handleFileChange = useCallback((event: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFile = event.target.files?.[0]
    if (selectedFile) {
      handleFileSelect(selectedFile)
    }
  }, [handleFileSelect])

  const handleDrop = useCallback((event: React.DragEvent<HTMLDivElement>) => {
    event.preventDefault()
    const droppedFile = event.dataTransfer.files[0]
    if (droppedFile) {
      handleFileSelect(droppedFile)
    }
  }, [handleFileSelect])

  const handleDragOver = useCallback((event: React.DragEvent<HTMLDivElement>) => {
    event.preventDefault()
  }, [])

  const pollProgress = useCallback(async () => {
    try {
      const response = await apiClient.get('/api/import/import/progress')
      const progress = response.data || response
      if (progress && progress.processed_parts !== undefined) {
        setImportProgress(progress)
        
        if (progress.is_complete) {
          if (progressPollInterval.current) {
            clearInterval(progressPollInterval.current)
            progressPollInterval.current = null
          }
          setShowProgress(false)
          setImporting(false)
        }
      }
    } catch (error: any) {
      // Don't log 404 errors (no progress available yet)
      if (error.response?.status !== 404) {
        console.error('Failed to fetch import progress:', error)
      }
    }
  }, [])

  const startProgressPolling = useCallback(() => {
    progressPollInterval.current = setInterval(pollProgress, 1000)
  }, [pollProgress])

  const stopProgressPolling = useCallback(() => {
    if (progressPollInterval.current) {
      clearInterval(progressPollInterval.current)
      progressPollInterval.current = null
    }
  }, [])

  const handleImport = useCallback(async () => {
    if (!file || !previewData || !previewData.is_supported) {
      toast.error('Please select a valid file')
      return
    }

    setImporting(true)
    setImportProgress(null)
    setShowProgress(true)

    try {
      // Start progress polling
      setImportProgress({
        processed_parts: 0,
        total_parts: 0,
        current_operation: 'Starting import...',
        is_complete: false
      })
      
      setTimeout(() => {
        startProgressPolling()
      }, 500)
      
      let response
      const fileName = file.name.toLowerCase()
      
      if (fileName.endsWith('.csv')) {
        // Handle CSV files with text content
        const fileContent = await file.text()
        response = await apiClient.post('/api/import/import/with-progress', {
          csv_content: fileContent,
          parser_type: parserType,
          order_info: {
            ...orderInfo,
            supplier: previewData.detected_parser || previewData.type_info,
            order_date: orderInfo.order_date || new Date().toISOString()
          }
        })
      } else {
        // Handle XLS files with file upload
        const formData = new FormData()
        formData.append('file', file)
        formData.append('supplier_name', parserType)
        formData.append('order_number', orderInfo.order_number)
        formData.append('order_date', orderInfo.order_date || new Date().toISOString())
        formData.append('notes', orderInfo.notes)
        
        response = await apiClient.post('/api/import/file', formData, {
          headers: {
            'Content-Type': 'multipart/form-data'
          }
        })
      }

      const result = response.data || response
      
      toast.success(`Imported ${result.success_parts?.length || 0} parts successfully`)
      
      if (result.failed_parts?.length > 0) {
        toast.error(`${result.failed_parts.length} parts failed to import`)
      }

      onImportComplete?.(result)
      clearFile()

    } catch (error) {
      toast.error('Failed to import parts from file')
      console.error('File import error:', error)
    } finally {
      stopProgressPolling()
      setImporting(false)
      setShowProgress(false)
      setImportProgress(null)
    }
  }, [file, previewData, parserType, orderInfo, onImportComplete, startProgressPolling, stopProgressPolling])

  const clearFile = useCallback(() => {
    setFile(null)
    setPreviewData(null)
    setShowPreview(false)
    setImportProgress(null)
    setOrderInfo({
      order_number: '',
      order_date: new Date().toISOString().split('T')[0],
      notes: ''
    })
    if (fileInputRef.current) {
      fileInputRef.current.value = ''
    }
  }, [])

  const updateOrderInfo = useCallback((updates: Partial<OrderInfo>) => {
    setOrderInfo(prev => ({ ...prev, ...updates }))
  }, [])

  return {
    // State
    file,
    previewData,
    loading,
    importing,
    showPreview,
    importProgress,
    showProgress,
    orderInfo,
    
    // Refs
    fileInputRef,
    
    // Actions
    handleFileSelect,
    handleFileChange,
    handleDrop,
    handleDragOver,
    handleImport,
    clearFile,
    updateOrderInfo,
    setShowPreview
  }
}