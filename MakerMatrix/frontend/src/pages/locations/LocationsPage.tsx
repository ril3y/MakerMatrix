import { motion } from 'framer-motion'
import { MapPin, Plus, Search, Filter, Building, FolderTree, Edit2, Trash2, ChevronRight, ChevronDown } from 'lucide-react'
import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import AddLocationModal from '@/components/locations/AddLocationModal'
import EditLocationModal from '@/components/locations/EditLocationModal'
import { locationsService } from '@/services/locations.service'
import { Location } from '@/types/locations'
import LoadingScreen from '@/components/ui/LoadingScreen'

const LocationsPage = () => {
  const [showAddModal, setShowAddModal] = useState(false)
  const [showEditModal, setShowEditModal] = useState(false)
  const [editingLocation, setEditingLocation] = useState<Location | null>(null)
  const [locations, setLocations] = useState<Location[]>([])
  const [locationTree, setLocationTree] = useState<Location[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [searchTerm, setSearchTerm] = useState('')
  const [viewMode, setViewMode] = useState<'list' | 'tree'>('list')
  const [expandedNodes, setExpandedNodes] = useState<Set<string>>(new Set())
  const navigate = useNavigate()

  const loadLocations = async () => {
    try {
      setLoading(true)
      setError(null)
      const data = await locationsService.getAllLocations()
      setLocations(data)
      const tree = locationsService.buildLocationTree(data)
      setLocationTree(tree)
    } catch (err: any) {
      setError(err.response?.data?.error || 'Failed to load locations')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadLocations()
  }, [])

  const handleLocationAdded = () => {
    loadLocations()
    setShowAddModal(false)
  }

  const handleLocationUpdated = () => {
    loadLocations()
    setShowEditModal(false)
    setEditingLocation(null)
  }

  const handleEdit = (location: Location) => {
    setEditingLocation(location)
    setShowEditModal(true)
  }

  const handleDelete = async (location: Location) => {
    if (!confirm(`Are you sure you want to delete "${location.name}"? This action cannot be undone.`)) {
      return
    }

    try {
      await locationsService.deleteLocation(location.id.toString())
      loadLocations()
    } catch (err: any) {
      alert(err.response?.data?.error || 'Failed to delete location')
    }
  }

  const toggleExpanded = (locationId: string) => {
    const newExpanded = new Set(expandedNodes)
    if (newExpanded.has(locationId)) {
      newExpanded.delete(locationId)
    } else {
      newExpanded.add(locationId)
    }
    setExpandedNodes(newExpanded)
  }

  const filteredLocations = locations.filter(location => 
    location.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
    (location.description && location.description.toLowerCase().includes(searchTerm.toLowerCase()))
  )

  const stats = {
    total: locations.length,
    active: locations.length, // All locations are active for now
    root: locations.filter(loc => !loc.parent_id).length
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <motion.div
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        className="flex items-center justify-between"
      >
        <div>
          <h1 className="text-2xl font-bold text-primary flex items-center gap-2">
            <MapPin className="w-6 h-6" />
            Locations
          </h1>
          <p className="text-secondary mt-1">
            Manage storage locations and hierarchies
          </p>
        </div>
        <button 
          onClick={() => setShowAddModal(true)}
          className="btn btn-primary flex items-center gap-2"
        >
          <Plus className="w-4 h-4" />
          Add Location
        </button>
      </motion.div>

      {/* Search and Filters */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.1 }}
        className="card p-4"
      >
        <div className="flex gap-4">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-muted" />
            <input
              type="text"
              placeholder="Search locations..."
              className="input pl-10 w-full"
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
            />
          </div>
          <button className="btn btn-secondary flex items-center gap-2">
            <Filter className="w-4 h-4" />
            Filters
          </button>
          <button 
            onClick={() => setViewMode(viewMode === 'list' ? 'tree' : 'list')}
            className="btn btn-secondary flex items-center gap-2"
          >
            <FolderTree className="w-4 h-4" />
            {viewMode === 'list' ? 'Tree View' : 'List View'}
          </button>
        </div>
      </motion.div>

      {/* Location Stats */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.15 }}
        className="grid grid-cols-1 md:grid-cols-3 gap-4"
      >
        <div className="card p-4">
          <div className="flex items-center gap-3">
            <Building className="w-8 h-8 text-primary" />
            <div>
              <p className="text-sm text-secondary">Total Locations</p>
              <p className="text-2xl font-bold text-primary">{stats.total}</p>
            </div>
          </div>
        </div>
        <div className="card p-4">
          <div className="flex items-center gap-3">
            <MapPin className="w-8 h-8 text-secondary" />
            <div>
              <p className="text-sm text-secondary">Active Locations</p>
              <p className="text-2xl font-bold text-primary">{stats.active}</p>
            </div>
          </div>
        </div>
        <div className="card p-4">
          <div className="flex items-center gap-3">
            <FolderTree className="w-8 h-8 text-accent" />
            <div>
              <p className="text-sm text-secondary">Root Locations</p>
              <p className="text-2xl font-bold text-primary">{stats.root}</p>
            </div>
          </div>
        </div>
      </motion.div>

      {/* Locations List/Tree */}
      {loading ? (
        <LoadingScreen />
      ) : error ? (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
          className="card p-6 text-center"
        >
          <p className="text-red-500">{error}</p>
        </motion.div>
      ) : filteredLocations.length === 0 ? (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
          className="card p-6 text-center"
        >
          <MapPin className="w-16 h-16 text-muted mx-auto mb-4" />
          <h3 className="text-lg font-semibold text-primary mb-2">
            {searchTerm ? 'No locations found' : 'No locations yet'}
          </h3>
          <p className="text-secondary">
            {searchTerm ? 'Try adjusting your search terms' : 'Click "Add Location" to create your first location'}
          </p>
        </motion.div>
      ) : viewMode === 'list' ? (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
          className="card overflow-hidden"
        >
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-border">
                  <th className="text-left p-4 text-secondary font-medium">Name</th>
                  <th className="text-left p-4 text-secondary font-medium">Type</th>
                  <th className="text-left p-4 text-secondary font-medium">Parent</th>
                  <th className="text-left p-4 text-secondary font-medium">Description</th>
                  <th className="text-right p-4 text-secondary font-medium">Actions</th>
                </tr>
              </thead>
              <tbody>
                {filteredLocations.map((location) => (
                  <tr key={location.id} className="border-b border-border hover:bg-background-secondary transition-colors">
                    <td className="p-4">
                      <div className="flex items-center gap-3">
                        <div className="flex items-center gap-2">
                          {location.emoji && (
                            <span className="text-lg">{location.emoji}</span>
                          )}
                          {location.image_url ? (
                            <img
                              src={location.image_url}
                              alt={location.name}
                              className="w-8 h-8 object-cover rounded border border-border"
                            />
                          ) : !location.emoji ? (
                            <MapPin className="w-4 h-4 text-primary" />
                          ) : null}
                        </div>
                        <span className="font-medium text-primary">{location.name}</span>
                      </div>
                    </td>
                    <td className="p-4 text-secondary">
                      {location.location_type || 'General'}
                    </td>
                    <td className="p-4 text-secondary">
                      {location.parent?.name || '-'}
                    </td>
                    <td className="p-4 text-secondary">
                      {location.description || '-'}
                    </td>
                    <td className="p-4">
                      <div className="flex items-center justify-end gap-2">
                        <button
                          onClick={() => handleEdit(location)}
                          className="btn btn-icon btn-secondary"
                          title="Edit location"
                        >
                          <Edit2 className="w-4 h-4" />
                        </button>
                        <button
                          onClick={() => handleDelete(location)}
                          className="btn btn-icon btn-secondary text-red-400 hover:text-red-300"
                          title="Delete location"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </motion.div>
      ) : (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
          className="card p-4"
        >
          <LocationTreeNode 
            locations={locationTree} 
            expandedNodes={expandedNodes}
            toggleExpanded={toggleExpanded}
            onEdit={handleEdit}
            onDelete={handleDelete}
          />
        </motion.div>
      )}

      {/* Add Location Modal */}
      <AddLocationModal
        isOpen={showAddModal}
        onClose={() => setShowAddModal(false)}
        onSuccess={handleLocationAdded}
      />

      {/* Edit Location Modal */}
      {editingLocation && (
        <EditLocationModal
          isOpen={showEditModal}
          onClose={() => {
            setShowEditModal(false)
            setEditingLocation(null)
          }}
          onSuccess={handleLocationUpdated}
          location={editingLocation}
        />
      )}
    </div>
  )
}

// Tree view component
interface LocationTreeNodeProps {
  locations: Location[]
  expandedNodes: Set<string>
  toggleExpanded: (id: string) => void
  onEdit: (location: Location) => void
  onDelete: (location: Location) => void
  level?: number
}

const LocationTreeNode: React.FC<LocationTreeNodeProps> = ({ 
  locations, 
  expandedNodes, 
  toggleExpanded, 
  onEdit, 
  onDelete,
  level = 0 
}) => {
  return (
    <div className="space-y-1">
      {locations.map((location) => {
        const hasChildren = location.children && location.children.length > 0
        const isExpanded = expandedNodes.has(location.id.toString())

        return (
          <div key={location.id}>
            <div 
              className="flex items-center justify-between p-2 rounded hover:bg-background-secondary transition-colors group"
              style={{ paddingLeft: `${level * 24 + 8}px` }}
            >
              <div className="flex items-center gap-2 flex-1">
                {hasChildren && (
                  <button
                    onClick={() => toggleExpanded(location.id.toString())}
                    className="p-1 hover:bg-background-tertiary rounded transition-colors"
                  >
                    {isExpanded ? (
                      <ChevronDown className="w-4 h-4 text-secondary" />
                    ) : (
                      <ChevronRight className="w-4 h-4 text-secondary" />
                    )}
                  </button>
                )}
                {!hasChildren && <div className="w-6" />}
                <div className="flex items-center gap-2">
                  {location.emoji && (
                    <span className="text-lg">{location.emoji}</span>
                  )}
                  {location.image_url ? (
                    <img
                      src={location.image_url}
                      alt={location.name}
                      className="w-4 h-4 object-cover rounded border border-border"
                    />
                  ) : !location.emoji ? (
                    <MapPin className="w-4 h-4 text-primary" />
                  ) : null}
                </div>
                <span className="font-medium text-primary">{location.name}</span>
                <span className="text-sm text-secondary ml-2">
                  ({location.location_type || 'General'})
                </span>
                {location.description && (
                  <span className="text-sm text-muted ml-2">- {location.description}</span>
                )}
              </div>
              <div className="flex items-center gap-2">
                <button
                  onClick={() => onEdit(location)}
                  className="btn btn-icon btn-secondary"
                  title="Edit location"
                >
                  <Edit2 className="w-4 h-4" />
                </button>
                <button
                  onClick={() => onDelete(location)}
                  className="btn btn-icon btn-secondary text-red-400 hover:text-red-300"
                  title="Delete location"
                >
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>
            </div>
            {hasChildren && isExpanded && (
              <LocationTreeNode
                locations={location.children!}
                expandedNodes={expandedNodes}
                toggleExpanded={toggleExpanded}
                onEdit={onEdit}
                onDelete={onDelete}
                level={level + 1}
              />
            )}
          </div>
        )
      })}
    </div>
  )
}

export default LocationsPage