import { useState, useEffect, useRef, useCallback } from 'react'
import { X, Package, MapPin } from 'lucide-react'
import type { Location } from '@/types/locations'
import { locationsService } from '@/services/locations.service'
import { partsService } from '@/services/parts.service'
import type { Part } from '@/types/parts'
import PartPreviewCard from '@/components/parts/PartPreviewCard'

interface ContainerSlotPickerModalProps {
  isOpen: boolean
  onClose: () => void
  containerLocation: Location
  currentSlotId?: string
  onSlotSelect: (slotId: string) => void
}

interface SlotWithParts extends Location {
  parts?: Part[]
}

const ContainerSlotPickerModal = ({
  isOpen,
  onClose,
  containerLocation,
  currentSlotId,
  onSlotSelect,
}: ContainerSlotPickerModalProps) => {
  const [slots, setSlots] = useState<SlotWithParts[]>([])
  const [loading, setLoading] = useState(false)
  const [selectedSlotId, setSelectedSlotId] = useState<string | undefined>(currentSlotId)
  const [hoveredPart, setHoveredPart] = useState<Part | null>(null)
  const [hoverPosition, setHoverPosition] = useState<{ x: number; y: number } | null>(null)
  const hoverTimeoutRef = useRef<NodeJS.Timeout | null>(null)

  const loadSlots = useCallback(async () => {
    try {
      setLoading(true)
      const allLocations = await locationsService.getAllLocations({ hide_auto_slots: false })
      // Filter to only child locations of this container that are auto-generated slots
      const containerSlots = allLocations.filter(
        (loc) => loc.parent_id === containerLocation.id && loc.is_auto_generated_slot
      )
      // Sort by slot_number
      containerSlots.sort((a, b) => (a.slot_number || 0) - (b.slot_number || 0))

      // Load parts for each slot
      const slotsWithParts: SlotWithParts[] = await Promise.all(
        containerSlots.map(async (slot) => {
          try {
            console.log(`[ContainerSlotPicker] Loading parts for slot ${slot.name} (${slot.id})`)
            const response = await partsService.searchParts({
              location_id: slot.id,
              page: 1,
              page_size: 100, // Get up to 100 parts per slot
            })
            // Response is wrapped in ApiResponse, so data contains the paginated response
            const items = (response as any).data?.items || (response as any).items || []
            console.log(`[ContainerSlotPicker] Slot ${slot.name} has ${items.length} parts:`, items)
            return {
              ...slot,
              parts: items,
            }
          } catch (error) {
            console.error(`Failed to load parts for slot ${slot.name}:`, error)
            return {
              ...slot,
              parts: [],
            }
          }
        })
      )

      setSlots(slotsWithParts)
    } catch (error) {
      console.error('Failed to load container slots:', error)
    } finally {
      setLoading(false)
    }
  }, [containerLocation])

  useEffect(() => {
    if (isOpen) {
      loadSlots()
      setSelectedSlotId(currentSlotId)
    }
  }, [loadSlots, isOpen, currentSlotId])

  const handleSlotClick = (slotId: string) => {
    setSelectedSlotId(slotId)
  }

  const handleConfirm = () => {
    if (selectedSlotId) {
      onSlotSelect(selectedSlotId)
      onClose()
    }
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

  const renderGridLayout = () => {
    const rows = containerLocation.grid_rows || 0
    const cols = containerLocation.grid_columns || 0

    if (!rows || !cols) return null

    // Calculate box height based on max 4 visible lines, but content scrolls for more
    const maxPartsInSlot = Math.max(...slots.map((s) => s.parts?.length || 0), 0)
    const displayLines = Math.min(maxPartsInSlot, 4)
    // Base height + space for up to 4 visible part lines (16px per line)
    const boxHeight = Math.max(80, 50 + displayLines * 16)

    const grid: SlotWithParts[][] = []
    let slotIndex = 0

    for (let r = 0; r < rows; r++) {
      const row: SlotWithParts[] = []
      for (let c = 0; c < cols; c++) {
        if (slotIndex < slots.length) {
          row.push(slots[slotIndex])
          slotIndex++
        }
      }
      grid.push(row)
    }

    return (
      <div className="space-y-2">
        {grid.map((row, rowIdx) => (
          <div key={rowIdx} className="flex gap-2 justify-center">
            {row.map((slot) => {
              const isSelected = selectedSlotId === slot.id
              const hasParts = (slot.parts?.length || 0) > 0

              return (
                <button
                  key={slot.id}
                  type="button"
                  onClick={() => handleSlotClick(slot.id)}
                  className={`
                    relative px-3 py-2 rounded-lg border-2 transition-all w-[160px] flex flex-col
                    ${
                      isSelected
                        ? 'border-primary bg-primary/20 shadow-lg scale-105'
                        : 'border-theme-primary hover:border-primary hover:bg-primary/10'
                    }
                    ${hasParts ? 'bg-yellow-500/10' : ''}
                  `}
                  style={{ height: `${boxHeight}px` }}
                  title={slot.parts?.map((p) => p.part_name).join(', ') || slot.name}
                >
                  <div className="flex items-center justify-between mb-1">
                    <div className="text-xs font-bold text-theme-primary">{slot.name}</div>
                    {hasParts && (
                      <div
                        className="flex items-center gap-1 px-1.5 py-0.5 bg-primary/20 rounded text-primary text-xs font-semibold"
                        title={`${slot.parts?.length || 0} unique part${(slot.parts?.length || 0) !== 1 ? 's' : ''}`}
                      >
                        <Package className="w-3 h-3" />
                        <span>{slot.parts?.length || 0}</span>
                      </div>
                    )}
                  </div>
                  {hasParts ? (
                    <div className="text-xs text-theme-secondary space-y-0.5 flex-1 overflow-y-auto scrollbar-hide">
                      {slot.parts?.map((part, idx) => (
                        <div
                          key={idx}
                          className="truncate"
                          onMouseEnter={(e) => handlePartHover(part, e)}
                          onMouseLeave={handlePartLeave}
                        >
                          {part.part_name}
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div className="text-xs text-theme-muted italic flex-1 flex items-center">
                      Empty
                    </div>
                  )}
                  {isSelected && (
                    <div className="absolute -top-1 -right-1 w-3 h-3 bg-primary rounded-full" />
                  )}
                </button>
              )
            })}
          </div>
        ))}
      </div>
    )
  }

  const renderSimpleLayout = () => {
    // Calculate box height based on max 4 visible lines, but content scrolls for more
    const maxPartsInSlot = Math.max(...slots.map((s) => s.parts?.length || 0), 0)
    const displayLines = Math.min(maxPartsInSlot, 4)
    // Base height + space for up to 4 visible part lines (16px per line)
    const boxHeight = Math.max(80, 50 + displayLines * 16)

    return (
      <div className="grid grid-cols-4 gap-2">
        {slots.map((slot) => {
          const isSelected = selectedSlotId === slot.id
          const hasParts = (slot.parts?.length || 0) > 0

          return (
            <button
              key={slot.id}
              type="button"
              onClick={() => handleSlotClick(slot.id)}
              className={`
                relative px-3 py-2 rounded-lg border-2 transition-all w-[160px] flex flex-col
                ${
                  isSelected
                    ? 'border-primary bg-primary/20 shadow-lg scale-105'
                    : 'border-theme-primary hover:border-primary hover:bg-primary/10'
                }
                ${hasParts ? 'bg-yellow-500/10' : ''}
              `}
              style={{ height: `${boxHeight}px` }}
              title={slot.parts?.map((p) => p.part_name).join(', ') || slot.name}
            >
              <div className="flex items-center justify-between mb-1">
                <div className="text-xs font-bold text-theme-primary">{slot.name}</div>
                {hasParts && (
                  <div
                    className="flex items-center gap-1 px-1.5 py-0.5 bg-primary/20 rounded text-primary text-xs font-semibold"
                    title={`${slot.parts?.length || 0} unique part${(slot.parts?.length || 0) !== 1 ? 's' : ''}`}
                  >
                    <Package className="w-3 h-3" />
                    <span>{slot.parts?.length || 0}</span>
                  </div>
                )}
              </div>
              {hasParts ? (
                <div className="text-xs text-theme-secondary space-y-0.5 flex-1 overflow-y-auto scrollbar-hide">
                  {slot.parts?.map((part, idx) => (
                    <div
                      key={idx}
                      className="truncate"
                      onMouseEnter={(e) => handlePartHover(part, e)}
                      onMouseLeave={handlePartLeave}
                    >
                      {part.part_name}
                    </div>
                  ))}
                </div>
              ) : (
                <div className="text-xs text-theme-muted italic flex-1 flex items-center">
                  Empty
                </div>
              )}
              {isSelected && (
                <div className="absolute -top-1 -right-1 w-3 h-3 bg-primary rounded-full" />
              )}
            </button>
          )
        })}
      </div>
    )
  }

  if (!isOpen) return null

  const isGridLayout = containerLocation.slot_layout_type === 'grid'

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
      <div className="bg-theme-elevated rounded-lg shadow-xl max-w-4xl w-full max-h-[90vh] overflow-hidden flex flex-col m-4">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-theme-primary">
          <div className="flex items-center gap-3">
            <Package className="w-6 h-6 text-primary" />
            <div>
              <h2 className="text-xl font-semibold text-theme-primary">
                Select Slot in {containerLocation.name}
              </h2>
              <p className="text-sm text-theme-secondary mt-1">
                {isGridLayout
                  ? `${containerLocation.grid_rows} × ${containerLocation.grid_columns} grid layout`
                  : `${slots.length} slots`}
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-2 hover:bg-theme-primary rounded-lg transition-colors"
          >
            <X className="w-5 h-5 text-theme-secondary" />
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-6 scrollbar-hide">
          {loading ? (
            <div className="text-center py-12">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary mx-auto mb-4"></div>
              <p className="text-theme-secondary">Loading slots...</p>
            </div>
          ) : slots.length === 0 ? (
            <div className="text-center py-12">
              <Package className="w-12 h-12 text-theme-muted mx-auto mb-4" />
              <p className="text-theme-secondary">No slots found in this container</p>
            </div>
          ) : (
            <>
              {/* Legend */}
              <div className="mb-6 flex items-center gap-6 text-sm">
                <div className="flex items-center gap-2">
                  <div className="w-4 h-4 border-2 border-theme-primary rounded"></div>
                  <span className="text-theme-secondary">Empty slot</span>
                </div>
                <div className="flex items-center gap-2">
                  <div className="w-4 h-4 border-2 border-theme-primary bg-yellow-500/10 rounded"></div>
                  <span className="text-theme-secondary">Occupied slot</span>
                </div>
                <div className="flex items-center gap-2">
                  <div className="w-4 h-4 border-2 border-primary bg-primary/20 rounded"></div>
                  <span className="text-theme-secondary">Selected slot</span>
                </div>
              </div>

              {/* Slot Grid/List */}
              {isGridLayout ? renderGridLayout() : renderSimpleLayout()}
            </>
          )}
        </div>

        {/* Footer */}
        <div className="p-6 border-t border-theme-primary bg-theme-secondary/20">
          <div className="flex justify-between items-center">
            <div className="text-sm text-theme-secondary">
              {selectedSlotId && (
                <div className="flex items-center gap-2">
                  <MapPin className="w-4 h-4" />
                  Selected: {slots.find((s) => s.id === selectedSlotId)?.name}
                </div>
              )}
            </div>
            <div className="flex gap-3">
              <button
                onClick={onClose}
                className="px-4 py-2 rounded-lg border border-theme-primary hover:bg-theme-primary text-theme-primary transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={handleConfirm}
                disabled={!selectedSlotId}
                className="px-4 py-2 rounded-lg bg-primary text-gray-900 hover:bg-primary-dark transition-colors disabled:opacity-50 disabled:cursor-not-allowed font-medium"
              >
                Confirm Selection
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Hover Preview */}
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
    </div>
  )
}

export default ContainerSlotPickerModal
