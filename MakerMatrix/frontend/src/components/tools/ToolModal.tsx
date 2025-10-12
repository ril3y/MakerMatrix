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
    tool_name: '',
    tool_number: '',
    description: '',
    manufacturer: '',
    model_number: '',
    product_url: '',
    purchase_date: '',
    purchase_price: undefined,
    condition: 'good',
    is_checkable: true,
    location_id: '',
    category_ids: [],
    image_url: '',
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
    { value: 'excellent', label: 'Excellent' },
    { value: 'good', label: 'Good' },
    { value: 'fair', label: 'Fair' },
    { value: 'poor', label: 'Poor' },
    { value: 'needs_repair', label: 'Needs Repair' },
    { value: 'out_of_service', label: 'Out of Service' },
  ]

  useEffect(() => {
    if (isOpen) {
      loadData()
      if (editingTool) {
        // Load existing tool data for editing
        setFormData({
          tool_name: editingTool.tool_name,
          tool_number: editingTool.tool_number || '',
          description: editingTool.description || '',
          manufacturer: editingTool.manufacturer || '',
          model_number: editingTool.model_number || '',
          product_url: editingTool.product_url || '',
          purchase_date: editingTool.purchase_date || '',
          purchase_price: editingTool.purchase_price,
          condition: editingTool.condition,
          is_checkable: editingTool.is_checkable,
          location_id: editingTool.location_id || '',
          category_ids: editingTool.categories && editingTool.categories.length > 0 ? editingTool.categories.map(c => c.id) : [],
          image_url: editingTool.image_url || '',
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

    if (!formData.tool_name.trim()) {
      newErrors.tool_name = 'Tool name is required'
    }

    if (formData.purchase_price !== undefined && formData.purchase_price < 0) {
      newErrors.purchase_price = 'Purchase price cannot be negative'
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
        // Ensure empty strings for dates are sent as undefined
        purchase_date: formData.purchase_date || undefined,
        // Ensure empty strings are sent as undefined for optional fields
        tool_number: formData.tool_number || undefined,
        description: formData.description || undefined,
        manufacturer: formData.manufacturer || undefined,
        model_number: formData.model_number || undefined,
        product_url: formData.product_url || undefined,
        location_id: formData.location_id || undefined,
        category_ids: formData.category_ids && formData.category_ids.length > 0 ? formData.category_ids : undefined,
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
      console.error('Full error response:', error.response?.data)
      console.error('Submit data:', submitData)
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
      tool_name: '',
      tool_number: '',
      description: '',
      manufacturer: '',
      model_number: '',
      product_url: '',
      purchase_date: '',
      purchase_price: undefined,
      condition: 'good',
      is_checkable: true,
      location_id: '',
      category_ids: [],
      image_url: '',
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
        // Add the newly created category to existing selections
        const currentCategories = formData.category_ids || []
        if (!currentCategories.includes(newestCategory.id)) {
          setFormData({ ...formData, category_ids: [...currentCategories, newestCategory.id] })
        }
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
            <FormField label="Tool Name" required error={errors.tool_name}>
              <input
                type="text"
                className="input w-full"
                value={formData.tool_name}
                onChange={(e) => setFormData({ ...formData, tool_name: e.target.value })}
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
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 p-4 bg-primary/5 rounded-lg border border-primary/10">
            <FormField label="Manufacturer">
              <input
                type="text"
                className="input w-full"
                value={formData.manufacturer}
                onChange={(e) => setFormData({ ...formData, manufacturer: e.target.value })}
                placeholder="Enter manufacturer"
              />
            </FormField>

            <FormField label="Model Number">
              <input
                type="text"
                className="input w-full"
                value={formData.model_number}
                onChange={(e) => setFormData({ ...formData, model_number: e.target.value })}
                placeholder="Enter model number"
              />
            </FormField>
          </div>

          {/* Row 2.5: Product URL */}
          <div className="p-4 bg-primary/5 rounded-lg border border-primary/10">
            <FormField label="Product URL" tooltip="Link to product page or documentation">
              <input
                type="url"
                className="input w-full"
                value={formData.product_url}
                onChange={(e) => setFormData({ ...formData, product_url: e.target.value })}
                placeholder="https://example.com/product"
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

          {/* Row 4: Location and Category */}
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
              <label className="text-sm font-medium text-primary">Categories</label>
              <CustomSelect
                value=""
                onChange={() => {}}
                multiSelect={true}
                selectedValues={formData.category_ids || []}
                onMultiSelectChange={(values) => setFormData({ ...formData, category_ids: values })}
                options={categories.map((cat) => ({
                  value: cat.id,
                  label: cat.name,
                }))}
                placeholder="Select categories..."
                searchable={true}
                searchPlaceholder="Search..."
                error={errors.category_ids}
                onAddNew={() => setShowAddCategoryModal(true)}
                addNewLabel="Add Category"
              />
            </div>
          </div>

          {/* Row 6: Description */}
          <div className="p-4 bg-primary/5 rounded-lg border border-primary/10">
            <FormField label="Description">
              <textarea
                className="input w-full min-h-[80px] resize-y"
                value={formData.description}
                onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                placeholder="Enter tool description"
                rows={3}
              />
            </FormField>
          </div>

          {/* Row 6.5: Tool Settings */}
          <div className="p-4 bg-primary/5 rounded-lg border border-primary/10">
            <label className="text-sm font-medium text-primary mb-3 block">Tool Settings</label>
            <div className="flex items-center gap-2">
              <input
                type="checkbox"
                id="is_checkable"
                checked={formData.is_checkable}
                onChange={(e) => setFormData({ ...formData, is_checkable: e.target.checked })}
                className="w-4 h-4 rounded border-border bg-background text-primary focus:ring-primary focus:ring-offset-0"
              />
              <label htmlFor="is_checkable" className="text-sm text-primary cursor-pointer">
                Tool can be checked out
                <span className="text-xs text-muted block">
                  Uncheck for large or stationary equipment that cannot be borrowed
                </span>
              </label>
            </div>
          </div>

          {/* Row 7: Image */}
          <div className="p-4 bg-primary/5 rounded-lg border border-primary/10">
            <FormField label="Tool Image">
              <ImageUpload
                onImageUploaded={setImageUrl}
                currentImageUrl={imageUrl}
                placeholder="Upload image"
                className="w-full"
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