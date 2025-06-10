export interface Category {
  id: string
  name: string
  description?: string
}

export interface CreateCategoryRequest {
  name: string
  description?: string
}

export interface UpdateCategoryRequest {
  id: string
  name?: string
  description?: string
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