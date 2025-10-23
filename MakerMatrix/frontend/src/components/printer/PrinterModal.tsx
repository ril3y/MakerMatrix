import { motion } from 'framer-motion'
import { useState, useEffect, useRef } from 'react'
import { X, Printer, TestTube, FileText, HelpCircle } from 'lucide-react'
import { CustomSelect } from '@/components/ui/CustomSelect'
import { settingsService } from '@/services/settings.service'
import type { LabelTemplate } from '@/services/template.service'
import { templateService } from '@/services/template.service'
import TemplateSelector from './TemplateSelector'
import toast from 'react-hot-toast'

interface LabelSize {
  name: string
  [key: string]: unknown
}

interface PrinterInfo {
  supported_sizes?: LabelSize[]
  [key: string]: unknown
}

interface AvailablePrinter {
  printer_id: string
  name?: string
  [key: string]: unknown
}

interface PrinterModalProps {
  isOpen: boolean
  onClose: () => void
  title?: string
  showTestMode?: boolean
  partData?: {
    id?: string
    part_name?: string
    part_number?: string
    emoji?: string
    location?: string
    category?: string
    quantity?: string
    description?: string
    additional_properties?: Record<string, unknown>
  }
}

const PrinterModal = ({
  isOpen,
  onClose,
  title = 'Print Label',
  showTestMode = false,
  partData,
}: PrinterModalProps) => {
  const [availablePrinters, setAvailablePrinters] = useState<AvailablePrinter[]>([])
  const [selectedPrinter, setSelectedPrinter] = useState<string>('')
  const [printerInfo, setPrinterInfo] = useState<PrinterInfo | null>(null)
  const [selectedTemplate, setSelectedTemplate] = useState<LabelTemplate | null>(null)
  const [labelTemplate, setLabelTemplate] = useState('{part_name}')
  const [selectedLabelSize, setSelectedLabelSize] = useState('12mm')
  const [labelLength, setLabelLength] = useState(39)
  const [previewUrl, setPreviewUrl] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)
  const [useTemplateSystem, setUseTemplateSystem] = useState(true)
  const [editingTemplateId, setEditingTemplateId] = useState<string | null>(null)
  const [editingTemplateName, setEditingTemplateName] = useState<string | null>(null)
  const [showTemplateSyntaxHelp, setShowTemplateSyntaxHelp] = useState(false)
  const [fontSizeOverride, setFontSizeOverride] = useState<number | null>(null)
  const reloadTemplatesRef = useRef<(() => Promise<void>) | null>(null)

  // Load custom template from localStorage on mount
  useEffect(() => {
    const savedTemplate = localStorage.getItem('makermatrix_custom_label_template')
    if (savedTemplate) {
      setLabelTemplate(savedTemplate)
    }
  }, [])

  // Save custom template to localStorage whenever it changes
  useEffect(() => {
    if (labelTemplate && !selectedTemplate) {
      localStorage.setItem('makermatrix_custom_label_template', labelTemplate)
    }
  }, [labelTemplate, selectedTemplate])

  useEffect(() => {
    if (isOpen) {
      loadPrinters()
      // Reset template selection when modal opens
      setSelectedTemplate(null)
      setUseTemplateSystem(true)
      // Load saved template from localStorage or use default
      const savedTemplate = localStorage.getItem('makermatrix_custom_label_template')
      if (savedTemplate) {
        setLabelTemplate(savedTemplate)
      } else if (partData) {
        setLabelTemplate('{part_name}')
      } else {
        setLabelTemplate('Test Label')
      }
      // Clear preview when modal opens
      setPreviewUrl(null)
    }
  }, [isOpen, partData])

  // Auto-generate preview when template configuration changes
  useEffect(() => {
    if (!isOpen) return

    // Only auto-preview if we have a template or custom text and label size
    const hasTemplate = selectedTemplate || (labelTemplate && labelTemplate.trim())
    if (!hasTemplate || !selectedLabelSize) return

    // Debounce the preview generation to avoid too many API calls
    const timeoutId = setTimeout(() => {
      generatePreview()
    }, 800) // 800ms delay after last change

    return () => clearTimeout(timeoutId)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedTemplate, labelTemplate, selectedLabelSize, labelLength, fontSizeOverride, isOpen])

  const handleTemplateSelect = (template: LabelTemplate | null) => {
    setSelectedTemplate(template)
    if (template) {
      // Use template system for printing/preview
      setUseTemplateSystem(true)
      // Update label size to match template
      setSelectedLabelSize(`${template.label_height_mm}mm`)
      setLabelLength(template.label_width_mm)
    } else {
      // Use legacy custom template system
      setUseTemplateSystem(false)
    }
    // Clear preview when template changes
    setPreviewUrl(null)
  }

  const loadPrinters = async () => {
    try {
      setLoading(true)
      const printers = await settingsService.getAvailablePrinters()
      setAvailablePrinters(printers)

      if (printers.length > 0 && !selectedPrinter && printers[0].printer_id) {
        setSelectedPrinter(printers[0].printer_id)
        await loadPrinterInfo(printers[0].printer_id)
      }
    } catch {
      toast.error('Failed to load printers')
    } finally {
      setLoading(false)
    }
  }

  const loadPrinterInfo = async (printerId: string) => {
    try {
      const info = await settingsService.getPrinterInfo(printerId)
      setPrinterInfo(info)

      if (info.supported_sizes && info.supported_sizes.length > 0) {
        const defaultSize =
          info.supported_sizes.find((s: LabelSize) => s.name === '12mm') ||
          info.supported_sizes.find((s: LabelSize) => s.name === '12') ||
          info.supported_sizes[0]
        setSelectedLabelSize(defaultSize.name)
      }
    } catch {
      toast.error('Failed to load printer information')
    }
  }

  const handlePrinterChange = async (printerId: string) => {
    setSelectedPrinter(printerId)
    await loadPrinterInfo(printerId)
  }

  const processLabelTemplate = (template: string) => {
    const data = partData || {
      part_name: 'Test Part',
      part_number: 'TP-001',
      location: 'A1-B2',
      category: 'Electronics',
      quantity: '10',
      description: 'Test part description',
      additional_properties: {},
    }

    let processed = template

    // Replace standard placeholders
    Object.entries(data).forEach(([key, value]) => {
      if (key !== 'additional_properties') {
        processed = processed.replace(new RegExp(`\\{${key}\\}`, 'g'), String(value || ''))
      }
    })

    // Handle additional_properties placeholders (e.g., {additional_properties.manufacturer})
    if (data.additional_properties && typeof data.additional_properties === 'object') {
      Object.entries(data.additional_properties).forEach(([key, value]) => {
        // Support both formats: {additional_properties.key} and {key} for direct access
        processed = processed.replace(
          new RegExp(`\\{additional_properties\\.${key}\\}`, 'g'),
          String(value || '')
        )
        // Also support direct access to additional_properties fields
        if (!Object.prototype.hasOwnProperty.call(data, key)) {
          processed = processed.replace(new RegExp(`\\{${key}\\}`, 'g'), String(value || ''))
        }
      })
    }

    // Remove QR placeholders from display text (QR will be shown in preview image)
    processed = processed.replace(/\{qr=[^}]+\}/g, '')
    processed = processed.replace(/\{qr\}/g, '')

    return processed
  }

  const extractQRInfo = (template: string) => {
    const data = partData || { id: 'test-id', part_number: 'TP-001' }

    // Check for {qr=data} pattern
    const qrWithDataMatch = template.match(/\{qr=([^}]+)\}/)
    if (qrWithDataMatch) {
      const qrDataKey = qrWithDataMatch[1]
      const qrValue = data[qrDataKey as keyof typeof data] || qrDataKey
      return `QR Data: ${qrValue}`
    }

    // Check for plain {qr}
    if (template.includes('{qr}')) {
      const mmId = data.id || 'test-id'
      return `QR Data: MM:${mmId}`
    }

    return null
  }

  const generatePreview = async () => {
    try {
      const testData = partData || {
        id: 'test-part-id-12345',
        part_name: 'Test Part',
        part_number: 'TP-001',
        emoji: '🔧',
        location: 'A1-B2',
        category: 'Electronics',
        quantity: '10',
        description: 'Test part description',
        additional_properties: {},
      }

      let blob: Blob

      // Determine which preview method to use (same logic as print)
      if (selectedTemplate) {
        // Use saved template system
        blob = await templateService.previewTemplate({
          template_id: selectedTemplate.id,
          data: testData,
        })
      } else if (labelTemplate.trim()) {
        // Use custom template text
        const requestData = {
          template: labelTemplate,
          text: '', // Not used anymore
          label_size: selectedLabelSize,
          label_length: selectedLabelSize.includes('mm') ? labelLength : undefined,
          options: {
            font_size_override: fontSizeOverride,
          },
          data: testData,
        }
        blob = await settingsService.previewAdvancedLabel(requestData)
      } else {
        // No template and no custom text
        toast.error('Please select a template or enter custom label text')
        return
      }

      const url = URL.createObjectURL(blob)
      setPreviewUrl(url)
    } catch (error) {
      const err = error as {
        response?: { data?: { message?: string; detail?: string }; status?: number }
        message?: string
      }
      console.error('Preview error:', error)

      // Extract user-friendly error message
      let errorMessage = 'Failed to generate preview'

      if (error instanceof Error) {
        const message = error.message

        // Check for field not found error
        if (message.includes('not found in data')) {
          // Extract field name from error message
          const fieldMatch = message.match(/Field '([^']+)' not found/)
          if (fieldMatch) {
            const fieldName = fieldMatch[1]
            errorMessage = `QR field '{${fieldName}}' does not exist in part data`
          } else {
            errorMessage = message
          }
        }
        // Check for QR data too long error
        else if (message.includes('QR data too long')) {
          const lengthMatch = message.match(/(\d+) characters \(max (\d+)/)
          if (lengthMatch) {
            const [, actual, max] = lengthMatch
            errorMessage = `QR code data too long (${actual} chars, max ${max} for 11mm label)`
          } else {
            errorMessage = 'QR code data exceeds size limit for 11mm label'
          }
        }
        // Other errors - use the message directly if it's descriptive
        else if (message && message !== 'Failed to process preview response') {
          errorMessage = message
        }
      }

      toast.error(errorMessage)
    }
  }

  const printLabel = async () => {
    if (!selectedPrinter) {
      toast.error('Please select a printer first')
      return
    }

    if (!selectedLabelSize) {
      toast.error('Please select a label size')
      return
    }

    try {
      const testData = partData || {
        id: 'test-part-id-12345',
        part_name: 'Test Part',
        part_number: 'TP-001',
        emoji: '🔧',
        location: 'A1-B2',
        category: 'Electronics',
        quantity: '10',
        description: 'Test part description',
        additional_properties: {},
      }

      let result: any

      // Determine which print method to use:
      // 1. If a saved template is selected, use template system
      // 2. Otherwise, use custom text with advanced label printing
      if (selectedTemplate) {
        // Use saved template system
        result = await templateService.printTemplate({
          printer_id: selectedPrinter,
          template_id: selectedTemplate.id,
          data: testData,
          label_size: selectedLabelSize,
          copies: 1,
        })
      } else if (labelTemplate.trim()) {
        // Use custom template text
        const requestData = {
          printer_id: selectedPrinter,
          template: labelTemplate,
          text: '', // Not used anymore
          label_size: selectedLabelSize,
          label_length: selectedLabelSize.includes('mm') ? labelLength : undefined,
          options: {
            font_size_override: fontSizeOverride,
          },
          data: testData,
        }
        result = await settingsService.printAdvancedLabel(requestData)
      } else {
        // No template and no custom text
        toast.error('Please select a template or enter custom label text')
        return
      }

      // Handle API response format: { status, message, data: { success, error, ... } }
      const printData = result.data || result
      const success = printData.success || result.status === 'success'
      const errorMessage = printData.error || printData.message || result.message

      if (success) {
        toast.success('✅ Label printed successfully!')
        onClose()
      } else {
        toast.error(`❌ Print failed: ${errorMessage || 'Unknown error'}`)
      }
    } catch (error) {
      const err = error as {
        response?: { data?: { message?: string; detail?: string }; status?: number }
        message?: string
      }
      console.error('Print error:', error)

      // Extract user-friendly error message
      let errorMessage = 'Failed to print label'

      if (error instanceof Error) {
        const message = error.message

        // Check for field not found error
        if (message.includes('not found in data')) {
          const fieldMatch = message.match(/Field '([^']+)' not found/)
          if (fieldMatch) {
            const fieldName = fieldMatch[1]
            errorMessage = `QR field '{${fieldName}}' does not exist in part data`
          } else {
            errorMessage = message
          }
        }
        // Check for QR data too long error
        else if (message.includes('QR data too long')) {
          const lengthMatch = message.match(/(\d+) characters \(max (\d+)/)
          if (lengthMatch) {
            const [, actual, max] = lengthMatch
            errorMessage = `QR code data too long (${actual} chars, max ${max} for 11mm label)`
          } else {
            errorMessage = 'QR code data exceeds size limit for 11mm label'
          }
        }
        // Use the message directly if available
        else if (message) {
          errorMessage = message
        }
      }

      toast.error(errorMessage)
    }
  }

  const handleEditTemplateLoad = (
    templateText: string,
    templateName: string,
    templateId: string
  ) => {
    // Load template for editing
    setLabelTemplate(templateText)
    setSelectedTemplate(null) // Clear selected template
    setEditingTemplateId(templateId)
    setEditingTemplateName(templateName)
  }

  const handleSaveCustomTemplate = async () => {
    if (!labelTemplate.trim()) {
      toast.error('Please enter template text first')
      return
    }

    // Parse label size to get dimensions
    const heightMm = parseFloat(selectedLabelSize.replace('mm', ''))

    // Detect QR in template
    const hasQr = labelTemplate.includes('{qr}') || /\{qr=[^}]+\}/.test(labelTemplate)

    // Detect rotation
    const rotateMatch = labelTemplate.match(/\{rotate=(\d+)\}/)
    const rotation = rotateMatch ? parseInt(rotateMatch[1]) : 0

    const templateData = {
      description: 'Custom user template',
      category: 'custom',
      label_width_mm: labelLength,
      label_height_mm: heightMm,
      layout_type: hasQr ? 'qr_text_horizontal' : 'text_only',
      text_template: labelTemplate,
      text_rotation:
        rotation === 0 ? '0' : rotation === 90 ? '90' : rotation === 180 ? '180' : '270',
      text_alignment: 'center',
      qr_enabled: hasQr,
      qr_position: hasQr ? 'left' : 'center',
      qr_scale: 0.95,
      enable_multiline: true,
      enable_auto_sizing: true,
      font_config: {},
      layout_config: {},
      spacing_config: {},
    }

    try {
      if (editingTemplateId) {
        // Update existing template
        const templateName = prompt('Update template name:', editingTemplateName || '')
        if (!templateName) return

        await templateService.updateTemplate(editingTemplateId, {
          ...templateData,
          display_name: templateName,
        })

        toast.success(`Template "${templateName}" updated!`)
        setEditingTemplateId(null)
        setEditingTemplateName(null)
      } else {
        // Create new template
        const templateName = prompt('Enter a name for this template:')
        if (!templateName) return

        // Generate unique name from display name
        const uniqueName = templateName.toLowerCase().replace(/[^a-z0-9]+/g, '_') + '_' + Date.now()

        await templateService.createTemplate({
          name: uniqueName,
          display_name: templateName,
          ...templateData,
        })

        toast.success(`Template "${templateName}" saved!`)
      }

      // Reload templates in the selector
      if (reloadTemplatesRef.current) {
        await reloadTemplatesRef.current()
      }
    } catch (error) {
      const err = error as {
        response?: { data?: { message?: string; detail?: string }; status?: number }
        message?: string
      }
      console.error('Failed to save template:', error)
      toast.error(error.message || 'Failed to save template')
    }
  }

  const testConnection = async () => {
    if (!selectedPrinter) return

    try {
      const result = await settingsService.testPrinterConnection(selectedPrinter)
      if (result.success) {
        toast.success('✅ Printer connection successful!')
      } else {
        toast.error('❌ Connection test failed')
      }
    } catch {
      toast.error('Failed to test printer connection')
    }
  }

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <motion.div
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        className="modal-container bg-background-primary rounded-lg p-6 w-full max-w-4xl mx-4 max-h-[90vh] overflow-y-auto"
      >
        <div className="flex items-center justify-between mb-6">
          <h4 className="text-xl font-semibold text-primary flex items-center gap-2">
            <Printer className="w-5 h-5" />
            {title} {partData && `- ${partData.part_name}`}
          </h4>
          <button onClick={onClose} className="text-secondary hover:text-primary">
            <X className="w-6 h-6" />
          </button>
        </div>

        {loading ? (
          <div className="text-center py-8">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary mx-auto"></div>
            <p className="text-secondary mt-2">Loading printers...</p>
          </div>
        ) : availablePrinters.length === 0 ? (
          <div className="text-center py-8">
            <Printer className="w-12 h-12 text-muted mx-auto mb-2" />
            <h3 className="text-lg font-semibold text-primary mb-2">No Printers Available</h3>
            <p className="text-secondary">Please add a printer in Settings first.</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Left Column - Controls */}
            <div className="space-y-4">
              {/* Printer Selection */}
              <div>
                <label className="block text-sm font-medium text-primary mb-2">
                  Select Printer
                </label>
                <CustomSelect
                  value={selectedPrinter}
                  onChange={handlePrinterChange}
                  options={
                    availablePrinters.length === 0
                      ? [{ value: '', label: 'No printers available' }]
                      : availablePrinters.map((printer) => ({
                          value: printer.printer_id,
                          label: `${printer.name} (${printer.model})`,
                        }))
                  }
                  placeholder="Select a printer"
                />
              </div>

              {/* Template Selection */}
              <div className="space-y-4">
                {/* Template Selector */}
                <TemplateSelector
                  selectedTemplateId={selectedTemplate?.id}
                  onTemplateSelect={handleTemplateSelect}
                  onEditTemplate={handleEditTemplateLoad}
                  onTemplatesLoaded={(fn) => {
                    reloadTemplatesRef.current = fn
                  }}
                  partData={partData}
                  labelSize={selectedLabelSize}
                  showCustomOption={true}
                />

                {/* Custom Template Input (only show when no template selected) */}
                {!selectedTemplate && (
                  <div>
                    <div className="flex items-center justify-between mb-2">
                      <label className="block text-sm font-medium text-primary">
                        Custom Template Text
                        {editingTemplateName && (
                          <span className="text-xs text-blue-500 ml-2">
                            (Editing: {editingTemplateName})
                          </span>
                        )}
                      </label>
                      <button
                        type="button"
                        onClick={() => handleSaveCustomTemplate()}
                        className="text-xs px-3 py-1 bg-primary text-on-primary font-semibold rounded hover:bg-primary/90 transition-colors"
                      >
                        {editingTemplateId ? 'Update Template' : 'Save as Template'}
                      </button>
                    </div>
                    <textarea
                      className="input w-full h-20 resize-none"
                      value={labelTemplate}
                      onChange={(e) => setLabelTemplate(e.target.value)}
                      placeholder="Use {part_name}, {part_number}, {qr}, {qr=part_number}, {rotate=90}, etc."
                    />
                    <div className="relative mt-1">
                      <button
                        type="button"
                        onClick={() => setShowTemplateSyntaxHelp(!showTemplateSyntaxHelp)}
                        className="flex items-center gap-1 text-xs text-secondary hover:text-primary transition-colors"
                      >
                        <HelpCircle className="w-3 h-3" />
                        Template Syntax Help
                      </button>

                      {showTemplateSyntaxHelp && (
                        <div className="absolute left-0 top-full mt-2 z-50 bg-background-primary border border-border rounded-lg shadow-lg p-4 w-96">
                          <div className="space-y-3">
                            <div>
                              <h4 className="text-sm font-medium text-primary mb-1">
                                Basic Variables
                              </h4>
                              <p className="text-xs text-secondary">
                                {'{part_name}'}, {'{part_number}'}, {'{location}'}, {'{category}'},{' '}
                                {'{description}'}
                              </p>
                            </div>
                            <div>
                              <h4 className="text-sm font-medium text-primary mb-1">QR Codes</h4>
                              <p className="text-xs text-secondary">
                                {'{qr}'} - Defaults to MM:id format
                                <br />
                                {'{qr=part_number}'}, {'{qr=location}'} - Use specific field for QR
                                data
                              </p>
                            </div>
                            <div>
                              <h4 className="text-sm font-medium text-primary mb-1">Rotation</h4>
                              <p className="text-xs text-secondary">
                                {'{rotate=90}'}, {'{rotate=180}'}, {'{rotate=270}'} - Default: 0°
                              </p>
                            </div>
                            <div>
                              <h4 className="text-sm font-medium text-primary mb-1">Formatting</h4>
                              <p className="text-xs text-secondary">Use \n for line breaks</p>
                            </div>
                          </div>
                        </div>
                      )}
                    </div>
                  </div>
                )}
              </div>

              {/* Label Size and Length */}
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-primary mb-2">Label Size</label>
                  <CustomSelect
                    value={selectedLabelSize}
                    onChange={setSelectedLabelSize}
                    options={
                      printerInfo?.supported_sizes?.length > 0
                        ? printerInfo.supported_sizes.map((size: any) => ({
                            value: size.name,
                            label: `${size.name} - ${size.width_mm}mm ${size.height_mm ? `x ${size.height_mm}mm` : '(continuous)'}`,
                          }))
                        : [
                            { value: '12mm', label: '12mm - 12mm (continuous)' },
                            { value: '17mm', label: '17mm - 17mm (continuous)' },
                            { value: '23mm', label: '23mm - 23mm (continuous)' },
                            { value: '29mm', label: '29mm - 29mm (continuous)' },
                            { value: '38mm', label: '38mm - 38mm (continuous)' },
                            { value: '50mm', label: '50mm - 50mm (continuous)' },
                            { value: '54mm', label: '54mm - 54mm (continuous)' },
                            { value: '62mm', label: '62mm - 62mm (continuous)' },
                          ]
                    }
                    placeholder="Select label size"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-primary mb-2">Length (mm)</label>
                  <input
                    type="number"
                    min="20"
                    max="200"
                    className="input w-full"
                    value={labelLength}
                    onChange={(e) => setLabelLength(Number(e.target.value))}
                    disabled={selectedLabelSize && !selectedLabelSize.includes('mm')}
                  />
                </div>
              </div>

              {/* Font Size Override - Advanced Option */}
              <div>
                <label className="block text-sm font-medium text-primary mb-2">Font Size</label>
                <CustomSelect
                  options={[
                    { value: 'auto', label: 'Auto (Smart Sizing)' },
                    { value: '8', label: '8px - Tiny' },
                    { value: '10', label: '10px - Very Small' },
                    { value: '12', label: '12px - Small' },
                    { value: '14', label: '14px' },
                    { value: '16', label: '16px' },
                    { value: '18', label: '18px' },
                    { value: '20', label: '20px' },
                    { value: '24', label: '24px - Large' },
                    { value: '28', label: '28px' },
                    { value: '32', label: '32px - Very Large' },
                    { value: '36', label: '36px' },
                    { value: '40', label: '40px - Extra Large' },
                  ]}
                  value={fontSizeOverride !== null ? String(fontSizeOverride) : 'auto'}
                  onChange={(value) => setFontSizeOverride(value === 'auto' ? null : Number(value))}
                  placeholder="Select font size"
                />
              </div>

              {/* Options - only show for custom templates */}

              {/* Action Buttons */}
              <div className="flex gap-2">
                {showTestMode && (
                  <button
                    onClick={testConnection}
                    className="btn btn-secondary flex items-center gap-2 flex-1"
                    disabled={!selectedPrinter}
                  >
                    <TestTube className="w-4 h-4" />
                    Test
                  </button>
                )}
                <button
                  onClick={generatePreview}
                  className="btn btn-secondary flex items-center gap-2 flex-1"
                  disabled={(!selectedTemplate && !labelTemplate) || !selectedLabelSize}
                  title="Preview updates automatically, click to refresh immediately"
                >
                  👁️ Refresh Preview
                </button>
              </div>

              <button
                onClick={printLabel}
                className="btn btn-primary w-full flex items-center gap-2 justify-center"
                disabled={
                  !selectedPrinter || (!selectedTemplate && !labelTemplate) || !selectedLabelSize
                }
              >
                <Printer className="w-4 h-4" />
                Print Label
              </button>
            </div>

            {/* Right Column - Preview */}
            <div className="space-y-4">
              <h5 className="font-medium text-primary">Preview</h5>
              <div className="bg-background-secondary rounded-lg p-4 flex items-center justify-center min-h-64">
                {previewUrl ? (
                  <div className="text-center">
                    <img
                      src={previewUrl}
                      alt="Label Preview"
                      className="
      max-w-full max-h-48 border border-border rounded
      mx-auto                   /* keep horizontally centred */
      block                     /* needed for mx-auto on an <img> */
    "
                      style={{ transformOrigin: 'center' }} /* stay centred vertically */
                    />
                    <p className="text-sm text-secondary mt-2">Label Preview</p>
                  </div>
                ) : (
                  <div className="text-center text-muted">
                    <Printer className="w-12 h-12 mx-auto mb-2 opacity-50" />
                    <p>Select a template or enter text to see preview</p>
                  </div>
                )}
              </div>

              {/* Show processed template preview */}
              <div className="bg-background-secondary rounded-lg p-3">
                <h6 className="text-sm font-medium text-primary mb-2">
                  {selectedTemplate ? 'Template Output Preview:' : 'Processed Text:'}
                </h6>
                {selectedTemplate ? (
                  <div className="space-y-2">
                    <p className="text-sm text-secondary font-mono">
                      {processLabelTemplate(selectedTemplate.text_template)}
                    </p>
                    <div className="flex flex-wrap items-center gap-2 text-xs text-muted">
                      <FileText className="w-3 h-3" />
                      <span>{selectedTemplate.display_name}</span>
                      {selectedTemplate.qr_enabled && (
                        <span className="bg-green-100 text-green-800 px-1.5 py-0.5 rounded">
                          + QR Code
                        </span>
                      )}
                      {selectedTemplate.text_rotation !== 'NONE' && (
                        <span className="bg-blue-100 text-blue-800 px-1.5 py-0.5 rounded">
                          {selectedTemplate.text_rotation}° rotation
                        </span>
                      )}
                    </div>
                    {extractQRInfo(selectedTemplate.text_template) && (
                      <p className="text-xs text-green-700 bg-green-50 px-2 py-1 rounded border border-green-200">
                        📊 {extractQRInfo(selectedTemplate.text_template)}
                      </p>
                    )}
                  </div>
                ) : (
                  <div className="space-y-2">
                    <p className="text-sm text-secondary font-mono">
                      {processLabelTemplate(labelTemplate)}
                    </p>
                    {extractQRInfo(labelTemplate) && (
                      <p className="text-xs text-green-700 bg-green-50 px-2 py-1 rounded border border-green-200">
                        📊 {extractQRInfo(labelTemplate)}
                      </p>
                    )}
                  </div>
                )}
              </div>
            </div>
          </div>
        )}
      </motion.div>
    </div>
  )
}

export default PrinterModal
