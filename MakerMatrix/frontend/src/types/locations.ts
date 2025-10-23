export interface Location {
  id: string
  name: string
  description?: string
  parent_id?: string
  location_type?: string // Optional to match parts.ts Location type
  image_url?: string
  emoji?: string

  // Container slot generation fields
  slot_count?: number
  slot_naming_pattern?: string
  slot_layout_type?: 'simple' | 'grid' | 'custom'
  grid_rows?: number
  grid_columns?: number
  slot_layout?: Record<string, unknown>

  // Per-slot identification
  is_auto_generated_slot?: boolean
  slot_number?: number
  slot_metadata?: Record<string, unknown>

  parent?: Location
  children?: Location[]
  parts_count?: number
  created_at?: string
  updated_at?: string
}

export interface CreateLocationRequest {
  name: string
  description?: string
  parent_id?: string
  location_type?: string
  image_url?: string
  emoji?: string

  // Container slot generation fields
  slot_count?: number
  slot_naming_pattern?: string
  slot_layout_type?: 'simple' | 'grid' | 'custom'
  grid_rows?: number
  grid_columns?: number
  slot_layout?: Record<string, unknown>

  // Index signature for base CRUD compatibility
  [key: string]: unknown
}

export interface UpdateLocationRequest {
  id: string
  name?: string
  description?: string
  parent_id?: string
  location_type?: string
  image_url?: string
  emoji?: string

  // Container slot generation fields (for updates)
  slot_count?: number
  slot_naming_pattern?: string
  slot_layout_type?: 'simple' | 'grid' | 'custom'
  grid_rows?: number
  grid_columns?: number
  slot_layout?: Record<string, unknown>

  // Index signature for base CRUD compatibility
  [key: string]: unknown
}

export interface LocationPath {
  id: string
  name: string
  parent?: LocationPath
}

export interface LocationDetails {
  location: Location
  children: Location[]
  parts_count: number
}

export interface LocationDeletePreview {
  location: Location
  children_count: number
  parts_count: number
  affected_parts: Array<{
    id: string
    part_name: string
    part_number?: string
  }>
}

export interface LocationDeleteResponse {
  deleted_location: Location
  deleted_children_count: number
  updated_parts_count: number
}

export interface LocationCleanupResponse {
  removed_locations: Location[]
  removed_count: number
}

// Container slot occupancy information
export interface SlotOccupancy {
  is_occupied: boolean
  part_count: number
  total_quantity: number
  parts: Array<{
    part_id: string
    part_name: string
    part_number?: string
    quantity: number
    is_primary: boolean
    description?: string
    image_url?: string
    category?: string
  }>
}

// Slot with occupancy data
export interface SlotWithOccupancy extends Location {
  occupancy?: SlotOccupancy
}
