import { useState, useEffect } from 'react'
import { Check, Loader2, Box, Grid3x3, List, AlertCircle } from 'lucide-react'
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { locationsService } from '@/services/locations.service'
import type { Location, SlotWithOccupancy } from '@/types/locations'
import { cn } from '@/lib/utils'

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
        className={cn(
          'relative p-4 border-2 rounded-lg transition-all hover:shadow-md',
          'focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2',
          isSelected && 'border-blue-500 bg-blue-50 dark:bg-blue-950',
          !isSelected && isOccupied && 'border-yellow-300 bg-yellow-50 dark:bg-yellow-950/20',
          !isSelected && !isOccupied && 'border-green-300 bg-green-50 dark:bg-green-950/20',
          'text-left'
        )}
      >
        {isSelected && (
          <div className="absolute top-2 right-2">
            <Check className="w-5 h-5 text-blue-600" />
          </div>
        )}

        <div className="font-medium text-sm mb-1">{slot.name}</div>

        {slot.slot_metadata && (
          <div className="text-xs text-gray-500 dark:text-gray-400 mb-2">
            {slot.slot_metadata.row !== undefined && `Row ${slot.slot_metadata.row}`}
            {slot.slot_metadata.column !== undefined && `, Col ${slot.slot_metadata.column}`}
          </div>
        )}

        <div className="flex items-center gap-2 flex-wrap">
          <Badge variant={isOccupied ? 'secondary' : 'default'} className="text-xs">
            {isOccupied ? 'Occupied' : 'Available'}
          </Badge>

          {isOccupied && partCount > 0 && (
            <>
              <Badge variant="outline" className="text-xs">
                {partCount} part{partCount !== 1 ? 's' : ''}
              </Badge>
              {totalQuantity > 0 && (
                <Badge variant="outline" className="text-xs">
                  Qty: {totalQuantity}
                </Badge>
              )}
            </>
          )}
        </div>
      </button>
    )
  }

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="max-w-4xl max-h-[80vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Box className="w-5 h-5" />
            Select Slot in {container.name}
          </DialogTitle>
          <DialogDescription>
            Choose a slot for this part. {isGridLayout ? 'Grid layout.' : 'List layout.'}
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4">
          {/* Filters */}
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              {isGridLayout ? (
                <Grid3x3 className="w-4 h-4 text-gray-500" />
              ) : (
                <List className="w-4 h-4 text-gray-500" />
              )}
              <span className="text-sm text-gray-600 dark:text-gray-400">
                {filteredSlots.length} of {slots.length} slots
              </span>
            </div>

            <Button
              variant="outline"
              size="sm"
              onClick={() => setShowAvailableOnly(!showAvailableOnly)}
            >
              {showAvailableOnly ? 'Show All' : 'Available Only'}
            </Button>
          </div>

          {/* Loading State */}
          {loading && (
            <div className="flex items-center justify-center py-12">
              <Loader2 className="w-8 h-8 animate-spin text-gray-400" />
            </div>
          )}

          {/* Error State */}
          {error && (
            <div className="flex items-center gap-2 p-4 bg-red-50 dark:bg-red-950/20 border border-red-200 dark:border-red-800 rounded-lg">
              <AlertCircle className="w-5 h-5 text-red-600 dark:text-red-400" />
              <span className="text-sm text-red-700 dark:text-red-300">{error}</span>
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
              <Box className="w-12 h-12 text-gray-300 dark:text-gray-600 mx-auto mb-4" />
              <p className="text-gray-500 dark:text-gray-400">
                {showAvailableOnly ? 'No available slots found' : 'No slots found'}
              </p>
            </div>
          )}
        </div>

        <div className="flex justify-end gap-2 pt-4 border-t">
          <Button variant="outline" onClick={onClose}>
            Cancel
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  )
}
