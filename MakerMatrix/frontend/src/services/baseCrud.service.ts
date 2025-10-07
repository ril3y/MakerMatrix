import { apiClient, ApiResponse } from './api'

export interface BaseEntity {
  id: string
  created_at?: string
  updated_at?: string
}

export interface CreateRequest {
  [key: string]: any
}

export interface UpdateRequest {
  id: string
  [key: string]: any
}

export interface PaginatedParams {
  page?: number
  pageSize?: number
  [key: string]: any
}

export interface PaginatedResponse<T> {
  data: T[]
  total: number
  page: number
  pageSize: number
  totalPages: number
}

export abstract class BaseCrudService<
  TEntity extends BaseEntity,
  TCreateRequest extends CreateRequest,
  TUpdateRequest extends UpdateRequest,
> {
  protected abstract baseUrl: string
  protected abstract entityName: string // For error messages

  // Abstract methods that must be implemented by subclasses
  protected abstract mapCreateRequestToBackend(data: TCreateRequest): any
  protected abstract mapUpdateRequestToBackend(data: TUpdateRequest): any
  protected abstract mapResponseToEntity(response: any): TEntity

  // Generic CRUD operations
  async getAll(): Promise<TEntity[]> {
    try {
      const response = await apiClient.get<ApiResponse<TEntity[]>>(
        `${this.baseUrl}/get_all_${this.entityName}s`
      )
      if (response.status === 'success' && response.data) {
        return response.data.map((item) => this.mapResponseToEntity(item))
      }
      return []
    } catch (error: any) {
      throw new Error(error.message || `Failed to load ${this.entityName}s`)
    }
  }

  async getAllPaginated(params: PaginatedParams = {}): Promise<PaginatedResponse<TEntity>> {
    try {
      const { page = 1, pageSize = 20, ...filters } = params
      const response = await apiClient.get<ApiResponse<TEntity[]>>(
        `${this.baseUrl}/get_all_${this.entityName}s`,
        {
          params: { page, page_size: pageSize, ...filters },
        }
      )

      if (response.status === 'success' && response.data) {
        const mappedData = response.data.map((item) => this.mapResponseToEntity(item))
        const totalPages = Math.ceil((response.total_parts || 0) / pageSize)

        return {
          data: mappedData,
          total: response.total_parts || 0,
          page,
          pageSize,
          totalPages,
        }
      }

      return {
        data: [],
        total: 0,
        page: 1,
        pageSize: 20,
        totalPages: 0,
      }
    } catch (error: any) {
      throw new Error(error.message || `Failed to load ${this.entityName}s`)
    }
  }

  async getById(id: string): Promise<TEntity> {
    try {
      const response = await apiClient.get<ApiResponse<TEntity>>(
        `${this.baseUrl}/get_${this.entityName}?${this.entityName}_id=${id}`
      )
      if (response.status === 'success' && response.data) {
        return this.mapResponseToEntity(response.data)
      }
      throw new Error(`${this.entityName} not found`)
    } catch (error: any) {
      throw new Error(error.message || `Failed to get ${this.entityName}`)
    }
  }

  async create(data: TCreateRequest): Promise<TEntity> {
    try {
      const backendData = this.mapCreateRequestToBackend(data)
      const response = await apiClient.post<ApiResponse<TEntity>>(
        `${this.baseUrl}/add_${this.entityName}`,
        backendData
      )

      if (response.status === 'success' && response.data) {
        return this.mapResponseToEntity(response.data)
      }
      throw new Error(response.message || `Failed to create ${this.entityName}`)
    } catch (error: any) {
      throw new Error(error.message || `Failed to create ${this.entityName}`)
    }
  }

  async update(data: TUpdateRequest): Promise<TEntity> {
    try {
      const { id, ...updateData } = data
      const backendData = this.mapUpdateRequestToBackend(updateData as TUpdateRequest)
      const response = await apiClient.put<ApiResponse<TEntity>>(
        `${this.baseUrl}/update_${this.entityName}/${id}`,
        backendData
      )

      if (response.status === 'success' && response.data) {
        return this.mapResponseToEntity(response.data)
      }
      throw new Error(response.message || `Failed to update ${this.entityName}`)
    } catch (error: any) {
      throw new Error(error.message || `Failed to update ${this.entityName}`)
    }
  }

  async delete(id: string): Promise<void> {
    try {
      const response = await apiClient.delete<ApiResponse>(
        `${this.baseUrl}/delete_${this.entityName}?${this.entityName}_id=${id}`
      )
      if (response.status !== 'success') {
        throw new Error(response.message || `Failed to delete ${this.entityName}`)
      }
    } catch (error: any) {
      throw new Error(error.message || `Failed to delete ${this.entityName}`)
    }
  }

  // Helper methods for common operations
  protected buildQueryParams(params: Record<string, any>): string {
    const searchParams = new URLSearchParams()
    Object.entries(params).forEach(([key, value]) => {
      if (value !== undefined && value !== null) {
        searchParams.append(key, String(value))
      }
    })
    return searchParams.toString()
  }

  protected async handleResponse<T>(response: ApiResponse<T>): Promise<T> {
    if (response.status === 'success' && response.data) {
      return response.data
    }
    throw new Error(response.message || 'Operation failed')
  }

  // Validation helpers
  protected validateId(id: string): void {
    if (!id || id.trim().length === 0) {
      throw new Error(`${this.entityName} ID is required`)
    }
  }

  protected validateCreateData(data: TCreateRequest): void {
    if (!data || typeof data !== 'object') {
      throw new Error(`Invalid ${this.entityName} data`)
    }
  }

  protected validateUpdateData(data: TUpdateRequest): void {
    if (!data || typeof data !== 'object') {
      throw new Error(`Invalid ${this.entityName} data`)
    }
    if (!data.id) {
      throw new Error(`${this.entityName} ID is required for updates`)
    }
  }
}

// Specialized base class for services that need name-based lookups
export abstract class BaseNamedCrudService<
  TEntity extends BaseEntity & { name: string },
  TCreateRequest extends CreateRequest,
  TUpdateRequest extends UpdateRequest,
> extends BaseCrudService<TEntity, TCreateRequest, TUpdateRequest> {
  async getByName(name: string): Promise<TEntity> {
    try {
      const response = await apiClient.get<ApiResponse<TEntity>>(
        `${this.baseUrl}/get_${this.entityName}?name=${encodeURIComponent(name)}`
      )
      if (response.status === 'success' && response.data) {
        return this.mapResponseToEntity(response.data)
      }
      throw new Error(`${this.entityName} not found`)
    } catch (error: any) {
      throw new Error(error.message || `Failed to get ${this.entityName}`)
    }
  }

  async checkNameExists(name: string, excludeId?: string): Promise<boolean> {
    try {
      const entity = await this.getByName(name)
      return entity ? entity.id !== excludeId : false
    } catch {
      return false
    }
  }

  // Delete by name (for services that support it)
  async deleteByName(name: string): Promise<void> {
    try {
      const response = await apiClient.delete<ApiResponse>(
        `${this.baseUrl}/remove_${this.entityName}?name=${encodeURIComponent(name)}`
      )
      if (response.status !== 'success') {
        throw new Error(response.message || `Failed to delete ${this.entityName}`)
      }
    } catch (error: any) {
      throw new Error(error.message || `Failed to delete ${this.entityName}`)
    }
  }
}

// Utility type for consistent service interfaces
export interface CrudServiceInterface<
  TEntity extends BaseEntity,
  TCreateRequest extends CreateRequest,
  TUpdateRequest extends UpdateRequest,
> {
  getAll(): Promise<TEntity[]>
  getAllPaginated(params?: PaginatedParams): Promise<PaginatedResponse<TEntity>>
  getById(id: string): Promise<TEntity>
  create(data: TCreateRequest): Promise<TEntity>
  update(data: TUpdateRequest): Promise<TEntity>
  delete(id: string): Promise<void>
}
