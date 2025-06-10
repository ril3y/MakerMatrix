import { motion } from 'framer-motion'
import { Package, Edit, Trash2, Tag, MapPin, Calendar, ArrowLeft, ExternalLink, Hash, Box, Image } from 'lucide-react'
import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { partsService } from '@/services/parts.service'
import { Part } from '@/types/parts'
import LoadingScreen from '@/components/ui/LoadingScreen'

const PartDetailsPage = () => {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const [part, setPart] = useState<Part | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

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
          <Package className="w-16 h-16 text-text-muted mx-auto mb-4" />
          <h3 className="text-lg font-semibold text-text-primary mb-2">
            Part Not Found
          </h3>
          <p className="text-text-secondary mb-4">
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
            <h1 className="text-2xl font-bold text-text-primary flex items-center gap-2">
              <Package className="w-6 h-6" />
              {part.name}
            </h1>
            <p className="text-text-secondary mt-1">
              Part Details
            </p>
          </div>
        </div>
        <div className="flex gap-2">
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
          <h2 className="text-lg font-semibold text-text-primary">Basic Information</h2>
        </div>
        <div className="card-content">
          <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
            {/* Image Thumbnail */}
            {part.image_url && (
              <div className="lg:col-span-1">
                <div className="aspect-square w-full max-w-48 mx-auto lg:mx-0">
                  <img
                    src={part.image_url}
                    alt={part.name}
                    className="w-full h-full object-cover rounded-lg border border-border"
                    onError={(e) => {
                      const target = e.target as HTMLImageElement;
                      target.style.display = 'none';
                      target.nextElementSibling?.classList.remove('hidden');
                    }}
                  />
                  <div className="hidden w-full h-full bg-bg-secondary rounded-lg border border-border flex items-center justify-center">
                    <div className="text-center text-text-muted">
                      <Image className="w-8 h-8 mx-auto mb-2" />
                      <p className="text-sm">Image not available</p>
                    </div>
                  </div>
                </div>
              </div>
            )}
            
            {/* Basic Info Grid */}
            <div className={`grid grid-cols-1 md:grid-cols-2 gap-6 ${part.image_url ? 'lg:col-span-3' : 'lg:col-span-4'}`}>
            <div className="flex items-start gap-3">
              <Hash className="w-5 h-5 text-text-muted mt-0.5" />
              <div>
                <p className="text-sm text-text-secondary">Part Number</p>
                <p className="font-semibold text-text-primary">{part.part_number || 'Not set'}</p>
              </div>
            </div>
            
            <div className="flex items-start gap-3">
              <Box className="w-5 h-5 text-text-muted mt-0.5" />
              <div>
                <p className="text-sm text-text-secondary">Quantity</p>
                <p className={`font-semibold ${
                  part.minimum_quantity && part.quantity <= part.minimum_quantity
                    ? 'text-red-400'
                    : 'text-text-primary'
                }`}>
                  {part.quantity}
                  {part.minimum_quantity && (
                    <span className="text-xs text-text-muted ml-2">
                      (Min: {part.minimum_quantity})
                    </span>
                  )}
                </p>
              </div>
            </div>

            <div className="flex items-start gap-3">
              <MapPin className="w-5 h-5 text-text-muted mt-0.5" />
              <div>
                <p className="text-sm text-text-secondary">Location</p>
                <p className="font-semibold text-text-primary">
                  {part.location?.name || 'Not assigned'}
                </p>
              </div>
            </div>

            <div className="flex items-start gap-3">
              <Tag className="w-5 h-5 text-text-muted mt-0.5" />
              <div>
                <p className="text-sm text-text-secondary">Supplier</p>
                <div className="flex items-center gap-2">
                  <p className="font-semibold text-text-primary">{part.supplier || 'Not set'}</p>
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
              <Calendar className="w-5 h-5 text-text-muted mt-0.5" />
              <div>
                <p className="text-sm text-text-secondary">Created</p>
                <p className="font-semibold text-text-primary">{formatDate(part.created_at)}</p>
              </div>
            </div>

            <div className="flex items-start gap-3">
              <Calendar className="w-5 h-5 text-text-muted mt-0.5" />
              <div>
                <p className="text-sm text-text-secondary">Last Updated</p>
                <p className="font-semibold text-text-primary">{formatDate(part.updated_at)}</p>
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
            <h2 className="text-lg font-semibold text-text-primary">Categories</h2>
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

      {/* Properties */}
      {part.properties && Object.keys(part.properties).length > 0 && (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3 }}
          className="card"
        >
          <div className="card-header">
            <h2 className="text-lg font-semibold text-text-primary">Properties</h2>
          </div>
          <div className="card-content">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {Object.entries(part.properties).map(([key, value]) => (
                <div key={key} className="border-l-2 border-primary/20 pl-4">
                  <p className="text-sm text-text-secondary capitalize">
                    {key.replace(/_/g, ' ')}
                  </p>
                  <p className="font-medium text-text-primary">
                    {typeof value === 'object' ? JSON.stringify(value) : String(value)}
                  </p>
                </div>
              ))}
            </div>
          </div>
        </motion.div>
      )}

    </div>
  )
}

export default PartDetailsPage