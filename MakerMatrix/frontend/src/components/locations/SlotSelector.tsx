import { useState, useEffect } from 'react'
import { Check, Loader2, Box, Grid3x3, List, AlertCircle } from 'lucide-react'
import Modal from '@/components/ui/Modal'
import { locationsService } from '@/services/locations.service'
import type { Location, SlotWithOccupancy } from '@/types/locations'

interface SlotSelectorProps {
  container: Location
  isOpen: boolean
  onClose: () => void
  onSelectSlot: (slot: SlotWithOccupancy) => void
  selectedSlotId?: string
}

export function SlotSelector({
  container,
  isOpen,
  onClose,
  onSelectSlot,
  selectedSlotId,
}: SlotSelectorProps) {
  const [slots, setSlots] = useState<SlotWithOccupancy[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [showAvailableOnly, setShowAvailableOnly] = useState(false)

  useEffect(() => {
    if (isOpen && container.id) {
      loadSlots()
    }
  }, [isOpen, container.id])

  const loadSlots = async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await locationsService.getContainerSlots(container.id, { include_occupancy: true })
      setSlots(data)
    } catch (err) {
      console.error('Failed to load slots:', err)
      setError('Failed to load slots. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  const filteredSlots = showAvailableOnly
    ? slots.filter((slot) => !slot.occupancy?.is_occupied)
    : slots

  const isGridLayout = container.slot_layout_type === 'grid'
  const gridRows = container.grid_rows || 1
  const gridColumns = container.grid_columns || 1

  const handleSlotClick = (slot: SlotWithOccupancy) => {
    onSelectSlot(slot)
    onClose()
  }

  const renderSlotCard = (slot: SlotWithOccupancy) => {
    const isSelected = selectedSlotId === slot.id
    const isOccupied = slot.occupancy?.is_occupied || false
    const partCount = slot.occupancy?.part_count || 0
    const totalQuantity = slot.occupancy?.total_quantity || 0

    return (
      <button
        key={slot.id}
        onClick={() => handleSlotClick(slot)}
        className={`
          relative p-3 border-2 rounded-lg transition-all hover:shadow-md
          focus:outline-none focus:ring-2 focus:ring-primary text-left
          ${isSelected ? 'border-primary bg-primary/10' : ''}
          ${!isSelected && isOccupied ? 'border-yellow-500/50 bg-yellow-500/10' : ''}
          ${!isSelected && !isOccupied ? 'border-green-500/50 bg-green-500/10' : ''}
        `}
      >
        {isSelected && (
          <div className="absolute top-2 right-2">
            <Check className="w-4 h-4 text-primary" />
          </div>
        )}

        <div className="font-medium text-sm mb-1">{slot.name}</div>

        {slot.slot_metadata && (
          <div className="text-xs text-secondary mb-2">
            {slot.slot_metadata.row !== undefined && `Row ${slot.slot_metadata.row}`}
            {slot.slot_metadata.column !== undefined && `, Col ${slot.slot_metadata.column}`}
          </div>
        )}

        <div className="flex items-center gap-2 flex-wrap text-xs">
          <span className={`px-2 py-0.5 rounded ${isOccupied ? 'bg-yellow-500/20 text-yellow-700 dark:text-yellow-300' : 'bg-green-500/20 text-green-700 dark:text-green-300'}`}>
            {isOccupied ? 'Occupied' : 'Available'}
          </span>

          {isOccupied && partCount > 0 && (
            <>
              <span className="px-2 py-0.5 rounded bg-secondary/20 text-secondary">
                {partCount} part{partCount !== 1 ? 's' : ''}
              </span>
              {totalQuantity > 0 && (
                <span className="px-2 py-0.5 rounded bg-secondary/20 text-secondary">
                  Qty: {totalQuantity}
                </span>
              )}
            </>
          )}
        </div>
      </button>
    )
  }

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={`Select Slot in ${container.name}`}
      size="xl"
    >
      <div className="space-y-4">
        {/* Header Info */}
        <div className="flex items-center justify-between pb-3 border-b border-border">
          <div className="flex items-center gap-2 text-sm text-secondary">
            {isGridLayout ? (
              <Grid3x3 className="w-4 h-4" />
            ) : (
              <List className="w-4 h-4" />
            )}
            <span>
              {filteredSlots.length} of {slots.length} slots
            </span>
          </div>

          <button
            onClick={() => setShowAvailableOnly(!showAvailableOnly)}
            className="btn btn-secondary btn-sm"
          >
            {showAvailableOnly ? 'Show All' : 'Available Only'}
          </button>
        </div>

        {/* Loading State */}
        {loading && (
          <div className="flex items-center justify-center py-12">
            <Loader2 className="w-8 h-8 animate-spin text-secondary" />
          </div>
        )}

        {/* Error State */}
        {error && (
          <div className="flex items-center gap-2 p-4 bg-red-500/10 border border-red-500/20 rounded-lg">
            <AlertCircle className="w-5 h-5 text-red-500" />
            <span className="text-sm text-red-600 dark:text-red-400">{error}</span>
          </div>
        )}

        {/* Grid View for Grid Layout */}
        {!loading && !error && isGridLayout && (
          <div
            className="grid gap-3"
            style={{
              gridTemplateColumns: `repeat(${gridColumns}, 1fr)`,
              gridTemplateRows: `repeat(${gridRows}, auto)`,
            }}
          >
            {filteredSlots.map((slot) => renderSlotCard(slot))}
          </div>
        )}

        {/* List View for Simple Layout */}
        {!loading && !error && !isGridLayout && (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
            {filteredSlots.map((slot) => renderSlotCard(slot))}
          </div>
        )}

        {/* Empty State */}
        {!loading && !error && filteredSlots.length === 0 && (
          <div className="text-center py-12">
            <Box className="w-12 h-12 text-secondary/30 mx-auto mb-4" />
            <p className="text-secondary">
              {showAvailableOnly ? 'No available slots found' : 'No slots found'}
            </p>
          </div>
        )}

        {/* Footer */}
        <div className="flex justify-end pt-4 border-t border-border">
          <button onClick={onClose} className="btn btn-secondary">
            Cancel
          </button>
        </div>
      </div>
    </Modal>
  )
}
