export interface Datasheet {
  id: string
  part_id: string
  file_uuid: string
  original_filename?: string
  file_extension: string
  file_size?: number
  source_url?: string
  supplier?: string
  manufacturer?: string
  title?: string
  description?: string
  created_at: string
  updated_at: string
  is_downloaded: boolean
  download_error?: string
  filename: string
}

export interface Part {
  id: string
  name: string
  part_number?: string
  supplier_part_number?: string  // Supplier's part number (different from our internal part_number)
  description?: string
  quantity: number
  minimum_quantity?: number
  supplier?: string
  supplier_url?: string
  product_url?: string
  image_url?: string
  emoji?: string
  manufacturer?: string
  manufacturer_part_number?: string
  component_type?: string
  additional_properties?: Record<string, unknown>
  location_id?: string
  location?: Location
  categories?: Category[]
  projects?: Project[]
  datasheets?: Datasheet[]
  created_at: string
  updated_at: string
  // Allocation fields (optional, loaded from backend when needed)
  total_quantity?: number
  location_count?: number
  primary_location?: Location
  lifecycle_status?: string
}

export interface Location {
  id: string
  name: string
  description?: string
  location_type?: string
  type?: string // Keep for backward compatibility
  parent_id?: string
  parent?: Location
  children?: Location[]
  part_count?: number
  created_at?: string
  updated_at?: string
}

export interface Category {
  id: string
  name: string
  created_at?: string
  updated_at?: string
}

export interface Project {
  id: string
  name: string
  description?: string
  status?: string
  image_url?: string
  links?: Record<string, string>
  created_at?: string
  updated_at?: string
}

export interface CreatePartRequest {
  name: string
  part_number?: string
  description?: string
  quantity: number
  minimum_quantity?: number
  supplier?: string
  supplier_url?: string
  product_url?: string
  supplier_part_number?: string
  image_url?: string
  emoji?: string
  manufacturer?: string
  manufacturer_part_number?: string
  component_type?: string
  additional_properties?: Record<string, unknown>
  location_id?: string
  categories?: string[]
}

export interface UpdatePartRequest extends Partial<CreatePartRequest> {
  id: string
}

export interface SearchPartsRequest {
  search_term?: string
  query?: string // Keep for backward compatibility
  category?: string
  location_id?: string
  min_quantity?: number
  max_quantity?: number
  supplier?: string
  sort_by?: string
  sort_order?: 'asc' | 'desc'
  page?: number
  page_size?: number
}

export interface CreateLocationRequest {
  name: string
  type?: string
  parent_id?: string
}

export interface UpdateLocationRequest extends Partial<CreateLocationRequest> {
  id: string
}

export interface CreateCategoryRequest {
  name: string
}

export interface UpdateCategoryRequest {
  id: string
  name: string
}
