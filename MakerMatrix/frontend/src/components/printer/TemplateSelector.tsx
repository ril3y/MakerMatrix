import { useState, useEffect } from 'react'
import { ChevronDown, FileText, Sparkles, User, Copy, Eye } from 'lucide-react'
import { templateService, LabelTemplate } from '@/services/template.service'
import toast from 'react-hot-toast'

interface TemplateSelectorProps {
  selectedTemplateId?: string
  onTemplateSelect: (template: LabelTemplate | null) => void
  partData?: Record<string, any>
  labelSize?: string
  showCustomOption?: boolean
}

const TemplateSelector = ({
  selectedTemplateId,
  onTemplateSelect,
  partData,
  labelSize = '12mm',
  showCustomOption = true
}: TemplateSelectorProps) => {
  const [templates, setTemplates] = useState<LabelTemplate[]>([])
  const [systemTemplates, setSystemTemplates] = useState<LabelTemplate[]>([])
  const [userTemplates, setUserTemplates] = useState<LabelTemplate[]>([])
  const [loading, setLoading] = useState(false)
  const [showDropdown, setShowDropdown] = useState(false)
  const [searchTerm, setSearchTerm] = useState('')

  useEffect(() => {
    loadTemplates()
  }, [labelSize])

  const loadTemplates = async () => {
    try {
      setLoading(true)

      // Load both system and user templates
      const [systemList, userList] = await Promise.all([
        templateService.getSystemTemplates(),
        templateService.getUserTemplates()
      ])

      // Ensure we have arrays
      const systemArray = Array.isArray(systemList) ? systemList : []
      const userArray = Array.isArray(userList) ? userList : []

      setSystemTemplates(systemArray)
      setUserTemplates(userArray)

      // Combine and filter compatible templates if label size is known
      const allTemplates = [...systemArray, ...userArray]

      if (labelSize) {
        const heightMm = parseFloat(labelSize.replace('mm', ''))
        if (!isNaN(heightMm)) {
          // Filter templates compatible with the selected label size
          const compatible = allTemplates.filter(t =>
            Math.abs(t.label_height_mm - heightMm) <= 1 // Allow 1mm tolerance
          )
          setTemplates(compatible)
        } else {
          setTemplates(allTemplates)
        }
      } else {
        setTemplates(allTemplates)
      }

      // Show info if no templates loaded
      if (allTemplates.length === 0) {
        console.info('No templates available. Check authentication or create templates.')
      }

    } catch (error) {
      console.error('Failed to load templates:', error)
      // Don't show error toast, just fall back to custom template
      setSystemTemplates([])
      setUserTemplates([])
      setTemplates([])
    } finally {
      setLoading(false)
    }
  }

  const handleTemplateSelect = (template: LabelTemplate | null) => {
    onTemplateSelect(template)
    setShowDropdown(false)
  }

  const handleCustomSelect = () => {
    onTemplateSelect(null)
    setShowDropdown(false)
  }

  const selectedTemplate = selectedTemplateId
    ? templates.find(t => t.id === selectedTemplateId)
    : null

  const filteredTemplates = templates.filter(template =>
    template.display_name.toLowerCase().includes(searchTerm.toLowerCase()) ||
    template.description.toLowerCase().includes(searchTerm.toLowerCase()) ||
    template.category.toLowerCase().includes(searchTerm.toLowerCase())
  )

  // Get suggested templates based on part data
  const suggestedTemplates = partData
    ? templateService.getTemplateSuggestions(partData, filteredTemplates)
    : filteredTemplates

  const getTemplateIcon = (template: LabelTemplate) => {
    if (template.is_system_template) {
      return <Sparkles className="w-4 h-4 text-yellow-500" />
    }
    return <User className="w-4 h-4 text-blue-500" />
  }

  const getLayoutDescription = (template: LabelTemplate) => {
    const parts = []
    if (template.qr_enabled) parts.push('QR Code')
    if (template.text_template) parts.push('Text')
    if (template.text_rotation !== 'NONE') parts.push(`${template.text_rotation}°`)
    return parts.join(' + ')
  }

  return (
    <div className="relative">
      <label className="block text-sm font-medium text-primary mb-2">
        Label Template
      </label>

      <div className="relative">
        <button
          type="button"
          onClick={() => setShowDropdown(!showDropdown)}
          className="input w-full text-left flex items-center justify-between"
        >
          <div className="flex items-center gap-2">
            {selectedTemplate ? (
              <>
                {getTemplateIcon(selectedTemplate)}
                <span>{selectedTemplate.display_name}</span>
                <span className="text-xs text-secondary">
                  ({getLayoutDescription(selectedTemplate)})
                </span>
              </>
            ) : (
              <>
                <FileText className="w-4 h-4 text-muted" />
                <span className="text-secondary">
                  {showCustomOption ? 'Custom Template' : 'Select a template...'}
                </span>
              </>
            )}
          </div>
          <ChevronDown className={`w-4 h-4 text-secondary transition-transform ${
            showDropdown ? 'rotate-180' : ''
          }`} />
        </button>

        {showDropdown && (
          <div className="absolute top-full left-0 right-0 z-50 mt-1 bg-background-primary border border-border rounded-lg shadow-lg max-h-80 overflow-y-auto">
            {/* Search */}
            <div className="p-3 border-b border-border">
              <input
                type="text"
                placeholder="Search templates..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="input w-full text-sm"
                autoFocus
              />
            </div>

            {loading ? (
              <div className="p-4 text-center">
                <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-primary mx-auto"></div>
                <p className="text-sm text-secondary mt-2">Loading templates...</p>
              </div>
            ) : (
              <>
                {/* Custom Template Option */}
                {showCustomOption && (
                  <div className="border-b border-border">
                    <button
                      onClick={handleCustomSelect}
                      className={`w-full p-3 text-left hover:bg-background-secondary transition-colors ${
                        !selectedTemplate ? 'bg-background-secondary' : ''
                      }`}
                    >
                      <div className="flex items-center gap-2">
                        <FileText className="w-4 h-4 text-muted" />
                        <div>
                          <div className="font-medium text-primary">Custom Template</div>
                          <div className="text-xs text-secondary">
                            Enter your own template text with variables
                          </div>
                        </div>
                      </div>
                    </button>
                  </div>
                )}

                {/* Suggested Templates */}
                {partData && suggestedTemplates.length > 0 && (
                  <div>
                    <div className="px-3 py-2 text-xs font-medium text-secondary bg-background-secondary">
                      💡 Suggested for your part
                    </div>
                    {suggestedTemplates.slice(0, 3).map((template) => (
                      <button
                        key={`suggested-${template.id}`}
                        onClick={() => handleTemplateSelect(template)}
                        className={`w-full p-3 text-left hover:bg-background-secondary transition-colors ${
                          selectedTemplateId === template.id ? 'bg-background-secondary' : ''
                        }`}
                      >
                        <div className="flex items-center gap-2">
                          {getTemplateIcon(template)}
                          <div className="flex-1 min-w-0">
                            <div className="flex items-center gap-2">
                              <span className="font-medium text-primary truncate">
                                {template.display_name}
                              </span>
                              <span className="text-xs text-yellow-600 bg-yellow-100 px-1.5 py-0.5 rounded">
                                Suggested
                              </span>
                            </div>
                            <div className="text-xs text-secondary truncate">
                              {template.description}
                            </div>
                            <div className="text-xs text-muted">
                              {getLayoutDescription(template)} • {template.label_width_mm}×{template.label_height_mm}mm
                            </div>
                          </div>
                        </div>
                      </button>
                    ))}
                  </div>
                )}

                {/* System Templates */}
                {systemTemplates.length > 0 && (
                  <div>
                    <div className="px-3 py-2 text-xs font-medium text-secondary bg-background-secondary">
                      ⭐ System Templates
                    </div>
                    {filteredTemplates
                      .filter(t => t.is_system_template)
                      .map((template) => (
                        <button
                          key={`system-${template.id}`}
                          onClick={() => handleTemplateSelect(template)}
                          className={`w-full p-3 text-left hover:bg-background-secondary transition-colors ${
                            selectedTemplateId === template.id ? 'bg-background-secondary' : ''
                          }`}
                        >
                          <div className="flex items-center gap-2">
                            {getTemplateIcon(template)}
                            <div className="flex-1 min-w-0">
                              <div className="font-medium text-primary truncate">
                                {template.display_name}
                              </div>
                              <div className="text-xs text-secondary truncate">
                                {template.description}
                              </div>
                              <div className="text-xs text-muted">
                                {getLayoutDescription(template)} • {template.label_width_mm}×{template.label_height_mm}mm
                              </div>
                            </div>
                          </div>
                        </button>
                      ))}
                  </div>
                )}

                {/* User Templates */}
                {userTemplates.length > 0 && (
                  <div>
                    <div className="px-3 py-2 text-xs font-medium text-secondary bg-background-secondary">
                      👤 My Templates
                    </div>
                    {filteredTemplates
                      .filter(t => !t.is_system_template)
                      .map((template) => (
                        <button
                          key={`user-${template.id}`}
                          onClick={() => handleTemplateSelect(template)}
                          className={`w-full p-3 text-left hover:bg-background-secondary transition-colors ${
                            selectedTemplateId === template.id ? 'bg-background-secondary' : ''
                          }`}
                        >
                          <div className="flex items-center gap-2">
                            {getTemplateIcon(template)}
                            <div className="flex-1 min-w-0">
                              <div className="font-medium text-primary truncate">
                                {template.display_name}
                              </div>
                              <div className="text-xs text-secondary truncate">
                                {template.description}
                              </div>
                              <div className="text-xs text-muted">
                                {getLayoutDescription(template)} • {template.label_width_mm}×{template.label_height_mm}mm
                              </div>
                            </div>
                          </div>
                        </button>
                      ))}
                  </div>
                )}

                {/* No Results */}
                {filteredTemplates.length === 0 && !loading && (
                  <div className="p-4 text-center text-secondary">
                    <FileText className="w-8 h-8 mx-auto mb-2 opacity-50" />
                    <p className="text-sm">No templates found</p>
                    {searchTerm && (
                      <p className="text-xs mt-1">Try a different search term</p>
                    )}
                  </div>
                )}
              </>
            )}
          </div>
        )}
      </div>

      {/* Template Details */}
      {selectedTemplate && (
        <div className="mt-2 p-3 bg-background-secondary rounded-lg">
          <div className="flex items-center justify-between mb-2">
            <h6 className="text-sm font-medium text-primary">Template Details</h6>
            <div className="flex items-center gap-1">
              {selectedTemplate.is_system_template && (
                <span className="text-xs bg-yellow-100 text-yellow-800 px-2 py-0.5 rounded">
                  System
                </span>
              )}
              <span className="text-xs bg-blue-100 text-blue-800 px-2 py-0.5 rounded">
                {selectedTemplate.category}
              </span>
            </div>
          </div>

          <div className="space-y-1 text-xs text-secondary">
            <p><strong>Size:</strong> {selectedTemplate.label_width_mm} × {selectedTemplate.label_height_mm}mm</p>
            <p><strong>Layout:</strong> {getLayoutDescription(selectedTemplate)}</p>
            {selectedTemplate.text_template && (
              <p><strong>Template:</strong> <code className="bg-background-primary px-1 rounded text-primary">
                {selectedTemplate.text_template}
              </code></p>
            )}
            <p><strong>Used:</strong> {selectedTemplate.usage_count} times</p>
          </div>
        </div>
      )}
    </div>
  )
}

export default TemplateSelector