import { useState, useEffect } from 'react'
import {
  Wrench,
  Edit3,
  Trash2,
  MapPin,
  Calendar,
  DollarSign,
  User,
  Package,
  CheckCircle,
  XCircle,
  ExternalLink,
  Tag,
  Settings,
  AlertCircle,
  Clock,
  FileText,
  Plus,
} from 'lucide-react'
import Modal from '@/components/ui/Modal'
import PartImage from '@/components/parts/PartImage'
import TagBadge from '@/components/tags/TagBadge'
import { toolsService } from '@/services/tools.service'
import { useAuthStore } from '@/store/authStore'
import type { Tool } from '@/types/tools'
import type { Tag } from '@/types/tags'
import toast from 'react-hot-toast'

interface ToolDetailModalProps {
  isOpen: boolean
  onClose: () => void
  toolId: string
  onEdit?: (tool: Tool) => void
  onDelete?: (toolId: string) => void
  onStatusChange?: () => void
}

const ToolDetailModal = ({ isOpen, onClose, toolId, onEdit, onDelete, onStatusChange }: ToolDetailModalProps) => {
  const [tool, setTool] = useState<Tool | null>(null)
  const [loading, setLoading] = useState(true)
  const [checkoutNotes, setCheckoutNotes] = useState('')
  const [checkinNotes, setCheckinNotes] = useState('')
  const [isCheckoutMode, setIsCheckoutMode] = useState(false)
  const [isCheckinMode, setIsCheckinMode] = useState(false)
  const [processingCheckout, setProcessingCheckout] = useState(false)

  // Maintenance record state
  const [maintenanceRecords, setMaintenanceRecords] = useState<any[]>([])
  const [showAddMaintenance, setShowAddMaintenance] = useState(false)
  const [maintenanceForm, setMaintenanceForm] = useState({
    maintenance_date: new Date().toISOString().split('T')[0],
    maintenance_type: 'inspection',
    notes: '',
    next_maintenance_date: '',
    cost: '',
  })
  const [processingMaintenance, setProcessingMaintenance] = useState(false)

  const { user } = useAuthStore()

  useEffect(() => {
    if (isOpen && toolId) {
      loadTool()
      loadMaintenanceRecords()
    }
  }, [isOpen, toolId])

  const loadTool = async () => {
    try {
      setLoading(true)
      const data = await toolsService.getTool(toolId)
      setTool(data)
    } catch (error: any) {
      console.error('Failed to load tool:', error)
      toast.error('Failed to load tool details')
    } finally {
      setLoading(false)
    }
  }

  const loadMaintenanceRecords = async () => {
    try {
      const records = await toolsService.getMaintenanceRecords(toolId)
      setMaintenanceRecords(records)
    } catch (error: any) {
      console.error('Failed to load maintenance records:', error)
    }
  }

  const handleAddMaintenance = async () => {
    if (!maintenanceForm.maintenance_date || !maintenanceForm.maintenance_type) {
      toast.error('Please fill in required fields')
      return
    }

    try {
      setProcessingMaintenance(true)
      await toolsService.createMaintenanceRecord(toolId, {
        maintenance_date: maintenanceForm.maintenance_date,
        maintenance_type: maintenanceForm.maintenance_type,
        notes: maintenanceForm.notes || undefined,
        next_maintenance_date: maintenanceForm.next_maintenance_date || undefined,
        cost: maintenanceForm.cost ? parseFloat(maintenanceForm.cost) : undefined,
      })

      toast.success('Maintenance record added successfully')
      setShowAddMaintenance(false)
      setMaintenanceForm({
        maintenance_date: new Date().toISOString().split('T')[0],
        maintenance_type: 'inspection',
        notes: '',
        next_maintenance_date: '',
        cost: '',
      })
      await loadMaintenanceRecords()
      await loadTool() // Reload tool to update maintenance dates
    } catch (error: any) {
      console.error('Failed to add maintenance record:', error)
      toast.error(error.message || 'Failed to add maintenance record')
    } finally {
      setProcessingMaintenance(false)
    }
  }

  const handleDeleteMaintenance = async (recordId: string) => {
    if (!window.confirm('Are you sure you want to delete this maintenance record?')) {
      return
    }

    try {
      await toolsService.deleteMaintenanceRecord(toolId, recordId)
      toast.success('Maintenance record deleted successfully')
      await loadMaintenanceRecords()
      await loadTool()
    } catch (error: any) {
      console.error('Failed to delete maintenance record:', error)
      toast.error(error.message || 'Failed to delete maintenance record')
    }
  }

  const handleCheckout = async () => {
    if (!tool || !user) return

    try {
      setProcessingCheckout(true)
      const updatedTool = await toolsService.checkoutTool(tool.id, user.username, checkoutNotes)
      setTool(updatedTool)
      setCheckoutNotes('')
      setIsCheckoutMode(false)
      toast.success('Tool checked out successfully')
      if (onStatusChange) {
        onStatusChange()
      }
    } catch (error: any) {
      console.error('Failed to checkout tool:', error)
      toast.error(error.message || 'Failed to checkout tool')
    } finally {
      setProcessingCheckout(false)
    }
  }

  const handleCheckin = async () => {
    if (!tool) return

    try {
      setProcessingCheckout(true)
      const updatedTool = await toolsService.checkinTool(tool.id, checkinNotes)
      setTool(updatedTool)
      setCheckinNotes('')
      setIsCheckinMode(false)
      toast.success('Tool checked in successfully')
      if (onStatusChange) {
        onStatusChange()
      }
    } catch (error: any) {
      console.error('Failed to checkin tool:', error)
      toast.error(error.message || 'Failed to checkin tool')
    } finally {
      setProcessingCheckout(false)
    }
  }

  const formatDate = (dateString?: string) => {
    if (!dateString) return '-'
    return new Date(dateString).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
    })
  }

  const formatCurrency = (amount?: number) => {
    if (amount === undefined) return '-'
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
    }).format(amount)
  }

  const getConditionColor = (condition: string) => {
    switch (condition) {
      case 'excellent':
        return 'text-green-600 dark:text-green-400 bg-green-50 dark:bg-green-900/20'
      case 'good':
        return 'text-blue-600 dark:text-blue-400 bg-blue-50 dark:bg-blue-900/20'
      case 'fair':
        return 'text-yellow-600 dark:text-yellow-400 bg-yellow-50 dark:bg-yellow-900/20'
      case 'poor':
        return 'text-orange-600 dark:text-orange-400 bg-orange-50 dark:bg-orange-900/20'
      case 'needs_repair':
        return 'text-red-600 dark:text-red-400 bg-red-50 dark:bg-red-900/20'
      case 'out_of_service':
        return 'text-gray-600 dark:text-gray-400 bg-gray-50 dark:bg-gray-900/20'
      default:
        return 'text-gray-600 dark:text-gray-400 bg-gray-50 dark:bg-gray-900/20'
    }
  }

  if (!tool && !loading) {
    return null
  }

  return (
    <Modal isOpen={isOpen} onClose={onClose} title="Tool Details" size="xl">
      {loading ? (
        <div className="text-center py-8">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary mx-auto"></div>
          <p className="text-theme-secondary mt-2">Loading tool details...</p>
        </div>
      ) : tool ? (
        <div className="space-y-4">
          {/* Header Section */}
          <div className="p-4 bg-theme-secondary rounded-lg border border-theme-primary">
            <div className="flex items-start justify-between gap-4">
              <div className="flex items-start gap-4 flex-1">
                <div className="p-3 bg-theme-elevated rounded-lg border border-theme-primary">
                  <Wrench className="w-8 h-8 text-primary" />
                </div>
                <div className="flex-1 min-w-0">
                  <h2 className="text-2xl font-bold text-theme-primary mb-1">{tool.tool_name}</h2>
                  {tool.tool_number && (
                    <p className="text-sm text-theme-muted">Tool #{tool.tool_number}</p>
                  )}
                  {(tool.manufacturer || tool.model_number) && (
                    <p className="text-sm text-theme-secondary mt-1">
                      {tool.manufacturer && tool.model_number
                        ? `${tool.manufacturer} - ${tool.model_number}`
                        : tool.manufacturer || tool.model_number}
                    </p>
                  )}
                </div>
              </div>

              {/* Status Badge - Only show for checkable tools */}
              <div className="flex flex-col items-end gap-2">
                {tool.is_checkable && (
                  <div className={`flex items-center gap-2 px-3 py-1.5 rounded-full ${tool.is_checked_out ? 'bg-red-50 dark:bg-red-900/20' : 'bg-green-50 dark:bg-green-900/20'}`}>
                    {tool.is_checked_out ? (
                      <>
                        <XCircle className="w-4 h-4 text-red-600 dark:text-red-400" />
                        <span className="text-sm font-medium text-red-600 dark:text-red-400">Checked Out</span>
                      </>
                    ) : (
                      <>
                        <CheckCircle className="w-4 h-4 text-green-600 dark:text-green-400" />
                        <span className="text-sm font-medium text-green-600 dark:text-green-400">Available</span>
                      </>
                    )}
                  </div>
                )}
                {/* Condition Badge */}
                <div className={`px-3 py-1 rounded-full text-xs font-medium capitalize ${getConditionColor(tool.condition)}`}>
                  {tool.condition.replace(/_/g, ' ')}
                </div>
              </div>
            </div>
          </div>

          {/* Image and Information Grid */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {/* Tool Image */}
            {tool.image_url && (
              <div className="aspect-square w-full">
                <div className="w-full h-full bg-theme-secondary border-2 border-theme-primary rounded-xl p-4 shadow-inner">
                  <PartImage
                    imageUrl={tool.image_url}
                    partName={tool.tool_name}
                    size="xl"
                    showFallback={true}
                    className="w-full h-full object-contain"
                  />
                </div>
              </div>
            )}

            {/* Basic Information */}
            <div className="p-4 bg-theme-secondary rounded-lg border border-theme-primary space-y-3">
              <h3 className="text-sm font-semibold text-theme-primary uppercase tracking-wider flex items-center gap-2">
                <Settings className="w-4 h-4" />
                Basic Information
              </h3>

              {tool.product_url && (
                <div>
                  <p className="text-xs text-theme-muted mb-1">Product URL</p>
                  <a
                    href={tool.product_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-sm font-medium text-blue-500 hover:text-blue-600 dark:text-blue-400 dark:hover:text-blue-300 flex items-center gap-1 hover:underline break-all"
                  >
                    <ExternalLink className="w-3 h-3 flex-shrink-0" />
                    <span className="truncate">{tool.product_url}</span>
                  </a>
                </div>
              )}

              <div>
                <p className="text-xs text-theme-muted mb-1">Checkout Status</p>
                <div className="flex items-center gap-2">
                  {tool.is_checkable ? (
                    <>
                      <CheckCircle className="w-4 h-4 text-green-600 dark:text-green-400" />
                      <span className="text-sm font-medium text-green-600 dark:text-green-400">Can be checked out</span>
                    </>
                  ) : (
                    <>
                      <XCircle className="w-4 h-4 text-gray-600 dark:text-gray-400" />
                      <span className="text-sm font-medium text-gray-600 dark:text-gray-400">Not available for checkout</span>
                    </>
                  )}
                </div>
              </div>

              {tool.location && (
                <div>
                  <p className="text-xs text-theme-muted mb-1">Location</p>
                  <div className="flex items-center gap-2 text-sm font-medium text-theme-primary">
                    <MapPin className="w-4 h-4" />
                    {tool.location.name}
                  </div>
                </div>
              )}

              {tool.categories && tool.categories.length > 0 && (
                <div>
                  <p className="text-xs text-theme-muted mb-1">Categories</p>
                  <div className="flex flex-wrap gap-2">
                    {tool.categories.map((category) => (
                      <span
                        key={category.id}
                        className="inline-flex items-center gap-1 px-2 py-1 bg-theme-elevated border border-theme-primary text-theme-primary text-xs rounded-md"
                      >
                        <Tag className="w-3 h-3" />
                        {category.name}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {(tool as any).tags && (tool as any).tags.length > 0 && (
                <div>
                  <p className="text-xs text-theme-muted mb-1">Tags</p>
                  <div className="flex flex-wrap gap-2">
                    {(tool as any).tags.map((tag: Tag) => (
                      <TagBadge
                        key={tag.id}
                        tag={tag}
                        size="sm"
                      />
                    ))}
                  </div>
                </div>
              )}
            </div>

            {/* Purchase & Maintenance Information */}
            <div className="p-4 bg-theme-secondary rounded-lg border border-theme-primary space-y-3">
              <h3 className="text-sm font-semibold text-theme-primary uppercase tracking-wider flex items-center gap-2">
                <DollarSign className="w-4 h-4" />
                Purchase & Maintenance
              </h3>

              {tool.purchase_date && (
                <div>
                  <p className="text-xs text-theme-muted mb-1">Purchase Date</p>
                  <div className="flex items-center gap-2 text-sm font-medium text-theme-primary">
                    <Calendar className="w-4 h-4" />
                    {formatDate(tool.purchase_date)}
                  </div>
                </div>
              )}

              {tool.purchase_price !== undefined && (
                <div>
                  <p className="text-xs text-theme-muted mb-1">Purchase Price</p>
                  <div className="flex items-center gap-2 text-sm font-medium text-theme-primary">
                    <DollarSign className="w-4 h-4" />
                    {formatCurrency(tool.purchase_price)}
                  </div>
                </div>
              )}

              {tool.last_maintenance_date && (
                <div>
                  <p className="text-xs text-theme-muted mb-1">Last Maintenance</p>
                  <div className="flex items-center gap-2 text-sm font-medium text-theme-primary">
                    <Clock className="w-4 h-4" />
                    {formatDate(tool.last_maintenance_date)}
                  </div>
                </div>
              )}

              {tool.next_maintenance_date && (
                <div>
                  <p className="text-xs text-theme-muted mb-1">Next Maintenance</p>
                  <div className="flex items-center gap-2 text-sm font-medium text-orange-500">
                    <AlertCircle className="w-4 h-4" />
                    {formatDate(tool.next_maintenance_date)}
                  </div>
                </div>
              )}

              {tool.maintenance_notes && (
                <div>
                  <p className="text-xs text-theme-muted mb-1">Maintenance Notes</p>
                  <p className="text-sm text-theme-secondary">{tool.maintenance_notes}</p>
                </div>
              )}
            </div>
          </div>

          {/* Checkout/Checkin Actions */}
          {tool.is_checkable && !tool.is_checked_out && !isCheckoutMode && (
            <div className="p-4 bg-green-50 dark:bg-green-900/20 rounded-lg border border-green-200 dark:border-green-800">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <CheckCircle className="w-5 h-5 text-green-600 dark:text-green-400" />
                  <span className="font-medium text-green-900 dark:text-green-100">
                    Tool is available for checkout
                  </span>
                </div>
                <button
                  onClick={() => setIsCheckoutMode(true)}
                  className="btn btn-primary btn-sm"
                >
                  Checkout Tool
                </button>
              </div>
            </div>
          )}

          {tool.is_checkable && tool.is_checked_out && tool.checked_out_by === user?.username && !isCheckinMode && (
            <div className="p-4 bg-yellow-50 dark:bg-yellow-900/20 rounded-lg border border-yellow-200 dark:border-yellow-800">
              <div className="flex items-center justify-between gap-4">
                <div className="flex-1">
                  <div className="flex items-center gap-3 mb-1">
                    <User className="w-5 h-5 text-yellow-600 dark:text-yellow-400" />
                    <span className="font-medium text-yellow-900 dark:text-yellow-100">
                      You have this tool checked out
                    </span>
                  </div>
                  {tool.checked_out_at && (
                    <p className="text-sm text-yellow-700 dark:text-yellow-300 ml-8">
                      Since {formatDate(tool.checked_out_at)}
                    </p>
                  )}
                </div>
                <button
                  onClick={() => setIsCheckinMode(true)}
                  className="btn btn-primary btn-sm"
                >
                  Check In Tool
                </button>
              </div>
            </div>
          )}

          {tool.is_checkable && tool.is_checked_out && tool.checked_out_by !== user?.username && (
            <div className="p-4 bg-red-50 dark:bg-red-900/20 rounded-lg border border-red-200 dark:border-red-800">
              <div className="flex items-center gap-3">
                <AlertCircle className="w-5 h-5 text-red-600 dark:text-red-400" />
                <div>
                  <p className="font-medium text-red-900 dark:text-red-100">
                    Checked out by: {tool.checked_out_by}
                  </p>
                  {tool.checked_out_at && (
                    <p className="text-sm text-red-700 dark:text-red-300">
                      Since {formatDate(tool.checked_out_at)}
                    </p>
                  )}
                  {tool.expected_return_date && (
                    <p className="text-sm text-red-700 dark:text-red-300">
                      Expected return: {formatDate(tool.expected_return_date)}
                    </p>
                  )}
                </div>
              </div>
            </div>
          )}

          {/* Checkout Form */}
          {tool.is_checkable && isCheckoutMode && (
            <div className="p-4 bg-blue-50 dark:bg-blue-900/20 rounded-lg border border-blue-200 dark:border-blue-800 space-y-3">
              <h3 className="font-medium text-blue-900 dark:text-blue-100 flex items-center gap-2">
                <Package className="w-4 h-4" />
                Checkout Tool
              </h3>
              <textarea
                className="input w-full"
                placeholder="Add checkout notes (optional)"
                rows={3}
                value={checkoutNotes}
                onChange={(e) => setCheckoutNotes(e.target.value)}
              />
              <div className="flex justify-end gap-2">
                <button
                  onClick={() => {
                    setIsCheckoutMode(false)
                    setCheckoutNotes('')
                  }}
                  className="btn btn-secondary btn-sm"
                  disabled={processingCheckout}
                >
                  Cancel
                </button>
                <button
                  onClick={handleCheckout}
                  className="btn btn-primary btn-sm"
                  disabled={processingCheckout}
                >
                  {processingCheckout ? 'Processing...' : 'Confirm Checkout'}
                </button>
              </div>
            </div>
          )}

          {/* Checkin Form */}
          {tool.is_checkable && isCheckinMode && (
            <div className="p-4 bg-blue-50 dark:bg-blue-900/20 rounded-lg border border-blue-200 dark:border-blue-800 space-y-3">
              <h3 className="font-medium text-blue-900 dark:text-blue-100 flex items-center gap-2">
                <Package className="w-4 h-4" />
                Check In Tool
              </h3>
              <textarea
                className="input w-full"
                placeholder="Add checkin notes (optional)"
                rows={3}
                value={checkinNotes}
                onChange={(e) => setCheckinNotes(e.target.value)}
              />
              <div className="flex justify-end gap-2">
                <button
                  onClick={() => {
                    setIsCheckinMode(false)
                    setCheckinNotes('')
                  }}
                  className="btn btn-secondary btn-sm"
                  disabled={processingCheckout}
                >
                  Cancel
                </button>
                <button
                  onClick={handleCheckin}
                  className="btn btn-primary btn-sm"
                  disabled={processingCheckout}
                >
                  {processingCheckout ? 'Processing...' : 'Confirm Check In'}
                </button>
              </div>
            </div>
          )}

          {/* Description */}
          {tool.description && (
            <div className="p-4 bg-theme-secondary rounded-lg border border-theme-primary">
              <h3 className="text-sm font-semibold text-theme-primary uppercase tracking-wider mb-2 flex items-center gap-2">
                <FileText className="w-4 h-4" />
                Description
              </h3>
              <p className="text-sm text-theme-secondary whitespace-pre-wrap">{tool.description}</p>
            </div>
          )}

          {/* Additional Properties */}
          {tool.additional_properties && Object.keys(tool.additional_properties).length > 0 && (
            <div className="p-4 bg-theme-secondary rounded-lg border border-theme-primary">
              <h3 className="text-sm font-semibold text-theme-primary uppercase tracking-wider mb-3 flex items-center gap-2">
                <Tag className="w-4 h-4" />
                Additional Properties
              </h3>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                {Object.entries(tool.additional_properties).map(([key, value]) => (
                  <div key={key} className="p-2 bg-theme-elevated rounded border border-theme-primary">
                    <p className="text-xs text-theme-muted mb-1">{key}</p>
                    <p className="text-sm font-medium text-theme-primary">{String(value)}</p>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Maintenance Records */}
          <div className="p-4 bg-theme-secondary rounded-lg border border-theme-primary">
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-sm font-semibold text-theme-primary uppercase tracking-wider flex items-center gap-2">
                <Settings className="w-4 h-4" />
                Maintenance Records ({maintenanceRecords.length})
              </h3>
              <button
                onClick={() => setShowAddMaintenance(!showAddMaintenance)}
                className="btn btn-primary btn-sm flex items-center gap-2"
              >
                <Plus className="w-4 h-4" />
                Add Maintenance
              </button>
            </div>

            {/* Add Maintenance Form */}
            {showAddMaintenance && (
              <div className="mb-4 p-4 bg-theme-elevated rounded-lg border border-theme-primary space-y-3">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  <div>
                    <label className="block text-xs text-theme-muted mb-1">Maintenance Date *</label>
                    <input
                      type="date"
                      className="input w-full"
                      value={maintenanceForm.maintenance_date}
                      onChange={(e) => setMaintenanceForm({ ...maintenanceForm, maintenance_date: e.target.value })}
                    />
                  </div>
                  <div>
                    <label className="block text-xs text-theme-muted mb-1">Maintenance Type *</label>
                    <select
                      className="input w-full"
                      value={maintenanceForm.maintenance_type}
                      onChange={(e) => setMaintenanceForm({ ...maintenanceForm, maintenance_type: e.target.value })}
                    >
                      <option value="inspection">Inspection</option>
                      <option value="calibration">Calibration</option>
                      <option value="repair">Repair</option>
                      <option value="cleaning">Cleaning</option>
                      <option value="other">Other</option>
                    </select>
                  </div>
                  <div>
                    <label className="block text-xs text-theme-muted mb-1">Next Maintenance Date</label>
                    <input
                      type="date"
                      className="input w-full"
                      value={maintenanceForm.next_maintenance_date}
                      onChange={(e) => setMaintenanceForm({ ...maintenanceForm, next_maintenance_date: e.target.value })}
                    />
                  </div>
                  <div>
                    <label className="block text-xs text-theme-muted mb-1">Cost ($)</label>
                    <input
                      type="number"
                      step="0.01"
                      className="input w-full"
                      value={maintenanceForm.cost}
                      onChange={(e) => setMaintenanceForm({ ...maintenanceForm, cost: e.target.value })}
                      placeholder="0.00"
                    />
                  </div>
                </div>
                <div>
                  <label className="block text-xs text-theme-muted mb-1">Notes</label>
                  <textarea
                    className="input w-full"
                    rows={3}
                    value={maintenanceForm.notes}
                    onChange={(e) => setMaintenanceForm({ ...maintenanceForm, notes: e.target.value })}
                    placeholder="Maintenance details and observations..."
                  />
                </div>
                <div className="flex justify-end gap-2">
                  <button
                    onClick={() => {
                      setShowAddMaintenance(false)
                      setMaintenanceForm({
                        maintenance_date: new Date().toISOString().split('T')[0],
                        maintenance_type: 'inspection',
                        notes: '',
                        next_maintenance_date: '',
                        cost: '',
                      })
                    }}
                    className="btn btn-secondary btn-sm"
                    disabled={processingMaintenance}
                  >
                    Cancel
                  </button>
                  <button
                    onClick={handleAddMaintenance}
                    className="btn btn-primary btn-sm"
                    disabled={processingMaintenance}
                  >
                    {processingMaintenance ? 'Adding...' : 'Add Record'}
                  </button>
                </div>
              </div>
            )}

            {/* Maintenance Records List */}
            {maintenanceRecords.length === 0 ? (
              <p className="text-sm text-theme-muted text-center py-4">No maintenance records yet</p>
            ) : (
              <div className="space-y-3">
                {maintenanceRecords.map((record) => (
                  <div key={record.id} className="p-3 bg-theme-elevated rounded-lg border border-theme-primary">
                    <div className="flex items-start justify-between gap-3">
                      <div className="flex-1">
                        <div className="flex items-center gap-2 mb-1">
                          <span className="text-sm font-semibold text-theme-primary capitalize">
                            {record.maintenance_type.replace(/_/g, ' ')}
                          </span>
                          <span className="text-xs text-theme-muted">
                            {formatDate(record.maintenance_date)}
                          </span>
                        </div>
                        {record.notes && (
                          <p className="text-sm text-theme-secondary mb-2">{record.notes}</p>
                        )}
                        <div className="flex flex-wrap gap-3 text-xs text-theme-muted">
                          <span className="flex items-center gap-1">
                            <User className="w-3 h-3" />
                            {record.performed_by}
                          </span>
                          {record.cost && (
                            <span className="flex items-center gap-1">
                              <DollarSign className="w-3 h-3" />
                              {formatCurrency(record.cost)}
                            </span>
                          )}
                          {record.next_maintenance_date && (
                            <span className="flex items-center gap-1">
                              <Clock className="w-3 h-3" />
                              Next: {formatDate(record.next_maintenance_date)}
                            </span>
                          )}
                        </div>
                      </div>
                      <button
                        onClick={() => handleDeleteMaintenance(record.id)}
                        className="text-red-600 hover:text-red-700 dark:text-red-400 dark:hover:text-red-300"
                        title="Delete maintenance record"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Actions */}
          <div className="flex justify-between pt-4 border-t border-border">
            <div className="flex gap-2">
              {onEdit && (
                <button
                  onClick={() => {
                    onEdit(tool)
                    onClose()
                  }}
                  className="btn btn-secondary flex items-center gap-2"
                >
                  <Edit3 className="w-4 h-4" />
                  Edit
                </button>
              )}
              {onDelete && (
                <button
                  onClick={() => {
                    if (window.confirm('Are you sure you want to delete this tool?')) {
                      onDelete(tool.id)
                      onClose()
                    }
                  }}
                  className="btn btn-danger flex items-center gap-2"
                >
                  <Trash2 className="w-4 h-4" />
                  Delete
                </button>
              )}
            </div>
            <button onClick={onClose} className="btn btn-primary">
              Close
            </button>
          </div>
        </div>
      ) : (
        <div className="text-center py-8">
          <p className="text-theme-secondary">Tool not found</p>
        </div>
      )}
    </Modal>
  )
}

export default ToolDetailModal
