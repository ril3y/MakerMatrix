import { useState, useEffect, useCallback } from 'react'
import { settingsService } from '@/services/settings.service'
import toast from 'react-hot-toast'

interface PartData {
  part_name?: string
  part_number?: string
  location?: string
  category?: string
  quantity?: string
  description?: string
  additional_properties?: Record<string, any>
}

interface PrinterHookOptions {
  partData?: PartData
  onPrintSuccess?: () => void
}

export const usePrinter = (options: PrinterHookOptions = {}) => {
  const { partData, onPrintSuccess } = options

  // Printer state
  const [availablePrinters, setAvailablePrinters] = useState<any[]>([])
  const [selectedPrinter, setSelectedPrinter] = useState<string>('')
  const [printerInfo, setPrinterInfo] = useState<any>(null)

  // Label configuration state
  const [labelTemplate, setLabelTemplate] = useState('{part_name}')
  const [selectedLabelSize, setSelectedLabelSize] = useState('12mm')
  const [labelLength, setLabelLength] = useState(39)
  const [fitToLabel, setFitToLabel] = useState(true)
  const [includeQR, setIncludeQR] = useState(false)
  const [qrData, setQrData] = useState('part_number')

  // Preview state
  const [previewUrl, setPreviewUrl] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  // Load available printers
  const loadPrinters = useCallback(async () => {
    try {
      setLoading(true)
      const printers = await settingsService.getAvailablePrinters()
      setAvailablePrinters(printers || [])
      
      // Auto-select first printer if available
      if (printers?.length > 0 && !selectedPrinter) {
        setSelectedPrinter(printers[0].printer_id)
      }
    } catch (error) {
      toast.error('Failed to load printers')
      setAvailablePrinters([])
    } finally {
      setLoading(false)
    }
  }, [selectedPrinter])

  // Load printer info when printer changes
  const loadPrinterInfo = useCallback(async (printerId: string) => {
    if (!printerId) return

    try {
      const info = await settingsService.getPrinterInfo(printerId)
      setPrinterInfo(info)
      
      // Set default label size if supported
      if (info.supported_sizes?.length > 0) {
        const defaultSize = info.supported_sizes.find((s: any) => s.name === '12mm') || info.supported_sizes[0]
        setSelectedLabelSize(defaultSize.name)
      }
    } catch (error) {
      toast.error('Failed to load printer info')
      setPrinterInfo(null)
    }
  }, [])

  // Handle printer selection change
  const handlePrinterChange = useCallback(async (printerId: string) => {
    setSelectedPrinter(printerId)
    await loadPrinterInfo(printerId)
  }, [loadPrinterInfo])

  // Process label template with data
  const processLabelTemplate = useCallback((template: string, data: PartData) => {
    let processed = template

    // Replace standard placeholders
    const standardReplacements: Record<string, string> = {
      part_name: data.part_name || '',
      part_number: data.part_number || '',
      location: data.location || '',
      category: data.category || '',
      quantity: data.quantity || '',
      description: data.description || ''
    }

    for (const [key, value] of Object.entries(standardReplacements)) {
      processed = processed.replace(new RegExp(`\\{${key}\\}`, 'g'), value)
    }

    // Replace additional_properties fields
    if (data.additional_properties) {
      for (const [key, value] of Object.entries(data.additional_properties)) {
        processed = processed.replace(new RegExp(`\\{${key}\\}`, 'g'), String(value || ''))
      }
    }

    // Handle QR codes
    const qrMatches = processed.match(/\{qr=([^}]+)\}/g)
    if (qrMatches) {
      qrMatches.forEach(match => {
        const qrDataKey = match.replace(/\{qr=([^}]+)\}/, '$1')
        const qrValue = data[qrDataKey as keyof PartData] || 
                       data.additional_properties?.[qrDataKey] || 
                       qrDataKey
        processed = processed.replace(match, `[QR:${qrValue}]`)
      })
    }

    return processed
  }, [])

  // Generate preview
  const generatePreview = useCallback(async () => {
    try {
      const data = partData || {
        part_name: 'Test Part',
        part_number: 'TP-001',
        location: 'A1-B2',
        category: 'Electronics',
        quantity: '10',
        description: 'Test part description',
        additional_properties: {}
      }

      const requestData = {
        template: labelTemplate,
        text: "",
        label_size: selectedLabelSize,
        label_length: selectedLabelSize.includes('mm') ? labelLength : undefined,
        options: {
          fit_to_label: fitToLabel,
          include_qr: includeQR,
          qr_data: includeQR ? qrData : undefined
        },
        data
      }

      const blob = await settingsService.previewAdvancedLabel(requestData)
      const url = URL.createObjectURL(blob)
      setPreviewUrl(url)
    } catch (error) {
      toast.error('Failed to generate preview')
    }
  }, [labelTemplate, selectedLabelSize, labelLength, fitToLabel, includeQR, qrData, partData])

  // Print label
  const printLabel = useCallback(async () => {
    if (!selectedPrinter) {
      toast.error('Please select a printer')
      return false
    }

    try {
      const data = partData || {
        part_name: 'Test Part',
        part_number: 'TP-001',
        location: 'A1-B2',
        category: 'Electronics',
        quantity: '10',
        description: 'Test part description',
        additional_properties: {}
      }

      const requestData = {
        printer_id: selectedPrinter,
        template: labelTemplate,
        text: "",
        label_size: selectedLabelSize,
        label_length: selectedLabelSize.includes('mm') ? labelLength : undefined,
        options: {
          fit_to_label: fitToLabel,
          include_qr: includeQR,
          qr_data: includeQR ? qrData : undefined
        },
        data
      }

      const result = await settingsService.printAdvancedLabel(requestData)
      
      // Handle API response format: { status, message, data: { success, error, ... } }
      const printData = result.data || result
      const success = printData.success || result.status === 'success'
      const errorMessage = printData.error || printData.message || result.message
      
      if (success) {
        toast.success('✅ Label printed successfully!')
        onPrintSuccess?.()
        return true
      } else {
        toast.error(`❌ Print failed: ${errorMessage || 'Unknown error'}`)
        return false
      }
    } catch (error) {
      toast.error('Failed to print label')
      return false
    }
  }, [selectedPrinter, labelTemplate, selectedLabelSize, labelLength, fitToLabel, includeQR, qrData, partData, onPrintSuccess])

  // Test printer connection
  const testConnection = useCallback(async () => {
    if (!selectedPrinter) {
      toast.error('Please select a printer')
      return false
    }

    try {
      const result = await settingsService.testPrinterConnection(selectedPrinter)
      
      // Check both the data.success field and top-level status
      const isSuccess = result.data?.success || result.status === 'success'
      const errorMessage = result.data?.error || result.data?.message || result.message || 'Unknown error'
      
      if (isSuccess) {
        toast.success('✅ Printer connection successful!')
        return true
      } else {
        toast.error(`❌ Connection test failed: ${errorMessage}`)
        return false
      }
    } catch (error) {
      toast.error('Failed to test printer connection')
      return false
    }
  }, [selectedPrinter])

  // Load printers on mount
  useEffect(() => {
    loadPrinters()
  }, [loadPrinters])

  // Load printer info when selection changes
  useEffect(() => {
    if (selectedPrinter) {
      loadPrinterInfo(selectedPrinter)
    }
  }, [selectedPrinter, loadPrinterInfo])

  return {
    // State
    availablePrinters,
    selectedPrinter,
    printerInfo,
    labelTemplate,
    selectedLabelSize,
    labelLength,
    fitToLabel,
    includeQR,
    qrData,
    previewUrl,
    loading,

    // Setters
    setSelectedPrinter,
    setLabelTemplate,
    setSelectedLabelSize,
    setLabelLength,
    setFitToLabel,
    setIncludeQR,
    setQrData,

    // Actions
    loadPrinters,
    loadPrinterInfo,
    handlePrinterChange,
    processLabelTemplate,
    generatePreview,
    printLabel,
    testConnection
  }
}