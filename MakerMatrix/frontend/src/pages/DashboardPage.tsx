import { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import {
  Package,
  AlertTriangle,
  MapPin,
  Tag,
  TrendingUp,
  TrendingDown,
  RefreshCw,
  ChevronUp,
  ChevronDown,
  BarChart3
} from 'lucide-react'
import { analyticsService } from '@/services/analytics.service'
import { Bar, Doughnut } from 'react-chartjs-2'
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  BarElement,
  ArcElement,
  Title,
  Tooltip,
  Legend
} from 'chart.js'
import toast from 'react-hot-toast'

// Register ChartJS components
ChartJS.register(
  CategoryScale,
  LinearScale,
  BarElement,
  ArcElement,
  Title,
  Tooltip,
  Legend
)

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

interface DashboardData {
  summary: InventorySummary
  parts_by_category: CategoryDistribution[]
  parts_by_location: LocationDistribution[]
  most_stocked_parts: StockedPart[]
  least_stocked_parts: StockedPart[]
  low_stock_parts: LowStockPart[]
}

const DashboardPage = () => {
  const [loading, setLoading] = useState(true)
  const [data, setData] = useState<DashboardData | null>(null)
  const [expandedSections, setExpandedSections] = useState({
    distribution: true,
    topParts: true,
    alerts: true
  })

  useEffect(() => {
    loadDashboardData()
  }, [])

  const loadDashboardData = async () => {
    try {
      setLoading(true)
      const response = await analyticsService.getDashboardSummary()
      setData(response)
    } catch (error) {
      toast.error('Failed to load dashboard data')
      console.error('Dashboard error:', error)
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

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary"></div>
      </div>
    )
  }

  if (!data) {
    return (
      <div className="text-center py-8">
        <p className="text-secondary">No dashboard data available</p>
      </div>
    )
  }

  // Prepare chart data
  const categoryChartData = {
    labels: data.parts_by_category.length > 0
      ? data.parts_by_category.slice(0, 10).map(item => item.category)
      : ['No Data'],
    datasets: [
      {
        label: 'Parts Count',
        data: data.parts_by_category.length > 0
          ? data.parts_by_category.slice(0, 10).map(item => item.part_count)
          : [0],
        backgroundColor: 'rgba(99, 102, 241, 0.8)',
        borderColor: 'rgba(99, 102, 241, 1)',
        borderWidth: 1
      }
    ]
  }

  const locationChartData = {
    labels: data.parts_by_location.length > 0
      ? data.parts_by_location.slice(0, 8).map(item => item.location)
      : ['No Data'],
    datasets: [
      {
        data: data.parts_by_location.length > 0
          ? data.parts_by_location.slice(0, 8).map(item => item.part_count)
          : [0],
        backgroundColor: [
          'rgba(99, 102, 241, 0.8)',
          'rgba(239, 68, 68, 0.8)',
          'rgba(34, 197, 94, 0.8)',
          'rgba(251, 191, 36, 0.8)',
          'rgba(168, 85, 247, 0.8)',
          'rgba(236, 72, 153, 0.8)',
          'rgba(14, 165, 233, 0.8)',
          'rgba(132, 204, 22, 0.8)'
        ],
        borderWidth: 0
      }
    ]
  }

  return (
    <div className="max-w-screen-2xl space-y-6">
      {/* Header */}
      <motion.div
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        className="flex items-center justify-between"
      >
        <div>
          <h1 className="text-2xl font-bold text-primary flex items-center gap-2">
            <BarChart3 className="w-6 h-6" />
            Dashboard
          </h1>
          <p className="text-secondary mt-1">
            Overview of your inventory
          </p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={loadDashboardData}
            className="btn btn-secondary flex items-center gap-2"
          >
            <RefreshCw className="w-4 h-4" />
            Refresh
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
              <p className="text-sm text-secondary">Total Parts</p>
              <p className="text-2xl font-bold text-primary">
                {data.summary.total_parts.toLocaleString()}
              </p>
              <p className="text-xs text-muted mt-1">
                {data.summary.total_units.toLocaleString()} total units
              </p>
            </div>
            <Package className="w-8 h-8 text-primary opacity-20" />
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
                {data.summary.low_stock_count}
              </p>
              <p className="text-xs text-muted mt-1">
                Parts below 10 units
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
              <p className="text-sm text-secondary">Categories</p>
              <p className="text-2xl font-bold text-primary">
                {data.summary.total_categories}
              </p>
              <p className="text-xs text-muted mt-1">
                Active categories
              </p>
            </div>
            <Tag className="w-8 h-8 text-primary opacity-20" />
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
              <p className="text-sm text-secondary">Locations</p>
              <p className="text-2xl font-bold text-primary">
                {data.summary.total_locations}
              </p>
              <p className="text-xs text-muted mt-1">
                {data.summary.parts_with_location} parts located
              </p>
            </div>
            <MapPin className="w-8 h-8 text-primary opacity-20" />
          </div>
        </motion.div>
      </div>

      {/* Distribution Charts Section */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.3 }}
        className="card"
      >
        <div
          className="p-4 border-b border-border flex items-center justify-between cursor-pointer"
          onClick={() => toggleSection('distribution')}
        >
          <h2 className="text-lg font-semibold text-primary flex items-center gap-2">
            <BarChart3 className="w-5 h-5" />
            Parts Distribution
          </h2>
          {expandedSections.distribution ? <ChevronUp /> : <ChevronDown />}
        </div>

        {expandedSections.distribution && (
          <div className="p-6 grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Categories Chart */}
            <div>
              <h3 className="text-md font-medium text-primary mb-4">By Category</h3>
              <div className="h-64">
                {data.parts_by_category.length > 0 ? (
                  <Bar
                    data={categoryChartData}
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
                            precision: 0
                          }
                        }
                      }
                    }}
                  />
                ) : (
                  <div className="flex items-center justify-center h-full text-muted">
                    No category data available
                  </div>
                )}
              </div>
            </div>

            {/* Locations Chart */}
            <div>
              <h3 className="text-md font-medium text-primary mb-4">By Location</h3>
              <div className="h-64">
                {data.parts_by_location.length > 0 ? (
                  <Doughnut
                    data={locationChartData}
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
                ) : (
                  <div className="flex items-center justify-center h-full text-muted">
                    No location data available
                  </div>
                )}
              </div>
            </div>
          </div>
        )}
      </motion.div>

      {/* Top Parts Section */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.35 }}
        className="card"
      >
        <div
          className="p-4 border-b border-border flex items-center justify-between cursor-pointer"
          onClick={() => toggleSection('topParts')}
        >
          <h2 className="text-lg font-semibold text-primary flex items-center gap-2">
            <Package className="w-5 h-5" />
            Stock Levels
          </h2>
          {expandedSections.topParts ? <ChevronUp /> : <ChevronDown />}
        </div>

        {expandedSections.topParts && (
          <div className="p-6 grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Most Stocked */}
            <div>
              <h3 className="text-md font-medium text-primary mb-4 flex items-center gap-2">
                <TrendingUp className="w-4 h-4 text-success" />
                Most Stocked Parts
              </h3>
              <div className="overflow-x-auto">
                <table className="table w-full">
                  <thead>
                    <tr>
                      <th>Part Name</th>
                      <th>Quantity</th>
                      <th>Location</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.most_stocked_parts.length > 0 ? (
                      data.most_stocked_parts.map((part) => (
                        <tr key={part.id}>
                          <td>
                            <div>
                              <div className="font-medium text-primary">{part.part_name}</div>
                              <div className="text-xs text-muted">{part.part_number}</div>
                            </div>
                          </td>
                          <td className="font-semibold text-success">{part.quantity.toLocaleString()}</td>
                          <td className="text-secondary text-sm">{part.location}</td>
                        </tr>
                      ))
                    ) : (
                      <tr>
                        <td colSpan={3} className="text-center text-muted py-4">
                          No parts available
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
            </div>

            {/* Least Stocked */}
            <div>
              <h3 className="text-md font-medium text-primary mb-4 flex items-center gap-2">
                <TrendingDown className="w-4 h-4 text-warning" />
                Least Stocked Parts
              </h3>
              <div className="overflow-x-auto">
                <table className="table w-full">
                  <thead>
                    <tr>
                      <th>Part Name</th>
                      <th>Quantity</th>
                      <th>Location</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.least_stocked_parts.length > 0 ? (
                      data.least_stocked_parts.map((part) => (
                        <tr key={part.id}>
                          <td>
                            <div>
                              <div className="font-medium text-primary">{part.part_name}</div>
                              <div className="text-xs text-muted">{part.part_number}</div>
                            </div>
                          </td>
                          <td className="font-semibold text-warning">{part.quantity.toLocaleString()}</td>
                          <td className="text-secondary text-sm">{part.location}</td>
                        </tr>
                      ))
                    ) : (
                      <tr>
                        <td colSpan={3} className="text-center text-muted py-4">
                          No parts available
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        )}
      </motion.div>

      {/* Low Stock Alerts Section */}
      {data.low_stock_parts.length > 0 && (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.4 }}
          className="card"
        >
          <div
            className="p-4 border-b border-border flex items-center justify-between cursor-pointer"
            onClick={() => toggleSection('alerts')}
          >
            <h2 className="text-lg font-semibold text-primary flex items-center gap-2">
              <AlertTriangle className="w-5 h-5 text-error" />
              Low Stock Alerts
            </h2>
            {expandedSections.alerts ? <ChevronUp /> : <ChevronDown />}
          </div>

          {expandedSections.alerts && (
            <div className="p-6">
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {data.low_stock_parts.map((part) => (
                  <div key={part.id} className="bg-error/5 border border-error/20 rounded-lg p-4">
                    <h4 className="font-medium text-primary">{part.part_name}</h4>
                    <p className="text-sm text-secondary mb-2">{part.part_number}</p>
                    <div className="space-y-1 text-sm">
                      <div className="flex justify-between">
                        <span className="text-muted">Current Stock:</span>
                        <span className="text-error font-medium">{part.quantity}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-muted">Location:</span>
                        <span className="text-secondary">{part.location_name || 'No Location'}</span>
                      </div>
                      {part.supplier && (
                        <div className="flex justify-between">
                          <span className="text-muted">Supplier:</span>
                          <span className="text-secondary text-xs">{part.supplier}</span>
                        </div>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </motion.div>
      )}
    </div>
  )
}

export default DashboardPage
