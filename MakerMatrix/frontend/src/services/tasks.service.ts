import { apiClient } from './api'

export interface CreateTaskRequest {
  task_type: string
  name: string
  description?: string
  priority?: 'low' | 'normal' | 'high' | 'urgent'
  input_data?: any
  max_retries?: number
  timeout_seconds?: number
  scheduled_at?: string
  related_entity_type?: string
  related_entity_id?: string
  parent_task_id?: string
  depends_on_task_ids?: string[]
}

export interface Task {
  id: string
  task_type: string
  name: string
  description?: string
  status: 'pending' | 'running' | 'completed' | 'failed' | 'cancelled'
  priority: 'low' | 'normal' | 'high' | 'urgent'
  progress_percentage: number
  current_step?: string
  input_data?: any
  result_data?: any
  error_message?: string
  max_retries: number
  retry_count: number
  timeout_seconds?: number
  created_at: string
  scheduled_at?: string
  started_at?: string
  completed_at?: string
  created_by_user_id?: string
  related_entity_type?: string
  related_entity_id?: string
  parent_task_id?: string
  depends_on_task_ids: string[]
}

export interface WorkerStatus {
  is_running: boolean
  running_tasks_count: number
  running_task_ids: string[]
  registered_handlers: number
}

export interface TaskStats {
  total_tasks: number
  by_status: Record<string, number>
  by_type: Record<string, number>
  by_priority: Record<string, number>
  running_tasks: number
  failed_tasks: number
  completed_today: number
}

export interface TaskType {
  type: string
  name: string
  description: string
}

class TasksService {
  private baseUrl = '/api/tasks'

  // Custom task creation removed for security reasons
  // Use specific quick task creation methods instead

  async getTasks(params?: {
    status?: string[]
    task_type?: string[]
    priority?: string[]
    created_by_user_id?: string
    related_entity_type?: string
    related_entity_id?: string
    limit?: number
    offset?: number
    order_by?: string
    order_desc?: boolean
  }): Promise<{ status: string; data: Task[]; total: number }> {
    return apiClient.get(this.baseUrl, { params })
  }

  async getMyTasks(params?: {
    status?: string[]
    task_type?: string[]
    priority?: string[]
    limit?: number
    offset?: number
  }): Promise<{ status: string; data: Task[] }> {
    return apiClient.get(`${this.baseUrl}/my`, { params })
  }

  async getTask(taskId: string): Promise<{ status: string; data: Task }> {
    return apiClient.get(`${this.baseUrl}/${taskId}`)
  }

  async updateTask(taskId: string, updates: {
    status?: string
    progress_percentage?: number
    current_step?: string
    result_data?: any
    error_message?: string
  }): Promise<{ status: string; data: Task }> {
    return apiClient.put(`${this.baseUrl}/${taskId}`, updates)
  }

  async cancelTask(taskId: string): Promise<{ status: string; message: string }> {
    return apiClient.post(`${this.baseUrl}/${taskId}/cancel`)
  }

  async retryTask(taskId: string): Promise<{ status: string; message: string }> {
    return apiClient.post(`${this.baseUrl}/${taskId}/retry`)
  }

  async getAvailableTaskTypes(): Promise<{ status: string; data: TaskType[] }> {
    return apiClient.get(`${this.baseUrl}/types/available`)
  }

  async getTaskStats(): Promise<{ status: string; data: TaskStats }> {
    return apiClient.get(`${this.baseUrl}/stats/summary`)
  }

  async startWorker(): Promise<{ status: string; message: string }> {
    return apiClient.post(`${this.baseUrl}/worker/start`)
  }

  async stopWorker(): Promise<{ status: string; message: string }> {
    return apiClient.post(`${this.baseUrl}/worker/stop`)
  }

  async getWorkerStatus(): Promise<{ status: string; data: WorkerStatus }> {
    return apiClient.get(`${this.baseUrl}/worker/status`)
  }

  // Quick task creation methods  
  async createQuickTask(taskType: 'csv-enrichment' | 'price-update' | 'database-cleanup' | 'bulk-enrichment', data: any): Promise<{ status: string; data: Task }> {
    // Convert kebab-case to snake_case for backend
    const backendTaskType = taskType.replace(/-/g, '_')
    return apiClient.post(`${this.baseUrl}/quick/${backendTaskType}`, data)
  }

  async createCSVEnrichmentTask(enrichmentData: any): Promise<{ status: string; data: Task }> {
    return this.createQuickTask('csv-enrichment', enrichmentData)
  }

  async createPriceUpdateTask(updateData: any): Promise<{ status: string; data: Task }> {
    return this.createQuickTask('price-update', updateData)
  }

  async createDatabaseCleanupTask(cleanupOptions: any): Promise<{ status: string; data: Task }> {
    return this.createQuickTask('database-cleanup', cleanupOptions)
  }

  // New enrichment task creation methods
  async createPartEnrichmentTask(enrichmentData: {
    part_id: string
    supplier?: string
    capabilities?: string[]
    force_refresh?: boolean
  }): Promise<{ status: string; data: Task }> {
    return apiClient.post(`${this.baseUrl}/quick/part_enrichment`, enrichmentData)
  }

  async createDatasheetFetchTask(fetchData: {
    part_id?: string
    part_number?: string
    supplier: string
  }): Promise<{ status: string; data: Task }> {
    return apiClient.post(`${this.baseUrl}/quick/datasheet_fetch`, fetchData)
  }

  async createImageFetchTask(fetchData: {
    part_id?: string
    part_number?: string
    supplier: string
  }): Promise<{ status: string; data: Task }> {
    return apiClient.post(`${this.baseUrl}/quick/image_fetch`, fetchData)
  }

  async createBulkEnrichmentTask(enrichmentData: {
    part_ids: string[]
    supplier_filter?: string
    capabilities?: string[]
    batch_size?: number
  }): Promise<{ status: string; data: Task }> {
    return apiClient.post(`${this.baseUrl}/quick/bulk_enrichment`, enrichmentData)
  }

  async createFileImportEnrichmentTask(enrichmentData: {
    enrichment_queue: Array<{
      part_id: string
      part_data: any
    }>
    file_type?: string
    supplier?: string
  }): Promise<{ status: string; data: Task }> {
    return apiClient.post(`${this.baseUrl}/quick/file_import_enrichment`, enrichmentData)
  }

  // Supplier capabilities methods
  async getSupplierCapabilities(): Promise<{ status: string; data: Record<string, any> }> {
    return apiClient.get(`${this.baseUrl}/capabilities/suppliers`)
  }

  async getSupplierCapability(supplierName: string): Promise<{ status: string; data: any }> {
    return apiClient.get(`${this.baseUrl}/capabilities/suppliers/${supplierName}`)
  }

  async findSuppliersWithCapability(capabilityType: string): Promise<{ 
    status: string; 
    data: { capability: string; suppliers: string[]; count: number } 
  }> {
    return apiClient.get(`${this.baseUrl}/capabilities/find/${capabilityType}`)
  }

  // Task monitoring utilities
  pollTaskProgress(taskId: string, callback: (task: Task) => void, intervalMs: number = 1000): () => void {
    const poll = async () => {
      try {
        const response = await this.getTask(taskId)
        callback(response.data)
        
        // Stop polling if task is complete
        if (['completed', 'failed', 'cancelled'].includes(response.data.status)) {
          clearInterval(interval)
        }
      } catch (error) {
        console.error('Error polling task progress:', error)
      }
    }

    const interval = setInterval(poll, intervalMs)
    
    // Initial poll
    poll()
    
    // Return cleanup function
    return () => clearInterval(interval)
  }

  async waitForTaskCompletion(taskId: string, timeoutMs: number = 300000): Promise<Task> {
    return new Promise((resolve, reject) => {
      const startTime = Date.now()
      
      const cleanup = this.pollTaskProgress(taskId, (task) => {
        if (task.status === 'completed') {
          cleanup()
          resolve(task)
        } else if (task.status === 'failed') {
          cleanup()
          reject(new Error(task.error_message || 'Task failed'))
        } else if (task.status === 'cancelled') {
          cleanup()
          reject(new Error('Task was cancelled'))
        } else if (Date.now() - startTime > timeoutMs) {
          cleanup()
          reject(new Error('Task polling timeout'))
        }
      })
    })
  }

  // Batch operations
  async cancelMultipleTasks(taskIds: string[]): Promise<{ successful: string[]; failed: string[] }> {
    const results = await Promise.allSettled(
      taskIds.map(id => this.cancelTask(id))
    )
    
    const successful: string[] = []
    const failed: string[] = []
    
    results.forEach((result, index) => {
      if (result.status === 'fulfilled') {
        successful.push(taskIds[index])
      } else {
        failed.push(taskIds[index])
      }
    })
    
    return { successful, failed }
  }

  async retryMultipleTasks(taskIds: string[]): Promise<{ successful: string[]; failed: string[] }> {
    const results = await Promise.allSettled(
      taskIds.map(id => this.retryTask(id))
    )
    
    const successful: string[] = []
    const failed: string[] = []
    
    results.forEach((result, index) => {
      if (result.status === 'fulfilled') {
        successful.push(taskIds[index])
      } else {
        failed.push(taskIds[index])
      }
    })
    
    return { successful, failed }
  }

  // Task template helpers
  getTaskTemplates(): Record<string, CreateTaskRequest> {
    return {
      priceUpdate: {
        task_type: 'price_update',
        name: 'Price Update Task',
        description: 'Update part prices from supplier APIs',
        priority: 'normal'
      },
      databaseCleanup: {
        task_type: 'database_cleanup',
        name: 'Database Cleanup',
        description: 'Clean up orphaned records and optimize database',
        priority: 'low'
      },
      inventoryAudit: {
        task_type: 'inventory_audit',
        name: 'Inventory Audit',
        description: 'Audit inventory levels and generate reports',
        priority: 'normal'
      },
      partValidation: {
        task_type: 'part_validation',
        name: 'Part Validation',
        description: 'Validate part data integrity and consistency',
        priority: 'normal'
      },
      dataSync: {
        task_type: 'data_sync',
        name: 'Data Synchronization',
        description: 'Synchronize data with external services',
        priority: 'normal'
      },
      // New enrichment task templates
      partEnrichment: {
        task_type: 'part_enrichment',
        name: 'Part Enrichment',
        description: 'Enrich part data from supplier APIs',
        priority: 'normal'
      },
      datasheetFetch: {
        task_type: 'datasheet_fetch',
        name: 'Datasheet Fetch',
        description: 'Fetch datasheet for part from supplier',
        priority: 'normal'
      },
      imageFetch: {
        task_type: 'image_fetch',
        name: 'Image Fetch',
        description: 'Fetch product image from supplier',
        priority: 'normal'
      },
      bulkEnrichment: {
        task_type: 'bulk_enrichment',
        name: 'Bulk Enrichment',
        description: 'Enrich multiple parts from supplier APIs',
        priority: 'normal'
      },
      csvEnrichment: {
        task_type: 'csv_enrichment',
        name: 'CSV Import Enrichment (Deprecated)',
        description: 'Enrich parts imported from CSV files - Use File Import Enrichment instead',
        priority: 'normal'
      },
      fileImportEnrichment: {
        task_type: 'file_import_enrichment',
        name: 'File Import Enrichment',
        description: 'Enrich parts imported from files (CSV, XLS, etc.)',
        priority: 'normal'
      }
    }
  }
}

export const tasksService = new TasksService()