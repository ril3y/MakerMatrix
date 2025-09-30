import { motion } from 'framer-motion'
import { useState, useEffect } from 'react'
import { X, Printer, TestTube, FileText } from 'lucide-react'
import { settingsService } from '@/services/settings.service'
import { templateService, LabelTemplate } from '@/services/template.service'
import TemplateSelector from './TemplateSelector'
import toast from 'react-hot-toast'

interface PrinterModalProps {
  isOpen: boolean
  onClose: () => void
  title?: string
  showTestMode?: boolean
  partData?: {
    id?: string
    part_name?: string
    part_number?: string
    location?: string
    category?: string
    quantity?: string
    description?: string
    additional_properties?: Record<string, any>
  }
}

const PrinterModal = ({ isOpen, onClose, title = "Print Label", showTestMode = false, partData }: PrinterModalProps) => {
  const [availablePrinters, setAvailablePrinters] = useState<any[]>([])
  const [selectedPrinter, setSelectedPrinter] = useState<string>('')
  const [printerInfo, setPrinterInfo] = useState<any>(null)
  const [selectedTemplate, setSelectedTemplate] = useState<LabelTemplate | null>(null)
  const [labelTemplate, setLabelTemplate] = useState('{part_name}')
  const [selectedLabelSize, setSelectedLabelSize] = useState('12mm')
  const [labelLength, setLabelLength] = useState(39)
  const [previewUrl, setPreviewUrl] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)
  const [useTemplateSystem, setUseTemplateSystem] = useState(true)

  useEffect(() => {
    if (isOpen) {
      loadPrinters()
      // Reset template selection when modal opens
      setSelectedTemplate(null)
      setUseTemplateSystem(true)
      // Set default template based on whether we have part data
      if (partData) {
        setLabelTemplate('{part_name}')
      } else {
        setLabelTemplate('Test Label')
      }
      // Clear preview when modal opens
      setPreviewUrl(null)
    }
  }, [isOpen, partData])

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
    } catch (error) {
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
        const defaultSize = info.supported_sizes.find((s: any) => s.name === '12mm') ||
          info.supported_sizes.find((s: any) => s.name === '12') ||
          info.supported_sizes[0]
        setSelectedLabelSize(defaultSize.name)
      }
    } catch (error) {
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
      additional_properties: {}
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
        processed = processed.replace(new RegExp(`\\{additional_properties\\.${key}\\}`, 'g'), String(value || ''))
        // Also support direct access to additional_properties fields
        if (!data.hasOwnProperty(key)) {
          processed = processed.replace(new RegExp(`\\{${key}\\}`, 'g'), String(value || ''))
        }
      })
    }

    // Handle QR code placeholders with data
    const qrWithDataMatch = processed.match(/\{qr=([^}]+)\}/)
    if (qrWithDataMatch) {
      const qrDataKey = qrWithDataMatch[1]
      const qrValue = data[qrDataKey as keyof typeof data] || qrDataKey
      processed = processed.replace(/\{qr=[^}]+\}/g, `[QR:${qrValue}]`)
    }

    // Handle plain {qr} - defaults to MM:id format
    if (processed.includes('{qr}')) {
      const mmId = data.id || 'test-id'
      processed = processed.replace(/\{qr\}/g, `[QR:MM:${mmId}]`)
    }

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
        location: 'A1-B2',
        category: 'Electronics',
        quantity: '10',
        description: 'Test part description',
        additional_properties: {}
      }

      let blob: Blob

      if (useTemplateSystem && selectedTemplate) {
        // Use new template system
        blob = await templateService.previewTemplate({
          template_id: selectedTemplate.id,
          data: testData
        })
      } else {
        // Use legacy custom template system
        const requestData = {
          template: labelTemplate,
          text: "", // Not used anymore
          label_size: selectedLabelSize,
          label_length: selectedLabelSize.includes('mm') ? labelLength : undefined,
          options: {},
          data: testData
        }
        blob = await settingsService.previewAdvancedLabel(requestData)
      }

      const url = URL.createObjectURL(blob)
      setPreviewUrl(url)
    } catch (error) {
      console.error('Preview error:', error)
      toast.error('Failed to generate preview')
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

    if (useTemplateSystem && !selectedTemplate) {
      toast.error('Please select a template first')
      return
    }

    try {
      const testData = partData || {
        id: 'test-part-id-12345',
        part_name: 'Test Part',
        part_number: 'TP-001',
        location: 'A1-B2',
        category: 'Electronics',
        quantity: '10',
        description: 'Test part description',
        additional_properties: {}
      }

      let result: any

      if (useTemplateSystem && selectedTemplate) {
        // Use new template system
        result = await templateService.printTemplate({
          printer_id: selectedPrinter,
          template_id: selectedTemplate.id,
          data: testData,
          label_size: selectedLabelSize,
          copies: 1
        })
      } else {
        // Use legacy custom template system
        const requestData = {
          printer_id: selectedPrinter,
          template: labelTemplate,
          text: "", // Not used anymore
          label_size: selectedLabelSize,
          label_length: selectedLabelSize.includes('mm') ? labelLength : undefined,
          options: {},
          data: testData
        }
        result = await settingsService.printAdvancedLabel(requestData)
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
      console.error('Print error:', error)
      toast.error(`Failed to print label: ${error instanceof Error ? error.message : 'Unknown error'}`)
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
    } catch (error) {
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
          <button
            onClick={onClose}
            className="text-secondary hover:text-primary"
          >
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
                <select
                  className="input w-full"
                  value={selectedPrinter}
                  onChange={(e) => handlePrinterChange(e.target.value)}
                >
                  {availablePrinters.length === 0 && (
                    <option value="">No printers available</option>
                  )}
                  {availablePrinters.map((printer) => (
                    <option key={printer.printer_id} value={printer.printer_id}>
                      {printer.name} ({printer.model})
                    </option>
                  ))}
                </select>
              </div>

              {/* Template Selection */}
              <div className="space-y-4">
                {/* Template Selector */}
                <TemplateSelector
                  selectedTemplateId={selectedTemplate?.id}
                  onTemplateSelect={handleTemplateSelect}
                  partData={partData}
                  labelSize={selectedLabelSize}
                  showCustomOption={true}
                />

                {/* Custom Template Input (only show when no template selected) */}
                {!selectedTemplate && (
                  <div>
                    <label className="block text-sm font-medium text-primary mb-2">
                      Custom Template Text
                    </label>
                    <textarea
                      className="input w-full h-20 resize-none"
                      value={labelTemplate}
                      onChange={(e) => setLabelTemplate(e.target.value)}
                      placeholder="Use {part_name}, {part_number}, {qr}, {qr=part_number}, etc."
                    />
                    <p className="text-xs text-secondary mt-1">
                      Available: {'{part_name}'}, {'{part_number}'}, {'{location}'}, {'{category}'}, {'{description}'}
                      <br />
                      QR Code: {'{qr}'} (defaults to MM:id format), {'{qr=part_number}'}, {'{qr=location}'}, etc.
                    </p>
                  </div>
                )}
              </div>

              {/* Label Size and Length */}
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-primary mb-2">
                    Label Size
                  </label>
                  <select
                    className="input w-full"
                    value={selectedLabelSize}
                    onChange={(e) => setSelectedLabelSize(e.target.value)}
                  >
                    {printerInfo?.supported_sizes?.length > 0 ? (
                      printerInfo.supported_sizes.map((size: any) => (
                        <option key={size.name} value={size.name}>
                          {size.name} - {size.width_mm}mm {size.height_mm ? `x ${size.height_mm}mm` : '(continuous)'}
                        </option>
                      ))
                    ) : (
                      // Fallback options when printer info is not available
                      <>
                        <option value="12mm">12mm - 12mm (continuous)</option>
                        <option value="17mm">17mm - 17mm (continuous)</option>
                        <option value="23mm">23mm - 23mm (continuous)</option>
                        <option value="29mm">29mm - 29mm (continuous)</option>
                        <option value="38mm">38mm - 38mm (continuous)</option>
                        <option value="50mm">50mm - 50mm (continuous)</option>
                        <option value="54mm">54mm - 54mm (continuous)</option>
                        <option value="62mm">62mm - 62mm (continuous)</option>
                      </>
                    )}
                  </select>
                </div>

                <div>
                  <label className="block text-sm font-medium text-primary mb-2">
                    Length (mm)
                  </label>
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
                >
                  👁️ Preview
                </button>
              </div>

              <button
                onClick={printLabel}
                className="btn btn-primary w-full flex items-center gap-2 justify-center"
                disabled={!selectedPrinter || (!selectedTemplate && !labelTemplate) || !selectedLabelSize}
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
                    <p>Click "Preview" to see your label</p>
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