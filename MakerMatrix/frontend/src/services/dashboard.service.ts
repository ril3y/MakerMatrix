/**
 * Dashboard Service - Fetches dashboard analytics data
 */

import type { ApiResponse } from './api'
import { apiClient } from './api'

interface InventorySummary {
  total_parts: number
  total_units: number
  total_categories: number
  total_locations: number
  parts_with_location: number
  parts_without_location: number
  low_stock_count: number
  zero_stock_count: number
}

interface CategoryDistribution {
  category: string
  part_count: number
  total_quantity: number
}

interface LocationDistribution {
  location: string
  part_count: number
  total_quantity: number
}

interface SupplierDistribution {
  supplier: string
  part_count: number
  total_quantity: number
}

interface StockedPart {
  id: string
  part_name: string
  part_number: string
  quantity: number
  supplier: string
  location: string
}

interface LowStockPart {
  id: string
  part_name: string
  part_number: string
  quantity: number
  supplier: string
  location_name: string
}

export interface DashboardData {
  summary: InventorySummary
  parts_by_category: CategoryDistribution[]
  parts_by_location: LocationDistribution[]
  parts_by_supplier: SupplierDistribution[]
  most_stocked_parts: StockedPart[]
  least_stocked_parts: StockedPart[]
  low_stock_parts: LowStockPart[]
}

export class DashboardService {
  /**
   * Get complete dashboard summary with all analytics
   */
  async getDashboardSummary(): Promise<DashboardData> {
    const response = await apiClient.get<ApiResponse<DashboardData>>('/api/dashboard/summary')
    if (!response.data) {
      throw new Error('Dashboard data is missing from API response')
    }
    return response.data
  }
}

export const dashboardService = new DashboardService()
