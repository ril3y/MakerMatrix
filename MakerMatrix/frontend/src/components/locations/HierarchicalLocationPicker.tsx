import { useState, useEffect } from 'react'
import { MapPin, ChevronRight, Box, X, Search, Loader2 } from 'lucide-react'
import { SlotSelector } from './SlotSelector'
import { locationsService } from '@/services/locations.service'
import type { Location, SlotWithOccupancy } from '@/types/locations'

interface HierarchicalLocationPickerProps {
  value?: string // Selected location/slot ID
  onChange: (locationId: string | undefined) => void
  label?: string
  required?: boolean
  error?: string
  disabled?: boolean
  className?: string
}

export function HierarchicalLocationPicker({
  value,
  onChange,
  label = 'Location',
  required = false,
  error,
  disabled = false,
  className,
}: HierarchicalLocationPickerProps) {
  const [locations, setLocations] = useState<Location[]>([])
  const [loading, setLoading] = useState(true)
  const [searchTerm, setSearchTerm] = useState('')
  const [selectedLocation, setSelectedLocation] = useState<Location | null>(null)
  const [selectedSlot, setSelectedSlot] = useState<SlotWithOccupancy | null>(null)
  const [slotSelectorOpen, setSlotSelectorOpen] = useState(false)
  const [containerForSlotSelection, setContainerForSlotSelection] = useState<Location | null>(null)

  useEffect(() => {
    loadLocations()
  }, [])

  useEffect(() => {
    // When value changes externally, load the selected location/slot details
    if (value && locations.length > 0) {
      loadSelectedLocationDetails(value)
    } else if (!value) {
      setSelectedLocation(null)
      setSelectedSlot(null)
    }
  }, [value, locations])

  const loadLocations = async () => {
    setLoading(true)
    try {
      // Hide auto-generated slots - we'll show them via SlotSelector
      const data = await locationsService.getAllLocations({ hide_auto_slots: true })
      setLocations(data)
    } catch (err) {
      console.error('Failed to load locations:', err)
    } finally {
      setLoading(false)
    }
  }

  const loadSelectedLocationDetails = async (locationId: string) => {
    // Check if it's a regular location or a slot
    const regularLocation = locations.find((loc) => loc.id === locationId)

    if (regularLocation) {
      setSelectedLocation(regularLocation)
      setSelectedSlot(null)
    } else {
      // It might be a slot - we need to load all slots to find it
      try {
        const allLocations = await locationsService.getAllLocations({ hide_auto_slots: false })
        const slotLocation = allLocations.find((loc) => loc.id === locationId)

        if (slotLocation && slotLocation.is_auto_generated_slot && slotLocation.parent_id) {
          const container = locations.find((loc) => loc.id === slotLocation.parent_id)
          if (container) {
            setSelectedLocation(container)
            setSelectedSlot(slotLocation as SlotWithOccupancy)
          }
        }
      } catch (err) {
        console.error('Failed to load slot details:', err)
      }
    }
  }

  const handleLocationClick = (location: Location) => {
    // If it's a container with slots, open slot selector
    if (location.slot_count && location.slot_count > 0) {
      setContainerForSlotSelection(location)
      setSlotSelectorOpen(true)
    } else {
      // Regular location - select directly
      setSelectedLocation(location)
      setSelectedSlot(null)
      onChange(location.id)
    }
  }

  const handleSlotSelect = (slot: SlotWithOccupancy) => {
    setSelectedLocation(containerForSlotSelection)
    setSelectedSlot(slot)
    onChange(slot.id)
    setSlotSelectorOpen(false)
  }

  const handleClear = () => {
    setSelectedLocation(null)
    setSelectedSlot(null)
    onChange(undefined)
  }

  const filteredLocations = searchTerm
    ? locations.filter((loc) =>
        loc.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
        loc.description?.toLowerCase().includes(searchTerm.toLowerCase())
      )
    : locations

  // Organize locations into tree structure
  const rootLocations = filteredLocations.filter((loc) => !loc.parent_id)
  const childLocationsByParent = new Map<string, Location[]>()

  filteredLocations.forEach((loc) => {
    if (loc.parent_id) {
      const children = childLocationsByParent.get(loc.parent_id) || []
      children.push(loc)
      childLocationsByParent.set(loc.parent_id, children)
    }
  })

  const renderLocationItem = (location: Location, depth: number = 0): JSX.Element => {
    const children = childLocationsByParent.get(location.id) || []
    const isContainer = location.slot_count && location.slot_count > 0
    const hasChildren = children.length > 0

    return (
      <div key={location.id}>
        <button
          onClick={() => handleLocationClick(location)}
          disabled={disabled}
          className={`
            w-full flex items-center gap-2 p-3 rounded-lg border transition-colors text-left
            hover:bg-background-secondary focus:outline-none focus:ring-2 focus:ring-primary
            ${disabled ? 'opacity-50 cursor-not-allowed' : ''}
            ${depth > 0 ? `ml-${depth * 4}` : ''}
          `}
        >
          {location.emoji ? (
            <span className="text-xl">{location.emoji}</span>
          ) : isContainer ? (
            <Box className="w-5 h-5 text-primary" />
          ) : (
            <MapPin className="w-5 h-5 text-secondary" />
          )}

          <div className="flex-1">
            <div className="font-medium text-sm">{location.name}</div>
            {location.description && (
              <div className="text-xs text-secondary">{location.description}</div>
            )}
          </div>

          {isContainer && (
            <div className="flex items-center gap-2">
              <span className="text-xs text-secondary">{location.slot_count} slots</span>
              <ChevronRight className="w-4 h-4 text-secondary" />
            </div>
          )}
        </button>

        {hasChildren && (
          <div className="ml-4 mt-1 space-y-1">
            {children.map((child) => renderLocationItem(child, depth + 1))}
          </div>
        )}
      </div>
    )
  }

  return (
    <div className={className}>
      <label className="text-sm font-medium text-primary">
        {label}
        {required && <span className="text-red-500 ml-1">*</span>}
      </label>

      {/* Selected Location Display */}
      {(selectedLocation || selectedSlot) && (
        <div className="mt-2 p-3 bg-primary/10 border border-primary/20 rounded-lg">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              {selectedLocation?.emoji && (
                <span className="text-xl">{selectedLocation.emoji}</span>
              )}
              <div>
                <div className="font-medium text-sm">
                  {selectedLocation?.name}
                  {selectedSlot && (
                    <>
                      <ChevronRight className="inline w-4 h-4 mx-1" />
                      {selectedSlot.name}
                    </>
                  )}
                </div>
                {selectedSlot?.slot_metadata && (
                  <div className="text-xs text-secondary">
                    {selectedSlot.slot_metadata.row !== undefined && `Row ${selectedSlot.slot_metadata.row}`}
                    {selectedSlot.slot_metadata.column !== undefined && `, Col ${selectedSlot.slot_metadata.column}`}
                  </div>
                )}
              </div>
            </div>
            <button
              onClick={handleClear}
              disabled={disabled}
              className="btn btn-ghost btn-sm"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        </div>
      )}

      {/* Location Selection UI */}
      {!selectedLocation && !selectedSlot && (
        <div className="mt-2 space-y-3">
          {/* Search */}
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-secondary" />
            <input
              type="text"
              placeholder="Search locations..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              disabled={disabled}
              className="input w-full pl-9"
            />
          </div>

          {/* Location List */}
          <div className="border rounded-lg p-2 max-h-64 overflow-y-auto space-y-1">
            {loading ? (
              <div className="flex items-center justify-center py-8">
                <Loader2 className="w-6 h-6 animate-spin text-secondary" />
              </div>
            ) : rootLocations.length === 0 ? (
              <div className="text-center py-8 text-secondary">
                {searchTerm ? 'No locations found' : 'No locations available'}
              </div>
            ) : (
              rootLocations.map((location) => renderLocationItem(location))
            )}
          </div>
        </div>
      )}

      {error && <p className="text-sm text-red-600 dark:text-red-400 mt-1">{error}</p>}

      {/* Slot Selector Modal */}
      {containerForSlotSelection && (
        <SlotSelector
          container={containerForSlotSelection}
          isOpen={slotSelectorOpen}
          onClose={() => setSlotSelectorOpen(false)}
          onSelectSlot={handleSlotSelect}
          selectedSlotId={selectedSlot?.id}
        />
      )}
    </div>
  )
}
