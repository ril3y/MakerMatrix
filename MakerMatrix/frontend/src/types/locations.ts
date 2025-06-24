export interface Location {
  id: string
  name: string
  description?: string
  parent_id?: string
  location_type: string
  image_url?: string
  emoji?: string
  parent?: Location
  children?: Location[]
  parts_count?: number
}

export interface CreateLocationRequest {
  name: string
  description?: string
  parent_id?: string
  location_type?: string
  image_url?: string
  emoji?: string
}

export interface UpdateLocationRequest {
  id: string
  name?: string
  description?: string
  parent_id?: string
  location_type?: string
  image_url?: string
  emoji?: string
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