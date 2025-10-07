import { useState, useEffect } from 'react'
import { X, Save, FileText, AlertCircle } from 'lucide-react'
import { CustomSelect } from '@/components/ui/CustomSelect'
import type { LabelTemplate } from '@/services/template.service'
import { templateService } from '@/services/template.service'
import { motion } from 'framer-motion'
import toast from 'react-hot-toast'

interface TemplateEditorModalProps {
  isOpen: boolean
  onClose: () => void
  template?: LabelTemplate | null
  onSave?: () => void
}

const TemplateEditorModal = ({ isOpen, onClose, template, onSave }: TemplateEditorModalProps) => {
  const [formData, setFormData] = useState({
    name: '',
    display_name: '',
    description: '',
    category: 'COMPONENT',
    label_width_mm: 39.0,
    label_height_mm: 12.0,
    text_template: '{part_name}\\n{part_number}',
    text_rotation: 'NONE',
    text_alignment: 'LEFT',
    qr_position: 'LEFT',
    qr_enabled: true,
    enable_multiline: true,
    enable_auto_sizing: true,
    qr_scale: 0.95,
  })

  const [saving, setSaving] = useState(false)
  const [errors, setErrors] = useState<Record<string, string>>({})

  useEffect(() => {
    if (template) {
      // Editing existing template
      setFormData({
        name: template.name,
        display_name: template.display_name,
        description: template.description,
        category: template.category,
        label_width_mm: template.label_width_mm,
        label_height_mm: template.label_height_mm,
        text_template: template.text_template,
        text_rotation: template.text_rotation,
        text_alignment: template.text_alignment,
        qr_position: template.qr_position,
        qr_enabled: template.qr_enabled,
        enable_multiline: template.enable_multiline,
        enable_auto_sizing: template.enable_auto_sizing,
        qr_scale: template.qr_scale,
      })
    } else {
      // Creating new template - reset to defaults
      setFormData({
        name: '',
        display_name: '',
        description: '',
        category: 'COMPONENT',
        label_width_mm: 39.0,
        label_height_mm: 12.0,
        text_template: '{part_name}\\n{part_number}',
        text_rotation: 'NONE',
        text_alignment: 'LEFT',
        qr_position: 'LEFT',
        qr_enabled: true,
        enable_multiline: true,
        enable_auto_sizing: true,
        qr_scale: 0.95,
      })
    }
    setErrors({})
  }, [template, isOpen])

  const validateForm = () => {
    const newErrors: Record<string, string> = {}

    if (!formData.name.trim()) {
      newErrors.name = 'Template name is required'
    }

    if (!formData.display_name.trim()) {
      newErrors.display_name = 'Display name is required'
    }

    if (formData.label_width_mm <= 0) {
      newErrors.label_width_mm = 'Width must be greater than 0'
    }

    if (formData.label_height_mm <= 0) {
      newErrors.label_height_mm = 'Height must be greater than 0'
    }

    if (!formData.text_template.trim() && !formData.qr_enabled) {
      newErrors.text_template = 'Must have either text template or QR code enabled'
    }

    setErrors(newErrors)
    return Object.keys(newErrors).length === 0
  }

  const handleSave = async () => {
    if (!validateForm()) {
      toast.error('Please fix the errors before saving')
      return
    }

    try {
      setSaving(true)

      if (template) {
        // Update existing template
        await templateService.updateTemplate(template.id, formData)
        toast.success('Template updated successfully!')
      } else {
        // Create new template
        await templateService.createTemplate(formData)
        toast.success('Template created successfully!')
      }

      if (onSave) {
        onSave()
      }
      onClose()
    } catch (error) {
      console.error('Failed to save template:', error)
      const err = error as { message?: string }
      toast.error(err.message || 'Failed to save template')
    } finally {
      setSaving(false)
    }
  }

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <motion.div
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        className="modal-container bg-background-primary rounded-lg p-6 w-full max-w-3xl mx-4 max-h-[90vh] overflow-y-auto"
      >
        <div className="flex items-center justify-between mb-6">
          <h4 className="text-xl font-semibold text-primary flex items-center gap-2">
            <FileText className="w-5 h-5" />
            {template ? 'Edit Template' : 'Create New Template'}
          </h4>
          <button onClick={onClose} className="text-secondary hover:text-primary">
            <X className="w-6 h-6" />
          </button>
        </div>

        <div className="space-y-4">
          {/* Basic Information */}
          <div className="bg-background-secondary rounded-lg p-4">
            <h5 className="font-medium text-primary mb-3">Basic Information</h5>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-primary mb-1">
                  Template Name (ID) *
                </label>
                <input
                  type="text"
                  className={`input w-full ${errors.name ? 'border-red-500' : ''}`}
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  placeholder="my_template_name"
                  disabled={!!template} // Can't change name when editing
                />
                {errors.name && <p className="text-xs text-red-500 mt-1">{errors.name}</p>}
                <p className="text-xs text-secondary mt-1">Unique identifier (no spaces)</p>
              </div>

              <div>
                <label className="block text-sm font-medium text-primary mb-1">
                  Display Name *
                </label>
                <input
                  type="text"
                  className={`input w-full ${errors.display_name ? 'border-red-500' : ''}`}
                  value={formData.display_name}
                  onChange={(e) => setFormData({ ...formData, display_name: e.target.value })}
                  placeholder="My Custom Template"
                />
                {errors.display_name && (
                  <p className="text-xs text-red-500 mt-1">{errors.display_name}</p>
                )}
              </div>
            </div>

            <div className="mt-4">
              <label className="block text-sm font-medium text-primary mb-1">Description</label>
              <textarea
                className="input w-full h-20 resize-none"
                value={formData.description}
                onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                placeholder="Describe when to use this template..."
              />
            </div>

            <div className="mt-4">
              <label className="block text-sm font-medium text-primary mb-1">Category</label>
              <CustomSelect
                value={formData.category}
                onChange={(val) => setFormData({ ...formData, category: val })}
                options={[
                  { value: 'COMPONENT', label: 'Component' },
                  { value: 'LOCATION', label: 'Location' },
                  { value: 'STORAGE', label: 'Storage' },
                  { value: 'CABLE', label: 'Cable' },
                  { value: 'INVENTORY', label: 'Inventory' },
                  { value: 'CUSTOM', label: 'Custom' },
                ]}
                placeholder="Select category"
              />
            </div>
          </div>

          {/* Label Size */}
          <div className="bg-background-secondary rounded-lg p-4">
            <h5 className="font-medium text-primary mb-3">Label Size</h5>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-primary mb-1">Width (mm) *</label>
                <input
                  type="number"
                  step="0.1"
                  min="1"
                  className={`input w-full ${errors.label_width_mm ? 'border-red-500' : ''}`}
                  value={formData.label_width_mm}
                  onChange={(e) =>
                    setFormData({ ...formData, label_width_mm: parseFloat(e.target.value) })
                  }
                />
                {errors.label_width_mm && (
                  <p className="text-xs text-red-500 mt-1">{errors.label_width_mm}</p>
                )}
              </div>

              <div>
                <label className="block text-sm font-medium text-primary mb-1">Height (mm) *</label>
                <input
                  type="number"
                  step="0.1"
                  min="1"
                  className={`input w-full ${errors.label_height_mm ? 'border-red-500' : ''}`}
                  value={formData.label_height_mm}
                  onChange={(e) =>
                    setFormData({ ...formData, label_height_mm: parseFloat(e.target.value) })
                  }
                />
                {errors.label_height_mm && (
                  <p className="text-xs text-red-500 mt-1">{errors.label_height_mm}</p>
                )}
              </div>
            </div>

            <div className="mt-2 p-2 bg-blue-50 border border-blue-200 rounded">
              <p className="text-xs text-blue-800">
                Common sizes: 12mm (12×39mm), 29mm (29×90mm), 62mm (62×100mm)
              </p>
            </div>
          </div>

          {/* Text Configuration */}
          <div className="bg-background-secondary rounded-lg p-4">
            <h5 className="font-medium text-primary mb-3">Text Configuration</h5>

            <div>
              <label className="block text-sm font-medium text-primary mb-1">Text Template</label>
              <textarea
                className={`input w-full h-24 resize-none font-mono text-sm ${errors.text_template ? 'border-red-500' : ''}`}
                value={formData.text_template}
                onChange={(e) => setFormData({ ...formData, text_template: e.target.value })}
                placeholder="{part_name}\n{part_number}\n{location}"
              />
              {errors.text_template && (
                <p className="text-xs text-red-500 mt-1">{errors.text_template}</p>
              )}
              <p className="text-xs text-secondary mt-1">
                Use variables: {'{part_name}'}, {'{part_number}'}, {'{location}'}, {'{category}'},
                etc.
                <br />
                Use \n for line breaks
              </p>
            </div>

            <div className="grid grid-cols-2 gap-4 mt-4">
              <div>
                <label className="block text-sm font-medium text-primary mb-1">Text Rotation</label>
                <CustomSelect
                  value={formData.text_rotation}
                  onChange={(val) => setFormData({ ...formData, text_rotation: val })}
                  options={[
                    { value: 'NONE', label: '0° (None)' },
                    { value: '90', label: '90° Clockwise' },
                    { value: '180', label: '180° Upside Down' },
                    { value: '270', label: '270° (90° Counter-Clockwise)' },
                  ]}
                  placeholder="Select rotation"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-primary mb-1">
                  Text Alignment
                </label>
                <CustomSelect
                  value={formData.text_alignment}
                  onChange={(val) => setFormData({ ...formData, text_alignment: val })}
                  options={[
                    { value: 'LEFT', label: 'Left' },
                    { value: 'CENTER', label: 'Center' },
                    { value: 'RIGHT', label: 'Right' },
                  ]}
                  placeholder="Select alignment"
                />
              </div>
            </div>

            <div className="flex gap-4 mt-4">
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={formData.enable_multiline}
                  onChange={(e) => setFormData({ ...formData, enable_multiline: e.target.checked })}
                  className="w-4 h-4"
                />
                <span className="text-sm text-primary">Enable multi-line</span>
              </label>

              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={formData.enable_auto_sizing}
                  onChange={(e) =>
                    setFormData({ ...formData, enable_auto_sizing: e.target.checked })
                  }
                  className="w-4 h-4"
                />
                <span className="text-sm text-primary">Auto-size text</span>
              </label>
            </div>
          </div>

          {/* QR Code Configuration */}
          <div className="bg-background-secondary rounded-lg p-4">
            <h5 className="font-medium text-primary mb-3">QR Code Configuration</h5>

            <label className="flex items-center gap-2 cursor-pointer mb-4">
              <input
                type="checkbox"
                checked={formData.qr_enabled}
                onChange={(e) => setFormData({ ...formData, qr_enabled: e.target.checked })}
                className="w-4 h-4"
              />
              <span className="text-sm font-medium text-primary">Include QR Code</span>
            </label>

            {formData.qr_enabled && (
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-primary mb-1">QR Position</label>
                  <CustomSelect
                    value={formData.qr_position}
                    onChange={(val) => setFormData({ ...formData, qr_position: val })}
                    options={[
                      { value: 'LEFT', label: 'Left' },
                      { value: 'RIGHT', label: 'Right' },
                      { value: 'TOP', label: 'Top' },
                      { value: 'BOTTOM', label: 'Bottom' },
                      { value: 'CENTER', label: 'Center' },
                      { value: 'TOP_LEFT', label: 'Top Left Corner' },
                      { value: 'TOP_RIGHT', label: 'Top Right Corner' },
                      { value: 'BOTTOM_LEFT', label: 'Bottom Left Corner' },
                    ]}
                    placeholder="Select QR position"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-primary mb-1">QR Scale</label>
                  <input
                    type="number"
                    step="0.05"
                    min="0.5"
                    max="1.0"
                    className="input w-full"
                    value={formData.qr_scale}
                    onChange={(e) =>
                      setFormData({ ...formData, qr_scale: parseFloat(e.target.value) })
                    }
                  />
                  <p className="text-xs text-secondary mt-1">0.5 = 50%, 1.0 = 100%</p>
                </div>
              </div>
            )}
          </div>

          {/* Warning for system templates */}
          {template?.is_system_template && (
            <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-3 flex items-start gap-2">
              <AlertCircle className="w-5 h-5 text-yellow-600 flex-shrink-0 mt-0.5" />
              <div className="text-sm text-yellow-800">
                <strong>Note:</strong> This is a system template. Your changes will create a new
                user template. System templates cannot be directly modified.
              </div>
            </div>
          )}
        </div>

        {/* Action Buttons */}
        <div className="flex gap-3 mt-6 pt-4 border-t border-border">
          <button onClick={onClose} className="flex-1 btn btn-secondary" disabled={saving}>
            Cancel
          </button>
          <button
            onClick={handleSave}
            className="flex-1 btn btn-primary flex items-center justify-center gap-2"
            disabled={saving}
          >
            {saving ? (
              <>
                <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
                Saving...
              </>
            ) : (
              <>
                <Save className="w-4 h-4" />
                {template ? 'Update Template' : 'Create Template'}
              </>
            )}
          </button>
        </div>
      </motion.div>
    </div>
  )
}

export default TemplateEditorModal
