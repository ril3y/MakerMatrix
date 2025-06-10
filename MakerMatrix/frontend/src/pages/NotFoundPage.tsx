import { motion } from 'framer-motion'
import { FileQuestion, Home, Search, ArrowLeft } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import { useState } from 'react'

const NotFoundPage = () => {
  const navigate = useNavigate()
  const [searchQuery, setSearchQuery] = useState('')

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault()
    if (searchQuery.trim()) {
      // Navigate to parts search with the query
      navigate(`/parts?search=${encodeURIComponent(searchQuery)}`)
    }
  }

  const binaryPattern = '01000010 01010111 01000010' // BWB in binary

  return (
    <div className="min-h-screen flex items-center justify-center p-4">
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
        className="w-full max-w-2xl text-center"
      >
        <motion.div
          initial={{ scale: 0, rotate: -180 }}
          animate={{ scale: 1, rotate: 0 }}
          transition={{ duration: 0.6, type: "spring" }}
          className="inline-flex items-center justify-center w-32 h-32 bg-primary/10 rounded-full mb-8"
        >
          <FileQuestion className="w-16 h-16 text-primary" />
        </motion.div>

        <motion.h1
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.2 }}
          className="text-6xl font-bold text-text-primary mb-4"
        >
          404
        </motion.h1>

        <motion.p
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.3 }}
          className="text-2xl font-semibold text-text-primary mb-2"
        >
          Page Not Found
        </motion.p>

        <motion.p
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.4 }}
          className="text-lg text-text-secondary mb-8"
        >
          Looks like this byte got lost in the matrix! The page you're looking for doesn't exist.
        </motion.p>

        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.5 }}
          className="text-sm font-mono text-text-muted mb-8"
        >
          {binaryPattern}
        </motion.div>

        {/* Search Bar */}
        <motion.form
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.6 }}
          onSubmit={handleSearch}
          className="mb-8"
        >
          <div className="relative max-w-md mx-auto">
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search for parts in the inventory..."
              className="input w-full pl-10 pr-4"
            />
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-5 h-5 text-text-muted" />
          </div>
        </motion.form>

        {/* Action Buttons */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.7 }}
          className="flex flex-col sm:flex-row gap-4 justify-center"
        >
          <button
            onClick={() => navigate(-1)}
            className="btn btn-secondary flex items-center gap-2"
          >
            <ArrowLeft className="w-4 h-4" />
            Go Back
          </button>
          <button
            onClick={() => navigate('/')}
            className="btn btn-primary flex items-center gap-2"
          >
            <Home className="w-4 h-4" />
            Return Home
          </button>
        </motion.div>

        {/* Helpful Links */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.8 }}
          className="mt-12 bg-bg-secondary rounded-lg p-6"
        >
          <p className="text-sm font-medium text-text-primary mb-3">
            Quick Links
          </p>
          <div className="flex flex-wrap gap-4 justify-center text-sm">
            <button
              onClick={() => navigate('/parts')}
              className="text-primary hover:underline"
            >
              Browse Parts
            </button>
            <span className="text-text-muted">•</span>
            <button
              onClick={() => navigate('/locations')}
              className="text-primary hover:underline"
            >
              View Locations
            </button>
            <span className="text-text-muted">•</span>
            <button
              onClick={() => navigate('/categories')}
              className="text-primary hover:underline"
            >
              Browse Categories
            </button>
            <span className="text-text-muted">•</span>
            <button
              onClick={() => navigate('/dashboard')}
              className="text-primary hover:underline"
            >
              Dashboard
            </button>
          </div>
        </motion.div>

        <motion.p
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.9 }}
          className="mt-8 text-xs text-text-muted"
        >
          Battle With Bytes - MakerMatrix Inventory System
        </motion.p>
      </motion.div>
    </div>
  )
}

export default NotFoundPage