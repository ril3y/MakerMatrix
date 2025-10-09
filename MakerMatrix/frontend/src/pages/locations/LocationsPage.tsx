import { motion } from 'framer-motion'
import {
  MapPin,
  Plus,
  Search,
  Filter,
  Building,
  FolderTree,
  Edit2,
  Trash2,
  ChevronRight,
  ChevronDown,
  Eye,
  Package,
} from 'lucide-react'
import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import AddLocationModal from '@/components/locations/AddLocationModal'
import EditLocationModal from '@/components/locations/EditLocationModal'
import LocationDetailsModal from '@/components/locations/LocationDetailsModal'
import ContainerSlotPickerModal from '@/components/locations/ContainerSlotPickerModal'
import AuthenticatedImage from '@/components/ui/AuthenticatedImage'
import { locationsService } from '@/services/locations.service'
import type { Location } from '@/types/locations'
import LoadingScreen from '@/components/ui/LoadingScreen'

const LocationsPage = () => {
  const [showAddModal, setShowAddModal] = useState(false)
  const [showEditModal, setShowEditModal] = useState(false)
  const [showDetailsModal, setShowDetailsModal] = useState(false)
  const [showSlotPickerModal, setShowSlotPickerModal] = useState(false)
  const [editingLocation, setEditingLocation] = useState<Location | null>(null)
  const [viewingLocation, setViewingLocation] = useState<Location | null>(null)
  const [selectedContainer, setSelectedContainer] = useState<Location | null>(null)
  const [locations, setLocations] = useState<Location[]>([])
  const [locationTree, setLocationTree] = useState<Location[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [searchTerm, setSearchTerm] = useState('')
  const [viewMode, setViewMode] = useState<'list' | 'tree'>('tree')
  const [expandedNodes, setExpandedNodes] = useState<Set<string>>(new Set())
  const [hideAutoSlots, setHideAutoSlots] = useState(true)
  const navigate = useNavigate()

  const loadLocations = async () => {
    try {
      setLoading(true)
      setError(null)
      const data = await locationsService.getAllLocations({ hide_auto_slots: hideAutoSlots })
      setLocations(data)
      const tree = locationsService.buildLocationTree(data)
      setLocationTree(tree)
    } catch (err) {
      const error = err as { response?: { data?: { error?: string; message?: string; detail?: string }; status?: number }; message?: string }
      setError(error.response?.data?.error || 'Failed to load locations')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadLocations()
  }, [hideAutoSlots])

  const handleLocationAdded = () => {
    loadLocations()
    setShowAddModal(false)
  }

  const handleLocationUpdated = () => {
    loadLocations()
    setShowEditModal(false)
    setEditingLocation(null)
  }

  const handleViewDetails = (location: Location) => {
    setViewingLocation(location)
    setShowDetailsModal(true)
  }

  const handleEdit = (location: Location) => {
    setEditingLocation(location)
    setShowEditModal(true)
  }

  const handleViewSlots = (location: Location, event: React.MouseEvent) => {
    event.stopPropagation() // Prevent triggering location details
    setSelectedContainer(location)
    setShowSlotPickerModal(true)
  }

  const handleDelete = async (location: Location) => {
    if (
      !confirm(`Are you sure you want to delete "${location.name}"? This action cannot be undone.`)
    ) {
      return
    }

    try {
      await locationsService.deleteLocation(location.id.toString())
      loadLocations()
    } catch (err) {
      const error = err as { response?: { data?: { error?: string; message?: string; detail?: string }; status?: number }; message?: string }
      alert(error.response?.data?.error || 'Failed to delete location')
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

  // Calculate total parts for a location, including parts in child slots for containers
  const getTotalPartsCount = (location: Location): number => {
    // For containers with slots, sum parts from all child slot locations
    if (location.location_type === 'container' && location.slot_count) {
      const childSlots = locations.filter(
        (loc) => loc.parent_id === location.id && loc.is_auto_generated_slot
      )
      return childSlots.reduce((sum, slot) => sum + (slot.parts_count || 0), 0)
    }
    // For regular locations, just return the parts_count
    return location.parts_count || 0
  }

  const filteredLocations = locations.filter(
    (location) =>
      location.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      (location.description &&
        location.description.toLowerCase().includes(searchTerm.toLowerCase()))
  )

  const stats = {
    total: locations.length,
    active: locations.length, // All locations are active for now
    root: locations.filter((loc) => !loc.parent_id).length,
  }

  return (
    <div className="max-w-screen-2xl space-y-6">
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
          <p className="text-secondary mt-1">Manage storage locations and hierarchies</p>
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
          <button
            onClick={() => setHideAutoSlots(!hideAutoSlots)}
            className="btn btn-secondary flex items-center gap-2"
            title={hideAutoSlots ? 'Show auto-generated slots' : 'Hide auto-generated slots'}
          >
            <Package className="w-4 h-4" />
            {hideAutoSlots ? 'Show' : 'Hide'} Auto-Slots
          </button>
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
            {searchTerm
              ? 'Try adjusting your search terms'
              : 'Click "Add Location" to create your first location'}
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
              <thead className="bg-gradient-to-r from-purple-600/20 to-blue-600/20">
                <tr className="border-b border-purple-500/10">
                  <th className="text-left p-4 text-primary font-bold text-xs uppercase tracking-wider">Name</th>
                  <th className="text-left p-4 text-primary font-bold text-xs uppercase tracking-wider">Type</th>
                  <th className="text-left p-4 text-primary font-bold text-xs uppercase tracking-wider">Parent</th>
                  <th className="text-left p-4 text-primary font-bold text-xs uppercase tracking-wider">Description</th>
                  <th className="text-right p-4 text-primary font-bold text-xs uppercase tracking-wider">Actions</th>
                </tr>
              </thead>
              <tbody className="bg-theme-elevated/50 divide-y divide-purple-500/10">
                {filteredLocations.map((location) => (
                  <tr
                    key={location.id}
                    className="hover:bg-gradient-to-r hover:from-purple-600/5 hover:to-blue-600/5 transition-all duration-200"
                  >
                    <td className="p-4">
                      <div
                        className="flex items-center gap-3 cursor-pointer group"
                        onClick={() => handleViewDetails(location)}
                      >
                        {location.emoji ? (
                          <span className="text-lg">{location.emoji}</span>
                        ) : location.image_url ? (
                          <AuthenticatedImage
                            src={location.image_url}
                            alt={location.name}
                            className="w-8 h-8 object-cover rounded border border-border"
                          />
                        ) : (
                          <MapPin className="w-4 h-4 text-primary" />
                        )}
                        <span className="font-medium text-primary group-hover:text-secondary transition-colors">
                          {location.name}
                        </span>
                        {location.slot_count && location.slot_count > 0 && (
                          <span className="ml-2 px-2 py-0.5 bg-primary/20 text-primary text-xs font-medium rounded border border-primary/30 flex items-center gap-1">
                            <Package className="w-3 h-3" />
                            {location.slot_count} slots
                          </span>
                        )}
                      </div>
                    </td>
                    <td className="p-4 text-secondary">
                      {location.location_type || 'General'}
                      {location.location_type === 'container' && location.slot_count && (
                        <span className="ml-2 text-xs text-muted">({location.slot_layout_type || 'simple'})</span>
                      )}
                    </td>
                    <td className="p-4 text-secondary">{location.parent?.name || '-'}</td>
                    <td className="p-4 text-secondary">{location.description || '-'}</td>
                    <td className="p-4">
                      <div className="flex items-center justify-end gap-2">
                        <button
                          onClick={() => handleViewDetails(location)}
                          className="btn btn-icon btn-primary"
                          title="View details"
                        >
                          <Eye className="w-4 h-4" />
                        </button>
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
            allLocations={locations}
            expandedNodes={expandedNodes}
            toggleExpanded={toggleExpanded}
            onViewDetails={handleViewDetails}
            onEdit={handleEdit}
            onDelete={handleDelete}
            onViewSlots={handleViewSlots}
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

      {/* Location Details Modal */}
      {viewingLocation && (
        <LocationDetailsModal
          isOpen={showDetailsModal}
          onClose={() => {
            setShowDetailsModal(false)
            setViewingLocation(null)
          }}
          location={viewingLocation}
          onRefresh={loadLocations}
          onOpenLocation={(newLocation) => {
            // Switch to viewing the new location
            setViewingLocation(newLocation)
          }}
        />
      )}

      {/* Container Slot Picker Modal */}
      {selectedContainer && (
        <ContainerSlotPickerModal
          isOpen={showSlotPickerModal}
          onClose={() => {
            setShowSlotPickerModal(false)
            setSelectedContainer(null)
          }}
          containerLocation={selectedContainer}
          onSlotSelect={(slotId) => {
            // Just close the modal - we're just viewing slots, not selecting
            setShowSlotPickerModal(false)
            setSelectedContainer(null)
          }}
        />
      )}
    </div>
  )
}

// Tree view component
interface LocationTreeNodeProps {
  locations: Location[]
  allLocations: Location[] // Full list for calculating parts in child slots
  expandedNodes: Set<string>
  toggleExpanded: (id: string) => void
  onViewDetails: (location: Location) => void
  onEdit: (location: Location) => void
  onDelete: (location: Location) => void
  onViewSlots: (location: Location, event: React.MouseEvent) => void
  level?: number
}

const LocationTreeNode: React.FC<LocationTreeNodeProps> = ({
  locations,
  allLocations,
  expandedNodes,
  toggleExpanded,
  onViewDetails,
  onEdit,
  onDelete,
  onViewSlots,
  level = 0,
}) => {
  // Calculate total parts for a location, including parts in child slots for containers
  const getTotalPartsCount = (location: Location): number => {
    // For containers with slots, sum parts from all child slot locations
    if (location.location_type === 'container' && location.slot_count) {
      const childSlots = allLocations.filter(
        (loc) => loc.parent_id === location.id && loc.is_auto_generated_slot
      )
      return childSlots.reduce((sum, slot) => sum + (slot.parts_count || 0), 0)
    }
    // For regular locations, just return the parts_count
    return location.parts_count || 0
  }

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
                <div
                  className="flex items-center gap-2 cursor-pointer flex-1"
                  onClick={() => onViewDetails(location)}
                >
                  <div className="flex items-center gap-2">
                    {location.emoji ? (
                      <span className="text-lg">{location.emoji}</span>
                    ) : location.image_url ? (
                      <AuthenticatedImage
                        src={location.image_url}
                        alt={location.name}
                        className="w-6 h-6 object-cover rounded border border-border"
                      />
                    ) : (
                      <MapPin className="w-4 h-4 text-primary" />
                    )}
                  </div>
                  <span className="font-medium text-primary hover:text-secondary transition-colors">
                    {location.name}
                  </span>
                  {/* Only show location type if it's not a container with slots (slots badge makes it obvious) */}
                  {!(location.location_type === 'container' && location.slot_count) && (
                    <span className="text-sm text-secondary ml-2">
                      ({location.location_type || 'General'})
                    </span>
                  )}
                  {location.slot_count && location.slot_count > 0 && (
                    <span
                      onClick={(e) => onViewSlots(location, e)}
                      className="ml-2 px-2 py-0.5 bg-primary/20 text-primary text-xs font-medium rounded border border-primary/30 flex items-center gap-1 inline-flex cursor-pointer hover:bg-primary/30 transition-colors"
                      title="View slot layout"
                    >
                      <Package className="w-3 h-3" />
                      {location.slot_count} slots
                    </span>
                  )}
                  {(() => {
                    const totalParts = getTotalPartsCount(location)
                    return (
                      totalParts > 0 && (
                        <span className="ml-2 px-2 py-0.5 bg-primary/20 text-primary text-xs font-medium rounded">
                          {totalParts} {totalParts === 1 ? 'part' : 'parts'}
                        </span>
                      )
                    )
                  })()}
                  {location.description && (
                    <span className="text-sm text-muted ml-2">- {location.description}</span>
                  )}
                </div>
              </div>
              <div className="flex items-center gap-2">
                <button
                  onClick={() => onViewDetails(location)}
                  className="btn btn-icon btn-primary"
                  title="View details"
                >
                  <Eye className="w-4 h-4" />
                </button>
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
                allLocations={allLocations}
                expandedNodes={expandedNodes}
                toggleExpanded={toggleExpanded}
                onViewDetails={onViewDetails}
                onEdit={onEdit}
                onDelete={onDelete}
                onViewSlots={onViewSlots}
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
