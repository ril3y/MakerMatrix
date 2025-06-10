import { useState, useEffect } from 'react'
import { Tag, AlertCircle } from 'lucide-react'
import Modal from '@/components/ui/Modal'
import FormField from '@/components/ui/FormField'
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
  const [formData, setFormData] = useState<UpdateCategoryRequest>({
    id: category.id,
    name: category.name,
    description: category.description || ''
  })
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [nameError, setNameError] = useState<string | null>(null)

  useEffect(() => {
    if (isOpen) {
      // Reset form when modal opens with new category
      setFormData({
        id: category.id,
        name: category.name,
        description: category.description || ''
      })
      setError(null)
      setNameError(null)
    }
  }, [isOpen, category])

  const validateName = (name: string): boolean => {
    const validation = categoriesService.validateCategoryName(name)
    if (!validation.valid) {
      setNameError(validation.error!)
      return false
    }

    if (existingCategories.some(cat => cat.toLowerCase() === name.toLowerCase())) {
      setNameError('A category with this name already exists')
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
    
    if (!validateName(formData.name)) return

    setLoading(true)
    setError(null)

    try {
      await categoriesService.updateCategory(formData)
      onSuccess()
      onClose()
    } catch (err: any) {
      setError(err.response?.data?.error || 'Failed to update category')
    } finally {
      setLoading(false)
    }
  }

  return (
    <Modal isOpen={isOpen} onClose={onClose} title="Edit Category">
      <form onSubmit={handleSubmit} className="space-y-4">
        {error && (
          <div className="bg-red-500/10 border border-red-500/50 rounded p-3 flex items-center gap-2">
            <AlertCircle className="w-4 h-4 text-red-500" />
            <p className="text-red-500 text-sm">{error}</p>
          </div>
        )}

        <FormField
          label="Category Name"
          required
          error={nameError}
        >
          <input
            type="text"
            value={formData.name}
            onChange={(e) => handleNameChange(e.target.value)}
            onBlur={() => validateName(formData.name)}
            className="input w-full"
            placeholder="e.g., Electronics, Resistors"
            autoFocus
          />
        </FormField>

        <FormField label="Description">
          <textarea
            value={formData.description}
            onChange={(e) => setFormData({ ...formData, description: e.target.value })}
            className="input w-full min-h-[80px]"
            placeholder="Optional description of this category"
            rows={3}
          />
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
            <Tag className="w-4 h-4" />
            {loading ? 'Updating...' : 'Update Category'}
          </button>
        </div>
      </form>
    </Modal>
  )
}

export default EditCategoryModal