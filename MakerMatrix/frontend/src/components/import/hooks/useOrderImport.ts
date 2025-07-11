import { useState, useRef, useCallback, useEffect } from 'react'
import toast from 'react-hot-toast'
import { apiClient } from '@/services/api'
import { previewFile } from '@/utils/filePreview'
import { tasksService } from '@/services/tasks.service'

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
  task_id?: string
  task_status?: 'pending' | 'running' | 'completed' | 'failed' | 'cancelled'
  progress_percentage?: number
}

export interface UseOrderImportProps {
  parserType: string
  parserName: string
  onImportComplete?: (result: ImportResult) => void
  validateFile?: (file: File) => boolean
  extractOrderInfoFromFilename?: (filename: string) => Promise<Partial<OrderInfo> | null>
  initialFile?: File | null
  initialPreviewData?: FilePreviewData | null
}

export const useOrderImport = ({
  parserType,
  parserName,
  onImportComplete,
  validateFile,
  extractOrderInfoFromFilename,
  initialFile,
  initialPreviewData
}: UseOrderImportProps) => {
  const [file, setFile] = useState<File | null>(initialFile || null)
  const [previewData, setPreviewData] = useState<FilePreviewData | null>(initialPreviewData || null)
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

  // Set showPreview if initial preview data is provided
  useEffect(() => {
    if (initialPreviewData && initialFile) {
      setShowPreview(true)
    }
  }, [initialPreviewData, initialFile])

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

  const pollProgress = useCallback(async (taskId?: string) => {
    if (!taskId) {
      console.log('No task ID available for progress tracking')
      return
    }
    
    try {
      const response = await tasksService.getTask(taskId)
      const task = response.data
      
      if (task) {
        const progress: ImportProgress = {
          processed_parts: 0,
          total_parts: 0,
          current_operation: task.current_step || 'Processing...',
          is_complete: task.status === 'completed' || task.status === 'failed' || task.status === 'cancelled',
          task_id: taskId,
          task_status: task.status,
          progress_percentage: task.progress_percentage || 0
        }
        
        // Try to extract part counts from task data if available
        if (task.input_data && task.input_data.part_ids) {
          progress.total_parts = task.input_data.part_ids.length
          progress.processed_parts = Math.round((task.progress_percentage || 0) * progress.total_parts / 100)
        }
        
        setImportProgress(progress)
        
        if (progress.is_complete) {
          if (progressPollInterval.current) {
            clearInterval(progressPollInterval.current)
            progressPollInterval.current = null
          }
          setShowProgress(false)
          setImporting(false)
          
          if (task.status === 'completed') {
            toast.success('Import and enrichment completed successfully!')
          } else if (task.status === 'failed') {
            toast.error(`Import task failed: ${task.error_message || 'Unknown error'}`)
          } else if (task.status === 'cancelled') {
            toast.error('Import task was cancelled')
          }
        }
      }
    } catch (error: any) {
      console.error('Failed to fetch task progress:', error)
      if (error.response?.status !== 404) {
        toast.error('Failed to fetch import progress')
      }
    }
  }, [])

  const startProgressPolling = useCallback((taskId?: string) => {
    if (!taskId) {
      console.log('No task ID provided for progress polling')
      return
    }
    progressPollInterval.current = setInterval(() => pollProgress(taskId), 2000)
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
      
      // Progress polling will be started after response if task ID is available
      
      let response
      const fileName = file.name.toLowerCase()
      
      // Use unified import endpoint for all file types (CSV, XLS, XLSX)
      const formData = new FormData()
      formData.append('file', file)
      formData.append('supplier_name', parserType)
      formData.append('order_number', orderInfo.order_number)
      formData.append('order_date', orderInfo.order_date || new Date().toISOString())
      formData.append('notes', orderInfo.notes)
      
      // Enable enrichment for better user experience
      formData.append('enable_enrichment', 'true')
      formData.append('enrichment_capabilities', 'get_part_details,fetch_datasheet')
      
      response = await apiClient.post('/api/import/file', formData, {
        headers: {
          'Content-Type': 'multipart/form-data'
        }
      })

      const result = response.data || response
      
      toast.success(`Imported ${result.imported_count || 0} parts successfully`)
      
      if (result.failed_count > 0) {
        toast.error(`${result.failed_count} parts failed to import`)
      }
      
      if (result.skipped_count > 0) {
        toast.info(`${result.skipped_count} parts were skipped (already exist)`)
      }
      
      // Extract task ID from warnings if available
      let taskId: string | undefined
      if (result.warnings && Array.isArray(result.warnings)) {
        for (const warning of result.warnings) {
          if (typeof warning === 'string' && warning.includes('Enrichment task created:')) {
            taskId = warning.split('Enrichment task created: ')[1]?.trim()
            break
          }
        }
      }
      
      if (taskId) {
        toast.info('Starting enrichment process...')
        setTimeout(() => {
          startProgressPolling(taskId)
        }, 1000)
      } else {
        // No enrichment task, show completion feedback
        setImportProgress({
          processed_parts: result.imported_count || 0,
          total_parts: result.imported_count || 0,
          current_operation: 'Import completed',
          is_complete: true
        })
        setTimeout(() => {
          setImporting(false)
          setShowProgress(false)
          setImportProgress(null)
        }, 2000) // Show completion for 2 seconds
      }

      onImportComplete?.(result)
      clearFile()

    } catch (error: any) {
      let errorMessage = 'Failed to import parts from file'
      
      // Provide more specific error messages
      if (error.response?.data?.message) {
        errorMessage = error.response.data.message
      } else if (error.response?.status === 401) {
        errorMessage = 'Authentication failed. Please log in again.'
      } else if (error.response?.status === 413) {
        errorMessage = 'File too large. Please select a smaller file.'
      } else if (error.response?.status === 500) {
        errorMessage = 'Server error. Please try again later.'
      } else if (error.message?.includes('Network Error')) {
        errorMessage = 'Network error. Please check your connection.'
      }
      
      toast.error(errorMessage)
      console.error('File import error:', error)
      
      // Show error in progress
      setImportProgress({
        processed_parts: 0,
        total_parts: 0,
        current_operation: 'Import failed',
        is_complete: true
      })
      
      setTimeout(() => {
        setImportProgress(null)
        setShowProgress(false)
      }, 3000) // Show error for 3 seconds
    } finally {
      stopProgressPolling()
      setImporting(false)
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