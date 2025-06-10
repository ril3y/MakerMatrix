export interface Part {
  id: string
  name: string
  part_number?: string
  quantity: number
  minimum_quantity?: number
  supplier?: string
  supplier_url?: string
  properties?: Record<string, any>
  location_id?: string
  location?: Location
  categories?: Category[]
  created_at: string
  updated_at: string
}

export interface Location {
  id: string
  name: string
  type?: string
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

export interface CreatePartRequest {
  name: string
  part_number?: string
  quantity: number
  minimum_quantity?: number
  supplier?: string
  supplier_url?: string
  properties?: Record<string, any>
  location_id?: string
  categories?: string[]
}

export interface UpdatePartRequest extends Partial<CreatePartRequest> {
  id: string
}

export interface SearchPartsRequest {
  query?: string
  category?: string
  location_id?: string
  min_quantity?: number
  max_quantity?: number
  supplier?: string
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