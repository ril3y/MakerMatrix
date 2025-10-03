import { motion } from 'framer-motion'
import { Package, Edit, Trash2, Tag, MapPin, Calendar, ArrowLeft, ExternalLink, Hash, Box, Image, Info, Zap, Settings, Globe, BookOpen, Clock, FileText, Download, Eye, Printer, TrendingUp, DollarSign, Copy, Check, Factory, Cpu, Leaf, AlertCircle, Layers, ShieldCheck, Plus } from 'lucide-react'
import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { partsService } from '@/services/parts.service'
import { categoriesService } from '@/services/categories.service'
import { Part, Datasheet } from '@/types/parts'
import { Category } from '@/types/categories'
import { getPDFProxyUrl } from '@/services/api'
import LoadingScreen from '@/components/ui/LoadingScreen'
import PartPDFViewer from '@/components/parts/PartPDFViewer'
import PDFViewer from '@/components/ui/PDFViewer'
import PartEnrichmentModal from '@/components/parts/PartEnrichmentModal'
import PrinterModal from '@/components/printer/PrinterModal'
import PartImage from '@/components/parts/PartImage'
import AddCategoryModal from '@/components/categories/AddCategoryModal'
import CategorySelector from '@/components/ui/CategorySelector'
import { analyticsService } from '@/services/analytics.service'
import { Line } from 'react-chartjs-2'

// Icon mapping for property explorer
const getIconForProperty = (propertyKey: string) => {
  const iconMapping = {
    'specifications': Zap,
    'supplier_data': Globe,
    'metadata': Clock,
    'order_data': DollarSign,
    'pricing_data': DollarSign,
    'compliance': ShieldCheck,
    'custom_fields': Settings,
    'enrichment': BookOpen,
    'order_history': TrendingUp,
  }
  return iconMapping[propertyKey.toLowerCase()] || Info
}

// Property leaf counting function
const countPropertyLeaves = (value: any): number => {
  if (value === null || value === undefined) return 1
  if (typeof value !== 'object') return 1
  if (Array.isArray(value)) {
    if (value.length === 0) return 0
    return value.reduce<number>((sum, item) => sum + countPropertyLeaves(item), 0)
  }
  const entries = Object.values(value) as unknown[]
  if (entries.length === 0) return 0
  return entries.reduce<number>((sum, item) => sum + countPropertyLeaves(item), 0)
}

const formatEnumValue = (value?: string | null) => {
  if (!value) return 'Not set'
  return value
    .replace(/[_-]+/g, ' ')
    .replace(/\b\w/g, (char) => char.toUpperCase())
}

const isIsoDateString = (value: string) => /\d{4}-\d{2}-\d{2}T\d{2}:\d{2}/.test(value)

const formatDateTime = (value?: string | null) => {
  if (!value) return null
  if (!isIsoDateString(value)) return null
  try {
    return new Date(value).toLocaleString()
  } catch (error) {
    return null
  }
}

const PartDetailsPage = () => {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const [part, setPart] = useState<Part | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [pdfViewerOpen, setPdfViewerOpen] = useState(false)
  const [selectedDatasheet, setSelectedDatasheet] = useState<Datasheet | null>(null)
  const [pdfPreviewOpen, setPdfPreviewOpen] = useState(false)
  const [pdfPreviewUrl, setPdfPreviewUrl] = useState<string>('')
  const [enrichmentModalOpen, setEnrichmentModalOpen] = useState(false)
  const [printerModalOpen, setPrinterModalOpen] = useState(false)
  const [priceTrends, setPriceTrends] = useState<any[]>([])
  const [loadingPriceHistory, setLoadingPriceHistory] = useState(false)
  const [copiedPartNumber, setCopiedPartNumber] = useState(false)
  const [copiedPartName, setCopiedPartName] = useState(false)

  // Category management state
  const [addCategoryModalOpen, setAddCategoryModalOpen] = useState(false)
  const [categoryManagementOpen, setCategoryManagementOpen] = useState(false)
  const [allCategories, setAllCategories] = useState<Category[]>([])
  const [selectedCategoryIds, setSelectedCategoryIds] = useState<string[]>([])
  const [loadingCategories, setLoadingCategories] = useState(false)
  const [openedFromManagement, setOpenedFromManagement] = useState(false)

  // Inline editing states
  const [editingField, setEditingField] = useState<string | null>(null)
  const [editingValue, setEditingValue] = useState<string>('')
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    if (id) {
      loadPart(id)
    }
  }, [id])

  // Load all categories for category management
  useEffect(() => {
    loadAllCategories()
  }, [])

  // Update selected categories when part changes
  useEffect(() => {
    if (part?.categories) {
      setSelectedCategoryIds(part.categories.map(cat => cat.id))
    }
  }, [part?.categories])

  const loadPart = async (partId: string) => {
    try {
      setLoading(true)
      setError(null)
      const response = await partsService.getPart(partId)
      setPart(response)
      // Load price history after part is loaded
      loadPriceHistory(partId)
    } catch (err: any) {
      setError(err.response?.data?.error || 'Failed to load part details')
    } finally {
      setLoading(false)
    }
  }

  const handleEdit = () => {
    if (part) {
      navigate(`/parts/${part.id}/edit`)
    }
  }

  const handleEnrich = () => {
    setEnrichmentModalOpen(true)
  }

  const handlePartUpdated = (updatedPart: Part) => {
    setPart(updatedPart)
    // Optionally reload the part from server to get all updates
    if (id) {
      loadPart(id)
    }
  }

  const loadPriceHistory = async (partId: string) => {
    try {
      setLoadingPriceHistory(true)
      const trends = await analyticsService.getPriceTrends({ part_id: partId, limit: 20 })
      setPriceTrends(trends)
    } catch (err) {
      console.error('Failed to load price history:', err)
    } finally {
      setLoadingPriceHistory(false)
    }
  }

  const handleDelete = async () => {
    if (part && confirm(`Are you sure you want to delete "${part.name}"?`)) {
      try {
        await partsService.deletePart(part.id)
        navigate('/parts')
      } catch (err: any) {
        setError(err.response?.data?.error || 'Failed to delete part')
      }
    }
  }

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    })
  }

  const copyToClipboard = async (text: string, type: 'part_number' | 'part_name') => {
    try {
      await navigator.clipboard.writeText(text)
      if (type === 'part_number') {
        setCopiedPartNumber(true)
        setTimeout(() => setCopiedPartNumber(false), 2000)
      } else {
        setCopiedPartName(true)
        setTimeout(() => setCopiedPartName(false), 2000)
      }
    } catch (err) {
      console.error('Failed to copy to clipboard:', err)
    }
  }

  const startEditing = (field: string, currentValue: string) => {
    setEditingField(field)
    setEditingValue(currentValue || '')
  }

  const cancelEditing = () => {
    setEditingField(null)
    setEditingValue('')
  }

  const saveField = async (field: string, value: string) => {
    if (!part) return

    setSaving(true)
    try {
      const updateData = {
        id: part.id,
        [field]: value
      }
      const updatedPart = await partsService.updatePart(updateData)

      // Update local state with the returned data
      setPart(updatedPart)
      setEditingField(null)
      setEditingValue('')
    } catch (err: any) {
      setError(err.response?.data?.error || `Failed to update ${field}`)
    } finally {
      setSaving(false)
    }
  }

  const getDatasheetUrl = (datasheet: Datasheet) => {
    // In development, use the vite proxy. In production, use the configured API URL
    const isDevelopment = (import.meta as any).env?.DEV
    if (isDevelopment) {
      // Use relative URL so it goes through Vite proxy
      return `/static/datasheets/${datasheet.filename}`
    } else {
      // Production: use full API URL
      const API_BASE_URL = (import.meta as any).env?.VITE_API_URL || 'http://localhost:8080'
      return `${API_BASE_URL}/static/datasheets/${datasheet.filename}`
    }
  }

  const downloadDatasheet = (datasheet: Datasheet) => {
    const url = getDatasheetUrl(datasheet)
    const link = document.createElement('a')
    link.href = url
    link.download = datasheet.original_filename || datasheet.filename
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
  }

  const viewDatasheet = (datasheet: Datasheet) => {
    setSelectedDatasheet(datasheet)
    setPdfViewerOpen(true)
  }

  const openPDFPreview = (url: string) => {
    // Use the backend PDF proxy to avoid CORS issues
    const proxyUrl = getPDFProxyUrl(url)
    setPdfPreviewUrl(proxyUrl)
    setPdfPreviewOpen(true)
  }

  const formatFileSize = (bytes?: number) => {
    if (!bytes) return 'Unknown size'
    if (bytes < 1024) return `${bytes} B`
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
  }

  // Category management functions
  const loadAllCategories = async () => {
    try {
      setLoadingCategories(true)
      const categories = await categoriesService.getAllCategories()
      console.log('Loaded categories:', categories)
      setAllCategories(categories || [])
    } catch (error) {
      console.error('Failed to load categories:', error)
      setError('Failed to load categories')
    } finally {
      setLoadingCategories(false)
    }
  }

  const handleToggleCategory = (categoryId: string) => {
    setSelectedCategoryIds(prev =>
      prev.includes(categoryId)
        ? prev.filter(id => id !== categoryId)
        : [...prev, categoryId]
    )
  }

  const saveCategoryChanges = async () => {
    if (!part || !id) return

    try {
      setSaving(true)
      const selectedCategories = allCategories.filter(cat => selectedCategoryIds.includes(cat.id))

      // Update part with new categories
      await partsService.updatePart({
        id: id,
        categories: selectedCategories.map(cat => cat.name)
      })

      // Refresh the part to get updated data
      await loadPart(id)
      setCategoryManagementOpen(false)
    } catch (error) {
      console.error('Failed to update categories:', error)
      setError('Failed to update categories')
    } finally {
      setSaving(false)
    }
  }

  const handleAddCategorySuccess = async () => {
    await loadAllCategories()
    setAddCategoryModalOpen(false)
    // If opened from management modal, return to it
    if (openedFromManagement) {
      setCategoryManagementOpen(true)
      setOpenedFromManagement(false)
    }
  }

  const handleAddCategoryFromManagement = () => {
    // Mark that this was opened from management modal
    setOpenedFromManagement(true)
    // Close management modal first, then open add category modal
    setCategoryManagementOpen(false)
    setAddCategoryModalOpen(true)
  }

  const handleAddCategoryDirect = () => {
    // Opened directly from main buttons
    setOpenedFromManagement(false)
    setAddCategoryModalOpen(true)
  }

  if (loading) {
    return <LoadingScreen />
  }

  if (error) {
    return (
      <div className="min-h-screen bg-theme-secondary">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
          <div className="bg-theme-elevated border border-error rounded-xl p-8 shadow-sm">
            <div className="text-center">
              <div className="p-3 bg-error rounded-full w-fit mx-auto mb-4">
                <AlertCircle className="w-8 h-8 text-theme-inverse" />
              </div>
              <h3 className="text-xl font-theme-display font-semibold text-theme-primary mb-2">
                Error Loading Part
              </h3>
              <p className="text-error mb-6 font-theme-primary">{error}</p>
              <button
                onClick={() => navigate('/parts')}
                className="inline-flex items-center gap-2 px-6 py-3 bg-primary text-theme-inverse rounded-lg hover:bg-primary-dark transition-colors font-medium"
              >
                <ArrowLeft className="w-4 h-4" />
                Back to Parts
              </button>
            </div>
          </div>
        </div>
      </div>
    )
  }

  if (!part) {
    return (
      <div className="min-h-screen bg-theme-secondary">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
          <div className="bg-theme-elevated border border-theme-primary rounded-xl p-12 shadow-sm">
            <div className="text-center">
              <div className="p-4 bg-primary-10 rounded-full w-fit mx-auto mb-6">
                <Package className="w-12 h-12 text-primary-accent" />
              </div>
              <h3 className="text-2xl font-theme-display font-semibold text-theme-primary mb-4">
                Part Not Found
              </h3>
              <p className="text-theme-secondary mb-8 font-theme-primary max-w-md mx-auto">
                The requested part could not be found. It may have been deleted or the link may be incorrect.
              </p>
              <button
                onClick={() => navigate('/parts')}
                className="inline-flex items-center gap-2 px-6 py-3 bg-primary text-theme-inverse rounded-lg hover:bg-primary-dark transition-colors font-medium"
              >
                <ArrowLeft className="w-4 h-4" />
                Back to Parts
              </button>
            </div>
          </div>
        </div>
      </div>
    )
  }

  const additionalProps = part.additional_properties || {}
  const propertyLeafCount = countPropertyLeaves(additionalProps)
  const lastEnrichmentIso = additionalProps?.metadata?.last_enrichment || additionalProps?.last_enrichment || additionalProps?.last_enrichment_date
  const lastEnrichmentDisplay = formatDateTime(lastEnrichmentIso)

  // Simple check if we have additional properties to display
  const hasAdditionalProperties = additionalProps && Object.keys(additionalProps).length > 0

  return (
    <div className="min-h-screen bg-theme-secondary">
      <div className="max-w-screen-2xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
        <div className="space-y-6">
          {/* Modern Header */}
          <motion.div
            initial={{ opacity: 0, y: -20 }}
            animate={{ opacity: 1, y: 0 }}
            className="bg-theme-elevated border border-theme-primary rounded-xl p-6 shadow-sm"
          >
            <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4">
              <div className="flex items-center gap-4">
                <button
                  onClick={() => navigate('/parts')}
                  className="inline-flex items-center justify-center w-10 h-10 rounded-lg bg-theme-secondary border border-theme-primary hover:bg-theme-tertiary transition-colors"
                  title="Back to Parts"
                >
                  <ArrowLeft className="w-5 h-5 text-theme-secondary" />
                </button>
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-3 mb-2">
                    <div className="p-2 bg-primary-10 rounded-lg">
                      <Package className="w-6 h-6 text-primary-accent" />
                    </div>
                    <button
                      onClick={() => copyToClipboard(part.name, 'part_name')}
                      className="group hover:bg-primary-10 rounded-lg px-3 py-2 transition-all duration-200 flex items-center gap-2 min-w-0"
                      title="Click to copy part name"
                    >
                      <h1 className="text-2xl font-theme-display font-bold text-theme-primary truncate">
                        {part.name}
                      </h1>
                      {copiedPartName ? (
                        <Check className="w-5 h-5 text-success shrink-0" />
                      ) : (
                        <Copy className="w-5 h-5 text-theme-muted opacity-0 group-hover:opacity-100 transition-opacity shrink-0" />
                      )}
                    </button>
                  </div>
                  <p className="text-theme-secondary font-theme-primary">
                    Electronic Component Details
                  </p>
                </div>
              </div>

              <div className="flex flex-wrap gap-3">
                <button
                  onClick={handleEnrich}
                  className="inline-flex items-center gap-2 px-4 py-2 bg-primary text-theme-inverse rounded-lg hover:bg-primary-dark transition-colors font-medium"
                >
                  <Zap className="w-4 h-4" />
                  Enrich Data
                </button>
                <button
                  onClick={() => setPrinterModalOpen(true)}
                  className="inline-flex items-center gap-2 px-4 py-2 bg-theme-tertiary border border-theme-primary text-theme-primary rounded-lg hover:bg-theme-secondary transition-colors font-medium"
                >
                  <Printer className="w-4 h-4" />
                  Print Label
                </button>
                <button
                  onClick={handleEdit}
                  className="inline-flex items-center gap-2 px-4 py-2 bg-theme-tertiary border border-theme-primary text-theme-primary rounded-lg hover:bg-theme-secondary transition-colors font-medium"
                >
                  <Edit className="w-4 h-4" />
                  Edit
                </button>
                <button
                  onClick={handleDelete}
                  className="inline-flex items-center gap-2 px-4 py-2 bg-error text-theme-inverse rounded-lg hover:opacity-90 transition-opacity font-medium"
                >
                  <Trash2 className="w-4 h-4" />
                  Delete
                </button>
              </div>
            </div>
          </motion.div>

          {/* Enhanced Basic Information Section */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1 }}
            className="bg-theme-elevated border border-theme-primary rounded-xl overflow-hidden shadow-sm"
          >
            <div className="bg-theme-tertiary border-b border-theme-primary px-6 py-4">
              <h2 className="text-xl font-theme-display font-semibold text-theme-primary flex items-center gap-3">
                <div className="p-2 bg-primary-10 rounded-lg">
                  <Info className="w-5 h-5 text-primary-accent" />
                </div>
                Basic Information
              </h2>
            </div>

            <div className="p-6">
              <div className="grid grid-cols-1 xl:grid-cols-4 gap-8">
                {/* Enhanced Image Section */}
                <div className="xl:col-span-1">
                  <div className="space-y-4">
                    <div className="aspect-square w-full max-w-64 mx-auto xl:mx-0">
                      <div className="w-full h-full bg-theme-secondary border-2 border-theme-primary rounded-xl p-4 shadow-inner">
                        <PartImage
                          imageUrl={part.image_url}
                          partName={part.name}
                          size="xl"
                          showFallback={true}
                          className="w-full h-full object-contain"
                        />
                      </div>
                    </div>

                    {/* Part Status Indicators */}
                    <div className="space-y-2">
                      <div className={`inline-flex items-center gap-2 px-3 py-2 rounded-lg text-sm font-medium ${
                        part.minimum_quantity && part.quantity <= part.minimum_quantity
                          ? 'bg-error text-theme-inverse'
                          : part.quantity > 0
                          ? 'bg-success text-theme-inverse'
                          : 'bg-warning text-theme-inverse'
                      }`}>
                        <Box className="w-4 h-4" />
                        {part.minimum_quantity && part.quantity <= part.minimum_quantity
                          ? `Low Stock (${part.quantity} remaining)`
                          : part.quantity > 0
                          ? `In Stock (${part.quantity} available)`
                          : 'Out of Stock (0 available)'
                        }
                      </div>

                      {part.lifecycle_status && (
                        <div className="inline-flex items-center gap-2 px-3 py-2 bg-primary-10 text-primary-accent rounded-lg text-sm font-medium">
                          <AlertCircle className="w-4 h-4" />
                          {formatEnumValue(part.lifecycle_status)}
                        </div>
                      )}
                    </div>
                  </div>
                </div>

                {/* Enhanced Info Grid */}
                <div className="xl:col-span-3">
                  <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6">
                    {/* Part Number Field */}
                    <div
                      className="bg-theme-secondary border border-theme-primary rounded-lg p-4 hover:bg-theme-tertiary transition-colors cursor-pointer"
                      onClick={() => startEditing('part_number', part.part_number || '')}
                    >
                      <div className="flex items-start gap-3">
                        <div className="p-2 bg-primary-10 rounded-lg shrink-0">
                          <Hash className="w-4 h-4 text-primary-accent" />
                        </div>
                        <div className="min-w-0 flex-1">
                          <p className="text-sm font-medium text-theme-secondary mb-1">Part Number</p>
                          {editingField === 'part_number' ? (
                            <div className="flex items-center gap-2" onClick={(e) => e.stopPropagation()}>
                              <input
                                type="text"
                                value={editingValue}
                                onChange={(e) => setEditingValue(e.target.value)}
                                className="flex-1 px-2 py-1 text-sm bg-theme-primary text-theme-primary border border-theme-primary rounded focus:outline-none focus:ring-2 focus:ring-primary"
                                autoFocus
                                onKeyDown={(e) => {
                                  if (e.key === 'Enter') saveField('part_number', editingValue)
                                  if (e.key === 'Escape') cancelEditing()
                                }}
                              />
                              <button
                                onClick={() => saveField('part_number', editingValue)}
                                disabled={saving}
                                className="px-2 py-1 bg-success text-theme-inverse rounded text-xs disabled:opacity-50"
                              >
                                {saving ? '⏳' : '✓'}
                              </button>
                              <button
                                onClick={cancelEditing}
                                className="px-2 py-1 bg-error text-theme-inverse rounded text-xs"
                              >
                                ✕
                              </button>
                            </div>
                          ) : (
                            part.part_number ? (
                              <button
                                onClick={(e) => {
                                  e.stopPropagation()
                                  copyToClipboard(part.part_number!, 'part_number')
                                }}
                                className="group hover:bg-primary-10 rounded-lg px-2 py-1 transition-all flex items-center gap-2 min-w-0"
                                title="Click to copy part number"
                              >
                                <p className="font-theme-mono font-semibold text-theme-primary truncate">
                                  {part.part_number}
                                </p>
                                {copiedPartNumber ? (
                                  <Check className="w-4 h-4 text-success shrink-0" />
                                ) : (
                                  <Copy className="w-4 h-4 text-theme-muted opacity-0 group-hover:opacity-100 transition-opacity shrink-0" />
                                )}
                              </button>
                            ) : (
                              <p className="font-semibold text-theme-muted">Not set</p>
                            )
                          )}
                        </div>
                      </div>
                    </div>

                    {/* Quantity Field */}
                    <div
                      className="bg-theme-secondary border border-theme-primary rounded-lg p-4 hover:bg-theme-tertiary transition-colors cursor-pointer"
                      onClick={() => startEditing('quantity', part.quantity.toString())}
                    >
                      <div className="flex items-start gap-3">
                        <div className="p-2 bg-primary-10 rounded-lg shrink-0">
                          <Box className="w-4 h-4 text-primary-accent" />
                        </div>
                        <div className="min-w-0 flex-1">
                          <p className="text-sm font-medium text-theme-secondary mb-1">Quantity</p>
                          {editingField === 'quantity' ? (
                            <div className="flex items-center gap-2" onClick={(e) => e.stopPropagation()}>
                              <input
                                type="number"
                                value={editingValue}
                                onChange={(e) => setEditingValue(e.target.value)}
                                className="w-20 px-2 py-1 text-sm bg-theme-primary text-theme-primary border border-theme-primary rounded focus:outline-none focus:ring-2 focus:ring-primary"
                                autoFocus
                                onKeyDown={(e) => {
                                  if (e.key === 'Enter') saveField('quantity', editingValue)
                                  if (e.key === 'Escape') cancelEditing()
                                }}
                              />
                              <button
                                onClick={() => saveField('quantity', editingValue)}
                                disabled={saving}
                                className="px-2 py-1 bg-success text-theme-inverse rounded text-xs disabled:opacity-50"
                              >
                                {saving ? '⏳' : '✓'}
                              </button>
                              <button
                                onClick={cancelEditing}
                                className="px-2 py-1 bg-error text-theme-inverse rounded text-xs"
                              >
                                ✕
                              </button>
                            </div>
                          ) : (
                            <div className="flex items-center gap-2">
                              <p className={`font-bold text-lg ${
                                part.minimum_quantity && part.quantity <= part.minimum_quantity
                                  ? 'text-error'
                                  : 'text-theme-primary'
                              }`}>
                                {part.quantity}
                              </p>
                              {part.minimum_quantity && (
                                <span className="text-xs text-theme-muted bg-theme-tertiary px-2 py-1 rounded">
                                  Min: {part.minimum_quantity}
                                </span>
                              )}
                            </div>
                          )}
                        </div>
                      </div>
                    </div>

                    {/* Location Field */}
                    <div className="bg-theme-secondary border border-theme-primary rounded-lg p-4 hover:bg-theme-tertiary transition-colors">
                      <div className="flex items-start gap-3">
                        <div className="p-2 bg-primary-10 rounded-lg shrink-0">
                          <MapPin className="w-4 h-4 text-primary-accent" />
                        </div>
                        <div className="min-w-0 flex-1">
                          <p className="text-sm font-medium text-theme-secondary mb-1">Location</p>
                          <p className="font-semibold text-theme-primary">
                            {part.location?.name || 'Not assigned'}
                          </p>
                        </div>
                      </div>
                    </div>

                    {/* Supplier Field */}
                    <div
                      className="bg-theme-secondary border border-theme-primary rounded-lg p-4 hover:bg-theme-tertiary transition-colors cursor-pointer"
                      onClick={() => startEditing('supplier', part.supplier || '')}
                    >
                      <div className="flex items-start gap-3">
                        <div className="p-2 bg-primary-10 rounded-lg shrink-0">
                          <Tag className="w-4 h-4 text-primary-accent" />
                        </div>
                        <div className="min-w-0 flex-1">
                          <p className="text-sm font-medium text-theme-secondary mb-1">Supplier</p>
                          {editingField === 'supplier' ? (
                            <div className="flex items-center gap-2" onClick={(e) => e.stopPropagation()}>
                              <input
                                type="text"
                                value={editingValue}
                                onChange={(e) => setEditingValue(e.target.value)}
                                className="flex-1 px-2 py-1 text-sm bg-theme-primary text-theme-primary border border-theme-primary rounded focus:outline-none focus:ring-2 focus:ring-primary"
                                autoFocus
                                onKeyDown={(e) => {
                                  if (e.key === 'Enter') saveField('supplier', editingValue)
                                  if (e.key === 'Escape') cancelEditing()
                                }}
                              />
                              <button
                                onClick={() => saveField('supplier', editingValue)}
                                disabled={saving}
                                className="px-2 py-1 bg-success text-theme-inverse rounded text-xs disabled:opacity-50"
                              >
                                {saving ? '⏳' : '✓'}
                              </button>
                              <button
                                onClick={cancelEditing}
                                className="px-2 py-1 bg-error text-theme-inverse rounded text-xs"
                              >
                                ✕
                              </button>
                            </div>
                          ) : (
                            <div className="flex items-center gap-2">
                              <p className="font-semibold text-theme-primary">{part.supplier || 'Not set'}</p>
                              {part.supplier_url && (
                                <a
                                  href={part.supplier_url}
                                  target="_blank"
                                  rel="noopener noreferrer"
                                  className="text-primary-accent hover:text-primary transition-colors"
                                  title="View supplier page"
                                  onClick={(e) => e.stopPropagation()}
                                >
                                  <ExternalLink className="w-4 h-4" />
                                </a>
                              )}
                            </div>
                          )}
                        </div>
                      </div>
                    </div>

                    {/* Manufacturer Field */}
                    <div className="bg-theme-secondary border border-theme-primary rounded-lg p-4 hover:bg-theme-tertiary transition-colors">
                      <div className="flex items-start gap-3">
                        <div className="p-2 bg-primary-10 rounded-lg shrink-0">
                          <Factory className="w-4 h-4 text-primary-accent" />
                        </div>
                        <div className="min-w-0 flex-1">
                          <p className="text-sm font-medium text-theme-secondary mb-1">Manufacturer</p>
                          <p className="font-semibold text-theme-primary">
                            {part.manufacturer || 'Not set'}
                          </p>
                        </div>
                      </div>
                    </div>

                    {/* Manufacturer Part Number Field */}
                    <div className="bg-theme-secondary border border-theme-primary rounded-lg p-4 hover:bg-theme-tertiary transition-colors">
                      <div className="flex items-start gap-3">
                        <div className="p-2 bg-primary-10 rounded-lg shrink-0">
                          <Cpu className="w-4 h-4 text-primary-accent" />
                        </div>
                        <div className="min-w-0 flex-1">
                          <p className="text-sm font-medium text-theme-secondary mb-1">Manufacturer Part Number</p>
                          <p className="font-theme-mono font-semibold text-theme-primary">
                            {part.manufacturer_part_number || 'Not set'}
                          </p>
                        </div>
                      </div>
                    </div>


                    {/* Created Date Field */}
                    <div className="bg-theme-secondary border border-theme-primary rounded-lg p-4 hover:bg-theme-tertiary transition-colors">
                      <div className="flex items-start gap-3">
                        <div className="p-2 bg-primary-10 rounded-lg shrink-0">
                          <Calendar className="w-4 h-4 text-primary-accent" />
                        </div>
                        <div className="min-w-0 flex-1">
                          <p className="text-sm font-medium text-theme-secondary mb-1">Created</p>
                          <p className="font-medium text-theme-primary">{formatDate(part.created_at)}</p>
                        </div>
                      </div>
                    </div>

                    {/* Last Updated Field */}
                    <div className="bg-theme-secondary border border-theme-primary rounded-lg p-4 hover:bg-theme-tertiary transition-colors">
                      <div className="flex items-start gap-3">
                        <div className="p-2 bg-primary-10 rounded-lg shrink-0">
                          <Calendar className="w-4 h-4 text-primary-accent" />
                        </div>
                        <div className="min-w-0 flex-1">
                          <p className="text-sm font-medium text-theme-secondary mb-1">Last Updated</p>
                          <p className="font-medium text-theme-primary">{formatDate(part.updated_at)}</p>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </motion.div>

          {/* Enhanced Categories Section - Always Visible */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.2 }}
            className="bg-theme-elevated border border-theme-primary rounded-xl overflow-hidden shadow-sm"
          >
            <div className="bg-theme-tertiary border-b border-theme-primary px-6 py-4">
              <div className="flex items-center justify-between">
                <h2 className="text-xl font-theme-display font-semibold text-theme-primary flex items-center gap-3">
                  <div className="p-2 bg-primary-10 rounded-lg">
                    <Tag className="w-5 h-5 text-primary-accent" />
                  </div>
                  Categories
                  <span className="text-sm bg-primary-10 text-primary-accent px-3 py-1 rounded-full font-medium">
                    {part.categories?.length || 0}
                  </span>
                </h2>

                <div className="flex items-center gap-2">
                  <button
                    onClick={handleAddCategoryDirect}
                    className="btn btn-secondary btn-sm flex items-center gap-2"
                    title="Create new category"
                  >
                    <Plus className="w-4 h-4" />
                    New Category
                  </button>
                  <button
                    onClick={() => setCategoryManagementOpen(true)}
                    className="btn btn-primary btn-sm flex items-center gap-2"
                    title="Manage categories for this part"
                  >
                    <Tag className="w-4 h-4" />
                    Manage Categories
                  </button>
                </div>
              </div>
            </div>

            <div className="p-6">
              {part.categories && part.categories.length > 0 ? (
                <div className="flex flex-wrap gap-3">
                  {part.categories.map((category) => (
                    <span
                      key={category.id}
                      className="inline-flex items-center gap-2 px-4 py-2 bg-primary-10 text-primary-accent rounded-lg text-sm font-medium hover:bg-primary-20 transition-colors border border-primary-20"
                    >
                      <div className="w-2 h-2 bg-primary-accent rounded-full"></div>
                      {category.name}
                    </span>
                  ))}
                </div>
              ) : (
                <div className="text-center py-8">
                  <Tag className="w-12 h-12 text-theme-muted mx-auto mb-3" />
                  <p className="text-theme-muted text-sm mb-4">
                    No categories assigned to this part yet.
                  </p>
                  <div className="flex items-center justify-center gap-2">
                    <button
                      onClick={() => setCategoryManagementOpen(true)}
                      className="btn btn-primary btn-sm flex items-center gap-2"
                    >
                      <Tag className="w-4 h-4" />
                      Assign Existing Category
                    </button>
                    <button
                      onClick={handleAddCategoryDirect}
                      className="btn btn-secondary btn-sm flex items-center gap-2"
                    >
                      <Plus className="w-4 h-4" />
                      Create New Category
                    </button>
                  </div>
                </div>
              )}
            </div>
          </motion.div>

          {/* Enhanced Description Section */}
          {part.description && (
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.25 }}
              className="bg-theme-elevated border border-theme-primary rounded-xl overflow-hidden shadow-sm"
            >
              <div className="bg-theme-tertiary border-b border-theme-primary px-6 py-4">
                <h2 className="text-xl font-theme-display font-semibold text-theme-primary flex items-center gap-3">
                  <div className="p-2 bg-primary-10 rounded-lg">
                    <FileText className="w-5 h-5 text-primary-accent" />
                  </div>
                  Description
                </h2>
              </div>
              <div className="p-6">
                <div
                  className="bg-theme-secondary border border-theme-primary rounded-lg p-4 cursor-pointer hover:bg-theme-tertiary transition-colors"
                  onClick={() => startEditing('description', part.description || '')}
                >
                  {editingField === 'description' ? (
                    <div onClick={(e) => e.stopPropagation()}>
                      <textarea
                        value={editingValue}
                        onChange={(e) => setEditingValue(e.target.value)}
                        className="w-full h-24 px-3 py-2 text-sm bg-theme-primary text-theme-primary border border-theme-primary rounded focus:outline-none focus:ring-2 focus:ring-primary resize-none"
                        autoFocus
                        onKeyDown={(e) => {
                          if (e.key === 'Enter' && e.ctrlKey) saveField('description', editingValue)
                          if (e.key === 'Escape') cancelEditing()
                        }}
                      />
                      <div className="flex items-center gap-2 mt-2">
                        <button
                          onClick={() => saveField('description', editingValue)}
                          disabled={saving}
                          className="px-3 py-1 bg-success text-theme-inverse rounded text-sm disabled:opacity-50"
                        >
                          {saving ? '⏳ Saving...' : 'Save'}
                        </button>
                        <button
                          onClick={cancelEditing}
                          className="px-3 py-1 bg-error text-theme-inverse rounded text-sm"
                        >
                          Cancel
                        </button>
                        <span className="text-xs text-theme-muted">Ctrl+Enter to save</span>
                      </div>
                    </div>
                  ) : (
                    <p className="text-theme-primary leading-relaxed font-theme-primary">
                      {part.description}
                    </p>
                  )}
                </div>
              </div>
            </motion.div>
          )}

      {/* Datasheets Section */}
      {((part.datasheets && part.datasheets.length > 0) || part.additional_properties?.datasheet_url || (part.additional_properties?.datasheet_downloaded && part.additional_properties?.datasheet_filename)) && (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3 }}
          className="card"
        >
          <div className="card-header">
            <h2 className="text-lg font-semibold text-primary flex items-center gap-2">
              <FileText className="w-5 h-5" />
              Datasheets
              <span className="text-sm bg-primary/10 text-primary px-2 py-1 rounded">
                {(part.datasheets?.length || 0) + (part.additional_properties?.datasheet_url ? 1 : 0) + (part.additional_properties?.datasheet_downloaded && part.additional_properties?.datasheet_filename ? 1 : 0)} file{((part.datasheets?.length || 0) + (part.additional_properties?.datasheet_url ? 1 : 0) + (part.additional_properties?.datasheet_downloaded && part.additional_properties?.datasheet_filename ? 1 : 0)) !== 1 ? 's' : ''}
              </span>
            </h2>
          </div>
          <div className="card-content">
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {/* Existing downloaded datasheets */}
              {part.datasheets?.map((datasheet) => (
                <div
                  key={datasheet.id}
                  className="border border-border/50 rounded-lg p-4 bg-background-secondary/30 hover:bg-background-secondary/50 transition-colors"
                >
                  <div className="flex items-start justify-between mb-3">
                    <div className="flex items-center gap-2">
                      <FileText className="w-5 h-5 text-blue-400 flex-shrink-0" />
                      <div className="min-w-0">
                        <h3 className="font-medium text-primary truncate">
                          {datasheet.title || datasheet.original_filename || datasheet.filename}
                        </h3>
                        {datasheet.supplier && (
                          <p className="text-xs text-secondary">{datasheet.supplier}</p>
                        )}
                      </div>
                    </div>
                    <div className={`px-2 py-1 rounded text-xs ${
                      datasheet.is_downloaded 
                        ? 'bg-green-500/10 text-green-400' 
                        : 'bg-yellow-500/10 text-yellow-400'
                    }`}>
                      {datasheet.is_downloaded ? 'Downloaded' : 'Pending'}
                    </div>
                  </div>

                  {datasheet.description && (
                    <p className="text-sm text-secondary mb-3 line-clamp-2">
                      {datasheet.description}
                    </p>
                  )}

                  <div className="space-y-2 mb-4">
                    <div className="flex justify-between text-xs text-muted">
                      <span>Size:</span>
                      <span>{formatFileSize(datasheet.file_size)}</span>
                    </div>
                    <div className="flex justify-between text-xs text-muted">
                      <span>Added:</span>
                      <span>{formatDate(datasheet.created_at)}</span>
                    </div>
                    {datasheet.source_url && (
                      <div className="flex justify-between text-xs text-muted">
                        <span>Source:</span>
                        <a
                          href={datasheet.source_url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-primary hover:text-primary-dark flex items-center gap-1"
                        >
                          <span className="truncate max-w-20">Original</span>
                          <ExternalLink className="w-3 h-3 flex-shrink-0" />
                        </a>
                      </div>
                    )}
                  </div>

                  {datasheet.is_downloaded ? (
                    <div className="flex gap-2">
                      <button
                        onClick={() => viewDatasheet(datasheet)}
                        className="flex-1 btn btn-primary text-sm flex items-center justify-center gap-2"
                      >
                        <Eye className="w-4 h-4" />
                        View
                      </button>
                      <button
                        onClick={() => downloadDatasheet(datasheet)}
                        className="btn btn-secondary text-sm flex items-center justify-center"
                        title="Download"
                      >
                        <Download className="w-4 h-4" />
                      </button>
                    </div>
                  ) : (
                    <div className="text-center py-2">
                      <p className="text-sm text-muted">
                        {datasheet.download_error 
                          ? `Download failed: ${datasheet.download_error}`
                          : 'Download pending...'
                        }
                      </p>
                    </div>
                  )}
                </div>
              ))}
              
              {/* Downloaded datasheet from additional_properties */}
              {part.additional_properties?.datasheet_downloaded && part.additional_properties?.datasheet_filename && (
                <div className="border border-border/50 rounded-lg p-4 bg-background-secondary/30 hover:bg-background-secondary/50 transition-colors">
                  <div className="flex items-start justify-between mb-3">
                    <div className="flex items-center gap-2">
                      <FileText className="w-5 h-5 text-green-400 flex-shrink-0" />
                      <div className="min-w-0">
                        <h3 className="font-medium text-primary truncate">
                          Downloaded Datasheet
                        </h3>
                        <p className="text-xs text-secondary">
                          {part.supplier || 'Unknown Supplier'}
                        </p>
                      </div>
                    </div>
                    <div className="px-2 py-1 rounded text-xs bg-green-500/10 text-green-400">
                      Local
                    </div>
                  </div>
                  
                  <p className="text-sm text-secondary mb-3 line-clamp-2">
                    Datasheet downloaded during enrichment
                  </p>
                  
                  <div className="space-y-2 mb-4">
                    <div className="flex justify-between text-xs text-muted">
                      <span>Size:</span>
                      <span>{((part.additional_properties.datasheet_size || 0) / 1024).toFixed(1)} KB</span>
                    </div>
                    <div className="flex justify-between text-xs text-muted">
                      <span>Status:</span>
                      <span>Downloaded</span>
                    </div>
                  </div>
                  
                  <div className="flex gap-2">
                    <button
                      onClick={() => {
                        const url = `/api/utility/static/datasheets/${part.additional_properties.datasheet_filename}`
                        setPdfPreviewUrl(url)
                        setPdfPreviewOpen(true)
                      }}
                      className="flex-1 btn btn-primary text-sm flex items-center justify-center gap-2"
                    >
                      <Eye className="w-4 h-4" />
                      View PDF
                    </button>
                    <button
                      onClick={() => {
                        const url = `/api/utility/static/datasheets/${part.additional_properties.datasheet_filename}`
                        const link = document.createElement('a')
                        link.href = url
                        link.download = part.additional_properties.datasheet_filename || 'datasheet.pdf'
                        document.body.appendChild(link)
                        link.click()
                        document.body.removeChild(link)
                      }}
                      className="btn btn-secondary text-sm flex items-center justify-center"
                      title="Download"
                    >
                      <Download className="w-4 h-4" />
                    </button>
                  </div>
                </div>
              )}
              
              {/* Enriched datasheet URL from additional_properties */}
              {part.additional_properties?.datasheet_url && (
                <div className="border border-border/50 rounded-lg p-4 bg-background-secondary/30 hover:bg-background-secondary/50 transition-colors">
                  <div className="flex items-start justify-between mb-3">
                    <div className="flex items-center gap-2">
                      <FileText className="w-5 h-5 text-blue-400 flex-shrink-0" />
                      <div className="min-w-0">
                        <h3 className="font-medium text-primary truncate">
                          Supplier Datasheet
                        </h3>
                        <p className="text-xs text-secondary">
                          {part.supplier || 'Unknown Supplier'}
                        </p>
                      </div>
                    </div>
                    <div className="px-2 py-1 rounded text-xs bg-blue-500/10 text-blue-400">
                      Online
                    </div>
                  </div>
                  
                  <p className="text-sm text-secondary mb-3 line-clamp-2">
                    Official datasheet from supplier website
                  </p>
                  
                  <div className="space-y-2 mb-4">
                    <div className="flex justify-between text-xs text-muted">
                      <span>Source:</span>
                      <span>Supplier API</span>
                    </div>
                    <div className="flex justify-between text-xs text-muted">
                      <span>Type:</span>
                      <span>External Link</span>
                    </div>
                  </div>
                  
                  <div className="flex gap-2">
                    <button
                      onClick={() => openPDFPreview(part.additional_properties.datasheet_url)}
                      className="flex-1 btn btn-primary text-sm flex items-center justify-center gap-2"
                    >
                      <Eye className="w-4 h-4" />
                      Preview PDF
                    </button>
                    <a
                      href={part.additional_properties.datasheet_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="btn btn-secondary text-sm flex items-center justify-center"
                      title="Open in new tab"
                    >
                      <ExternalLink className="w-4 h-4" />
                    </a>
                  </div>
                </div>
              )}
            </div>
          </div>
        </motion.div>
      )}

      {/* Additional Properties */}
      {hasAdditionalProperties && (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.35 }}
          className="bg-theme-elevated border border-theme-primary rounded-xl overflow-hidden shadow-sm"
        >
          <div className="bg-theme-tertiary border-b border-theme-primary px-6 py-4">
            <div className="flex flex-wrap items-center justify-between gap-4">
              <div>
                <h2 className="text-xl font-theme-display font-semibold text-theme-primary flex items-center gap-3">
                  <div className="p-2 bg-primary-10 rounded-lg">
                    <Cpu className="w-5 h-5 text-primary-accent" />
                  </div>
                  Additional Properties
                </h2>
                {lastEnrichmentDisplay && (
                  <p className="text-sm text-theme-secondary mt-1 flex items-center gap-2">
                    <Clock className="w-4 h-4" />
                    Data enriched {lastEnrichmentDisplay}
                  </p>
                )}
              </div>
            </div>
          </div>

          <div className="p-6">
            <CleanPropertiesDisplay properties={additionalProps} />
          </div>
        </motion.div>
      )}

      {/* Order History Section */}
      {priceTrends.length > 0 && (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.4 }}
          className="card"
        >
          <div className="card-header">
            <h2 className="text-lg font-semibold text-primary flex items-center gap-2">
              <TrendingUp className="w-5 h-5" />
              Order History & Price Trends
              <span className="text-sm bg-primary/10 text-primary px-2 py-1 rounded">
                {priceTrends.length} orders
              </span>
            </h2>
          </div>
          <div className="card-content">
            {loadingPriceHistory ? (
              <div className="flex items-center justify-center py-8">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
              </div>
            ) : (
              <div className="space-y-6">
                {/* Price Trend Chart */}
                <div>
                  <h3 className="text-md font-medium text-primary mb-4">Price Trend</h3>
                  <div className="h-64">
                    <Line
                      data={{
                        labels: priceTrends.map(item => new Date(item.order_date).toLocaleDateString()),
                        datasets: [
                          {
                            label: 'Unit Price',
                            data: priceTrends.map(item => item.unit_price),
                            borderColor: 'rgb(99, 102, 241)',
                            backgroundColor: 'rgba(99, 102, 241, 0.1)',
                            fill: true,
                            tension: 0.4
                          }
                        ]
                      }}
                      options={{
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: {
                          legend: {
                            display: false
                          }
                        },
                        scales: {
                          y: {
                            beginAtZero: false,
                            ticks: {
                              callback: function(value: any) {
                                return '$' + Number(value).toFixed(2)
                              }
                            }
                          }
                        }
                      }}
                    />
                  </div>
                </div>

                {/* Order Details Table */}
                <div>
                  <h3 className="text-md font-medium text-primary mb-4">Order Details</h3>
                  <div className="overflow-x-auto">
                    <table className="table w-full">
                      <thead>
                        <tr>
                          <th>Date</th>
                          <th>Supplier</th>
                          <th>Unit Price</th>
                          <th>Change</th>
                        </tr>
                      </thead>
                      <tbody>
                        {priceTrends.map((trend, index) => {
                          const prevPrice = index < priceTrends.length - 1 ? priceTrends[index + 1].unit_price : null
                          const priceChange = prevPrice ? ((trend.unit_price - prevPrice) / prevPrice) * 100 : 0
                          
                          return (
                            <tr key={index}>
                              <td className="text-primary">{new Date(trend.order_date).toLocaleDateString()}</td>
                              <td className="text-secondary">{trend.supplier}</td>
                              <td className="text-secondary">${trend.unit_price.toFixed(2)}</td>
                              <td>
                                {prevPrice && (
                                  <span className={`flex items-center gap-1 ${priceChange > 0 ? 'text-error' : priceChange < 0 ? 'text-success' : 'text-secondary'}`}>
                                    {priceChange > 0 ? '↑' : priceChange < 0 ? '↓' : '→'}
                                    {Math.abs(priceChange).toFixed(1)}%
                                  </span>
                                )}
                              </td>
                            </tr>
                          )
                        })}
                      </tbody>
                    </table>
                  </div>
                </div>
              </div>
            )}
          </div>
        </motion.div>
      )}

      {/* PDF Viewer Modal */}
      {selectedDatasheet && (
        <PartPDFViewer
          isOpen={pdfViewerOpen}
          onClose={() => {
            setPdfViewerOpen(false)
            setSelectedDatasheet(null)
          }}
          datasheet={selectedDatasheet}
        />
      )}

      {/* Enrichment Modal */}
      <PartEnrichmentModal
        isOpen={enrichmentModalOpen}
        onClose={() => setEnrichmentModalOpen(false)}
        part={part}
        onPartUpdated={handlePartUpdated}
      />

      {/* Printer Modal */}
      <PrinterModal
        isOpen={printerModalOpen}
        onClose={() => setPrinterModalOpen(false)}
        partData={{
          id: part.id,
          part_name: part.name,
          part_number: part.part_number || '',
          location: part.location?.name || '',
          category: part.categories?.[0]?.name || '',
          quantity: part.quantity?.toString() || '0',
          description: part.description || '',
          additional_properties: part.additional_properties || {}
        }}
      />

      {/* Add Category Modal */}
      <AddCategoryModal
        isOpen={addCategoryModalOpen}
        onClose={() => setAddCategoryModalOpen(false)}
        onSuccess={handleAddCategorySuccess}
        existingCategories={allCategories.map(cat => cat.name)}
      />

      {/* Category Management Modal */}
      {categoryManagementOpen && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
          <div className="bg-theme-elevated border border-theme-primary rounded-xl shadow-xl max-w-2xl w-full max-h-[80vh] overflow-hidden">
            <div className="bg-theme-tertiary border-b border-theme-primary px-6 py-4">
              <h2 className="text-xl font-theme-display font-semibold text-theme-primary flex items-center gap-3">
                <Tag className="w-5 h-5 text-primary-accent" />
                Manage Categories for {part?.name}
              </h2>
            </div>

            <div className="p-6">
              {loadingCategories ? (
                <div className="text-center py-8">
                  <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-accent mx-auto"></div>
                  <p className="text-theme-muted mt-3">Loading categories...</p>
                </div>
              ) : (
                <CategorySelector
                  categories={allCategories}
                  selectedCategories={selectedCategoryIds}
                  onToggleCategory={handleToggleCategory}
                  onAddNewCategory={handleAddCategoryFromManagement}
                  label="Select Categories"
                  description="Choose which categories to assign to this part"
                  showAddButton={true}
                  layout="checkboxes"
                />
              )}
            </div>

            <div className="bg-theme-tertiary border-t border-theme-primary px-6 py-4 flex items-center justify-between">
              <button
                onClick={() => setCategoryManagementOpen(false)}
                className="btn btn-secondary"
                disabled={saving}
              >
                Cancel
              </button>
              <button
                onClick={saveCategoryChanges}
                className="btn btn-primary flex items-center gap-2"
                disabled={saving}
              >
                {saving ? (
                  <>
                    <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
                    Saving...
                  </>
                ) : (
                  <>
                    <Tag className="w-4 h-4" />
                    Save Categories
                  </>
                )}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Debug Section */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.5 }}
        className="bg-theme-elevated border border-theme-primary rounded-xl overflow-hidden shadow-sm"
      >
        <details className="group">
          <summary className="cursor-pointer p-4 hover:bg-theme-tertiary transition-colors">
            <span className="text-sm font-medium text-theme-secondary flex items-center gap-2">
              <Settings className="w-4 h-4" />
              Debug Information
              <span className="text-xs bg-theme-tertiary px-2 py-1 rounded">
                Raw Data
              </span>
            </span>
          </summary>
          <div className="border-t border-theme-primary p-4">
            <div className="bg-theme-secondary border border-theme-primary rounded-lg p-4">
              <pre className="text-xs font-mono text-theme-primary overflow-auto max-h-96">
                {JSON.stringify(part, null, 2)}
              </pre>
            </div>
          </div>
        </details>
      </motion.div>

      {/* PDF Preview Modal for Supplier Datasheets */}
      {pdfPreviewOpen && pdfPreviewUrl && (
        <PDFViewer
          fileUrl={pdfPreviewUrl}
          fileName={`${part?.name || 'Part'} - Datasheet.pdf`}
          onClose={() => setPdfPreviewOpen(false)}
        />
      )}
        </div>
      </div>
    </div>
  );
};

// Additional properties explorer functions

// type AdditionalPropertiesExplorerProps = {
//   properties: Record<string, any>
// }

// type PropertyGroupProps = {
//   propertyKey: string
//   value: any
// }

// type PropertyTreeProps = {
//   value: any
//   depth: number
// }

// type PropertyValueProps = {
//   value: any
// }


function CleanPropertiesDisplay({ properties }: { properties: Record<string, any> }) {
  const entries = Object.entries(properties)
  if (!entries.length) return null

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
      {entries.map(([key, value]) => (
        <SpecificationCard key={key} label={key} value={value} />
      ))}
    </div>
  )
}

function SpecificationCard({ label, value, small = false }: { label: string; value: any; small?: boolean }) {
  const isImportant = ['Package', 'Unit Price', 'Minimum Order Quantity'].includes(label)
  const [isExpanded, setIsExpanded] = useState(false)

  // Check if this is a complex object that could be expanded
  const isComplexObject = typeof value === 'object' && value !== null && !Array.isArray(value) && Object.keys(value).length > 1
  const formattedValue = formatSpecValue(value)

  return (
    <div className={`
      bg-theme-secondary border border-theme-primary rounded-lg p-4 hover:bg-theme-tertiary transition-colors
      ${isImportant ? 'ring-2 ring-primary-accent ring-opacity-20' : ''}
      ${small ? 'p-3' : ''}
    `}>
      <div className="space-y-2">
        <dt className={`text-xs font-medium text-theme-secondary uppercase tracking-wide ${small ? 'text-[10px]' : ''} flex items-center justify-between`}>
          <span>{formatEnumValue(label)}</span>
          {isComplexObject && (
            <button
              onClick={() => setIsExpanded(!isExpanded)}
              className="text-primary-accent hover:text-primary transition-colors"
              title={isExpanded ? 'Collapse' : 'Expand details'}
            >
              {isExpanded ? '▲' : '▼'}
            </button>
          )}
        </dt>
        <dd className={`font-semibold text-theme-primary ${small ? 'text-sm' : 'text-base'}`}>
          {isExpanded && isComplexObject ? (
            <div className="space-y-1">
              {Object.entries(value).map(([key, val]) => (
                <div key={key} className="text-sm">
                  <span className="text-theme-secondary">{formatEnumValue(key)}:</span>{' '}
                  <span className="text-theme-primary">{formatSpecValue(val)}</span>
                </div>
              ))}
            </div>
          ) : (
            formattedValue
          )}
        </dd>
      </div>
    </div>
  )
}

function formatSpecValue(value: any): string | JSX.Element {
  if (value === null || value === undefined) return '—'
  if (typeof value === 'boolean') return value ? 'Yes' : 'No'
  if (typeof value === 'number') {
    // Format currency
    if (value > 0 && value < 1000 && value.toString().includes('.')) {
      return `$${value.toFixed(4)}`
    }
    return value.toString()
  }

  // Handle arrays
  if (Array.isArray(value)) {
    if (value.length === 0) return '—'
    if (value.length === 1) return formatSpecValue(value[0]) as string
    return value.map(item => formatSpecValue(item)).join(', ')
  }

  // Handle objects - show actual key-value pairs as separate lines
  if (typeof value === 'object') {
    if (value === null) return '—'

    // Try to extract meaningful data from objects first
    if (value.name) return String(value.name)
    if (value.value) return String(value.value)
    if (value.label) return String(value.label)
    if (value.title) return String(value.title)

    const keys = Object.keys(value)
    if (keys.length === 0) return '—'

    // If object has one key, try to show its value
    if (keys.length === 1) {
      const key = keys[0]
      const val = formatSpecValue(value[key])
      return `${key}: ${val}`
    }

    // For objects with multiple keys, return JSX with clean line breaks
    const pairs = keys
      .filter(key => value[key] !== null && value[key] !== undefined)
      .slice(0, 5) // Show more items since we're not cramming them together
      .map(key => {
        const val = formatSpecValue(value[key])
        return { key, val }
      })

    return (
      <div className="space-y-1">
        {pairs.map(({ key, val }, index) => (
          <div key={index} className="text-sm">
            <span className="text-theme-secondary font-medium">{key}:</span>{' '}
            <span className="text-theme-primary">{val}</span>
          </div>
        ))}
        {keys.length > 5 && (
          <div className="text-xs text-theme-secondary italic">
            +{keys.length - 5} more properties
          </div>
        )}
      </div>
    )
  }

  const stringValue = String(value)

  // Prevent [object Object] display
  if (stringValue === '[object Object]') return 'Complex Data'

  // Format dates
  const formattedDate = formatDateTime(stringValue)
  if (formattedDate) return formattedDate

  // Format URLs
  if (stringValue.startsWith('http')) {
    return stringValue.split('/').pop() || stringValue
  }

  return stringValue || '—'
}


export default PartDetailsPage;
