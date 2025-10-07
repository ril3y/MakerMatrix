import { apiClient } from './api'

export interface LabelTemplate {
  id: string
  name: string
  display_name: string
  description: string
  category: string
  label_width_mm: number
  label_height_mm: number
  layout_type: string
  text_template: string
  text_rotation: string
  text_alignment: string
  qr_position: string
  qr_scale: number
  qr_enabled: boolean
  enable_multiline: boolean
  enable_auto_sizing: boolean
  font_config: Record<string, any>
  layout_config: Record<string, any>
  spacing_config: Record<string, any>
  is_system_template: boolean
  is_public: boolean
  usage_count: number
  created_at: string
  updated_at: string
}

export interface TemplateCategory {
  value: string
  label: string
  description: string
}

export interface TemplatePreviewRequest {
  template_id: string
  data: Record<string, any>
}

export interface TemplatePrintRequest {
  printer_id: string
  template_id: string
  data: Record<string, any>
  label_size: string
  copies?: number
}

class TemplateService {
  private baseUrl = '/api/templates'

  // Get all templates with optional filtering
  async getTemplates(
    params: {
      category?: string
      is_system?: boolean
      search?: string
      page?: number
      page_size?: number
    } = {}
  ): Promise<LabelTemplate[]> {
    try {
      const searchParams = new URLSearchParams()

      if (params.category) searchParams.append('category', params.category)
      if (params.is_system !== undefined)
        searchParams.append('is_system', params.is_system.toString())
      if (params.search) searchParams.append('search', params.search)
      if (params.page) searchParams.append('page', params.page.toString())
      if (params.page_size) searchParams.append('page_size', params.page_size.toString())

      const url = searchParams.toString() ? `${this.baseUrl}/?${searchParams}` : `${this.baseUrl}/`
      console.log('Fetching templates from:', url)
      const response = await apiClient.get(url)
      console.log('Template API response:', response)

      if (response.status === 'success') {
        // Backend returns { templates: [], total_count: number }
        const data = response.data

        // Check if data has templates property (new backend format)
        if (data && typeof data === 'object' && 'templates' in data) {
          const templates = data.templates
          console.log(`Successfully fetched ${templates.length} templates`)
          return templates
        }

        // Fallback: check if data is array directly (legacy format)
        if (Array.isArray(data)) {
          console.log(`Successfully fetched ${data.length} templates`)
          return data
        }

        console.warn('Template API returned unexpected data format:', data)
        return []
      }

      // If not success, return empty array instead of throwing
      console.warn('Failed to fetch templates:', response.message, response)
      return []
    } catch (error: any) {
      console.error('Error fetching templates:', error)
      console.error('Error details:', error.response?.data || error.message)
      // Return empty array on error instead of throwing
      return []
    }
  }

  // Get system templates (pre-designed templates)
  async getSystemTemplates(): Promise<LabelTemplate[]> {
    return this.getTemplates({ is_system: true })
  }

  // Get user templates
  async getUserTemplates(): Promise<LabelTemplate[]> {
    return this.getTemplates({ is_system: false })
  }

  // Get template by ID
  async getTemplate(id: string): Promise<LabelTemplate> {
    const response = await apiClient.get(`${this.baseUrl}/${id}`)

    if (response.status === 'success') {
      return response.data
    }
    throw new Error(response.message || 'Failed to fetch template')
  }

  // Create new template
  async createTemplate(template: Partial<LabelTemplate>): Promise<LabelTemplate> {
    const response = await apiClient.post(`${this.baseUrl}/`, template)

    if (response.status === 'success') {
      return response.data
    }
    throw new Error(response.message || 'Failed to create template')
  }

  // Update template
  async updateTemplate(id: string, template: Partial<LabelTemplate>): Promise<LabelTemplate> {
    const response = await apiClient.put(`${this.baseUrl}/${id}`, template)

    if (response.status === 'success') {
      return response.data
    }
    throw new Error(response.message || 'Failed to update template')
  }

  // Delete template
  async deleteTemplate(id: string): Promise<void> {
    const response = await apiClient.delete(`${this.baseUrl}/${id}`)

    if (response.status !== 'success') {
      throw new Error(response.message || 'Failed to delete template')
    }
  }

  // Duplicate template
  async duplicateTemplate(id: string): Promise<LabelTemplate> {
    const response = await apiClient.post(`${this.baseUrl}/${id}/duplicate`)

    if (response.status === 'success') {
      return response.data
    }
    throw new Error(response.message || 'Failed to duplicate template')
  }

  // Get template categories
  async getCategories(): Promise<TemplateCategory[]> {
    const response = await apiClient.get(`${this.baseUrl}/categories`)

    if (response.status === 'success') {
      return response.data || []
    }
    throw new Error(response.message || 'Failed to fetch categories')
  }

  // Search templates
  async searchTemplates(query: string): Promise<LabelTemplate[]> {
    const response = await apiClient.post(`${this.baseUrl}/search/`, { query })

    if (response.status === 'success') {
      return response.data || []
    }
    throw new Error(response.message || 'Failed to search templates')
  }

  // Get compatible templates for a specific label height
  async getCompatibleTemplates(labelHeightMm: number): Promise<LabelTemplate[]> {
    const response = await apiClient.get(`${this.baseUrl}/compatible/${labelHeightMm}`)

    if (response.status === 'success') {
      return response.data || []
    }
    throw new Error(response.message || 'Failed to fetch compatible templates')
  }

  // Preview template with data
  async previewTemplate(request: TemplatePreviewRequest): Promise<Blob> {
    const response = await fetch('/api/printer/preview/template', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${localStorage.getItem('access_token')}`,
      },
      body: JSON.stringify(request),
    })

    if (!response.ok) {
      const errorData = await response.json()
      throw new Error(errorData.message || 'Failed to generate template preview')
    }

    // Backend returns JSON with {status, data: {preview_url, width, height}}
    const jsonResponse = await response.json()
    if (jsonResponse.status === 'success' && jsonResponse.data?.preview_url) {
      // Convert base64 data URL to Blob
      const base64Data = jsonResponse.data.preview_url
      const response = await fetch(base64Data)
      return response.blob()
    }

    throw new Error('Invalid preview response format')
  }

  // Print using template
  async printTemplate(request: TemplatePrintRequest): Promise<any> {
    const response = await apiClient.post('/api/printer/print/template', request)

    if (response.status === 'success') {
      return response.data
    }
    throw new Error(response.message || 'Failed to print template')
  }

  // Get template usage suggestions based on part data
  getTemplateSuggestions(
    partData: Record<string, any>,
    templates: LabelTemplate[]
  ): LabelTemplate[] {
    // Prioritize system templates that match the use case
    const suggestions = templates.filter((t) => t.is_system_template)

    // Sort by relevance based on part data
    return suggestions.sort((a, b) => {
      let scoreA = 0
      let scoreB = 0

      // Prefer templates that have fields matching the available data
      const dataKeys = Object.keys(partData)

      if (a.text_template) {
        dataKeys.forEach((key) => {
          if (a.text_template.includes(`{${key}}`)) scoreA++
        })
      }

      if (b.text_template) {
        dataKeys.forEach((key) => {
          if (b.text_template.includes(`{${key}}`)) scoreB++
        })
      }

      return scoreB - scoreA
    })
  }
}

export const templateService = new TemplateService()
