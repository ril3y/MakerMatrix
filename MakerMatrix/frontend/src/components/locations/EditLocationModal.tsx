import { useState, useEffect } from 'react'
import { MapPin, AlertCircle, Upload, X, Save } from 'lucide-react'
import Modal from '@/components/ui/Modal'
import FormField from '@/components/ui/FormField'
import EmojiPicker from '@/components/ui/EmojiPicker'
import { locationsService } from '@/services/locations.service'
import { utilityService } from '@/services/utility.service'
import { Location, UpdateLocationRequest } from '@/types/locations'
import toast from 'react-hot-toast'

interface EditLocationModalProps {
  isOpen: boolean
  onClose: () => void
  onSuccess: () => void
  location: Location
}

const EditLocationModal: React.FC<EditLocationModalProps> = ({ 
  isOpen, 
  onClose, 
  onSuccess,
  location 
}) => {
  const [formData, setFormData] = useState<UpdateLocationRequest>({
    id: location.id,
    name: location.name,
    description: location.description || '',
    location_type: location.location_type || 'General',
    parent_id: location.parent_id || undefined
  })
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [locations, setLocations] = useState<Location[]>([])
  const [nameError, setNameError] = useState<string | null>(null)
  const [imageFile, setImageFile] = useState<File | null>(null)
  const [imagePreview, setImagePreview] = useState<string | null>(null)
  const [uploadingImage, setUploadingImage] = useState(false)
  const [imageChanged, setImageChanged] = useState(false)
  const [selectedEmoji, setSelectedEmoji] = useState<string | null>(null)
  const [emojiChanged, setEmojiChanged] = useState(false)

  useEffect(() => {
    if (isOpen) {
      loadLocations()
      // Reset form when modal opens with new location
      setFormData({
        id: location.id,
        name: location.name,
        description: location.description || '',
        location_type: location.location_type || 'General',
        parent_id: location.parent_id || undefined
      })
      setError(null)
      setNameError(null)
      // Reset image state
      setImageFile(null)
      setImagePreview(location.image_url || null)
      setImageChanged(false)
      // Reset emoji state
      setSelectedEmoji(location.emoji || null)
      setEmojiChanged(false)
    }
  }, [isOpen, location])

  const loadLocations = async () => {
    try {
      const data = await locationsService.getAllLocations()
      // Filter out the current location and its descendants
      const descendantIds = locationsService.getDescendantIds(location)
      const validLocations = data.filter(loc => 
        loc.id !== location.id && !descendantIds.includes(loc.id)
      )
      setLocations(validLocations)
    } catch (err) {
      console.error('Failed to load locations:', err)
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
    setImageChanged(true)

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
    setImageChanged(true)
  }

  const handleEmojiChange = (emoji: string | null) => {
    setSelectedEmoji(emoji)
    setEmojiChanged(true)
  }

  const validateName = async (name: string) => {
    if (!name.trim()) {
      setNameError('Location name is required')
      return false
    }

    if (name.trim().length < 2) {
      setNameError('Location name must be at least 2 characters')
      return false
    }

    // Check if name already exists (excluding current location)
    const exists = await locationsService.checkNameExists(name, formData.parent_id || undefined, location.id)
    if (exists) {
      setNameError('A location with this name already exists in the same parent location')
      return false
    }

    setNameError(null)
    return true
  }

  const handleNameChange = (name: string) => {
    setFormData({ ...formData, name })
    if (nameError) {
      validateName(name)
    }
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    
    const isValid = await validateName(formData.name)
    if (!isValid) return

    setLoading(true)
    setError(null)

    try {
      // Handle image upload if image was changed
      let imageUrl = imagePreview
      if (imageChanged) {
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
        } else {
          // Image was removed
          imageUrl = null
        }
      }

      const updateData: UpdateLocationRequest = {
        ...formData,
        image_url: imageUrl || undefined,
        emoji: emojiChanged ? (selectedEmoji || undefined) : undefined
      }

      await locationsService.updateLocation(updateData)
      toast.success('Location updated successfully')
      onSuccess()
      onClose()
    } catch (err: any) {
      setError(err.response?.data?.error || 'Failed to update location')
    } finally {
      setLoading(false)
    }
  }

  // Build hierarchical display for parent locations
  const buildLocationHierarchy = (locations: Location[]): Array<{id: string, name: string, level: number}> => {
    const result: Array<{id: string, name: string, level: number}> = []
    
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

  const hierarchicalLocations = buildLocationHierarchy(locations)

  return (
    <Modal isOpen={isOpen} onClose={onClose} title="Edit Location">
      <form onSubmit={handleSubmit} className="space-y-4">
        {error && (
          <div className="bg-red-500/10 border border-red-500/50 rounded p-3 flex items-center gap-2">
            <AlertCircle className="w-4 h-4 text-red-500" />
            <p className="text-red-500 text-sm">{error}</p>
          </div>
        )}

        <FormField
          label="Location Name"
          required
          error={nameError}
        >
          <input
            type="text"
            value={formData.name}
            onChange={(e) => handleNameChange(e.target.value)}
            onBlur={() => validateName(formData.name)}
            className="input w-full"
            placeholder="e.g., Warehouse A, Shelf 1"
            autoFocus
          />
        </FormField>

        <FormField label="Location Type">
          <select
            value={formData.location_type}
            onChange={(e) => setFormData({ ...formData, location_type: e.target.value })}
            className="input w-full"
          >
            <option value="General">General</option>
            <option value="Warehouse">Warehouse</option>
            <option value="Room">Room</option>
            <option value="Shelf">Shelf</option>
            <option value="Bin">Bin</option>
            <option value="Drawer">Drawer</option>
            <option value="Box">Box</option>
          </select>
        </FormField>

        <FormField label="Parent Location">
          <select
            value={formData.parent_id || ''}
            onChange={(e) => setFormData({ ...formData, parent_id: e.target.value || undefined })}
            className="input w-full"
          >
            <option value="">No parent (root location)</option>
            {hierarchicalLocations.map((location) => (
              <option key={location.id} value={location.id}>
                {'  '.repeat(location.level)}
                {location.level > 0 && '└ '}
                {location.name}
              </option>
            ))}
          </select>
        </FormField>

        <FormField label="Description">
          <textarea
            value={formData.description}
            onChange={(e) => setFormData({ ...formData, description: e.target.value })}
            className="input w-full min-h-[80px]"
            placeholder="Optional description of this location"
            rows={3}
          />
        </FormField>

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
                {imageChanged && (
                  <div className="absolute -bottom-2 left-1/2 transform -translate-x-1/2">
                    <span className="bg-orange-500 text-white text-xs px-2 py-1 rounded">Modified</span>
                  </div>
                )}
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
            onChange={handleEmojiChange}
            placeholder="Click to select an emoji..."
          />
          {emojiChanged && (
            <div className="mt-2">
              <span className="bg-orange-500 text-white text-xs px-2 py-1 rounded">Modified</span>
            </div>
          )}
        </FormField>

        <div className="flex justify-end gap-3 pt-4">
          <button
            type="button"
            onClick={onClose}
            className="btn btn-secondary"
            disabled={loading}
          >
            Cancel
          </button>
          <button
            type="submit"
            className="btn btn-primary flex items-center gap-2"
            disabled={loading || !!nameError}
          >
            <MapPin className="w-4 h-4" />
            {loading ? 'Updating...' : 'Update Location'}
          </button>
        </div>
      </form>
    </Modal>
  )
}

export default EditLocationModal