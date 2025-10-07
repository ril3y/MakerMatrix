/**
 * Edit Supplier Configuration Modal
 *
 * Modal for editing existing supplier configurations with validation and capability management.
 */

import React, { useState, useEffect, useCallback } from 'react'
import { X, AlertTriangle, Save, TestTube } from 'lucide-react'
import type {
  SupplierConfig,
  SupplierConfigUpdate,
  ConnectionTestResult,
} from '../../services/supplier.service'
import { supplierService } from '../../services/supplier.service'
import { CredentialEditor } from '../../components/suppliers/CredentialEditor'
import { SupplierTestResult } from '../../components/suppliers/SupplierTestResult'

interface EditSupplierModalProps {
  supplier: SupplierConfig
  onClose: () => void
  onSuccess: () => void
}

export const EditSupplierModal: React.FC<EditSupplierModalProps> = ({
  supplier,
  onClose,
  onSuccess,
}) => {
  const [loading, setLoading] = useState(false)
  const [testing, setTesting] = useState(false)
  const [errors, setErrors] = useState<string[]>([])
  const [testResult, setTestResult] = useState<ConnectionTestResult | null>(null)
  const [successMessage, setSuccessMessage] = useState<string>('')

  // Backend-driven capabilities and credential schema
  const [availableCapabilities, setAvailableCapabilities] = useState<string[]>([])
  const [credentialSchema, setCredentialSchema] = useState<any[]>([])
  const [loadingCapabilities, setLoadingCapabilities] = useState(true)

  // Track current credentials for testing and credential status
  const [currentCredentials, setCurrentCredentials] = useState<Record<string, string>>({})
  const [credentialStatus, setCredentialStatus] = useState<any>(null)

  const [config, setConfig] = useState<SupplierConfigUpdate>({
    display_name: supplier.display_name,
    description: supplier.description || '',
    website_url: supplier.website_url,
    image_url: supplier.image_url,
    enabled: supplier.enabled,
    capabilities: supplier.capabilities || [],
    custom_headers: supplier.custom_headers,
    custom_parameters: supplier.custom_parameters,
  })

  // Load capabilities and schema from backend
  useEffect(() => {
    const loadSupplierData = async () => {
      try {
        setLoadingCapabilities(true)

        // Get actual capabilities from backend
        const capabilitiesResponse = await fetch(
          `/api/suppliers/${supplier.supplier_name.toLowerCase()}/capabilities`,
          {
            headers: { Authorization: `Bearer ${localStorage.getItem('auth_token')}` },
          }
        )

        if (!capabilitiesResponse.ok) {
          throw new Error(
            `Capabilities API returned ${capabilitiesResponse.status}: ${capabilitiesResponse.statusText}`
          )
        }

        const capabilitiesData = await capabilitiesResponse.json()
        if (capabilitiesData.status === 'success') {
          setAvailableCapabilities(capabilitiesData.data)
          // Auto-enable all supported capabilities
          setConfig((prev) => ({ ...prev, capabilities: capabilitiesData.data }))
        } else {
          throw new Error(`Capabilities API failed: ${capabilitiesData.message || 'Unknown error'}`)
        }

        // Get credential schema from backend
        console.log(`Fetching credentials schema for ${supplier.supplier_name}`)
        const schemaResponse = await fetch(
          `/api/suppliers/${supplier.supplier_name.toLowerCase()}/credentials-schema`,
          {
            headers: { Authorization: `Bearer ${localStorage.getItem('auth_token')}` },
          }
        )
        console.log('Schema response status:', schemaResponse.status)
        if (!schemaResponse.ok) {
          throw new Error(
            `Schema API returned ${schemaResponse.status}: ${schemaResponse.statusText}`
          )
        }
        const schemaData = await schemaResponse.json()
        console.log('Schema data:', schemaData)
        if (schemaData.status === 'success') {
          setCredentialSchema(schemaData.data)
        } else {
          throw new Error(`Credentials schema API failed: ${schemaData.message || 'Unknown error'}`)
        }

        // Get credential status to show what's already configured
        try {
          console.log('Fetching credential status for:', supplier.supplier_name)
          const status = await supplierService.getCredentialStatus(supplier.supplier_name)
          console.log('Credential status response:', status)
          setCredentialStatus(status)
          console.log('Credential status set in state:', status)
        } catch (error) {
          console.error('Failed to load credential status:', error)
          console.error('Error details:', error)
        }
      } catch (error) {
        console.error('Failed to load supplier data:', error)
        const errorMessage = error instanceof Error ? error.message : 'Unknown error'
        setErrors([`Failed to load supplier information: ${errorMessage}`])
      } finally {
        setLoadingCapabilities(false)
      }
    }

    loadSupplierData()
  }, [supplier.supplier_name])

  // Handle Escape key to close modal
  useEffect(() => {
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        onClose()
      }
    }

    window.addEventListener('keydown', handleEscape)
    return () => window.removeEventListener('keydown', handleEscape)
  }, [onClose])

  const handleConfigChange = (field: keyof SupplierConfigUpdate, value: any) => {
    setConfig((prev) => ({ ...prev, [field]: value }))
    setErrors([]) // Clear errors when user makes changes
  }

  const handleCapabilityChange = (capability: string, enabled: boolean) => {
    const currentCapabilities = config.capabilities || []
    let updatedCapabilities: string[]

    if (enabled) {
      // Add capability if not already present
      updatedCapabilities = currentCapabilities.includes(capability)
        ? currentCapabilities
        : [...currentCapabilities, capability]
    } else {
      // Remove capability
      updatedCapabilities = currentCapabilities.filter((cap) => cap !== capability)
    }

    handleConfigChange('capabilities', updatedCapabilities)
  }

  const handleCustomHeaderChange = (key: string, value: string) => {
    const newHeaders = { ...config.custom_headers }
    if (value.trim()) {
      newHeaders[key] = value
    } else {
      delete newHeaders[key]
    }
    handleConfigChange('custom_headers', newHeaders)
  }

  const addCustomHeader = () => {
    const key = prompt('Enter header name:')
    if (key && key.trim()) {
      handleCustomHeaderChange(key.trim(), '')
    }
  }

  // Memoize callback functions to prevent infinite loops
  const handleCredentialsReady = useCallback((credentials: Record<string, string>) => {
    setCurrentCredentials(credentials)
  }, [])

  const handleCredentialsSave = useCallback(
    async (credentials: Record<string, string>) => {
      try {
        await supplierService.saveCredentials(supplier.supplier_name, credentials)
        // Refresh credential status
        const newStatus = await supplierService.getCredentialStatus(supplier.supplier_name)
        setCredentialStatus(newStatus)
        setSuccessMessage('Credentials saved successfully!')
      } catch (error) {
        console.error('Failed to save credentials:', error)
        setErrors(['Failed to save credentials: ' + (error as Error).message])
      }
    },
    [supplier.supplier_name]
  )

  const handleTestConnection = async () => {
    try {
      setTesting(true)
      setTestResult(null)

      // For DigiKey and Mouser, save credentials first before testing
      if (
        ['digikey', 'mouser'].includes(supplier.supplier_name.toLowerCase()) &&
        currentCredentials &&
        Object.keys(currentCredentials).length > 0
      ) {
        try {
          await supplierService.saveCredentials(supplier.supplier_name, currentCredentials)
          // Refresh credential status
          const newStatus = await supplierService.getCredentialStatus(supplier.supplier_name)
          setCredentialStatus(newStatus)
        } catch (credError) {
          console.error('Failed to save credentials before testing:', credError)
          setTestResult({
            supplier_name: supplier.supplier_name,
            success: false,
            test_duration_seconds: 0,
            tested_at: new Date().toISOString(),
            error_message:
              'Failed to save credentials before testing: ' + (credError as Error).message,
          })
          return
        }
      }

      const result = await supplierService.testConnection(
        supplier.supplier_name,
        currentCredentials
      )
      setTestResult(result)
    } catch (err: any) {
      setTestResult({
        supplier_name: supplier.supplier_name,
        success: false,
        test_duration_seconds: 0,
        tested_at: new Date().toISOString(),
        error_message: err.response?.data?.detail || 'Connection test failed',
      })
    } finally {
      setTesting(false)
    }
  }

  const handleSubmit = async () => {
    try {
      setLoading(true)
      setErrors([])
      setSuccessMessage('')

      // Validate configuration
      const validationErrors = supplierService.validateConfig(config, supplier.supplier_name)
      if (validationErrors.length > 0) {
        setErrors(validationErrors)
        return
      }

      // Update supplier
      await supplierService.updateSupplier(supplier.supplier_name, config)

      // For DigiKey and Mouser, also save credentials if they've been entered
      if (
        ['digikey', 'mouser'].includes(supplier.supplier_name.toLowerCase()) &&
        currentCredentials &&
        Object.keys(currentCredentials).length > 0
      ) {
        try {
          await supplierService.saveCredentials(supplier.supplier_name, currentCredentials)
          // Refresh credential status
          const newStatus = await supplierService.getCredentialStatus(supplier.supplier_name)
          setCredentialStatus(newStatus)
        } catch (credError) {
          console.error('Failed to save credentials:', credError)
          setErrors([
            'Configuration saved, but failed to save credentials: ' + (credError as Error).message,
          ])
          return
        }
      }

      // Show success message briefly before closing
      setSuccessMessage('Configuration saved successfully!')
      setTimeout(() => {
        onSuccess()
      }, 1000)
    } catch (err: any) {
      const errorMessage = err.response?.data?.detail || 'Failed to update supplier configuration'
      setErrors([errorMessage])
    } finally {
      setLoading(false)
    }
  }

  const hasChanges = () => {
    const originalConfig = {
      display_name: supplier.display_name,
      description: supplier.description || '',
      website_url: supplier.website_url,
      image_url: supplier.image_url,
      enabled: supplier.enabled,
      capabilities: supplier.capabilities || [],
      custom_headers: supplier.custom_headers,
      custom_parameters: supplier.custom_parameters,
    }

    const configChanged = JSON.stringify(config) !== JSON.stringify(originalConfig)

    // For DigiKey and Mouser, also check if credentials have been entered
    const credentialsChanged =
      ['digikey', 'mouser'].includes(supplier.supplier_name.toLowerCase()) &&
      currentCredentials &&
      Object.keys(currentCredentials).length > 0 &&
      Object.values(currentCredentials).some((value) => value && value.trim() !== '')

    return configChanged || credentialsChanged
  }

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-xl max-w-4xl w-full max-h-[90vh] overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-gray-200 dark:border-gray-700">
          <div>
            <h2 className="text-xl font-semibold text-gray-900 dark:text-white">
              Edit Supplier Configuration
            </h2>
            <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
              {supplier.supplier_name} - {supplier.display_name}
            </p>
          </div>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
          >
            <X className="w-6 h-6" />
          </button>
        </div>

        {/* Content */}
        <div className="p-6 overflow-y-auto max-h-[calc(90vh-200px)]">
          <div className="space-y-6">
            {/* Success Message */}
            {successMessage && (
              <div className="bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-md p-4">
                <div className="flex">
                  <div className="w-5 h-5 text-green-400">✓</div>
                  <div className="ml-3">
                    <h3 className="text-sm font-medium text-green-800 dark:text-green-200">
                      {successMessage}
                    </h3>
                  </div>
                </div>
              </div>
            )}

            {/* Error Display */}
            {errors.length > 0 && (
              <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-md p-4">
                <div className="flex">
                  <AlertTriangle className="w-5 h-5 text-red-400" />
                  <div className="ml-3">
                    <h3 className="text-sm font-medium text-red-800 dark:text-red-200">
                      Configuration Errors
                    </h3>
                    <ul className="mt-1 text-sm text-red-700 dark:text-red-300 list-disc list-inside">
                      {errors.map((error, index) => (
                        <li key={index}>{error}</li>
                      ))}
                    </ul>
                  </div>
                </div>
              </div>
            )}

            {/* Test Result */}
            {testResult && <SupplierTestResult testResult={testResult} />}

            {/* Basic Information */}
            <div className="bg-gray-50 dark:bg-gray-700/50 rounded-lg p-4">
              <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-4">
                Basic Information
              </h3>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                    Supplier Name
                  </label>
                  <input
                    type="text"
                    value={supplier.supplier_name}
                    readOnly
                    className="w-full border border-gray-300 dark:border-gray-600 rounded-md px-3 py-2 bg-gray-100 dark:bg-gray-600 text-gray-900 dark:text-white"
                  />
                  <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                    Supplier name cannot be changed
                  </p>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                    Display Name *
                  </label>
                  <input
                    type="text"
                    value={config.display_name}
                    onChange={(e) => handleConfigChange('display_name', e.target.value)}
                    className="w-full border border-gray-300 dark:border-gray-600 rounded-md px-3 py-2 bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                  />
                </div>
                <div className="md:col-span-2">
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                    Description
                  </label>
                  <textarea
                    value={config.description}
                    onChange={(e) => handleConfigChange('description', e.target.value)}
                    rows={2}
                    className="w-full border border-gray-300 dark:border-gray-600 rounded-md px-3 py-2 bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                  />
                </div>
                <div className="md:col-span-2">
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                    Website URL
                  </label>
                  <div className="flex items-center gap-3">
                    <input
                      type="url"
                      value={config.website_url || ''}
                      onChange={(e) => handleConfigChange('website_url', e.target.value)}
                      placeholder="https://www.lcsc.com"
                      className="flex-1 border border-gray-300 dark:border-gray-600 rounded-md px-3 py-2 bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                    />
                    {supplier.image_url && (
                      <img
                        src={supplier.image_url}
                        alt={supplier.display_name}
                        className="w-10 h-10 rounded object-contain border border-gray-300 dark:border-gray-600 p-1 flex-shrink-0"
                        title="Current favicon"
                        onError={(e) => {
                          e.currentTarget.style.display = 'none'
                        }}
                      />
                    )}
                  </div>
                  <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                    Supplier's official website - favicon will be automatically fetched and stored
                    locally when you save
                  </p>
                </div>
                <div className="md:col-span-2">
                  <label className="flex items-center space-x-2">
                    <input
                      type="checkbox"
                      checked={config.enabled}
                      onChange={(e) => handleConfigChange('enabled', e.target.checked)}
                      className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                    />
                    <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
                      Enable this supplier configuration
                    </span>
                  </label>
                </div>
              </div>
            </div>

            {/* Credentials Configuration - Backend Driven */}
            <div className="bg-gray-50 dark:bg-gray-700/50 rounded-lg p-4">
              <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-4">
                Credentials Setup
              </h3>
              {loadingCapabilities ? (
                <div className="text-center py-4">
                  <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-blue-600 mx-auto"></div>
                  <p className="text-sm text-gray-500 mt-2">Loading credential requirements...</p>
                </div>
              ) : (
                <CredentialEditor
                  supplierName={supplier.supplier_name}
                  credentialSchema={credentialSchema}
                  currentlyConfigured={credentialStatus?.fully_configured || false}
                  credentialStatus={credentialStatus}
                  onCredentialsReady={handleCredentialsReady}
                  onSave={handleCredentialsSave}
                  loading={loadingCapabilities}
                />
              )}
            </div>

            {/* Capabilities - Compact */}
            <div className="bg-gray-50 dark:bg-gray-700/50 rounded-lg p-4">
              <div className="flex items-center justify-between mb-3">
                <h3 className="text-lg font-medium text-gray-900 dark:text-white">
                  Supported Capabilities
                </h3>
                <span className="text-xs text-gray-500 dark:text-gray-400 font-medium">
                  {availableCapabilities.length} capabilities
                </span>
              </div>

              {loadingCapabilities ? (
                <div className="text-center py-4">
                  <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-blue-600 mx-auto"></div>
                  <p className="text-sm text-gray-500 mt-2">Loading capabilities...</p>
                </div>
              ) : (
                <div className="flex flex-wrap gap-2">
                  {availableCapabilities.map((capability) => {
                    // Create human-readable labels for capabilities (dynamic fallback)
                    const getCapabilityLabel = (cap: string) => {
                      return cap
                        .replace(/_/g, ' ')
                        .replace(/\b\w/g, (l) => l.toUpperCase())
                        .replace(/Fetch /g, '')
                        .replace(/Get /g, '')
                        .trim()
                    }

                    const getCapabilityDescription = (cap: string) => {
                      const verb = cap.includes('fetch')
                        ? 'Fetch'
                        : cap.includes('search')
                          ? 'Search for'
                          : cap.includes('import')
                            ? 'Import'
                            : 'Support'
                      const object = cap
                        .replace(/^(fetch_|search_|get_|import_)/, '')
                        .replace(/_/g, ' ')
                      return `${verb} ${object}`
                    }

                    return (
                      <div key={capability} className="group relative">
                        <span className="inline-flex items-center px-2 py-1 rounded-md text-xs font-medium bg-green-100 dark:bg-green-900/30 text-green-800 dark:text-green-200 cursor-help">
                          ✓ {getCapabilityLabel(capability)}
                        </span>
                        <div className="absolute bottom-full left-1/2 transform -translate-x-1/2 mb-2 w-48 p-2 bg-black text-white text-xs rounded opacity-0 group-hover:opacity-100 transition-opacity duration-200 pointer-events-none z-10">
                          {getCapabilityDescription(capability)}
                        </div>
                      </div>
                    )
                  })}
                </div>
              )}
            </div>

            {/* Custom Headers */}
            <div className="bg-gray-50 dark:bg-gray-700/50 rounded-lg p-4">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-lg font-medium text-gray-900 dark:text-white">
                  Custom Headers
                </h3>
                <button
                  onClick={addCustomHeader}
                  className="text-sm text-blue-600 dark:text-blue-400 hover:text-blue-500 dark:hover:text-blue-300"
                >
                  Add Header
                </button>
              </div>
              <div className="space-y-2">
                {Object.entries(config.custom_headers || {}).map(([key, value]) => (
                  <div key={key} className="flex items-center space-x-2">
                    <input
                      type="text"
                      value={key}
                      readOnly
                      className="flex-1 border border-gray-300 dark:border-gray-600 rounded-md px-3 py-2 bg-gray-100 dark:bg-gray-600 text-gray-900 dark:text-white"
                    />
                    <input
                      type="text"
                      value={value}
                      onChange={(e) => handleCustomHeaderChange(key, e.target.value)}
                      placeholder="Header value"
                      className="flex-1 border border-gray-300 dark:border-gray-600 rounded-md px-3 py-2 bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                    />
                    <button
                      onClick={() => handleCustomHeaderChange(key, '')}
                      className="text-red-600 dark:text-red-400 hover:text-red-500 dark:hover:text-red-300"
                    >
                      <X className="w-4 h-4" />
                    </button>
                  </div>
                ))}
                {Object.keys(config.custom_headers || {}).length === 0 && (
                  <p className="text-sm text-gray-500 dark:text-gray-400 italic">
                    No custom headers configured
                  </p>
                )}
              </div>
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between p-6 border-t border-gray-200 dark:border-gray-700">
          <div className="text-sm text-gray-500 dark:text-gray-400">
            {errors.length > 0 ? (
              <span className="text-red-600 dark:text-red-400">
                ⚠️ Please fix validation errors above
              </span>
            ) : hasChanges() ? (
              'You have unsaved changes'
            ) : (
              'No changes made'
            )}
          </div>
          <div className="flex items-center space-x-3">
            <button
              onClick={handleTestConnection}
              disabled={testing || loading}
              className="inline-flex items-center px-4 py-2 border border-gray-300 dark:border-gray-600 text-sm font-medium rounded-md text-gray-700 dark:text-gray-200 bg-white dark:bg-gray-700 hover:bg-gray-50 dark:hover:bg-gray-600 disabled:opacity-50"
            >
              <TestTube className={`w-4 h-4 mr-2 ${testing ? 'animate-pulse' : ''}`} />
              {testing ? 'Testing...' : 'Test Connection'}
            </button>
            <button
              onClick={onClose}
              disabled={loading}
              className="px-4 py-2 border border-gray-300 dark:border-gray-600 text-sm font-medium rounded-md text-gray-700 dark:text-gray-200 bg-white dark:bg-gray-700 hover:bg-gray-50 dark:hover:bg-gray-600 disabled:opacity-50"
            >
              Cancel
            </button>
            <button
              onClick={handleSubmit}
              disabled={loading || !hasChanges()}
              title={
                errors.length > 0
                  ? `Cannot save: ${errors.join(', ')}`
                  : !hasChanges()
                    ? 'No changes to save'
                    : 'Save the current configuration changes'
              }
              className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 disabled:opacity-50"
            >
              {loading ? (
                <>
                  <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                  Saving...
                </>
              ) : (
                <>
                  <Save className="w-4 h-4 mr-2" />
                  Save Changes
                </>
              )}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
