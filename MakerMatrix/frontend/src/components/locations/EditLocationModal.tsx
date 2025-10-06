import { useState, useEffect } from 'react'
import { MapPin, AlertCircle, Save } from 'lucide-react'
import Modal from '@/components/ui/Modal'
import FormField from '@/components/ui/FormField'
import { CustomSelect } from '@/components/ui/CustomSelect'
import EmojiPicker from '@/components/ui/EmojiPicker'
import ImageUpload from '@/components/ui/ImageUpload'
import { locationsService } from '@/services/locations.service'
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
  const locationTypes = [
    { value: 'standard', label: 'Standard' },
    { value: 'warehouse', label: 'Warehouse' },
    { value: 'toolbox', label: 'Toolbox' },
    { value: 'room', label: 'Room' },
    { value: 'shelf', label: 'Shelf' },
    { value: 'drawer', label: 'Drawer' },
    { value: 'bin', label: 'Bin' },
    { value: 'cabinet', label: 'Cabinet' },
    { value: 'building', label: 'Building' }
  ]

  const [formData, setFormData] = useState<UpdateLocationRequest>({
    id: location.id,
    name: location.name,
    description: location.description || '',
    location_type: location.location_type || 'standard',
    parent_id: location.parent_id || undefined
  })
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [locations, setLocations] = useState<Location[]>([])
  const [nameError, setNameError] = useState<string | null>(null)
  const [imageUrl, setImageUrl] = useState<string>('')
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
        location_type: location.location_type || 'standard',
        parent_id: location.parent_id || undefined
      })
      setError(null)
      setNameError(null)
      // Reset image state
      setImageUrl(location.image_url || '')
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

  const handleImageUploaded = (url: string) => {
    setImageUrl(url)
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
      const updateData: UpdateLocationRequest = {
        ...formData
      }

      // Only include image_url if it was changed
      if (imageChanged) {
        updateData.image_url = imageUrl || null
      }

      // Only include emoji if it was changed
      if (emojiChanged) {
        updateData.emoji = selectedEmoji || null
      }

      console.log('[DEBUG] emojiChanged:', emojiChanged)
      console.log('[DEBUG] selectedEmoji:', selectedEmoji)
      console.log('[DEBUG] Update data being sent:', updateData)

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

        <FormField label="Location Type" description="Select from common types or create a custom type">
          <CustomSelect
            value={formData.location_type || 'standard'}
            onChange={(value) => setFormData({ ...formData, location_type: value })}
            options={locationTypes}
            placeholder="Select or type a custom type"
            searchPlaceholder="Type to search or create custom type..."
            allowCustom={true}
            customLabel="Create custom type"
          />
        </FormField>

        <FormField label="Parent Location">
          <CustomSelect
            value={formData.parent_id || ''}
            onChange={(value) => setFormData({ ...formData, parent_id: value || undefined })}
            options={[
              { value: '', label: 'No parent (root location)' },
              ...hierarchicalLocations.map((loc) => ({
                value: loc.id,
                label: `${'  '.repeat(loc.level)}${loc.level > 0 ? '└ ' : ''}${loc.name}`
              }))
            ]}
            placeholder="Select parent location"
          />
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
        <FormField label="Location Image" description="Upload, drag & drop, or paste an image to help identify this location (max 5MB)">
          <ImageUpload
            onImageUploaded={handleImageUploaded}
            currentImageUrl={imageUrl}
            placeholder="Upload location image"
            className="w-full"
          />
          {imageChanged && imageUrl && (
            <div className="mt-2">
              <span className="bg-orange-500 text-white text-xs px-2 py-1 rounded">Modified - will update on save</span>
            </div>
          )}
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