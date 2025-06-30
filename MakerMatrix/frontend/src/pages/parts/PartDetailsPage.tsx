import { motion } from 'framer-motion'
import { Package, Edit, Trash2, Tag, MapPin, Calendar, ArrowLeft, ExternalLink, Hash, Box, Image, Info, Zap, Settings, Globe, BookOpen, Clock, FileText, Download, Eye, Printer, TrendingUp, DollarSign, Copy, Check } from 'lucide-react'
import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { partsService } from '@/services/parts.service'
import { Part, Datasheet } from '@/types/parts'
import { getPDFProxyUrl } from '@/services/api'
import LoadingScreen from '@/components/ui/LoadingScreen'
import PartPDFViewer from '@/components/parts/PartPDFViewer'
import PDFViewer from '@/components/ui/PDFViewer'
import PartEnrichmentModal from '@/components/parts/PartEnrichmentModal'
import PrinterModal from '@/components/printer/PrinterModal'
import PartImage from '@/components/parts/PartImage'
import { analyticsService } from '@/services/analytics.service'
import { Line } from 'react-chartjs-2'

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

  useEffect(() => {
    if (id) {
      loadPart(id)
    }
  }, [id])

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

  if (loading) {
    return <LoadingScreen />
  }

  if (error) {
    return (
      <div className="space-y-6">
        <div className="bg-red-500/10 border border-red-500/20 rounded-lg p-4">
          <p className="text-red-400">{error}</p>
          <button 
            onClick={() => navigate('/parts')}
            className="text-red-300 hover:text-red-200 text-sm mt-2"
          >
            Back to Parts
          </button>
        </div>
      </div>
    )
  }

  if (!part) {
    return (
      <div className="space-y-6">
        <div className="text-center py-8">
          <Package className="w-16 h-16 text-muted mx-auto mb-4" />
          <h3 className="text-lg font-semibold text-primary mb-2">
            Part Not Found
          </h3>
          <p className="text-secondary mb-4">
            The requested part could not be found.
          </p>
          <button 
            onClick={() => navigate('/parts')}
            className="btn btn-primary"
          >
            Back to Parts
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <motion.div
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        className="flex items-center justify-between"
      >
        <div className="flex items-center gap-4">
          <button
            onClick={() => navigate('/parts')}
            className="btn btn-secondary btn-sm"
          >
            <ArrowLeft className="w-4 h-4" />
          </button>
          <div>
            <h1 className="text-2xl font-bold text-primary flex items-center gap-2">
              <Package className="w-6 h-6" />
              <button
                onClick={() => copyToClipboard(part.name, 'part_name')}
                className="hover:bg-primary/10 rounded px-2 py-1 transition-colors flex items-center gap-2 group"
                title="Click to copy part name"
              >
                {part.name}
                {copiedPartName ? (
                  <Check className="w-4 h-4 text-green-500" />
                ) : (
                  <Copy className="w-4 h-4 opacity-0 group-hover:opacity-100 transition-opacity" />
                )}
              </button>
            </h1>
            <p className="text-secondary mt-1">
              Part Details
            </p>
          </div>
        </div>
        <div className="flex gap-2">
          <button onClick={handleEnrich} className="btn btn-primary flex items-center gap-2">
            <Zap className="w-4 h-4" />
            Enrich
          </button>
          <button 
            onClick={() => setPrinterModalOpen(true)} 
            className="btn btn-secondary flex items-center gap-2"
          >
            <Printer className="w-4 h-4" />
            Print Label
          </button>
          <button onClick={handleEdit} className="btn btn-secondary flex items-center gap-2">
            <Edit className="w-4 h-4" />
            Edit
          </button>
          <button onClick={handleDelete} className="btn btn-danger flex items-center gap-2">
            <Trash2 className="w-4 h-4" />
            Delete
          </button>
        </div>
      </motion.div>

      {/* Image and Basic Information */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.1 }}
        className="card"
      >
        <div className="card-header">
          <h2 className="text-lg font-semibold text-primary">Basic Information</h2>
        </div>
        <div className="card-content">
          <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
            {/* Image Thumbnail */}
            <div className="lg:col-span-1">
              <div className="aspect-square w-full max-w-48 mx-auto lg:mx-0">
                <PartImage 
                  imageUrl={part.image_url}
                  partName={part.name}
                  size="xl"
                  showFallback={true}
                  className="w-full h-full object-contain bg-white"
                />
              </div>
            </div>
            
            {/* Basic Info Grid */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6 lg:col-span-3">
            <div className="flex items-start gap-3">
              <Hash className="w-5 h-5 text-muted mt-0.5" />
              <div>
                <p className="text-sm text-secondary">Part Number</p>
                {part.part_number ? (
                  <button
                    onClick={() => copyToClipboard(part.part_number!, 'part_number')}
                    className="font-semibold text-primary hover:bg-primary/10 rounded px-2 py-1 transition-colors flex items-center gap-2 group"
                    title="Click to copy part number"
                  >
                    {part.part_number}
                    {copiedPartNumber ? (
                      <Check className="w-4 h-4 text-green-500" />
                    ) : (
                      <Copy className="w-4 h-4 opacity-0 group-hover:opacity-100 transition-opacity" />
                    )}
                  </button>
                ) : (
                  <p className="font-semibold text-primary">Not set</p>
                )}
              </div>
            </div>
            
            <div className="flex items-start gap-3">
              <Box className="w-5 h-5 text-muted mt-0.5" />
              <div>
                <p className="text-sm text-secondary">Quantity</p>
                <p className={`font-semibold ${
                  part.minimum_quantity && part.quantity <= part.minimum_quantity
                    ? 'text-red-400'
                    : 'text-primary'
                }`}>
                  {part.quantity}
                  {part.minimum_quantity && (
                    <span className="text-xs text-muted ml-2">
                      (Min: {part.minimum_quantity})
                    </span>
                  )}
                </p>
              </div>
            </div>

            <div className="flex items-start gap-3">
              <MapPin className="w-5 h-5 text-muted mt-0.5" />
              <div>
                <p className="text-sm text-secondary">Location</p>
                <p className="font-semibold text-primary">
                  {part.location?.name || 'Not assigned'}
                </p>
              </div>
            </div>

            <div className="flex items-start gap-3">
              <Tag className="w-5 h-5 text-muted mt-0.5" />
              <div>
                <p className="text-sm text-secondary">Supplier</p>
                <div className="flex items-center gap-2">
                  <p className="font-semibold text-primary">{part.supplier || 'Not set'}</p>
                  {part.supplier_url && (
                    <a
                      href={part.supplier_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-primary hover:text-primary-dark"
                    >
                      <ExternalLink className="w-4 h-4" />
                    </a>
                  )}
                </div>
              </div>
            </div>

            <div className="flex items-start gap-3">
              <Calendar className="w-5 h-5 text-muted mt-0.5" />
              <div>
                <p className="text-sm text-secondary">Created</p>
                <p className="font-semibold text-primary">{formatDate(part.created_at)}</p>
              </div>
            </div>

            <div className="flex items-start gap-3">
              <Calendar className="w-5 h-5 text-muted mt-0.5" />
              <div>
                <p className="text-sm text-secondary">Last Updated</p>
                <p className="font-semibold text-primary">{formatDate(part.updated_at)}</p>
              </div>
            </div>
            </div>
          </div>
        </div>
      </motion.div>

      {/* Categories */}
      {part.categories && part.categories.length > 0 && (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
          className="card"
        >
          <div className="card-header">
            <h2 className="text-lg font-semibold text-primary">Categories</h2>
          </div>
          <div className="card-content">
            <div className="flex flex-wrap gap-2">
              {part.categories.map((category) => (
                <span
                  key={category.id}
                  className="px-3 py-1 bg-primary/10 text-primary rounded-full text-sm font-medium"
                >
                  {category.name}
                </span>
              ))}
            </div>
          </div>
        </motion.div>
      )}

      {/* Description */}
      {part.description && (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.25 }}
          className="card"
        >
          <div className="card-header">
            <h2 className="text-lg font-semibold text-primary">Description</h2>
          </div>
          <div className="card-content">
            <p className="text-secondary">{part.description}</p>
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
              {(() => {
                console.log('Datasheet debug:', {
                  datasheet_downloaded: part.additional_properties?.datasheet_downloaded,
                  datasheet_filename: part.additional_properties?.datasheet_filename,
                  additional_properties: part.additional_properties
                });
                return part.additional_properties?.datasheet_downloaded && part.additional_properties?.datasheet_filename;
              })() && (
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

      {/* Enhanced Properties Display - Always show if part has properties OR show debugging */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.35 }}
        className="card"
      >
        <div className="card-header">
          <h2 className="text-lg font-semibold text-primary flex items-center gap-2">
            <Info className="w-5 h-5" />
            Properties & Technical Data
            {part.additional_properties && (
              <span className="text-sm bg-primary/10 text-primary px-2 py-1 rounded">
                {Object.keys(part.additional_properties).length} properties
              </span>
            )}
          </h2>
        </div>
        <div className="card-content">
          {part.additional_properties && Object.keys(part.additional_properties).length > 0 ? (
            <>
              {/* Quick Stats Summary */}
              <div className="mb-6 p-4 bg-background-secondary/20 rounded-lg border border-border/30">
                <h3 className="text-sm font-semibold text-primary mb-3 flex items-center gap-2">
                  <Zap className="w-4 h-4" />
                  Quick Overview
                </h3>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                  <div>
                    <span className="text-secondary">Total Properties:</span>
                    <span className="ml-2 font-semibold text-primary">{Object.keys(part.additional_properties).length}</span>
                  </div>
                  {part.additional_properties.description && (
                    <div className="col-span-2 md:col-span-3">
                      <span className="text-secondary">Description:</span>
                      <span className="ml-2 text-primary">{String(part.additional_properties.description).substring(0, 100)}...</span>
                    </div>
                  )}
                </div>
              </div>
              
              <EnhancedPropertiesSection part={part} />
            </>
          ) : (
            <div className="text-center py-8">
              <Info className="w-12 h-12 text-muted mx-auto mb-4 opacity-50" />
              <h3 className="text-lg font-medium text-primary mb-2">No Additional Properties</h3>
              <p className="text-secondary">
                This part doesn't have enriched properties yet. Properties are added during CSV import with enrichment.
              </p>
            </div>
          )}
          
          {/* Debug info - remove in production */}
          <details className="mt-4 p-3 bg-background-secondary/30 dark:bg-black rounded border">
            <summary className="cursor-pointer text-sm font-medium text-secondary">
              Debug: Complete Part Model Data
            </summary>
            <pre className="mt-2 text-xs text-muted overflow-x-auto">
              {JSON.stringify(part, null, 2)}
            </pre>
          </details>
        </div>
      </motion.div>

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
          part_name: part.name,
          part_number: part.part_number || '',
          location: part.location?.name || '',
          category: part.categories?.[0]?.name || '',
          quantity: part.quantity?.toString() || '0',
          description: part.description || '',
          additional_properties: part.additional_properties || {}
        }}
      />

      {/* PDF Preview Modal for Supplier Datasheets */}
      {pdfPreviewOpen && pdfPreviewUrl && (
        <PDFViewer
          fileUrl={pdfPreviewUrl}
          fileName={`${part?.name || 'Part'} - Datasheet.pdf`}
          onClose={() => setPdfPreviewOpen(false)}
        />
      )}
    </div>
  )
}

// Enhanced Properties Section Component
const EnhancedPropertiesSection = ({ part }: { part: Part }) => {
  const [activeTab, setActiveTab] = useState('technical')

  const organizeProperties = (properties: Record<string, any>) => {
    const organized = {
      technical: {} as Record<string, any>,
      component: {} as Record<string, any>,
      supplier: {} as Record<string, any>,
      enrichment: {} as Record<string, any>,
      import: {} as Record<string, any>,
      other: {} as Record<string, any>
    }

    Object.entries(properties).forEach(([key, value]) => {
      const lowerKey = key.toLowerCase()
      
      // Component-specific data (check first to prioritize component categorization)
      if (lowerKey.includes('component_') || key.startsWith('component_') ||
          lowerKey.includes('package') || lowerKey.includes('footprint') || 
          lowerKey.includes('mounting') || lowerKey.includes('form_factor') ||
          lowerKey.includes('resistor_') || lowerKey.includes('capacitor_') || 
          lowerKey.includes('inductor_') || lowerKey.includes('diode_') || 
          lowerKey.includes('ic_') || lowerKey.includes('series') ||
          (lowerKey.includes('type') && !lowerKey.includes('import') && !lowerKey.includes('file')) ||
          (lowerKey.includes('value') && !lowerKey.includes('total') && !lowerKey.includes('inventory'))) {
        organized.component[key] = value
      }
      // Technical specifications (from EasyEDA API enrichment)
      else if (key.startsWith('spec_') || 
          lowerKey.includes('voltage') || lowerKey.includes('capacitance') || 
          lowerKey.includes('resistance') || lowerKey.includes('tolerance') || 
          lowerKey.includes('temperature') || lowerKey.includes('rating') ||
          lowerKey.includes('frequency') || lowerKey.includes('power') ||
          lowerKey.includes('current') || lowerKey.includes('impedance')) {
        organized.technical[key] = value
      }
      // Supplier and pricing information
      else if (lowerKey.includes('supplier') || lowerKey.includes('price') || 
               lowerKey.includes('currency') || lowerKey.includes('order') || 
               lowerKey.includes('lcsc') || lowerKey.includes('digikey') ||
               lowerKey.includes('mouser') || lowerKey.includes('manufacturer') ||
               lowerKey.includes('part_number') || lowerKey.includes('datasheet')) {
        organized.supplier[key] = value
      }
      // Enrichment and API data
      else if (lowerKey.includes('enriched') || lowerKey.includes('enrichment') || 
               lowerKey.includes('easyeda') || lowerKey.includes('api') ||
               lowerKey.includes('extracted') || lowerKey.includes('parsed')) {
        organized.enrichment[key] = value
      }
      // Import source and metadata
      else if (lowerKey.includes('import') || lowerKey.includes('source') ||
               lowerKey.includes('row') || lowerKey.includes('csv') ||
               lowerKey.includes('batch') || lowerKey.includes('timestamp')) {
        organized.import[key] = value
      }
      // Everything else
      else {
        organized.other[key] = value
      }
    })

    return organized
  }

  const organizedProps = organizeProperties(part.additional_properties || {})

  const formatKey = (key: string) => {
    return key
      .replace(/^spec_/, '')
      .replace(/^(resistor_|capacitor_|inductor_|diode_|ic_)/, '')
      .replace(/_/g, ' ')
      .replace(/\b\w/g, l => l.toUpperCase())
  }

  const formatValue = (value: any, key: string) => {
    if (typeof value === 'object') {
      // Special handling for specifications object
      if (key.toLowerCase() === 'specifications' && value && typeof value === 'object') {
        return (
          <div className="space-y-2">
            <div className="text-sm font-medium text-primary">Technical Specifications</div>
            <div className="bg-background-secondary rounded-lg p-3">
              <div className="grid grid-cols-1 gap-2">
                {Object.entries(value).map(([specKey, specValue]) => (
                  <div key={specKey} className="flex justify-between py-1 border-b border-border last:border-b-0">
                    <span className="text-sm font-medium text-secondary">{specKey}:</span>
                    <span className="text-sm text-primary">{String(specValue)}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )
      }
      
      // Special handling for standardized pricing data
      if (key.toLowerCase() === 'pricing_data' && value && typeof value === 'object') {
        const pricingType = value.pricing_type
        const currency = value.currency || 'USD'
        
        return (
          <div className="space-y-2">
            <div className="text-sm font-medium text-primary flex items-center gap-2">
              <DollarSign className="w-4 h-4" />
              Pricing Information
            </div>
            <div className="bg-background-secondary rounded-lg p-3">
              {pricingType === 'no_pricing' && (
                <div className="text-sm text-secondary text-center py-2">
                  No pricing information available
                </div>
              )}
              
              {pricingType === 'single_price' && value.unit_price && (
                <div className="text-center">
                  <div className="text-lg font-semibold text-primary">
                    ${Number(value.unit_price).toFixed(2)} {currency}
                  </div>
                  <div className="text-xs text-secondary">Per unit</div>
                </div>
              )}
              
              {pricingType === 'quantity_breaks' && value.price_breaks && (
                <div className="space-y-2">
                  <div className="text-xs text-secondary mb-2">Quantity pricing tiers:</div>
                  {value.price_breaks.map((priceBreak: any, index: number) => (
                    <div key={index} className="flex justify-between py-1 border-b border-border last:border-b-0">
                      <span className="text-sm text-secondary">
                        {priceBreak.quantity === 1 ? '1+' : `${priceBreak.quantity.toLocaleString()}+`}:
                      </span>
                      <span className="text-sm font-medium text-primary">
                        ${Number(priceBreak.price).toFixed(2)} {currency}
                      </span>
                    </div>
                  ))}
                  {value.unit_price && (
                    <div className="mt-2 pt-2 border-t border-border">
                      <div className="text-xs text-secondary">Best unit price: ${Number(value.unit_price).toFixed(2)} {currency}</div>
                    </div>
                  )}
                </div>
              )}
              
              {value.supplier && (
                <div className="mt-2 pt-2 border-t border-border text-xs text-secondary">
                  Source: {value.supplier}
                  {value.last_updated && (
                    <span className="ml-2">• Updated: {new Date(value.last_updated).toLocaleDateString()}</span>
                  )}
                </div>
              )}
            </div>
          </div>
        )
      }
      
      // Legacy handling for pricing data array (for backward compatibility)
      if (key.toLowerCase().includes('pricing') && Array.isArray(value)) {
        return (
          <div className="space-y-2">
            <div className="text-sm font-medium text-primary">Legacy Pricing Information</div>
            <div className="bg-background-secondary rounded-lg p-3">
              <div className="grid grid-cols-1 gap-2">
                {value.map((priceInfo, index) => (
                  <div key={index} className="flex justify-between py-1 border-b border-border last:border-b-0">
                    <span className="text-sm text-secondary">
                      {priceInfo.quantity === 1 ? '1 piece' : `${priceInfo.quantity.toLocaleString()} pieces`}:
                    </span>
                    <span className="text-sm font-medium text-primary">
                      ${priceInfo.price} {priceInfo.currency}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )
      }
      
      // Generic object display for other objects
      return (
        <details className="group">
          <summary className="cursor-pointer text-primary hover:text-primary-dark">
            View object data
          </summary>
          <pre className="mt-1 text-xs bg-background-secondary p-2 rounded">
            {JSON.stringify(value, null, 2)}
          </pre>
        </details>
      )
    }
    
    const stringValue = String(value)
    
    // Format URLs as clickable links
    if (stringValue.startsWith('http') || stringValue.startsWith('https')) {
      return (
        <a 
          href={stringValue} 
          target="_blank" 
          rel="noopener noreferrer"
          className="text-primary hover:text-primary-dark flex items-center gap-1 group"
        >
          <span className="truncate max-w-xs group-hover:max-w-none">{stringValue}</span>
          <ExternalLink className="w-3 h-3 flex-shrink-0" />
        </a>
      )
    }
    
    // Format numbers with units if applicable
    if (key.toLowerCase().includes('price') && !isNaN(Number(stringValue))) {
      return `$${Number(stringValue).toFixed(2)}`
    }
    
    // Add units for common electrical properties
    const lowerKey = key.toLowerCase()
    if (!isNaN(Number(stringValue)) && stringValue !== '') {
      if (lowerKey.includes('voltage') || lowerKey.includes('volt')) {
        return `${stringValue}V`
      }
      if (lowerKey.includes('current') || lowerKey.includes('amp')) {
        return `${stringValue}A`
      }
      if (lowerKey.includes('resistance') || lowerKey.includes('ohm')) {
        return `${stringValue}Ω`
      }
      if (lowerKey.includes('capacitance') || lowerKey.includes('farad')) {
        return `${stringValue}F`
      }
      if (lowerKey.includes('frequency') || lowerKey.includes('hertz')) {
        return `${stringValue}Hz`
      }
      if (lowerKey.includes('power') || lowerKey.includes('watt')) {
        return `${stringValue}W`
      }
      if (lowerKey.includes('temperature') && !lowerKey.includes('coefficient')) {
        return `${stringValue}°C`
      }
      if (lowerKey.includes('tolerance') || lowerKey.includes('percent')) {
        return `${stringValue}%`
      }
    }
    
    return stringValue
  }

  const renderPropertyGrid = (properties: Record<string, any>) => (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
      {Object.entries(properties).map(([key, value]) => (
        <div key={key} className="border border-border/50 rounded-lg p-3 bg-background-secondary/30 hover:bg-background-secondary/50 transition-colors">
          <p className="text-xs text-gray-700 dark:text-gray-300 font-medium mb-1 uppercase tracking-wide">
            {formatKey(key)}
          </p>
          <div className="font-medium text-primary text-sm break-words">
            {formatValue(value, key)}
          </div>
          {/* Show raw key for debugging */}
          <p className="text-xs text-gray-600 dark:text-gray-400 mt-1 font-mono">
            {key}
          </p>
        </div>
      ))}
    </div>
  )

  const tabs = [
    { 
      id: 'technical', 
      label: 'Technical Specs', 
      icon: Zap, 
      count: Object.keys(organizedProps.technical).length,
      description: 'Electrical and physical specifications'
    },
    { 
      id: 'component', 
      label: 'Component Data', 
      icon: Settings, 
      count: Object.keys(organizedProps.component).length,
      description: 'Package, footprint, and component-specific data'
    },
    { 
      id: 'supplier', 
      label: 'Supplier Info', 
      icon: Globe, 
      count: Object.keys(organizedProps.supplier).length,
      description: 'Supplier details, pricing, and part numbers'
    },
    { 
      id: 'enrichment', 
      label: 'Enrichment Data', 
      icon: BookOpen, 
      count: Object.keys(organizedProps.enrichment).length,
      description: 'API-sourced and parsed information'
    },
    { 
      id: 'import', 
      label: 'Import Info', 
      icon: Clock, 
      count: Object.keys(organizedProps.import).length,
      description: 'Import source and metadata'
    },
    { 
      id: 'other', 
      label: 'Other Properties', 
      icon: Info, 
      count: Object.keys(organizedProps.other).length,
      description: 'Additional uncategorized properties'
    }
  ].filter(tab => tab.count > 0)

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: 0.3 }}
      className="card"
    >
      <div className="card-header">
        <h2 className="text-lg font-semibold text-primary flex items-center gap-2">
          <Info className="w-5 h-5" />
          Part Properties & Specifications
        </h2>
      </div>
      
      <div className="card-content">
        {/* Tabs */}
        <div className="flex flex-wrap gap-1 mb-6 border-b border-border">
          {tabs.map((tab) => {
            const Icon = tab.icon
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`flex items-center gap-2 px-4 py-2 rounded-t-lg border-b-2 transition-colors ${
                  activeTab === tab.id
                    ? 'bg-primary/10 text-primary border-primary'
                    : 'text-gray-700 dark:text-gray-300 hover:text-primary border-transparent hover:bg-background-secondary/50'
                }`}
              >
                <Icon className="w-4 h-4" />
                {tab.label}
                <span className="px-2 py-0.5 bg-background-secondary rounded-full text-xs">
                  {tab.count}
                </span>
              </button>
            )
          })}
        </div>

        {/* Tab Content */}
        <div className="min-h-32">
          {activeTab === 'technical' && organizedProps.technical && Object.keys(organizedProps.technical).length > 0 && (
            <div>
              <div className="flex items-center gap-2 mb-4">
                <Zap className="w-4 h-4 text-primary" />
                <h3 className="font-medium text-primary">Technical Specifications</h3>
              </div>
              {renderPropertyGrid(organizedProps.technical)}
            </div>
          )}

          {activeTab === 'component' && organizedProps.component && Object.keys(organizedProps.component).length > 0 && (
            <div>
              <div className="flex items-center gap-2 mb-4">
                <Settings className="w-4 h-4 text-primary" />
                <h3 className="font-medium text-primary">Component-Specific Data</h3>
              </div>
              {renderPropertyGrid(organizedProps.component)}
            </div>
          )}

          {activeTab === 'supplier' && organizedProps.supplier && Object.keys(organizedProps.supplier).length > 0 && (
            <div>
              <div className="flex items-center gap-2 mb-4">
                <Globe className="w-4 h-4 text-primary" />
                <h3 className="font-medium text-primary">Supplier Information</h3>
              </div>
              {renderPropertyGrid(organizedProps.supplier)}
            </div>
          )}

          {activeTab === 'enrichment' && organizedProps.enrichment && Object.keys(organizedProps.enrichment).length > 0 && (
            <div>
              <div className="flex items-center gap-2 mb-4">
                <BookOpen className="w-4 h-4 text-primary" />
                <h3 className="font-medium text-primary">Data Enrichment Information</h3>
              </div>
              {renderPropertyGrid(organizedProps.enrichment)}
            </div>
          )}

          {activeTab === 'import' && organizedProps.import && Object.keys(organizedProps.import).length > 0 && (
            <div>
              <div className="flex items-center gap-2 mb-4">
                <Clock className="w-4 h-4 text-primary" />
                <h3 className="font-medium text-primary">Import Information</h3>
              </div>
              {renderPropertyGrid(organizedProps.import)}
            </div>
          )}

          {activeTab === 'other' && organizedProps.other && Object.keys(organizedProps.other).length > 0 && (
            <div>
              <div className="flex items-center gap-2 mb-4">
                <Info className="w-4 h-4 text-primary" />
                <h3 className="font-medium text-primary">Other Properties</h3>
              </div>
              {renderPropertyGrid(organizedProps.other)}
            </div>
          )}

          {/* Show message if no properties in selected tab */}
          {tabs.find(tab => tab.id === activeTab)?.count === 0 && (
            <div className="text-center py-8 text-muted">
              <Info className="w-8 h-8 mx-auto mb-2 opacity-50" />
              <p>No properties available in this category</p>
              <p className="text-sm mt-1">{tabs.find(tab => tab.id === activeTab)?.description}</p>
            </div>
          )}
        </div>
      </div>
    </motion.div>
  )
}

export default PartDetailsPage