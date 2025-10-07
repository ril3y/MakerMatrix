/**
 * Dynamic Add Supplier Modal
 *
 * Modal that dynamically discovers available suppliers and builds configuration forms
 * based on their schemas. Works with the new modular supplier system.
 */

import React, { useState, useEffect } from 'react'
import { X, AlertTriangle, CheckCircle, Settings } from 'lucide-react'
import type { SupplierInfo } from '../../services/dynamic-supplier.service'
import { dynamicSupplierService } from '../../services/dynamic-supplier.service'
import { DynamicSupplierConfigForm } from './DynamicSupplierConfigForm'

interface DynamicAddSupplierModalProps {
  onClose: () => void
  onSuccess: () => void
  existingSuppliers?: string[] // List of already configured supplier names
}

export const DynamicAddSupplierModal: React.FC<DynamicAddSupplierModalProps> = ({
  onClose,
  onSuccess,
  existingSuppliers = [],
}) => {
  const [step, setStep] = useState(1) // 1: Select Supplier, 2: Configure
  const [selectedSupplier, setSelectedSupplier] = useState<string>('')
  const [availableSuppliers, setAvailableSuppliers] = useState<Record<string, SupplierInfo>>({})
  const [loading, setLoading] = useState(true)
  const [configuring, setConfiguring] = useState(false)
  const [errors, setErrors] = useState<string[]>([])

  const [credentials, setCredentials] = useState<Record<string, any>>({})
  const [config, setConfig] = useState<Record<string, any>>({})
  const [testLoading, setTestLoading] = useState(false)
  const [testResult, setTestResult] = useState<{
    success: boolean
    message: string
    details?: any
  } | null>(null)

  useEffect(() => {
    loadAvailableSuppliers()
  }, [])

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

  const loadAvailableSuppliers = async () => {
    try {
      setLoading(true)
      setErrors([])
      const suppliersInfo = await dynamicSupplierService.getAllSuppliersInfo()
      console.log('API call successful - suppliersInfo:', suppliersInfo)
      console.log('Type of suppliersInfo:', typeof suppliersInfo)
      console.log('Object.keys length:', Object.keys(suppliersInfo || {}).length)

      setAvailableSuppliers(suppliersInfo || {})

      // Verify state was set correctly
      console.log('State should be set now. Checking in next tick...')
      setTimeout(() => {
        console.log('Current availableSuppliers state:', availableSuppliers)
      }, 100)
    } catch (error) {
      console.error('Failed to load suppliers:', error)
      setAvailableSuppliers({})
      setErrors([
        `Failed to load available suppliers: ${error instanceof Error ? error.message : 'Unknown error'}`,
      ])
    } finally {
      setLoading(false)
    }
  }

  const handleSupplierSelection = (supplierName: string) => {
    setSelectedSupplier(supplierName)
    setStep(2)
    setErrors([])
    setTestResult(null)
  }

  const handleTestConnection = async () => {
    try {
      setTestLoading(true)
      setTestResult(null)

      const result = await dynamicSupplierService.testConnection(
        selectedSupplier,
        credentials,
        config
      )
      setTestResult(result)
    } catch (error) {
      console.error('Test connection failed:', error)
      setTestResult({
        success: false,
        message: `Test failed: ${error instanceof Error ? error.message : 'Unknown error'}`,
      })
    } finally {
      setTestLoading(false)
    }
  }

  const handleSave = async () => {
    try {
      setConfiguring(true)
      setErrors([])

      // Get supplier info to construct the configuration
      const supplierInfo = availableSuppliers[selectedSupplier]
      if (!supplierInfo) {
        throw new Error('Supplier information not found')
      }

      // Check if this supplier actually needs to be saved
      // Some suppliers like LCSC are just public APIs that don't need persistent config
      const needsCredentials = Object.keys(credentials).length > 0
      const needsConfiguration = Object.keys(config).length > 0

      if (!needsCredentials && !needsConfiguration) {
        // For suppliers like LCSC that don't need saved config, just mark as successful
        console.log(`${selectedSupplier} is a public API - no configuration needed to save`)
      } else {
        // Use the existing supplier service to save the configuration
        const { supplierService } = await import('../../services/supplier.service')

        // Convert capabilities array to individual boolean fields that backend expects
        const capabilities = supplierInfo.capabilities || []
        const capabilityFields = {
          supports_datasheet: capabilities.includes('fetch_datasheet'),
          supports_image: capabilities.includes('fetch_image'),
          supports_pricing: capabilities.includes('fetch_pricing'),
          supports_stock: capabilities.includes('fetch_stock'),
          supports_specifications: capabilities.includes('fetch_specifications'),
        }

        // Create supplier configuration with consistent naming
        const supplierConfig = {
          supplier_name: selectedSupplier.toUpperCase(), // Use uppercase for consistency
          display_name: supplierInfo.display_name,
          description: supplierInfo.description,
          api_type: 'rest', // Default API type
          base_url: supplierInfo.website_url || '',
          enabled: true,
          ...capabilityFields, // Spread the individual capability fields
          configuration: config,
        }

        console.log('Creating supplier configuration:', supplierConfig)

        try {
          // Try to create new supplier
          await supplierService.createSupplier(supplierConfig)
        } catch (error) {
          const err = error as { response?: { status?: number } }
          if (err.response?.status === 409) {
            // Supplier already exists, try to update instead
            console.log(`Supplier ${selectedSupplier} already exists, updating configuration...`)
            await supplierService.updateSupplier(supplierConfig.supplier_name, {
              display_name: supplierConfig.display_name,
              description: supplierConfig.description,
              enabled: supplierConfig.enabled,
              ...capabilityFields, // Use the converted capability fields
              configuration: config,
            })
          } else {
            throw error // Re-throw if it's not a conflict error
          }
        }

        // Save credentials if any
        if (needsCredentials) {
          console.log('Saving supplier credentials:', credentials)
          await supplierService.updateCredentials(supplierConfig.supplier_name, credentials)
        }
      }

      console.log('Supplier configuration saved successfully')
      onSuccess()
    } catch (error) {
      console.error('Failed to save supplier configuration:', error)
      setErrors([
        `Failed to save configuration: ${error instanceof Error ? error.message : 'Unknown error'}`,
      ])
    } finally {
      setConfiguring(false)
    }
  }

  if (loading) {
    return (
      <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow-xl max-w-2xl w-full p-8">
          <div className="flex items-center justify-center">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mr-3"></div>
            <span className="text-gray-600 dark:text-gray-400">Loading available suppliers...</span>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-xl max-w-4xl w-full max-h-[90vh] overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-gray-200 dark:border-gray-700">
          <div>
            <h2 className="text-xl font-semibold text-gray-900 dark:text-white">
              Add Supplier Configuration
            </h2>
            <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
              {step === 1
                ? 'Choose a supplier to configure'
                : `Configure ${availableSuppliers[selectedSupplier]?.display_name || selectedSupplier}`}
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
          {step === 1 ? (
            /* Step 1: Select Supplier */
            <div>
              {errors.length > 0 && (
                <div className="mb-6 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-md p-4">
                  <div className="flex">
                    <AlertTriangle className="w-5 h-5 text-red-400" />
                    <div className="ml-3">
                      <h3 className="text-sm font-medium text-red-800 dark:text-red-200">
                        Error Loading Suppliers
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

              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {Object.entries(availableSuppliers || {})
                  .filter(([name]) => !existingSuppliers.includes(name.toUpperCase()))
                  .map(([name, info]) => {
                    const isAlreadyConfigured = existingSuppliers.includes(name.toUpperCase())
                    return (
                      <button
                        key={name}
                        onClick={() => !isAlreadyConfigured && handleSupplierSelection(name)}
                        disabled={isAlreadyConfigured}
                        className={`p-4 border-2 rounded-lg text-left transition-colors ${
                          isAlreadyConfigured
                            ? 'border-gray-300 dark:border-gray-600 bg-gray-100 dark:bg-gray-700 opacity-50 cursor-not-allowed'
                            : 'border-gray-200 dark:border-gray-600 hover:border-blue-500 hover:bg-gray-50 dark:hover:bg-gray-700'
                        }`}
                      >
                        <div className="flex items-center space-x-3">
                          <Settings className="w-8 h-8 text-blue-600 dark:text-blue-400" />
                          <div>
                            <h3 className="font-medium text-gray-900 dark:text-white">
                              {info.display_name}
                              {isAlreadyConfigured && (
                                <span className="ml-2 text-xs text-yellow-600 dark:text-yellow-400">
                                  (Already Configured)
                                </span>
                              )}
                            </h3>
                            <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
                              {info.description}
                            </p>
                            <div className="mt-2 flex flex-wrap gap-1">
                              {info.capabilities.slice(0, 3).map((capability) => (
                                <span
                                  key={capability}
                                  className="inline-block px-2 py-1 text-xs bg-blue-100 dark:bg-blue-900 text-blue-800 dark:text-blue-200 rounded"
                                >
                                  {capability.replace('_', ' ')}
                                </span>
                              ))}
                              {info.capabilities.length > 3 && (
                                <span className="inline-block px-2 py-1 text-xs bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-400 rounded">
                                  +{info.capabilities.length - 3} more
                                </span>
                              )}
                            </div>
                          </div>
                        </div>
                      </button>
                    )
                  })}
              </div>

              {(() => {
                const suppliersCount = Object.keys(availableSuppliers || {}).length
                console.log('Render check - suppliers count:', suppliersCount)
                console.log('Render check - availableSuppliers:', availableSuppliers)
                console.log('Render check - loading:', loading)

                if (suppliersCount === 0 && !loading) {
                  return (
                    <div className="text-center py-8">
                      <Settings className="w-12 h-12 text-gray-400 mx-auto mb-4" />
                      <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-2">
                        No Suppliers Available
                      </h3>
                      <p className="text-gray-500 dark:text-gray-400">
                        No supplier implementations were found. Check your backend configuration.
                      </p>
                    </div>
                  )
                }
                return null
              })()}
            </div>
          ) : (
            /* Step 2: Configure Supplier */
            <DynamicSupplierConfigForm
              supplierName={selectedSupplier}
              onCredentialsChange={setCredentials}
              onConfigChange={setConfig}
              errors={errors}
              onTest={handleTestConnection}
              isTestLoading={testLoading}
              testResult={testResult}
            />
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between p-6 border-t border-gray-200 dark:border-gray-700">
          <div>
            {step === 2 && (
              <button
                onClick={() => setStep(1)}
                disabled={configuring}
                className="text-sm text-gray-600 dark:text-gray-400 hover:text-gray-500 dark:hover:text-gray-300 disabled:opacity-50"
              >
                ← Back to Supplier Selection
              </button>
            )}
          </div>
          <div className="flex items-center space-x-3">
            <button
              onClick={onClose}
              disabled={configuring}
              className="px-4 py-2 border border-gray-300 dark:border-gray-600 text-sm font-medium rounded-md text-gray-700 dark:text-gray-200 bg-white dark:bg-gray-700 hover:bg-gray-50 dark:hover:bg-gray-600 disabled:opacity-50"
            >
              Cancel
            </button>
            {step === 2 && (
              <button
                onClick={handleSave}
                disabled={configuring}
                className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 disabled:opacity-50"
              >
                {configuring ? (
                  <>
                    <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                    Saving...
                  </>
                ) : (
                  <>
                    <CheckCircle className="w-4 h-4 mr-2" />
                    Save Configuration
                  </>
                )}
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
