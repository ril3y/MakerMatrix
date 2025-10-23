import { useState, useEffect, useCallback } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  X,
  Zap,
  Check,
  AlertCircle,
  Loader2,
  Download,
  Image,
  FileText,
  DollarSign,
  Package,
  Info,
  RefreshCw,
  Search,
  Clock,
  CheckCircle,
} from 'lucide-react'
import type { Task } from '@/services/tasks.service'
import { tasksService } from '@/services/tasks.service'
import type { Part } from '@/types/parts'
import type { EnrichmentRequirementCheckResponse } from '@/services/parts.service'
import { partsService } from '@/services/parts.service'

interface PartEnrichmentModalProps {
  isOpen: boolean
  onClose: () => void
  part: Part
  onPartUpdated: (updatedPart: Part) => void
}

import type { LucideIcon } from 'lucide-react'

interface EnrichmentResult {
  capability: string
  success: boolean
  data?: unknown
  error?: string
  icon: LucideIcon
  label: string
  description: string
}

// Capability definitions with icons and descriptions
const capabilityDefinitions = {
  enrich_basic_info: {
    icon: Info,
    label: 'Basic Info',
    description: 'Enrich basic part information (description, manufacturer, etc.)',
  },
  fetch_datasheet: {
    icon: FileText,
    label: 'Datasheet',
    description: 'Download and attach datasheet PDF',
  },
  fetch_image: {
    icon: Image,
    label: 'Product Image',
    description: 'Fetch high-quality product image',
  },
  fetch_pricing: {
    icon: DollarSign,
    label: 'Pricing',
    description: 'Get current pricing information',
  },
  fetch_stock: {
    icon: Package,
    label: 'Stock Information',
    description: 'Check availability and stock levels',
  },
  fetch_specifications: {
    icon: RefreshCw,
    label: 'Technical Specifications',
    description: 'Retrieve detailed component specifications',
  },
  fetch_alternatives: {
    icon: Search,
    label: 'Alternative Parts',
    description: 'Find alternative/substitute parts',
  },
  fetch_lifecycle_status: {
    icon: Clock,
    label: 'Lifecycle Status',
    description: 'Get part lifecycle and availability status',
  },
  validate_part_number: {
    icon: CheckCircle,
    label: 'Part Validation',
    description: 'Validate part numbers and existence',
  },
  search_parts: {
    icon: Search,
    label: 'Search Parts',
    description: 'Search for parts using supplier databases',
  },
  get_part_details: {
    icon: Info,
    label: 'Part Details',
    description: 'Get detailed part information from supplier',
  },
  import_orders: {
    icon: Download,
    label: 'Import Orders',
    description: 'Import order data from supplier systems',
  },
}

const PartEnrichmentModal = ({
  isOpen,
  onClose,
  part,
  onPartUpdated,
}: PartEnrichmentModalProps) => {
  const [selectedCapabilities, setSelectedCapabilities] = useState<string[]>([])
  const [availableCapabilities, setAvailableCapabilities] = useState<string[]>([])
  const [enrichmentResults, setEnrichmentResults] = useState<EnrichmentResult[]>([])
  const [isEnriching, setIsEnriching] = useState(false)
  const [currentTask, setCurrentTask] = useState<Task | null>(null)
  const [taskProgress, setTaskProgress] = useState(0)
  const [currentStep, setCurrentStep] = useState('')
  const [supplierCapabilities, setSupplierCapabilities] = useState<Record<string, string[]>>({})
  const [selectedSupplier, setSelectedSupplier] = useState<string>('')
  const [requirementCheck, setRequirementCheck] =
    useState<EnrichmentRequirementCheckResponse | null>(null)
  const [isCheckingRequirements, setIsCheckingRequirements] = useState(false)
  const [missingFieldValues, setMissingFieldValues] = useState<Record<string, string>>({})
  const [isSavingFields, setIsSavingFields] = useState(false)

  // Intelligently detect supplier from part data
  const detectSupplierFromPart = (part: Part): string => {
    const additionalProps = part.additional_properties || {}

    console.log('Detecting supplier from part data:', {
      enrichment_source: additionalProps.enrichment_source,
      lcsc_part_number: additionalProps.lcsc_part_number,
      supplier: part.supplier,
      part_vendor: additionalProps.part_vendor,
      additional_properties: part.additional_properties,
    })

    // First check enrichment_source
    if (additionalProps.enrichment_source && typeof additionalProps.enrichment_source === 'string') {
      console.log('Using enrichment_source:', additionalProps.enrichment_source)
      return additionalProps.enrichment_source.toLowerCase()
    }

    // Check for supplier-specific part numbers
    if (additionalProps.lcsc_part_number) {
      console.log('Detected LCSC from part number')
      return 'lcsc'
    }

    if (additionalProps.digikey_part_number) {
      console.log('Detected DIGIKEY from part number')
      return 'digikey'
    }

    if (additionalProps.mouser_part_number) {
      console.log('Detected MOUSER from part number')
      return 'mouser'
    }

    // Fallback to existing logic
    if (part.supplier) {
      console.log('Using part.supplier:', part.supplier)
      return part.supplier.toLowerCase()
    }

    if (additionalProps.part_vendor && typeof additionalProps.part_vendor === 'string') {
      console.log('Using part.part_vendor:', additionalProps.part_vendor)
      return additionalProps.part_vendor.toLowerCase()
    }

    console.log('No supplier detected from part data')
    return ''
  }

  // Check enrichment requirements
  const checkEnrichmentRequirements = useCallback(async () => {
    if (!selectedSupplier || !part.id) {
      return
    }

    setIsCheckingRequirements(true)
    try {
      const check = await partsService.checkEnrichmentRequirements(part.id, selectedSupplier)
      setRequirementCheck(check)
      console.log('Enrichment requirement check:', check)

      // Initialize missing field values object
      const initialValues: Record<string, string> = {}
      check.required_checks.forEach((reqCheck) => {
        if (!reqCheck.is_present) {
          initialValues[reqCheck.field_name] = ''
        }
      })
      setMissingFieldValues(initialValues)
    } catch (error) {
      console.error('Failed to check enrichment requirements:', error)
      setRequirementCheck(null)
    } finally {
      setIsCheckingRequirements(false)
    }
  }, [selectedSupplier, part.id])

  useEffect(() => {
    if (isOpen) {
      loadSupplierCapabilities()
    }
  }, [isOpen])

  // Auto-select supplier after capabilities are loaded
  useEffect(() => {
    if (isOpen && Object.keys(supplierCapabilities).length > 0 && !selectedSupplier) {
      // Set default selected supplier with intelligent detection
      const detectedSupplier = detectSupplierFromPart(part)
      console.log(
        'Detected supplier:',
        detectedSupplier,
        'Available suppliers:',
        Object.keys(supplierCapabilities)
      )

      if (detectedSupplier && supplierCapabilities[detectedSupplier]) {
        console.log('Auto-selecting detected supplier:', detectedSupplier)
        setSelectedSupplier(detectedSupplier)
      } else if (Object.keys(supplierCapabilities).length === 1) {
        // If only one supplier available, auto-select it
        const onlySupplier = Object.keys(supplierCapabilities)[0]
        console.log('Auto-selecting only available supplier:', onlySupplier)
        setSelectedSupplier(onlySupplier)
      }
    }
  }, [isOpen, part, supplierCapabilities, selectedSupplier])

  useEffect(() => {
    if (selectedSupplier && supplierCapabilities[selectedSupplier]) {
      const caps = supplierCapabilities[selectedSupplier] || []
      console.log('Setting available capabilities:', caps)
      console.log('Full supplier data:', supplierCapabilities[selectedSupplier])
      setAvailableCapabilities(caps)

      // Auto-select most common/useful capabilities
      const recommended = caps.filter((cap: string) =>
        ['fetch_datasheet', 'fetch_image', 'get_part_details'].includes(cap)
      )
      console.log('Available capabilities:', caps)
      console.log('Auto-selected capabilities:', recommended)
      console.log('Capability definitions keys:', Object.keys(capabilityDefinitions))
      setSelectedCapabilities(recommended)

      // Check enrichment requirements for selected supplier
      checkEnrichmentRequirements()
    }
  }, [selectedSupplier, supplierCapabilities, checkEnrichmentRequirements])

  // Check if all required fields are filled
  const areAllRequiredFieldsFilled = (): boolean => {
    if (!requirementCheck || requirementCheck.can_enrich) {
      return true // No missing required fields
    }

    // Check if all missing required fields have been filled in
    const missingRequiredFields = requirementCheck.required_checks.filter(
      (check) => !check.is_present
    )

    return missingRequiredFields.every((check) => {
      const value = missingFieldValues[check.field_name]
      return value && value.trim().length > 0
    })
  }

  // Save missing field values to the part (used before starting enrichment)
  const saveMissingFieldsIfNeeded = async (): Promise<boolean> => {
    if (!part.id || areAllRequiredFieldsFilled()) {
      return true // Nothing to save or already valid
    }

    try {
      setIsSavingFields(true)

      // Build update payload
      const updateData: any = {}
      Object.entries(missingFieldValues).forEach(([fieldName, value]) => {
        if (value && value.trim()) {
          updateData[fieldName] = value.trim()
        }
      })

      if (Object.keys(updateData).length === 0) {
        return false
      }

      // Update the part
      await partsService.updatePart({
        id: part.id,
        ...updateData,
      })

      // Notify parent of updated part
      onPartUpdated({ ...part, ...updateData })

      return true
    } catch (error) {
      console.error('Failed to save missing fields:', error)
      alert('Failed to save field values. Please try again.')
      return false
    } finally {
      setIsSavingFields(false)
    }
  }

  const loadSupplierCapabilities = async () => {
    try {
      const response = await tasksService.getSupplierCapabilities()
      console.log('Raw response:', response)
      console.log('Response data:', response.data)

      // Handle the response structure - it might be response.data.data or response.data
      const capabilitiesData = response.data?.data || response.data
      console.log('Extracted capabilities data:', capabilitiesData)

      // Type guard to ensure we have the right structure
      const validCapabilities: Record<string, string[]> = {}
      if (capabilitiesData && typeof capabilitiesData === 'object') {
        Object.entries(capabilitiesData as Record<string, unknown>).forEach(([key, value]) => {
          if (Array.isArray(value)) {
            validCapabilities[key] = value.filter((item): item is string => typeof item === 'string')
          }
        })
      }

      setSupplierCapabilities(validCapabilities)
    } catch (error) {
      console.error('Failed to load supplier capabilities:', error)
    }
  }

  const handleCapabilityToggle = (capability: string) => {
    setSelectedCapabilities((prev) =>
      prev.includes(capability) ? prev.filter((c) => c !== capability) : [...prev, capability]
    )
  }

  const startEnrichment = async () => {
    if (selectedCapabilities.length === 0) {
      alert('Please select at least one enrichment capability')
      return
    }

    // Save missing fields first if needed
    if (!areAllRequiredFieldsFilled()) {
      const saved = await saveMissingFieldsIfNeeded()
      if (!saved) {
        alert('Please fill in all required fields')
        return
      }
    }

    setIsEnriching(true)
    setEnrichmentResults([])
    setTaskProgress(0)
    setCurrentStep('Starting enrichment...')

    try {
      // Create enrichment task
      const response = await tasksService.createPartEnrichmentTask({
        part_id: part.id,
        supplier: selectedSupplier,
        capabilities: selectedCapabilities,
        force_refresh: true,
      })

      setCurrentTask(response.data)

      // Poll for task progress
      const cleanup = await tasksService.pollTaskProgress(response.data.id, (task) => {
        setTaskProgress(task.progress_percentage)
        setCurrentStep(task.current_step || 'Processing...')

        if (task.status === 'completed') {
          handleEnrichmentComplete(task)
        } else if (task.status === 'failed') {
          handleEnrichmentFailed(task)
        }
      })

      // Store cleanup function for later use
      return cleanup
    } catch (error) {
      console.error('Failed to start enrichment:', error)
      setIsEnriching(false)
      alert('Failed to start enrichment task')
    }
  }

  const handleEnrichmentComplete = (task: Task) => {
    setIsEnriching(false)

    // Process enrichment results
    const resultData = task.result_data as Record<string, unknown> | undefined
    const enrichmentSummary = resultData?.enrichment_summary as Record<string, unknown> | undefined
    const results = (enrichmentSummary?.results as Record<string, unknown>) || {}

    const enrichmentResults: EnrichmentResult[] = selectedCapabilities.map((capability) => {
      const result = results[capability] as { success?: boolean; data?: unknown; error?: string } | undefined
      const definition = capabilityDefinitions[capability as keyof typeof capabilityDefinitions]

      return {
        capability,
        success: result?.success || false,
        data: result?.data,
        error: result?.error,
        icon: definition?.icon || Info,
        label: definition?.label || capability,
        description: definition?.description || '',
      }
    })

    setEnrichmentResults(enrichmentResults)

    // Refresh the part data to show updates
    onPartUpdated({ ...part, ...task.result_data })
  }

  const handleEnrichmentFailed = (task: Task) => {
    setIsEnriching(false)
    setCurrentStep(`Failed: ${task.error_message}`)
    alert(`Enrichment failed: ${task.error_message}`)
  }

  const renderEnrichmentResults = () => {
    if (enrichmentResults.length === 0) return null

    return (
      <div className="space-y-4">
        <h3 className="text-lg font-semibold text-primary">Enrichment Results</h3>
        <div className="space-y-3">
          {enrichmentResults.map((result) => {
            const IconComponent = result.icon
            return (
              <div
                key={result.capability}
                className={`p-5 rounded-lg border ${
                  result.success
                    ? 'bg-green-500/10 border-green-500/20'
                    : 'bg-red-500/10 border-red-500/20'
                }`}
              >
                <div className="flex items-start gap-3">
                  <div
                    className={`p-2 rounded-lg ${
                      result.success ? 'bg-green-500/20' : 'bg-red-500/20'
                    }`}
                  >
                    {result.success ? (
                      <Check className="w-5 h-5 text-green-400" />
                    ) : (
                      <AlertCircle className="w-5 h-5 text-red-400" />
                    )}
                  </div>
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-1">
                      <IconComponent className="w-4 h-4 text-secondary" />
                      <span className="font-medium text-primary">{result.label}</span>
                    </div>
                    <p className="text-sm text-secondary mb-2">{result.description}</p>

                    {result.success && result.data && (
                      <div className="bg-bg-secondary p-4 rounded border text-sm">
                        <h4 className="font-medium text-green-400 mb-2">Retrieved Data:</h4>
                        <pre className="text-secondary whitespace-pre-wrap">
                          {JSON.stringify(result.data, null, 2)}
                        </pre>
                      </div>
                    )}

                    {!result.success && result.error && (
                      <div className="text-sm text-red-400">Error: {result.error}</div>
                    )}
                  </div>
                </div>
              </div>
            )
          })}
        </div>
      </div>
    )
  }

  if (!isOpen) return null

  return (
    <AnimatePresence>
      <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50 p-4">
        <motion.div
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          exit={{ opacity: 0, scale: 0.95 }}
          className="bg-white dark:bg-gray-800 rounded-lg shadow-2xl w-full max-w-4xl max-h-[90vh] overflow-hidden border border-gray-200 dark:border-gray-700"
        >
          <div className="flex items-center justify-between p-6 border-b border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-900">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-blue-500/20 rounded-lg">
                <Zap className="w-5 h-5 text-blue-400" />
              </div>
              <div>
                <h2 className="text-xl font-bold text-gray-900 dark:text-white">
                  Enrich Part Data
                </h2>
                <p className="text-gray-600 dark:text-gray-300">{part.name}</p>
              </div>
            </div>
            <button
              onClick={onClose}
              className="p-2 hover:bg-gray-200 dark:hover:bg-gray-700 rounded-lg transition-colors"
            >
              <X className="w-5 h-5 text-gray-500 dark:text-gray-400" />
            </button>
          </div>

          <div className="p-6 max-h-[calc(90vh-8rem)] overflow-y-auto bg-white dark:bg-gray-800">
            {/* Debug info */}
            <div className="mb-4 p-3 bg-gray-100 dark:bg-gray-700 rounded-lg text-sm">
              <div>
                <strong>Debug Info:</strong>
              </div>
              <div>Selected Supplier: {selectedSupplier || 'None'}</div>
              <div>
                Available Capabilities:{' '}
                {availableCapabilities.length > 0 ? availableCapabilities.join(', ') : 'None'}
              </div>
              <div>
                Selected Capabilities:{' '}
                {selectedCapabilities.length > 0 ? selectedCapabilities.join(', ') : 'None'}
              </div>
              <div>
                Button Enabled:{' '}
                {!(selectedCapabilities.length === 0 || !selectedSupplier) ? 'Yes' : 'No'}
              </div>
            </div>
            {!isEnriching && enrichmentResults.length === 0 && (
              <div className="space-y-6">
                {/* Supplier Selection */}
                <div>
                  <label className="block text-sm font-medium text-gray-900 dark:text-white mb-2">
                    Supplier
                  </label>
                  <select
                    value={selectedSupplier}
                    onChange={(e) => setSelectedSupplier(e.target.value)}
                    className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  >
                    {Object.keys(supplierCapabilities).length === 0 ? (
                      <option value="">No suppliers available</option>
                    ) : Object.keys(supplierCapabilities).length === 1 ? (
                      <option value={Object.keys(supplierCapabilities)[0]}>
                        {Object.keys(supplierCapabilities)[0]} (auto-selected)
                      </option>
                    ) : (
                      <>
                        <option value="">Select a supplier...</option>
                        {Object.keys(supplierCapabilities).map((supplier) => (
                          <option key={supplier} value={supplier}>
                            {supplier}
                          </option>
                        ))}
                      </>
                    )}
                  </select>
                  {Object.keys(supplierCapabilities).length === 0 && (
                    <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
                      No enabled suppliers found. Configure suppliers in Settings.
                    </p>
                  )}
                </div>

                {/* Enrichment Requirements Warning */}
                {requirementCheck && !requirementCheck.can_enrich && (
                  <div className="bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-lg p-4">
                    <div className="flex items-start gap-3">
                      <Info className="w-5 h-5 text-yellow-500 flex-shrink-0 mt-0.5" />
                      <div className="flex-1">
                        <h3 className="font-semibold text-yellow-800 dark:text-yellow-300 mb-2">
                          Required Information Missing
                        </h3>
                        <p className="text-sm text-yellow-700 dark:text-yellow-400 mb-3">
                          {requirementCheck.supplier_name === 'mcmaster-carr' ? (
                            <>
                              McMaster-Carr requires either a <strong>product URL</strong> or{' '}
                              <strong>part number</strong> to fetch part details. Please edit the
                              part to add one of these:
                              <ul className="mt-2 ml-4 list-disc">
                                <li>Product URL (e.g., https://www.mcmaster.com/92095A212/)</li>
                                <li>McMaster Part Number (e.g., 92095A212)</li>
                              </ul>
                            </>
                          ) : (
                            <>
                              Please fill in the required information to enrich from{' '}
                              {requirementCheck.supplier_name}:
                            </>
                          )}
                        </p>

                        {/* Input fields for missing required data */}
                        <div className="space-y-3">
                          {requirementCheck.required_checks
                            .filter((check) => !check.is_present)
                            .map((check) => {
                              const isFilled =
                                missingFieldValues[check.field_name]?.trim().length > 0
                              return (
                                <div key={check.field_name}>
                                  <label className="block text-sm font-medium text-gray-900 dark:text-white mb-1">
                                    {check.display_name} <span className="text-red-500">*</span>
                                  </label>
                                  <div className="relative">
                                    <input
                                      type="text"
                                      value={missingFieldValues[check.field_name] || ''}
                                      onChange={(e) =>
                                        setMissingFieldValues({
                                          ...missingFieldValues,
                                          [check.field_name]: e.target.value,
                                        })
                                      }
                                      placeholder={`Enter ${check.display_name.toLowerCase()}`}
                                      className={`w-full px-3 py-2 pr-10 border rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-colors ${
                                        isFilled
                                          ? 'border-green-500 dark:border-green-600'
                                          : 'border-gray-300 dark:border-gray-600'
                                      }`}
                                    />
                                    {isFilled && (
                                      <CheckCircle className="absolute right-3 top-1/2 -translate-y-1/2 w-5 h-5 text-green-500" />
                                    )}
                                  </div>
                                  {check.validation_message && (
                                    <p className="text-xs text-gray-600 dark:text-gray-400 mt-1">
                                      {check.validation_message}
                                    </p>
                                  )}
                                </div>
                              )
                            })}
                        </div>

                        {requirementCheck.suggestions &&
                          requirementCheck.suggestions.length > 0 && (
                            <div className="mt-4 pt-3 border-t border-yellow-200 dark:border-yellow-800">
                              <p className="text-sm font-medium text-yellow-800 dark:text-yellow-300 mb-2">
                                Suggestions:
                              </p>
                              <ul className="space-y-1">
                                {requirementCheck.suggestions.map((suggestion, idx) => (
                                  <li
                                    key={idx}
                                    className="text-sm text-yellow-700 dark:text-yellow-400"
                                  >
                                    • {suggestion}
                                  </li>
                                ))}
                              </ul>
                            </div>
                          )}
                      </div>
                    </div>
                  </div>
                )}

                {/* Recommended Fields Warning */}
                {requirementCheck &&
                  requirementCheck.can_enrich &&
                  requirementCheck.missing_recommended.length > 0 && (
                    <div className="bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-lg p-4">
                      <div className="flex items-start gap-3">
                        <Info className="w-5 h-5 text-yellow-500 flex-shrink-0 mt-0.5" />
                        <div className="flex-1">
                          <h3 className="font-semibold text-yellow-800 dark:text-yellow-300 mb-2">
                            Recommended Fields Missing
                          </h3>
                          <p className="text-sm text-yellow-700 dark:text-yellow-400 mb-2">
                            Adding these fields will improve enrichment quality:
                          </p>
                          <ul className="space-y-1">
                            {requirementCheck.recommended_checks
                              .filter((check) => !check.is_present)
                              .map((check) => (
                                <li
                                  key={check.field_name}
                                  className="text-sm text-yellow-700 dark:text-yellow-400"
                                >
                                  • {check.display_name}
                                </li>
                              ))}
                          </ul>
                        </div>
                      </div>
                    </div>
                  )}

                {/* Capability Selection */}
                {availableCapabilities.length > 0 && (
                  <div>
                    <label className="block text-sm font-medium text-gray-900 dark:text-white mb-3">
                      Select enrichment capabilities
                    </label>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                      {availableCapabilities.map((capability) => {
                        const definition =
                          capabilityDefinitions[capability as keyof typeof capabilityDefinitions]
                        console.log(`Capability: ${capability}, Definition found: ${!!definition}`)
                        if (!definition) {
                          console.warn(`No definition found for capability: ${capability}`)
                          return null
                        }

                        const IconComponent = definition.icon
                        const isSelected = selectedCapabilities.includes(capability)

                        return (
                          <div
                            key={capability}
                            onClick={() => handleCapabilityToggle(capability)}
                            className={`p-5 rounded-lg border cursor-pointer transition-all ${
                              isSelected
                                ? 'bg-blue-50 dark:bg-blue-900/20 border-blue-200 dark:border-blue-700'
                                : 'bg-gray-50 dark:bg-gray-700 border-gray-200 dark:border-gray-600 hover:border-gray-300 dark:hover:border-gray-500'
                            }`}
                          >
                            <div className="flex items-start gap-3">
                              <div
                                className={`p-2 rounded-lg ${
                                  isSelected ? 'bg-blue-500/20' : 'bg-gray-200 dark:bg-gray-600'
                                }`}
                              >
                                <IconComponent
                                  className={`w-4 h-4 ${
                                    isSelected
                                      ? 'text-blue-400'
                                      : 'text-gray-600 dark:text-gray-300'
                                  }`}
                                />
                              </div>
                              <div className="flex-1">
                                <h3 className="font-medium text-gray-900 dark:text-white mb-1">
                                  {definition.label}
                                </h3>
                                <p className="text-sm text-gray-600 dark:text-gray-300">
                                  {definition.description}
                                </p>
                              </div>
                              {isSelected && <Check className="w-5 h-5 text-blue-400" />}
                            </div>
                          </div>
                        )
                      })}
                    </div>
                  </div>
                )}

                {/* Start Button */}
                <div className="flex justify-end gap-3 pt-4 border-t border-gray-200 dark:border-gray-700">
                  <button
                    onClick={onClose}
                    className="px-4 py-2 border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-700 hover:bg-gray-50 dark:hover:bg-gray-600 rounded-lg transition-colors"
                  >
                    Cancel
                  </button>
                  <button
                    onClick={startEnrichment}
                    disabled={
                      selectedCapabilities.length === 0 ||
                      !selectedSupplier ||
                      isCheckingRequirements ||
                      isSavingFields ||
                      !areAllRequiredFieldsFilled()
                    }
                    className="px-4 py-2 bg-blue-500 hover:bg-blue-600 disabled:bg-gray-300 disabled:cursor-not-allowed text-white rounded-lg transition-colors flex items-center gap-2"
                    title={
                      !selectedSupplier
                        ? 'Select a supplier to start enrichment'
                        : isCheckingRequirements
                          ? 'Checking enrichment requirements...'
                          : isSavingFields
                            ? 'Saving field values...'
                            : !areAllRequiredFieldsFilled()
                              ? 'Fill in all required fields to continue'
                              : selectedCapabilities.length === 0
                                ? 'Select at least one capability to enrich (e.g., fetch datasheet, fetch image)'
                                : `Start enriching ${part.name} using ${selectedSupplier} with ${selectedCapabilities.length} selected capabilities`
                    }
                  >
                    {isCheckingRequirements || isSavingFields ? (
                      <Loader2 className="w-4 h-4 animate-spin" />
                    ) : (
                      <Zap className="w-4 h-4" />
                    )}
                    {isCheckingRequirements
                      ? 'Checking...'
                      : isSavingFields
                        ? 'Saving...'
                        : 'Start Enrichment'}
                  </button>
                </div>
              </div>
            )}

            {/* Progress Display */}
            {isEnriching && (
              <div className="space-y-6">
                <div className="text-center">
                  <div className="inline-flex items-center gap-3 p-4 bg-blue-500/10 rounded-lg border border-blue-500/20">
                    <Loader2 className="w-6 h-6 text-blue-400 animate-spin" />
                    <div>
                      <div className="font-medium text-primary">Enriching Part Data</div>
                      <div className="text-sm text-secondary">{currentStep}</div>
                    </div>
                  </div>
                </div>

                <div className="space-y-2">
                  <div className="flex justify-between text-sm">
                    <span className="text-secondary">Progress</span>
                    <span className="text-primary">{taskProgress}%</span>
                  </div>
                  <div className="w-full bg-bg-secondary rounded-full h-2">
                    <motion.div
                      className="bg-blue-500 h-2 rounded-full"
                      initial={{ width: 0 }}
                      animate={{ width: `${taskProgress}%` }}
                      transition={{ duration: 0.3 }}
                    />
                  </div>
                </div>
              </div>
            )}

            {/* Results Display */}
            {renderEnrichmentResults()}

            {/* Close Button for Results */}
            {enrichmentResults.length > 0 && (
              <div className="flex justify-end pt-4 border-t border-gray-200 dark:border-gray-700">
                <button
                  onClick={onClose}
                  className="px-4 py-2 bg-blue-500 hover:bg-blue-600 text-white rounded-lg transition-colors"
                >
                  Close
                </button>
              </div>
            )}
          </div>
        </motion.div>
      </div>
    </AnimatePresence>
  )
}

export default PartEnrichmentModal
