/**
 * Dynamic Supplier Configuration Form
 *
 * Automatically builds a configuration form based on the supplier's schema.
 * Works with any supplier that implements the BaseSupplier interface.
 */

import React, { useState, useEffect } from 'react'
import { AlertTriangle, CheckCircle, HelpCircle, ExternalLink, Info } from 'lucide-react'
import { CustomSelect } from '@/components/ui/CustomSelect'
import { FieldDefinition, SupplierInfo } from '../../services/dynamic-supplier.service'
import { SupplierTestResult } from '../../components/suppliers/SupplierTestResult'

interface DynamicSupplierConfigFormProps {
  supplierName: string
  onCredentialsChange: (credentials: Record<string, any>) => void
  onConfigChange: (config: Record<string, any>) => void
  errors: string[]
  onTest?: () => void
  isTestLoading?: boolean
  testResult?: { success: boolean; message: string; details?: any } | null
}

export const DynamicSupplierConfigForm: React.FC<DynamicSupplierConfigFormProps> = ({
  supplierName,
  onCredentialsChange,
  onConfigChange,
  errors,
  onTest,
  isTestLoading,
  testResult,
}) => {
  const [supplierInfo, setSupplierInfo] = useState<SupplierInfo | null>(null)
  const [credentialFields, setCredentialFields] = useState<FieldDefinition[]>([])
  const [configFields, setConfigFields] = useState<FieldDefinition[]>([])
  const [credentials, setCredentials] = useState<Record<string, any>>({})
  const [config, setConfig] = useState<Record<string, any>>({})
  const [loading, setLoading] = useState(true)
  const [loadingError, setLoadingError] = useState<string | null>(null)

  useEffect(() => {
    loadSupplierData()
  }, [supplierName])

  const reloadSchemasWithConfig = async (currentConfig: Record<string, any>) => {
    try {
      setLoading(true)
      const { dynamicSupplierService } = await import('../../services/dynamic-supplier.service')

      console.log('Reloading schemas with current config:', currentConfig)

      // Use the new context-aware schema endpoints
      const [credSchema, configSchema] = await Promise.all([
        dynamicSupplierService.getCredentialSchemaWithConfig(
          supplierName,
          credentials,
          currentConfig
        ),
        dynamicSupplierService.getConfigurationSchemaWithConfig(
          supplierName,
          credentials,
          currentConfig
        ),
      ])

      console.log('Reloaded credential schema:', credSchema)
      console.log('Reloaded config schema:', configSchema)

      // Ensure schemas are arrays
      const safeCredSchema = Array.isArray(credSchema) ? credSchema : []
      const safeConfigSchema = Array.isArray(configSchema) ? configSchema : []

      setCredentialFields(safeCredSchema)
      setConfigFields(safeConfigSchema)

      // Keep existing config values but add any new default values for new fields
      const updatedConfig = { ...currentConfig }
      safeConfigSchema.forEach((field) => {
        if (!(field.name in updatedConfig) && field.default_value !== undefined) {
          updatedConfig[field.name] = field.default_value
        }
      })

      setConfig(updatedConfig)
      onConfigChange(updatedConfig)
    } catch (error) {
      console.error('Failed to reload schemas:', error)
    } finally {
      setLoading(false)
    }
  }

  const loadSupplierData = async () => {
    try {
      setLoading(true)
      setLoadingError(null)

      const { dynamicSupplierService } = await import('../../services/dynamic-supplier.service')

      // Load supplier info, schemas, and environment defaults in parallel
      console.log('Loading supplier data for:', supplierName)
      const [info, credSchema, configSchema, envDefaults] = await Promise.all([
        dynamicSupplierService.getSupplierInfo(supplierName),
        dynamicSupplierService.getCredentialSchema(supplierName),
        dynamicSupplierService.getConfigurationSchema(supplierName),
        dynamicSupplierService.getSupplierEnvDefaults(supplierName),
      ])

      console.log('Loaded supplier info:', info)
      console.log('Loaded credential schema:', credSchema)
      console.log('Loaded config schema:', configSchema)
      console.log('Loaded environment defaults:', envDefaults)

      setSupplierInfo(info)

      // Ensure schemas are arrays
      const safeCredSchema = Array.isArray(credSchema) ? credSchema : []
      const safeConfigSchema = Array.isArray(configSchema) ? configSchema : []

      setCredentialFields(safeCredSchema)
      setConfigFields(safeConfigSchema)

      // Initialize with default values from schema
      const defaultCredentials: Record<string, any> = {}
      safeCredSchema.forEach((field) => {
        if (field.default_value !== undefined) {
          defaultCredentials[field.name] = field.default_value
        }
      })

      const defaultConfig: Record<string, any> = {}
      safeConfigSchema.forEach((field) => {
        if (field.default_value !== undefined) {
          defaultConfig[field.name] = field.default_value
        }
      })

      // Override with environment defaults if available
      const finalCredentials = { ...defaultCredentials, ...envDefaults }

      console.log('Final credentials with env defaults:', finalCredentials)

      setCredentials(finalCredentials)
      setConfig(defaultConfig)
      onCredentialsChange(finalCredentials)
      onConfigChange(defaultConfig)
    } catch (error) {
      console.error('Failed to load supplier data:', error)
      setLoadingError(
        `Failed to load supplier configuration: ${error instanceof Error ? error.message : 'Unknown error'}`
      )
    } finally {
      setLoading(false)
    }
  }

  const handleCredentialChange = (fieldName: string, value: any) => {
    const newCredentials = { ...credentials, [fieldName]: value }
    setCredentials(newCredentials)
    onCredentialsChange(newCredentials)
  }

  const handleConfigChange = (fieldName: string, value: any) => {
    const newConfig = { ...config, [fieldName]: value }
    setConfig(newConfig)
    onConfigChange(newConfig)

    // For certain fields that affect schema structure, reload schemas
    // This handles dynamic schema changes like McMaster-Carr's mode selector
    if (fieldName === 'mode') {
      console.log(`Configuration field '${fieldName}' changed to '${value}', reloading schemas...`)
      reloadSchemasWithConfig(newConfig)
    }
  }

  const renderField = (field: FieldDefinition, value: any, onChange: (value: any) => void) => {
    const fieldId = `field-${field.name}`

    switch (field.field_type) {
      case 'password':
        return (
          <input
            id={fieldId}
            type="password"
            value={value || ''}
            onChange={(e) => onChange(e.target.value)}
            placeholder={field.placeholder}
            className="w-full border border-gray-300 dark:border-gray-600 rounded-md px-3 py-2 bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
            required={field.required}
          />
        )

      case 'email':
        return (
          <input
            id={fieldId}
            type="email"
            value={value || ''}
            onChange={(e) => onChange(e.target.value)}
            placeholder={field.placeholder}
            className="w-full border border-gray-300 dark:border-gray-600 rounded-md px-3 py-2 bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
            required={field.required}
          />
        )

      case 'url':
        return (
          <input
            id={fieldId}
            type="url"
            value={value || ''}
            onChange={(e) => onChange(e.target.value)}
            placeholder={field.placeholder}
            className="w-full border border-gray-300 dark:border-gray-600 rounded-md px-3 py-2 bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
            required={field.required}
          />
        )

      case 'number':
        return (
          <input
            id={fieldId}
            type="number"
            value={value || ''}
            onChange={(e) => onChange(parseFloat(e.target.value) || 0)}
            placeholder={field.placeholder}
            className="w-full border border-gray-300 dark:border-gray-600 rounded-md px-3 py-2 bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
            required={field.required}
            min={field.validation?.min_length}
            max={field.validation?.max_length}
          />
        )

      case 'boolean':
        return (
          <label className="flex items-center space-x-2">
            <input
              id={fieldId}
              type="checkbox"
              checked={!!value}
              onChange={(e) => onChange(e.target.checked)}
              className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
            />
            <span className="text-sm text-gray-700 dark:text-gray-300">
              {field.description || 'Enable this option'}
            </span>
          </label>
        )

      case 'select':
        return (
          <CustomSelect
            value={value || ''}
            onChange={onChange}
            options={[
              { value: '', label: 'Select...' },
              ...(field.options?.map((option) => ({
                value: option.value,
                label: option.label,
              })) || []),
            ]}
            placeholder="Select..."
          />
        )

      case 'textarea':
        return (
          <textarea
            id={fieldId}
            value={value || ''}
            onChange={(e) => onChange(e.target.value)}
            placeholder={field.placeholder}
            rows={3}
            className="w-full border border-gray-300 dark:border-gray-600 rounded-md px-3 py-2 bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
            required={field.required}
          />
        )

      default:
        return (
          <input
            id={fieldId}
            type="text"
            value={value || ''}
            onChange={(e) => onChange(e.target.value)}
            placeholder={field.placeholder}
            className="w-full border border-gray-300 dark:border-gray-600 rounded-md px-3 py-2 bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
            required={field.required}
          />
        )
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center p-8">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
        <span className="ml-3 text-gray-600 dark:text-gray-400">
          Loading supplier configuration...
        </span>
      </div>
    )
  }

  if (loadingError) {
    return (
      <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-md p-4">
        <div className="flex">
          <AlertTriangle className="w-5 h-5 text-red-400" />
          <div className="ml-3">
            <h3 className="text-sm font-medium text-red-800 dark:text-red-200">
              Configuration Error
            </h3>
            <p className="mt-1 text-sm text-red-700 dark:text-red-300">{loadingError}</p>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Supplier Information */}
      {supplierInfo && (
        <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-md p-4">
          <div className="flex">
            <Info className="w-5 h-5 text-blue-400" />
            <div className="ml-3">
              <h3 className="text-sm font-medium text-blue-800 dark:text-blue-200">
                {supplierInfo.display_name}
              </h3>
              <p className="mt-1 text-sm text-blue-700 dark:text-blue-300">
                {supplierInfo.description}
              </p>
              <div className="mt-2 flex flex-wrap gap-4 text-xs">
                {supplierInfo.website_url && (
                  <a
                    href={supplierInfo.website_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center text-blue-600 dark:text-blue-400 hover:text-blue-500"
                  >
                    Website <ExternalLink className="w-3 h-3 ml-1" />
                  </a>
                )}
                {supplierInfo.api_documentation_url && (
                  <a
                    href={supplierInfo.api_documentation_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center text-blue-600 dark:text-blue-400 hover:text-blue-500"
                  >
                    API Docs <ExternalLink className="w-3 h-3 ml-1" />
                  </a>
                )}
                {supplierInfo.rate_limit_info && (
                  <span className="text-blue-600 dark:text-blue-400">
                    Rate Limit: {supplierInfo.rate_limit_info}
                  </span>
                )}
              </div>
              <div className="mt-2">
                <span className="text-xs text-blue-600 dark:text-blue-400">
                  Capabilities: {supplierInfo.capabilities.join(', ')}
                </span>
              </div>
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

      {/* Credentials Section */}
      {credentialFields.length > 0 && (
        <div className="bg-gray-50 dark:bg-gray-700/50 rounded-lg p-4">
          <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-4">Credentials</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {credentialFields.map((field) => (
              <div key={field.name}>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  {field.label} {field.required && <span className="text-red-500">*</span>}
                </label>
                {renderField(field, credentials[field.name], (value) =>
                  handleCredentialChange(field.name, value)
                )}
                {field.help_text && (
                  <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">{field.help_text}</p>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Configuration Section */}
      {configFields.length > 0 && (
        <div className="bg-gray-50 dark:bg-gray-700/50 rounded-lg p-4">
          <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-4">Configuration</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {configFields.map((field) => (
              <div key={field.name}>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  {field.label} {field.required && <span className="text-red-500">*</span>}
                </label>
                {renderField(field, config[field.name], (value) =>
                  handleConfigChange(field.name, value)
                )}
                {field.help_text && (
                  <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">{field.help_text}</p>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Test Connection */}
      {onTest && (
        <div className="bg-gray-50 dark:bg-gray-700/50 rounded-lg p-4">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-medium text-gray-900 dark:text-white">Test Connection</h3>
            <button
              onClick={onTest}
              disabled={isTestLoading}
              className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 disabled:opacity-50"
            >
              {isTestLoading ? (
                <>
                  <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                  Testing...
                </>
              ) : (
                <>
                  <HelpCircle className="w-4 h-4 mr-2" />
                  Test Connection
                </>
              )}
            </button>
          </div>

          {testResult && <SupplierTestResult testResult={testResult} />}
        </div>
      )}

      {/* OAuth Note */}
      {supplierInfo?.supports_oauth && (
        <div className="bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-md p-4">
          <div className="flex">
            <HelpCircle className="w-5 h-5 text-yellow-400" />
            <div className="ml-3">
              <h3 className="text-sm font-medium text-yellow-800 dark:text-yellow-200">
                OAuth Authentication Required
              </h3>
              <p className="mt-1 text-sm text-yellow-700 dark:text-yellow-300">
                This supplier uses OAuth authentication. After configuring your credentials, you'll
                need to complete the OAuth authorization process to use this supplier.
              </p>
            </div>
          </div>
        </div>
      )}

      {/* No Auth Required Note */}
      {credentialFields.length === 0 && (
        <div className="bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-md p-4">
          <div className="flex">
            <CheckCircle className="w-5 h-5 text-green-400" />
            <div className="ml-3">
              <h3 className="text-sm font-medium text-green-800 dark:text-green-200">
                No Authentication Required
              </h3>
              <p className="mt-1 text-sm text-green-700 dark:text-green-300">
                This supplier uses a public API and doesn't require any credentials.
              </p>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
