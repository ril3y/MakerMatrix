// Tool condition enum (matches backend validation)
export type ToolCondition =
  | 'excellent'
  | 'good'
  | 'fair'
  | 'poor'
  | 'needs_repair'
  | 'out_of_service'

// Tool status enum
export type ToolStatus = 'available' | 'checked_out' | 'maintenance' | 'retired'

// Base Tool interface (matches backend ToolResponse)
export interface Tool {
  id: string
  tool_name: string
  tool_number?: string
  description?: string
  manufacturer?: string
  model_number?: string
  tool_type?: string

  supplier?: string
  supplier_part_number?: string
  supplier_url?: string
  product_url?: string

  image_url?: string
  emoji?: string

  additional_properties?: Record<string, unknown>

  condition: ToolCondition
  last_maintenance_date?: string
  next_maintenance_date?: string
  maintenance_notes?: string

  is_checked_out: boolean
  checked_out_by?: string
  checked_out_at?: string
  expected_return_date?: string

  purchase_date?: string
  purchase_price?: number
  current_value?: number

  is_checkable: boolean
  is_calibrated_tool: boolean
  is_consumable: boolean
  exclude_from_analytics: boolean

  quantity: number
  location?: {
    id: string
    name: string
    path?: string
  }
  location_id?: string
  categories?: Array<{
    id: string
    name: string
  }>
  tags?: Array<{
    id: string
    name: string
    color?: string
    icon?: string
  }>

  created_at: string
  updated_at: string
}

// Create tool request (matches backend ToolCreateRequest)
export interface CreateToolRequest {
  tool_name: string
  tool_number?: string
  description?: string
  manufacturer?: string
  model_number?: string
  tool_type?: string
  supplier?: string
  supplier_part_number?: string
  supplier_url?: string
  product_url?: string
  image_url?: string
  emoji?: string
  additional_properties?: Record<string, unknown>
  condition?: ToolCondition
  is_checkable?: boolean
  is_calibrated_tool?: boolean
  is_consumable?: boolean
  purchase_date?: string
  purchase_price?: number
  location_id?: string
  quantity?: number
  category_ids?: string[]
}

// Update tool request
export interface UpdateToolRequest extends Partial<CreateToolRequest> {
  condition?: ToolCondition
  status?: ToolStatus
}

// Search tools request
export interface SearchToolsRequest {
  search_term?: string
  condition?: ToolCondition
  status?: ToolStatus
  category_id?: string
  location_id?: string
  checked_out?: boolean
  sort_by?: 'name' | 'tool_number' | 'condition' | 'status' | 'created_at' | 'updated_at'
  sort_order?: 'asc' | 'desc'
  page?: number
  page_size?: number
}

// Checkout/checkin history
export interface ToolHistory {
  id: string
  tool_id: string
  user_id: string
  user?: {
    id: string
    username: string
  }
  action: 'checkout' | 'checkin' | 'maintenance' | 'condition_change'
  timestamp: string
  notes?: string
  previous_value?: string
  new_value?: string
}

// Maintenance record
export interface ToolMaintenanceRecord {
  id: string
  tool_id: string
  maintenance_date: string
  maintenance_type: string
  performed_by: string
  notes?: string
  next_maintenance_date?: string
  cost?: number
  created_at: string
  updated_at?: string
}

// Paginated response for tools
export interface ToolsPaginatedResponse {
  tools: Tool[]
  total: number
  page: number
  page_size: number
  total_pages: number
}
