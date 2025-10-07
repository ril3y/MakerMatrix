/**
 * Location Details Modal
 *
 * Displays detailed information about a location including:
 * - Location information (name, type, hierarchy, image)
 * - All parts allocated to this location
 * - Part allocation management (edit quantities, clear allocations)
 * - Label printing for parts at this location
 */

import { useState, useEffect } from 'react'
import {
  MapPin,
  Package,
  Edit,
  Printer,
  AlertCircle,
  ChevronRight,
  Undo2,
  FolderTree,
  Plus,
} from 'lucide-react'
import Modal from '@/components/ui/Modal'
import type { Location, LocationDetails } from '@/types/locations'
import { locationsService } from '@/services/locations.service'
import { partsService } from '@/services/parts.service'
import { partAllocationService } from '@/services/part-allocation.service'
import PrinterModal from '@/components/printer/PrinterModal'
import AddLocationModal from '@/components/locations/AddLocationModal'
import EditLocationModal from '@/components/locations/EditLocationModal'
import toast from 'react-hot-toast'

interface LocationDetailsModalProps {
  isOpen: boolean
  onClose: () => void
  location: Location
  onRefresh?: () => void
  onOpenLocation?: (location: Location) => void
}

interface PartAtLocation {
  id: string
  part_name: string
  part_number?: string
  description?: string
  quantity_at_location: number
  total_quantity?: number
  allocation_id?: string
  is_primary_storage?: boolean
  category?: string
  manufacturer?: string
  image_url?: string
}

const LocationDetailsModal: React.FC<LocationDetailsModalProps> = ({
  isOpen,
  onClose,
  location,
  onRefresh,
  onOpenLocation,
}) => {
  const [loading, setLoading] = useState(true)
  const [locationDetails, setLocationDetails] = useState<LocationDetails | null>(null)
  const [partsAtLocation, setPartsAtLocation] = useState<PartAtLocation[]>([])
  const [locationPath, setLocationPath] = useState<string>('')

  // Print modal state
  const [showPrintModal, setShowPrintModal] = useState(false)
  const [selectedPartForPrint, setSelectedPartForPrint] = useState<PartAtLocation | null>(null)

  // Confirmation modal state
  const [showConfirmModal, setShowConfirmModal] = useState(false)
  const [partToReturn, setPartToReturn] = useState<PartAtLocation | null>(null)

  // Add child location modal state
  const [showAddChildModal, setShowAddChildModal] = useState(false)

  // Edit location modal state
  const [showEditModal, setShowEditModal] = useState(false)

  useEffect(() => {
    if (isOpen) {
      loadLocationData()
    }
  }, [isOpen, location.id])

  const loadLocationData = async () => {
    try {
      setLoading(true)

      // Load location details
      const details = await locationsService.getLocationDetails(location.id)
      setLocationDetails(details)

      // Build location path
      const path = await buildLocationPath(location.id)
      setLocationPath(path)

      // Search for parts at this location
      const searchResponse = await partsService.searchParts({
        location_id: location.id,
        page: 1,
        page_size: 1000, // Get all parts at this location
      })

      // The response structure is { data: { items: [...], total, page, page_size } }
      const partsData = searchResponse?.data?.items || searchResponse?.items || []

      // Fetch allocation data for each part to get accurate quantity at this location
      const partsWithAllocations = await Promise.all(
        partsData.map(async (part: any) => {
          try {
            const allocations = await partAllocationService.getPartAllocations(part.id)
            const locationAllocation = allocations.allocations.find(
              (a) => a.location_id === location.id
            )

            return {
              id: part.id,
              part_name: part.name || part.part_name,
              part_number: part.part_number,
              description: part.description,
              quantity_at_location: locationAllocation?.quantity_at_location || 0,
              total_quantity: allocations.total_quantity,
              allocation_id: locationAllocation?.id,
              is_primary_storage: locationAllocation?.is_primary_storage,
              category: part.categories?.[0]?.name,
              manufacturer: part.manufacturer,
              image_url: part.image_url,
            }
          } catch (error) {
            console.error(`Failed to get allocations for part ${part.id}:`, error)
            // Fallback to part.quantity if allocation fetch fails
            return {
              id: part.id,
              part_name: part.name || part.part_name,
              part_number: part.part_number,
              description: part.description,
              quantity_at_location: part.quantity || 0,
              total_quantity: part.total_quantity,
              category: part.categories?.[0]?.name,
              manufacturer: part.manufacturer,
              image_url: part.image_url,
            }
          }
        })
      )

      setPartsAtLocation(partsWithAllocations)
    } catch (error) {
      const err = error as { response?: { data?: { message?: string; detail?: string }; status?: number }; message?: string }
      console.error('Failed to load location data:', error)
      toast.error('Failed to load location details')
    } finally {
      setLoading(false)
    }
  }

  const buildLocationPath = async (locationId: string): Promise<string> => {
    try {
      const pathData = await locationsService.getLocationPath(locationId)
      const pathParts: string[] = []

      let current = pathData
      while (current) {
        pathParts.unshift(current.name)
        current = current.parent as any
      }

      return pathParts.join(' > ')
    } catch {
      return location.name
    }
  }

  const handleReturnToOriginal = (part: PartAtLocation) => {
    setPartToReturn(part)
    setShowConfirmModal(true)
  }

  const confirmReturnToOriginal = async () => {
    if (!partToReturn) return

    try {
      // Get the part's allocations to find the primary storage location
      const allocations = await partAllocationService.getPartAllocations(partToReturn.id)

      // Find the primary storage location
      const primaryAllocation = allocations.allocations.find((a) => a.is_primary_storage)

      if (!primaryAllocation) {
        toast.error('No primary storage location found for this part')
        return
      }

      // If the current location is already the primary location, no need to transfer
      if (primaryAllocation.location_id === location.id) {
        toast.error('This part is already at its primary storage location')
        setShowConfirmModal(false)
        setPartToReturn(null)
        return
      }

      // Transfer all quantity from current location back to primary location
      await partAllocationService.transferQuantity(partToReturn.id, {
        from_location_id: location.id,
        to_location_id: primaryAllocation.location_id,
        quantity: partToReturn.quantity_at_location,
        notes: 'Returned to primary storage location',
      })

      toast.success(
        `${partToReturn.part_name} returned to ${primaryAllocation.location?.name || 'primary storage'}`
      )
      setShowConfirmModal(false)
      setPartToReturn(null)
      loadLocationData()
      if (onRefresh) onRefresh()
    } catch (error) {
      const err = error as { response?: { data?: { message?: string; detail?: string }; status?: number }; message?: string }
      console.error('Failed to return part:', error)
      toast.error(error.message || 'Failed to return part to original location')
    }
  }

  const handlePrintLabel = (part: PartAtLocation) => {
    setSelectedPartForPrint(part)
    setShowPrintModal(true)
  }

  const handleClosePrintModal = () => {
    setShowPrintModal(false)
    setSelectedPartForPrint(null)
  }

  return (
    <>
      <Modal isOpen={isOpen} onClose={onClose} title="" size="xl">
        <div className="space-y-6">
          {/* Header */}
          <div className="flex items-start justify-between border-b border-theme-primary pb-4">
            <div className="flex items-start gap-4 flex-1">
              {/* Emoji/Icon */}
              <div className="flex-shrink-0">
                {location.emoji ? (
                  <div className="text-5xl">{location.emoji}</div>
                ) : (
                  <div className="w-16 h-16 bg-primary/10 rounded-lg flex items-center justify-center">
                    <MapPin className="w-8 h-8 text-primary" />
                  </div>
                )}
              </div>

              {/* Location Info */}
              <div className="flex-1">
                <div className="flex items-center gap-2">
                  <h2 className="text-2xl font-bold text-theme-primary">{location.name}</h2>
                  <button
                    onClick={() => setShowEditModal(true)}
                    className="p-2 hover:bg-theme-secondary rounded-lg transition-colors"
                    title="Edit location"
                  >
                    <Edit className="w-5 h-5 text-theme-secondary hover:text-primary" />
                  </button>
                </div>
                <div className="flex items-center gap-2 mt-1 text-sm text-theme-secondary">
                  <span className="px-2 py-1 bg-theme-secondary rounded text-xs font-medium">
                    {location.location_type}
                  </span>
                  {locationPath && (
                    <div className="flex items-center gap-1 text-theme-muted">
                      <ChevronRight className="w-3 h-3" />
                      <span>{locationPath}</span>
                    </div>
                  )}
                </div>
                {location.description && (
                  <p className="mt-2 text-theme-secondary">{location.description}</p>
                )}
              </div>
            </div>
          </div>

          {/* Image if available */}
          {location.image_url && (
            <div className="rounded-lg overflow-hidden border border-theme-primary">
              <img
                src={location.image_url}
                alt={location.name}
                className="w-full h-48 object-cover"
              />
            </div>
          )}

          {/* Stats */}
          <div className="grid grid-cols-3 gap-4">
            <div className="p-4 bg-theme-secondary rounded-lg border border-theme-primary">
              <div className="text-sm text-theme-muted">Parts</div>
              <div className="text-2xl font-bold text-theme-primary">{partsAtLocation.length}</div>
            </div>
            <div className="p-4 bg-theme-secondary rounded-lg border border-theme-primary">
              <div className="text-sm text-theme-muted">Total Quantity</div>
              <div className="text-2xl font-bold text-theme-primary">
                {partsAtLocation
                  .reduce((sum, p) => sum + p.quantity_at_location, 0)
                  .toLocaleString()}
              </div>
            </div>
            <div className="p-4 bg-theme-secondary rounded-lg border border-theme-primary">
              <div className="text-sm text-theme-muted">Child Locations</div>
              <div className="text-2xl font-bold text-theme-primary">
                {locationDetails?.children.length || 0}
              </div>
            </div>
          </div>

          {/* Child Locations or Parts */}
          <div>
            {locationDetails && locationDetails.children.length > 0 ? (
              // Show child locations if this is a parent location
              <>
                <div className="flex items-center justify-between mb-3">
                  <h3 className="text-lg font-semibold text-theme-primary flex items-center gap-2">
                    <FolderTree className="w-5 h-5" />
                    Child Locations
                  </h3>
                  <button
                    onClick={() => setShowAddChildModal(true)}
                    className="btn btn-sm btn-secondary flex items-center gap-2"
                  >
                    <Plus className="w-4 h-4" />
                    Add Child Location
                  </button>
                </div>
                {loading ? (
                  <div className="text-center py-8">
                    <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary mx-auto"></div>
                    <p className="text-theme-secondary mt-2">Loading locations...</p>
                  </div>
                ) : (
                  <div className="space-y-2 max-h-96 overflow-y-auto">
                    {locationDetails.children.map((childLocation: any) => (
                      <div
                        key={childLocation.id}
                        className="p-4 bg-theme-primary border border-theme-primary rounded-lg hover:border-primary transition-colors cursor-pointer"
                        onClick={() => {
                          // Open this child location's details
                          if (onOpenLocation) {
                            onOpenLocation(childLocation)
                          }
                        }}
                      >
                        <div className="flex items-start gap-3">
                          {/* Location Icon/Emoji */}
                          <div className="flex-shrink-0">
                            {childLocation.emoji ? (
                              <div className="text-3xl">{childLocation.emoji}</div>
                            ) : (
                              <div className="w-12 h-12 bg-primary/10 rounded-lg flex items-center justify-center">
                                <MapPin className="w-6 h-6 text-primary" />
                              </div>
                            )}
                          </div>

                          {/* Location Info */}
                          <div className="flex-1">
                            <h4 className="font-medium text-theme-primary">{childLocation.name}</h4>
                            <p className="text-sm text-theme-secondary">
                              Type: {childLocation.location_type || 'General'}
                            </p>
                            {childLocation.description && (
                              <p className="text-xs text-theme-muted mt-1">
                                {childLocation.description}
                              </p>
                            )}
                          </div>

                          {/* Chevron */}
                          <ChevronRight className="w-5 h-5 text-theme-muted flex-shrink-0" />
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </>
            ) : (
              // Show parts if this is a leaf location (no children yet)
              <>
                <div className="flex items-center justify-between mb-3">
                  <h3 className="text-lg font-semibold text-theme-primary flex items-center gap-2">
                    <Package className="w-5 h-5" />
                    Parts at this Location
                  </h3>
                  <button
                    onClick={() => setShowAddChildModal(true)}
                    className="btn btn-sm btn-secondary flex items-center gap-2"
                  >
                    <Plus className="w-4 h-4" />
                    Add Child Location
                  </button>
                </div>

                {loading ? (
                  <div className="text-center py-8">
                    <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary mx-auto"></div>
                    <p className="text-theme-secondary mt-2">Loading parts...</p>
                  </div>
                ) : partsAtLocation.length === 0 ? (
                  <div className="text-center py-8 bg-theme-secondary rounded-lg border border-theme-primary">
                    <Package className="w-12 h-12 text-theme-muted mx-auto mb-2" />
                    <p className="text-theme-muted">No parts at this location</p>
                  </div>
                ) : (
                  <div className="space-y-2 max-h-96 overflow-y-auto">
                    {partsAtLocation.map((part) => (
                      <div
                        key={part.id}
                        className="p-4 bg-theme-primary border border-theme-primary rounded-lg hover:border-primary transition-colors"
                      >
                        <div className="flex items-start justify-between">
                          {/* Part Info */}
                          <div className="flex items-start gap-3 flex-1">
                            {part.image_url && (
                              <img
                                src={part.image_url}
                                alt={part.part_name}
                                className="w-12 h-12 object-cover rounded border border-theme-primary"
                              />
                            )}
                            <div className="flex-1">
                              <h4 className="font-medium text-theme-primary">{part.part_name}</h4>
                              {part.part_number && (
                                <p className="text-sm text-theme-secondary">
                                  PN: {part.part_number}
                                </p>
                              )}
                              {part.description && (
                                <p className="text-xs text-theme-muted mt-1 line-clamp-1">
                                  {part.description}
                                </p>
                              )}
                              <div className="flex items-center gap-4 mt-2">
                                <span className="text-sm font-medium text-primary">
                                  Qty: {part.quantity_at_location.toLocaleString()}
                                </span>
                                {part.category && (
                                  <span className="text-xs px-2 py-1 bg-theme-tertiary rounded text-theme-secondary">
                                    {part.category}
                                  </span>
                                )}
                              </div>
                            </div>
                          </div>

                          {/* Actions */}
                          <div className="flex items-center gap-2">
                            <button
                              onClick={() => handlePrintLabel(part)}
                              className="p-2 hover:bg-primary/10 rounded-md transition-colors"
                              title="Print Label"
                            >
                              <Printer className="w-4 h-4 text-primary" />
                            </button>
                            <button
                              onClick={() => handleReturnToOriginal(part)}
                              className="p-2 hover:bg-orange-500/10 rounded-md transition-colors"
                              title="Return to Original Location"
                            >
                              <Undo2 className="w-4 h-4 text-orange-500" />
                            </button>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </>
            )}
          </div>

          {/* Actions */}
          <div className="flex justify-end gap-3 pt-4 border-t border-theme-primary">
            <button onClick={onClose} className="btn btn-secondary">
              Close
            </button>
          </div>
        </div>
      </Modal>

      {/* Print Modal */}
      {showPrintModal && selectedPartForPrint && (
        <PrinterModal
          isOpen={showPrintModal}
          onClose={handleClosePrintModal}
          title={`Print Label: ${selectedPartForPrint.part_name}`}
          partData={{
            part_name: selectedPartForPrint.part_name,
            part_number: selectedPartForPrint.part_number || '',
            location: location.name,
            category: selectedPartForPrint.category || '',
            quantity: selectedPartForPrint.quantity_at_location.toString(),
            description: selectedPartForPrint.description || '',
          }}
        />
      )}

      {/* Return to Original Location Confirmation Modal */}
      {showConfirmModal && partToReturn && (
        <Modal
          isOpen={showConfirmModal}
          onClose={() => {
            setShowConfirmModal(false)
            setPartToReturn(null)
          }}
          title="Return to Original Location"
          size="md"
        >
          <div className="space-y-4">
            {/* Information Message */}
            <div className="flex items-start gap-3 p-4 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg">
              <AlertCircle className="w-5 h-5 text-blue-500 flex-shrink-0 mt-0.5" />
              <div>
                <h3 className="font-medium text-blue-900 dark:text-blue-100">
                  About Returning Parts
                </h3>
                <p className="text-sm text-blue-700 dark:text-blue-300 mt-1">
                  This will return the part to its original primary storage location. The allocation
                  to this location will be removed.
                </p>
              </div>
            </div>

            {/* Part Details */}
            <div className="p-4 bg-theme-secondary rounded-lg border border-theme-primary">
              <h4 className="text-sm font-medium text-theme-muted mb-3">Part Details</h4>
              <div className="space-y-2">
                <div className="flex items-start gap-3">
                  {partToReturn.image_url && (
                    <img
                      src={partToReturn.image_url}
                      alt={partToReturn.part_name}
                      className="w-12 h-12 object-cover rounded border border-theme-primary"
                    />
                  )}
                  <div className="flex-1">
                    <p className="font-medium text-theme-primary">{partToReturn.part_name}</p>
                    {partToReturn.part_number && (
                      <p className="text-sm text-theme-secondary">PN: {partToReturn.part_number}</p>
                    )}
                  </div>
                </div>
                <div className="pt-2 border-t border-theme-primary">
                  <p className="text-sm text-theme-secondary">
                    <span className="font-medium">Quantity at this location:</span>{' '}
                    {partToReturn.quantity_at_location.toLocaleString()}
                  </p>
                  <p className="text-sm text-theme-secondary mt-1">
                    <span className="font-medium">Current location:</span> {location.name}
                  </p>
                </div>
              </div>
            </div>

            {/* Warning */}
            <div className="flex items-start gap-3 p-4 bg-orange-50 dark:bg-orange-900/20 border border-orange-200 dark:border-orange-800 rounded-lg">
              <Undo2 className="w-5 h-5 text-orange-500 flex-shrink-0 mt-0.5" />
              <div>
                <p className="text-sm text-orange-700 dark:text-orange-300">
                  This action will move all <strong>{partToReturn.quantity_at_location}</strong>{' '}
                  units back to the part's primary storage location.
                </p>
              </div>
            </div>

            {/* Action Buttons */}
            <div className="flex justify-end gap-3 pt-4 border-t border-theme-primary">
              <button
                onClick={() => {
                  setShowConfirmModal(false)
                  setPartToReturn(null)
                }}
                className="btn btn-secondary"
              >
                Cancel
              </button>
              <button
                onClick={confirmReturnToOriginal}
                className="btn bg-orange-500 hover:bg-orange-600 text-white"
              >
                Return to Original Location
              </button>
            </div>
          </div>
        </Modal>
      )}

      {/* Add Child Location Modal */}
      <AddLocationModal
        isOpen={showAddChildModal}
        onClose={() => setShowAddChildModal(false)}
        onSuccess={() => {
          setShowAddChildModal(false)
          loadLocationData() // Reload to show new child
          if (onRefresh) onRefresh() // Refresh parent list too
        }}
        defaultParentId={location.id}
      />

      {/* Edit Location Modal */}
      <EditLocationModal
        isOpen={showEditModal}
        onClose={() => setShowEditModal(false)}
        onSuccess={() => {
          setShowEditModal(false)
          loadLocationData() // Reload to show updated info
          if (onRefresh) onRefresh() // Refresh parent list too
        }}
        location={location}
      />
    </>
  )
}

export default LocationDetailsModal
