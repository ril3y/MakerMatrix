import { Tag } from 'lucide-react'
import { useMemo } from 'react'
import CrudModal from '@/components/ui/CrudModal'
import FormField from '@/components/ui/FormField'
import { useModalForm } from '@/hooks/useModalForm'
import { categoriesService } from '@/services/categories.service'
import { CreateCategoryRequest } from '@/types/parts'

interface AddCategoryModalProps {
  isOpen: boolean
  onClose: () => void
  onSuccess: () => void
  existingCategories?: string[]
}

const AddCategoryModal = ({
  isOpen,
  onClose,
  onSuccess,
  existingCategories = [],
}: AddCategoryModalProps) => {
  const initialData: CreateCategoryRequest = useMemo(
    () => ({
      name: '',
      description: '',
    }),
    []
  )

  const validate = (data: CreateCategoryRequest): Record<string, string> => {
    const errors: Record<string, string> = {}

    if (!data.name.trim()) {
      errors.name = 'Category name is required'
    } else if (data.name.trim().length < 2) {
      errors.name = 'Category name must be at least 2 characters'
    } else if (data.name.trim().length > 50) {
      errors.name = 'Category name must be less than 50 characters'
    }

    // Check for duplicate names
    if (existingCategories.some((cat) => cat.toLowerCase() === data.name.toLowerCase().trim())) {
      errors.name = 'A category with this name already exists'
    }

    // Basic validation for category name format
    if (data.name.trim() && !/^[a-zA-Z0-9\s\-_&()]+$/.test(data.name.trim())) {
      errors.name = 'Category name contains invalid characters'
    }

    return errors
  }

  const handleSubmit = async (data: CreateCategoryRequest) => {
    const submitData: CreateCategoryRequest = {
      name: data.name.trim(),
      description: data.description?.trim() || undefined,
    }

    await categoriesService.createCategory(submitData)
    onSuccess()
  }

  const {
    formData,
    errors,
    loading,
    handleSubmit: onSubmit,
    handleClose,
    updateField,
  } = useModalForm({
    initialData,
    validate,
    onSubmit: handleSubmit,
    successMessage: 'Category created successfully',
  })

  const suggestedCategories = [
    'Electronics',
    'Resistors',
    'Capacitors',
    'Connectors',
    'Tools',
    'Hardware',
    'Sensors',
    'Microcontrollers',
    'Power Supplies',
    'Cables',
    'Mechanical',
    'Fasteners',
    'Arduino',
    'Raspberry Pi',
  ]

  const availableSuggestions = suggestedCategories.filter(
    (cat) => !existingCategories.some((existing) => existing.toLowerCase() === cat.toLowerCase())
  )

  return (
    <CrudModal
      isOpen={isOpen}
      onClose={() => handleClose(onClose)}
      title="Add New Category"
      size="md"
      onSubmit={onSubmit}
      loading={loading}
      mode="create"
      loadingText="Creating..."
    >
      <FormField
        label="Category Name"
        required
        error={errors.name}
        description="Use descriptive names like 'Electronics', 'Resistors', or 'Arduino Components'"
      >
        <input
          type="text"
          className="input w-full"
          value={formData.name}
          onChange={(e) => updateField('name', e.target.value)}
          placeholder="Enter category name"
          maxLength={50}
        />
      </FormField>

      {/* Character count */}
      <div className="text-right">
        <span
          className={`text-xs ${formData.name.length > 40 ? 'text-warning' : 'text-theme-secondary'}`}
        >
          {formData.name.length}/50 characters
        </span>
      </div>

      <FormField
        label="Description"
        error={errors.description}
        description="Optional description to help identify this category"
      >
        <textarea
          className="input w-full min-h-[80px] resize-y"
          value={formData.description || ''}
          onChange={(e) => updateField('description', e.target.value)}
          placeholder="Enter category description (optional)"
          rows={3}
        />
      </FormField>

      {/* Suggested categories */}
      {availableSuggestions.length > 0 && (
        <div className="space-y-3">
          <label className="text-sm font-medium text-theme-primary">Quick Select</label>
          <div className="flex flex-wrap gap-2">
            {availableSuggestions.slice(0, 8).map((suggestion) => (
              <button
                key={suggestion}
                type="button"
                onClick={() => updateField('name', suggestion)}
                className="px-3 py-1 text-sm bg-primary-10 text-primary rounded-full hover:bg-primary-20 transition-colors"
              >
                {suggestion}
              </button>
            ))}
          </div>
          <p className="text-xs text-theme-secondary">
            Click a suggestion to use it, or type your own category name
          </p>
        </div>
      )}

      {/* Preview */}
      {formData.name.trim() && (
        <div className="p-3 bg-theme-secondary rounded-md border border-theme-primary">
          <p className="text-sm text-theme-muted mb-1">Preview:</p>
          <div className="flex items-center gap-2">
            <Tag className="w-4 h-4 text-primary-accent" />
            <span className="text-sm font-medium text-theme-primary">{formData.name.trim()}</span>
          </div>
        </div>
      )}
    </CrudModal>
  )
}

export default AddCategoryModal
