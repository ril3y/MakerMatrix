/**
 * Bulk Edit Modal
 *
 * Modal for editing multiple parts at once with shared field updates
 */

import { useState, useEffect } from 'react'
import { Edit3, AlertCircle, Plus, X } from 'lucide-react'
import CrudModal from '@/components/ui/CrudModal'
import FormField from '@/components/ui/FormField'
import { CustomSelect } from '@/components/ui/CustomSelect'
import { SupplierSelector } from '@/components/ui/SupplierSelector'
import { categoriesService } from '@/services/categories.service'
import { locationsService } from '@/services/locations.service'
import { partsService } from '@/services/parts.service'
import { Category } from '@/types/categories'
import { Location } from '@/types/locations'
import toast from 'react-hot-toast'

interface BulkEditModalProps {
  isOpen: boolean
  onClose: () => void
  onSuccess: () => void
  selectedPartIds: string[]
  selectedCount: number
}

interface BulkEditFormData {
  // Field enablers - only update if enabled
  updateSupplier: boolean
  updateLocation: boolean
  updateMinimumQuantity: boolean
  addCategories: boolean
  removeCategories: boolean

  // Field values
  supplier?: string
  location_id?: string
  minimum_quantity?: number
  categories_to_add: string[]
  categories_to_remove: string[]
}

const BulkEditModal = ({
  isOpen,
  onClose,
  onSuccess,
  selectedPartIds,
  selectedCount,
}: BulkEditModalProps) => {
  const [loading, setLoading] = useState(false)
  const [categories, setCategories] = useState<Category[]>([])
  const [locations, setLocations] = useState<Location[]>([])

  const [formData, setFormData] = useState<BulkEditFormData>({
    updateSupplier: false,
    updateLocation: false,
    updateMinimumQuantity: false,
    addCategories: false,
    removeCategories: false,
    supplier: '',
    location_id: '',
    minimum_quantity: undefined,
    categories_to_add: [],
    categories_to_remove: [],
  })

  useEffect(() => {
    if (isOpen) {
      loadCategories()
      loadLocations()
    }
  }, [isOpen])

  const loadCategories = async () => {
    try {
      const data = await categoriesService.getAllCategories()
      setCategories(data)
    } catch (error) {
      console.error('Failed to load categories:', error)
      toast.error('Failed to load categories')
    }
  }

  const loadLocations = async () => {
    try {
      const data = await locationsService.getAllLocations()
      setLocations(data)
    } catch (error) {
      console.error('Failed to load locations:', error)
      toast.error('Failed to load locations')
    }
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()

    // Validate that at least one field is being updated
    if (
      !formData.updateSupplier &&
      !formData.updateLocation &&
      !formData.updateMinimumQuantity &&
      !formData.addCategories &&
      !formData.removeCategories
    ) {
      toast.error('Please select at least one field to update')
      return
    }

    setLoading(true)

    try {
      // Build update payload with only enabled fields
      const updates: any = {}

      if (formData.updateSupplier && formData.supplier) {
        updates.supplier = formData.supplier
      }

      if (formData.updateLocation && formData.location_id) {
        updates.location_id = formData.location_id
      }

      if (formData.updateMinimumQuantity && formData.minimum_quantity !== undefined) {
        updates.minimum_quantity = formData.minimum_quantity
      }

      // Call backend API for bulk update
      const result = await partsService.bulkUpdateParts({
        part_ids: selectedPartIds,
        supplier: formData.updateSupplier ? formData.supplier : undefined,
        location_id: formData.updateLocation ? formData.location_id : undefined,
        minimum_quantity: formData.updateMinimumQuantity ? formData.minimum_quantity : undefined,
        add_categories:
          formData.addCategories && formData.categories_to_add.length > 0
            ? formData.categories_to_add
            : undefined,
        remove_categories:
          formData.removeCategories && formData.categories_to_remove.length > 0
            ? formData.categories_to_remove
            : undefined,
      })

      // Show success/error messages
      if (result.updated_count > 0) {
        toast.success(
          `Successfully updated ${result.updated_count} part${result.updated_count > 1 ? 's' : ''}`
        )
      }

      if (result.failed_count > 0) {
        toast.error(
          `Failed to update ${result.failed_count} part${result.failed_count > 1 ? 's' : ''}`
        )
        console.error('Bulk update errors:', result.errors)
      }

      // Wait for onSuccess to complete before closing (handles async callbacks)
      await Promise.resolve(onSuccess())
      onClose()
    } catch (error: any) {
      console.error('Bulk update failed:', error)
      toast.error(error.message || 'Failed to update parts')
    } finally {
      setLoading(false)
    }
  }

  const handleClose = () => {
    if (!loading) {
      // Reset form
      setFormData({
        updateSupplier: false,
        updateLocation: false,
        updateMinimumQuantity: false,
        addCategories: false,
        removeCategories: false,
        supplier: '',
        location_id: '',
        minimum_quantity: undefined,
        categories_to_add: [],
        categories_to_remove: [],
      })
      onClose()
    }
  }

  const toggleCategoryToAdd = (categoryName: string) => {
    setFormData((prev) => ({
      ...prev,
      categories_to_add: prev.categories_to_add.includes(categoryName)
        ? prev.categories_to_add.filter((c) => c !== categoryName)
        : [...prev.categories_to_add, categoryName],
    }))
  }

  const toggleCategoryToRemove = (categoryName: string) => {
    setFormData((prev) => ({
      ...prev,
      categories_to_remove: prev.categories_to_remove.includes(categoryName)
        ? prev.categories_to_remove.filter((c) => c !== categoryName)
        : [...prev.categories_to_remove, categoryName],
    }))
  }

  return (
    <CrudModal
      isOpen={isOpen}
      onClose={handleClose}
      title="Bulk Edit Parts"
      onSubmit={handleSubmit}
      loading={loading}
      mode="edit"
      size="lg"
      loadingText="Updating parts..."
      submitButtonIcon={<Edit3 className="w-4 h-4" />}
    >
      <div className="space-y-6">
        {/* Warning banner */}
        <div className="bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-lg p-4">
          <div className="flex items-start gap-3">
            <AlertCircle className="w-5 h-5 text-yellow-600 dark:text-yellow-400 flex-shrink-0 mt-0.5" />
            <div>
              <p className="text-sm font-medium text-yellow-800 dark:text-yellow-200">
                Bulk editing {selectedCount} part{selectedCount > 1 ? 's' : ''}
              </p>
              <p className="text-xs text-yellow-700 dark:text-yellow-300 mt-1">
                Only enabled fields will be updated. Changes will apply to all selected parts.
              </p>
            </div>
          </div>
        </div>

        {/* Supplier */}
        <div className="space-y-2">
          <div className="flex items-center gap-2">
            <input
              type="checkbox"
              id="updateSupplier"
              checked={formData.updateSupplier}
              onChange={(e) => setFormData({ ...formData, updateSupplier: e.target.checked })}
              className="w-4 h-4 rounded border-theme-primary"
            />
            <label
              htmlFor="updateSupplier"
              className="text-sm font-medium text-theme-primary cursor-pointer"
            >
              Update Supplier
            </label>
          </div>
          {formData.updateSupplier && (
            <SupplierSelector
              value={formData.supplier || ''}
              onChange={(value) => setFormData({ ...formData, supplier: value })}
              placeholder="Select supplier..."
            />
          )}
        </div>

        {/* Location */}
        <div className="space-y-2">
          <div className="flex items-center gap-2">
            <input
              type="checkbox"
              id="updateLocation"
              checked={formData.updateLocation}
              onChange={(e) => setFormData({ ...formData, updateLocation: e.target.checked })}
              className="w-4 h-4 rounded border-theme-primary"
            />
            <label
              htmlFor="updateLocation"
              className="text-sm font-medium text-theme-primary cursor-pointer"
            >
              Update Primary Location
            </label>
          </div>
          {formData.updateLocation && (
            <CustomSelect
              value={formData.location_id || ''}
              onChange={(value) => setFormData({ ...formData, location_id: value })}
              options={locations.map((loc) => ({
                value: loc.id,
                label: loc.name,
              }))}
              placeholder="Select location..."
              searchable
              searchPlaceholder="Search locations..."
            />
          )}
        </div>

        {/* Minimum Quantity */}
        <div className="space-y-2">
          <div className="flex items-center gap-2">
            <input
              type="checkbox"
              id="updateMinimumQuantity"
              checked={formData.updateMinimumQuantity}
              onChange={(e) =>
                setFormData({ ...formData, updateMinimumQuantity: e.target.checked })
              }
              className="w-4 h-4 rounded border-theme-primary"
            />
            <label
              htmlFor="updateMinimumQuantity"
              className="text-sm font-medium text-theme-primary cursor-pointer"
            >
              Set Minimum Quantity
            </label>
          </div>
          {formData.updateMinimumQuantity && (
            <input
              type="number"
              value={formData.minimum_quantity || ''}
              onChange={(e) =>
                setFormData({ ...formData, minimum_quantity: parseInt(e.target.value) || 0 })
              }
              className="input w-full"
              placeholder="Enter minimum quantity..."
              min={0}
            />
          )}
        </div>

        {/* Add Categories */}
        <div className="space-y-2">
          <div className="flex items-center gap-2">
            <input
              type="checkbox"
              id="addCategories"
              checked={formData.addCategories}
              onChange={(e) => setFormData({ ...formData, addCategories: e.target.checked })}
              className="w-4 h-4 rounded border-theme-primary"
            />
            <label
              htmlFor="addCategories"
              className="text-sm font-medium text-theme-primary cursor-pointer"
            >
              Add Categories
            </label>
          </div>
          {formData.addCategories && (
            <div className="space-y-2">
              <div className="flex flex-wrap gap-2">
                {formData.categories_to_add.map((categoryName) => (
                  <span
                    key={categoryName}
                    className="inline-flex items-center gap-1 px-3 py-1 rounded-full text-xs font-medium bg-blue-100 dark:bg-blue-900/30 text-blue-800 dark:text-blue-200"
                  >
                    {categoryName}
                    <button
                      onClick={() => toggleCategoryToAdd(categoryName)}
                      className="hover:text-blue-600"
                    >
                      <X className="w-3 h-3" />
                    </button>
                  </span>
                ))}
              </div>
              <CustomSelect
                value=""
                onChange={(value) => {
                  const category = categories.find((c) => c.id === value)
                  if (category && !formData.categories_to_add.includes(category.name)) {
                    toggleCategoryToAdd(category.name)
                  }
                }}
                options={categories
                  .filter((c) => !formData.categories_to_add.includes(c.name))
                  .map((c) => ({
                    value: c.id,
                    label: c.name,
                  }))}
                placeholder="Select category to add..."
                searchable
                searchPlaceholder="Search categories..."
              />
            </div>
          )}
        </div>

        {/* Remove Categories */}
        <div className="space-y-2">
          <div className="flex items-center gap-2">
            <input
              type="checkbox"
              id="removeCategories"
              checked={formData.removeCategories}
              onChange={(e) => setFormData({ ...formData, removeCategories: e.target.checked })}
              className="w-4 h-4 rounded border-theme-primary"
            />
            <label
              htmlFor="removeCategories"
              className="text-sm font-medium text-theme-primary cursor-pointer"
            >
              Remove Categories
            </label>
          </div>
          {formData.removeCategories && (
            <div className="space-y-2">
              <div className="flex flex-wrap gap-2">
                {formData.categories_to_remove.map((categoryName) => (
                  <span
                    key={categoryName}
                    className="inline-flex items-center gap-1 px-3 py-1 rounded-full text-xs font-medium bg-red-100 dark:bg-red-900/30 text-red-800 dark:text-red-200"
                  >
                    {categoryName}
                    <button
                      onClick={() => toggleCategoryToRemove(categoryName)}
                      className="hover:text-red-600"
                    >
                      <X className="w-3 h-3" />
                    </button>
                  </span>
                ))}
              </div>
              <CustomSelect
                value=""
                onChange={(value) => {
                  const category = categories.find((c) => c.id === value)
                  if (category && !formData.categories_to_remove.includes(category.name)) {
                    toggleCategoryToRemove(category.name)
                  }
                }}
                options={categories
                  .filter((c) => !formData.categories_to_remove.includes(c.name))
                  .map((c) => ({
                    value: c.id,
                    label: c.name,
                  }))}
                placeholder="Select category to remove..."
                searchable
                searchPlaceholder="Search categories..."
              />
            </div>
          )}
        </div>
      </div>
    </CrudModal>
  )
}

export default BulkEditModal
