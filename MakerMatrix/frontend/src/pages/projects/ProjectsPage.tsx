import { motion } from 'framer-motion'
import {
  Hash,
  Plus,
  Search,
  Edit2,
  Trash2,
  Package,
  ExternalLink,
  Image as ImageIcon,
} from 'lucide-react'
import { useState, useEffect, useMemo } from 'react'
import AddProjectModal from '@/components/projects/AddProjectModal'
import EditProjectModal from '@/components/projects/EditProjectModal'
import { projectsService } from '@/services/projects.service'
import { Project } from '@/types/projects'
import LoadingScreen from '@/components/ui/LoadingScreen'

const ProjectsPage = () => {
  const [showAddModal, setShowAddModal] = useState(false)
  const [showEditModal, setShowEditModal] = useState(false)
  const [editingProject, setEditingProject] = useState<Project | null>(null)
  const [projects, setProjects] = useState<Project[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [searchTerm, setSearchTerm] = useState('')

  const loadProjects = async () => {
    try {
      setLoading(true)
      setError(null)
      const data = await projectsService.getAllProjects()
      setProjects(data)
    } catch (err: any) {
      setError(err.response?.data?.error || 'Failed to load projects')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadProjects()
  }, [])

  const handleProjectAdded = () => {
    loadProjects()
    setShowAddModal(false)
  }

  const handleProjectUpdated = () => {
    loadProjects()
    setShowEditModal(false)
    setEditingProject(null)
  }

  const handleEdit = (project: Project) => {
    setEditingProject(project)
    setShowEditModal(true)
  }

  const handleDelete = async (project: Project) => {
    if (
      !confirm(
        `Are you sure you want to delete "${project.name}"? This will not delete the parts, just remove the project tag.`
      )
    ) {
      return
    }

    try {
      await projectsService.deleteProject(project.id)
      loadProjects()
    } catch (err: any) {
      alert(err.response?.data?.error || 'Failed to delete project')
    }
  }

  const filteredProjects = projectsService.filterProjects(projects, searchTerm)
  const sortedProjects = projectsService.sortProjectsByName(filteredProjects)

  const stats = {
    total: projects.length,
    active: projectsService.getProjectsByStatus(projects, 'active').length,
    completed: projectsService.getProjectsByStatus(projects, 'completed').length,
    planning: projectsService.getProjectsByStatus(projects, 'planning').length,
  }

  // Get existing project names for validation
  const existingProjects = useMemo(() => projects.map((proj) => proj.name), [projects])

  // Helper to get status color
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

  if (loading) return <LoadingScreen />

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
            <Hash className="w-6 h-6" />
            Projects
          </h1>
          <p className="text-secondary mt-1">Manage and track your projects</p>
        </div>
        <button
          onClick={() => setShowAddModal(true)}
          className="btn btn-primary flex items-center gap-2"
        >
          <Plus className="w-4 h-4" />
          Add Project
        </button>
      </motion.div>

      {/* Stats Cards */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.1 }}
        className="grid grid-cols-1 md:grid-cols-4 gap-4"
      >
        <div className="card">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-secondary">Total Projects</p>
              <p className="text-2xl font-bold text-primary">{stats.total}</p>
            </div>
            <Hash className="w-8 h-8 text-muted" />
          </div>
        </div>

        <div className="card">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-secondary">Planning</p>
              <p className="text-2xl font-bold text-blue-400">{stats.planning}</p>
            </div>
            <div className="w-8 h-8 rounded-full bg-blue-600/20 flex items-center justify-center">
              <Hash className="w-4 h-4 text-blue-400" />
            </div>
          </div>
        </div>

        <div className="card">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-secondary">Active</p>
              <p className="text-2xl font-bold text-green-400">{stats.active}</p>
            </div>
            <div className="w-8 h-8 rounded-full bg-green-600/20 flex items-center justify-center">
              <Hash className="w-4 h-4 text-green-400" />
            </div>
          </div>
        </div>

        <div className="card">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-secondary">Completed</p>
              <p className="text-2xl font-bold text-purple-400">{stats.completed}</p>
            </div>
            <div className="w-8 h-8 rounded-full bg-purple-600/20 flex items-center justify-center">
              <Hash className="w-4 h-4 text-purple-400" />
            </div>
          </div>
        </div>
      </motion.div>

      {/* Search */}
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.2 }}
        className="card"
      >
        <div className="relative">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-5 h-5 text-muted" />
          <input
            type="text"
            placeholder="Search projects..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="input w-full pl-10"
          />
        </div>
      </motion.div>

      {/* Projects List */}
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.3 }}
        className="space-y-3"
      >
        {error && (
          <div className="bg-red-500/10 border border-red-500/50 rounded-lg p-4 text-red-400">
            {error}
          </div>
        )}

        {sortedProjects.length === 0 ? (
          <div className="card text-center py-12">
            <Hash className="w-12 h-12 text-muted mx-auto mb-4" />
            <p className="text-secondary">
              {searchTerm
                ? 'No projects found matching your search.'
                : 'No projects yet. Create your first project to get started!'}
            </p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {sortedProjects.map((project) => (
              <motion.div
                key={project.id}
                initial={{ opacity: 0, scale: 0.95 }}
                animate={{ opacity: 1, scale: 1 }}
                className="card hover:shadow-lg transition-shadow"
              >
                {/* Project Image */}
                {project.image_url && (
                  <div className="mb-3 rounded-lg overflow-hidden bg-theme-secondary">
                    <img
                      src={project.image_url}
                      alt={project.name}
                      className="w-full h-32 object-cover"
                    />
                  </div>
                )}

                {/* Project Header */}
                <div className="flex items-start justify-between mb-3">
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-1">
                      <Hash className="w-4 h-4 text-muted" />
                      <h3 className="text-lg font-semibold text-primary truncate">
                        {project.name}
                      </h3>
                    </div>
                    <span
                      className={`inline-block px-2 py-0.5 rounded text-xs font-medium ${getStatusColor(project.status)}`}
                    >
                      {project.status}
                    </span>
                  </div>
                </div>

                {/* Description */}
                {project.description && (
                  <p className="text-sm text-secondary mb-3 line-clamp-2">{project.description}</p>
                )}

                {/* Stats */}
                <div className="flex items-center gap-4 mb-3 text-sm text-secondary">
                  <div className="flex items-center gap-1">
                    <Package className="w-4 h-4" />
                    <span>{project.parts_count} parts</span>
                  </div>
                  {project.estimated_cost && (
                    <div className="flex items-center gap-1">
                      <span>${project.estimated_cost.toFixed(2)}</span>
                    </div>
                  )}
                </div>

                {/* Links */}
                {project.links && Object.keys(project.links).length > 0 && (
                  <div className="flex flex-wrap gap-2 mb-3">
                    {Object.entries(project.links).map(([key, value]) => (
                      <a
                        key={key}
                        href={value as string}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="inline-flex items-center gap-1 text-xs text-accent hover:text-accent-hover transition-colors"
                      >
                        <ExternalLink className="w-3 h-3" />
                        {key}
                      </a>
                    ))}
                  </div>
                )}

                {/* Actions */}
                <div className="flex gap-2 pt-3 border-t border-border">
                  <button
                    onClick={() => handleEdit(project)}
                    className="btn btn-secondary btn-sm flex-1 flex items-center justify-center gap-1"
                  >
                    <Edit2 className="w-3 h-3" />
                    Edit
                  </button>
                  <button
                    onClick={() => handleDelete(project)}
                    className="btn btn-danger btn-sm flex-1 flex items-center justify-center gap-1"
                  >
                    <Trash2 className="w-3 h-3" />
                    Delete
                  </button>
                </div>
              </motion.div>
            ))}
          </div>
        )}
      </motion.div>

      {/* Modals */}
      <AddProjectModal
        isOpen={showAddModal}
        onClose={() => setShowAddModal(false)}
        onSuccess={handleProjectAdded}
        existingProjects={existingProjects}
      />

      <EditProjectModal
        isOpen={showEditModal}
        onClose={() => setShowEditModal(false)}
        onSuccess={handleProjectUpdated}
        project={editingProject}
        existingProjects={existingProjects}
      />
    </div>
  )
}

export default ProjectsPage
