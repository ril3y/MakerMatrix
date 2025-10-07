import { motion } from 'framer-motion'
import { useState, useEffect } from 'react'
import { X, TestTube } from 'lucide-react'
import { CustomSelect } from '@/components/ui/CustomSelect'
import { settingsService } from '@/services/settings.service'
import toast from 'react-hot-toast'

interface DynamicPrinterModalProps {
  isOpen: boolean
  onClose: () => void
  mode: 'add' | 'edit'
  existingPrinter?: any
  onSuccess: () => void
}

const DynamicPrinterModal = ({
  isOpen,
  onClose,
  mode,
  existingPrinter,
  onSuccess,
}: DynamicPrinterModalProps) => {
  const [supportedDrivers, setSupportedDrivers] = useState<any[]>([])
  const [selectedDriverInfo, setSelectedDriverInfo] = useState<any>(null)
  const [discoveredPrinters, setDiscoveredPrinters] = useState<any[]>([])
  const [testResult, setTestResult] = useState<any>(null)
  const [testingSetup, setTestingSetup] = useState(false)
  const [loading, setLoading] = useState(false)
  const [discoveryTask, setDiscoveryTask] = useState<any>(null)
  const [discoveryProgress, setDiscoveryProgress] = useState(0)

  const [printerData, setPrinterData] = useState({
    printer_id: '',
    name: '',
    driver_type: '',
    model: '',
    backend: '',
    identifier: '',
    dpi: 300,
    scaling_factor: 1.1,
    // Dynamic fields will be added here
    custom_fields: {} as Record<string, any>,
  })

  useEffect(() => {
    if (isOpen) {
      loadSupportedDrivers()
      loadLatestDiscovery()

      if (mode === 'edit' && existingPrinter) {
        // Extract custom fields from the config object if available
        const customFields = { ...existingPrinter.custom_fields }
        if (existingPrinter.config) {
          // Merge any additional fields from the config object
          Object.assign(customFields, existingPrinter.config)
        }

        // Populate form with existing printer data
        setPrinterData({
          printer_id: existingPrinter.printer_id,
          name: existingPrinter.name,
          driver_type: existingPrinter.driver_type || '',
          model: existingPrinter.model || '',
          backend: existingPrinter.backend || 'network',
          identifier: existingPrinter.identifier || '',
          dpi: existingPrinter.dpi || 300,
          scaling_factor: existingPrinter.scaling_factor || 1.1,
          custom_fields: customFields,
        })

        // Load driver info for the existing printer
        if (existingPrinter.driver_type) {
          loadDriverInfo(existingPrinter.driver_type)
        }
      } else {
        // Reset form for add mode
        setPrinterData({
          printer_id: '',
          name: '',
          driver_type: '',
          model: '',
          backend: '',
          identifier: '',
          dpi: 300,
          scaling_factor: 1.1,
          custom_fields: {},
        })
        setSelectedDriverInfo(null)
      }
    }
  }, [isOpen, mode, existingPrinter])

  const loadSupportedDrivers = async () => {
    try {
      const drivers = await settingsService.getSupportedDrivers()
      setSupportedDrivers(drivers)
    } catch (error) {
      console.error('Failed to load supported drivers:', error)
      toast.error('Failed to load supported drivers')
    }
  }

  const loadDriverInfo = async (driverType: string) => {
    try {
      const driverInfo = await settingsService.getDriverInfo(driverType)
      setSelectedDriverInfo(driverInfo)

      // Only set default values if we're in add mode or the field is empty
      setPrinterData((prev) => ({
        ...prev,
        // Only update these if we're in add mode or they're empty
        dpi: mode === 'add' || !prev.dpi ? driverInfo.default_dpi || prev.dpi || 300 : prev.dpi,
        scaling_factor:
          mode === 'add' || !prev.scaling_factor
            ? driverInfo.recommended_scaling || prev.scaling_factor || 1.1
            : prev.scaling_factor,
        model: mode === 'add' || !prev.model ? driverInfo.supported_models?.[0] || '' : prev.model,
        backend: mode === 'add' || !prev.backend ? driverInfo.backends?.[0] || '' : prev.backend,
        // Initialize custom fields with defaults only for new fields or add mode
        custom_fields: {
          ...prev.custom_fields,
          ...Object.entries(driverInfo.custom_fields || {}).reduce(
            (acc, [key, field]: [string, any]) => {
              // Only set default if we're in add mode or the field doesn't exist
              if (mode === 'add' || prev.custom_fields[key] === undefined) {
                acc[key] = field.default
              }
              return acc
            },
            {} as Record<string, any>
          ),
        },
      }))
    } catch (error) {
      console.error('Failed to load driver info:', error)
      toast.error('Failed to load driver information')
    }
  }

  const handleDriverChange = async (driverType: string) => {
    setPrinterData((prev) => ({ ...prev, driver_type: driverType, custom_fields: {} }))
    if (driverType) {
      await loadDriverInfo(driverType)
    } else {
      setSelectedDriverInfo(null)
    }
  }

  const handleBackendChange = (backend: string) => {
    setPrinterData((prev) => ({ ...prev, backend }))

    // Update identifier placeholder based on backend
    if (selectedDriverInfo?.backend_options?.[backend]) {
      const backendInfo = selectedDriverInfo.backend_options[backend]
      // You could also auto-update the identifier format hint here
    }
  }

  const handleCustomFieldChange = (fieldName: string, value: any) => {
    setPrinterData((prev) => ({
      ...prev,
      custom_fields: {
        ...prev.custom_fields,
        [fieldName]: value,
      },
    }))
  }

  const testPrinterSetup = async () => {
    try {
      setTestingSetup(true)

      let result
      if (mode === 'edit' && existingPrinter?.printer_id) {
        // For edit mode, test the existing registered printer
        console.log('🧪 Edit mode: Testing existing printer:', existingPrinter.printer_id)
        console.log('🔗 Using endpoint: /printer/printers/{id}/test')
        result = await settingsService.testPrinterConnection(existingPrinter.printer_id)
      } else {
        // For add mode, test the setup configuration
        console.log('🧪 Add mode: Testing printer setup configuration')
        console.log('🔗 Using endpoint: /printer/test-setup')
        console.log('📋 Configuration:', printerData)
        result = await settingsService.testPrinterSetup(printerData)
      }

      setTestResult(result)

      // Check for success based on mode - edit mode returns nested data structure
      const isSuccess = mode === 'edit' ? result.data?.success : result.success

      if (isSuccess) {
        toast.success('✅ Connection test successful!')
        // Apply recommendations if any (only for setup tests)
        if (mode === 'add' && result.recommendations) {
          setPrinterData((prev) => ({
            ...prev,
            scaling_factor: result.recommendations.scaling_factor || prev.scaling_factor,
          }))
        }
      } else {
        const errorMessage =
          mode === 'edit'
            ? result.data?.error || result.message || 'Connection test failed'
            : result.message || 'Connection test failed'
        toast.error(`❌ Connection test failed: ${errorMessage}`)
      }
    } catch (error) {
      console.error('Test failed:', error)
      toast.error('Test failed')
      setTestResult({ success: false, message: 'Test failed' })
    } finally {
      setTestingSetup(false)
    }
  }

  const discoverPrinters = async () => {
    try {
      setLoading(true)
      setDiscoveryProgress(0)
      setDiscoveredPrinters([])

      // Start discovery task
      const taskResult = await settingsService.startPrinterDiscovery()
      setDiscoveryTask(taskResult)
      toast.success('Started printer discovery...')

      // Poll for results
      const taskId = taskResult.task_id
      const pollInterval = setInterval(async () => {
        try {
          const status = await settingsService.getPrinterDiscoveryStatus(taskId)
          setDiscoveryProgress(status.progress || 0)

          if (status.status === 'COMPLETED') {
            setDiscoveredPrinters(status.discovered_printers || [])
            toast.success(
              `Discovery complete - found ${status.discovered_printers?.length || 0} printers`
            )
            clearInterval(pollInterval)
            setLoading(false)
          } else if (status.status === 'FAILED') {
            toast.error('Printer discovery failed')
            clearInterval(pollInterval)
            setLoading(false)
          }
          // Continue polling if still running
        } catch (error) {
          console.error('Failed to poll discovery status:', error)
          clearInterval(pollInterval)
          setLoading(false)
        }
      }, 1000) // Poll every second

      // Timeout after 60 seconds
      setTimeout(() => {
        clearInterval(pollInterval)
        setLoading(false)
        if (discoveryTask && discoveryProgress < 100) {
          toast.warning('Discovery timeout - check latest results')
        }
      }, 60000)
    } catch {
      toast.error('Failed to start printer discovery')
      setLoading(false)
    }
  }

  // Load latest discovery results on modal open
  const loadLatestDiscovery = async () => {
    try {
      const result = await settingsService.getLatestPrinterDiscovery()
      if (result.discovered_printers && result.discovered_printers.length > 0) {
        setDiscoveredPrinters(result.discovered_printers)
      }
    } catch {
      // Ignore error - no previous discovery results
    }
  }

  const handleSubmit = async () => {
    try {
      if (!printerData.name || !printerData.identifier) {
        toast.error('Please fill in all required fields')
        return
      }

      // Auto-generate printer_id from name if not provided (for add mode)
      const finalPrinterData = { ...printerData }
      if (mode === 'add' && !finalPrinterData.printer_id) {
        finalPrinterData.printer_id = finalPrinterData.name
          .toLowerCase()
          .replace(/[^a-z0-9]/g, '_')
          .replace(/_+/g, '_')
          .replace(/^_|_$/g, '')
      }

      // Merge custom fields into main printer data for submission
      const submissionData = {
        ...finalPrinterData,
        ...finalPrinterData.custom_fields,
      }
      delete submissionData.custom_fields

      if (mode === 'edit') {
        await settingsService.updatePrinter(existingPrinter.printer_id, submissionData)
        toast.success('✅ Printer updated successfully!')
      } else {
        await settingsService.registerPrinter(submissionData)
        toast.success('✅ Printer registered successfully!')
      }

      onSuccess()
      onClose()
    } catch (error: any) {
      console.error(`${mode} printer error:`, error)

      // Handle specific error cases
      if (error?.response?.status === 409) {
        toast.error('❌ A printer with this ID already exists')
      } else if (error?.response?.data?.detail) {
        toast.error(`❌ ${error.response.data.detail}`)
      } else {
        toast.error(`❌ Failed to ${mode} printer`)
      }
    }
  }

  const renderCustomField = (fieldName: string, fieldConfig: any) => {
    const value = printerData.custom_fields[fieldName] || fieldConfig.default

    switch (fieldConfig.type) {
      case 'select':
        return (
          <CustomSelect
            value={value}
            onChange={(val) => handleCustomFieldChange(fieldName, val)}
            options={fieldConfig.options.map((option: any) => ({
              value: option,
              label: option,
            }))}
            placeholder="Select an option"
          />
        )

      case 'range':
        return (
          <div className="space-y-2">
            <input
              type="range"
              min={fieldConfig.min}
              max={fieldConfig.max}
              step={1}
              className="w-full"
              value={value}
              onChange={(e) => handleCustomFieldChange(fieldName, Number(e.target.value))}
            />
            <div className="text-center text-sm text-secondary">Value: {value}</div>
          </div>
        )

      default:
        return (
          <input
            type="text"
            className="input w-full"
            value={value}
            onChange={(e) => handleCustomFieldChange(fieldName, e.target.value)}
          />
        )
    }
  }

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <motion.div
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        className="modal-container bg-background-primary rounded-lg p-6 w-full max-w-4xl mx-4 max-h-[90vh] overflow-y-auto"
      >
        <div className="flex items-center justify-between mb-6">
          <h4 className="text-xl font-semibold text-primary">
            {mode === 'edit' ? 'Edit Printer' : 'Add New Printer'}
          </h4>
          <button onClick={onClose} className="text-secondary hover:text-primary">
            <X className="w-6 h-6" />
          </button>
        </div>

        <div className="space-y-6">
          <p className="text-sm text-secondary">
            {mode === 'edit'
              ? 'Update your printer configuration.'
              : 'Configure a new printer for use with MakerMatrix.'}
          </p>

          {/* Basic Fields */}
          {mode === 'edit' ? (
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-primary mb-2">Printer ID</label>
                <input
                  type="text"
                  className="input w-full"
                  value={printerData.printer_id}
                  disabled={true}
                />
                <p className="text-xs text-secondary mt-1">Printer ID cannot be changed</p>
              </div>

              <div>
                <label className="block text-sm font-medium text-primary mb-2">
                  Printer Name *
                </label>
                <input
                  type="text"
                  className="input w-full"
                  placeholder="My Label Printer"
                  value={printerData.name}
                  onChange={(e) => setPrinterData((prev) => ({ ...prev, name: e.target.value }))}
                />
              </div>
            </div>
          ) : (
            <div>
              <label className="block text-sm font-medium text-primary mb-2">Printer Name *</label>
              <input
                type="text"
                className="input w-full"
                placeholder="My Label Printer"
                value={printerData.name}
                onChange={(e) => setPrinterData((prev) => ({ ...prev, name: e.target.value }))}
              />
              <p className="text-xs text-secondary mt-1">
                Printer ID will be auto-generated from the name
              </p>
            </div>
          )}

          {/* Driver Selection */}
          <div>
            <label className="block text-sm font-medium text-primary mb-2">Driver Type *</label>
            <CustomSelect
              value={printerData.driver_type}
              onChange={handleDriverChange}
              options={[
                { value: '', label: 'Select a driver...' },
                ...supportedDrivers.map((driver) => ({
                  value: driver.id,
                  label: driver.name,
                })),
              ]}
              placeholder="Select a driver..."
            />
            {selectedDriverInfo && (
              <p className="text-xs text-secondary mt-1">{selectedDriverInfo.description}</p>
            )}
          </div>

          {/* Driver-specific fields */}
          {selectedDriverInfo && (
            <>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-primary mb-2">Model</label>
                  <CustomSelect
                    value={printerData.model}
                    onChange={(val) => setPrinterData((prev) => ({ ...prev, model: val }))}
                    options={
                      selectedDriverInfo.supported_models?.map((model: string) => ({
                        value: model,
                        label: model,
                      })) || []
                    }
                    placeholder="Select model"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-primary mb-2">Backend</label>
                  <CustomSelect
                    value={printerData.backend}
                    onChange={handleBackendChange}
                    options={
                      selectedDriverInfo.backends?.map((backend: string) => ({
                        value: backend,
                        label: backend.charAt(0).toUpperCase() + backend.slice(1).replace('_', ' '),
                      })) || []
                    }
                    placeholder="Select backend"
                  />
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-primary mb-2">
                  {selectedDriverInfo.backend_options?.[printerData.backend]?.identifier_format ||
                    'Identifier'}{' '}
                  *
                </label>
                <input
                  type="text"
                  className="input w-full"
                  placeholder={
                    selectedDriverInfo.backend_options?.[printerData.backend]?.example ||
                    'Enter identifier...'
                  }
                  value={printerData.identifier}
                  onChange={(e) =>
                    setPrinterData((prev) => ({ ...prev, identifier: e.target.value }))
                  }
                />
                {selectedDriverInfo.backend_options?.[printerData.backend]?.example && (
                  <p className="text-xs text-secondary mt-1">
                    Example: {selectedDriverInfo.backend_options[printerData.backend].example}
                  </p>
                )}
              </div>

              {/* Standard printer fields */}
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-primary mb-2">DPI</label>
                  <input
                    type="number"
                    className="input w-full"
                    value={printerData.dpi}
                    onChange={(e) =>
                      setPrinterData((prev) => ({ ...prev, dpi: Number(e.target.value) }))
                    }
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-primary mb-2">
                    Scaling Factor
                  </label>
                  <input
                    type="number"
                    step="0.1"
                    min="0.5"
                    max="2.0"
                    className="input w-full"
                    value={printerData.scaling_factor}
                    onChange={(e) =>
                      setPrinterData((prev) => ({
                        ...prev,
                        scaling_factor: Number(e.target.value),
                      }))
                    }
                  />
                </div>
              </div>

              {/* Custom driver-specific fields */}
              {selectedDriverInfo.custom_fields &&
                Object.keys(selectedDriverInfo.custom_fields).length > 0 && (
                  <div className="border-t border-border pt-4">
                    <h5 className="font-medium text-primary mb-4">
                      {selectedDriverInfo.name} Specific Settings
                    </h5>
                    <div className="grid grid-cols-2 gap-4">
                      {Object.entries(selectedDriverInfo.custom_fields).map(
                        ([fieldName, fieldConfig]: [string, any]) => {
                          // Skip fields that are backend-specific if not the current backend
                          const backendOptions =
                            selectedDriverInfo.backend_options?.[printerData.backend]
                          if (
                            backendOptions?.additional_fields &&
                            !backendOptions.additional_fields.includes(fieldName)
                          ) {
                            return null
                          }

                          return (
                            <div key={fieldName}>
                              <label className="block text-sm font-medium text-primary mb-2">
                                {fieldConfig.label}
                              </label>
                              {renderCustomField(fieldName, fieldConfig)}
                            </div>
                          )
                        }
                      )}
                    </div>
                  </div>
                )}

              {/* Test Connection Section */}
              <div className="border-t border-border pt-4">
                <div className="flex gap-2 mb-3">
                  <button
                    onClick={testPrinterSetup}
                    disabled={
                      testingSetup ||
                      (!printerData.identifier && mode === 'add') ||
                      !printerData.driver_type
                    }
                    className="btn btn-secondary btn-sm flex items-center gap-2"
                  >
                    {testingSetup ? (
                      <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-primary"></div>
                    ) : (
                      <TestTube className="w-4 h-4" />
                    )}
                    {mode === 'edit' ? 'Test Printer' : 'Test Connection'}
                  </button>

                  {printerData.backend === 'network' &&
                    selectedDriverInfo?.supports_network_discovery && (
                      <button
                        onClick={discoverPrinters}
                        disabled={loading}
                        className="btn btn-secondary btn-sm flex items-center gap-2"
                      >
                        🔍 Discover Network Printers
                      </button>
                    )}
                </div>

                {testResult && (
                  <div
                    className={`p-3 rounded-lg text-sm ${
                      (mode === 'edit' ? testResult.data?.success : testResult.success)
                        ? 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200'
                        : 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200'
                    }`}
                  >
                    <p className="font-medium">
                      {(mode === 'edit' ? testResult.data?.success : testResult.success)
                        ? '✅ Connection Successful'
                        : '❌ Connection Failed'}
                    </p>
                    <p>
                      {mode === 'edit'
                        ? testResult.data?.message || testResult.message || 'Test completed'
                        : testResult.message || 'Test completed'}
                    </p>
                    {mode === 'edit' && testResult.data?.response_time_ms && (
                      <p className="text-xs mt-1">
                        Response time: {testResult.data.response_time_ms.toFixed(2)}ms
                      </p>
                    )}
                    {testResult.recommendations && (
                      <div className="mt-2">
                        <p className="font-medium">Recommendations:</p>
                        <ul className="list-disc list-inside ml-2">
                          {testResult.recommendations.scaling_factor && (
                            <li>
                              Scaling factor adjusted to {testResult.recommendations.scaling_factor}
                            </li>
                          )}
                        </ul>
                      </div>
                    )}
                  </div>
                )}

                {discoveredPrinters.length > 0 && (
                  <div className="mt-3 p-3 bg-background-secondary rounded-lg">
                    <p className="font-medium text-primary mb-2">Discovered Printers:</p>
                    <div className="space-y-2">
                      {discoveredPrinters.map((printer, index) => (
                        <div key={index} className="flex items-center justify-between text-sm">
                          <span>
                            {printer.name} ({printer.identifier})
                          </span>
                          <button
                            onClick={() => {
                              setPrinterData((prev) => ({
                                ...prev,
                                name: printer.name,
                                identifier: printer.identifier,
                                model: printer.model || prev.model,
                              }))
                            }}
                            className="btn btn-secondary btn-xs"
                          >
                            Use
                          </button>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </>
          )}

          <div className="flex gap-2 mt-6">
            <button onClick={onClose} className="btn btn-secondary flex-1">
              Cancel
            </button>
            <button
              onClick={handleSubmit}
              className="btn btn-primary flex-1"
              disabled={!printerData.name || !printerData.identifier}
            >
              {mode === 'edit' ? 'Update Printer' : 'Add Printer'}
            </button>
          </div>
        </div>
      </motion.div>
    </div>
  )
}

export default DynamicPrinterModal
