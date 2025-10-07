import { useState } from 'react'
import { Save, X, Hash, Plus, Link as LinkIcon } from 'lucide-react'
import Modal from '@/components/ui/Modal'
import FormField from '@/components/ui/FormField'
import ImageUpload from '@/components/ui/ImageUpload'
import { projectsService } from '@/services/projects.service'
import { ProjectCreate } from '@/types/projects'
import toast from 'react-hot-toast'

interface AddProjectModalProps {
  isOpen: boolean
  onClose: () => void
  onSuccess: () => void
  existingProjects?: string[]
}

const AddProjectModal = ({
  isOpen,
  onClose,
  onSuccess,
  existingProjects = [],
}: AddProjectModalProps) => {
  const [formData, setFormData] = useState<ProjectCreate>({
    name: '',
    description: '',
    status: 'planning',
  })
  const [imageUrl, setImageUrl] = useState<string>('')
  const [links, setLinks] = useState<Array<{ key: string; value: string }>>([])
  const [errors, setErrors] = useState<Record<string, string>>({})
  const [loading, setLoading] = useState(false)

  const validate = (): boolean => {
    const newErrors: Record<string, string> = {}

    if (!formData.name?.trim()) {
      newErrors.name = 'Project name is required'
    } else if (existingProjects.some((p) => p.toLowerCase() === formData.name.toLowerCase())) {
      newErrors.name = 'A project with this name already exists'
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

      // Prepare links object
      const linksObject: Record<string, string> = {}
      links.forEach(({ key, value }) => {
        if (key.trim() && value.trim()) {
          linksObject[key.trim()] = value.trim()
        }
      })

      const submitData: ProjectCreate = {
        ...formData,
        image_url: imageUrl || undefined,
        links: Object.keys(linksObject).length > 0 ? linksObject : undefined,
      }

      await projectsService.createProject(submitData)
      toast.success('Project created successfully')
      handleClose()
      onSuccess()
    } catch (error: any) {
      console.error('Failed to create project:', error)
      const errorMessage =
        error.response?.data?.detail ||
        error.response?.data?.message ||
        error.message ||
        'Failed to create project'
      toast.error(errorMessage)
    } finally {
      setLoading(false)
    }
  }

  const handleClose = () => {
    setFormData({
      name: '',
      description: '',
      status: 'planning',
    })
    setImageUrl('')
    setLinks([])
    setErrors({})
    onClose()
  }

  const addLink = () => {
    setLinks([...links, { key: '', value: '' }])
  }

  const updateLink = (index: number, field: 'key' | 'value', value: string) => {
    const updated = [...links]
    updated[index][field] = value
    setLinks(updated)
  }

  const removeLink = (index: number) => {
    setLinks(links.filter((_, i) => i !== index))
  }

  return (
    <Modal isOpen={isOpen} onClose={handleClose} title="Add New Project" size="lg">
      <form onSubmit={handleSubmit} className="space-y-4">
        <FormField label="Project Name" required error={errors.name}>
          <div className="relative">
            <Hash className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-muted" />
            <input
              type="text"
              className="input w-full pl-10"
              value={formData.name}
              onChange={(e) => setFormData({ ...formData, name: e.target.value })}
              placeholder="e.g., golfcart-harness"
              autoFocus
            />
          </div>
          <p className="text-xs text-muted mt-1">
            Use lowercase with hyphens for hashtag-like names
          </p>
        </FormField>

        <FormField label="Description" error={errors.description}>
          <textarea
            className="input w-full min-h-[80px] resize-y"
            value={formData.description}
            onChange={(e) => setFormData({ ...formData, description: e.target.value })}
            placeholder="Brief description of the project (optional)"
            rows={3}
          />
        </FormField>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <FormField label="Status" error={errors.status}>
            <select
              className="input w-full"
              value={formData.status}
              onChange={(e) => setFormData({ ...formData, status: e.target.value as any })}
            >
              <option value="planning">Planning</option>
              <option value="active">Active</option>
              <option value="completed">Completed</option>
              <option value="archived">Archived</option>
            </select>
          </FormField>

          <FormField label="Project Image" description="Upload an image for the project">
            <ImageUpload
              onImageUploaded={setImageUrl}
              currentImageUrl={imageUrl}
              placeholder="Upload project image"
              className="w-full"
            />
          </FormField>
        </div>

        {/* Links Section */}
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <label className="text-sm font-medium text-primary">Links</label>
            <button
              type="button"
              onClick={addLink}
              className="btn btn-secondary btn-sm flex items-center gap-1"
            >
              <Plus className="w-3 h-3" />
              Add Link
            </button>
          </div>

          {links.map((link, index) => (
            <div key={index} className="flex gap-2">
              <input
                type="text"
                placeholder="Link name (e.g., GitHub)"
                className="input flex-1"
                value={link.key}
                onChange={(e) => updateLink(index, 'key', e.target.value)}
              />
              <input
                type="url"
                placeholder="URL (e.g., https://github.com/...)"
                className="input flex-1"
                value={link.value}
                onChange={(e) => updateLink(index, 'value', e.target.value)}
              />
              <button
                type="button"
                onClick={() => removeLink(index)}
                className="btn btn-secondary btn-sm"
              >
                <X className="w-3 h-3" />
              </button>
            </div>
          ))}

          {links.length === 0 && (
            <p className="text-sm text-secondary">
              No links added. Click "Add Link" to include project-related URLs (GitHub,
              documentation, etc.)
            </p>
          )}
        </div>

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
            {loading ? 'Creating...' : 'Create Project'}
          </button>
        </div>
      </form>
    </Modal>
  )
}

export default AddProjectModal
