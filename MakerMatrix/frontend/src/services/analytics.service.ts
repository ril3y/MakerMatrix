import { apiClient, ApiResponse } from './api'

export interface SpendingBySupplier {
  supplier: string
  total_spent: number
  order_count: number
}

export interface SpendingTrend {
  period: string
  total_spent: number
  order_count: number
}

export interface PartOrderFrequency {
  part_id: number
  name: string
  part_number: string
  current_quantity: number
  total_orders: number
  average_price: number
  last_order_date: string | null
}

export interface PriceTrend {
  part_id: number
  part_name: string
  part_number: string
  unit_price: number
  order_date: string
  supplier: string
}

export interface LowStockPart {
  part_id: number
  name: string
  part_number: string
  current_quantity: number
  minimum_quantity: number | null
  average_order_quantity: number
  suggested_reorder_quantity: number
  last_order_date: string | null
  total_orders: number
}

export interface InventoryValue {
  total_value: number
  priced_parts: number
  unpriced_parts: number
  total_units: number
}

export interface CategorySpending {
  category: string
  total_spent: number
  unique_parts: number
}

export interface DashboardSummary {
  period: {
    start_date: string
    end_date: string
  }
  spending_by_supplier: SpendingBySupplier[]
  spending_trend: SpendingTrend[]
  frequent_parts: PartOrderFrequency[]
  low_stock_count: number
  low_stock_parts: LowStockPart[]
  inventory_value: InventoryValue
  category_spending: CategorySpending[]
}

export interface AnalyticsParams {
  start_date?: string
  end_date?: string
  limit?: number
  period?: 'day' | 'week' | 'month' | 'year'
  lookback_periods?: number
  min_orders?: number
  part_id?: string | number
  supplier?: string
  threshold_multiplier?: number
}

class AnalyticsService {
  async getSpendingBySupplier(params?: AnalyticsParams): Promise<SpendingBySupplier[]> {
    const queryParams = new URLSearchParams()
    if (params?.start_date) queryParams.append('start_date', params.start_date)
    if (params?.end_date) queryParams.append('end_date', params.end_date)
    if (params?.limit) queryParams.append('limit', params.limit.toString())
    
    const response = await apiClient.get<ApiResponse<SpendingBySupplier[]>>(`/api/analytics/spending/by-supplier?${queryParams}`)
    return response.data || []
  }

  async getSpendingTrend(params?: AnalyticsParams): Promise<SpendingTrend[]> {
    const queryParams = new URLSearchParams()
    if (params?.period) queryParams.append('period', params.period)
    if (params?.lookback_periods) queryParams.append('lookback_periods', params.lookback_periods.toString())
    
    const response = await apiClient.get<ApiResponse<SpendingTrend[]>>(`/api/analytics/spending/trend?${queryParams}`)
    return response.data || []
  }

  async getPartOrderFrequency(params?: AnalyticsParams): Promise<PartOrderFrequency[]> {
    const queryParams = new URLSearchParams()
    if (params?.limit) queryParams.append('limit', params.limit.toString())
    if (params?.min_orders) queryParams.append('min_orders', params.min_orders.toString())
    
    const response = await apiClient.get<ApiResponse<PartOrderFrequency[]>>(`/api/analytics/parts/order-frequency?${queryParams}`)
    return response.data || []
  }

  async getPriceTrends(params?: AnalyticsParams): Promise<PriceTrend[]> {
    const queryParams = new URLSearchParams()
    if (params?.part_id) queryParams.append('part_id', params.part_id.toString())
    if (params?.supplier) queryParams.append('supplier', params.supplier)
    if (params?.limit) queryParams.append('limit', params.limit.toString())
    
    const response = await apiClient.get<ApiResponse<PriceTrend[]>>(`/api/analytics/prices/trends?${queryParams}`)
    return response.data || []
  }

  async getLowStockParts(params?: AnalyticsParams): Promise<LowStockPart[]> {
    const queryParams = new URLSearchParams()
    if (params?.threshold_multiplier) queryParams.append('threshold_multiplier', params.threshold_multiplier.toString())
    
    const response = await apiClient.get<ApiResponse<LowStockPart[]>>(`/api/analytics/inventory/low-stock?${queryParams}`)
    return response.data || []
  }

  async getCategorySpending(params?: AnalyticsParams): Promise<CategorySpending[]> {
    const queryParams = new URLSearchParams()
    if (params?.start_date) queryParams.append('start_date', params.start_date)
    if (params?.end_date) queryParams.append('end_date', params.end_date)
    
    const response = await apiClient.get<ApiResponse<CategorySpending[]>>(`/api/analytics/spending/by-category?${queryParams}`)
    return response.data || []
  }

  async getInventoryValue(): Promise<InventoryValue> {
    const response = await apiClient.get<ApiResponse<InventoryValue>>(`/api/analytics/inventory/value`)
    return response.data || { total_value: 0, priced_parts: 0, unpriced_parts: 0, total_units: 0 }
  }

  async getDashboardSummary(): Promise<DashboardSummary> {
    const response = await apiClient.get<ApiResponse<DashboardSummary>>(`/api/analytics/dashboard/summary`)
    return response.data as DashboardSummary
  }
}

export const analyticsService = new AnalyticsService()