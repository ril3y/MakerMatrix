// Tag entity type (matches backend TagResponse)
export interface Tag {
  id: string
  name: string // Tag name without # prefix
  color?: string // Hex color for badge (e.g., "#3B82F6")
  icon?: string // Optional emoji icon
  description?: string
  is_system_tag: boolean // Protected from deletion
  created_by: string
  created_at: string
  updated_at: string
  parts_count: number // Usage tracking
  tools_count: number
  last_used_at?: string
}

// Create tag request (matches backend TagCreateRequest)
export interface CreateTagRequest {
  name: string
  color?: string
  icon?: string
  description?: string
}

// Update tag request (matches backend TagUpdateRequest)
export interface UpdateTagRequest {
  name?: string
  color?: string
  icon?: string
  description?: string
}

// Bulk tag assignment request
export interface BulkAssignTagsRequest {
  tag_ids: string[]
  part_ids?: string[]
  tool_ids?: string[]
}

// Bulk tag removal request
export interface BulkRemoveTagsRequest {
  tag_ids: string[]
  part_ids?: string[]
  tool_ids?: string[]
}

// Tag statistics
export interface TagStats {
  total_tags: number
  total_system_tags: number
  total_user_tags: number
  most_used_tags: Array<{
    tag: Tag
    usage_count: number
  }>
  recent_tags: Tag[]
  tags_by_entity_type: {
    parts: number
    tools: number
  }
}

// Search/filter parameters for tags
export interface SearchTagsRequest {
  search?: string
  is_system_tag?: boolean
  entity_type?: 'parts' | 'tools'
  sort_by?: 'name' | 'created_at' | 'usage' | 'last_used'
  sort_order?: 'asc' | 'desc'
  page?: number
  page_size?: number
}
