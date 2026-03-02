import { useState, useEffect, useRef, useCallback } from 'react'
import { createPortal } from 'react-dom'
import { X, Package, Search, Loader2, Trash2, AlertTriangle } from 'lucide-react'
import type { Location } from '@/types/locations'
import type { SlotWithOccupancy } from '@/types/locations'
import { locationsService } from '@/services/locations.service'
import { partsService } from '@/services/parts.service'
import type { Part } from '@/types/parts'
import PartPreviewCard from '@/components/parts/PartPreviewCard'
import toast from 'react-hot-toast'

interface ContainerSlotPickerModalProps {
  isOpen: boolean
  onClose: () => void
  containerLocation: Location
  currentSlotId?: string
  onSlotSelect: (slotId: string) => void
}

interface SlotWithParts {
  id: string
  name: string
  slot_number?: number
  slot_metadata?: Record<string, unknown>
  parts: Array<{
    part_id: string
    part_name: string
    part_number?: string
    quantity: number
    is_primary: boolean
    description?: string
    image_url?: string
    category?: string
  }>
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
  const [hoveredPart, setHoveredPart] = useState<Part | null>(null)
  const [hoverPosition, setHoverPosition] = useState<{ x: number; y: number } | null>(null)
  const hoverTimeoutRef = useRef<NodeJS.Timeout | null>(null)

  // Part search state
  const [activeSlotId, setActiveSlotId] = useState<string | null>(null)
  const [searchQuery, setSearchQuery] = useState('')
  const [searchResults, setSearchResults] = useState<Part[]>([])
  const [searchLoading, setSearchLoading] = useState(false)
  const searchInputRef = useRef<HTMLInputElement>(null)
  const searchPanelRef = useRef<HTMLDivElement>(null)
  const debounceRef = useRef<NodeJS.Timeout | null>(null)

  // Move confirmation state
  const [pendingAssign, setPendingAssign] = useState<{
    part: Part
    slotId: string
    currentLocationName: string
  } | null>(null)

  const loadSlots = useCallback(async () => {
    try {
      setLoading(true)
      const rawSlots: SlotWithOccupancy[] = await locationsService.getContainerSlots(
        containerLocation.id,
        { include_occupancy: true }
      )

      const mapped: SlotWithParts[] = rawSlots.map((s) => ({
        id: s.id,
        name: s.name,
        slot_number: s.slot_number,
        slot_metadata: s.slot_metadata as Record<string, unknown> | undefined,
        parts: s.occupancy?.parts || [],
      }))

      setSlots(mapped)
    } catch (error) {
      console.error('Failed to load container slots:', error)
    } finally {
      setLoading(false)
    }
  }, [containerLocation.id])

  useEffect(() => {
    if (isOpen) {
      loadSlots()
    }
    return () => {
      setActiveSlotId(null)
      setSearchQuery('')
      setSearchResults([])
    }
  }, [loadSlots, isOpen])

  // Debounced search
  useEffect(() => {
    if (!searchQuery.trim()) {
      setSearchResults([])
      setSearchLoading(false)
      return
    }

    setSearchLoading(true)
    if (debounceRef.current) clearTimeout(debounceRef.current)

    debounceRef.current = setTimeout(async () => {
      try {
        const result = await partsService.searchPartsText(searchQuery, 1, 10)
        setSearchResults(result.data)
      } catch (error) {
        console.error('Search failed:', error)
        setSearchResults([])
      } finally {
        setSearchLoading(false)
      }
    }, 300)

    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current)
    }
  }, [searchQuery])

  // Focus search input when a slot is activated
  useEffect(() => {
    if (activeSlotId) {
      setTimeout(() => searchInputRef.current?.focus(), 50)
    }
  }, [activeSlotId])

  // Close search panel on Escape or click outside
  useEffect(() => {
    if (!activeSlotId) return

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        setActiveSlotId(null)
        setSearchQuery('')
        setSearchResults([])
      }
    }

    const handleClickOutside = (e: MouseEvent) => {
      if (searchPanelRef.current && !searchPanelRef.current.contains(e.target as Node)) {
        setActiveSlotId(null)
        setSearchQuery('')
        setSearchResults([])
      }
    }

    document.addEventListener('keydown', handleKeyDown)
    // Delay adding click listener to prevent immediate close
    const timer = setTimeout(() => {
      document.addEventListener('mousedown', handleClickOutside)
    }, 100)

    return () => {
      document.removeEventListener('keydown', handleKeyDown)
      document.removeEventListener('mousedown', handleClickOutside)
      clearTimeout(timer)
    }
  }, [activeSlotId])

  // Cleanup timeouts on unmount
  useEffect(() => {
    return () => {
      if (hoverTimeoutRef.current) clearTimeout(hoverTimeoutRef.current)
      if (debounceRef.current) clearTimeout(debounceRef.current)
    }
  }, [])

  const handleSlotClick = (slotId: string) => {
    if (activeSlotId === slotId) {
      // Clicking same slot again closes search
      setActiveSlotId(null)
      setSearchQuery('')
      setSearchResults([])
    } else {
      setActiveSlotId(slotId)
      setSearchQuery('')
      setSearchResults([])
    }
  }

  const handleAssignPart = async (part: Part, slotId: string) => {
    // Check if part already has a location
    const currentLocation = part.location
    const currentLocationName = currentLocation?.name || (part.location_id ? 'another location' : '')

    if (currentLocationName) {
      // Part is already somewhere — show confirmation
      setPendingAssign({ part, slotId, currentLocationName })
      return
    }

    // No existing location — assign directly
    await doAssignPart(part, slotId)
  }

  const doAssignPart = async (part: Part, slotId: string) => {
    try {
      await partsService.updatePart({ id: part.id, location_id: slotId })
      const slotName = slots.find((s) => s.id === slotId)?.name || slotId
      toast.success(`Part '${part.part_name || part.name}' assigned to ${slotName}`)
      onSlotSelect(slotId)
      setActiveSlotId(null)
      setSearchQuery('')
      setSearchResults([])
      setPendingAssign(null)
      await loadSlots()
    } catch (error) {
      console.error('Failed to assign part:', error)
      toast.error('Failed to assign part to slot')
    }
  }

  const handleRemovePart = async (partId: string, partName: string, slotName: string) => {
    try {
      // Move part to the parent container location (unslot it)
      await partsService.updatePart({ id: partId, location_id: containerLocation.id })
      toast.success(`Part '${partName}' removed from ${slotName}`)
      setActiveSlotId(null)
      await loadSlots()
    } catch (error) {
      console.error('Failed to remove part from slot:', error)
      toast.error('Failed to remove part from slot')
    }
  }

  const handlePartHover = (part: Part, event: React.MouseEvent) => {
    if (hoverTimeoutRef.current) clearTimeout(hoverTimeoutRef.current)
    const rect = event.currentTarget.getBoundingClientRect()
    setHoverPosition({ x: rect.right + 10, y: rect.top })
    hoverTimeoutRef.current = setTimeout(() => {
      setHoveredPart(part)
    }, 300)
  }

  const handleOccupantHover = (
    occupant: SlotWithParts['parts'][0],
    event: React.MouseEvent
  ) => {
    // Build a minimal Part-like object for the preview card
    const partLike = {
      id: occupant.part_id,
      name: occupant.part_name,
      part_name: occupant.part_name,
      part_number: occupant.part_number,
      description: occupant.description,
      image_url: occupant.image_url,
      quantity: occupant.quantity,
    } as Part
    handlePartHover(partLike, event)
  }

  const handlePartLeave = () => {
    if (hoverTimeoutRef.current) clearTimeout(hoverTimeoutRef.current)
    setHoveredPart(null)
    setHoverPosition(null)
  }

  // Build grid cells — from slots array or fallback to container dimensions
  const buildGridCells = (): SlotWithParts[][] => {
    const rows = containerLocation.grid_rows || 0
    const cols = containerLocation.grid_columns || 0
    if (!rows || !cols) return []

    const grid: SlotWithParts[][] = []
    let slotIndex = 0

    for (let r = 0; r < rows; r++) {
      const row: SlotWithParts[] = []
      for (let c = 0; c < cols; c++) {
        if (slotIndex < slots.length) {
          row.push(slots[slotIndex])
          slotIndex++
        } else {
          // Placeholder cell for missing slot
          row.push({
            id: `placeholder-${r}-${c}`,
            name: `R${r + 1}-C${c + 1}`,
            slot_number: r * cols + c + 1,
            parts: [],
          })
        }
      }
      grid.push(row)
    }
    return grid
  }

  const buildSimpleCells = (): SlotWithParts[] => {
    const count = containerLocation.slot_count || slots.length
    if (count === 0) return slots

    const cells: SlotWithParts[] = []
    for (let i = 0; i < count; i++) {
      if (i < slots.length) {
        cells.push(slots[i])
      } else {
        cells.push({
          id: `placeholder-${i}`,
          name: `Slot ${i + 1}`,
          slot_number: i + 1,
          parts: [],
        })
      }
    }
    return cells
  }

  const renderSlotCell = (slot: SlotWithParts) => {
    const isActive = activeSlotId === slot.id
    const isPlaceholder = slot.id.startsWith('placeholder-')
    const hasParts = slot.parts.length > 0

    return (
      <button
        key={slot.id}
        type="button"
        onClick={() => !isPlaceholder && handleSlotClick(slot.id)}
        disabled={isPlaceholder}
        className={`
          relative px-2 py-1.5 rounded-lg border-2 transition-all w-[140px] h-[100px] flex flex-col overflow-hidden
          ${
            isActive
              ? 'border-primary bg-primary/20 shadow-lg ring-2 ring-primary/40'
              : isPlaceholder
                ? 'border-dashed border-theme-muted opacity-50 cursor-not-allowed'
                : 'border-theme-primary hover:border-primary hover:bg-primary/10 cursor-pointer'
          }
          ${hasParts && !isActive ? 'bg-yellow-500/10' : ''}
        `}
        title={
          isPlaceholder
            ? 'Slot not yet created'
            : !hasParts
              ? `${slot.name} — click to assign a part`
              : undefined
        }
      >
        <div className="flex items-center justify-between mb-0.5 flex-shrink-0">
          <div className="text-[10px] font-bold text-theme-primary">{slot.name}</div>
          {hasParts && (
            <div className="flex items-center gap-0.5 px-1 py-0.5 bg-primary/20 rounded text-primary text-[9px] font-semibold">
              <Package className="w-2.5 h-2.5" />
              <span>{slot.parts.length}</span>
            </div>
          )}
        </div>
        {hasParts ? (
          <div className="flex-1 overflow-hidden space-y-0.5">
            {slot.parts.map((occupant, idx) => (
              <div key={idx} className="flex items-start gap-1">
                {occupant.image_url ? (
                  <img
                    src={occupant.image_url}
                    alt=""
                    className="w-5 h-5 rounded-sm object-cover flex-shrink-0 mt-px"
                  />
                ) : (
                  <div className="w-5 h-5 rounded-sm bg-theme-primary/50 flex items-center justify-center flex-shrink-0 mt-px">
                    <Package className="w-3 h-3 text-theme-muted" />
                  </div>
                )}
                <span
                  className="text-[10px] leading-tight text-theme-secondary line-clamp-3 min-w-0"
                  onMouseEnter={(e) => {
                    e.stopPropagation()
                    handleOccupantHover(occupant, e)
                  }}
                  onMouseLeave={handlePartLeave}
                  title={occupant.part_name}
                >
                  {occupant.part_name}
                </span>
              </div>
            ))}
          </div>
        ) : (
          <div className="text-[10px] text-theme-muted italic flex-1 flex items-center">
            {isPlaceholder ? 'Pending' : 'Empty'}
          </div>
        )}
        {isActive && (
          <div className="absolute -top-1 -right-1 w-3 h-3 bg-primary rounded-full animate-pulse" />
        )}
      </button>
    )
  }

  const renderGridLayout = () => {
    const grid = buildGridCells()
    if (grid.length === 0) return null

    return (
      <div className="space-y-2">
        {grid.map((row, rowIdx) => (
          <div key={rowIdx} className="flex gap-2 justify-center">
            {row.map((slot) => renderSlotCell(slot))}
          </div>
        ))}
      </div>
    )
  }

  const renderSimpleLayout = () => {
    const cells = buildSimpleCells()
    if (cells.length === 0) return null

    return (
      <div className="grid grid-cols-4 gap-2">
        {cells.map((slot) => renderSlotCell(slot))}
      </div>
    )
  }

  const renderSlotPanel = () => {
    if (!activeSlotId) return null
    const activeSlot = slots.find((s) => s.id === activeSlotId)
    if (!activeSlot) return null

    const hasParts = activeSlot.parts.length > 0

    const closePanel = () => {
      setActiveSlotId(null)
      setSearchQuery('')
      setSearchResults([])
    }

    return (
      <div
        ref={searchPanelRef}
        className="mt-6 border-2 border-primary/30 rounded-lg bg-theme-elevated p-4"
      >
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-sm font-semibold text-theme-primary">
            {hasParts ? `${activeSlot.name} — Assigned Parts` : `Assign Part to ${activeSlot.name}`}
          </h3>
          <button
            type="button"
            onClick={closePanel}
            className="p-1 hover:bg-theme-primary rounded transition-colors"
          >
            <X className="w-4 h-4 text-theme-secondary" />
          </button>
        </div>

        {/* Show current parts in this slot with remove buttons */}
        {hasParts && (
          <div className="mb-3 border border-theme-primary rounded-lg divide-y divide-theme-primary">
            {activeSlot.parts.map((occupant) => (
              <div
                key={occupant.part_id}
                className="flex items-center gap-3 px-4 py-2"
              >
                {occupant.image_url ? (
                  <img
                    src={occupant.image_url}
                    alt=""
                    className="w-8 h-8 rounded object-cover flex-shrink-0"
                  />
                ) : (
                  <div className="w-8 h-8 rounded bg-theme-primary flex items-center justify-center flex-shrink-0">
                    <Package className="w-4 h-4 text-theme-muted" />
                  </div>
                )}
                <div className="min-w-0 flex-1">
                  <div className="text-sm font-medium text-theme-primary truncate">
                    {occupant.part_name}
                  </div>
                  <div className="text-xs text-theme-secondary truncate">
                    {occupant.part_number && <span className="mr-2">{occupant.part_number}</span>}
                    <span>Qty: {occupant.quantity}</span>
                  </div>
                </div>
                <button
                  type="button"
                  onClick={() =>
                    handleRemovePart(occupant.part_id, occupant.part_name, activeSlot.name)
                  }
                  className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-xs font-medium text-red-400 hover:bg-red-500/10 border border-red-500/30 hover:border-red-500/50 transition-colors flex-shrink-0"
                  title={`Remove ${occupant.part_name} from ${activeSlot.name}`}
                >
                  <Trash2 className="w-3.5 h-3.5" />
                  Remove
                </button>
              </div>
            ))}
          </div>
        )}

        {/* Search to add more parts */}
        <div>
          {hasParts && (
            <div className="text-xs text-theme-secondary mb-2">Add another part to this slot:</div>
          )}
          <div className="relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-theme-muted" />
            <input
              ref={searchInputRef}
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search parts by name or number..."
              className="input w-full pl-10 pr-10"
              autoComplete="off"
            />
            {searchLoading && (
              <Loader2 className="absolute right-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-theme-muted animate-spin" />
            )}
          </div>

          {searchResults.length > 0 && (
            <div className="mt-2 max-h-60 overflow-y-auto border border-theme-primary rounded-lg">
              {searchResults.map((part) => (
                <button
                  key={part.id}
                  type="button"
                  onClick={() => handleAssignPart(part, activeSlotId)}
                  className="w-full text-left px-4 py-2 hover:bg-primary/10 transition-colors border-b border-theme-primary last:border-b-0 flex items-center gap-3"
                >
                  {part.image_url ? (
                    <img
                      src={part.image_url}
                      alt=""
                      className="w-8 h-8 rounded object-cover flex-shrink-0"
                    />
                  ) : (
                    <div className="w-8 h-8 rounded bg-theme-primary flex items-center justify-center flex-shrink-0">
                      <Package className="w-4 h-4 text-theme-muted" />
                    </div>
                  )}
                  <div className="min-w-0 flex-1">
                    <div className="text-sm font-medium text-theme-primary truncate">
                      {part.part_name || part.name}
                    </div>
                    <div className="text-xs text-theme-secondary truncate">
                      {part.part_number && <span className="mr-2">{part.part_number}</span>}
                      {part.quantity !== undefined && <span>Qty: {part.quantity}</span>}
                    </div>
                  </div>
                </button>
              ))}
            </div>
          )}

          {searchQuery.trim() && !searchLoading && searchResults.length === 0 && (
            <div className="mt-2 text-center py-4 text-sm text-theme-muted">
              No parts found for &quot;{searchQuery}&quot;
            </div>
          )}
        </div>
      </div>
    )
  }

  if (!isOpen) return null

  const isGridLayout = containerLocation.slot_layout_type === 'grid'
  const totalSlots = containerLocation.slot_count || slots.length
  const occupiedSlots = slots.filter((s) => s.parts.length > 0).length
  const hasContent = slots.length > 0 || totalSlots > 0

  return createPortal(
    <div className="fixed inset-0 z-[10000] flex items-center justify-center bg-black/50">
      <div className="bg-theme-elevated rounded-lg shadow-xl max-w-4xl w-full max-h-[90vh] overflow-hidden flex flex-col m-4">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-theme-primary">
          <div className="flex items-center gap-3">
            <Package className="w-6 h-6 text-primary" />
            <div>
              <h2 className="text-xl font-semibold text-theme-primary">
                {containerLocation.name}
              </h2>
              <p className="text-sm text-theme-secondary mt-1">
                {isGridLayout
                  ? `${containerLocation.grid_rows} x ${containerLocation.grid_columns} grid layout`
                  : `${totalSlots} slots`}
                {' — click a slot to manage parts'}
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
          ) : !hasContent ? (
            <div className="text-center py-12">
              <Package className="w-12 h-12 text-theme-muted mx-auto mb-4" />
              <p className="text-theme-secondary">No slots configured for this container</p>
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

              {/* Slot Panel (appears below grid when a slot is active) */}
              {renderSlotPanel()}
            </>
          )}
        </div>

        {/* Footer */}
        <div className="p-4 border-t border-theme-primary bg-theme-secondary/20">
          <div className="flex justify-between items-center">
            <div className="text-sm text-theme-secondary">
              {occupiedSlots} / {totalSlots} slots occupied
            </div>
            <button
              onClick={onClose}
              className="px-4 py-2 rounded-lg border border-theme-primary hover:bg-theme-primary text-theme-primary transition-colors"
            >
              Close
            </button>
          </div>
        </div>
      </div>

      {/* Move Confirmation Dialog */}
      {pendingAssign && (
        <div className="fixed inset-0 z-[10002] flex items-center justify-center bg-black/40">
          <div className="bg-theme-elevated rounded-lg shadow-xl max-w-md w-full p-6 m-4 border border-theme-primary">
            <div className="flex items-center gap-3 mb-4">
              <div className="p-2 rounded-full bg-yellow-500/10">
                <AlertTriangle className="w-5 h-5 text-yellow-500" />
              </div>
              <h3 className="text-lg font-semibold text-theme-primary">Move Part?</h3>
            </div>
            <p className="text-sm text-theme-secondary mb-1">
              <span className="font-medium text-theme-primary">
                {pendingAssign.part.part_name || pendingAssign.part.name}
              </span>{' '}
              is currently in{' '}
              <span className="font-medium text-theme-primary">
                {pendingAssign.currentLocationName}
              </span>.
            </p>
            <p className="text-sm text-theme-secondary mb-6">
              Move it to{' '}
              <span className="font-medium text-theme-primary">
                {slots.find((s) => s.id === pendingAssign.slotId)?.name || pendingAssign.slotId}
              </span>?
            </p>
            <div className="flex justify-end gap-3">
              <button
                type="button"
                onClick={() => setPendingAssign(null)}
                className="px-4 py-2 rounded-lg border border-theme-primary hover:bg-theme-primary text-theme-primary transition-colors text-sm"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={() => doAssignPart(pendingAssign.part, pendingAssign.slotId)}
                className="px-4 py-2 rounded-lg bg-primary text-gray-900 hover:bg-primary-dark transition-colors font-medium text-sm"
              >
                Move Part
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Hover Preview */}
      {hoveredPart && hoverPosition && (
        <div
          className="fixed z-[10001] pointer-events-none"
          style={{
            left: `${hoverPosition.x}px`,
            top: `${hoverPosition.y}px`,
          }}
        >
          <PartPreviewCard part={hoveredPart} />
        </div>
      )}
    </div>,
    document.body
  )
}

export default ContainerSlotPickerModal
