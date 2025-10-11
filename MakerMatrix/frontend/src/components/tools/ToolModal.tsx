import { useState, useEffect } from 'react'
import { Save, Wrench, Plus, X, MapPin, Tag, Calendar, DollarSign } from 'lucide-react'
import Modal from '@/components/ui/Modal'
import FormField from '@/components/ui/FormField'
import ImageUpload from '@/components/ui/ImageUpload'
import { CustomSelect } from '@/components/ui/CustomSelect'
import LocationTreeSelector from '@/components/ui/LocationTreeSelector'
import { TooltipIcon } from '@/components/ui/Tooltip'
import AddCategoryModal from '@/components/categories/AddCategoryModal'
import AddLocationModal from '@/components/locations/AddLocationModal'
import { toolsService } from '@/services/tools.service'
import { locationsService } from '@/services/locations.service'
import { categoriesService } from '@/services/categories.service'
import type { Tool, CreateToolRequest, UpdateToolRequest, ToolCondition } from '@/types/tools'
import type { Location, Category } from '@/types/parts'
import toast from 'react-hot-toast'

interface ToolModalProps {
  isOpen: boolean
  onClose: () => void
  onSuccess: () => void
  editingTool?: Tool | null
}

const ToolModal = ({ isOpen, onClose, onSuccess, editingTool }: ToolModalProps) => {
  const [formData, setFormData] = useState<CreateToolRequest>({
    name: '',
    tool_number: '',
    description: '',
    manufacturer: '',
    model: '',
    serial_number: '',
    purchase_date: '',
    purchase_price: undefined,
    condition: 'good',
    location_id: '',
    category_id: '',
    last_maintenance: '',
    next_maintenance: '',
    maintenance_notes: '',
    image_url: '',
    manual_url: '',
    notes: '',
    additional_properties: {},
  })

  const [locations, setLocations] = useState<Location[]>([])
  const [categories, setCategories] = useState<Category[]>([])
  const [customProperties, setCustomProperties] = useState<Array<{ key: string; value: string }>>(
    []
  )
  const [errors, setErrors] = useState<Record<string, string>>({})
  const [loading, setLoading] = useState(false)
  const [loadingData, setLoadingData] = useState(false)
  const [imageUrl, setImageUrl] = useState<string>('')

  // Inline modal states
  const [showAddCategoryModal, setShowAddCategoryModal] = useState(false)
  const [showAddLocationModal, setShowAddLocationModal] = useState(false)
  const [isAdditionalPropsOpen, setIsAdditionalPropsOpen] = useState(false)

  const conditionOptions = [
    { value: 'new', label: 'New' },
    { value: 'good', label: 'Good' },
    { value: 'fair', label: 'Fair' },
    { value: 'poor', label: 'Poor' },
    { value: 'broken', label: 'Broken' },
  ]

  useEffect(() => {
    if (isOpen) {
      loadData()
      if (editingTool) {
        // Load existing tool data for editing
        setFormData({
          name: editingTool.name,
          tool_number: editingTool.tool_number || '',
          description: editingTool.description || '',
          manufacturer: editingTool.manufacturer || '',
          model: editingTool.model || '',
          serial_number: editingTool.serial_number || '',
          purchase_date: editingTool.purchase_date || '',
          purchase_price: editingTool.purchase_price,
          condition: editingTool.condition,
          location_id: editingTool.location_id || '',
          category_id: editingTool.category_id || '',
          last_maintenance: editingTool.last_maintenance || '',
          next_maintenance: editingTool.next_maintenance || '',
          maintenance_notes: editingTool.maintenance_notes || '',
          image_url: editingTool.image_url || '',
          manual_url: editingTool.manual_url || '',
          notes: editingTool.notes || '',
          additional_properties: editingTool.additional_properties || {},
        })
        setImageUrl(editingTool.image_url || '')

        // Load custom properties
        if (editingTool.additional_properties) {
          const props = Object.entries(editingTool.additional_properties).map(([key, value]) => ({
            key,
            value: String(value),
          }))
          setCustomProperties(props)
        }
      } else {
        // Clear form for new tool
        clearFormData()
      }
    }
  }, [isOpen, editingTool])

  const loadData = async () => {
    try {
      setLoadingData(true)
      const [locationsData, categoriesData] = await Promise.all([
        locationsService.getAllLocations(),
        categoriesService.getAllCategories(),
      ])
      setLocations(locationsData || [])
      setCategories(categoriesData || [])
    } catch (error) {
      console.error('Failed to load data:', error)
      toast.error('Failed to load data')
      setLocations([])
      setCategories([])
    } finally {
      setLoadingData(false)
    }
  }

  const validate = (): boolean => {
    const newErrors: Record<string, string> = {}

    if (!formData.name.trim()) {
      newErrors.name = 'Tool name is required'
    }

    if (formData.purchase_price !== undefined && formData.purchase_price < 0) {
      newErrors.purchase_price = 'Purchase price cannot be negative'
    }

    if (formData.manual_url && !isValidUrl(formData.manual_url)) {
      newErrors.manual_url = 'Please enter a valid URL'
    }

    // Date validation
    if (formData.purchase_date && formData.last_maintenance) {
      if (new Date(formData.last_maintenance) < new Date(formData.purchase_date)) {
        newErrors.last_maintenance = 'Last maintenance cannot be before purchase date'
      }
    }

    if (formData.last_maintenance && formData.next_maintenance) {
      if (new Date(formData.next_maintenance) < new Date(formData.last_maintenance)) {
        newErrors.next_maintenance = 'Next maintenance cannot be before last maintenance'
      }
    }

    setErrors(newErrors)
    return Object.keys(newErrors).length === 0
  }

  const isValidUrl = (url: string): boolean => {
    try {
      new URL(url)
      return true
    } catch {
      return false
    }
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()

    if (!validate()) {
      return
    }

    try {
      setLoading(true)

      // Prepare properties object
      const properties: Record<string, unknown> = {}
      customProperties.forEach(({ key, value }) => {
        if (key.trim() && value.trim()) {
          properties[key.trim()] = value.trim()
        }
      })

      const submitData = {
        ...formData,
        image_url: imageUrl || undefined,
        additional_properties: Object.keys(properties).length > 0 ? properties : undefined,
      }

      if (editingTool) {
        // Update existing tool
        await toolsService.updateTool(editingTool.id, submitData as UpdateToolRequest)
        toast.success('Tool updated successfully')
      } else {
        // Create new tool
        await toolsService.createTool(submitData)
        toast.success('Tool created successfully')
      }

      clearFormData()
      onSuccess()
      handleClose()
    } catch (error: any) {
      console.error('Failed to save tool:', error)
      const errorMessage =
        error.response?.data?.detail ||
        error.response?.data?.message ||
        error.message ||
        'Failed to save tool'
      toast.error(errorMessage)
    } finally {
      setLoading(false)
    }
  }

  const handleClose = () => {
    setShowAddCategoryModal(false)
    setShowAddLocationModal(false)
    onClose()
  }

  const clearFormData = () => {
    setFormData({
      name: '',
      tool_number: '',
      description: '',
      manufacturer: '',
      model: '',
      serial_number: '',
      purchase_date: '',
      purchase_price: undefined,
      condition: 'good',
      location_id: '',
      category_id: '',
      last_maintenance: '',
      next_maintenance: '',
      maintenance_notes: '',
      image_url: '',
      manual_url: '',
      notes: '',
      additional_properties: {},
    })
    setCustomProperties([])
    setErrors({})
    setImageUrl('')
  }

  const addCustomProperty = () => {
    setCustomProperties([...customProperties, { key: '', value: '' }])
    setIsAdditionalPropsOpen(true)
  }

  const updateCustomProperty = (index: number, field: 'key' | 'value', value: string) => {
    const updated = [...customProperties]
    updated[index][field] = value
    setCustomProperties(updated)
  }

  const removeCustomProperty = (index: number) => {
    setCustomProperties(customProperties.filter((_, i) => i !== index))
  }

  const handleCategoryCreated = async () => {
    try {
      const categoriesData = await categoriesService.getAllCategories()
      setCategories(categoriesData || [])

      if (categoriesData && categoriesData.length > 0) {
        const sortedCategories = categoriesData.sort(
          (a, b) => new Date(b.created_at || 0).getTime() - new Date(a.created_at || 0).getTime()
        )
        const newestCategory = sortedCategories[0]
        setFormData({ ...formData, category_id: newestCategory.id })
      }
    } catch (error) {
      console.error('Failed to reload categories:', error)
    }
    setShowAddCategoryModal(false)
  }

  const handleLocationCreated = async () => {
    try {
      const locationsData = await locationsService.getAllLocations()
      setLocations(locationsData || [])

      if (locationsData && locationsData.length > 0) {
        const sortedLocations = locationsData.sort(
          (a, b) => new Date(b.created_at || 0).getTime() - new Date(a.created_at || 0).getTime()
        )
        const newestLocation = sortedLocations[0]
        setFormData({ ...formData, location_id: newestLocation.id })
      }
    } catch (error) {
      console.error('Failed to reload locations:', error)
    }
    setShowAddLocationModal(false)
  }

  return (
    <Modal
      isOpen={isOpen}
      onClose={handleClose}
      title={editingTool ? 'Edit Tool' : 'Add New Tool'}
      size="xl"
    >
      {loadingData ? (
        <div className="text-center py-8">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary mx-auto"></div>
          <p className="text-secondary mt-2">Loading...</p>
        </div>
      ) : (
        <form onSubmit={handleSubmit} className="space-y-4">
          {/* Row 1: Basic Info */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 p-4 bg-primary/5 rounded-lg border border-primary/10">
            <FormField label="Tool Name" required error={errors.name}>
              <input
                type="text"
                className="input w-full"
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                placeholder="Enter tool name"
              />
            </FormField>

            <FormField label="Tool Number" error={errors.tool_number}>
              <input
                type="text"
                className="input w-full"
                value={formData.tool_number}
                onChange={(e) => setFormData({ ...formData, tool_number: e.target.value })}
                placeholder="Enter tool number"
              />
            </FormField>

            <FormField label="Condition" required>
              <select
                className="input w-full"
                value={formData.condition}
                onChange={(e) => setFormData({ ...formData, condition: e.target.value as ToolCondition })}
              >
                {conditionOptions.map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
            </FormField>
          </div>

          {/* Row 2: Manufacturer and Model */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 p-4 bg-primary/5 rounded-lg border border-primary/10">
            <FormField label="Manufacturer">
              <input
                type="text"
                className="input w-full"
                value={formData.manufacturer}
                onChange={(e) => setFormData({ ...formData, manufacturer: e.target.value })}
                placeholder="Enter manufacturer"
              />
            </FormField>

            <FormField label="Model">
              <input
                type="text"
                className="input w-full"
                value={formData.model}
                onChange={(e) => setFormData({ ...formData, model: e.target.value })}
                placeholder="Enter model"
              />
            </FormField>

            <FormField label="Serial Number">
              <input
                type="text"
                className="input w-full"
                value={formData.serial_number}
                onChange={(e) => setFormData({ ...formData, serial_number: e.target.value })}
                placeholder="Enter serial number"
              />
            </FormField>
          </div>

          {/* Row 3: Purchase Info */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 p-4 bg-primary/5 rounded-lg border border-primary/10">
            <FormField label="Purchase Date">
              <input
                type="date"
                className="input w-full"
                value={formData.purchase_date}
                onChange={(e) => setFormData({ ...formData, purchase_date: e.target.value })}
              />
            </FormField>

            <FormField label="Purchase Price" error={errors.purchase_price}>
              <div className="flex items-center gap-2">
                <DollarSign className="w-4 h-4 text-muted" />
                <input
                  type="number"
                  step="0.01"
                  min="0"
                  className="input w-full"
                  value={formData.purchase_price || ''}
                  onChange={(e) => setFormData({
                    ...formData,
                    purchase_price: e.target.value ? parseFloat(e.target.value) : undefined
                  })}
                  placeholder="0.00"
                />
              </div>
            </FormField>
          </div>

          {/* Row 4: Maintenance Info */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 p-4 bg-primary/5 rounded-lg border border-primary/10">
            <FormField
              label="Last Maintenance"
              error={errors.last_maintenance}
            >
              <input
                type="date"
                className="input w-full"
                value={formData.last_maintenance}
                onChange={(e) => setFormData({ ...formData, last_maintenance: e.target.value })}
              />
            </FormField>

            <FormField
              label={
                <div className="flex items-center gap-1">
                  <span>Next Maintenance</span>
                  <TooltipIcon
                    variant="help"
                    position="top"
                    tooltip="Schedule the next maintenance date for this tool"
                  />
                </div>
              }
              error={errors.next_maintenance}
            >
              <input
                type="date"
                className="input w-full"
                value={formData.next_maintenance}
                onChange={(e) => setFormData({ ...formData, next_maintenance: e.target.value })}
              />
            </FormField>

            <FormField label="Maintenance Notes">
              <input
                type="text"
                className="input w-full"
                value={formData.maintenance_notes}
                onChange={(e) => setFormData({ ...formData, maintenance_notes: e.target.value })}
                placeholder="Maintenance details"
              />
            </FormField>
          </div>

          {/* Row 5: Location and Category */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 p-4 bg-primary/5 rounded-lg border border-primary/10">
            <div className="space-y-2">
              <label className="text-sm font-medium text-primary">Location</label>
              <div className="relative">
                <LocationTreeSelector
                  selectedLocationId={formData.location_id}
                  onLocationSelect={(locationId) =>
                    setFormData({ ...formData, location_id: locationId || '' })
                  }
                  description="Storage location"
                  error={errors.location_id}
                  showAddButton={false}
                  compact={true}
                  showLabel={false}
                />
                <button
                  type="button"
                  onClick={() => setShowAddLocationModal(true)}
                  className="absolute top-2 right-2 p-1.5 rounded-md bg-primary/10 hover:bg-primary/20 transition-colors border border-primary/30"
                  disabled={loading}
                  title="Add new location"
                >
                  <Plus className="w-4 h-4 text-primary" />
                </button>
              </div>
            </div>

            <div className="space-y-2">
              <label className="text-sm font-medium text-primary">Category</label>
              <CustomSelect
                value={formData.category_id}
                onChange={(value) => setFormData({ ...formData, category_id: value })}
                options={categories.map((cat) => ({
                  value: cat.id,
                  label: cat.name,
                }))}
                placeholder="Select category..."
                searchable={true}
                searchPlaceholder="Search..."
                error={errors.category_id}
                onAddNew={() => setShowAddCategoryModal(true)}
                addNewLabel="Add Category"
              />
            </div>
          </div>

          {/* Row 6: Description and Notes */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 p-4 bg-primary/5 rounded-lg border border-primary/10">
            <FormField label="Description">
              <textarea
                className="input w-full min-h-[80px] resize-y"
                value={formData.description}
                onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                placeholder="Enter tool description"
                rows={3}
              />
            </FormField>

            <FormField label="Notes">
              <textarea
                className="input w-full min-h-[80px] resize-y"
                value={formData.notes}
                onChange={(e) => setFormData({ ...formData, notes: e.target.value })}
                placeholder="Additional notes"
                rows={3}
              />
            </FormField>
          </div>

          {/* Row 7: Image and Manual */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 p-4 bg-primary/5 rounded-lg border border-primary/10">
            <FormField label="Tool Image">
              <ImageUpload
                onImageUploaded={setImageUrl}
                currentImageUrl={imageUrl}
                placeholder="Upload image"
                className="w-full"
              />
            </FormField>

            <FormField label="Manual URL" error={errors.manual_url}>
              <input
                type="url"
                className="input w-full"
                value={formData.manual_url}
                onChange={(e) => setFormData({ ...formData, manual_url: e.target.value })}
                placeholder="https://example.com/manual.pdf"
              />
            </FormField>
          </div>

          {/* Additional Properties */}
          <details className="group" open={isAdditionalPropsOpen}>
            <summary className="flex items-center justify-between cursor-pointer p-3 bg-primary/5 border border-primary/20 rounded-md hover:bg-primary/10 transition-colors list-none">
              <div className="flex items-center gap-2">
                <Tag className="w-4 h-4 text-primary" />
                <label className="text-sm font-medium text-primary">Additional Properties</label>
                <span className="text-xs text-theme-muted">
                  ({customProperties.length} {customProperties.length === 1 ? 'property' : 'properties'})
                </span>
              </div>
              <button
                type="button"
                onClick={(e) => {
                  e.preventDefault()
                  addCustomProperty()
                }}
                className="px-2 py-1 rounded-md bg-primary/10 hover:bg-primary/20 transition-colors border border-primary/30 flex items-center gap-1 text-xs text-primary font-medium"
              >
                <Plus className="w-3 h-3" />
                Add
              </button>
            </summary>

            <div className="mt-3 space-y-2">
              {customProperties.map((prop, index) => (
                <div key={index} className="grid grid-cols-[1fr,1fr,auto] gap-2">
                  <input
                    type="text"
                    placeholder="Property name"
                    className="input w-full"
                    value={prop.key}
                    onChange={(e) => updateCustomProperty(index, 'key', e.target.value)}
                  />
                  <input
                    type="text"
                    placeholder="Property value"
                    className="input w-full"
                    value={prop.value}
                    onChange={(e) => updateCustomProperty(index, 'value', e.target.value)}
                  />
                  <button
                    type="button"
                    onClick={() => removeCustomProperty(index)}
                    className="btn btn-secondary btn-sm"
                  >
                    <X className="w-3 h-3" />
                  </button>
                </div>
              ))}

              {customProperties.length === 0 && (
                <p className="text-xs text-theme-muted p-2">
                  No custom properties added. Click "Add" to include additional specifications.
                </p>
              )}
            </div>
          </details>

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
              {loading ? 'Saving...' : editingTool ? 'Update Tool' : 'Create Tool'}
            </button>
          </div>
        </form>
      )}

      {/* Inline Modals */}
      <AddCategoryModal
        isOpen={showAddCategoryModal}
        onClose={() => setShowAddCategoryModal(false)}
        onSuccess={handleCategoryCreated}
        existingCategories={categories.map((c) => c.name)}
      />

      <AddLocationModal
        isOpen={showAddLocationModal}
        onClose={() => setShowAddLocationModal(false)}
        onSuccess={handleLocationCreated}
      />
    </Modal>
  )
}

export default ToolModal