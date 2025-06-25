import { useState, useEffect } from 'react'
import { Save, MapPin, Upload, X, Image } from 'lucide-react'
import Modal from '@/components/ui/Modal'
import FormField from '@/components/ui/FormField'
import EmojiPicker from '@/components/ui/EmojiPicker'
import LocationTreeSelector from '@/components/ui/LocationTreeSelector'
import { locationsService } from '@/services/locations.service'
import { utilityService } from '@/services/utility.service'
import { CreateLocationRequest, Location } from '@/types/locations'
import toast from 'react-hot-toast'

interface AddLocationModalProps {
  isOpen: boolean
  onClose: () => void
  onSuccess: () => void
}

const AddLocationModal = ({ isOpen, onClose, onSuccess }: AddLocationModalProps) => {
  const [formData, setFormData] = useState<CreateLocationRequest>({
    name: '',
    location_type: '',
    parent_id: ''
  })

  const [parentLocations, setParentLocations] = useState<Location[]>([])
  const [errors, setErrors] = useState<Record<string, string>>({})
  const [loading, setLoading] = useState(false)
  const [loadingData, setLoadingData] = useState(false)
  const [imageFile, setImageFile] = useState<File | null>(null)
  const [imagePreview, setImagePreview] = useState<string | null>(null)
  const [uploadingImage, setUploadingImage] = useState(false)
  const [selectedEmoji, setSelectedEmoji] = useState<string | null>(null)

  const locationTypes = [
    { value: 'warehouse', label: 'Warehouse' },
    { value: 'room', label: 'Room' },
    { value: 'shelf', label: 'Shelf' },
    { value: 'drawer', label: 'Drawer' },
    { value: 'bin', label: 'Bin' },
    { value: 'rack', label: 'Rack' },
    { value: 'cabinet', label: 'Cabinet' },
    { value: 'box', label: 'Box' },
    { value: 'other', label: 'Other' }
  ]

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

  const handleImageChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return

    // Validate file type
    if (!file.type.startsWith('image/')) {
      toast.error('Please select an image file')
      return
    }

    // Validate file size (5MB limit)
    if (file.size > 5 * 1024 * 1024) {
      toast.error('Image size must be less than 5MB')
      return
    }

    setImageFile(file)

    // Create preview
    const reader = new FileReader()
    reader.onload = (e) => {
      setImagePreview(e.target?.result as string)
    }
    reader.readAsDataURL(file)
  }

  const removeImage = () => {
    setImageFile(null)
    setImagePreview(null)
  }

  const validate = (): boolean => {
    const newErrors: Record<string, string> = {}

    if (!formData.name.trim()) {
      newErrors.name = 'Location name is required'
    }

    // Check for duplicate names at the same level
    const siblingLocations = formData.parent_id 
      ? parentLocations.filter(loc => loc.parent_id === formData.parent_id)
      : parentLocations.filter(loc => !loc.parent_id)
    
    if (siblingLocations.some(loc => loc.name.toLowerCase() === formData.name.toLowerCase().trim())) {
      newErrors.name = 'A location with this name already exists at this level'
    }

    setErrors(newErrors)
    return Object.keys(newErrors).length === 0
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    
    if (!validate()) {
      return
    }

    try {
      setLoading(true)

      // Handle image upload first if there's an image
      let imageUrl = ''
      if (imageFile) {
        try {
          setUploadingImage(true)
          const uploadResult = await utilityService.uploadImage(imageFile)
          imageUrl = `/utility/get_image/${uploadResult.image_id}.${imageFile.name.split('.').pop()}`
        } catch (error) {
          toast.error('Failed to upload image')
          return
        } finally {
          setUploadingImage(false)
        }
      }

      const submitData: CreateLocationRequest = {
        name: formData.name.trim(),
        location_type: formData.location_type || undefined,
        parent_id: formData.parent_id || undefined,
        image_url: imageUrl || undefined,
        emoji: selectedEmoji || undefined
      }

      await locationsService.createLocation(submitData)
      toast.success('Location created successfully')
      onSuccess()
      handleClose()
    } catch (error: any) {
      toast.error(error.response?.data?.message || 'Failed to create location')
    } finally {
      setLoading(false)
    }
  }

  const handleClose = () => {
    setFormData({
      name: '',
      location_type: '',
      parent_id: ''
    })
    setErrors({})
    setImageFile(null)
    setImagePreview(null)
    setSelectedEmoji(null)
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
    <Modal isOpen={isOpen} onClose={handleClose} title="Add New Location" size="md">
      {loadingData ? (
        <div className="text-center py-8">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary mx-auto"></div>
          <p className="text-secondary mt-2">Loading...</p>
        </div>
      ) : (
        <form onSubmit={handleSubmit} className="space-y-6">
          <FormField label="Location Name" required error={errors.name}>
            <input
              type="text"
              className="input w-full"
              value={formData.name}
              onChange={(e) => setFormData({ ...formData, name: e.target.value })}
              placeholder="Enter location name"
            />
          </FormField>

          <FormField label="Location Type" description="What type of storage location is this?">
            <select
              className="input w-full"
              value={formData.location_type}
              onChange={(e) => setFormData({ ...formData, location_type: e.target.value })}
            >
              <option value="">Select a type</option>
              {locationTypes.map((type) => (
                <option key={type.value} value={type.value}>
                  {type.label}
                </option>
              ))}
            </select>
          </FormField>

          <LocationTreeSelector
            selectedLocationId={formData.parent_id}
            onLocationSelect={(locationId) => setFormData({ ...formData, parent_id: locationId || '' })}
            label="Parent Location"
            description="Select a parent location to create a hierarchy (optional)"
            showAddButton={false}
            compact={true}
          />

          {/* Preview of full path */}
          {formData.parent_id && (
            <div className="p-3 bg-background-secondary rounded-md">
              <p className="text-sm text-secondary mb-1">Full path will be:</p>
              <p className="text-sm font-medium text-primary">
                {(() => {
                  const parent = parentLocations.find(loc => loc.id === formData.parent_id)
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
                    return buildPath(parent) + ' → ' + (formData.name || '[New Location]')
                  }
                  return formData.name || '[New Location]'
                })()}
              </p>
            </div>
          )}

          {/* Image Upload */}
          <FormField label="Location Image" description="Add an image to help identify this location (optional)">
            <div className="space-y-4">
              {imagePreview ? (
                <div className="relative inline-block">
                  <img
                    src={imagePreview}
                    alt="Location preview"
                    className="w-32 h-32 object-cover rounded-lg border border-border"
                  />
                  <button
                    type="button"
                    onClick={removeImage}
                    className="absolute -top-2 -right-2 bg-destructive text-destructive-foreground rounded-full p-1 hover:bg-destructive/90 transition-colors"
                    disabled={uploadingImage}
                  >
                    <X className="w-4 h-4" />
                  </button>
                </div>
              ) : (
                <div className="border-2 border-dashed border-border rounded-lg p-6 text-center hover:border-primary/50 transition-colors">
                  <input
                    type="file"
                    accept="image/*"
                    onChange={handleImageChange}
                    className="hidden"
                    id="location-image-upload"
                    disabled={uploadingImage}
                  />
                  <label
                    htmlFor="location-image-upload"
                    className="cursor-pointer flex flex-col items-center gap-2"
                  >
                    {uploadingImage ? (
                      <>
                        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
                        <span className="text-sm text-secondary">Uploading...</span>
                      </>
                    ) : (
                      <>
                        <Upload className="w-8 h-8 text-secondary" />
                        <span className="text-sm text-primary">Click to upload an image</span>
                        <span className="text-xs text-secondary">PNG, JPG, GIF up to 5MB</span>
                      </>
                    )}
                  </label>
                </div>
              )}
            </div>
          </FormField>

          {/* Emoji Picker */}
          <FormField label="Location Emoji" description="Choose an emoji to help identify this location (optional)">
            <EmojiPicker
              value={selectedEmoji || undefined}
              onChange={setSelectedEmoji}
              placeholder="Click to select an emoji..."
            />
          </FormField>

          {/* Actions */}
          <div className="flex justify-end gap-3 pt-4 border-t border-border">
            <button
              type="button"
              onClick={handleClose}
              className="btn btn-secondary"
              disabled={loading}
            >
              Cancel
            </button>
            <button
              type="submit"
              className="btn btn-primary flex items-center gap-2"
              disabled={loading}
            >
              {loading ? (
                <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
              ) : (
                <Save className="w-4 h-4" />
              )}
              {loading ? 'Creating...' : 'Create Location'}
            </button>
          </div>
        </form>
      )}
    </Modal>
  )
}

export default AddLocationModal