import { useMemo } from 'react'
import { Tag } from 'lucide-react'
import CrudModal from '@/components/ui/CrudModal'
import FormField from '@/components/ui/FormField'
import { useModalForm } from '@/hooks/useModalForm'
import { categoriesService } from '@/services/categories.service'
import { Category, UpdateCategoryRequest } from '@/types/categories'

interface EditCategoryModalProps {
  isOpen: boolean
  onClose: () => void
  onSuccess: () => void
  category: Category
  existingCategories: string[]
}

const EditCategoryModal: React.FC<EditCategoryModalProps> = ({
  isOpen,
  onClose,
  onSuccess,
  category,
  existingCategories
}) => {
  const initialData: UpdateCategoryRequest = useMemo(() => ({
    id: category.id,
    name: category.name,
    description: category.description || ''
  }), [category.id, category.name, category.description])

  const validate = (data: UpdateCategoryRequest): Record<string, string> => {
    const errors: Record<string, string> = {}
    
    const validation = categoriesService.validateCategoryName(data.name)
    if (!validation.valid) {
      errors.name = validation.error!
    }

    // Check for duplicate names (excluding current category)
    if (existingCategories.some(cat => 
      cat.toLowerCase() === data.name.toLowerCase() && 
      cat.toLowerCase() !== category.name.toLowerCase()
    )) {
      errors.name = 'A category with this name already exists'
    }

    return errors
  }

  const handleSubmit = async (data: UpdateCategoryRequest) => {
    await categoriesService.updateCategory(data)
    onSuccess()
  }

  const {
    formData,
    errors,
    loading,
    handleSubmit: onSubmit,
    handleClose,
    updateField
  } = useModalForm({
    initialData,
    validate,
    onSubmit: handleSubmit,
    successMessage: 'Category updated successfully'
  })

  return (
    <CrudModal
      isOpen={isOpen}
      onClose={() => handleClose(onClose)}
      title="Edit Category"
      onSubmit={onSubmit}
      loading={loading}
      mode="edit"
      loadingText="Updating..."
      submitButtonIcon={<Tag className="w-4 h-4" />}
      className="min-h-[400px]"
    >
      <div className="space-y-6 pb-6">
        <FormField
          label="Category Name"
          required
          error={errors.name}
        >
          <input
            type="text"
            value={formData.name}
            onChange={(e) => updateField('name', e.target.value)}
            className="input w-full"
            placeholder="e.g., Electronics, Resistors"
            autoFocus
          />
        </FormField>

        <FormField label="Description">
          <textarea
            value={formData.description}
            onChange={(e) => updateField('description', e.target.value)}
            className="input w-full min-h-[120px]"
            placeholder="Optional description of this category"
            rows={4}
          />
        </FormField>
      </div>
    </CrudModal>
  )
}

export default EditCategoryModal