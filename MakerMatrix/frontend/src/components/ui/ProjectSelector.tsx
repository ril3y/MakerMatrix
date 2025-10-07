import React from 'react'
import { Plus, Hash } from 'lucide-react'
import { Project } from '../../types/projects'
import FormField from './FormField'

interface ProjectSelectorProps {
  projects: Project[]
  selectedProjects: string[]
  onToggleProject: (projectId: string) => void
  onAddNewProject?: () => void
  label?: string
  description?: string
  error?: string
  showAddButton?: boolean
  layout?: 'checkboxes' | 'pills'
  className?: string
}

const ProjectSelector: React.FC<ProjectSelectorProps> = ({
  projects,
  selectedProjects,
  onToggleProject,
  onAddNewProject,
  label = 'Projects',
  description,
  error,
  showAddButton = false,
  layout = 'pills',
  className = '',
}) => {
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

  if (layout === 'pills') {
    return (
      <div className={className}>
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <Hash className="w-5 h-5 text-muted" />
            <h2 className="text-lg font-semibold text-primary">{label}</h2>
          </div>
          {showAddButton && onAddNewProject && (
            <button
              type="button"
              onClick={onAddNewProject}
              className="btn btn-secondary text-sm flex items-center gap-2"
            >
              <Plus className="w-4 h-4" />
              New Project
            </button>
          )}
        </div>

        {description && <p className="text-sm text-muted mb-3">{description}</p>}

        <div className="flex flex-wrap gap-2">
          {projects.map((project) => {
            const isSelected = selectedProjects.includes(project.id)
            return (
              <button
                key={project.id}
                type="button"
                onClick={() => onToggleProject(project.id)}
                className={`
                  px-3 py-1.5 rounded-full text-sm font-medium transition-all
                  flex items-center gap-1.5 border
                  ${
                    isSelected
                      ? 'bg-purple-600 text-white border-purple-600 shadow-sm'
                      : getStatusColor(project.status) + ' hover:brightness-110'
                  }
                `}
                title={`${project.name} (${project.status}) - ${project.parts_count} parts`}
              >
                <Hash className="w-3.5 h-3.5" />
                {project.name}
                {project.parts_count > 0 && (
                  <span className="text-xs opacity-75 ml-1">({project.parts_count})</span>
                )}
              </button>
            )
          })}
          {projects.length === 0 && (
            <p className="text-muted text-sm italic">
              No projects available. Create your first project to get started.
            </p>
          )}
        </div>

        {error && <p className="text-red-500 text-sm mt-2">{error}</p>}
      </div>
    )
  }

  // Checkboxes layout (fallback)
  return (
    <FormField label={label} description={description} error={error} className={className}>
      <div className="space-y-3">
        {showAddButton && onAddNewProject && (
          <div className="flex justify-end">
            <button
              type="button"
              onClick={onAddNewProject}
              className="btn btn-secondary btn-sm flex items-center gap-2"
            >
              <Plus className="w-4 h-4" />
              New Project
            </button>
          </div>
        )}

        <div className="border border-border rounded-md p-3 max-h-32 overflow-y-auto">
          {projects.length > 0 ? (
            <div className="space-y-2">
              {projects.map((project) => (
                <label key={project.id} className="flex items-center gap-2 cursor-pointer group">
                  <input
                    type="checkbox"
                    checked={selectedProjects.includes(project.id)}
                    onChange={() => onToggleProject(project.id)}
                    className="rounded border-border"
                  />
                  <div className="flex items-center gap-2 flex-1">
                    <Hash className="w-3.5 h-3.5 text-muted" />
                    <span className="text-sm text-primary group-hover:text-accent">
                      {project.name}
                    </span>
                    {project.parts_count > 0 && (
                      <span className="text-xs text-muted">({project.parts_count} parts)</span>
                    )}
                  </div>
                  <span className={`text-xs px-2 py-0.5 rounded ${getStatusColor(project.status)}`}>
                    {project.status}
                  </span>
                </label>
              ))}
            </div>
          ) : (
            <p className="text-sm text-secondary">No projects available</p>
          )}
        </div>
      </div>
    </FormField>
  )
}

export default ProjectSelector
