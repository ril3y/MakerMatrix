/**
 * Allocations Summary Component
 *
 * Displays all location allocations for a part, showing where quantities
 * are distributed across multiple locations (reels, cassettes, etc.)
 */

import React, { useState, useEffect } from 'react'
import { Package, MapPin, ArrowRightLeft, Plus, AlertCircle } from 'lucide-react'
import {
  partAllocationService,
  AllocationSummary,
  PartAllocation,
} from '../../services/part-allocation.service'

interface AllocationsSummaryProps {
  partId: string
  onTransferClick?: (allocation: PartAllocation) => void
  onRefresh?: () => void
}

export const AllocationsSummary: React.FC<AllocationsSummaryProps> = ({
  partId,
  onTransferClick,
  onRefresh,
}) => {
  const [allocations, setAllocations] = useState<AllocationSummary | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    loadAllocations()
  }, [partId])

  const loadAllocations = async () => {
    try {
      setLoading(true)
      setError(null)
      const data = await partAllocationService.getPartAllocations(partId)
      setAllocations(data)
      // Don't call onRefresh here - only call it when user explicitly clicks refresh
    } catch (err: any) {
      console.error('Error loading allocations:', err)
      setError(err.response?.data?.detail || err.message || 'Failed to load allocations')
    } finally {
      setLoading(false)
    }
  }

  const handleRefreshClick = async () => {
    await loadAllocations()
    onRefresh?.()
  }

  if (loading) {
    return (
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
        <div className="flex items-center justify-center h-32">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
        <div className="flex items-center space-x-3 text-red-600 dark:text-red-400">
          <AlertCircle className="w-5 h-5" />
          <span>{error}</span>
        </div>
      </div>
    )
  }

  if (!allocations || allocations.allocations.length === 0) {
    return (
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
        <div className="text-center py-8">
          <Package className="w-12 h-12 text-gray-400 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-2">No Allocations</h3>
          <p className="text-gray-500 dark:text-gray-400">
            This part has not been allocated to any locations yet.
          </p>
        </div>
      </div>
    )
  }

  const getLocationIcon = (locationType: string) => {
    switch (locationType.toLowerCase()) {
      case 'cassette':
        return '📦'
      case 'reel':
        return '🎞️'
      case 'bin':
        return '🗄️'
      case 'shelf':
        return '📚'
      default:
        return '📍'
    }
  }

  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg shadow">
      {/* Header */}
      <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-700">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <Package className="w-5 h-5 text-gray-600 dark:text-gray-400" />
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
              Location Allocations
            </h3>
          </div>
          <div className="flex items-center space-x-4">
            <div className="text-right">
              <div className="text-sm text-gray-500 dark:text-gray-400">Total Quantity</div>
              <div className="text-xl font-bold text-gray-900 dark:text-white">
                {allocations.total_quantity.toLocaleString()}
              </div>
            </div>
            <div className="text-right">
              <div className="text-sm text-gray-500 dark:text-gray-400">Locations</div>
              <div className="text-xl font-bold text-gray-900 dark:text-white">
                {allocations.location_count}
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Allocations List */}
      <div className="divide-y divide-gray-200 dark:divide-gray-700">
        {allocations.allocations.map((allocation) => (
          <div
            key={allocation.id}
            className="px-6 py-4 hover:bg-gray-50 dark:hover:bg-gray-700/50 transition-colors"
          >
            <div className="flex items-center justify-between">
              {/* Location Info */}
              <div className="flex items-center space-x-3 flex-1">
                <div className="flex-shrink-0">
                  <span className="text-2xl">
                    {allocation.location?.emoji ||
                      getLocationIcon(allocation.location?.location_type || '')}
                  </span>
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center space-x-2">
                    <p className="text-sm font-medium text-gray-900 dark:text-white truncate">
                      {allocation.location?.name || 'Unknown Location'}
                    </p>
                    {allocation.is_primary_storage && (
                      <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-blue-100 dark:bg-blue-900/30 text-blue-800 dark:text-blue-200">
                        Primary
                      </span>
                    )}
                  </div>
                  {allocation.location_path && (
                    <p className="text-sm text-gray-500 dark:text-gray-400 truncate">
                      <MapPin className="w-3 h-3 inline mr-1" />
                      {allocation.location_path}
                    </p>
                  )}
                  {allocation.notes && (
                    <p className="text-xs text-gray-500 dark:text-gray-400 mt-1 italic">
                      {allocation.notes}
                    </p>
                  )}
                </div>
              </div>

              {/* Quantity & Actions */}
              <div className="flex items-center space-x-4 ml-4">
                <div className="text-right">
                  <div className="text-lg font-semibold text-gray-900 dark:text-white">
                    {allocation.quantity_at_location.toLocaleString()}
                  </div>
                  <div className="text-xs text-gray-500 dark:text-gray-400">
                    {((allocation.quantity_at_location / allocations.total_quantity) * 100).toFixed(
                      1
                    )}
                    %
                  </div>
                </div>
                {onTransferClick && (
                  <button
                    onClick={() => onTransferClick(allocation)}
                    className="p-2 text-gray-400 hover:text-blue-600 dark:hover:text-blue-400 hover:bg-gray-100 dark:hover:bg-gray-600 rounded-md transition-colors"
                    title="Transfer from this location"
                  >
                    <ArrowRightLeft className="w-4 h-4" />
                  </button>
                )}
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Footer Actions */}
      <div className="px-6 py-4 bg-gray-50 dark:bg-gray-700/50 border-t border-gray-200 dark:border-gray-700">
        <button
          onClick={handleRefreshClick}
          className="text-sm text-blue-600 dark:text-blue-400 hover:text-blue-500 dark:hover:text-blue-300 font-medium"
        >
          Refresh Allocations
        </button>
      </div>
    </div>
  )
}
