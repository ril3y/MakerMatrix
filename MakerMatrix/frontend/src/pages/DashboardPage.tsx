import { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import { useNavigate } from 'react-router-dom'
import {
  Package,
  AlertTriangle,
  MapPin,
  Tag,
  TrendingUp,
  RefreshCw,
  ChevronUp,
  ChevronDown,
  BarChart3,
  Activity,
  Clock,
} from 'lucide-react'
import { activityService, type Activity as ActivityType } from '@/services/activity.service'
import { Bar, Doughnut } from 'react-chartjs-2'
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  BarElement,
  ArcElement,
  Title,
  Tooltip,
  Legend,
} from 'chart.js'
import toast from 'react-hot-toast'
import { dashboardService, type DashboardData } from '@/services/dashboard.service'

// Register ChartJS components
ChartJS.register(CategoryScale, LinearScale, BarElement, ArcElement, Title, Tooltip, Legend)

const DashboardPage = () => {
  const navigate = useNavigate()
  const [loading, setLoading] = useState(true)
  const [data, setData] = useState<DashboardData | null>(null)
  const [activities, setActivities] = useState<ActivityType[]>([])
  const [loadingActivities, setLoadingActivities] = useState(true)
  const [expandedSections, setExpandedSections] = useState({
    distribution: true,
    topParts: true,
    alerts: true,
    activity: true,
    stocks: true,
  })

  useEffect(() => {
    loadDashboardData()
    loadRecentActivities()
  }, [])

  const loadDashboardData = async () => {
    try {
      setLoading(true)
      const response = await dashboardService.getDashboardSummary()
      setData(response)
    } catch (error) {
      toast.error('Failed to load dashboard data')
      console.error('Dashboard error:', error)
      setData(null)
    } finally {
      setLoading(false)
    }
  }

  const loadRecentActivities = async () => {
    try {
      setLoadingActivities(true)
      const recentActivities = await activityService.getRecentActivities({
        limit: 10,
        hours: 24,
      })
      setActivities(recentActivities)
    } catch (error) {
      console.error('Failed to load recent activities:', error)
      // Don't show error toast for activities - it's not critical
    } finally {
      setLoadingActivities(false)
    }
  }

  const toggleSection = (section: keyof typeof expandedSections) => {
    setExpandedSections((prev) => ({
      ...prev,
      [section]: !prev[section],
    }))
  }

  const handleSupplierClick = (supplierName: string) => {
    // Navigate to parts page with supplier filter
    navigate(`/parts?supplier=${encodeURIComponent(supplierName)}`)
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

  // Prepare chart data with theme colors
  const categoryChartData = {
    labels:
      data.parts_by_category.length > 0
        ? data.parts_by_category.slice(0, 10).map((item) => item.category)
        : ['No Data'],
    datasets: [
      {
        label: 'Parts Count',
        data:
          data.parts_by_category.length > 0
            ? data.parts_by_category.slice(0, 10).map((item) => item.part_count)
            : [0],
        backgroundColor: 'rgba(0, 255, 157, 0.8)', // --primary color
        borderColor: 'rgba(0, 255, 157, 1)',
        borderWidth: 1,
      },
    ],
  }

  const locationChartData = {
    labels:
      data.parts_by_location.length > 0
        ? data.parts_by_location.slice(0, 8).map((item) => item.location)
        : ['No Data'],
    datasets: [
      {
        data:
          data.parts_by_location.length > 0
            ? data.parts_by_location.slice(0, 8).map((item) => item.part_count)
            : [0],
        backgroundColor: [
          'rgba(0, 255, 157, 0.8)', // primary (cyan/green)
          'rgba(239, 68, 68, 0.8)', // error (red)
          'rgba(16, 185, 129, 0.8)', // success (green)
          'rgba(245, 158, 11, 0.8)', // warning (amber)
          'rgba(147, 51, 234, 0.8)', // purple
          'rgba(236, 72, 153, 0.8)', // pink
          'rgba(14, 165, 233, 0.8)', // cyan
          'rgba(132, 204, 22, 0.8)', // lime
        ],
        borderWidth: 0,
      },
    ],
  }

  const supplierChartData = {
    labels:
      data.parts_by_supplier.length > 0
        ? data.parts_by_supplier.map((item) => item.supplier)
        : ['No Data'],
    datasets: [
      {
        data:
          data.parts_by_supplier.length > 0
            ? data.parts_by_supplier.map((item) => item.part_count)
            : [0],
        backgroundColor: [
          'rgba(0, 255, 157, 0.8)', // primary (cyan/green)
          'rgba(239, 68, 68, 0.8)', // error (red)
          'rgba(16, 185, 129, 0.8)', // success (green)
          'rgba(245, 158, 11, 0.8)', // warning (amber)
          'rgba(147, 51, 234, 0.8)', // purple
          'rgba(236, 72, 153, 0.8)', // pink
          'rgba(14, 165, 233, 0.8)', // cyan
          'rgba(132, 204, 22, 0.8)', // lime
          'rgba(168, 85, 247, 0.8)', // violet
          'rgba(59, 130, 246, 0.8)', // blue
        ],
        borderWidth: 0,
      },
    ],
  }

  // Helper function to get supplier icon URL
  const getSupplierIcon = (supplierName: string) => {
    const normalizedName = supplierName
      .toLowerCase()
      .trim()
      .replace(/\s+/g, '-') // Replace spaces with hyphens
      .replace(/_/g, '-') // Replace underscores with hyphens

    // Map supplier names to their icon filenames (handles variations)
    const iconMap: Record<string, string> = {
      lcsc: 'lcsc.ico',
      digikey: 'digikey.png',
      'digi-key': 'digikey.png',
      mouser: 'mouser.png',
      'mcmaster-carr': 'mcmaster-carr.ico',
      mcmaster: 'mcmaster-carr.ico',
      boltdepot: 'bolt-depot.png',
      'bolt-depot': 'bolt-depot.png', // Legacy support
    }

    return iconMap[normalizedName] || null
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
          <p className="text-secondary mt-1">Overview of your inventory</p>
        </div>
        <div className="flex gap-2">
          <button onClick={loadDashboardData} className="btn btn-secondary flex items-center gap-2">
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
          className="card p-6 border-l-4 border-l-accent"
        >
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-secondary">Total Parts</p>
              <p className="text-2xl font-bold text-accent">
                {data.summary.total_parts.toLocaleString()}
              </p>
              <p className="text-xs text-muted mt-1">
                {data.summary.total_units.toLocaleString()} total units
              </p>
            </div>
            <div className="w-12 h-12 rounded-full bg-accent/10 flex items-center justify-center">
              <Package className="w-6 h-6 text-accent" />
            </div>
          </div>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.15 }}
          className="card p-6 border-l-4 border-l-error"
        >
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-secondary">Low Stock Alerts</p>
              <p className="text-2xl font-bold text-error">{data.summary.low_stock_count}</p>
              <p className="text-xs text-muted mt-1">Parts below 10 units</p>
            </div>
            <div className="w-12 h-12 rounded-full bg-error/10 flex items-center justify-center">
              <AlertTriangle className="w-6 h-6 text-error" />
            </div>
          </div>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
          className="card p-6 border-l-4 border-l-purple-500"
        >
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-secondary">Categories</p>
              <p className="text-2xl font-bold text-purple-400">{data.summary.total_categories}</p>
              <p className="text-xs text-muted mt-1">Active categories</p>
            </div>
            <div className="w-12 h-12 rounded-full bg-purple-500/10 flex items-center justify-center">
              <Tag className="w-6 h-6 text-purple-400" />
            </div>
          </div>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.25 }}
          className="card p-6 border-l-4 border-l-blue-500"
        >
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-secondary">Locations</p>
              <p className="text-2xl font-bold text-blue-400">{data.summary.total_locations}</p>
              <p className="text-xs text-muted mt-1">
                {data.summary.parts_with_location} parts located
              </p>
            </div>
            <div className="w-12 h-12 rounded-full bg-blue-500/10 flex items-center justify-center">
              <MapPin className="w-6 h-6 text-blue-400" />
            </div>
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
          <div className="p-6 space-y-6">
            {/* Charts Grid */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
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
                              usePointStyle: true,
                              font: {
                                size: 10,
                              },
                            },
                          },
                        },
                      }}
                    />
                  ) : (
                    <div className="flex items-center justify-center h-full text-muted">
                      No location data available
                    </div>
                  )}
                </div>
              </div>

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
                            display: false,
                          },
                        },
                        scales: {
                          y: {
                            beginAtZero: true,
                            ticks: {
                              precision: 0,
                            },
                          },
                        },
                      }}
                    />
                  ) : (
                    <div className="flex items-center justify-center h-full text-muted">
                      No category data available
                    </div>
                  )}
                </div>
              </div>

              {/* Suppliers Chart */}
              <div>
                <h3 className="text-md font-medium text-primary mb-4">By Supplier</h3>
                <div className="h-64">
                  {data.parts_by_supplier.length > 0 ? (
                    <Doughnut
                      data={supplierChartData}
                      options={{
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: {
                          legend: {
                            position: 'right',
                            labels: {
                              padding: 10,
                              usePointStyle: true,
                              font: {
                                size: 10,
                              },
                            },
                          },
                        },
                      }}
                    />
                  ) : (
                    <div className="flex items-center justify-center h-full text-muted">
                      No supplier data available
                    </div>
                  )}
                </div>
              </div>
            </div>

            {/* Supplier Icons Legend */}
            {data.parts_by_supplier.length > 0 && (
              <div className="border-t border-border pt-4">
                <h3 className="text-sm font-medium text-primary mb-3">Suppliers</h3>
                <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-4">
                  {data.parts_by_supplier.map((supplier) => {
                    return (
                      <div
                        key={supplier.supplier}
                        onClick={() => handleSupplierClick(supplier.supplier)}
                        className="flex items-center gap-3 p-3 bg-card-light dark:bg-card-dark rounded-lg border border-border hover:border-primary transition-colors cursor-pointer"
                        title={`Click to view all ${supplier.part_count} parts from ${supplier.supplier}`}
                      >
                        <div className="w-8 h-8 flex items-center justify-center">
                          <img
                            src={`/api/utility/supplier_icon/${supplier.supplier}`}
                            alt={supplier.supplier}
                            className="w-full h-full object-contain"
                            onError={(e) => {
                              // Fallback to initial letter if image fails to load
                              const target = e.currentTarget
                              const parent = target.parentElement
                              if (parent) {
                                target.style.display = 'none'
                                const fallback = document.createElement('div')
                                fallback.className =
                                  'w-8 h-8 rounded bg-primary/20 flex items-center justify-center text-xs font-bold text-primary'
                                fallback.textContent = supplier.supplier.charAt(0).toUpperCase()
                                parent.appendChild(fallback)
                              }
                            }}
                          />
                        </div>
                        <div className="flex-1 min-w-0">
                          <p className="text-sm font-medium text-primary truncate">
                            {supplier.supplier}
                          </p>
                          <p className="text-xs text-muted">{supplier.part_count} parts</p>
                        </div>
                      </div>
                    )
                  })}
                </div>
              </div>
            )}
          </div>
        )}
      </motion.div>

      {/* Recent Activity Section */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.35 }}
        className="card"
      >
        <div
          className="p-4 border-b border-border flex items-center justify-between cursor-pointer"
          onClick={() => toggleSection('activity')}
        >
          <h2 className="text-lg font-semibold text-primary flex items-center gap-2">
            <Activity className="w-5 h-5" />
            Recent Activity
          </h2>
          {expandedSections.activity ? <ChevronUp /> : <ChevronDown />}
        </div>

        {expandedSections.activity && (
          <div className="p-6">
            {loadingActivities ? (
              <div className="flex items-center justify-center h-32">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
              </div>
            ) : activities.length === 0 ? (
              <div className="text-center py-8 text-muted">
                <Activity className="w-12 h-12 mx-auto mb-2 opacity-50" />
                <p>No recent activity</p>
              </div>
            ) : (
              <div className="space-y-2">
                {activities.map((activity) => (
                  <div
                    key={activity.id}
                    className="flex items-start gap-3 p-3 bg-background-secondary rounded-lg border border-border hover:border-primary/50 transition-colors"
                  >
                    <div className="text-2xl flex-shrink-0">
                      {activityService.getActivityIcon(activity)}
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-start justify-between gap-2">
                        <div className="flex-1 min-w-0">
                          <p className="text-sm text-primary font-medium">
                            {activityService.formatActivityDescription(activity)}
                          </p>
                          {activity.username && (
                            <p className="text-xs text-muted mt-0.5">by {activity.username}</p>
                          )}
                        </div>
                        <div className="flex items-center gap-1 text-xs text-muted flex-shrink-0">
                          <Clock className="w-3 h-3" />
                          {activityService.formatRelativeTime(activity.timestamp)}
                        </div>
                      </div>
                      {activity.details && Object.keys(activity.details).length > 0 && (
                        <div className="mt-1 text-xs text-secondary">
                          {Object.entries(activity.details)
                            .filter(([key]) => !['id', 'timestamp'].includes(key))
                            .slice(0, 2)
                            .map(([key, value]) => (
                              <span key={key} className="mr-3">
                                {key}: {typeof value === 'object' ? JSON.stringify(value) : String(value)}
                              </span>
                            ))}
                        </div>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </motion.div>

      {/* Stock Levels Section */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.4 }}
        className="card"
      >
        <div
          className="p-4 border-b border-border flex items-center justify-between cursor-pointer"
          onClick={() => toggleSection('stocks')}
        >
          <h2 className="text-lg font-semibold text-primary flex items-center gap-2">
            <TrendingUp className="w-5 h-5" />
            Stock Levels
          </h2>
          {expandedSections.stocks ? <ChevronUp /> : <ChevronDown />}
        </div>

        {expandedSections.stocks && (
          <div className="p-6 space-y-6">
            {/* Most Stocked Parts */}
            <div>
              <h3 className="text-md font-medium text-primary mb-4">Most Stocked Parts</h3>
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead>
                    <tr className="border-b border-border">
                      <th className="text-left py-2 px-4 text-sm font-medium text-primary">
                        Part Name
                      </th>
                      <th className="text-left py-2 px-4 text-sm font-medium text-primary">
                        Part Number
                      </th>
                      <th className="text-left py-2 px-4 text-sm font-medium text-primary">
                        Supplier
                      </th>
                      <th className="text-right py-2 px-4 text-sm font-medium text-primary">
                        Quantity
                      </th>
                      <th className="text-left py-2 px-4 text-sm font-medium text-primary">
                        Location
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.most_stocked_parts.map((part) => (
                      <tr
                        key={part.id}
                        onClick={() => navigate(`/parts/${part.id}`)}
                        className="border-b border-border hover:bg-background-hover cursor-pointer transition-colors"
                      >
                        <td className="py-2 px-4 text-sm text-primary">{part.part_name}</td>
                        <td className="py-2 px-4 text-sm text-secondary">{part.part_number}</td>
                        <td className="py-2 px-4 text-sm text-secondary">{part.supplier}</td>
                        <td className="py-2 px-4 text-sm text-right font-medium text-success">
                          {part.quantity}
                        </td>
                        <td className="py-2 px-4 text-sm text-secondary">{part.location}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>

            {/* Least Stocked Parts */}
            <div>
              <h3 className="text-md font-medium text-primary mb-4">Least Stocked Parts</h3>
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead>
                    <tr className="border-b border-border">
                      <th className="text-left py-2 px-4 text-sm font-medium text-primary">
                        Part Name
                      </th>
                      <th className="text-left py-2 px-4 text-sm font-medium text-primary">
                        Part Number
                      </th>
                      <th className="text-left py-2 px-4 text-sm font-medium text-primary">
                        Supplier
                      </th>
                      <th className="text-right py-2 px-4 text-sm font-medium text-primary">
                        Quantity
                      </th>
                      <th className="text-left py-2 px-4 text-sm font-medium text-primary">
                        Location
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.least_stocked_parts.map((part) => (
                      <tr
                        key={part.id}
                        onClick={() => navigate(`/parts/${part.id}`)}
                        className="border-b border-border hover:bg-background-hover cursor-pointer transition-colors"
                      >
                        <td className="py-2 px-4 text-sm text-primary">{part.part_name}</td>
                        <td className="py-2 px-4 text-sm text-secondary">{part.part_number}</td>
                        <td className="py-2 px-4 text-sm text-secondary">{part.supplier}</td>
                        <td className="py-2 px-4 text-sm text-right font-medium text-warning">
                          {part.quantity}
                        </td>
                        <td className="py-2 px-4 text-sm text-secondary">{part.location}</td>
                      </tr>
                    ))}
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
          transition={{ delay: 0.45 }}
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
                  <div
                    key={part.id}
                    onClick={() => navigate(`/parts/${part.id}`)}
                    className="bg-error/5 border border-error/20 rounded-lg p-4 cursor-pointer hover:bg-error/10 hover:border-error/30 transition-colors"
                  >
                    <h4 className="font-medium text-primary hover:text-primary-dark">
                      {part.part_name}
                    </h4>
                    <p className="text-sm text-secondary mb-2">{part.part_number}</p>
                    <div className="space-y-1 text-sm">
                      <div className="flex justify-between">
                        <span className="text-muted">Current Stock:</span>
                        <span className="text-error font-medium">{part.quantity}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-muted">Location:</span>
                        <span className="text-secondary">
                          {part.location_name || 'No Location'}
                        </span>
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
