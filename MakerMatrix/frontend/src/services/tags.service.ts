import type { ApiResponse, PaginatedResponse } from './api'
import { apiClient } from './api'
import type {
  Tag,
  CreateTagRequest,
  UpdateTagRequest,
  BulkAssignTagsRequest,
  BulkRemoveTagsRequest,
  TagStats,
  SearchTagsRequest,
} from '@/types/tags'
import type { Part } from '@/types/parts'
import type { Tool } from '@/types/tools'

export class TagsService {
  // === CRUD OPERATIONS ===

  async createTag(data: CreateTagRequest): Promise<Tag> {
    const response = await apiClient.post<ApiResponse<Tag>>('/api/tags', data)

    if (response.status === 'success' && response.data) {
      return response.data
    }
    throw new Error(response.message || 'Failed to create tag')
  }

  async getTag(id: string): Promise<Tag> {
    const response = await apiClient.get<ApiResponse<Tag>>(`/api/tags/${id}`)
    if (response.status === 'success' && response.data) {
      return response.data
    }
    throw new Error(response.message || 'Failed to get tag')
  }

  async updateTag(id: string, data: UpdateTagRequest): Promise<Tag> {
    const response = await apiClient.put<ApiResponse<Tag>>(`/api/tags/${id}`, data)
    if (response.status === 'success' && response.data) {
      return response.data
    }
    throw new Error(response.message || 'Failed to update tag')
  }

  async deleteTag(id: string): Promise<void> {
    const response = await apiClient.delete<ApiResponse>(`/api/tags/${id}`)
    if (response.status !== 'success') {
      throw new Error(response.message || 'Failed to delete tag')
    }
  }

  async getAllTags(params?: SearchTagsRequest): Promise<PaginatedResponse<Tag>> {
    const response = await apiClient.get<
      ApiResponse<{
        tags: Tag[]
        total: number
        page: number
        page_size: number
        total_pages: number
      }>
    >('/api/tags', {
      params: {
        search: params?.search,
        is_system_tag: params?.is_system_tag,
        entity_type: params?.entity_type,
        sort_by: params?.sort_by || 'name',
        sort_order: params?.sort_order || 'asc',
        page: params?.page || 1,
        page_size: params?.page_size || 100,
      },
    })

    if (response.status === 'success' && response.data) {
      // Backend returns data.tags, frontend expects items
      return {
        items: response.data.tags || [],
        total: response.data.total || 0,
        page: response.data.page || 1,
        page_size: response.data.page_size || 100,
        total_pages: response.data.total_pages || 1,
      }
    }

    throw new Error(response.message || 'Failed to get tags')
  }

  // === TAG ASSIGNMENT - PARTS ===

  async assignTagToPart(tagId: string, partId: string): Promise<void> {
    const response = await apiClient.post<ApiResponse>(`/api/tags/${tagId}/parts/${partId}`)
    if (response.status !== 'success') {
      throw new Error(response.message || 'Failed to assign tag to part')
    }
  }

  async removeTagFromPart(tagId: string, partId: string): Promise<void> {
    const response = await apiClient.delete<ApiResponse>(`/api/tags/${tagId}/parts/${partId}`)
    if (response.status !== 'success') {
      throw new Error(response.message || 'Failed to remove tag from part')
    }
  }

  async getPartTags(partId: string): Promise<Tag[]> {
    const response = await apiClient.get<ApiResponse<Tag[]>>(`/api/tags/parts/${partId}/tags`)
    if (response.status === 'success' && response.data) {
      return response.data
    }
    throw new Error(response.message || 'Failed to get part tags')
  }

  async getPartsWithTag(tagId: string, page = 1, pageSize = 20): Promise<PaginatedResponse<Part>> {
    const response = await apiClient.get<
      ApiResponse<{
        parts: Part[]
        total: number
        page: number
        page_size: number
        total_pages: number
      }>
    >(`/api/tags/${tagId}/parts`, {
      params: { page, page_size: pageSize },
    })

    if (response.status === 'success' && response.data) {
      return {
        items: response.data.parts || [],
        total: response.data.total || 0,
        page: response.data.page || 1,
        page_size: response.data.page_size || 20,
        total_pages: response.data.total_pages || 1,
      }
    }

    throw new Error(response.message || 'Failed to get parts with tag')
  }

  // === TAG ASSIGNMENT - TOOLS ===

  async assignTagToTool(tagId: string, toolId: string): Promise<void> {
    const response = await apiClient.post<ApiResponse>(`/api/tags/${tagId}/tools/${toolId}`)
    if (response.status !== 'success') {
      throw new Error(response.message || 'Failed to assign tag to tool')
    }
  }

  async removeTagFromTool(tagId: string, toolId: string): Promise<void> {
    const response = await apiClient.delete<ApiResponse>(`/api/tags/${tagId}/tools/${toolId}`)
    if (response.status !== 'success') {
      throw new Error(response.message || 'Failed to remove tag from tool')
    }
  }

  async getToolTags(toolId: string): Promise<Tag[]> {
    const response = await apiClient.get<ApiResponse<Tag[]>>(`/api/tags/tools/${toolId}/tags`)
    if (response.status === 'success' && response.data) {
      return response.data
    }
    throw new Error(response.message || 'Failed to get tool tags')
  }

  async getToolsWithTag(tagId: string, page = 1, pageSize = 20): Promise<PaginatedResponse<Tool>> {
    const response = await apiClient.get<
      ApiResponse<{
        tools: Tool[]
        total: number
        page: number
        page_size: number
        total_pages: number
      }>
    >(`/api/tags/${tagId}/tools`, {
      params: { page, page_size: pageSize },
    })

    if (response.status === 'success' && response.data) {
      return {
        items: response.data.tools || [],
        total: response.data.total || 0,
        page: response.data.page || 1,
        page_size: response.data.page_size || 20,
        total_pages: response.data.total_pages || 1,
      }
    }

    throw new Error(response.message || 'Failed to get tools with tag')
  }

  // === BULK OPERATIONS ===

  async bulkAssignTags(data: BulkAssignTagsRequest): Promise<void> {
    const response = await apiClient.post<ApiResponse>('/api/tags/bulk/assign', data)
    if (response.status !== 'success') {
      throw new Error(response.message || 'Failed to bulk assign tags')
    }
  }

  async bulkRemoveTags(data: BulkRemoveTagsRequest): Promise<void> {
    const response = await apiClient.post<ApiResponse>('/api/tags/bulk/remove', data)
    if (response.status !== 'success') {
      throw new Error(response.message || 'Failed to bulk remove tags')
    }
  }

  // === STATISTICS ===

  async getTagStats(): Promise<TagStats> {
    const response = await apiClient.get<ApiResponse<TagStats>>('/api/tags/stats')
    if (response.status === 'success' && response.data) {
      return response.data
    }
    throw new Error(response.message || 'Failed to get tag statistics')
  }

  // === HELPER METHODS ===

  async searchTags(query: string, limit = 10): Promise<Tag[]> {
    if (query.length < 1) {
      return []
    }

    try {
      const response = await this.getAllTags({
        search: query,
        page_size: limit,
        sort_by: 'usage',
        sort_order: 'desc',
      })
      return response.items || []
    } catch (error) {
      console.error('Error searching tags:', error)
      return []
    }
  }

  async checkTagExists(name: string, excludeId?: string): Promise<boolean> {
    try {
      const response = await this.getAllTags({ search: name, page_size: 100 })
      const tags = response.items || []
      const exactMatch = tags.find(
        (tag) =>
          tag.name.toLowerCase() === name.toLowerCase() && (!excludeId || tag.id !== excludeId)
      )
      return !!exactMatch
    } catch {
      return false
    }
  }
}

export const tagsService = new TagsService()
