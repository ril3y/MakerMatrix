import { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import { 
  TrendingUp, 
  TrendingDown, 
  DollarSign, 
  Package, 
  AlertTriangle,
  Calendar,
  Filter,
  Download,
  RefreshCw,
  ChevronUp,
  ChevronDown
} from 'lucide-react'
import { analyticsService } from '@/services/analytics.service'
import { Line, Bar, Doughnut } from 'react-chartjs-2'
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  ArcElement,
  Title,
  Tooltip,
  Legend,
  Filler
} from 'chart.js'
import toast from 'react-hot-toast'

// Register ChartJS components
ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  ArcElement,
  Title,
  Tooltip,
  Legend,
  Filler
)

interface DashboardSummary {
  period: {
    start_date: string
    end_date: string
  }
  spending_by_supplier: Array<{
    supplier: string
    total_spent: number
    order_count: number
  }>
  spending_trend: Array<{
    period: string
    total_spent: number
    order_count: number
  }>
  frequent_parts: Array<{
    part_id: number
    name: string
    part_number: string
    current_quantity: number
    total_orders: number
    average_price: number
    last_order_date: string | null
  }>
  low_stock_count: number
  low_stock_parts: Array<{
    part_id: number
    name: string
    part_number: string
    current_quantity: number
    minimum_quantity: number | null
    average_order_quantity: number
    suggested_reorder_quantity: number
    last_order_date: string | null
    total_orders: number
  }>
  inventory_value: {
    total_value: number
    priced_parts: number
    unpriced_parts: number
    total_units: number
  }
  category_spending: Array<{
    category: string
    total_spent: number
    unique_parts: number
  }>
}

const AnalyticsDashboard = () => {
  const [loading, setLoading] = useState(true)
  const [summary, setSummary] = useState<DashboardSummary | null>(null)
  const [selectedPeriod, setSelectedPeriod] = useState('30')
  const [expandedSections, setExpandedSections] = useState({
    spending: true,
    inventory: true,
    trends: true,
    alerts: true
  })

  useEffect(() => {
    loadDashboardData()
  }, [selectedPeriod])

  const loadDashboardData = async () => {
    try {
      setLoading(true)
      const data = await analyticsService.getDashboardSummary()
      setSummary(data)
    } catch (error) {
      toast.error('Failed to load analytics data')
    } finally {
      setLoading(false)
    }
  }

  const toggleSection = (section: keyof typeof expandedSections) => {
    setExpandedSections(prev => ({
      ...prev,
      [section]: !prev[section]
    }))
  }

  const formatCurrency = (value: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 0,
      maximumFractionDigits: 2
    }).format(value)
  }

  const formatDate = (dateString: string | null) => {
    if (!dateString) return 'N/A'
    return new Date(dateString).toLocaleDateString()
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary"></div>
      </div>
    )
  }

  if (!summary) {
    return (
      <div className="text-center py-8">
        <p className="text-secondary">No analytics data available</p>
      </div>
    )
  }

  // Prepare chart data
  const spendingTrendData = {
    labels: summary.spending_trend.map(item => new Date(item.period).toLocaleDateString()),
    datasets: [
      {
        label: 'Total Spent',
        data: summary.spending_trend.map(item => item.total_spent),
        borderColor: 'rgb(99, 102, 241)',
        backgroundColor: 'rgba(99, 102, 241, 0.1)',
        fill: true,
        tension: 0.4
      }
    ]
  }

  const supplierSpendingData = {
    labels: summary.spending_by_supplier.map(item => item.supplier),
    datasets: [
      {
        data: summary.spending_by_supplier.map(item => item.total_spent),
        backgroundColor: [
          'rgba(99, 102, 241, 0.8)',
          'rgba(239, 68, 68, 0.8)',
          'rgba(34, 197, 94, 0.8)',
          'rgba(251, 191, 36, 0.8)',
          'rgba(168, 85, 247, 0.8)'
        ],
        borderWidth: 0
      }
    ]
  }

  const categorySpendingData = {
    labels: summary.category_spending.slice(0, 5).map(item => item.category),
    datasets: [
      {
        label: 'Spending by Category',
        data: summary.category_spending.slice(0, 5).map(item => item.total_spent),
        backgroundColor: 'rgba(99, 102, 241, 0.8)',
        borderColor: 'rgba(99, 102, 241, 1)',
        borderWidth: 1
      }
    ]
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <motion.div
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        className="flex items-center justify-between"
      >
        <div>
          <h1 className="text-2xl font-bold text-primary flex items-center gap-2">
            <TrendingUp className="w-6 h-6" />
            Analytics Dashboard
          </h1>
          <p className="text-secondary mt-1">
            Period: {formatDate(summary.period.start_date)} - {formatDate(summary.period.end_date)}
          </p>
        </div>
        <div className="flex gap-2">
          <select
            className="input"
            value={selectedPeriod}
            onChange={(e) => setSelectedPeriod(e.target.value)}
          >
            <option value="7">Last 7 days</option>
            <option value="30">Last 30 days</option>
            <option value="90">Last 90 days</option>
            <option value="365">Last year</option>
          </select>
          <button
            onClick={loadDashboardData}
            className="btn btn-secondary flex items-center gap-2"
          >
            <RefreshCw className="w-4 h-4" />
            Refresh
          </button>
          <button className="btn btn-primary flex items-center gap-2">
            <Download className="w-4 h-4" />
            Export
          </button>
        </div>
      </motion.div>

      {/* Key Metrics Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="card p-6"
        >
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-secondary">Total Inventory Value</p>
              <p className="text-2xl font-bold text-primary">
                {formatCurrency(summary.inventory_value.total_value)}
              </p>
              <p className="text-xs text-muted mt-1">
                {summary.inventory_value.priced_parts} priced parts
              </p>
            </div>
            <DollarSign className="w-8 h-8 text-primary opacity-20" />
          </div>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.15 }}
          className="card p-6"
        >
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-secondary">Low Stock Alerts</p>
              <p className="text-2xl font-bold text-error">
                {summary.low_stock_count}
              </p>
              <p className="text-xs text-muted mt-1">
                Parts below threshold
              </p>
            </div>
            <AlertTriangle className="w-8 h-8 text-error opacity-20" />
          </div>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
          className="card p-6"
        >
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-secondary">Total Units</p>
              <p className="text-2xl font-bold text-primary">
                {(summary.inventory_value.total_units ?? 0).toLocaleString()}
              </p>
              <p className="text-xs text-muted mt-1">
                Across all parts
              </p>
            </div>
            <Package className="w-8 h-8 text-primary opacity-20" />
          </div>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.25 }}
          className="card p-6"
        >
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-secondary">Suppliers</p>
              <p className="text-2xl font-bold text-primary">
                {summary.spending_by_supplier.length}
              </p>
              <p className="text-xs text-muted mt-1">
                Active suppliers
              </p>
            </div>
            <TrendingUp className="w-8 h-8 text-primary opacity-20" />
          </div>
        </motion.div>
      </div>

      {/* Spending Analysis Section */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.3 }}
        className="card"
      >
        <div 
          className="p-4 border-b border-border flex items-center justify-between cursor-pointer"
          onClick={() => toggleSection('spending')}
        >
          <h2 className="text-lg font-semibold text-primary flex items-center gap-2">
            <DollarSign className="w-5 h-5" />
            Spending Analysis
          </h2>
          {expandedSections.spending ? <ChevronUp /> : <ChevronDown />}
        </div>
        
        {expandedSections.spending && (
          <div className="p-6 grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Spending Trend Chart */}
            <div>
              <h3 className="text-md font-medium text-primary mb-4">Spending Trend</h3>
              <div className="h-64">
                <Line 
                  data={spendingTrendData} 
                  options={{
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                      legend: {
                        display: false
                      }
                    },
                    scales: {
                      y: {
                        beginAtZero: true,
                        ticks: {
                          callback: function(value) {
                            return '$' + (value ?? 0).toLocaleString()
                          }
                        }
                      }
                    }
                  }}
                />
              </div>
            </div>

            {/* Supplier Spending Chart */}
            <div>
              <h3 className="text-md font-medium text-primary mb-4">Spending by Supplier</h3>
              <div className="h-64">
                <Doughnut 
                  data={supplierSpendingData}
                  options={{
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                      legend: {
                        position: 'right',
                        labels: {
                          padding: 10,
                          usePointStyle: true
                        }
                      }
                    }
                  }}
                />
              </div>
            </div>

            {/* Category Spending */}
            <div className="lg:col-span-2">
              <h3 className="text-md font-medium text-primary mb-4">Top Categories by Spending</h3>
              <div className="h-64">
                <Bar
                  data={categorySpendingData}
                  options={{
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                      legend: {
                        display: false
                      }
                    },
                    scales: {
                      y: {
                        beginAtZero: true,
                        ticks: {
                          callback: function(value) {
                            return '$' + (value ?? 0).toLocaleString()
                          }
                        }
                      }
                    }
                  }}
                />
              </div>
            </div>
          </div>
        )}
      </motion.div>

      {/* Inventory Insights Section */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.35 }}
        className="card"
      >
        <div 
          className="p-4 border-b border-border flex items-center justify-between cursor-pointer"
          onClick={() => toggleSection('inventory')}
        >
          <h2 className="text-lg font-semibold text-primary flex items-center gap-2">
            <Package className="w-5 h-5" />
            Inventory Insights
          </h2>
          {expandedSections.inventory ? <ChevronUp /> : <ChevronDown />}
        </div>
        
        {expandedSections.inventory && (
          <div className="p-6">
            {/* Most Frequently Ordered Parts */}
            <div className="mb-6">
              <h3 className="text-md font-medium text-primary mb-4">Most Frequently Ordered Parts</h3>
              <div className="overflow-x-auto">
                <table className="table w-full">
                  <thead>
                    <tr>
                      <th>Part Name</th>
                      <th>Part Number</th>
                      <th>Current Stock</th>
                      <th>Total Orders</th>
                      <th>Avg Price</th>
                      <th>Last Order</th>
                    </tr>
                  </thead>
                  <tbody>
                    {summary.frequent_parts.map((part) => (
                      <tr key={part.part_id}>
                        <td className="font-medium text-primary">{part.name}</td>
                        <td className="text-secondary">{part.part_number}</td>
                        <td className="text-secondary">{part.current_quantity}</td>
                        <td className="text-secondary">{part.total_orders}</td>
                        <td className="text-secondary">{formatCurrency(part.average_price)}</td>
                        <td className="text-secondary">{formatDate(part.last_order_date)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>

            {/* Low Stock Alerts */}
            {summary.low_stock_count > 0 && (
              <div>
                <h3 className="text-md font-medium text-primary mb-4 flex items-center gap-2">
                  <AlertTriangle className="w-4 h-4 text-error" />
                  Low Stock Alerts
                </h3>
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                  {summary.low_stock_parts.map((part) => (
                    <div key={part.part_id} className="bg-error/5 border border-error/20 rounded-lg p-4">
                      <h4 className="font-medium text-primary">{part.name}</h4>
                      <p className="text-sm text-secondary mb-2">{part.part_number}</p>
                      <div className="space-y-1 text-sm">
                        <div className="flex justify-between">
                          <span className="text-muted">Current:</span>
                          <span className="text-error font-medium">{part.current_quantity}</span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-muted">Avg Order:</span>
                          <span className="text-secondary">{Math.round(part.average_order_quantity)}</span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-muted">Suggested:</span>
                          <span className="text-success font-medium">{part.suggested_reorder_quantity}</span>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </motion.div>
    </div>
  )
}

export default AnalyticsDashboard