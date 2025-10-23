import type { ApiResponse } from './api'
import { apiClient } from './api'
import type { Project, ProjectCreate, ProjectUpdate, ProjectsResponse } from '../types/projects'
import type { Part } from '../types/parts'

export class ProjectsService {
  async createProject(data: ProjectCreate): Promise<Project> {
    const response = await apiClient.post<ApiResponse<Project>>('/api/projects/', data)
    if (response.status === 'success' && response.data) {
      return response.data
    }
    throw new Error(response.message || 'Failed to create project')
  }

  async getProject(params: { id?: string; name?: string; slug?: string }): Promise<Project> {
    if (!params.id && !params.name && !params.slug) {
      throw new Error('Either id, name, or slug must be provided')
    }

    const queryParams = new URLSearchParams()
    if (params.id) queryParams.append('project_id', params.id)
    if (params.name) queryParams.append('name', params.name)
    if (params.slug) queryParams.append('slug', params.slug)

    const response = await apiClient.get<ApiResponse<Project>>(
      `/api/projects/${params.id}?${queryParams}`
    )
    if (response.status === 'success' && response.data) {
      return response.data
    }
    throw new Error(response.message || 'Failed to get project')
  }

  async updateProject(id: string, data: ProjectUpdate): Promise<Project> {
    const response = await apiClient.put<ApiResponse<Project>>(`/api/projects/${id}`, data)
    if (response.status === 'success' && response.data) {
      return response.data
    }
    throw new Error(response.message || 'Failed to update project')
  }

  async deleteProject(id: string): Promise<Project> {
    const response = await apiClient.delete<ApiResponse<Project>>(`/api/projects/${id}`)
    if (response.status === 'success' && response.data) {
      return response.data
    }
    throw new Error(response.message || 'Failed to delete project')
  }

  async getAllProjects(): Promise<Project[]> {
    const response = await apiClient.get<ApiResponse<ProjectsResponse>>('/api/projects/')
    if (response.status === 'success' && response.data) {
      return response.data.projects || []
    }
    return []
  }

  async addPartToProject(projectId: string, partId: string, notes?: string): Promise<void> {
    const response = await apiClient.post<ApiResponse<void>>(
      `/api/projects/${projectId}/parts/${partId}`,
      notes ? { notes } : undefined
    )
    if (response.status !== 'success') {
      throw new Error(response.message || 'Failed to add part to project')
    }
  }

  async removePartFromProject(projectId: string, partId: string): Promise<void> {
    const response = await apiClient.delete<ApiResponse<void>>(
      `/api/projects/${projectId}/parts/${partId}`
    )
    if (response.status !== 'success') {
      throw new Error(response.message || 'Failed to remove part from project')
    }
  }

  async getProjectParts(projectId: string): Promise<Part[]> {
    const response = await apiClient.get<ApiResponse<{ parts: Part[] }>>(
      `/api/projects/${projectId}/parts`
    )
    if (response.status === 'success' && response.data) {
      return response.data.parts || []
    }
    return []
  }

  async getPartProjects(partId: string): Promise<Project[]> {
    const response = await apiClient.get<ApiResponse<ProjectsResponse>>(
      `/api/projects/parts/${partId}/projects`
    )
    if (response.status === 'success' && response.data) {
      return response.data.projects || []
    }
    return []
  }

  // Helper methods
  async checkNameExists(name: string, excludeId?: string): Promise<boolean> {
    try {
      const project = await this.getProject({ name })
      return project ? project.id !== excludeId : false
    } catch {
      return false
    }
  }

  sortProjectsByName(projects: Project[]): Project[] {
    return [...projects].sort((a, b) => a.name.localeCompare(b.name))
  }

  filterProjects(projects: Project[], searchTerm: string): Project[] {
    const term = searchTerm.toLowerCase()
    return projects.filter(
      (project) =>
        project.name.toLowerCase().includes(term) ||
        (project.description && project.description.toLowerCase().includes(term)) ||
        project.slug.toLowerCase().includes(term)
    )
  }

  getProjectsByStatus(projects: Project[], status: Project['status']): Project[] {
    return projects.filter((project) => project.status === status)
  }
}

export const projectsService = new ProjectsService()
