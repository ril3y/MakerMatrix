import { describe, it, expect, vi, beforeEach } from 'vitest'
import { tagsService } from '../tags.service'
import { apiClient } from '../api'
import type { Tag, CreateTagRequest, UpdateTagRequest } from '@/types/tags'

// Mock the API client
vi.mock('../api', () => ({
  apiClient: {
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
    delete: vi.fn(),
  },
}))

const mockTag: Tag = {
  id: 'tag-1',
  name: 'testing',
  color: '#3B82F6',
  icon: '🧪',
  description: 'For testing purposes',
  is_system_tag: false,
  created_by: 'user-1',
  created_at: '2025-01-01T00:00:00Z',
  updated_at: '2025-01-01T00:00:00Z',
  parts_count: 5,
  tools_count: 3,
}

describe('TagsService', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('createTag', () => {
    it('creates a tag successfully', async () => {
      const createData: CreateTagRequest = {
        name: 'testing',
        color: '#3B82F6',
        icon: '🧪',
        description: 'For testing purposes',
      }

      vi.mocked(apiClient.post).mockResolvedValue({
        status: 'success',
        data: mockTag,
        message: 'Tag created',
      })

      const result = await tagsService.createTag(createData)

      expect(apiClient.post).toHaveBeenCalledWith('/api/tags', createData)
      expect(result).toEqual(mockTag)
    })

    it('throws error on failure', async () => {
      vi.mocked(apiClient.post).mockResolvedValue({
        status: 'error',
        message: 'Failed to create tag',
      })

      await expect(tagsService.createTag({ name: 'test' })).rejects.toThrow('Failed to create tag')
    })
  })

  describe('getTag', () => {
    it('gets a tag by id', async () => {
      vi.mocked(apiClient.get).mockResolvedValue({
        status: 'success',
        data: mockTag,
        message: 'Success',
      })

      const result = await tagsService.getTag('tag-1')

      expect(apiClient.get).toHaveBeenCalledWith('/api/tags/tag-1')
      expect(result).toEqual(mockTag)
    })

    it('throws error when tag not found', async () => {
      vi.mocked(apiClient.get).mockResolvedValue({
        status: 'error',
        message: 'Tag not found',
      })

      await expect(tagsService.getTag('invalid-id')).rejects.toThrow('Tag not found')
    })
  })

  describe('updateTag', () => {
    it('updates a tag successfully', async () => {
      const updateData: UpdateTagRequest = {
        name: 'updated-testing',
        color: '#10B981',
      }

      const updatedTag = { ...mockTag, ...updateData }

      vi.mocked(apiClient.put).mockResolvedValue({
        status: 'success',
        data: updatedTag,
        message: 'Tag updated',
      })

      const result = await tagsService.updateTag('tag-1', updateData)

      expect(apiClient.put).toHaveBeenCalledWith('/api/tags/tag-1', updateData)
      expect(result).toEqual(updatedTag)
    })
  })

  describe('deleteTag', () => {
    it('deletes a tag successfully', async () => {
      vi.mocked(apiClient.delete).mockResolvedValue({
        status: 'success',
        message: 'Tag deleted',
      })

      await tagsService.deleteTag('tag-1')

      expect(apiClient.delete).toHaveBeenCalledWith('/api/tags/tag-1')
    })

    it('throws error on failure', async () => {
      vi.mocked(apiClient.delete).mockResolvedValue({
        status: 'error',
        message: 'Cannot delete system tag',
      })

      await expect(tagsService.deleteTag('tag-1')).rejects.toThrow('Cannot delete system tag')
    })
  })

  describe('getAllTags', () => {
    it('gets all tags with pagination', async () => {
      const mockTags = [mockTag]

      vi.mocked(apiClient.get).mockResolvedValue({
        status: 'success',
        data: {
          tags: mockTags,
          total: 1,
          page: 1,
          page_size: 100,
          total_pages: 1,
        },
        message: 'Success',
      })

      const result = await tagsService.getAllTags()

      expect(apiClient.get).toHaveBeenCalledWith('/api/tags', {
        params: {
          search: undefined,
          is_system_tag: undefined,
          entity_type: undefined,
          sort_by: 'name',
          sort_order: 'asc',
          page: 1,
          page_size: 100,
        },
      })

      expect(result).toEqual({
        items: mockTags,
        total: 1,
        page: 1,
        page_size: 100,
        total_pages: 1,
      })
    })

    it('accepts search parameters', async () => {
      vi.mocked(apiClient.get).mockResolvedValue({
        status: 'success',
        data: {
          tags: [],
          total: 0,
          page: 1,
          page_size: 20,
          total_pages: 0,
        },
        message: 'Success',
      })

      await tagsService.getAllTags({
        search: 'test',
        is_system_tag: false,
        entity_type: 'parts',
        sort_by: 'usage',
        sort_order: 'desc',
        page: 2,
        page_size: 20,
      })

      expect(apiClient.get).toHaveBeenCalledWith('/api/tags', {
        params: {
          search: 'test',
          is_system_tag: false,
          entity_type: 'parts',
          sort_by: 'usage',
          sort_order: 'desc',
          page: 2,
          page_size: 20,
        },
      })
    })
  })

  describe('assignTagToPart', () => {
    it('assigns a tag to a part', async () => {
      vi.mocked(apiClient.post).mockResolvedValue({
        status: 'success',
        message: 'Tag assigned',
      })

      await tagsService.assignTagToPart('tag-1', 'part-1')

      expect(apiClient.post).toHaveBeenCalledWith('/api/tags/tag-1/parts/part-1')
    })
  })

  describe('removeTagFromPart', () => {
    it('removes a tag from a part', async () => {
      vi.mocked(apiClient.delete).mockResolvedValue({
        status: 'success',
        message: 'Tag removed',
      })

      await tagsService.removeTagFromPart('tag-1', 'part-1')

      expect(apiClient.delete).toHaveBeenCalledWith('/api/tags/tag-1/parts/part-1')
    })
  })

  describe('getPartTags', () => {
    it('gets all tags for a part', async () => {
      const mockTags = [mockTag]

      vi.mocked(apiClient.get).mockResolvedValue({
        status: 'success',
        data: mockTags,
        message: 'Success',
      })

      const result = await tagsService.getPartTags('part-1')

      expect(apiClient.get).toHaveBeenCalledWith('/api/parts/part-1/tags')
      expect(result).toEqual(mockTags)
    })
  })

  describe('assignTagToTool', () => {
    it('assigns a tag to a tool', async () => {
      vi.mocked(apiClient.post).mockResolvedValue({
        status: 'success',
        message: 'Tag assigned',
      })

      await tagsService.assignTagToTool('tag-1', 'tool-1')

      expect(apiClient.post).toHaveBeenCalledWith('/api/tags/tag-1/tools/tool-1')
    })
  })

  describe('removeTagFromTool', () => {
    it('removes a tag from a tool', async () => {
      vi.mocked(apiClient.delete).mockResolvedValue({
        status: 'success',
        message: 'Tag removed',
      })

      await tagsService.removeTagFromTool('tag-1', 'tool-1')

      expect(apiClient.delete).toHaveBeenCalledWith('/api/tags/tag-1/tools/tool-1')
    })
  })

  describe('getToolTags', () => {
    it('gets all tags for a tool', async () => {
      const mockTags = [mockTag]

      vi.mocked(apiClient.get).mockResolvedValue({
        status: 'success',
        data: mockTags,
        message: 'Success',
      })

      const result = await tagsService.getToolTags('tool-1')

      expect(apiClient.get).toHaveBeenCalledWith('/api/tools/tool-1/tags')
      expect(result).toEqual(mockTags)
    })
  })

  describe('bulkAssignTags', () => {
    it('bulk assigns tags to parts and tools', async () => {
      const bulkData = {
        tag_ids: ['tag-1', 'tag-2'],
        part_ids: ['part-1', 'part-2'],
        tool_ids: ['tool-1'],
      }

      vi.mocked(apiClient.post).mockResolvedValue({
        status: 'success',
        message: 'Tags assigned',
      })

      await tagsService.bulkAssignTags(bulkData)

      expect(apiClient.post).toHaveBeenCalledWith('/api/tags/bulk/assign', bulkData)
    })
  })

  describe('bulkRemoveTags', () => {
    it('bulk removes tags from parts and tools', async () => {
      const bulkData = {
        tag_ids: ['tag-1', 'tag-2'],
        part_ids: ['part-1', 'part-2'],
      }

      vi.mocked(apiClient.post).mockResolvedValue({
        status: 'success',
        message: 'Tags removed',
      })

      await tagsService.bulkRemoveTags(bulkData)

      expect(apiClient.post).toHaveBeenCalledWith('/api/tags/bulk/remove', bulkData)
    })
  })

  describe('getTagStats', () => {
    it('gets tag statistics', async () => {
      const mockStats = {
        total_tags: 10,
        total_system_tags: 3,
        total_user_tags: 7,
        most_used_tags: [],
        recent_tags: [],
        tags_by_entity_type: {
          parts: 50,
          tools: 25,
        },
      }

      vi.mocked(apiClient.get).mockResolvedValue({
        status: 'success',
        data: mockStats,
        message: 'Success',
      })

      const result = await tagsService.getTagStats()

      expect(apiClient.get).toHaveBeenCalledWith('/api/tags/stats')
      expect(result).toEqual(mockStats)
    })
  })

  describe('searchTags', () => {
    it('searches for tags', async () => {
      const mockTags = [mockTag]

      vi.mocked(apiClient.get).mockResolvedValue({
        status: 'success',
        data: {
          tags: mockTags,
          total: 1,
          page: 1,
          page_size: 10,
          total_pages: 1,
        },
        message: 'Success',
      })

      const result = await tagsService.searchTags('test', 10)

      expect(result).toEqual(mockTags)
    })

    it('returns empty array for short queries', async () => {
      const result = await tagsService.searchTags('', 10)
      expect(result).toEqual([])
      expect(apiClient.get).not.toHaveBeenCalled()
    })

    it('returns empty array on error', async () => {
      vi.mocked(apiClient.get).mockRejectedValue(new Error('Network error'))

      const result = await tagsService.searchTags('test', 10)
      expect(result).toEqual([])
    })
  })

  describe('checkTagExists', () => {
    it('returns true when tag exists', async () => {
      vi.mocked(apiClient.get).mockResolvedValue({
        status: 'success',
        data: {
          tags: [mockTag],
          total: 1,
          page: 1,
          page_size: 100,
          total_pages: 1,
        },
        message: 'Success',
      })

      const result = await tagsService.checkTagExists('testing')
      expect(result).toBe(true)
    })

    it('returns false when tag does not exist', async () => {
      vi.mocked(apiClient.get).mockResolvedValue({
        status: 'success',
        data: {
          tags: [],
          total: 0,
          page: 1,
          page_size: 100,
          total_pages: 0,
        },
        message: 'Success',
      })

      const result = await tagsService.checkTagExists('nonexistent')
      expect(result).toBe(false)
    })

    it('excludes specified tag id from check', async () => {
      vi.mocked(apiClient.get).mockResolvedValue({
        status: 'success',
        data: {
          tags: [mockTag],
          total: 1,
          page: 1,
          page_size: 100,
          total_pages: 1,
        },
        message: 'Success',
      })

      const result = await tagsService.checkTagExists('testing', 'tag-1')
      expect(result).toBe(false) // Excluded, so returns false
    })

    it('returns false on error', async () => {
      vi.mocked(apiClient.get).mockRejectedValue(new Error('Network error'))

      const result = await tagsService.checkTagExists('testing')
      expect(result).toBe(false)
    })
  })
})
