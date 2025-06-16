import { useState, useEffect } from 'react'
import { Save, MapPin } from 'lucide-react'
import Modal from '@/components/ui/Modal'
import FormField from '@/components/ui/FormField'
import { locationsService } from '@/services/locations.service'
import { CreateLocationRequest, Location } from '@/types/parts'
import toast from 'react-hot-toast'

interface AddLocationModalProps {
  isOpen: boolean
  onClose: () => void
  onSuccess: () => void
}

const AddLocationModal = ({ isOpen, onClose, onSuccess }: AddLocationModalProps) => {
  const [formData, setFormData] = useState<CreateLocationRequest>({
    name: '',
    type: '',
    parent_id: ''
  })

  const [parentLocations, setParentLocations] = useState<Location[]>([])
  const [errors, setErrors] = useState<Record<string, string>>({})
  const [loading, setLoading] = useState(false)
  const [loadingData, setLoadingData] = useState(false)

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

      const submitData: CreateLocationRequest = {
        name: formData.name.trim(),
        type: formData.type || undefined,
        parent_id: formData.parent_id || undefined
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
      type: '',
      parent_id: ''
    })
    setErrors({})
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
              value={formData.type}
              onChange={(e) => setFormData({ ...formData, type: e.target.value })}
            >
              <option value="">Select a type</option>
              {locationTypes.map((type) => (
                <option key={type.value} value={type.value}>
                  {type.label}
                </option>
              ))}
            </select>
          </FormField>

          <FormField 
            label="Parent Location" 
            description="Select a parent location to create a hierarchy (optional)"
          >
            <select
              className="input w-full"
              value={formData.parent_id}
              onChange={(e) => setFormData({ ...formData, parent_id: e.target.value })}
            >
              <option value="">No parent (root level)</option>
              {hierarchicalLocations.map((location) => (
                <option key={location.id} value={location.id}>
                  {'  '.repeat(location.level)}
                  {location.level > 0 && '└ '}
                  {location.name}
                </option>
              ))}
            </select>
          </FormField>

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