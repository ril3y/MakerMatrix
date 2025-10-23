/**
 * Reusable Credential Editor Component
 *
 * Provides a consistent interface for editing supplier credentials across all suppliers.
 * Shows masked current values, allows editing, and includes test functionality.
 */

import React, { useState, useEffect, useMemo, useRef } from 'react'
import { Eye, EyeOff, TestTube, Save, HelpCircle, CheckCircle, XCircle } from 'lucide-react'
import { useFormWithValidation } from '@/hooks/useFormWithValidation'
import {
  createCredentialFormSchema,
  type CredentialField,
  type CredentialFormData,
  type CredentialTestResult,
  type CredentialStatus,
} from '@/schemas/credentials'
import { FormInput } from '@/components/forms'
import toast from 'react-hot-toast'

interface CredentialEditorProps {
  supplierName: string
  credentialSchema: CredentialField[]
  currentlyConfigured?: boolean // Whether credentials are already set on backend
  credentialStatus?: CredentialStatus // Full credential status from backend
  onCredentialChange?: (credentials: CredentialFormData) => void
  onTest?: (credentials: CredentialFormData) => Promise<CredentialTestResult>
  onSave?: (credentials: CredentialFormData) => Promise<void>
  loading?: boolean
  onCredentialsReady?: (credentials: CredentialFormData) => void // Expose current credentials
}

export const CredentialEditor: React.FC<CredentialEditorProps> = ({
  supplierName,
  credentialSchema,
  currentlyConfigured = false,
  credentialStatus,
  onCredentialChange,
  onTest,
  onSave,
  loading = false,
  onCredentialsReady,
}) => {
  const [showValues, setShowValues] = useState<Record<string, boolean>>({})
  const [testing, setTesting] = useState(false)
  const [testResult, setTestResult] = useState<CredentialTestResult | null>(null)
  const [initialCredentials, setInitialCredentials] = useState<CredentialFormData>({})

  // Create dynamic form schema based on credential fields
  const formSchema = useMemo(() => {
    // Type assertion: credentialSchema comes from API with unknown types
    return createCredentialFormSchema(credentialSchema as Array<{
      name: string
      label: string
      field_type: string
      required: boolean
      description?: string
      placeholder?: string
      help_text?: string
    }>)
  }, [credentialSchema])

  // Form with validation
  const form = useFormWithValidation<CredentialFormData>({
    schema: formSchema,
    onSubmit: async (data) => {
      if (onSave) {
        await onSave(data)
        toast.success('Credentials saved successfully')
      }
    },
    onError: (error) => {
      console.error('Failed to save credentials:', error)
      toast.error('Failed to save credentials')
    },
  })

  // Initialize credentials when schema changes or credential status loads
  useEffect(() => {
    if (credentialSchema.length === 0) return

    const initializeCredentials = async () => {
      const credentials: CredentialFormData = {}
      const showValuesState: Record<string, boolean> = {}

      // Fetch actual credentials if any are configured
      let actualCredentials: CredentialFormData = {}
      if (
        credentialStatus &&
        (credentialStatus.has_database_credentials || credentialStatus.has_environment_credentials)
      ) {
        try {
          const apiUrl = `/api/suppliers/${supplierName.toLowerCase()}/credentials`
          const response = await fetch(apiUrl, {
            headers: { Authorization: `Bearer ${localStorage.getItem('auth_token')}` },
          })
          if (response.ok) {
            const data = await response.json()
            actualCredentials = data.data || data || {}
          } else {
            console.error('Credentials API failed:', response.status, response.statusText)
          }
        } catch (error) {
          console.error('Failed to fetch credentials:', error)
        }
      }

      credentialSchema.forEach((field) => {
        // Use actual value if available, otherwise empty string
        const actualValue = actualCredentials[field.name]
        credentials[field.name] = actualValue || ''

        // Password fields start hidden, text fields start visible
        showValuesState[field.name] = field.field_type !== 'password'
      })

      setInitialCredentials(credentials)
      setShowValues(showValuesState)

      // Reset form with initial data (using setValue for each field instead of reset)
      Object.entries(credentials).forEach(([key, value]) => {
        form.setValue(key as keyof CredentialFormData, value)
      })
    }

    initializeCredentials()
  }, [credentialSchema, credentialStatus, supplierName, form])

  // Watch form values and notify parent of changes
  const currentCredentials = form.watch() as unknown as CredentialFormData

  // Use a ref to track the last notified credentials to prevent infinite loops
  const lastNotifiedRef = useRef<string>('')

  useEffect(() => {
    if (currentCredentials && Object.keys(currentCredentials).length > 0) {
      const credentialsString = JSON.stringify(currentCredentials)

      // Only notify if credentials actually changed
      if (credentialsString !== lastNotifiedRef.current) {
        lastNotifiedRef.current = credentialsString
        onCredentialChange?.(currentCredentials)
        onCredentialsReady?.(currentCredentials)
      }
    }
  }, [currentCredentials, onCredentialChange, onCredentialsReady])

  const toggleShowValue = (fieldName: string) => {
    setShowValues((prev) => ({ ...prev, [fieldName]: !prev[fieldName] }))
  }

  const handleTest = async () => {
    if (!onTest) return

    try {
      setTesting(true)
      setTestResult(null)
      const result = await onTest(currentCredentials)
      setTestResult(result)
    } catch (error) {
      setTestResult({
        success: false,
        message: error instanceof Error ? error.message : 'Test failed',
      })
    } finally {
      setTesting(false)
    }
  }

  const getConfiguredStatus = (): boolean => {
    if (!credentialStatus) return false
    return credentialStatus.fully_configured || false
  }

  const getStatusText = (): string => {
    if (!credentialStatus) return 'Loading...'

    if (credentialStatus.error) {
      return 'Error Loading Status'
    }

    const hasDb = credentialStatus.has_database_credentials
    const hasEnv = credentialStatus.has_environment_credentials
    const isConfigured = credentialStatus.fully_configured

    if (isConfigured) {
      if (hasDb && hasEnv) {
        return 'Credentials Set (DB + Environment)'
      } else if (hasDb) {
        return 'Credentials Set (Database)'
      } else if (hasEnv) {
        return 'Credentials Set (Environment)'
      } else {
        return 'Configured'
      }
    } else {
      const missing = credentialStatus.missing_required?.length || 0
      return missing > 0
        ? `Missing ${missing} Required Field${missing > 1 ? 's' : ''}`
        : 'No Credentials Set'
    }
  }

  if (credentialSchema.length === 0) {
    return (
      <div className="bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-md p-4">
        <div className="flex items-center">
          <div className="w-5 h-5 text-green-400">✓</div>
          <div className="ml-3">
            <h4 className="text-sm font-medium text-green-800 dark:text-green-200">
              No Credentials Required
            </h4>
            <p className="text-sm text-green-700 dark:text-green-300 mt-1">
              This supplier uses public APIs or web scraping and doesn't require authentication
              credentials.
            </p>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      {/* Compact Status Header */}
      <div className="flex items-center justify-between p-3 bg-gray-50 dark:bg-gray-700 rounded-md">
        <div className="flex items-center space-x-2">
          {getConfiguredStatus() ? (
            <CheckCircle className="w-5 h-5 text-green-500" />
          ) : (
            <XCircle className="w-5 h-5 text-red-500" />
          )}
          <span className="text-sm font-medium">{getStatusText()}</span>
        </div>
        <span className="text-xs text-gray-500">
          {getConfiguredStatus() ? 'Enter new values to update' : 'Required for API access'}
        </span>
      </div>

      {/* Test Result */}
      {testResult && (
        <div
          className={`border rounded-md p-4 ${
            testResult.success
              ? 'bg-green-50 dark:bg-green-900/20 border-green-200 dark:border-green-800'
              : 'bg-red-50 dark:bg-red-900/20 border-red-200 dark:border-red-800'
          }`}
        >
          <div className="flex items-center">
            <div className={`w-5 h-5 ${testResult.success ? 'text-green-400' : 'text-red-400'}`}>
              {testResult.success ? '✓' : '✗'}
            </div>
            <div className="ml-3">
              <h3
                className={`text-sm font-medium ${
                  testResult.success
                    ? 'text-green-800 dark:text-green-200'
                    : 'text-red-800 dark:text-red-200'
                }`}
              >
                Credentials Test {testResult.success ? 'Successful' : 'Failed'}
              </h3>
              {testResult.message && (
                <p
                  className={`mt-1 text-sm ${
                    testResult.success
                      ? 'text-green-700 dark:text-green-300'
                      : 'text-red-700 dark:text-red-300'
                  }`}
                >
                  {testResult.message}
                </p>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Credential Fields - Using FormInput */}
      <div className="space-y-3">
        {credentialSchema.map((field) => {
          const isPassword = field.field_type === 'password'
          const currentValue = form.watch(field.name) || ''
          const isConfigured = credentialStatus?.configured_fields?.includes(field.name) || false
          const shouldShow = showValues[field.name]
          const hasValue = currentValue.length > 0

          return (
            <div key={field.name} className="space-y-1">
              <div className="flex items-center space-x-2 mb-1">
                <span className="block text-sm font-medium text-gray-700 dark:text-gray-300">
                  {field.label}
                  {field.required && <span className="text-red-500 ml-1">*</span>}
                </span>

                {/* Status Indicator */}
                <div className="flex items-center space-x-1">
                  {isConfigured ? (
                    <span className="inline-flex items-center px-1.5 py-0.5 rounded text-xs font-medium bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-200">
                      SET
                    </span>
                  ) : (
                    <span className="inline-flex items-center px-1.5 py-0.5 rounded text-xs font-medium bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-200">
                      REQUIRED
                    </span>
                  )}

                  {/* Help Tooltip */}
                  {(field.description || field.help_text) && (
                    <div className="group relative">
                      <HelpCircle className="w-4 h-4 text-gray-400 hover:text-gray-600 cursor-help" />
                      <div className="absolute bottom-full left-1/2 transform -translate-x-1/2 mb-2 w-64 p-2 bg-black text-white text-xs rounded opacity-0 group-hover:opacity-100 transition-opacity duration-200 pointer-events-none z-10">
                        {field.description && (
                          <div className="font-medium">{field.description}</div>
                        )}
                        {field.help_text && (
                          <div className="mt-1 text-gray-300">{field.help_text}</div>
                        )}
                      </div>
                    </div>
                  )}
                </div>
              </div>

              <div className="relative">
                <FormInput
                  label={field.label}
                  type={shouldShow ? 'text' : 'password'}
                  placeholder={field.placeholder || `Enter ${field.label.toLowerCase()}`}
                  registration={form.register(field.name)}
                  error={form.getFieldError(field.name)}
                  disabled={loading}
                  className="pr-10"
                />

                {(isPassword || hasValue) && (
                  <button
                    type="button"
                    onClick={() => toggleShowValue(field.name)}
                    className="absolute inset-y-0 right-0 pr-3 flex items-center text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 z-10"
                    title="Toggle visibility"
                  >
                    {shouldShow ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                  </button>
                )}
              </div>
            </div>
          )
        })}
      </div>

      {/* Action Buttons */}
      <div className="flex items-center space-x-3 pt-4">
        {onTest && (
          <button
            onClick={handleTest}
            disabled={testing || loading}
            className="inline-flex items-center px-3 py-2 border border-gray-300 text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 disabled:opacity-50"
          >
            <TestTube className={`w-4 h-4 mr-2 ${testing ? 'animate-pulse' : ''}`} />
            {testing ? 'Testing...' : 'Test Connection'}
          </button>
        )}

        {onSave && !['digikey', 'mouser'].includes(supplierName.toLowerCase()) && (
          <button
            onClick={form.onSubmit}
            disabled={!form.isDirty || form.loading || loading}
            className="inline-flex items-center px-3 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 disabled:opacity-50"
          >
            <Save className={`w-4 h-4 mr-2 ${form.loading ? 'animate-pulse' : ''}`} />
            {form.loading ? 'Saving...' : 'Save Credentials'}
          </button>
        )}
      </div>
    </div>
  )
}
