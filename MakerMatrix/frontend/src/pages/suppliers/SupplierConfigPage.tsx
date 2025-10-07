/**
 * Supplier Configuration Management Page
 *
 * Provides a comprehensive interface for managing supplier API configurations,
 * credentials, and enrichment capabilities with security features.
 */

import React, { useState, useEffect, useRef } from 'react'
import {
  Plus,
  Settings,
  Upload,
  AlertTriangle,
  CheckCircle,
  XCircle,
  Activity,
  Clock,
} from 'lucide-react'
import type { SupplierConfig } from '../../services/supplier.service'
import { supplierService } from '../../services/supplier.service'
import { dynamicSupplierService } from '../../services/dynamic-supplier.service'
import type { SupplierRateLimitData } from '../../services/rate-limit.service'
import { rateLimitService } from '../../services/rate-limit.service'
import { DynamicAddSupplierModal } from './DynamicAddSupplierModal'
import { EditSupplierModal } from './EditSupplierModal'
import { EditSimpleSupplierModal } from './EditSimpleSupplierModal'
import { ImportExportModal } from './ImportExportModal'
import { AddSimpleSupplierModal } from './AddSimpleSupplierModal'

export const SupplierConfigPage: React.FC = () => {
  const [suppliers, setSuppliers] = useState<SupplierConfig[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // Modal states
  const [showAddModal, setShowAddModal] = useState(false)
  const [showAddSimpleModal, setShowAddSimpleModal] = useState(false)
  const [editingSupplier, setEditingSupplier] = useState<SupplierConfig | null>(null)
  const [showImportExport, setShowImportExport] = useState(false)

  // Cache for credential requirements to avoid repeated API calls
  const [credentialRequirements, setCredentialRequirements] = useState<Record<string, boolean>>({})

  // Cache for actual credential status
  const [credentialStatuses, setCredentialStatuses] = useState<Record<string, any>>({})

  // Loading state for each supplier's credential status
  const [loadingCredentialStatus, setLoadingCredentialStatus] = useState<Record<string, boolean>>(
    {}
  )

  // Rate limit data
  const [rateLimitData, setRateLimitData] = useState<Record<string, SupplierRateLimitData>>({})
  const [loadingRateLimits, setLoadingRateLimits] = useState(false)

  // Ref to prevent duplicate initial loads (React StrictMode in dev runs effects twice)
  const initialLoadDone = useRef(false)

  useEffect(() => {
    if (!initialLoadDone.current) {
      initialLoadDone.current = true
      loadSuppliers()
      loadRateLimitData()
    }
  }, [])

  const loadSuppliers = async () => {
    try {
      setLoading(true)
      setError(null)
      const data = await supplierService.getSuppliers()
      setSuppliers(data || [])

      // Separate simple and API suppliers
      const apiSuppliers = (data || []).filter((s) => s.supplier_type !== 'simple')
      const simpleSuppliers = (data || []).filter((s) => s.supplier_type === 'simple')

      // Set initial loading states
      const loadingStates: Record<string, boolean> = {}
      const requirements: Record<string, boolean> = {}
      const statuses: Record<string, any> = {}

      // Handle simple suppliers (no API calls needed)
      for (const supplier of simpleSuppliers) {
        loadingStates[supplier.supplier_name] = false
        requirements[supplier.supplier_name] = false
        statuses[supplier.supplier_name] = {
          is_configured: true,
          configured_fields: [],
          supplier_type: 'simple',
        }
      }

      // Set API suppliers to loading
      for (const supplier of apiSuppliers) {
        loadingStates[supplier.supplier_name] = true
      }

      // Update states once for simple suppliers
      setLoadingCredentialStatus(loadingStates)
      setCredentialRequirements(requirements)
      setCredentialStatuses(statuses)

      // Batch load credential info for all API suppliers in parallel
      const credentialPromises = apiSuppliers.map(async (supplier) => {
        try {
          // Get credential schema and status in parallel for each supplier
          const [credentialSchema, credentialStatus] = await Promise.all([
            dynamicSupplierService.getCredentialSchema(supplier.supplier_name.toLowerCase()),
            supplierService.getCredentialStatus(supplier.supplier_name).catch(() => ({
              is_configured: false,
              configured_fields: [],
            })),
          ])

          const requiresCredentials = Array.isArray(credentialSchema) && credentialSchema.length > 0

          return {
            supplierName: supplier.supplier_name,
            requiresCredentials,
            credentialStatus,
          }
        } catch (err) {
          console.warn(`Failed to load credentials for ${supplier.supplier_name}:`, err)
          return {
            supplierName: supplier.supplier_name,
            requiresCredentials: true,
            credentialStatus: { is_configured: false, configured_fields: [] },
          }
        }
      })

      // Wait for all credential checks to complete
      const results = await Promise.all(credentialPromises)

      // Batch update all states at once
      const newRequirements: Record<string, boolean> = { ...requirements }
      const newStatuses: Record<string, any> = { ...statuses }
      const newLoadingStates: Record<string, boolean> = { ...loadingStates }

      results.forEach(({ supplierName, requiresCredentials, credentialStatus }) => {
        newRequirements[supplierName] = requiresCredentials
        newStatuses[supplierName] = credentialStatus
        newLoadingStates[supplierName] = false
      })

      setCredentialRequirements(newRequirements)
      setCredentialStatuses(newStatuses)
      setLoadingCredentialStatus(newLoadingStates)
    } catch (err) {
      const error = err as { response?: { data?: { error?: string; message?: string; detail?: string }; status?: number }; message?: string }
      console.error('Error loading suppliers:', err)
      const errorMessage =
        err.response?.data?.detail || error.message || 'Failed to load supplier configurations'
      setError(errorMessage)
      setSuppliers([]) // Ensure suppliers is always an array
    } finally {
      setLoading(false)
    }
  }

  const loadRateLimitData = async () => {
    try {
      setLoadingRateLimits(true)
      const rateLimits = await rateLimitService.getAllSupplierUsage()

      // Convert array to object for easier lookup
      const rateLimitMap: Record<string, SupplierRateLimitData> = {}
      rateLimits.forEach((data) => {
        rateLimitMap[data.supplier_name.toLowerCase()] = data
      })

      setRateLimitData(rateLimitMap)
    } catch (err) {
      const error = err as { response?: { data?: { error?: string; message?: string; detail?: string }; status?: number }; message?: string }
      console.error('Error loading rate limit data:', err)
      // Don't show error for rate limits as it's supplementary data
    } finally {
      setLoadingRateLimits(false)
    }
  }

  const handleToggleEnabled = async (supplier: SupplierConfig) => {
    try {
      await supplierService.updateSupplier(supplier.supplier_name, {
        enabled: !supplier.enabled,
      })
      await loadSuppliers()
    } catch (err) {
      const error = err as { response?: { data?: { error?: string; message?: string; detail?: string }; status?: number }; message?: string }
      setError(error.response?.data?.detail || 'Failed to update supplier status')
    }
  }

  const handleDeleteSupplier = async (supplierName: string) => {
    if (
      !confirm(
        `Are you sure you want to delete the supplier configuration for "${supplierName}"? This action cannot be undone.`
      )
    ) {
      return
    }

    try {
      await supplierService.deleteSupplier(supplierName)
      await loadSuppliers()
    } catch (err) {
      const error = err as { response?: { data?: { error?: string; message?: string; detail?: string }; status?: number }; message?: string }
      setError(error.response?.data?.detail || 'Failed to delete supplier configuration')
    }
  }

  // Separate suppliers into API and simple types
  const apiSuppliers = (suppliers || []).filter((s) => s.supplier_type !== 'simple')
  const simpleSuppliers = (suppliers || []).filter((s) => s.supplier_type === 'simple')
  const filteredSuppliers = suppliers || []

  const getStatusIcon = (supplier: SupplierConfig) => {
    // Check if we're still loading credential status for this supplier
    if (loadingCredentialStatus[supplier.supplier_name]) {
      return (
        <div className="animate-spin rounded-full h-5 w-5 border-2 border-gray-300 border-t-blue-600"></div>
      )
    }

    if (!supplier.enabled) {
      return <XCircle className="w-5 h-5 text-gray-400" />
    }

    // Check if this supplier requires credentials
    const requiresCredentials = credentialRequirements[supplier.supplier_name] ?? true

    // If no credentials are required (like LCSC), show green
    if (!requiresCredentials) {
      return <CheckCircle className="w-5 h-5 text-green-500" /> // Public API, no credentials needed
    }

    // Check actual credential status for suppliers that need credentials
    const credentialStatus = credentialStatuses[supplier.supplier_name]
    if (credentialStatus?.is_configured) {
      return <CheckCircle className="w-5 h-5 text-green-500" /> // Credentials configured and working
    } else {
      return <AlertTriangle className="w-5 h-5 text-yellow-500" /> // Credentials missing or not working
    }
  }

  const getStatusText = (supplier: SupplierConfig) => {
    // Check if we're still loading credential status for this supplier
    if (loadingCredentialStatus[supplier.supplier_name]) {
      return 'Checking...'
    }

    if (!supplier.enabled) return 'Disabled'

    // Check if this supplier requires credentials
    const requiresCredentials = credentialRequirements[supplier.supplier_name] ?? true

    // If no credentials are required (like LCSC), show as configured
    if (!requiresCredentials) {
      return 'Configured' // Public API, no credentials needed
    }

    // Check actual credential status for suppliers that need credentials
    const credentialStatus = credentialStatuses[supplier.supplier_name]
    if (credentialStatus?.is_configured) {
      return 'Configured' // Credentials configured and working
    } else {
      return 'Not Configured' // Credentials missing or not working
    }
  }

  // Helper component to render supplier card
  const SupplierCard = ({ supplier }: { supplier: SupplierConfig }) => {
    return (
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow hover:shadow-md transition-shadow border border-gray-200 dark:border-gray-700">
        <div className="p-6">
          {/* Header */}
          <div className="flex items-start justify-between mb-4">
            <div className="flex items-center space-x-3">
              {supplier.image_url ? (
                <img
                  src={supplier.image_url}
                  alt={supplier.display_name}
                  className="w-10 h-10 rounded object-contain flex-shrink-0"
                  onError={(e) => {
                    // Fallback to status icon if image fails to load
                    e.currentTarget.style.display = 'none'
                  }}
                />
              ) : (
                getStatusIcon(supplier)
              )}
              <div>
                <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
                  {supplier.display_name}
                </h3>
                <p className="text-sm text-gray-500 dark:text-gray-400">{supplier.supplier_name}</p>
              </div>
            </div>
            <div className="flex items-center space-x-1">
              <button
                onClick={() => setEditingSupplier(supplier)}
                className="p-2 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
                title="Edit Configuration"
              >
                <Settings className="w-4 h-4" />
              </button>
            </div>
          </div>

          {/* Description */}
          {supplier.description && (
            <p className="text-sm text-gray-600 dark:text-gray-300 mb-4">{supplier.description}</p>
          )}

          {/* Status and Info */}
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-sm text-gray-500 dark:text-gray-400">Status:</span>
              {loadingCredentialStatus[supplier.supplier_name] ? (
                <span className="text-sm font-medium text-blue-600 dark:text-blue-400 flex items-center">
                  <div className="animate-spin rounded-full h-3 w-3 border-2 border-gray-300 border-t-blue-600 mr-2"></div>
                  {getStatusText(supplier)}
                </span>
              ) : (
                <span
                  className={`text-sm font-medium ${
                    supplier.enabled
                      ? 'text-green-600 dark:text-green-400'
                      : 'text-red-600 dark:text-red-400'
                  }`}
                >
                  {getStatusText(supplier)}
                </span>
              )}
            </div>

            <div className="flex items-center justify-between">
              <span className="text-sm text-gray-500 dark:text-gray-400">Type:</span>
              {supplier.supplier_type === 'simple' ? (
                <span className="inline-flex items-center px-2 py-1 rounded-md text-xs font-medium bg-gray-100 dark:bg-gray-800 text-gray-700 dark:text-gray-300">
                  Simple Supplier
                </span>
              ) : (
                <span className="text-sm text-gray-900 dark:text-white uppercase">
                  {supplier.api_type}
                </span>
              )}
            </div>

            {supplier.supplier_type !== 'simple' && (
              <div className="flex items-center justify-between">
                <span className="text-sm text-gray-500 dark:text-gray-400">Capabilities:</span>
                <span className="text-sm text-gray-900 dark:text-white">
                  {supplier.capabilities.length}
                </span>
              </div>
            )}

            {/* Rate Limit Information */}
            {supplier.supplier_type !== 'simple' &&
              rateLimitData[supplier.supplier_name.toLowerCase()] && (
                <>
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-gray-500 dark:text-gray-400">
                      <Activity className="w-3 h-3 inline mr-1" />
                      API Usage:
                    </span>
                    <span className="text-sm">
                      {rateLimitData[supplier.supplier_name.toLowerCase()].stats_24h.total_requests}{' '}
                      calls (24h)
                    </span>
                  </div>

                  <div className="flex items-center justify-between">
                    <span className="text-sm text-gray-500 dark:text-gray-400">
                      <Clock className="w-3 h-3 inline mr-1" />
                      Rate Limit:
                    </span>
                    <div className="text-right">
                      {Object.entries(
                        rateLimitData[supplier.supplier_name.toLowerCase()].usage_percentage
                      ).map(([period, percentage]) => (
                        <div key={period} className="text-xs">
                          <span className={rateLimitService.getUsageColor(percentage)}>
                            {rateLimitService.formatUsagePercentage(percentage)}
                          </span>
                          <span className="text-gray-400 ml-1">{period.replace('per_', '')}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                </>
              )}

            {loadingRateLimits && (
              <div className="flex items-center justify-between">
                <span className="text-sm text-gray-500 dark:text-gray-400">Rate Limits:</span>
                <span className="text-xs text-gray-400">Loading...</span>
              </div>
            )}
          </div>

          {/* Capabilities */}
          {supplier.supplier_type !== 'simple' && (
            <div className="mt-4">
              <div className="flex flex-wrap gap-1">
                {supplier.capabilities.map((capability) => (
                  <span
                    key={capability}
                    className="inline-flex items-center px-2 py-1 rounded-md text-xs font-medium bg-blue-100 dark:bg-blue-900/30 text-blue-800 dark:text-blue-200"
                  >
                    {(() => {
                      const nameMap: Record<string, string> = {
                        get_part_details: 'Part Enrichment',
                        fetch_datasheet: 'Datasheet Retrieval',
                        fetch_image: 'Image Fetching',
                        fetch_pricing: 'Pricing Data',
                        fetch_stock: 'Stock Levels',
                        import_orders: 'Order Import',
                        parametric_search: 'Advanced Search',
                      }
                      return (
                        nameMap[capability] || capability.replace('fetch_', '').replace('_', ' ')
                      )
                    })()}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Actions */}
          <div className="mt-6 flex items-center justify-end">
            <div className="flex items-center space-x-3">
              {/* Only show Enable/Disable for API suppliers, not simple suppliers */}
              {supplier.supplier_type !== 'simple' && (
                <button
                  onClick={() => handleToggleEnabled(supplier)}
                  className={`text-sm font-medium ${
                    supplier.enabled
                      ? 'text-red-600 dark:text-red-400 hover:text-red-500 dark:hover:text-red-300'
                      : 'text-green-600 dark:text-green-400 hover:text-green-500 dark:hover:text-green-300'
                  }`}
                >
                  {supplier.enabled ? 'Disable' : 'Enable'}
                </button>
              )}
              <button
                onClick={() => handleDeleteSupplier(supplier.supplier_name)}
                className="text-sm text-red-600 dark:text-red-400 hover:text-red-500 dark:hover:text-red-300"
              >
                Delete
              </button>
            </div>
          </div>
        </div>
      </div>
    )
  }

  if (loading && suppliers.length === 0) {
    return (
      <div className="min-h-screen bg-gray-50 dark:bg-gray-900 p-6">
        <div className="max-w-screen-2xl mx-auto">
          <div className="flex items-center justify-center h-64">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900 p-6">
      <div className="max-w-screen-2xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-3xl font-bold text-gray-900 dark:text-white">
                Supplier Configuration
              </h1>
              <p className="mt-2 text-gray-600 dark:text-gray-300">
                Manage supplier API configurations, credentials, and enrichment capabilities
              </p>
            </div>
            <div className="flex items-center space-x-3">
              <button
                onClick={() => setShowImportExport(true)}
                className="inline-flex items-center px-4 py-2 border border-gray-300 dark:border-gray-600 text-sm font-medium rounded-md text-gray-700 dark:text-gray-200 bg-white dark:bg-gray-700 hover:bg-gray-50 dark:hover:bg-gray-600"
              >
                <Upload className="w-4 h-4 mr-2" />
                Import/Export
              </button>
              <button
                onClick={() => setShowAddSimpleModal(true)}
                className="inline-flex items-center px-4 py-2 border border-gray-300 dark:border-gray-600 text-sm font-medium rounded-md text-gray-700 dark:text-gray-200 bg-white dark:bg-gray-700 hover:bg-gray-50 dark:hover:bg-gray-600"
                title="Add a simple supplier without API integration (e.g., NewEgg, Amazon)"
              >
                <Plus className="w-4 h-4 mr-2" />
                Add Simple Supplier
              </button>
              <button
                onClick={() => setShowAddModal(true)}
                className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700"
                title="Add a supplier with API integration (e.g., DigiKey, Mouser)"
              >
                <Plus className="w-4 h-4 mr-2" />
                Add API Supplier
              </button>
            </div>
          </div>
        </div>

        {/* Error Alert */}
        {error && (
          <div className="mb-6 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-md p-4">
            <div className="flex">
              <AlertTriangle className="w-5 h-5 text-red-400" />
              <div className="ml-3">
                <h3 className="text-sm font-medium text-red-800 dark:text-red-200">Error</h3>
                <p className="mt-1 text-sm text-red-700 dark:text-red-300">{error}</p>
                <button
                  onClick={() => setError(null)}
                  className="mt-2 text-sm text-red-600 dark:text-red-400 hover:text-red-500 dark:hover:text-red-300"
                >
                  Dismiss
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Header Info */}
        <div className="mb-6 bg-white dark:bg-gray-800 rounded-lg shadow p-6">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-6">
              <span className="text-sm text-gray-500 dark:text-gray-400">
                <span className="font-semibold text-gray-900 dark:text-white">
                  {apiSuppliers.length}
                </span>{' '}
                API Supplier{apiSuppliers.length !== 1 ? 's' : ''}
              </span>
              <span className="text-sm text-gray-500 dark:text-gray-400">
                <span className="font-semibold text-gray-900 dark:text-white">
                  {simpleSuppliers.length}
                </span>{' '}
                Simple Supplier{simpleSuppliers.length !== 1 ? 's' : ''}
              </span>
            </div>
            <span className="text-sm text-gray-500 dark:text-gray-400">
              Total: {filteredSuppliers.length}
            </span>
          </div>
        </div>

        {/* Suppliers Display */}
        {filteredSuppliers.length === 0 ? (
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-12 text-center">
            <Settings className="w-12 h-12 text-gray-400 mx-auto mb-4" />
            <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-2">
              No suppliers found
            </h3>
            <p className="text-gray-500 dark:text-gray-400 mb-6">
              Get started by adding your first supplier configuration or initializing defaults.
            </p>
            {(suppliers || []).length === 0 && (
              <div className="flex justify-center space-x-4">
                <button
                  onClick={() => setShowAddModal(true)}
                  className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700"
                >
                  <Plus className="w-4 h-4 mr-2" />
                  Add Supplier
                </button>
              </div>
            )}
          </div>
        ) : (
          <div className="space-y-8">
            {/* API Suppliers Section */}
            {apiSuppliers.length > 0 && (
              <div>
                <h2 className="text-xl font-semibold text-gray-900 dark:text-white mb-4 flex items-center">
                  <Settings className="w-5 h-5 mr-2" />
                  API Suppliers
                  <span className="ml-2 text-sm font-normal text-gray-500 dark:text-gray-400">
                    ({apiSuppliers.length})
                  </span>
                </h2>
                <div className="grid grid-cols-1 lg:grid-cols-2 xl:grid-cols-3 gap-6">
                  {apiSuppliers.map((supplier) => (
                    <SupplierCard key={supplier.id} supplier={supplier} />
                  ))}
                </div>
              </div>
            )}

            {/* Simple Suppliers Section */}
            {simpleSuppliers.length > 0 && (
              <div>
                <h2 className="text-xl font-semibold text-gray-900 dark:text-white mb-4 flex items-center">
                  <Plus className="w-5 h-5 mr-2" />
                  Simple Suppliers
                  <span className="ml-2 text-sm font-normal text-gray-500 dark:text-gray-400">
                    ({simpleSuppliers.length})
                  </span>
                </h2>
                <div className="grid grid-cols-1 lg:grid-cols-2 xl:grid-cols-3 gap-6">
                  {simpleSuppliers.map((supplier) => (
                    <SupplierCard key={supplier.id} supplier={supplier} />
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Modals */}
      {showAddModal && (
        <DynamicAddSupplierModal
          onClose={() => setShowAddModal(false)}
          onSuccess={() => {
            setShowAddModal(false)
            loadSuppliers()
          }}
          existingSuppliers={suppliers.map((s) => s.supplier_name)}
        />
      )}

      {showAddSimpleModal && (
        <AddSimpleSupplierModal
          onClose={() => setShowAddSimpleModal(false)}
          onSuccess={() => {
            setShowAddSimpleModal(false)
            loadSuppliers()
          }}
        />
      )}

      {editingSupplier && editingSupplier.supplier_type === 'simple' && (
        <EditSimpleSupplierModal
          supplier={editingSupplier}
          onClose={() => setEditingSupplier(null)}
          onSuccess={() => {
            setEditingSupplier(null)
            loadSuppliers()
          }}
          onDelete={handleDeleteSupplier}
        />
      )}

      {editingSupplier && editingSupplier.supplier_type !== 'simple' && (
        <EditSupplierModal
          supplier={editingSupplier}
          onClose={() => setEditingSupplier(null)}
          onSuccess={() => {
            setEditingSupplier(null)
            loadSuppliers()
          }}
          onDelete={handleDeleteSupplier}
        />
      )}

      {showImportExport && (
        <ImportExportModal
          onClose={() => setShowImportExport(false)}
          onSuccess={() => {
            setShowImportExport(false)
            loadSuppliers()
          }}
        />
      )}
    </div>
  )
}

export default SupplierConfigPage
