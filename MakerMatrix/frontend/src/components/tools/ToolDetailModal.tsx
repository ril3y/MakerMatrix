import { useState, useEffect } from 'react'
import {
  Wrench,
  X,
  Edit3,
  Trash2,
  MapPin,
  Calendar,
  DollarSign,
  User,
  FileText,
  AlertCircle,
  Package,
  CheckCircle,
  XCircle,
} from 'lucide-react'
import Modal from '@/components/ui/Modal'
import { toolsService } from '@/services/tools.service'
import { useAuthStore } from '@/store/authStore'
import type { Tool } from '@/types/tools'
import toast from 'react-hot-toast'

interface ToolDetailModalProps {
  isOpen: boolean
  onClose: () => void
  toolId: string
  onEdit?: (tool: Tool) => void
  onDelete?: (toolId: string) => void
}

const ToolDetailModal = ({ isOpen, onClose, toolId, onEdit, onDelete }: ToolDetailModalProps) => {
  const [tool, setTool] = useState<Tool | null>(null)
  const [loading, setLoading] = useState(true)
  const [checkoutNotes, setCheckoutNotes] = useState('')
  const [checkinNotes, setCheckinNotes] = useState('')
  const [isCheckoutMode, setIsCheckoutMode] = useState(false)
  const [isCheckinMode, setIsCheckinMode] = useState(false)
  const [processingCheckout, setProcessingCheckout] = useState(false)
  const { user } = useAuthStore()

  useEffect(() => {
    if (isOpen && toolId) {
      loadTool()
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

  const handleCheckout = async () => {
    if (!tool || !user) return

    try {
      setProcessingCheckout(true)
      const updatedTool = await toolsService.checkoutTool(tool.id, user.username, checkoutNotes)
      setTool(updatedTool)
      setCheckoutNotes('')
      setIsCheckoutMode(false)
      toast.success('Tool checked out successfully')
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
      case 'new':
        return 'text-green-500'
      case 'good':
        return 'text-blue-500'
      case 'fair':
        return 'text-yellow-500'
      case 'poor':
        return 'text-orange-500'
      case 'broken':
        return 'text-red-500'
      default:
        return 'text-gray-500'
    }
  }

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'available':
        return <CheckCircle className="w-5 h-5 text-green-500" />
      case 'checked_out':
        return <XCircle className="w-5 h-5 text-red-500" />
      case 'maintenance':
        return <AlertCircle className="w-5 h-5 text-yellow-500" />
      case 'retired':
        return <Package className="w-5 h-5 text-gray-500" />
      default:
        return null
    }
  }

  if (!tool && !loading) {
    return null
  }

  return (
    <Modal isOpen={isOpen} onClose={onClose} title="Tool Details" size="lg">
      {loading ? (
        <div className="text-center py-8">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary mx-auto"></div>
          <p className="text-secondary mt-2">Loading tool details...</p>
        </div>
      ) : tool ? (
        <div className="space-y-6">
          {/* Header with status and actions */}
          <div className="flex items-center justify-between pb-4 border-b border-border">
            <div className="flex items-center gap-3">
              <Wrench className="w-8 h-8 text-primary" />
              <div>
                <h2 className="text-xl font-semibold text-primary">{tool.name}</h2>
                {tool.tool_number && (
                  <p className="text-sm text-muted">Tool #{tool.tool_number}</p>
                )}
              </div>
            </div>
            <div className="flex items-center gap-2">
              {getStatusIcon(tool.status)}
              <span className="text-sm font-medium capitalize">{tool.status.replace('_', ' ')}</span>
            </div>
          </div>

          {/* Tool Image */}
          {tool.image_url && (
            <div className="flex justify-center">
              <img
                src={tool.image_url}
                alt={tool.name}
                className="max-w-full max-h-64 rounded-lg object-contain"
              />
            </div>
          )}

          {/* Checkout/Checkin Section */}
          {tool.status === 'available' && !isCheckoutMode && (
            <div className="bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-lg p-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <CheckCircle className="w-5 h-5 text-green-600" />
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

          {tool.status === 'checked_out' && tool.checked_out_by === user?.username && !isCheckinMode && (
            <div className="bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-lg p-4">
              <div className="flex items-center justify-between">
                <div>
                  <div className="flex items-center gap-2">
                    <XCircle className="w-5 h-5 text-yellow-600" />
                    <span className="font-medium text-yellow-900 dark:text-yellow-100">
                      You have this tool checked out
                    </span>
                  </div>
                  {tool.checkout_date && (
                    <p className="text-sm text-yellow-700 dark:text-yellow-300 mt-1">
                      Since {formatDate(tool.checkout_date)}
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

          {tool.status === 'checked_out' && tool.checked_out_by !== user?.username && (
            <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-4">
              <div className="flex items-center gap-2">
                <User className="w-5 h-5 text-red-600" />
                <span className="font-medium text-red-900 dark:text-red-100">
                  Checked out by: {tool.checked_out_by}
                </span>
                {tool.checkout_date && (
                  <span className="text-sm text-red-700 dark:text-red-300">
                    (Since {formatDate(tool.checkout_date)})
                  </span>
                )}
              </div>
              {tool.expected_return_date && (
                <p className="text-sm text-red-700 dark:text-red-300 mt-1">
                  Expected return: {formatDate(tool.expected_return_date)}
                </p>
              )}
            </div>
          )}

          {/* Checkout Form */}
          {isCheckoutMode && (
            <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-4 space-y-3">
              <h3 className="font-medium text-blue-900 dark:text-blue-100">Checkout Tool</h3>
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
          {isCheckinMode && (
            <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-4 space-y-3">
              <h3 className="font-medium text-blue-900 dark:text-blue-100">Check In Tool</h3>
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

          {/* Tool Information Grid */}
          <div className="grid grid-cols-2 gap-4">
            {/* Basic Information */}
            <div className="space-y-3">
              <h3 className="text-sm font-semibold text-primary uppercase tracking-wider">
                Basic Information
              </h3>

              {tool.manufacturer && (
                <div>
                  <p className="text-xs text-muted">Manufacturer</p>
                  <p className="text-sm font-medium text-primary">{tool.manufacturer}</p>
                </div>
              )}

              {tool.model && (
                <div>
                  <p className="text-xs text-muted">Model</p>
                  <p className="text-sm font-medium text-primary">{tool.model}</p>
                </div>
              )}

              {tool.serial_number && (
                <div>
                  <p className="text-xs text-muted">Serial Number</p>
                  <p className="text-sm font-medium text-primary">{tool.serial_number}</p>
                </div>
              )}

              <div>
                <p className="text-xs text-muted">Condition</p>
                <p className={`text-sm font-medium capitalize ${getConditionColor(tool.condition)}`}>
                  {tool.condition}
                </p>
              </div>

              {tool.location && (
                <div>
                  <p className="text-xs text-muted">Location</p>
                  <p className="text-sm font-medium text-primary flex items-center gap-1">
                    <MapPin className="w-3 h-3" />
                    {tool.location.name}
                  </p>
                </div>
              )}

              {tool.category && (
                <div>
                  <p className="text-xs text-muted">Category</p>
                  <p className="text-sm font-medium text-primary">{tool.category.name}</p>
                </div>
              )}
            </div>

            {/* Purchase and Maintenance Information */}
            <div className="space-y-3">
              <h3 className="text-sm font-semibold text-primary uppercase tracking-wider">
                Purchase & Maintenance
              </h3>

              {tool.purchase_date && (
                <div>
                  <p className="text-xs text-muted">Purchase Date</p>
                  <p className="text-sm font-medium text-primary flex items-center gap-1">
                    <Calendar className="w-3 h-3" />
                    {formatDate(tool.purchase_date)}
                  </p>
                </div>
              )}

              {tool.purchase_price !== undefined && (
                <div>
                  <p className="text-xs text-muted">Purchase Price</p>
                  <p className="text-sm font-medium text-primary flex items-center gap-1">
                    <DollarSign className="w-3 h-3" />
                    {formatCurrency(tool.purchase_price)}
                  </p>
                </div>
              )}

              {tool.last_maintenance && (
                <div>
                  <p className="text-xs text-muted">Last Maintenance</p>
                  <p className="text-sm font-medium text-primary">{formatDate(tool.last_maintenance)}</p>
                </div>
              )}

              {tool.next_maintenance && (
                <div>
                  <p className="text-xs text-muted">Next Maintenance</p>
                  <p className="text-sm font-medium text-orange-500">
                    {formatDate(tool.next_maintenance)}
                  </p>
                </div>
              )}

              {tool.maintenance_notes && (
                <div>
                  <p className="text-xs text-muted">Maintenance Notes</p>
                  <p className="text-sm text-primary">{tool.maintenance_notes}</p>
                </div>
              )}
            </div>
          </div>

          {/* Description */}
          {tool.description && (
            <div>
              <h3 className="text-sm font-semibold text-primary uppercase tracking-wider mb-2">
                Description
              </h3>
              <p className="text-sm text-secondary">{tool.description}</p>
            </div>
          )}

          {/* Notes */}
          {tool.notes && (
            <div>
              <h3 className="text-sm font-semibold text-primary uppercase tracking-wider mb-2">
                Notes
              </h3>
              <p className="text-sm text-secondary">{tool.notes}</p>
            </div>
          )}

          {/* Manual Link */}
          {tool.manual_url && (
            <div>
              <h3 className="text-sm font-semibold text-primary uppercase tracking-wider mb-2">
                Manual
              </h3>
              <a
                href={tool.manual_url}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-2 text-sm text-blue-600 hover:text-blue-700"
              >
                <FileText className="w-4 h-4" />
                View Manual
              </a>
            </div>
          )}

          {/* Additional Properties */}
          {tool.additional_properties && Object.keys(tool.additional_properties).length > 0 && (
            <div>
              <h3 className="text-sm font-semibold text-primary uppercase tracking-wider mb-2">
                Additional Properties
              </h3>
              <div className="grid grid-cols-2 gap-2">
                {Object.entries(tool.additional_properties).map(([key, value]) => (
                  <div key={key}>
                    <p className="text-xs text-muted">{key}</p>
                    <p className="text-sm font-medium text-primary">{String(value)}</p>
                  </div>
                ))}
              </div>
            </div>
          )}

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
          <p className="text-secondary">Tool not found</p>
        </div>
      )}
    </Modal>
  )
}

export default ToolDetailModal