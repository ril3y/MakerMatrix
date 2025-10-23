export interface Category {
  id: string
  name: string
  description?: string
  part_count?: number
  created_at?: string
  updated_at?: string
  [key: string]: unknown
}

export interface CreateCategoryRequest {
  name: string
  description?: string
  [key: string]: unknown
}

export interface UpdateCategoryRequest {
  id: string
  name?: string
  description?: string
  parent_id?: string | null
  [key: string]: unknown
}

export interface CategoryResponse {
  category: Category
}

export interface CategoriesListResponse {
  categories: Category[]
}

export interface DeleteCategoriesResponse {
  deleted_count: number
}
