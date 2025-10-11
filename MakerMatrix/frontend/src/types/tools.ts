// Tool condition enum
export type ToolCondition = 'new' | 'good' | 'fair' | 'poor' | 'broken'

// Tool status enum
export type ToolStatus = 'available' | 'checked_out' | 'maintenance' | 'retired'

// Base Tool interface
export interface Tool {
  id: string
  name: string
  tool_number?: string
  description?: string
  manufacturer?: string
  model?: string
  serial_number?: string
  purchase_date?: string
  purchase_price?: number
  condition: ToolCondition
  status: ToolStatus
  location_id?: string
  location?: {
    id: string
    name: string
    path?: string
  }
  category_id?: string
  category?: {
    id: string
    name: string
  }
  checked_out_by?: string
  checkout_date?: string
  expected_return_date?: string
  last_maintenance?: string
  next_maintenance?: string
  maintenance_notes?: string
  image_url?: string
  manual_url?: string
  notes?: string
  additional_properties?: Record<string, any>
  created_at: string
  updated_at: string
}

// Create tool request
export interface CreateToolRequest {
  name: string
  tool_number?: string
  description?: string
  manufacturer?: string
  model?: string
  serial_number?: string
  purchase_date?: string
  purchase_price?: number
  condition?: ToolCondition
  location_id?: string
  category_id?: string
  last_maintenance?: string
  next_maintenance?: string
  maintenance_notes?: string
  image_url?: string
  manual_url?: string
  notes?: string
  additional_properties?: Record<string, any>
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