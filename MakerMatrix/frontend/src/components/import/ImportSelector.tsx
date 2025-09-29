import React, { useState, useCallback, useRef, useEffect } from 'react'
import { motion } from 'framer-motion'
import { FileText, ChevronDown, Upload, CheckCircle, AlertCircle, File, X, Settings, Zap, Info, DollarSign, Image, Package, RefreshCw } from 'lucide-react'
import UnifiedFileImporter from './UnifiedFileImporter'
import { ImportResult } from './hooks/useOrderImport'
import { apiClient } from '@/services/api'
import { previewFile } from '@/utils/filePreview'
import toast from 'react-hot-toast'
import { DynamicAddSupplierModal } from '../../pages/suppliers/DynamicAddSupplierModal'

interface ImportSelectorProps {
  onImportComplete?: (result: ImportResult) => void
}

interface FilePreviewData {
  filename: string
  size: number
  type: string
  detected_parser: string | null
  preview_rows: any[]
  headers: string[]
  total_rows: number | string
  is_supported: boolean
  validation_errors: string[]
  file_format: string
}

const ImportSelector: React.FC<ImportSelectorProps> = ({ onImportComplete }) => {
  const [selectedParser, setSelectedParser] = useState<string>('')
  const [detectedParser, setDetectedParser] = useState<string>('')
  const [autoDetected, setAutoDetected] = useState<boolean>(false)
  const [dragActive, setDragActive] = useState<boolean>(false)
  const [uploadedFile, setUploadedFile] = useState<File | null>(null)
  const [filePreview, setFilePreview] = useState<FilePreviewData | null>(null)
  const [isProcessing, setIsProcessing] = useState<boolean>(false)
  const [parsers, setParsers] = useState<any[]>([])
  const [isLoadingParsers, setIsLoadingParsers] = useState<boolean>(true)
  const [selectedEnrichmentCapabilities, setSelectedEnrichmentCapabilities] = useState<string[]>([])
  const [enableAutoEnrichment, setEnableAutoEnrichment] = useState<boolean>(true)
  const [showSupplierModal, setShowSupplierModal] = useState<boolean>(false)
  const fileInputRef = useRef<HTMLInputElement>(null)

  // Helper functions for capability display
  const getCapabilityDisplayName = (capability: string): string => {
    const displayNames: Record<string, string> = {
      'get_part_details': 'Part Details',
      'fetch_datasheet': 'Datasheets',
      'fetch_pricing_stock': 'Pricing & Stock',
      'fetch_image': 'Product Images',
      'fetch_specifications': 'Specifications'
    }
    return displayNames[capability] || capability
  }

  const getCapabilityIcon = (capability: string) => {
    const icons: Record<string, any> = {
      'get_part_details': <Info className="w-4 h-4" />,
      'fetch_datasheet': <FileText className="w-4 h-4" />,
      'fetch_pricing_stock': <DollarSign className="w-4 h-4" />,
      'fetch_image': <Image className="w-4 h-4" />,
      'fetch_specifications': <RefreshCw className="w-4 h-4" />
    }
    return icons[capability] || <Package className="w-4 h-4" />
  }

  // Function to refresh suppliers list
  const refreshSuppliers = async () => {
    setIsLoadingParsers(true)
    await loadAvailableSuppliers()
  }

  // Handle successful supplier configuration
  const handleSupplierConfigured = async () => {
    setShowSupplierModal(false)
    toast.success('Supplier configured successfully!')
    await refreshSuppliers()
  }

  // Load available suppliers dynamically from API
  const loadAvailableSuppliers = useCallback(async () => {
      try {
        setIsLoadingParsers(true)
        
        // First check if there are any configured suppliers
        let configuredSuppliers = []
        try {
          const configResponse = await apiClient.get('/api/suppliers/config/suppliers')
          configuredSuppliers = configResponse.data?.data || []
          console.log('Configured suppliers from DB:', configuredSuppliers)
        } catch (configError) {
          console.warn('Could not load configured suppliers, will use import suppliers only:', configError)
        }
        
        // Get import capabilities
        const response = await apiClient.get('/api/import/suppliers')
        console.log('Import suppliers response:', response)
        
        if (response.data?.data || response.data) {
          const importSuppliers = response.data?.data || response.data || []
          console.log('Available import suppliers:', importSuppliers)
          
          let availableSuppliers = []
          
          if (configuredSuppliers.length > 0) {
            // Filter by configured suppliers if we have any
            const enabledSupplierNames = configuredSuppliers
              .filter(config => config.enabled)
              .map(config => config.supplier_name.toLowerCase())
            
            console.log('Enabled supplier names:', enabledSupplierNames)
            
            availableSuppliers = importSuppliers
              .filter(supplier => 
                enabledSupplierNames.includes(supplier.name.toLowerCase()) &&
                supplier.import_available
              )
          } else {
            // If no configured suppliers, show all available import suppliers
            availableSuppliers = importSuppliers.filter(supplier => supplier.import_available)
          }
          
          // Map to frontend format
          const mappedSuppliers = availableSuppliers.map(supplier => {
            let description = `${supplier.display_name} (${supplier.supported_file_types.join(', ').toUpperCase()})`
            let color = 'bg-blue-500'
            
            // Add configuration status to description
            if (supplier.is_configured) {
              description += ' - Configured'
              color = 'bg-green-500'
            } else if (supplier.configuration_status === 'partial') {
              description += ' - Partial (Import only)'
              color = 'bg-yellow-500'
            } else {
              description += ' - Not configured'
              color = 'bg-gray-500'
            }
            
            return {
              id: supplier.name,
              name: supplier.display_name,
              description,
              color,
              supported: supplier.import_available,
              import_available: supplier.import_available,
              missing_credentials: supplier.missing_credentials || [],
              is_configured: supplier.is_configured || false,
              configuration_status: supplier.configuration_status || 'not_configured',
              enrichment_capabilities: supplier.enrichment_capabilities || [],
              enrichment_available: supplier.enrichment_available || false,
              enrichment_missing_credentials: supplier.enrichment_missing_credentials || []
            }
          })
          
          console.log('Final mapped suppliers:', mappedSuppliers)
          
          setParsers(mappedSuppliers)
          
          if (mappedSuppliers.length === 0) {
            if (configuredSuppliers.length === 0) {
              console.log('No suppliers configured at all')
              toast.error('No suppliers are configured. Please configure suppliers in Settings.')
            } else {
              console.log('Suppliers configured but none available for import')
              toast.error('Configured suppliers are not available for import. Check supplier configurations.')
            }
          }
        } else {
          console.error('Failed to load suppliers:', response.message)
          toast.error('Failed to load available suppliers')
        }
      } catch (error) {
        console.error('Error loading suppliers:', error)
        
        // Check if this is a backend connectivity issue
        const isNetworkError = error instanceof Error && (
          error.message.includes('fetch') ||
          error.message.includes('Network') ||
          error.message.includes('Failed to fetch') ||
          error.message.includes('ERR_NETWORK') ||
          error.message.includes('ERR_INTERNET_DISCONNECTED')
        )
        
        if (isNetworkError) {
          toast.error('Backend not connected - using fallback suppliers')
        } else {
          toast.error('Error loading available suppliers')
        }
        
        // Fallback to hardcoded suppliers
        setParsers([
          {
            id: 'lcsc',
            name: 'LCSC Electronics',
            supported_file_types: ['csv'],
            component: UnifiedFileImporter
          }
        ])
      } finally {
        setIsLoadingParsers(false)
      }
    }, [])

  useEffect(() => {
    loadAvailableSuppliers()
  }, [loadAvailableSuppliers])

  const selectedParserInfo = parsers.find(p => p.id === selectedParser || p.name === selectedParser)

  // Auto-select default enrichment capabilities when parser is selected
  useEffect(() => {
    if (selectedParser && selectedParserInfo && selectedParserInfo.enrichment_available) {
      const capabilities = selectedParserInfo.enrichment_capabilities || []

      // For DigiKey and other suppliers, auto-select recommended capabilities
      let defaultCapabilities: string[] = []

      if (selectedParser.toLowerCase() === 'digikey') {
        // DigiKey recommended capabilities
        defaultCapabilities = capabilities.filter(cap =>
          cap === 'get_part_details' ||
          cap === 'fetch_datasheet' ||
          cap === 'fetch_pricing_stock'
        )
      } else {
        // For other suppliers, select the most common capabilities
        defaultCapabilities = capabilities.filter(cap =>
          cap === 'get_part_details' ||
          cap === 'fetch_datasheet'
        )
      }

      if (enableAutoEnrichment && defaultCapabilities.length > 0) {
        setSelectedEnrichmentCapabilities(defaultCapabilities)
        toast.success(`Auto-selected ${defaultCapabilities.length} enrichment capabilities for ${selectedParserInfo.name}`)
      }
    }
  }, [selectedParser, selectedParserInfo, enableAutoEnrichment])
  

  // File upload functions
  const handleFileSelect = async (file: File) => {
    if (!file) return

    const fileExtension = file.name.toLowerCase().split('.').pop()
    const allowedExtensions = ['csv', 'xls', 'xlsx']

    if (!allowedExtensions.includes(fileExtension || '')) {
      toast.error('Please upload a CSV or XLS file')
      return
    }

    setIsProcessing(true)
    setUploadedFile(file)

    try {
      // Get file preview using frontend-only processing
      const previewData = await previewFile(file)
      
      // Auto-detect parser from preview data
      const suggestedParser = previewData.detected_parser || ''
      
      if (suggestedParser) {
        setDetectedParser(suggestedParser)
        setSelectedParser(suggestedParser)
        setAutoDetected(true)
        toast.success(`Auto-detected: ${parsers.find(p => p.id === suggestedParser)?.name || suggestedParser}`)
      } else {
        toast('File uploaded successfully, please select a parser type')
      }
      
      // Set preview data from frontend processing
      const fileExtension = file.name.toLowerCase().split('.').pop()
      setFilePreview({
        filename: file.name,
        size: file.size,
        type: file.type,
        detected_parser: suggestedParser,
        file_format: fileExtension?.toUpperCase() || 'Unknown',
        total_rows: previewData.total_rows || 0,
        headers: previewData.headers || [],
        is_supported: previewData.is_supported !== false,
        validation_errors: previewData.validation_errors || [],
        preview_rows: previewData.preview_rows || []
      })
      
      if (previewData.validation_errors && previewData.validation_errors.length > 0) {
        toast.error(`Validation issues: ${previewData.validation_errors[0]}`)
      }
      
    } catch (error) {
      console.error('File preview error:', error)
      
      // Check if this is a backend connectivity issue
      const isNetworkError = error instanceof Error && (
        error.message.includes('fetch') ||
        error.message.includes('Network') ||
        error.message.includes('Failed to fetch') ||
        error.message.includes('ERR_NETWORK') ||
        error.message.includes('ERR_INTERNET_DISCONNECTED')
      )
      
      const isBackendDown = error instanceof Error && (
        error.message.includes('500') ||
        error.message.includes('502') ||
        error.message.includes('503') ||
        error.message.includes('504')
      )
      
      if (isNetworkError || isBackendDown) {
        toast.error('Backend not connected - please check if the server is running')
      } else {
        toast.error('Failed to preview file')
      }
      
      // Fallback to basic file info if preview fails
      const filename = file.name.toLowerCase()
      let suggestedParser = ''
      
      if (filename.includes('lcsc')) {
        suggestedParser = 'lcsc'
      } else if (filename.includes('digikey') || filename.includes('dk_')) {
        suggestedParser = 'digikey'  
      } else if (filename.includes('mouser')) {
        suggestedParser = 'mouser'
      }
      
      if (suggestedParser) {
        setDetectedParser(suggestedParser)
        setSelectedParser(suggestedParser)
        setAutoDetected(true)
      }
      
      // Set basic file info for preview
      const fileExtension = file.name.toLowerCase().split('.').pop()
      const isValidFileFormat = ['csv', 'xls', 'xlsx'].includes(fileExtension || '')
      
      let errorMessage = 'Could not preview file content'
      let supportedStatus = !!suggestedParser && isValidFileFormat
      
      if (isNetworkError || isBackendDown) {
        errorMessage = 'Backend not connected - cannot validate file format'
        // For backend connectivity issues, assume the file might be supported if format is valid
        supportedStatus = isValidFileFormat
      } else if (!isValidFileFormat) {
        errorMessage = 'File format not supported. Please use CSV or XLS files.'
        supportedStatus = false
      }
      
      setFilePreview({
        filename: file.name,
        size: file.size,
        type: file.type,
        detected_parser: suggestedParser,
        file_format: fileExtension?.toUpperCase() || 'Unknown',
        total_rows: 'Error loading preview',
        headers: [],
        is_supported: supportedStatus,
        validation_errors: [errorMessage]
      })
    } finally {
      setIsProcessing(false)
    }
  }

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setDragActive(false)
    
    const files = Array.from(e.dataTransfer.files)
    if (files.length > 0) {
      handleFileSelect(files[0])
    }
  }, [])

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setDragActive(true)
  }, [])

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setDragActive(false)
  }, [])

  const clearFile = () => {
    setUploadedFile(null)
    setFilePreview(null)
    setSelectedParser('')
    setDetectedParser('')
    setAutoDetected(false)
    setSelectedEnrichmentCapabilities([])
    setEnableAutoEnrichment(true)
    if (fileInputRef.current) {
      fileInputRef.current.value = ''
    }
  }

  return (
    <div className="space-y-6">
      <div className="text-center">
        <h3 className="text-lg font-semibold text-primary mb-2 flex items-center justify-center gap-2">
          <FileText className="w-5 h-5" />
          Import Parts from Order Files
        </h3>
        <p className="text-secondary">
          Upload your order files (CSV or XLS) below. We'll automatically detect the supplier and format.
        </p>
      </div>

      {!isLoadingParsers && parsers.length === 0 ? (
        <div className="card p-8 text-center">
          <div className="w-16 h-16 bg-blue-100 dark:bg-blue-900/30 rounded-full flex items-center justify-center mx-auto mb-4">
            <Settings className="w-8 h-8 text-blue-600 dark:text-blue-400" />
          </div>
          <h4 className="text-lg font-medium text-gray-900 dark:text-white mb-2">
            No Suppliers Configured
          </h4>
          <p className="text-gray-600 dark:text-gray-300 mb-6">
            To import supplier order files, you need to configure at least one supplier first.
            <br />
            Supported suppliers include LCSC, DigiKey, Mouser, and more.
          </p>
          <button
            onClick={() => setShowSupplierModal(true)}
            className="inline-flex items-center px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium rounded-md transition-colors"
          >
            <Settings className="w-4 h-4 mr-2" />
            Configure Suppliers
          </button>
        </div>
      ) : (
        <>
          <div className="card p-6">
            <div 
          className={`border-2 border-dashed rounded-lg p-8 transition-all cursor-pointer ${
            dragActive 
              ? 'border-primary bg-primary/5' 
              : uploadedFile 
              ? 'border-success bg-success/5' 
              : 'border-border hover:border-primary/50 hover:bg-primary/5'
          }`}
          onDrop={handleDrop}
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onClick={() => !uploadedFile && fileInputRef.current?.click()}
        >
          <input
            ref={fileInputRef}
            type="file"
            className="hidden"
            accept=".csv,.xls,.xlsx"
            onChange={(e) => {
              const file = e.target.files?.[0]
              if (file) {
                handleFileSelect(file)
                // Clear the input value to allow re-selection of the same file
                if (fileInputRef.current) {
                  fileInputRef.current.value = ''
                }
              }
            }}
          />

          <div className="text-center">
            {isProcessing ? (
              <div className="flex flex-col items-center gap-4">
                <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary"></div>
                <p className="text-primary font-medium">Processing file...</p>
              </div>
            ) : uploadedFile ? (
              <div className="flex flex-col items-center gap-4">
                <div className="flex items-center gap-3 bg-background-secondary p-4 rounded-lg">
                  <File className="w-8 h-8 text-success" />
                  <div className="text-left">
                    <p className="font-medium text-primary">{uploadedFile.name}</p>
                    <p className="text-sm text-secondary">
                      {(uploadedFile.size / 1024).toFixed(1)} KB
                      {filePreview && ` • ${filePreview.total_rows} rows`}
                    </p>
                  </div>
                  <button
                    onClick={(e) => {
                      e.stopPropagation()
                      clearFile()
                    }}
                    className="text-secondary hover:text-error transition-colors"
                  >
                    <X className="w-5 h-5" />
                  </button>
                </div>
                
                {autoDetected && detectedParser && (
                  <div className="flex items-center gap-2 text-success">
                    <CheckCircle className="w-5 h-5" />
                    <span className="font-medium">
                      Auto-detected: {parsers.find(p => p.id === detectedParser)?.name}
                    </span>
                  </div>
                )}
              </div>
            ) : (
              <div className="flex flex-col items-center gap-4">
                <Upload className="w-12 h-12 text-muted" />
                <div>
                  <p className="text-lg font-medium text-primary mb-2">
                    Drop your order file here or click to browse
                  </p>
                  <p className="text-sm text-secondary">
                    {isLoadingParsers 
                      ? 'Loading available suppliers...' 
                      : `Supports CSV, XLS, and XLSX files from ${parsers.map(p => p.name).join(', ')}, and more`
                    }
                  </p>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Parser Selection Dropdown */}
        {uploadedFile && (
          <div className="mt-6 space-y-4">
            <div>
              <label className="block text-sm font-medium text-primary mb-2">
                Supplier/Parser Type
                {autoDetected && (
                  <span className="ml-2 text-xs text-success">(Auto-detected)</span>
                )}
              </label>
              <div className="relative">
                <select
                  value={selectedParser}
                  onChange={(e) => setSelectedParser(e.target.value)}
                  className="input w-full appearance-none pr-10"
                  disabled={isLoadingParsers}
                >
                  {/* All options have unique keys */}
                  <option key="placeholder" value="">
                    {isLoadingParsers ? 'Loading suppliers...' : 'Select a parser...'}
                  </option>
                  {parsers.map((parser, index) => (
                    <option key={parser.id || `parser-${index}`} value={parser.id} disabled={!parser.import_available}>
                      {parser.name}
                      {!parser.import_available ? ' (Configuration required)' : ''}
                    </option>
                  ))}
                </select>
                <ChevronDown className="absolute right-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-secondary pointer-events-none" />
              </div>
            </div>

            {/* Configuration Warning */}
            {selectedParserInfo && !selectedParserInfo.is_configured && (
              <div className="bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-700 rounded-lg p-4">
                <div className="flex items-start">
                  <AlertCircle className="w-5 h-5 text-yellow-600 dark:text-yellow-400 mt-0.5 mr-3 flex-shrink-0" />
                  <div>
                    <h5 className="font-medium text-yellow-800 dark:text-yellow-200 mb-1">
                      {selectedParserInfo.configuration_status === 'partial' ? 'Partial Configuration' : 'Supplier Not Configured'}
                    </h5>
                    <p className="text-sm text-yellow-700 dark:text-yellow-300 mb-3">
                      {selectedParserInfo.configuration_status === 'partial' 
                        ? `${selectedParserInfo.name} can import files but is not fully configured. You'll be able to import parts but won't have access to enrichment features like datasheet downloads or real-time pricing.`
                        : `${selectedParserInfo.name} is not configured in your system. Please configure this supplier to access all features.`
                      }
                    </p>
                    <button
                      onClick={() => setShowSupplierModal(true)}
                      className="inline-flex items-center px-3 py-1.5 bg-yellow-600 hover:bg-yellow-700 text-white text-sm font-medium rounded-md transition-colors"
                    >
                      <Settings className="w-4 h-4 mr-1.5" />
                      Configure Supplier
                    </button>
                  </div>
                </div>
              </div>
            )}

            {/* Enrichment Capabilities Selection */}
            {selectedParserInfo && selectedParserInfo.enrichment_available && (
              <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-700 rounded-lg p-4">
                <div className="flex items-start">
                  <Zap className="w-5 h-5 text-blue-600 dark:text-blue-400 mt-0.5 mr-3 flex-shrink-0" />
                  <div className="flex-1">
                    <div className="flex items-center justify-between mb-2">
                      <h5 className="font-medium text-blue-800 dark:text-blue-200">
                        Auto-Enrichment Options
                        {selectedParser.toLowerCase() === 'digikey' && (
                          <span className="ml-2 text-xs bg-green-100 dark:bg-green-900/30 text-green-800 dark:text-green-200 px-2 py-1 rounded-full">
                            Recommended for DigiKey
                          </span>
                        )}
                      </h5>
                      <label className="flex items-center">
                        <input
                          type="checkbox"
                          checked={enableAutoEnrichment}
                          onChange={(e) => {
                            setEnableAutoEnrichment(e.target.checked)
                            if (!e.target.checked) {
                              setSelectedEnrichmentCapabilities([])
                            }
                          }}
                          className="mr-2 rounded border-blue-300 text-blue-600 focus:ring-blue-500"
                        />
                        <span className="text-sm text-blue-700 dark:text-blue-300 font-medium">
                          Enable Auto-Enrichment
                        </span>
                      </label>
                    </div>
                    <p className="text-sm text-blue-700 dark:text-blue-300 mb-3">
                      {selectedParserInfo.name} can automatically enrich imported parts with additional data like datasheets, images, and pricing information.
                    </p>

                    {enableAutoEnrichment && (
                      <div className="space-y-2">
                        <div className="flex items-center gap-2 mb-2">
                          <span className="text-sm font-medium text-blue-800 dark:text-blue-200">
                            Select capabilities to enable:
                          </span>
                          <button
                            onClick={() => setSelectedEnrichmentCapabilities(selectedParserInfo.enrichment_capabilities || [])}
                            className="text-xs text-blue-600 dark:text-blue-400 hover:text-blue-800 dark:hover:text-blue-200"
                          >
                            Select All
                          </button>
                          <span className="text-xs text-blue-600 dark:text-blue-400">|</span>
                          <button
                            onClick={() => setSelectedEnrichmentCapabilities([])}
                            className="text-xs text-blue-600 dark:text-blue-400 hover:text-blue-800 dark:hover:text-blue-200"
                          >
                            Clear All
                          </button>
                        </div>
                        {selectedParserInfo.enrichment_capabilities.map((capability) => (
                          <label key={capability} className="flex items-center hover:bg-blue-100 dark:hover:bg-blue-900/30 p-2 rounded transition-colors">
                            <input
                              type="checkbox"
                              checked={selectedEnrichmentCapabilities.includes(capability)}
                              onChange={(e) => {
                                if (e.target.checked) {
                                  setSelectedEnrichmentCapabilities(prev => [...prev, capability])
                                } else {
                                  setSelectedEnrichmentCapabilities(prev => prev.filter(c => c !== capability))
                                }
                              }}
                              className="mr-3 rounded border-blue-300 text-blue-600 focus:ring-blue-500"
                            />
                            <div className="flex items-center space-x-2 flex-1">
                              {getCapabilityIcon(capability)}
                              <span className="text-sm text-blue-700 dark:text-blue-300 font-medium">
                                {getCapabilityDisplayName(capability)}
                              </span>
                              {selectedParser.toLowerCase() === 'digikey' &&
                               (capability === 'get_part_details' || capability === 'fetch_datasheet' || capability === 'fetch_pricing_stock') && (
                                <span className="text-xs bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-300 px-1.5 py-0.5 rounded">
                                  Recommended
                                </span>
                              )}
                            </div>
                          </label>
                        ))}

                        {selectedEnrichmentCapabilities.length > 0 && (
                          <div className="mt-3 p-2 bg-green-100 dark:bg-green-900/30 rounded text-sm">
                            <p className="text-green-800 dark:text-green-200">
                              <strong>Selected:</strong> {selectedEnrichmentCapabilities.length} capability(ies) will be applied after import.
                            </p>
                          </div>
                        )}
                      </div>
                    )}

                    {selectedParserInfo.enrichment_missing_credentials?.length > 0 && (
                      <div className="mt-3 p-2 bg-yellow-100 dark:bg-yellow-900/30 rounded text-sm">
                        <p className="text-yellow-800 dark:text-yellow-200">
                          <strong>Note:</strong> Some enrichment features may require additional configuration: {selectedParserInfo.enrichment_missing_credentials.join(', ')}
                        </p>
                      </div>
                    )}
                  </div>
                </div>
              </div>
            )}

            {/* Enrichment Not Available Warning */}
            {selectedParserInfo && !selectedParserInfo.enrichment_available && selectedParserInfo.enrichment_missing_credentials?.length > 0 && (
              <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-700 rounded-lg p-4">
                <div className="flex items-start">
                  <Zap className="w-5 h-5 text-red-600 dark:text-red-400 mt-0.5 mr-3 flex-shrink-0" />
                  <div className="flex-1">
                    <h5 className="font-medium text-red-800 dark:text-red-200 mb-2">
                      Auto-Enrichment Not Available
                    </h5>
                    <p className="text-sm text-red-700 dark:text-red-300 mb-3">
                      {selectedParserInfo.name} enrichment requires additional configuration to access detailed part information, datasheets, and pricing.
                    </p>
                    <div className="bg-red-100 dark:bg-red-900/40 border border-red-200 dark:border-red-700 rounded p-3">
                      <p className="text-sm text-red-800 dark:text-red-200 font-medium mb-2">
                        ⚙️ Configuration Required:
                      </p>
                      <ul className="text-sm text-red-700 dark:text-red-300 space-y-1">
                        {selectedParserInfo.enrichment_missing_credentials.map((cred) => (
                          <li key={cred} className="flex items-center">
                            <span className="w-1.5 h-1.5 bg-red-500 rounded-full mr-2"></span>
                            {cred.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase())}
                          </li>
                        ))}
                      </ul>
                      {selectedParser.toLowerCase() === 'digikey' && (
                        <div className="mt-3 pt-3 border-t border-red-200 dark:border-red-700">
                          <p className="text-xs text-red-600 dark:text-red-400">
                            💡 <strong>For DigiKey:</strong> Register at{' '}
                            <a href="https://developer.digikey.com" target="_blank" rel="noopener noreferrer"
                               className="underline hover:text-red-800 dark:hover:text-red-200">
                              developer.digikey.com
                            </a>
                            {' '}to get API credentials.
                          </p>
                        </div>
                      )}
                    </div>
                    <div className="mt-3 p-2 bg-blue-100 dark:bg-blue-900/40 rounded text-sm">
                      <p className="text-blue-800 dark:text-blue-200">
                        <strong>Import will still work</strong> - you'll get basic part information from the file,
                        but no additional enrichment data like datasheets or real-time pricing.
                      </p>
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* File Preview Info */}
            {filePreview && (
              <div className="bg-background-secondary rounded-lg p-4">
                <h5 className="font-medium text-primary mb-2">File Preview</h5>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                  <div>
                    <span className="text-secondary">Format:</span>
                    <span className="text-primary ml-2 font-medium">
                      {filePreview.file_format?.toUpperCase() || 'Unknown'}
                    </span>
                  </div>
                  <div>
                    <span className="text-secondary">Rows:</span>
                    <span className="text-primary ml-2 font-medium">{filePreview.total_rows}</span>
                  </div>
                  <div>
                    <span className="text-secondary">Columns:</span>
                    <span className="text-primary ml-2 font-medium">{filePreview.headers?.length || 0}</span>
                  </div>
                  <div>
                    <span className="text-secondary">Status:</span>
                    <span className={`ml-2 font-medium ${filePreview.is_supported ? 'text-success' : 'text-error'}`}>
                      {filePreview.is_supported 
                        ? 'Supported' 
                        : filePreview.validation_errors?.some(err => err.includes('Backend not connected'))
                          ? 'Backend Offline'
                          : 'Not Supported'
                      }
                    </span>
                  </div>
                </div>
                
                {filePreview.validation_errors?.length > 0 && (
                  <div className={`mt-3 p-3 rounded border ${
                    filePreview.validation_errors.some(err => err.includes('Backend not connected'))
                      ? 'bg-yellow-50 dark:bg-yellow-900/20 border-yellow-200 dark:border-yellow-700'
                      : 'bg-error/10 border-error/20'
                  }`}>
                    <p className={`text-sm font-medium mb-1 ${
                      filePreview.validation_errors.some(err => err.includes('Backend not connected'))
                        ? 'text-yellow-800 dark:text-yellow-200'
                        : 'text-error'
                    }`}>
                      {filePreview.validation_errors.some(err => err.includes('Backend not connected'))
                        ? 'Connection Issues:'
                        : 'Validation Issues:'
                      }
                    </p>
                    <ul className={`text-sm list-disc list-inside ${
                      filePreview.validation_errors.some(err => err.includes('Backend not connected'))
                        ? 'text-yellow-700 dark:text-yellow-300'
                        : 'text-error'
                    }`}>
                      {filePreview.validation_errors?.map((error, index) => (
                        <li key={index}>{error}</li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            )}
          </div>
        )}
          </div>


          {/* Selected Parser Component */}
          {uploadedFile && selectedParser && (
            <motion.div
              key={selectedParser}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.3 }}
            >
              {selectedParserInfo ? (
                <UnifiedFileImporter
                  uploadedFile={uploadedFile}
                  filePreview={filePreview}
                  parserType={selectedParser}
                  parserName={selectedParserInfo.name}
                  description={selectedParserInfo.description}
                  selectedEnrichmentCapabilities={selectedEnrichmentCapabilities}
                  supplierCapabilities={selectedParserInfo}
                  onImportComplete={(result) => {
                    onImportComplete?.(result)
                    // Reset state after successful import
                    clearFile()
                  }}
                />
              ) : (
                <div className="border-2 border-red-200 dark:border-red-800 bg-red-50 dark:bg-red-900/20 rounded-lg p-8 text-center">
                  <div className="w-16 h-16 bg-red-100 dark:bg-red-900/30 rounded-full flex items-center justify-center mx-auto mb-4">
                    <AlertCircle className="w-8 h-8 text-red-600 dark:text-red-400" />
                  </div>
                  <h4 className="text-lg font-medium text-red-800 dark:text-red-200 mb-2">
                    Parser Not Available
                  </h4>
                  <p className="text-red-700 dark:text-red-300 mb-4">
                    The selected parser is not available. Please select a different parser or check your configuration.
                  </p>
                  {selectedParserInfo && !selectedParserInfo.is_configured && (
                    <div className="mt-4 p-3 bg-yellow-100 dark:bg-yellow-900/30 rounded border border-yellow-300 dark:border-yellow-700">
                      <p className="text-sm text-yellow-800 dark:text-yellow-200 mb-2">
                        <strong>Note:</strong> {selectedParserInfo.name} is not configured in your system.
                      </p>
                      <a
                        href="/settings/suppliers"
                        className="inline-flex items-center px-3 py-1.5 bg-yellow-600 hover:bg-yellow-700 text-white text-sm font-medium rounded-md transition-colors"
                      >
                        <Settings className="w-4 h-4 mr-1.5" />
                        Configure {selectedParserInfo.name}
                      </a>
                    </div>
                  )}
                </div>
              )}
            </motion.div>
          )}

          {/* Instructions when no file is uploaded - removed redundant section */}
        </>
      )}

      {/* Supplier Configuration Modal */}
      {showSupplierModal && (
        <DynamicAddSupplierModal
          onClose={() => setShowSupplierModal(false)}
          onSuccess={handleSupplierConfigured}
        />
      )}
    </div>
  )
}

export default ImportSelector