import { useEffect, useState } from 'react'
import { Save, Plus } from 'lucide-react'
import { 
  FormInput, 
  FormTextarea, 
  FormSelect, 
  FormNumberInput,
  FormSection,
  FormGrid,
  FormActions,
  ImageUpload,
  CategorySelector,
  LocationTreeSelector
} from '@/components/forms'
import Modal from '@/components/ui/Modal'
import AddCategoryModal from '@/components/categories/AddCategoryModal'
import AddLocationModal from '@/components/locations/AddLocationModal'
import { useFormWithValidation } from '@/hooks/useFormWithValidation'
import { partFormSchema, type PartFormData } from '@/schemas/parts'
import { partsService } from '@/services/parts.service'
import { locationsService } from '@/services/locations.service'
import { categoriesService } from '@/services/categories.service'
import { DynamicSupplierService } from '@/services/dynamic-supplier.service'
import { Location, Category } from '@/types/parts'
import toast from 'react-hot-toast'

interface AddPartModalProps {
  isOpen: boolean
  onClose: () => void
  onSuccess: () => void
}

const AddPartModal = ({ isOpen, onClose, onSuccess }: AddPartModalProps) => {
  // Form state using our new standardized hook
  const form = useFormWithValidation<PartFormData>({
    schema: partFormSchema,
    defaultValues: {
      part_name: '',
      part_number: '',
      description: '',
      quantity: 1,
      supplier: '',
      location_id: '',
      image_url: '',
      additional_properties: {},
      category_names: [],
    },
    onSubmit: async (data) => {
      // Transform form data for API
      const submitData = {
        ...data,
        // Handle image upload
        image_url: imageUrl || data.image_url,
        // Convert additional properties array to object
        additional_properties: customProperties.reduce((acc, prop) => {
          if (prop.key && prop.value) {
            acc[prop.key] = prop.value
          }
          return acc
        }, {} as Record<string, any>),
      }
      
      const result = await partsService.createPart(submitData)
      return result
    },
    onSuccess: () => {
      toast.success('Part added successfully!')
      onSuccess()
      resetForm()
    },
    successMessage: 'Part added successfully!',
    resetOnSuccess: true,
  })

  // Data loading states
  const [locations, setLocations] = useState<Location[]>([])
  const [categories, setCategories] = useState<Category[]>([])
  const [suppliers, setSuppliers] = useState<Array<{id: string; name: string; description: string}>>([])
  const [loadingData, setLoadingData] = useState(false)
  
  // Additional form states
  const [imageUrl, setImageUrl] = useState<string>('')
  const [customProperties, setCustomProperties] = useState<Array<{key: string, value: string}>>([])
  const [showAddCategoryModal, setShowAddCategoryModal] = useState(false)
  const [showAddLocationModal, setShowAddLocationModal] = useState(false)

  // Load data when modal opens
  useEffect(() => {
    if (isOpen) {
      loadData()
    }
  }, [isOpen])

  // Reset form when modal closes
  useEffect(() => {
    if (!isOpen) {
      resetForm()
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
      setLocations([])
      setCategories([])
      setSuppliers([])
    } finally {
      setLoadingData(false)
    }
  }

  const resetForm = () => {
    form.reset()
    setImageUrl('')
    setCustomProperties([])
  }

  const handleImageUpload = (url: string) => {
    setImageUrl(url)
  }

  const handleCategoryChange = (categoryNames: string[]) => {
    form.setValue('category_names', categoryNames)
  }

  const handleLocationChange = (locationId: string) => {
    form.setValue('location_id', locationId)
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

  const handleAddCategory = () => {
    setShowAddCategoryModal(true)
  }

  const handleAddLocation = () => {
    setShowAddLocationModal(true)
  }

  const handleCategoryAdded = () => {
    setShowAddCategoryModal(false)
    loadData() // Refresh categories
  }

  const handleLocationAdded = () => {
    setShowAddLocationModal(false)
    loadData() // Refresh locations
  }

  return (
    <>
      <Modal
        isOpen={isOpen}
        onClose={onClose}
        title="Add New Part"
        icon={<Save className="w-5 h-5" />}
        size="lg"
        loading={form.loading || loadingData}
      >
        <form onSubmit={form.onSubmit} className="space-y-6">
          {/* Basic Information Section */}
          <FormSection title="Basic Information" required>
            <FormGrid columns={2}>
              <FormInput
                label="Part Name"
                required
                {...form.getFieldProps('part_name')}
                placeholder="Enter part name"
              />
              
              <FormInput
                label="Part Number"
                {...form.getFieldProps('part_number')}
                placeholder="Supplier part number"
              />
              
              <FormNumberInput
                label="Quantity"
                required
                min={0}
                {...form.getFieldProps('quantity')}
                className="md:col-span-2"
              />
            </FormGrid>
            
            <FormTextarea
              label="Description"
              {...form.getFieldProps('description')}
              placeholder="Enter part description"
              rows={3}
            />
          </FormSection>

          {/* Supplier Information Section */}
          <FormSection title="Supplier Information">
            <FormSelect
              label="Supplier"
              {...form.getFieldProps('supplier')}
              placeholder="Select supplier"
            >
              <option value="">No supplier</option>
              {suppliers.map((supplier) => (
                <option key={supplier.id} value={supplier.name}>
                  {supplier.name}
                </option>
              ))}
            </FormSelect>
          </FormSection>

          {/* Organization Section */}
          <FormSection title="Organization">
            <FormGrid columns={2}>
              <div>
                <label className="block text-sm font-medium text-primary mb-2">
                  Location
                </label>
                <div className="flex gap-2">
                  <div className="flex-1">
                    <LocationTreeSelector
                      locations={locations}
                      selectedLocationId={form.watch('location_id') || ''}
                      onLocationSelect={handleLocationChange}
                      placeholder="Select location"
                    />
                  </div>
                  <button
                    type="button"
                    onClick={handleAddLocation}
                    className="px-3 py-2 border border-border rounded-md hover:bg-muted"
                    title="Add new location"
                  >
                    <Plus className="w-4 h-4" />
                  </button>
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-primary mb-2">
                  Categories
                </label>
                <div className="flex gap-2">
                  <div className="flex-1">
                    <CategorySelector
                      categories={categories}
                      selectedCategories={form.watch('category_names') || []}
                      onCategoryChange={handleCategoryChange}
                      placeholder="Select categories"
                    />
                  </div>
                  <button
                    type="button"
                    onClick={handleAddCategory}
                    className="px-3 py-2 border border-border rounded-md hover:bg-muted"
                    title="Add new category"
                  >
                    <Plus className="w-4 h-4" />
                  </button>
                </div>
              </div>
            </FormGrid>
          </FormSection>

          {/* Image Section */}
          <FormSection title="Image" collapsible defaultOpen={false}>
            <ImageUpload
              onImageUpload={handleImageUpload}
              currentImageUrl={imageUrl}
              accept="image/*"
              maxSize={5 * 1024 * 1024} // 5MB
            />
          </FormSection>

          {/* Custom Properties Section */}
          <FormSection title="Custom Properties" collapsible defaultOpen={false}>
            <div className="space-y-3">
              {customProperties.map((prop, index) => (
                <div key={index} className="flex gap-2 items-end">
                  <FormInput
                    label={index === 0 ? "Property Name" : ""}
                    value={prop.key}
                    onChange={(e) => updateCustomProperty(index, 'key', e.target.value)}
                    placeholder="Property name"
                    className="flex-1"
                  />
                  <FormInput
                    label={index === 0 ? "Value" : ""}
                    value={prop.value}
                    onChange={(e) => updateCustomProperty(index, 'value', e.target.value)}
                    placeholder="Property value"
                    className="flex-1"
                  />
                  <button
                    type="button"
                    onClick={() => removeCustomProperty(index)}
                    className="px-3 py-2 text-red-600 hover:bg-red-50 rounded-md"
                    title="Remove property"
                  >
                    ×
                  </button>
                </div>
              ))}
              
              <button
                type="button"
                onClick={addCustomProperty}
                className="px-4 py-2 text-sm border border-dashed border-border rounded-md hover:bg-muted flex items-center gap-2"
              >
                <Plus className="w-4 h-4" />
                Add Custom Property
              </button>
            </div>
          </FormSection>

          {/* Form Actions */}
          <FormActions
            onSubmit={() => {}} // Form handles submit
            onCancel={onClose}
            submitText="Add Part"
            loading={form.loading}
            disabled={!form.isValid || loadingData}
            layout="right"
          />
        </form>
      </Modal>

      {/* Add Category Modal */}
      <AddCategoryModal
        isOpen={showAddCategoryModal}
        onClose={() => setShowAddCategoryModal(false)}
        onSuccess={handleCategoryAdded}
      />

      {/* Add Location Modal */}
      <AddLocationModal
        isOpen={showAddLocationModal}
        onClose={() => setShowAddLocationModal(false)}
        onSuccess={handleLocationAdded}
      />
    </>
  )
}

export default AddPartModal