import { useState, useEffect } from 'react'
import { Plus, Edit, Trash2, Copy, FileText, Sparkles, User } from 'lucide-react'
import { templateService, LabelTemplate } from '@/services/template.service'
import TemplateEditorModal from '@/components/templates/TemplateEditorModal'
import toast from 'react-hot-toast'

const Templates = () => {
  console.log('Templates component rendering...')
  const [templates, setTemplates] = useState<LabelTemplate[]>([])
  const [systemTemplates, setSystemTemplates] = useState<LabelTemplate[]>([])
  const [userTemplates, setUserTemplates] = useState<LabelTemplate[]>([])
  const [loading, setLoading] = useState(false)
  const [selectedCategory, setSelectedCategory] = useState<string>('all')
  const [isEditorOpen, setIsEditorOpen] = useState(false)
  const [editingTemplate, setEditingTemplate] = useState<LabelTemplate | null>(null)

  useEffect(() => {
    loadTemplates()
  }, [])

  const loadTemplates = async () => {
    try {
      setLoading(true)
      console.log('Loading templates...')
      const [system, user] = await Promise.all([
        templateService.getSystemTemplates(),
        templateService.getUserTemplates()
      ])

      console.log('Raw API responses:', { system, user })

      // Ensure we have arrays
      const systemArray = Array.isArray(system) ? system : []
      const userArray = Array.isArray(user) ? user : []

      console.log(`Loaded ${systemArray.length} system templates, ${userArray.length} user templates`)

      setSystemTemplates(systemArray)
      setUserTemplates(userArray)
      setTemplates([...systemArray, ...userArray])

      // Show helpful message if no templates loaded
      if (systemArray.length === 0 && userArray.length === 0) {
        console.warn('No templates loaded. This may be an authentication issue.')
      }
    } catch (error) {
      console.error('Failed to load templates:', error)
      toast.error('Failed to load templates')
    } finally {
      setLoading(false)
    }
  }

  const handleCreate = () => {
    console.log('Create Template button clicked!')
    setEditingTemplate(null)
    setIsEditorOpen(true)
    console.log('Modal should be opening, isEditorOpen set to true')
  }

  const handleEdit = (template: LabelTemplate) => {
    setEditingTemplate(template)
    setIsEditorOpen(true)
  }

  const handleDuplicate = async (template: LabelTemplate) => {
    try {
      await templateService.duplicateTemplate(template.id)
      toast.success(`Template "${template.display_name}" duplicated successfully`)
      loadTemplates()
    } catch (error) {
      toast.error('Failed to duplicate template')
    }
  }

  const handleSave = () => {
    setIsEditorOpen(false)
    setEditingTemplate(null)
    loadTemplates()
  }

  const handleDelete = async (template: LabelTemplate) => {
    if (!confirm(`Are you sure you want to delete "${template.display_name}"?`)) {
      return
    }

    try {
      await templateService.deleteTemplate(template.id)
      toast.success(`Template "${template.display_name}" deleted successfully`)
      loadTemplates()
    } catch (error) {
      toast.error('Failed to delete template')
    }
  }

  const getTemplateIcon = (template: LabelTemplate) => {
    if (template.is_system_template) {
      return <Sparkles className="w-5 h-5 text-yellow-500" />
    }
    return <User className="w-5 h-5 text-blue-500" />
  }

  const getLayoutDescription = (template: LabelTemplate) => {
    const parts = []
    if (template.qr_enabled) parts.push('QR Code')
    if (template.text_template) parts.push('Text')
    if (template.text_rotation !== 'NONE') parts.push(`${template.text_rotation}° rotation`)
    return parts.join(' + ')
  }

  const filteredTemplates = selectedCategory === 'all'
    ? templates
    : selectedCategory === 'system'
    ? systemTemplates
    : userTemplates

  return (
    <div className="container mx-auto px-4 py-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-3xl font-bold text-primary mb-2">Label Templates</h1>
          <p className="text-secondary">Manage your label templates for printing</p>
        </div>
        <button
          onClick={handleCreate}
          className="btn btn-primary flex items-center gap-2 px-6 py-3 text-lg font-semibold shadow-lg hover:shadow-xl transition-all"
        >
          <Plus className="w-5 h-5" />
          Create New Template
        </button>
      </div>

      {/* Category Filter */}
      <div className="flex gap-2 mb-6">
        <button
          onClick={() => setSelectedCategory('all')}
          className={`px-4 py-2 rounded-lg transition-colors ${
            selectedCategory === 'all'
              ? 'bg-primary text-white'
              : 'bg-background-secondary text-secondary hover:bg-background-tertiary'
          }`}
        >
          All Templates ({templates.length})
        </button>
        <button
          onClick={() => setSelectedCategory('system')}
          className={`px-4 py-2 rounded-lg transition-colors ${
            selectedCategory === 'system'
              ? 'bg-primary text-white'
              : 'bg-background-secondary text-secondary hover:bg-background-tertiary'
          }`}
        >
          <div className="flex items-center gap-2">
            <Sparkles className="w-4 h-4" />
            System ({systemTemplates.length})
          </div>
        </button>
        <button
          onClick={() => setSelectedCategory('user')}
          className={`px-4 py-2 rounded-lg transition-colors ${
            selectedCategory === 'user'
              ? 'bg-primary text-white'
              : 'bg-background-secondary text-secondary hover:bg-background-tertiary'
          }`}
        >
          <div className="flex items-center gap-2">
            <User className="w-4 h-4" />
            My Templates ({userTemplates.length})
          </div>
        </button>
      </div>

      {/* Templates Grid */}
      {loading ? (
        <div className="flex items-center justify-center py-12">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
        </div>
      ) : filteredTemplates.length === 0 ? (
        <div className="text-center py-12">
          <FileText className="w-16 h-16 text-muted mx-auto mb-4" />
          <h3 className="text-lg font-semibold text-primary mb-2">No templates found</h3>
          <p className="text-secondary mb-4">
            {selectedCategory === 'user'
              ? 'Create your first custom template to get started'
              : 'No templates available in this category'}
          </p>

          {/* Show helpful message if no system templates loaded */}
          {selectedCategory === 'system' && systemTemplates.length === 0 && (
            <div className="mt-4 p-4 bg-yellow-50 border border-yellow-200 rounded-lg max-w-md mx-auto">
              <p className="text-sm text-yellow-800">
                <strong>Expected 7 system templates</strong> but none loaded.
                <br />
                This usually means an authentication issue.
                <br />
                <br />
                Try:
                <br />
                • Logging out and back in
                <br />
                • Checking browser console (F12) for errors
                <br />
                • Or use "Create Template" to make your own
              </p>
            </div>
          )}
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {filteredTemplates.map((template) => (
            <div
              key={template.id}
              className="bg-background-secondary rounded-lg p-4 hover:shadow-lg transition-shadow"
            >
              {/* Template Header */}
              <div className="flex items-start justify-between mb-3">
                <div className="flex items-center gap-2">
                  {getTemplateIcon(template)}
                  <div>
                    <h3 className="font-semibold text-primary">{template.display_name}</h3>
                    <p className="text-xs text-secondary">{template.category}</p>
                  </div>
                </div>
                {template.is_system_template && (
                  <span className="text-xs bg-yellow-100 text-yellow-800 px-2 py-1 rounded">
                    System
                  </span>
                )}
              </div>

              {/* Description */}
              <p className="text-sm text-secondary mb-3 line-clamp-2">
                {template.description}
              </p>

              {/* Template Details */}
              <div className="space-y-2 mb-4">
                <div className="flex items-center justify-between text-xs">
                  <span className="text-muted">Size:</span>
                  <span className="text-primary font-medium">
                    {template.label_width_mm} × {template.label_height_mm}mm
                  </span>
                </div>
                <div className="flex items-center justify-between text-xs">
                  <span className="text-muted">Layout:</span>
                  <span className="text-primary">{getLayoutDescription(template)}</span>
                </div>
                <div className="flex items-center justify-between text-xs">
                  <span className="text-muted">Used:</span>
                  <span className="text-primary">{template.usage_count} times</span>
                </div>
              </div>

              {/* Template Text Preview */}
              {template.text_template && (
                <div className="bg-background-primary rounded p-2 mb-4">
                  <p className="text-xs text-muted mb-1">Template:</p>
                  <code className="text-xs text-primary break-all">
                    {template.text_template.substring(0, 60)}
                    {template.text_template.length > 60 ? '...' : ''}
                  </code>
                </div>
              )}

              {/* Actions */}
              <div className="flex gap-2">
                {!template.is_system_template && (
                  <>
                    <button
                      onClick={() => handleEdit(template)}
                      className="flex-1 btn btn-secondary flex items-center justify-center gap-2 text-sm"
                    >
                      <Edit className="w-3 h-3" />
                      Edit
                    </button>
                    <button
                      onClick={() => handleDelete(template)}
                      className="btn btn-secondary flex items-center justify-center gap-2 text-sm text-red-600 hover:text-red-700"
                    >
                      <Trash2 className="w-3 h-3" />
                      Delete
                    </button>
                  </>
                )}
                <button
                  onClick={() => handleDuplicate(template)}
                  className="flex-1 btn btn-secondary flex items-center justify-center gap-2 text-sm"
                  title="Duplicate this template to create your own version"
                >
                  <Copy className="w-3 h-3" />
                  Duplicate
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Info Box */}
      <div className="mt-8 bg-blue-50 border border-blue-200 rounded-lg p-4">
        <h4 className="font-semibold text-blue-900 mb-2">💡 Quick Tips</h4>
        <ul className="text-sm text-blue-800 space-y-1">
          <li>• <strong>System Templates</strong> are pre-designed and ready to use</li>
          <li>• <strong>Duplicate</strong> a system template to customize it for your needs</li>
          <li>• <strong>12mm × 39mm</strong> template with QR code is the "MakerMatrix 12mm Box Label"</li>
          <li>• Templates are automatically suggested based on your part data when printing</li>
        </ul>
      </div>

      {/* Template Editor Modal */}
      <TemplateEditorModal
        isOpen={isEditorOpen}
        onClose={() => {
          setIsEditorOpen(false)
          setEditingTemplate(null)
        }}
        template={editingTemplate}
        onSave={handleSave}
      />
    </div>
  )
}

export default Templates