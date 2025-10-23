import { useState, useEffect, useRef, useCallback } from 'react'
import { Check, Loader2, Box, Grid3x3, List, AlertCircle, Package } from 'lucide-react'
import Modal from '@/components/ui/Modal'
import { locationsService } from '@/services/locations.service'
import type { Location, SlotWithOccupancy } from '@/types/locations'
import type { Part } from '@/types/parts'
import PartPreviewCard from '@/components/parts/PartPreviewCard'

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

  // Part hover tooltip state
  const [hoveredPart, setHoveredPart] = useState<Part | null>(null)
  const [hoverPosition, setHoverPosition] = useState<{ x: number; y: number } | null>(null)
  const hoverTimeoutRef = useRef<NodeJS.Timeout | null>(null)

  const loadSlots = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await locationsService.getContainerSlots(container.id, {
        include_occupancy: true,
      })
      setSlots(data)
    } catch (err) {
      console.error('Failed to load slots:', err)
      setError('Failed to load slots. Please try again.')
    } finally {
      setLoading(false)
    }
  }, [container.id])

  useEffect(() => {
    if (isOpen && container.id) {
      loadSlots()
    }
  }, [isOpen, container.id, loadSlots])

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

  const handlePartHover = (part: Part, event: React.MouseEvent) => {
    // Clear any existing timeout
    if (hoverTimeoutRef.current) {
      clearTimeout(hoverTimeoutRef.current)
    }

    // Set position slightly offset from cursor
    const rect = event.currentTarget.getBoundingClientRect()
    setHoverPosition({
      x: rect.right + 10,
      y: rect.top,
    })

    // Show preview after short delay
    hoverTimeoutRef.current = setTimeout(() => {
      setHoveredPart(part)
    }, 300)
  }

  const handlePartLeave = () => {
    // Clear timeout if user leaves before delay
    if (hoverTimeoutRef.current) {
      clearTimeout(hoverTimeoutRef.current)
    }
    setHoveredPart(null)
    setHoverPosition(null)
  }

  // Cleanup timeout on unmount
  useEffect(() => {
    return () => {
      if (hoverTimeoutRef.current) {
        clearTimeout(hoverTimeoutRef.current)
      }
    }
  }, [])

  const renderSlotCard = (slot: SlotWithOccupancy) => {
    const isSelected = selectedSlotId === slot.id
    const isOccupied = slot.occupancy?.is_occupied || false
    const partCount = slot.occupancy?.part_count || 0
    const totalQuantity = slot.occupancy?.total_quantity || 0
    const parts = slot.occupancy?.parts || []

    return (
      <button
        key={slot.id}
        onClick={() => handleSlotClick(slot)}
        className={`
          relative p-3 border-2 rounded-lg transition-all hover:shadow-md
          focus:outline-none focus:ring-2 focus:ring-primary text-left flex flex-col min-h-[100px]
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

        {/* Slot Header */}
        <div className="flex items-center justify-between mb-2">
          <div className="font-medium text-sm">{slot.name}</div>
          {isOccupied && partCount > 0 && (
            <div className="flex items-center gap-1 px-1.5 py-0.5 bg-primary/20 rounded text-primary text-xs font-semibold">
              <Package className="w-3 h-3" />
              <span>{partCount}</span>
            </div>
          )}
        </div>

        {slot.slot_metadata && (
          <div className="text-xs text-secondary mb-2">
            {slot.slot_metadata.row !== undefined && `Row ${slot.slot_metadata.row}`}
            {slot.slot_metadata.column !== undefined && `, Col ${slot.slot_metadata.column}`}
          </div>
        )}

        {/* Part List or Empty State */}
        {isOccupied && parts.length > 0 ? (
          <div className="text-xs text-secondary space-y-0.5 flex-1 overflow-y-auto max-h-24">
            {parts.map((part, idx) => (
              <div
                key={idx}
                className="truncate hover:text-primary cursor-help"
                onMouseEnter={(e) => {
                  // Convert occupancy part to full Part type for preview
                  const partForPreview: Part = {
                    id: part.part_id,
                    part_name: part.part_name || 'Unknown Part',
                    part_number: part.part_number,
                    quantity: part.quantity,
                    description: part.description,
                    image_url: part.image_url,
                    categories: part.category ? [{ id: '', name: part.category }] : [],
                  } as Part
                  handlePartHover(partForPreview, e)
                }}
                onMouseLeave={handlePartLeave}
                title={`${part.part_name} (Qty: ${part.quantity})`}
              >
                • {part.part_name}
              </div>
            ))}
          </div>
        ) : (
          <div className="text-xs text-secondary/50 italic flex-1 flex items-center">
            Empty slot
          </div>
        )}

        {/* Footer with total quantity */}
        {isOccupied && totalQuantity > 0 && (
          <div className="text-xs text-primary font-medium mt-2 pt-2 border-t border-border">
            Total: {totalQuantity} units
          </div>
        )}
      </button>
    )
  }

  return (
    <Modal isOpen={isOpen} onClose={onClose} title={`Select Slot in ${container.name}`} size="xl">
      <div className="space-y-4">
        {/* Header Info */}
        <div className="flex items-center justify-between pb-3 border-b border-border">
          <div className="flex items-center gap-2 text-sm text-secondary">
            {isGridLayout ? <Grid3x3 className="w-4 h-4" /> : <List className="w-4 h-4" />}
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

      {/* Hover Preview Tooltip */}
      {hoveredPart && hoverPosition && (
        <div
          className="fixed z-[60] pointer-events-none"
          style={{
            left: `${hoverPosition.x}px`,
            top: `${hoverPosition.y}px`,
          }}
        >
          <PartPreviewCard part={hoveredPart} />
        </div>
      )}
    </Modal>
  )
}
