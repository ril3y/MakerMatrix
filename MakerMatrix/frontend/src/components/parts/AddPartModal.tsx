import { useState, useEffect } from 'react'
import { Save, Package, Plus, X, Upload, Image } from 'lucide-react'
import Modal from '@/components/ui/Modal'
import FormField from '@/components/ui/FormField'
import { partsService } from '@/services/parts.service'
import { locationsService } from '@/services/locations.service'
import { categoriesService } from '@/services/categories.service'
import { utilityService } from '@/services/utility.service'
import { DynamicSupplierService } from '@/services/dynamic-supplier.service'
import { tasksService } from '@/services/tasks.service'
import { CreatePartRequest } from '@/types/parts'
import { Location, Category } from '@/types/parts'
import toast from 'react-hot-toast'

interface AddPartModalProps {
  isOpen: boolean
  onClose: () => void
  onSuccess: () => void
}

const AddPartModal = ({ isOpen, onClose, onSuccess }: AddPartModalProps) => {
  const [formData, setFormData] = useState<CreatePartRequest>({
    name: '',
    part_number: '',
    quantity: 0,
    minimum_quantity: 0,
    supplier: '',
    supplier_url: '',
    location_id: '',
    categories: [],
    additional_properties: {}
  })

  const [locations, setLocations] = useState<Location[]>([])
  const [categories, setCategories] = useState<Category[]>([])
  const [suppliers, setSuppliers] = useState<Array<{id: string; name: string; description: string}>>([])
  const [selectedCategories, setSelectedCategories] = useState<string[]>([])
  const [customProperties, setCustomProperties] = useState<Array<{key: string, value: string}>>([])
  const [errors, setErrors] = useState<Record<string, string>>({})
  const [loading, setLoading] = useState(false)
  const [loadingData, setLoadingData] = useState(false)
  const [imageFile, setImageFile] = useState<File | null>(null)
  const [imagePreview, setImagePreview] = useState<string | null>(null)
  const [uploadingImage, setUploadingImage] = useState(false)

  useEffect(() => {
    if (isOpen) {
      loadData()
    }
  }, [isOpen])

  const loadData = async () => {
    try {
      setLoadingData(true)
      const [locationsData, categoriesData, suppliersData] = await Promise.all([
        locationsService.getAllLocations(),
        categoriesService.getAllCategories(),
        DynamicSupplierService.getInstance().getConfiguredSuppliers()
      ])
      setLocations(locationsData || [])
      setCategories(categoriesData || [])
      setSuppliers(suppliersData || [])
    } catch (error) {
      console.error('Failed to load data:', error)
      toast.error('Failed to load data')
      // Set empty arrays as fallbacks
      setLocations([])
      setCategories([])
      setSuppliers([])
    } finally {
      setLoadingData(false)
    }
  }

  const validate = (): boolean => {
    const newErrors: Record<string, string> = {}

    if (!formData.name.trim()) {
      newErrors.name = 'Part name is required'
    }

    if (formData.quantity < 0) {
      newErrors.quantity = 'Quantity cannot be negative'
    }

    if (formData.minimum_quantity && formData.minimum_quantity < 0) {
      newErrors.minimum_quantity = 'Minimum quantity cannot be negative'
    }

    if (formData.supplier_url && !isValidUrl(formData.supplier_url)) {
      newErrors.supplier_url = 'Please enter a valid URL'
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

  const handleImageChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (file) {
      // Validate file type
      if (!file.type.startsWith('image/')) {
        toast.error('Please select an image file')
        return
      }

      // Validate file size (max 5MB)
      if (file.size > 5 * 1024 * 1024) {
        toast.error('Image size should be less than 5MB')
        return
      }

      setImageFile(file)
      
      // Create preview
      const reader = new FileReader()
      reader.onloadend = () => {
        setImagePreview(reader.result as string)
      }
      reader.readAsDataURL(file)
    }
  }

  const removeImage = () => {
    setImageFile(null)
    setImagePreview(null)
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    
    if (!validate()) {
      return
    }

    try {
      setLoading(true)

      // Upload image first if there is one
      let imageUrl: string | undefined
      if (imageFile) {
        try {
          setUploadingImage(true)
          imageUrl = await utilityService.uploadImage(imageFile)
        } catch (error) {
          console.error('Failed to upload image:', error)
          toast.error('Failed to upload image')
          setLoading(false)
          setUploadingImage(false)
          return
        } finally {
          setUploadingImage(false)
        }
      }

      // Prepare properties object
      const properties: Record<string, any> = {}
      customProperties.forEach(({ key, value }) => {
        if (key.trim() && value.trim()) {
          properties[key.trim()] = value.trim()
        }
      })

      const submitData: CreatePartRequest = {
        ...formData,
        image_url: imageUrl,
        categories: selectedCategories,
        additional_properties: Object.keys(properties).length > 0 ? properties : undefined
      }

      const createdPart = await partsService.createPart(submitData)
      toast.success('Part created successfully')
      
      // Auto-enrich if supplier is specified
      if (formData.supplier && formData.supplier.trim()) {
        try {
          console.log(`Auto-enriching part ${createdPart.id} with supplier ${formData.supplier}`)
          const enrichmentTask = await tasksService.createPartEnrichmentTask({
            part_id: createdPart.id,
            supplier: formData.supplier.trim(),
            capabilities: ['fetch_datasheet', 'fetch_image', 'fetch_pricing', 'fetch_specifications'],
            force_refresh: false
          })
          toast.success(`Enrichment task created: ${enrichmentTask.data.name}`)
          console.log('Enrichment task created:', enrichmentTask.data)
        } catch (error) {
          console.error('Failed to create enrichment task:', error)
          toast.error('Part created but enrichment failed to start')
        }
      }
      
      onSuccess()
      handleClose()
    } catch (error: any) {
      toast.error(error.response?.data?.message || 'Failed to create part')
    } finally {
      setLoading(false)
    }
  }

  const handleClose = () => {
    setFormData({
      name: '',
      part_number: '',
      quantity: 0,
      minimum_quantity: 0,
      supplier: '',
      supplier_url: '',
      location_id: '',
      categories: [],
      additional_properties: {}
    })
    setSelectedCategories([])
    setCustomProperties([])
    setErrors({})
    setImageFile(null)
    setImagePreview(null)
    onClose()
  }

  const addCustomProperty = () => {
    setCustomProperties([...customProperties, { key: '', value: '' }])
  }

  const updateCustomProperty = (index: number, field: 'key' | 'value', value: string) => {
    const updated = [...customProperties]
    updated[index][field] = value
    setCustomProperties(updated)
  }

  const removeCustomProperty = (index: number) => {
    setCustomProperties(customProperties.filter((_, i) => i !== index))
  }

  const toggleCategory = (categoryId: string) => {
    if (selectedCategories.includes(categoryId)) {
      setSelectedCategories(selectedCategories.filter(id => id !== categoryId))
    } else {
      setSelectedCategories([...selectedCategories, categoryId])
    }
  }

  return (
    <Modal isOpen={isOpen} onClose={handleClose} title="Add New Part" size="lg">
      {loadingData ? (
        <div className="text-center py-8">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary mx-auto"></div>
          <p className="text-secondary mt-2">Loading...</p>
        </div>
      ) : (
        <form onSubmit={handleSubmit} className="space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* Basic Information */}
            <FormField label="Part Name" required error={errors.name}>
              <input
                type="text"
                className="input w-full"
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                placeholder="Enter part name"
              />
            </FormField>

            <FormField label="Part Number" error={errors.part_number}>
              <input
                type="text"
                className="input w-full"
                value={formData.part_number}
                onChange={(e) => setFormData({ ...formData, part_number: e.target.value })}
                placeholder="Enter part number"
              />
            </FormField>

            <FormField label="Quantity" required error={errors.quantity}>
              <input
                type="number"
                min="0"
                className="input w-full"
                value={formData.quantity}
                onChange={(e) => setFormData({ ...formData, quantity: parseInt(e.target.value) || 0 })}
              />
            </FormField>

            <FormField label="Minimum Quantity" error={errors.minimum_quantity} description="Alert when quantity falls below this level">
              <input
                type="number"
                min="0"
                className="input w-full"
                value={formData.minimum_quantity}
                onChange={(e) => setFormData({ ...formData, minimum_quantity: parseInt(e.target.value) || 0 })}
              />
            </FormField>

            <FormField label="Location" error={errors.location_id}>
              <select
                className="input w-full"
                value={formData.location_id}
                onChange={(e) => setFormData({ ...formData, location_id: e.target.value })}
              >
                <option value="">Select a location</option>
                {locations.map((location) => (
                  <option key={location.id} value={location.id}>
                    {location.name}
                  </option>
                ))}
              </select>
            </FormField>

            <FormField label="Supplier" error={errors.supplier}>
              <select
                className="input w-full"
                value={formData.supplier}
                onChange={(e) => setFormData({ ...formData, supplier: e.target.value })}
              >
                <option value="">Select a supplier</option>
                {suppliers && suppliers.map((supplier) => (
                  <option key={supplier.id} value={supplier.name}>
                    {supplier.name}
                  </option>
                ))}
              </select>
            </FormField>
          </div>

          <FormField label="Supplier URL" error={errors.supplier_url}>
            <input
              type="url"
              className="input w-full"
              value={formData.supplier_url}
              onChange={(e) => setFormData({ ...formData, supplier_url: e.target.value })}
              placeholder="https://supplier.com/part-page"
            />
          </FormField>

          {/* Image Upload */}
          <FormField label="Part Image" description="Upload an image of the part (max 5MB)">
            <div className="space-y-3">
              {imagePreview ? (
                <div className="relative">
                  <img 
                    src={imagePreview} 
                    alt="Part preview" 
                    className="w-32 h-32 object-cover rounded-lg border border-border"
                  />
                  <button
                    type="button"
                    onClick={removeImage}
                    className="absolute -top-2 -right-2 p-1 bg-red-500 text-white rounded-full hover:bg-red-600"
                  >
                    <X className="w-4 h-4" />
                  </button>
                </div>
              ) : (
                <label className="flex flex-col items-center justify-center w-32 h-32 border-2 border-dashed border-theme-secondary rounded-lg cursor-pointer hover:border-primary hover:bg-theme-secondary transition-colors">
                  <input
                    type="file"
                    accept="image/*"
                    onChange={handleImageChange}
                    className="hidden"
                  />
                  {uploadingImage ? (
                    <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-primary"></div>
                  ) : (
                    <>
                      <Upload className="w-8 h-8 text-theme-muted mb-2" />
                      <span className="text-xs text-theme-muted">Upload Image</span>
                    </>
                  )}
                </label>
              )}
            </div>
          </FormField>

          {/* Categories */}
          <FormField label="Categories" description="Select categories that apply to this part">
            <div className="border border-border rounded-md p-3 max-h-32 overflow-y-auto">
              {categories.length > 0 ? (
                <div className="space-y-2">
                  {categories.map((category) => (
                    <label key={category.id} className="flex items-center gap-2 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={selectedCategories.includes(category.id)}
                        onChange={() => toggleCategory(category.id)}
                        className="rounded border-border"
                      />
                      <span className="text-sm text-primary">{category.name}</span>
                    </label>
                  ))}
                </div>
              ) : (
                <p className="text-sm text-secondary">No categories available</p>
              )}
            </div>
          </FormField>

          {/* Custom Properties */}
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <label className="text-sm font-medium text-primary">Custom Properties</label>
              <button
                type="button"
                onClick={addCustomProperty}
                className="btn btn-secondary btn-sm flex items-center gap-1"
              >
                <Plus className="w-3 h-3" />
                Add Property
              </button>
            </div>
            
            {customProperties.map((prop, index) => (
              <div key={index} className="flex gap-2">
                <input
                  type="text"
                  placeholder="Property name"
                  className="input flex-1"
                  value={prop.key}
                  onChange={(e) => updateCustomProperty(index, 'key', e.target.value)}
                />
                <input
                  type="text"
                  placeholder="Property value"
                  className="input flex-1"
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
              <p className="text-sm text-secondary">No custom properties added</p>
            )}
          </div>

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
              {loading ? 'Creating...' : 'Create Part'}
            </button>
          </div>
        </form>
      )}
    </Modal>
  )
}

export default AddPartModal