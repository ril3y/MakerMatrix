import { useState, useEffect, useCallback } from 'react'
import { X, Save, FileText, AlertCircle, RefreshCw } from 'lucide-react'
import { CustomSelect } from '@/components/ui/CustomSelect'
import type { LabelTemplate } from '@/services/template.service'
import { templateService } from '@/services/template.service'
import { settingsService } from '@/services/settings.service'
import type { LabelSize } from '@/types/settings'
import LabelPreview from '@/components/printer/LabelPreview'
import { motion } from 'framer-motion'
import toast from 'react-hot-toast'

interface TemplateEditorModalProps {
  isOpen: boolean
  onClose: () => void
  template?: LabelTemplate | null
  onSave?: () => void
}

/** Generate a slug ID from a display name (lowercase, underscores, no special chars). */
function generateTemplateId(displayName: string): string {
  return displayName
    .toLowerCase()
    .replace(/[^a-z0-9]/g, '_')
    .replace(/_+/g, '_')
    .replace(/^_|_$/g, '')
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
  const [supportedSizes, setSupportedSizes] = useState<LabelSize[]>([])
  const [selectedSizeKey, setSelectedSizeKey] = useState('')
  const [previewUrl, setPreviewUrl] = useState<string | null>(null)
  const [previewLoading, setPreviewLoading] = useState(false)

  // Fetch printer supported sizes on modal open
  useEffect(() => {
    if (!isOpen) return

    const loadPrinterSizes = async () => {
      try {
        const printers = await settingsService.getAvailablePrinters()
        if (printers.length > 0) {
          const info = await settingsService.getPrinterInfo(printers[0].printer_id)
          if (info.supported_sizes?.length) {
            setSupportedSizes(info.supported_sizes)
          }
        }
      } catch {
        // Printer not available — sizes will be empty, user can still type manually
      }
    }

    loadPrinterSizes()
  }, [isOpen])

  useEffect(() => {
    if (template) {
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
      setSelectedSizeKey('')
    } else {
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
      setSelectedSizeKey('')
    }
    setErrors({})
    setPreviewUrl(null)
  }, [template, isOpen])

  // When supported sizes load, try to match the current dimensions to a size.
  // Template convention: label_height_mm = tape width, label_width_mm = label length.
  // Printer sizes: width_mm = tape width, height_mm = die-cut length (0 for continuous).
  useEffect(() => {
    if (supportedSizes.length === 0) return
    const match = supportedSizes.find(
      (s) =>
        s.width_mm === formData.label_height_mm &&
        (s.is_continuous || s.height_mm === formData.label_width_mm)
    )
    if (match) {
      setSelectedSizeKey(match.name)
    }
  }, [supportedSizes, formData.label_width_mm, formData.label_height_mm])

  const handleSizeChange = (sizeName: string) => {
    setSelectedSizeKey(sizeName)
    const size = supportedSizes.find((s) => s.name === sizeName)
    if (size) {
      setFormData((prev) => ({
        ...prev,
        // tape width → label_height_mm, die-cut length → label_width_mm
        label_height_mm: size.width_mm,
        label_width_mm: size.is_continuous ? prev.label_width_mm : size.height_mm,
      }))
    }
  }

  const sizeOptions = supportedSizes.map((size) => ({
    value: size.name,
    label: size.is_continuous
      ? `${size.name} - ${size.width_mm}mm continuous`
      : `${size.name} - ${size.width_mm}x${size.height_mm}mm`,
  }))

  // --- Preview generation ---
  const generatePreview = useCallback(async () => {
    const tpl = formData.text_template.trim()
    if (!tpl) return
    if (formData.label_width_mm <= 0 || formData.label_height_mm <= 0) return

    try {
      setPreviewLoading(true)

      const testData = {
        id: 'preview-id-12345',
        part_name: 'Test Part',
        part_number: 'TP-001',
        emoji: '🔧',
        location: 'A1-B2',
        category: 'Electronics',
        quantity: '10',
        description: 'Sample part for preview',
      }

      // Use the draft template preview endpoint — sends ALL template
      // properties (rotation, alignment, qr_position, etc.) so the
      // preview matches what will actually print.
      const blob = await templateService.previewTemplateDraft(formData, testData)

      const url = URL.createObjectURL(blob)
      setPreviewUrl((prev) => {
        if (prev) URL.revokeObjectURL(prev)
        return url
      })
    } catch (error) {
      console.error('Preview error:', error)
      // Silently fail for preview — don't toast on every keystroke
      setPreviewUrl(null)
    } finally {
      setPreviewLoading(false)
    }
  }, [formData])

  // Auto-generate preview with debounce
  useEffect(() => {
    if (!isOpen) return

    const timeoutId = setTimeout(() => {
      generatePreview()
    }, 800)

    return () => clearTimeout(timeoutId)
  }, [isOpen, generatePreview])

  // Cleanup blob URL on unmount
  useEffect(() => {
    return () => {
      if (previewUrl) URL.revokeObjectURL(previewUrl)
    }
  }, [previewUrl])

  const validateForm = () => {
    const newErrors: Record<string, string> = {}

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

      const saveData = {
        ...formData,
        name: template ? formData.name : generateTemplateId(formData.display_name),
      }

      if (template) {
        await templateService.updateTemplate(template.id, saveData)
        toast.success('Template updated successfully!')
      } else {
        await templateService.createTemplate(saveData)
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
        className="modal-container bg-background-primary rounded-lg w-full max-w-5xl mx-4 max-h-[90vh] flex flex-col"
      >
        {/* Header */}
        <div className="flex items-center justify-between p-6 pb-0 mb-4">
          <h4 className="text-xl font-semibold text-primary flex items-center gap-2">
            <FileText className="w-5 h-5" />
            {template ? 'Edit Template' : 'Create New Template'}
          </h4>
          <button onClick={onClose} className="text-secondary hover:text-primary">
            <X className="w-6 h-6" />
          </button>
        </div>

        {/* Two-column content area */}
        <div className="flex-1 overflow-y-auto px-6 pb-4">
          <div className="grid grid-cols-1 lg:grid-cols-5 gap-6">
            {/* Left Column - Form (3/5 width) */}
            <div className="lg:col-span-3 space-y-4">
              {/* Basic Information */}
              <div className="bg-background-secondary rounded-lg p-4">
                <h5 className="font-medium text-primary mb-3">Basic Information</h5>

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
                  {!template && formData.display_name.trim() && (
                    <p className="text-xs text-secondary mt-1">
                      ID: {generateTemplateId(formData.display_name)}
                    </p>
                  )}
                </div>

                <div className="mt-4">
                  <label className="block text-sm font-medium text-primary mb-1">Description</label>
                  <textarea
                    className="input w-full h-16 resize-none"
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
                      {
                        value: 'COMPONENT',
                        label: 'Component - Labels for electronic parts, ICs, resistors, etc.',
                      },
                      {
                        value: 'LOCATION',
                        label: 'Location - Labels for storage locations, shelves, bins',
                      },
                      {
                        value: 'STORAGE',
                        label: 'Storage - Labels for containers, reels, cassettes',
                      },
                      {
                        value: 'CABLE',
                        label: 'Cable - Labels for cables and wire harnesses',
                      },
                      {
                        value: 'INVENTORY',
                        label: 'Inventory - Labels for inventory tracking and audits',
                      },
                      {
                        value: 'CUSTOM',
                        label: 'Custom - Custom label format',
                      },
                    ]}
                    placeholder="Select category"
                  />
                </div>
              </div>

              {/* Label Size */}
              <div className="bg-background-secondary rounded-lg p-4">
                <h5 className="font-medium text-primary mb-3">Label Size</h5>

                {sizeOptions.length > 0 ? (
                  <CustomSelect
                    value={selectedSizeKey}
                    onChange={handleSizeChange}
                    options={sizeOptions}
                    placeholder="Select a label size..."
                  />
                ) : (
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="block text-sm font-medium text-primary mb-1">
                        Width (mm)
                      </label>
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
                      <label className="block text-sm font-medium text-primary mb-1">
                        Height (mm)
                      </label>
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
                )}

                {selectedSizeKey && (
                  <p className="text-xs text-secondary mt-2">
                    {formData.label_height_mm}mm tape, {formData.label_width_mm}mm length
                  </p>
                )}
              </div>

              {/* Text Template */}
              <div className="bg-background-secondary rounded-lg p-4">
                <h5 className="font-medium text-primary mb-3">Text Template</h5>

                <div>
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
                    Use variables: {'{part_name}'}, {'{part_number}'}, {'{location}'},{' '}
                    {'{category}'}, etc. Use \n for line breaks.
                  </p>
                </div>
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

            {/* Right Column - Preview & Layout Options (2/5 width) */}
            <div className="lg:col-span-2 space-y-4">
              {/* Preview */}
              <div>
                <div className="flex items-center justify-between mb-2">
                  <h5 className="font-medium text-primary">Preview</h5>
                  <button
                    onClick={generatePreview}
                    className="text-xs text-secondary hover:text-primary flex items-center gap-1"
                    disabled={previewLoading}
                  >
                    <RefreshCw className={`w-3 h-3 ${previewLoading ? 'animate-spin' : ''}`} />
                    Refresh
                  </button>
                </div>

                <LabelPreview
                  previewUrl={previewUrl}
                  loading={previewLoading}
                  emptyMessage="Configure your template to see a live preview"
                  caption="Label Preview"
                />

                <p className="text-xs text-secondary mt-2">
                  Preview uses sample data: "Test Part" (TP-001) at location A1-B2
                </p>
              </div>

              {/* Text Layout Options */}
              <div className="bg-background-secondary rounded-lg p-4">
                <h5 className="font-medium text-primary mb-3">Text Options</h5>

                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="block text-xs font-medium text-primary mb-1">Rotation</label>
                    <CustomSelect
                      value={formData.text_rotation}
                      onChange={(val) => setFormData({ ...formData, text_rotation: val })}
                      options={[
                        { value: 'NONE', label: '0° (None)' },
                        { value: '90', label: '90°' },
                        { value: '180', label: '180°' },
                        { value: '270', label: '270°' },
                      ]}
                      placeholder="Rotation"
                    />
                  </div>

                  <div>
                    <label className="block text-xs font-medium text-primary mb-1">Alignment</label>
                    <CustomSelect
                      value={formData.text_alignment}
                      onChange={(val) => setFormData({ ...formData, text_alignment: val })}
                      options={[
                        { value: 'LEFT', label: 'Left' },
                        { value: 'CENTER', label: 'Center' },
                        { value: 'RIGHT', label: 'Right' },
                      ]}
                      placeholder="Alignment"
                    />
                  </div>
                </div>

                <div className="flex gap-4 mt-3">
                  <label className="flex items-center gap-2 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={formData.enable_multiline}
                      onChange={(e) =>
                        setFormData({ ...formData, enable_multiline: e.target.checked })
                      }
                      className="w-4 h-4"
                    />
                    <span className="text-sm text-primary">Multi-line</span>
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
                    <span className="text-sm text-primary">Auto-size</span>
                  </label>
                </div>
              </div>

              {/* QR Code Configuration */}
              <div className="bg-background-secondary rounded-lg p-4">
                <h5 className="font-medium text-primary mb-3">QR Code</h5>

                <label className="flex items-center gap-2 cursor-pointer mb-3">
                  <input
                    type="checkbox"
                    checked={formData.qr_enabled}
                    onChange={(e) => setFormData({ ...formData, qr_enabled: e.target.checked })}
                    className="w-4 h-4"
                  />
                  <span className="text-sm font-medium text-primary">Include QR Code</span>
                </label>

                {formData.qr_enabled && (
                  <div className="grid grid-cols-2 gap-3">
                    <div>
                      <label className="block text-xs font-medium text-primary mb-1">Position</label>
                      <CustomSelect
                        value={formData.qr_position}
                        onChange={(val) => setFormData({ ...formData, qr_position: val })}
                        options={[
                          { value: 'LEFT', label: 'Left' },
                          { value: 'RIGHT', label: 'Right' },
                          { value: 'TOP', label: 'Top' },
                          { value: 'BOTTOM', label: 'Bottom' },
                          { value: 'CENTER', label: 'Center' },
                          { value: 'TOP_LEFT', label: 'Top Left' },
                          { value: 'TOP_RIGHT', label: 'Top Right' },
                          { value: 'BOTTOM_LEFT', label: 'Bottom Left' },
                        ]}
                        placeholder="Position"
                      />
                    </div>

                    <div>
                      <label className="block text-xs font-medium text-primary mb-1">Scale</label>
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
                      <p className="text-xs text-secondary mt-1">0.5–1.0</p>
                    </div>
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>

        {/* Action Buttons */}
        <div className="flex gap-3 px-6 py-4 border-t border-border bg-background-primary rounded-b-lg">
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
