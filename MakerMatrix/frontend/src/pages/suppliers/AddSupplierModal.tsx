/**
 * Add Supplier Configuration Modal
 *
 * Modal for creating new supplier configurations with predefined templates
 * and custom configuration options.
 */

import React, { useState } from 'react'
import { X, AlertTriangle, CheckCircle, Settings } from 'lucide-react'
import { supplierService, SupplierConfigCreate } from '../../services/supplier.service'
import { DigiKeyConfigForm } from './DigiKeyConfigForm'
import { LCSCConfigForm } from './LCSCConfigForm'
import { MouserConfigForm } from './MouserConfigForm'
import { prepareDigiKeyConfig } from './configs/digikey-config'
import { prepareLCSCConfig } from './configs/lcsc-config'
import { prepareMouserConfig } from './configs/mouser-config'

interface AddSupplierModalProps {
  onClose: () => void
  onSuccess: () => void
}

export const AddSupplierModal: React.FC<AddSupplierModalProps> = ({ onClose, onSuccess }) => {
  const [step, setStep] = useState(1) // 1: Select Type, 2: Configure
  const [selectedType, setSelectedType] = useState<string>('')
  const [loading, setLoading] = useState(false)
  const [errors, setErrors] = useState<string[]>([])

  // Base configuration - supplier-specific fields handled separately
  const [config, setConfig] = useState<SupplierConfigCreate>({
    supplier_name: '',
    display_name: '',
    description: '',
    api_type: 'rest',
    base_url: '',
    api_version: '',
    rate_limit_per_minute: 60,
    timeout_seconds: 30,
    max_retries: 3,
    retry_backoff: 1.0,
    enabled: true,
    supports_datasheet: false,
    supports_image: false,
    supports_pricing: false,
    supports_stock: false,
    supports_specifications: false,
    custom_headers: {},
    custom_parameters: {},
  })

  // Supplier-specific data (e.g., DigiKey fields)
  const [supplierSpecificData, setSupplierSpecificData] = useState<Record<string, any>>({})

  const supplierTypes = supplierService.getAvailableSupplierTypes()
  const capabilities = supplierService.getSupportedCapabilities()

  const handleTypeSelection = (typeName: string) => {
    setSelectedType(typeName)

    // Apply predefined configuration for known suppliers
    const presets: Record<string, Partial<SupplierConfigCreate>> = {
      lcsc: {
        supplier_name: 'lcsc',
        display_name: 'LCSC Electronics',
        description: 'Chinese electronics component supplier with EasyEDA integration',
        base_url: 'https://easyeda.com/api/components',
        api_version: 'v1',
        rate_limit_per_minute: 100,
        supports_datasheet: true,
        supports_image: true,
        supports_pricing: true,
        supports_specifications: true,
      },
      digikey: {
        supplier_name: 'digikey',
        display_name: 'DigiKey Electronics',
        description: 'Global electronic components distributor',
        base_url: 'https://api.digikey.com/v1',
        api_version: 'v1',
        rate_limit_per_minute: 1000,
        supports_datasheet: true,
        supports_image: true,
        supports_pricing: true,
        supports_stock: true,
        supports_specifications: true,
      },
      mouser: {
        supplier_name: 'mouser',
        display_name: 'Mouser Electronics',
        description: 'Electronic component distributor with extensive catalog',
        base_url: 'https://api.mouser.com/api/v1',
        api_version: 'v1',
        rate_limit_per_minute: 1000,
        supports_datasheet: true,
        supports_image: true,
        supports_pricing: true,
        supports_stock: true,
        supports_specifications: true,
      },
    }

    if (presets[typeName]) {
      setConfig((prev) => ({ ...prev, ...presets[typeName] }))
    }
  }

  const handleConfigChange = (field: string, value: any) => {
    // Check if this is a base config field or supplier-specific
    if (field in config) {
      setConfig((prev) => ({ ...prev, [field]: value }))
    } else {
      // Store supplier-specific fields separately
      setSupplierSpecificData((prev) => ({ ...prev, [field]: value }))
    }
    setErrors([]) // Clear errors when user makes changes
  }

  const handleCapabilityChange = (capability: string, enabled: boolean) => {
    const field = `supports_${capability.replace('fetch_', '')}` as keyof SupplierConfigCreate
    handleConfigChange(field, enabled)
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

  const handleSubmit = async () => {
    try {
      setLoading(true)
      setErrors([])

      // Prepare configuration using supplier-specific transformation
      let configForAPI: SupplierConfigCreate = { ...config }

      // Apply supplier-specific transformations
      if (selectedType === 'digikey') {
        configForAPI = prepareDigiKeyConfig(config, supplierSpecificData)
      } else if (selectedType === 'lcsc') {
        configForAPI = prepareLCSCConfig(config, supplierSpecificData)
      } else if (selectedType === 'mouser') {
        configForAPI = prepareMouserConfig(config, supplierSpecificData)
      }

      // Validate configuration
      const validationErrors = supplierService.validateConfig(configForAPI)
      if (validationErrors.length > 0) {
        setErrors(validationErrors)
        return
      }

      // Create supplier
      await supplierService.createSupplier(configForAPI)
      onSuccess()
    } catch (err: any) {
      const errorMessage = err.response?.data?.detail || 'Failed to create supplier configuration'
      setErrors([errorMessage])
    } finally {
      setLoading(false)
    }
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
              {step === 1 ? 'Choose a supplier type to get started' : 'Configure supplier settings'}
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
            /* Step 1: Select Supplier Type */
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {supplierTypes.map((type) => (
                <button
                  key={type.name}
                  onClick={() => {
                    handleTypeSelection(type.name)
                    setStep(2)
                  }}
                  className={`p-4 border-2 rounded-lg text-left hover:border-blue-500 transition-colors ${
                    selectedType === type.name
                      ? 'border-blue-500 bg-blue-50 dark:bg-blue-900/20'
                      : 'border-gray-200 dark:border-gray-600'
                  }`}
                >
                  <div className="flex items-center space-x-3">
                    <Settings className="w-8 h-8 text-blue-600 dark:text-blue-400" />
                    <div>
                      <h3 className="font-medium text-gray-900 dark:text-white">
                        {type.display_name}
                      </h3>
                      <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
                        {type.description}
                      </p>
                    </div>
                  </div>
                </button>
              ))}
            </div>
          ) : (
            /* Step 2: Configure Supplier */
            <div className="space-y-6">
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

              {/* Supplier-Specific Configuration Forms */}
              {selectedType === 'digikey' && (
                <DigiKeyConfigForm
                  config={config}
                  onConfigChange={handleConfigChange}
                  errors={errors}
                />
              )}
              {selectedType === 'lcsc' && (
                <LCSCConfigForm
                  config={config}
                  onConfigChange={handleConfigChange}
                  errors={errors}
                />
              )}
              {selectedType === 'mouser' && (
                <MouserConfigForm
                  config={config}
                  onConfigChange={handleConfigChange}
                  errors={errors}
                />
              )}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between p-6 border-t border-gray-200 dark:border-gray-700">
          <div>
            {step === 2 && (
              <button
                onClick={() => setStep(1)}
                disabled={loading}
                className="text-sm text-gray-600 dark:text-gray-400 hover:text-gray-500 dark:hover:text-gray-300 disabled:opacity-50"
              >
                ← Back to Supplier Types
              </button>
            )}
          </div>
          <div className="flex items-center space-x-3">
            <button
              onClick={onClose}
              disabled={loading}
              className="px-4 py-2 border border-gray-300 dark:border-gray-600 text-sm font-medium rounded-md text-gray-700 dark:text-gray-200 bg-white dark:bg-gray-700 hover:bg-gray-50 dark:hover:bg-gray-600 disabled:opacity-50"
            >
              Cancel
            </button>
            {step === 2 && (
              <button
                onClick={handleSubmit}
                disabled={loading}
                className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 disabled:opacity-50"
              >
                {loading ? (
                  <>
                    <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                    Creating...
                  </>
                ) : (
                  <>
                    <CheckCircle className="w-4 h-4 mr-2" />
                    Create Supplier
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
