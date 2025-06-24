import React from 'react'
import { TestTube, Monitor, Eye, Printer } from 'lucide-react'
import { usePrinter } from '@/hooks/usePrinter'

interface PartData {
  part_name?: string
  part_number?: string
  location?: string
  category?: string
  quantity?: string
  description?: string
  additional_properties?: Record<string, any>
}

interface PrinterInterfaceProps {
  partData?: PartData
  onPrintSuccess?: () => void
  showConnectionTest?: boolean
  className?: string
}

const PrinterInterface: React.FC<PrinterInterfaceProps> = ({
  partData,
  onPrintSuccess,
  showConnectionTest = true,
  className = ""
}) => {
  const {
    availablePrinters,
    selectedPrinter,
    printerInfo,
    labelTemplate,
    selectedLabelSize,
    labelLength,
    fitToLabel,
    includeQR,
    qrData,
    previewUrl,
    loading,
    setLabelTemplate,
    setSelectedLabelSize,
    setLabelLength,
    setFitToLabel,
    setIncludeQR,
    setQrData,
    handlePrinterChange,
    processLabelTemplate,
    generatePreview,
    printLabel,
    testConnection
  } = usePrinter({ partData, onPrintSuccess })

  const testData = partData || {
    part_name: 'Test Part',
    part_number: 'TP-001',
    location: 'A1-B2',
    category: 'Electronics',
    quantity: '10',
    description: 'Test part description',
    additional_properties: {}
  }

  const processedText = processLabelTemplate(labelTemplate, testData)

  return (
    <div className={`space-y-6 ${className}`}>
      {/* Printer Selection */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <h3 className="text-lg font-semibold flex items-center gap-2">
            <Printer className="w-5 h-5" />
            Printer Settings
          </h3>
          {showConnectionTest && (
            <button
              onClick={testConnection}
              className="btn btn-secondary flex items-center gap-2"
              disabled={!selectedPrinter}
            >
              <TestTube className="w-4 h-4" />
              Test Connection
            </button>
          )}
        </div>

        <div className="space-y-2">
          <label className="block text-sm font-medium">Printer</label>
          <select
            value={selectedPrinter}
            onChange={(e) => handlePrinterChange(e.target.value)}
            className="input w-full"
          >
            <option value="">Select a printer...</option>
            {availablePrinters.map((printer) => (
              <option key={printer.printer_id} value={printer.printer_id}>
                {printer.name} ({printer.model})
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Label Configuration */}
      <div className="space-y-4">
        <h3 className="text-lg font-semibold">Label Configuration</h3>
        
        <div className="space-y-2">
          <label className="block text-sm font-medium">Label Template</label>
          <textarea
            value={labelTemplate}
            onChange={(e) => setLabelTemplate(e.target.value)}
            className="input w-full h-24 resize-none"
            placeholder="Enter template with placeholders like {part_name}, {description}, {material}, etc."
          />
          <p className="text-xs text-secondary">
            Available placeholders: {'{part_name}'}, {'{part_number}'}, {'{description}'}, {'{location}'}, {'{category}'}, {'{quantity}'}
            {partData?.additional_properties && Object.keys(partData.additional_properties).length > 0 && (
              <span>, {Object.keys(partData.additional_properties).map(key => `{${key}}`).join(', ')}</span>
            )}
            <br />
            QR codes: {'{qr=part_number}'} or {'{qr=any_field}'}
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="space-y-2">
            <label className="block text-sm font-medium">Label Size</label>
            <select
              value={selectedLabelSize}
              onChange={(e) => setSelectedLabelSize(e.target.value)}
              className="input w-full"
            >
              {printerInfo?.supported_sizes?.map((size: any) => (
                <option key={size.name} value={size.name}>
                  {size.name} ({size.width_mm}mm x {size.height_mm || 'continuous'}mm)
                </option>
              )) || (
                <>
                  <option value="12mm">12mm</option>
                  <option value="29mm">29mm</option>
                </>
              )}
            </select>
          </div>

          {selectedLabelSize.includes('mm') && (
            <div className="space-y-2">
              <label className="block text-sm font-medium">Label Length (mm)</label>
              <input
                type="number"
                value={labelLength}
                onChange={(e) => setLabelLength(Number(e.target.value))}
                className="input w-full"
                min="20"
                max="200"
              />
            </div>
          )}
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="space-y-2">
            <label className="flex items-center gap-2">
              <input
                type="checkbox"
                checked={fitToLabel}
                onChange={(e) => setFitToLabel(e.target.checked)}
                className="checkbox"
              />
              <span className="text-sm">Fit text to label</span>
            </label>
          </div>

          <div className="space-y-2">
            <label className="flex items-center gap-2">
              <input
                type="checkbox"
                checked={includeQR}
                onChange={(e) => setIncludeQR(e.target.checked)}
                className="checkbox"
              />
              <span className="text-sm">Include QR code</span>
            </label>
          </div>
        </div>

        {includeQR && (
          <div className="space-y-2">
            <label className="block text-sm font-medium">QR Code Data Field</label>
            <input
              type="text"
              value={qrData}
              onChange={(e) => setQrData(e.target.value)}
              className="input w-full"
              placeholder="part_number"
            />
          </div>
        )}
      </div>

      {/* Preview and Actions */}
      <div className="space-y-4">
        <div className="flex flex-wrap gap-2">
          <button
            onClick={generatePreview}
            className="btn btn-secondary flex items-center gap-2"
            disabled={loading}
          >
            <Eye className="w-4 h-4" />
            Generate Preview
          </button>
          
          <button
            onClick={printLabel}
            className="btn btn-primary flex items-center gap-2"
            disabled={!selectedPrinter}
          >
            <Printer className="w-4 h-4" />
            Print Label
          </button>
        </div>

        {/* Processed Text Preview */}
        {processedText && (
          <div className="space-y-2">
            <label className="block text-sm font-medium">Processed Text:</label>
            <div className="p-2 bg-base-200 rounded border text-sm font-mono whitespace-pre-wrap">
              {processedText}
            </div>
          </div>
        )}

        {/* Image Preview */}
        {previewUrl && (
          <div className="space-y-2">
            <label className="block text-sm font-medium flex items-center gap-2">
              <Monitor className="w-4 h-4" />
              Label Preview:
            </label>
            <div className="border rounded p-4 bg-white flex justify-center">
              <img
                src={previewUrl}
                alt="Label Preview"
                className="max-w-full h-auto border"
                style={{ maxHeight: '300px' }}
              />
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

export default PrinterInterface