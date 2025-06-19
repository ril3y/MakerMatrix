/**
 * Rate Limiting Service
 * 
 * Provides API access to rate limiting usage statistics and monitoring.
 */

import { apiClient } from './api';

export interface RateLimitUsage {
  per_minute: number;
  per_hour: number;
  per_day: number;
}

export interface RateLimitInfo {
  per_minute: number;
  per_hour: number;
  per_day: number;
}

export interface UsagePercentage {
  per_minute: number;
  per_hour: number;
  per_day: number;
}

export interface RateLimitStatus {
  allowed: boolean;
  supplier_name: string;
  current_usage: RateLimitUsage;
  limits: RateLimitInfo;
  usage_percentage: UsagePercentage;
  violations?: string[];
  retry_after_seconds?: number;
}

export interface SupplierUsageStats {
  supplier_name: string;
  total_requests: number;
  successful_requests: number;
  failed_requests: number;
  success_rate: number;
  avg_response_time_ms?: number;
  endpoint_breakdown: Record<string, number>;
}

export interface SupplierRateLimitData {
  supplier_name: string;
  enabled: boolean;
  limits: RateLimitInfo;
  current_usage: RateLimitUsage;
  usage_percentage: UsagePercentage;
  stats_24h: SupplierUsageStats;
}

export interface RateLimitSummary {
  total_suppliers: number;
  suppliers_with_usage: number;
  total_requests_24h: number;
  approaching_limits: Array<{
    supplier: string;
    period: string;
    usage_percentage: number;
  }>;
  suppliers: SupplierRateLimitData[];
}

class RateLimitService {
  /**
   * Get rate limit usage for all suppliers
   */
  async getAllSupplierUsage(): Promise<SupplierRateLimitData[]> {
    try {
      const response = await apiClient.get('/api/rate-limits/suppliers');
      return response.data || [];
    } catch (error) {
      console.error('Failed to get supplier usage:', error);
      throw error;
    }
  }

  /**
   * Get detailed usage for a specific supplier
   */
  async getSupplierUsage(supplierName: string, timePeriod: string = '24h'): Promise<{
    supplier_name: string;
    rate_limit_status: RateLimitStatus;
    usage_statistics: SupplierUsageStats;
  }> {
    try {
      const response = await apiClient.get(`/api/rate-limits/suppliers/${supplierName}?time_period=${timePeriod}`);
      return response.data;
    } catch (error) {
      console.error(`Failed to get usage for ${supplierName}:`, error);
      throw error;
    }
  }

  /**
   * Get current rate limit status for a supplier (for real-time monitoring)
   */
  async getSupplierRateLimitStatus(supplierName: string): Promise<RateLimitStatus> {
    try {
      const response = await apiClient.get(`/api/rate-limits/suppliers/${supplierName}/status`);
      return response.data;
    } catch (error) {
      console.error(`Failed to get rate limit status for ${supplierName}:`, error);
      throw error;
    }
  }

  /**
   * Get summary of rate limiting across all suppliers
   */
  async getRateLimitSummary(): Promise<RateLimitSummary> {
    try {
      const response = await apiClient.get('/api/rate-limits/summary');
      return response.data;
    } catch (error) {
      console.error('Failed to get rate limit summary:', error);
      throw error;
    }
  }

  /**
   * Initialize default rate limits
   */
  async initializeDefaultLimits(): Promise<void> {
    try {
      await apiClient.post('/api/rate-limits/initialize');
    } catch (error) {
      console.error('Failed to initialize rate limits:', error);
      throw error;
    }
  }

  /**
   * Format usage percentage for display
   */
  formatUsagePercentage(percentage: number): string {
    return `${Math.round(percentage)}%`;
  }

  /**
   * Get status color based on usage percentage
   */
  getUsageColor(percentage: number): string {
    if (percentage >= 90) return 'text-red-600 dark:text-red-400';
    if (percentage >= 75) return 'text-yellow-600 dark:text-yellow-400';
    if (percentage >= 50) return 'text-blue-600 dark:text-blue-400';
    return 'text-green-600 dark:text-green-400';
  }

  /**
   * Get status icon based on usage percentage
   */
  getUsageIcon(percentage: number): '🔴' | '🟡' | '🔵' | '🟢' {
    if (percentage >= 90) return '🔴';
    if (percentage >= 75) return '🟡';
    if (percentage >= 50) return '🔵';
    return '🟢';
  }

  /**
   * Format time until reset
   */
  formatTimeUntilReset(resetTime: string): string {
    const reset = new Date(resetTime);
    const now = new Date();
    const diffMs = reset.getTime() - now.getTime();
    
    if (diffMs <= 0) return 'Now';
    
    const hours = Math.floor(diffMs / (1000 * 60 * 60));
    const minutes = Math.floor((diffMs % (1000 * 60 * 60)) / (1000 * 60));
    
    if (hours > 0) return `${hours}h ${minutes}m`;
    return `${minutes}m`;
  }
}

export const rateLimitService = new RateLimitService();