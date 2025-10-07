export interface Project {
  id: string
  name: string
  slug: string
  description?: string
  status: 'planning' | 'active' | 'completed' | 'archived'
  image_url?: string
  links?: Record<string, unknown>
  project_metadata?: Record<string, unknown>
  parts_count: number
  estimated_cost?: number
  created_at: string
  updated_at: string
  completed_at?: string
}

export interface ProjectCreate {
  name: string
  slug?: string
  description?: string
  status?: 'planning' | 'active' | 'completed' | 'archived'
  image_url?: string
  links?: Record<string, unknown>
  project_metadata?: Record<string, unknown>
}

export interface ProjectUpdate {
  name?: string
  slug?: string
  description?: string
  status?: 'planning' | 'active' | 'completed' | 'archived'
  image_url?: string
  links?: Record<string, unknown>
  project_metadata?: Record<string, unknown>
  estimated_cost?: number
  completed_at?: string
}

export interface ProjectsResponse {
  projects: Project[]
}

export interface ProjectPartAssociation {
  part_id: string
  project_id: string
  notes?: string
}
