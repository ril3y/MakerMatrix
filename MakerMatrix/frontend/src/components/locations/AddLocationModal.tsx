import { useState, useEffect } from 'react'
import CrudModal from '@/components/ui/CrudModal'
import { FormInput, FormField, LocationTreeSelector } from '@/components/forms'
import { CustomSelect } from '@/components/ui/CustomSelect'
import EmojiPicker from '@/components/ui/EmojiPicker'
import ImageUpload from '@/components/ui/ImageUpload'
import { useModalFormWithValidation } from '@/hooks/useFormWithValidation'
import { locationFormSchema, type LocationFormData } from '@/schemas/locations'
import { locationsService } from '@/services/locations.service'
import { Location } from '@/types/locations'
import toast from 'react-hot-toast'

interface AddLocationModalProps {
  isOpen: boolean
  onClose: () => void
  onSuccess: () => void
}

const AddLocationModal = ({ isOpen, onClose, onSuccess }: AddLocationModalProps) => {
  const [parentLocations, setParentLocations] = useState<Location[]>([])
  const [loadingData, setLoadingData] = useState(false)
  const [imageUrl, setImageUrl] = useState<string>('')

  const locationTypes = [
    { value: 'standard', label: 'Standard' },
    { value: 'warehouse', label: 'Warehouse' },
    { value: 'room', label: 'Room' },
    { value: 'shelf', label: 'Shelf' },
    { value: 'drawer', label: 'Drawer' },
    { value: 'bin', label: 'Bin' },
    { value: 'cabinet', label: 'Cabinet' },
    { value: 'building', label: 'Building' }
  ]

  // Form with validation
  const form = useModalFormWithValidation<LocationFormData>({
    schema: locationFormSchema,
    isOpen,
    onClose,
    defaultValues: {
      name: '',
      description: '',
      location_type: 'standard',
      parent_id: undefined,
      image_url: undefined,
      emoji: undefined,
      image_file: undefined,
    },
    onSubmit: handleFormSubmit,
    onSuccess: () => {
      onSuccess()
      handleClose()
    },
    successMessage: 'Location created successfully',
    transformData: (data) => {
      // Transform form data to API format
      const { image_file, ...apiData } = data
      return {
        ...apiData,
        name: data.name.trim(),
        parent_id: data.parent_id || undefined,
        location_type: data.location_type || 'standard',
      }
    },
  })

  useEffect(() => {
    if (isOpen) {
      loadParentLocations()
    }
  }, [isOpen])

  const loadParentLocations = async () => {
    try {
      setLoadingData(true)
      const locations = await locationsService.getAllLocations()
      setParentLocations(locations)
    } catch (error) {
      toast.error('Failed to load parent locations')
    } finally {
      setLoadingData(false)
    }
  }

  // Handle form submission
  async function handleFormSubmit(data: LocationFormData) {
    // Check for duplicate names at the same level
    const siblingLocations = data.parent_id
      ? parentLocations.filter(loc => loc.parent_id === data.parent_id)
      : parentLocations.filter(loc => !loc.parent_id)

    if (siblingLocations.some(loc => loc.name.toLowerCase() === data.name.toLowerCase().trim())) {
      throw new Error('A location with this name already exists at this level')
    }

    // Create location with image URL
    const locationData = {
      ...data,
      name: data.name.trim(),
      parent_id: data.parent_id || undefined,
      location_type: data.location_type || 'standard',
      image_url: imageUrl || undefined,
    }

    return await locationsService.createLocation(locationData)
  }


  const handleClose = () => {
    setImageUrl('')
    form.reset()
    onClose()
  }

  // Build hierarchical display for parent locations
  const buildLocationHierarchy = (locations: Location[]): Array<{id: string, name: string, level: number}> => {
    const result: Array<{id: string, name: string, level: number}> = []
    
    // Create a map for quick lookup
    const locationMap = new Map<string, Location>()
    locations.forEach(loc => locationMap.set(loc.id, loc))
    
    const addLocation = (location: Location, level: number = 0) => {
      result.push({
        id: location.id,
        name: location.name,
        level
      })
      
      // Find children in the flat list
      const children = locations.filter(loc => loc.parent_id === location.id)
      children
        .sort((a, b) => a.name.localeCompare(b.name)) // Sort alphabetically
        .forEach(child => addLocation(child, level + 1))
    }

    // Start with root locations (no parent) and sort them
    const rootLocations = locations
      .filter(loc => !loc.parent_id)
      .sort((a, b) => a.name.localeCompare(b.name))
    
    rootLocations.forEach(loc => addLocation(loc))

    return result
  }

  const hierarchicalLocations = buildLocationHierarchy(parentLocations)

  return (
    <CrudModal
      isOpen={isOpen}
      onClose={handleClose}
      title="Add New Location"
      size="md"
      mode="create"
      onSubmit={form.onSubmit}
      loading={form.loading}
      loadingText="Creating..."
      submitText="Create Location"
    >
      {loadingData ? (
        <div className="text-center py-8">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary mx-auto"></div>
          <p className="text-theme-secondary mt-2">Loading...</p>
        </div>
      ) : (
        <>
          <FormInput
            label="Location Name"
            placeholder="Enter location name"
            required
            registration={form.register('name')}
            error={form.getFieldError('name')}
          />

          <FormField
            label="Location Type"
            description="What type of storage location is this?"
            error={form.getFieldError('location_type')}
          >
            <CustomSelect
              value={form.watch('location_type') || 'standard'}
              onChange={(value) => form.setValue('location_type', value)}
              options={locationTypes}
              placeholder="Select a type"
              error={form.getFieldError('location_type')}
            />
          </FormField>

          <FormField label="Parent Location" description="Select a parent location to create a hierarchy (optional)">
            <LocationTreeSelector
              selectedLocationId={form.watch('parent_id')}
              onLocationSelect={(locationId) => form.setValue('parent_id', locationId || undefined)}
              showAddButton={false}
              compact={true}
            />
          </FormField>

          {/* Preview of full path */}
          {form.watch('parent_id') && (
            <div className="p-3 bg-theme-secondary rounded-md border border-theme-primary">
              <p className="text-sm text-theme-muted mb-1">Full path will be:</p>
              <p className="text-sm font-medium text-theme-primary">
                {(() => {
                  const parent = parentLocations.find(loc => loc.id === form.watch('parent_id'))
                  if (parent) {
                    // Build full path from flat list
                    const buildPath = (loc: Location): string => {
                      if (loc.parent_id) {
                        const parentLoc = parentLocations.find(p => p.id === loc.parent_id)
                        if (parentLoc) {
                          return buildPath(parentLoc) + ' → ' + loc.name
                        }
                      }
                      return loc.name
                    }
                    return buildPath(parent) + ' → ' + (form.watch('name') || '[New Location]')
                  }
                  return form.watch('name') || '[New Location]'
                })()}
              </p>
            </div>
          )}

          {/* Image Upload */}
          <FormField label="Location Image" description="Upload, drag & drop, or paste an image to help identify this location (max 5MB)">
            <ImageUpload
              onImageUploaded={setImageUrl}
              currentImageUrl={imageUrl}
              placeholder="Upload location image"
              className="w-full"
            />
          </FormField>

          {/* Emoji Picker */}
          <FormField label="Location Emoji" description="Choose an emoji to help identify this location (optional)">
            <EmojiPicker
              value={form.watch('emoji') || undefined}
              onChange={(emoji) => form.setValue('emoji', emoji)}
              placeholder="Click to select an emoji..."
            />
          </FormField>
        </>
      )}
    </CrudModal>
  )
}

export default AddLocationModal