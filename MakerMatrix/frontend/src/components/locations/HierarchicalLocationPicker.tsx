import { useState, useEffect } from 'react'
import { ChevronRight, Box, MapPin } from 'lucide-react'
import { CustomSelect } from '@/components/ui/CustomSelect'
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

  const handleLocationSelect = (locationId: string) => {
    const location = locations.find((loc) => loc.id === locationId)
    if (!location) return

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

  // Build location options for CustomSelect
  const locationOptions = locations.map((loc) => {
    const isContainer = loc.slot_count && loc.slot_count > 0
    let label = loc.name
    if (isContainer) {
      label = `${loc.name} (${loc.slot_count} slots)`
    }

    return {
      value: loc.id,
      label: label,
      image_url: loc.emoji ? undefined : loc.image_url || undefined,
    }
  })

  // Get current display value for CustomSelect
  const currentValue = selectedSlot?.id || selectedLocation?.id || ''

  // Display label showing selected location/slot
  const displayLabel = (() => {
    if (selectedSlot && selectedLocation) {
      return `${selectedLocation.name} → ${selectedSlot.name}`
    }
    if (selectedLocation) {
      return selectedLocation.name
    }
    return ''
  })()

  return (
    <div className={className}>
      <label className="text-sm font-medium text-primary block mb-2">
        {label}
        {required && <span className="text-red-500 ml-1">*</span>}
      </label>

      {/* Show selected path if slot is selected */}
      {selectedSlot && selectedLocation && (
        <div className="mb-2 p-3 bg-primary/10 border border-primary/20 rounded-lg">
          <div className="flex items-center gap-2 text-sm">
            {selectedLocation.emoji && <span className="text-xl">{selectedLocation.emoji}</span>}
            <Box className="w-4 h-4 text-primary" />
            <span className="font-medium">{selectedLocation.name}</span>
            <ChevronRight className="w-4 h-4 text-secondary" />
            <MapPin className="w-4 h-4 text-primary" />
            <span className="font-medium">{selectedSlot.name}</span>
            {selectedSlot.slot_metadata && (
              <span className="text-xs text-secondary">
                {selectedSlot.slot_metadata.row !== undefined &&
                  `Row ${selectedSlot.slot_metadata.row}`}
                {selectedSlot.slot_metadata.column !== undefined &&
                  `, Col ${selectedSlot.slot_metadata.column}`}
              </span>
            )}
          </div>
        </div>
      )}

      {/* CustomSelect for location picker */}
      <CustomSelect
        value={currentValue}
        onChange={handleLocationSelect}
        options={locationOptions}
        placeholder="Select location..."
        searchable={true}
        searchPlaceholder="Search locations..."
        disabled={disabled || loading}
        error={error}
      />

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
