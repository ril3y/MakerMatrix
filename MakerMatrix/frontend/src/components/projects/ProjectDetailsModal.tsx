import { useState, useEffect } from 'react'
import { X, Package, ExternalLink, MapPin, Hash } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import Modal from '@/components/ui/Modal'
import { projectsService } from '@/services/projects.service'
import type { Project } from '@/types/projects'
import type { Part } from '@/types/parts'
import { getFaviconUrl, extractDisplayName, extractDomain } from '@/utils/url.utils'

interface ProjectDetailsModalProps {
  isOpen: boolean
  onClose: () => void
  project: Project | null
}

const ProjectDetailsModal = ({ isOpen, onClose, project }: ProjectDetailsModalProps) => {
  const navigate = useNavigate()
  const [parts, setParts] = useState<Part[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [displayCount, setDisplayCount] = useState(4)
  const partsPerLoad = 4

  useEffect(() => {
    const loadParts = async () => {
      if (!project) return

      try {
        setLoading(true)
        setError(null)
        const projectParts = await projectsService.getProjectParts(project.id)
        setParts(projectParts)
        setDisplayCount(4) // Reset to show first 4 parts
      } catch (err) {
        console.error('Failed to load project parts:', err)
        setError('Failed to load parts for this project')
      } finally {
        setLoading(false)
      }
    }

    if (isOpen && project) {
      loadParts()
    }
  }, [isOpen, project])

  const handlePartClick = (partId: string) => {
    navigate(`/parts/${partId}`)
    onClose()
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'planning':
        return 'bg-blue-600/20 text-blue-400 border-blue-600/50'
      case 'active':
        return 'bg-green-600/20 text-green-400 border-green-600/50'
      case 'completed':
        return 'bg-purple-600/20 text-purple-400 border-purple-600/50'
      case 'archived':
        return 'bg-gray-600/20 text-gray-400 border-gray-600/50'
      default:
        return 'bg-gray-700 text-gray-300 border-gray-600'
    }
  }

  // Get parts to display (limited by displayCount)
  const displayedParts = parts.slice(0, displayCount)
  const hasMore = displayCount < parts.length

  // Handle scroll to load more
  const handleScroll = (e: React.UIEvent<HTMLDivElement>) => {
    const target = e.currentTarget
    const scrolledToBottom = target.scrollHeight - target.scrollTop <= target.clientHeight + 50

    if (scrolledToBottom && hasMore && !loading) {
      setDisplayCount((prev) => Math.min(prev + partsPerLoad, parts.length))
    }
  }

  if (!project) return null

  return (
    <Modal isOpen={isOpen} onClose={onClose} title="" size="xl">
      <div className="space-y-6">
        {/* Project Header */}
        <div className="bg-theme-secondary rounded-lg p-6 border border-theme-primary">
          <div className="flex items-start gap-4">
            {/* Project Image */}
            {project.image_url && (
              <img
                src={project.image_url}
                alt={project.name}
                className="w-24 h-24 object-cover rounded-lg border border-theme-primary flex-shrink-0"
              />
            )}

            {/* Project Info */}
            <div className="flex-1 min-w-0">
              {/* Name and Status */}
              <div className="flex items-center gap-3 mb-2 flex-wrap">
                <div className="flex items-center gap-2">
                  <Hash className="w-5 h-5 text-purple-400" />
                  <h2 className="text-xl font-bold text-theme-primary">{project.name}</h2>
                </div>
                <span
                  className={`inline-block px-2.5 py-1 rounded text-xs font-medium ${getStatusColor(project.status)}`}
                >
                  {project.status}
                </span>
              </div>

              {/* Description */}
              {project.description && (
                <p className="text-theme-secondary text-sm mb-3">{project.description}</p>
              )}

              {/* Stats - Inline and compact */}
              <div className="flex items-center gap-4 text-sm">
                <div className="flex items-center gap-2">
                  <Package className="w-4 h-4 text-theme-muted" />
                  <span className="text-theme-secondary">
                    <span className="font-semibold text-theme-primary">{project.parts_count}</span>{' '}
                    parts
                  </span>
                </div>
                {project.estimated_cost && (
                  <div className="flex items-center gap-2">
                    <span className="text-theme-muted">•</span>
                    <span className="text-theme-secondary">
                      Est.{' '}
                      <span className="font-semibold text-theme-primary">
                        ${project.estimated_cost.toFixed(2)}
                      </span>
                    </span>
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* Project Links */}
          {project.links && Object.keys(project.links).length > 0 && (
            <div className="mt-4 pt-4 border-t border-theme-primary">
              <p className="text-xs font-semibold text-theme-secondary mb-2 uppercase tracking-wide">
                Project Links
              </p>
              <div className="flex flex-wrap gap-2">
                {Object.entries(project.links).map(([key, value]) => {
                  const domain = extractDomain(value as string)
                  const displayName = domain ? extractDisplayName(domain) : key
                  return (
                    <a
                      key={key}
                      href={value as string}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-flex items-center gap-2 px-3 py-1.5 bg-theme-elevated border border-theme-primary rounded-lg text-sm text-primary hover:text-secondary hover:border-secondary transition-colors"
                    >
                      <img
                        src={getFaviconUrl(value as string)}
                        alt=""
                        className="w-4 h-4"
                        onError={(e) => {
                          e.currentTarget.style.display = 'none'
                        }}
                      />
                      {displayName}
                      <ExternalLink className="w-3 h-3" />
                    </a>
                  )
                })}
              </div>
            </div>
          )}
        </div>

        {/* Parts List */}
        <div className="bg-theme-secondary rounded-lg p-6 border border-theme-primary">
          <h3 className="text-lg font-semibold text-primary mb-4 flex items-center gap-2">
            <Package className="w-5 h-5" />
            Parts in this Project ({parts.length})
          </h3>

          {loading ? (
            <div className="text-center py-8">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary mx-auto"></div>
              <p className="text-muted mt-2">Loading parts...</p>
            </div>
          ) : error ? (
            <div className="bg-red-500/10 border border-red-500/50 rounded-lg p-4 text-red-400">
              {error}
            </div>
          ) : parts.length === 0 ? (
            <div className="text-center py-8 text-muted">
              <Package className="w-12 h-12 mx-auto mb-2 opacity-50" />
              <p>No parts assigned to this project yet.</p>
            </div>
          ) : (
            <div className="space-y-2 max-h-[400px] overflow-y-auto pr-2" onScroll={handleScroll}>
              {displayedParts.map((part) => (
                <div
                  key={part.id}
                  onClick={() => handlePartClick(part.id)}
                  className="bg-theme-elevated p-4 rounded-lg border border-theme-primary hover:border-accent transition-colors cursor-pointer"
                >
                  <div className="flex items-start gap-4">
                    {part.image_url && (
                      <img
                        src={part.image_url}
                        alt={part.name}
                        className="w-16 h-16 object-cover rounded border border-theme-primary"
                      />
                    )}
                    <div className="flex-1 min-w-0">
                      <h4 className="font-semibold text-primary truncate">{part.name}</h4>
                      {part.part_number && (
                        <p className="text-sm text-muted">Part #: {part.part_number}</p>
                      )}
                      {part.description && (
                        <p className="text-sm text-secondary line-clamp-2 mt-1">
                          {part.description}
                        </p>
                      )}
                      <div className="flex items-center gap-4 mt-2 text-xs text-muted">
                        <span className="flex items-center gap-1">
                          <Package className="w-3 h-3" />
                          Qty: {part.quantity}
                        </span>
                        {part.location && (
                          <span className="flex items-center gap-1">
                            <MapPin className="w-3 h-3" />
                            {part.location.name}
                          </span>
                        )}
                        {part.supplier && <span>Supplier: {part.supplier}</span>}
                      </div>
                    </div>
                  </div>
                </div>
              ))}

              {/* Loading more indicator */}
              {hasMore && (
                <div className="text-center py-4 text-theme-muted text-sm">
                  Scroll for more parts...
                </div>
              )}
            </div>
          )}
        </div>

        {/* Close Button */}
        <div className="flex justify-end pt-4 border-t border-border">
          <button onClick={onClose} className="btn btn-secondary flex items-center gap-2">
            <X className="w-4 h-4" />
            Close
          </button>
        </div>
      </div>
    </Modal>
  )
}

export default ProjectDetailsModal
