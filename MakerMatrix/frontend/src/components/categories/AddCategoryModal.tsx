import { useState } from 'react'
import { Save, Tag } from 'lucide-react'
import Modal from '@/components/ui/Modal'
import FormField from '@/components/ui/FormField'
import { categoriesService } from '@/services/categories.service'
import { CreateCategoryRequest } from '@/types/parts'
import toast from 'react-hot-toast'

interface AddCategoryModalProps {
  isOpen: boolean
  onClose: () => void
  onSuccess: () => void
  existingCategories?: string[]
}

const AddCategoryModal = ({ isOpen, onClose, onSuccess, existingCategories = [] }: AddCategoryModalProps) => {
  const [formData, setFormData] = useState<CreateCategoryRequest>({
    name: ''
  })

  const [errors, setErrors] = useState<Record<string, string>>({})
  const [loading, setLoading] = useState(false)

  const validate = (): boolean => {
    const newErrors: Record<string, string> = {}

    if (!formData.name.trim()) {
      newErrors.name = 'Category name is required'
    } else if (formData.name.trim().length < 2) {
      newErrors.name = 'Category name must be at least 2 characters'
    } else if (formData.name.trim().length > 50) {
      newErrors.name = 'Category name must be less than 50 characters'
    }

    // Check for duplicate names
    if (existingCategories.some(cat => cat.toLowerCase() === formData.name.toLowerCase().trim())) {
      newErrors.name = 'A category with this name already exists'
    }

    // Basic validation for category name format
    if (formData.name.trim() && !/^[a-zA-Z0-9\s\-_&()]+$/.test(formData.name.trim())) {
      newErrors.name = 'Category name contains invalid characters'
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

      const submitData: CreateCategoryRequest = {
        name: formData.name.trim()
      }

      await categoriesService.createCategory(submitData)
      toast.success('Category created successfully')
      onSuccess()
      handleClose()
    } catch (error: any) {
      toast.error(error.response?.data?.message || 'Failed to create category')
    } finally {
      setLoading(false)
    }
  }

  const handleClose = () => {
    setFormData({
      name: ''
    })
    setErrors({})
    onClose()
  }

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
    'Raspberry Pi'
  ]

  const availableSuggestions = suggestedCategories.filter(
    cat => !existingCategories.some(existing => existing.toLowerCase() === cat.toLowerCase())
  )

  return (
    <Modal isOpen={isOpen} onClose={handleClose} title="Add New Category" size="md">
      <form onSubmit={handleSubmit} className="space-y-6">
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
            onChange={(e) => setFormData({ ...formData, name: e.target.value })}
            placeholder="Enter category name"
            maxLength={50}
          />
        </FormField>

        {/* Character count */}
        <div className="text-right">
          <span className={`text-xs ${formData.name.length > 40 ? 'text-orange-500' : 'text-text-secondary'}`}>
            {formData.name.length}/50 characters
          </span>
        </div>

        {/* Suggested categories */}
        {availableSuggestions.length > 0 && (
          <div className="space-y-3">
            <label className="text-sm font-medium text-text-primary">Quick Select</label>
            <div className="flex flex-wrap gap-2">
              {availableSuggestions.slice(0, 8).map((suggestion) => (
                <button
                  key={suggestion}
                  type="button"
                  onClick={() => setFormData({ ...formData, name: suggestion })}
                  className="px-3 py-1 text-sm bg-primary/10 text-primary rounded-full hover:bg-primary/20 transition-colors"
                >
                  {suggestion}
                </button>
              ))}
            </div>
            <p className="text-xs text-text-secondary">
              Click a suggestion to use it, or type your own category name
            </p>
          </div>
        )}

        {/* Preview */}
        {formData.name.trim() && (
          <div className="p-3 bg-background-secondary rounded-md">
            <p className="text-sm text-text-secondary mb-1">Preview:</p>
            <div className="flex items-center gap-2">
              <Tag className="w-4 h-4 text-primary" />
              <span className="text-sm font-medium text-text-primary">
                {formData.name.trim()}
              </span>
            </div>
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
            {loading ? 'Creating...' : 'Create Category'}
          </button>
        </div>
      </form>
    </Modal>
  )
}

export default AddCategoryModal