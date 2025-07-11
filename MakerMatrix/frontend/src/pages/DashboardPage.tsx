import { motion } from 'framer-motion'
import { Package, MapPin, Tags, Users, Activity, RefreshCw } from 'lucide-react'
import { useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useDashboardStore } from '@/store/dashboardStore'
import LoadingScreen from '@/components/ui/LoadingScreen'
import RecentActivity from '@/components/dashboard/RecentActivity'

const DashboardPage = () => {
  const { stats, isLoading, error, loadStats, refreshStats, clearError } = useDashboardStore()
  const navigate = useNavigate()

  useEffect(() => {
    loadStats()
  }, [])

  const handleRefresh = () => {
    refreshStats()
  }

  const handleCardClick = (title: string) => {
    switch (title) {
      case 'Total Parts':
        navigate('/parts')
        break
      case 'Locations':
        navigate('/locations')
        break
      case 'Categories':
        navigate('/categories')
        break
      case 'Active Users':
        navigate('/users')
        break
      default:
        break
    }
  }

  if (isLoading && !stats) {
    return <LoadingScreen />
  }

  const dashboardStats = [
    {
      title: 'Total Parts',
      value: stats?.totalParts?.toString() || '0',
      icon: Package,
      change: '',
      changeType: 'neutral' as const,
    },
    {
      title: 'Locations',
      value: stats?.totalLocations?.toString() || '0',
      icon: MapPin,
      change: '',
      changeType: 'neutral' as const,
    },
    {
      title: 'Categories',
      value: stats?.totalCategories?.toString() || '0',
      icon: Tags,
      change: '',
      changeType: 'neutral' as const,
    },
    {
      title: 'Active Users',
      value: stats?.activeUsers?.toString() || '0',
      icon: Users,
      change: '',
      changeType: 'neutral' as const,
    },
  ]

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-primary">Dashboard</h1>
          <p className="text-secondary mt-2">
            Welcome to MakerMatrix - Battle With Bytes Inventory System
          </p>
        </div>
        <button 
          onClick={handleRefresh}
          disabled={isLoading}
          className="btn btn-secondary flex items-center gap-2"
        >
          <RefreshCw className={`w-4 h-4 ${isLoading ? 'animate-spin' : ''}`} />
          Refresh
        </button>
      </div>

      {/* Error Display */}
      {error && (
        <motion.div
          initial={{ opacity: 0, height: 0 }}
          animate={{ opacity: 1, height: 'auto' }}
          className="bg-red-500/10 border border-red-500/20 rounded-lg p-4"
        >
          <p className="text-red-400">{error}</p>
          <button 
            onClick={clearError}
            className="text-red-300 hover:text-red-200 text-sm mt-2"
          >
            Dismiss
          </button>
        </motion.div>
      )}

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {dashboardStats.map((stat, index) => (
          <motion.div
            key={stat.title}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.3, delay: index * 0.1 }}
            className="card p-6 cursor-pointer hover:shadow-lg transition-all duration-200 hover:scale-105 group"
            onClick={() => handleCardClick(stat.title)}
          >
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-secondary group-hover:text-primary transition-colors">
                  {stat.title}
                </p>
                <p className="text-2xl font-bold text-primary group-hover:text-primary transition-colors">
                  {stat.value}
                </p>
                {stat.change && (
                  <div className="flex items-center mt-2">
                    <span
                      className="text-sm font-medium text-muted"
                    >
                      {stat.change}
                    </span>
                  </div>
                )}
              </div>
              <div className="p-3 bg-background-secondary rounded-lg group-hover:bg-primary-10 transition-colors">
                <stat.icon className="w-6 h-6 text-primary group-hover:scale-110 transition-transform" />
              </div>
            </div>
          </motion.div>
        ))}
      </div>

      {/* Recent Activity */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.3, delay: 0.4 }}
      >
        <RecentActivity limit={10} refreshInterval={30000} />
      </motion.div>

      {/* Quick Actions */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.3, delay: 0.5 }}
        className="card"
      >
        <div className="card-header">
          <h2 className="text-xl font-semibold text-primary">
            Quick Actions
          </h2>
        </div>
        <div className="card-content">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <button 
              onClick={() => navigate('/parts')}
              className="btn btn-secondary flex flex-col items-center gap-2 py-4 hover:bg-primary-10 transition-colors"
            >
              <Package className="w-5 h-5" />
              <span>Parts</span>
            </button>
            <button 
              onClick={() => navigate('/locations')}
              className="btn btn-secondary flex flex-col items-center gap-2 py-4 hover:bg-primary-10 transition-colors"
            >
              <MapPin className="w-5 h-5" />
              <span>Add Location</span>
            </button>
            <button 
              onClick={() => navigate('/categories')}
              className="btn btn-secondary flex flex-col items-center gap-2 py-4 hover:bg-primary-10 transition-colors"
            >
              <Tags className="w-5 h-5" />
              <span>Manage Categories</span>
            </button>
            <button 
              onClick={() => navigate('/users')}
              className="btn btn-secondary flex flex-col items-center gap-2 py-4 hover:bg-primary-10 transition-colors"
            >
              <Users className="w-5 h-5" />
              <span>Manage Users</span>
            </button>
          </div>
        </div>
      </motion.div>
    </div>
  )
}

export default DashboardPage