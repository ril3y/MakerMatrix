/**
 * Global Search Panel
 *
 * Slide-in panel that appears from the right side of the screen
 * Allows searching for parts from any page without losing context
 */

import { useState, useEffect, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { X, Search, Package, MapPin, Hash, ExternalLink, Loader2 } from 'lucide-react'
import { motion, AnimatePresence } from 'framer-motion'
import { partsService } from '@/services/parts.service'
import type { Part } from '@/types/parts'

interface GlobalSearchPanelProps {
  isOpen: boolean
  onClose: () => void
  initialSearchTerm?: string
  onSearchChange?: (value: string) => void
}

const GlobalSearchPanel = ({
  isOpen,
  onClose,
  initialSearchTerm = '',
  onSearchChange: _onSearchChange,
}: GlobalSearchPanelProps) => {
  const navigate = useNavigate()
  const [searchTerm, setSearchTerm] = useState(initialSearchTerm)
  const [results, setResults] = useState<Part[]>([])
  const [loading, setLoading] = useState(false)
  const [totalCount, setTotalCount] = useState(0)
  const [hoveredPart, setHoveredPart] = useState<Part | null>(null)
  const searchInputRef = useRef<HTMLInputElement>(null)

  // Sync with parent search value
  useEffect(() => {
    setSearchTerm(initialSearchTerm)
  }, [initialSearchTerm])

  // Focus search input when panel opens
  useEffect(() => {
    if (isOpen && searchInputRef.current) {
      setTimeout(() => searchInputRef.current?.focus(), 100)
    }
  }, [isOpen])

  // Clear search when panel closes
  useEffect(() => {
    if (!isOpen) {
      setSearchTerm('')
      setResults([])
      setTotalCount(0)
    }
  }, [isOpen])

  // Handle ESC key to close
  useEffect(() => {
    const handleEsc = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && isOpen) {
        onClose()
      }
    }

    window.addEventListener('keydown', handleEsc)
    return () => window.removeEventListener('keydown', handleEsc)
  }, [isOpen, onClose])

  // Search parts with debounce
  useEffect(() => {
    if (!searchTerm.trim()) {
      setResults([])
      setTotalCount(0)
      return
    }

    const timeoutId = setTimeout(async () => {
      try {
        setLoading(true)
        const response = await partsService.searchPartsText(searchTerm, 1, 10)
        setResults(response.data)
        setTotalCount(response.total_parts || 0)
      } catch (error) {
        console.error('Search failed:', error)
        setResults([])
        setTotalCount(0)
      } finally {
        setLoading(false)
      }
    }, 300) // 300ms debounce

    return () => clearTimeout(timeoutId)
  }, [searchTerm])

  const handlePartClick = (partId: string) => {
    onClose()
    navigate(`/parts/${partId}`)
  }

  const handleViewAllResults = () => {
    onClose()
    navigate(`/parts?search=${encodeURIComponent(searchTerm)}`)
  }

  return (
    <AnimatePresence>
      {isOpen && (
        <>
          {/* Backdrop - exclude header area (80px) */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="fixed inset-0 top-20 bg-black/50 backdrop-blur-sm z-40"
            onClick={onClose}
          />

          {/* Part Preview Panel - appears to the left when hovering */}
          <AnimatePresence>
            {hoveredPart && (
              <motion.div
                initial={{ opacity: 0, x: 20 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: 20 }}
                transition={{ duration: 0.15 }}
                className="fixed right-[920px] top-24 w-[400px] bg-gray-900 dark:bg-gray-800 border-2 border-primary rounded-lg shadow-2xl z-[60] p-6"
              >
                {/* Preview Header */}
                <div className="flex items-start gap-4 mb-4">
                  {hoveredPart.image_url ? (
                    <img
                      src={hoveredPart.image_url}
                      alt={hoveredPart.name}
                      className="w-24 h-24 object-cover rounded border-2 border-primary flex-shrink-0"
                    />
                  ) : hoveredPart.emoji ? (
                    <div className="w-24 h-24 flex items-center justify-center bg-theme-tertiary border-2 border-primary rounded text-5xl flex-shrink-0">
                      {hoveredPart.emoji}
                    </div>
                  ) : (
                    <div className="w-24 h-24 flex items-center justify-center bg-theme-tertiary border-2 border-primary rounded flex-shrink-0">
                      <Package className="w-12 h-12 text-theme-muted" />
                    </div>
                  )}
                  <div className="flex-1 min-w-0">
                    <h3 className="text-lg font-semibold text-white mb-1">{hoveredPart.name}</h3>
                    {hoveredPart.part_number && (
                      <p className="text-sm text-gray-400">Part #: {hoveredPart.part_number}</p>
                    )}
                  </div>
                </div>

                {/* Preview Details */}
                <div className="space-y-3 text-sm">
                  {hoveredPart.description && (
                    <div>
                      <p className="font-semibold text-white mb-1">Description</p>
                      <p className="text-gray-300">{hoveredPart.description}</p>
                    </div>
                  )}

                  <div className="grid grid-cols-2 gap-3">
                    <div>
                      <p className="font-semibold text-white mb-1">Quantity</p>
                      <p className="text-gray-300">{hoveredPart.quantity} in stock</p>
                    </div>
                    {hoveredPart.location && (
                      <div>
                        <p className="font-semibold text-white mb-1">Location</p>
                        <p className="text-gray-300">{hoveredPart.location.name}</p>
                      </div>
                    )}
                  </div>

                  {hoveredPart.supplier && (
                    <div>
                      <p className="font-semibold text-white mb-1">Supplier</p>
                      <p className="text-gray-300">{hoveredPart.supplier}</p>
                    </div>
                  )}

                  {hoveredPart.categories && hoveredPart.categories.length > 0 && (
                    <div>
                      <p className="font-semibold text-white mb-1">Categories</p>
                      <div className="flex flex-wrap gap-1">
                        {hoveredPart.categories.map((cat) => (
                          <span
                            key={cat.id}
                            className="px-2 py-1 bg-primary/20 text-primary text-xs rounded"
                          >
                            {cat.name}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}
                </div>

                {/* Hover instruction */}
                <div className="mt-4 pt-3 border-t border-gray-700 text-xs text-gray-500 text-center">
                  Click to view full details
                </div>
              </motion.div>
            )}
          </AnimatePresence>

          {/* Slide-in Panel - Wider overlay from right */}
          <motion.div
            initial={{ x: '100%' }}
            animate={{ x: 0 }}
            exit={{ x: '100%' }}
            transition={{ type: 'spring', damping: 30, stiffness: 300 }}
            className="fixed right-0 top-0 bottom-0 w-full max-w-[900px] bg-theme-elevated border-l border-theme-primary shadow-2xl z-50 flex flex-col"
          >
            {/* Header */}
            <div className="bg-theme-tertiary border-b border-theme-primary px-6 py-4 flex items-center justify-between flex-shrink-0">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-primary/10 rounded-lg">
                  <Search className="w-5 h-5 text-primary" />
                </div>
                <div>
                  <h2 className="text-xl font-semibold text-theme-primary">Search Results</h2>
                  {searchTerm && (
                    <p className="text-sm text-theme-secondary">
                      Searching for:{' '}
                      <span className="text-theme-primary font-medium">{searchTerm}</span>
                    </p>
                  )}
                </div>
              </div>
              <button
                onClick={onClose}
                className="p-2 hover:bg-theme-secondary rounded-lg transition-colors"
                aria-label="Close search"
              >
                <X className="w-5 h-5 text-theme-secondary" />
              </button>
            </div>

            {/* Results */}
            <div className="flex-1 overflow-y-auto">
              {!searchTerm ? (
                <div className="flex flex-col items-center justify-center h-full text-center px-6">
                  <Search className="w-16 h-16 text-theme-muted opacity-50 mb-4" />
                  <h3 className="text-lg font-semibold text-theme-primary mb-2">
                    Search for parts
                  </h3>
                  <p className="text-theme-secondary text-sm">
                    Start typing to search by part name, number, or description
                  </p>
                  <div className="mt-4 text-xs text-theme-muted">
                    Press{' '}
                    <kbd className="px-2 py-1 bg-theme-tertiary border border-theme-primary rounded">
                      ESC
                    </kbd>{' '}
                    to close
                  </div>
                </div>
              ) : loading ? (
                <div className="flex items-center justify-center h-32">
                  <Loader2 className="w-8 h-8 text-primary animate-spin" />
                </div>
              ) : results.length === 0 ? (
                <div className="flex flex-col items-center justify-center h-full text-center px-6">
                  <Package className="w-16 h-16 text-theme-muted opacity-50 mb-4" />
                  <h3 className="text-lg font-semibold text-theme-primary mb-2">
                    No results found
                  </h3>
                  <p className="text-theme-secondary text-sm">
                    Try different keywords or check your spelling
                  </p>
                </div>
              ) : (
                <div className="p-4 space-y-2">
                  {results.map((part) => (
                    <motion.div
                      key={part.id}
                      initial={{ opacity: 0, y: 10 }}
                      animate={{ opacity: 1, y: 0 }}
                      onClick={() => handlePartClick(part.id)}
                      onMouseEnter={() => setHoveredPart(part)}
                      onMouseLeave={() => setHoveredPart(null)}
                      className="bg-theme-secondary border border-theme-primary rounded-lg p-4 hover:border-primary transition-colors cursor-pointer group"
                    >
                      <div className="flex items-center gap-4">
                        {/* Part Image */}
                        {part.image_url ? (
                          <img
                            src={part.image_url}
                            alt={part.name}
                            className="w-20 h-20 object-cover rounded border border-theme-primary flex-shrink-0"
                          />
                        ) : part.emoji ? (
                          <div className="w-20 h-20 flex items-center justify-center bg-theme-tertiary border border-theme-primary rounded text-4xl flex-shrink-0">
                            {part.emoji}
                          </div>
                        ) : (
                          <div className="w-20 h-20 flex items-center justify-center bg-theme-tertiary border border-theme-primary rounded flex-shrink-0">
                            <Package className="w-10 h-10 text-theme-muted" />
                          </div>
                        )}

                        {/* Part Info - Main Column */}
                        <div className="flex-1 min-w-0 grid grid-cols-2 gap-4">
                          {/* Left Column */}
                          <div>
                            <h4 className="font-semibold text-theme-primary truncate group-hover:text-primary transition-colors text-base">
                              {part.name}
                            </h4>
                            {part.part_number && (
                              <p className="text-sm text-theme-muted">Part #: {part.part_number}</p>
                            )}
                            {part.description && (
                              <p className="text-sm text-theme-secondary line-clamp-2 mt-1">
                                {part.description}
                              </p>
                            )}
                          </div>

                          {/* Right Column - Metadata */}
                          <div className="space-y-2 text-sm">
                            <div className="flex items-center gap-2">
                              <Package className="w-4 h-4 text-theme-muted flex-shrink-0" />
                              <span className="text-theme-secondary">
                                <span className="font-semibold text-theme-primary">
                                  {part.quantity}
                                </span>{' '}
                                in stock
                              </span>
                            </div>
                            {part.location && (
                              <div className="flex items-center gap-2">
                                <MapPin className="w-4 h-4 text-theme-muted flex-shrink-0" />
                                <span className="text-theme-secondary truncate">
                                  {part.location.name}
                                </span>
                              </div>
                            )}
                            {part.categories && part.categories.length > 0 && (
                              <div className="flex items-center gap-2">
                                <Hash className="w-4 h-4 text-theme-muted flex-shrink-0" />
                                <span className="text-theme-secondary truncate">
                                  {part.categories[0].name}
                                </span>
                              </div>
                            )}
                          </div>
                        </div>

                        {/* Arrow */}
                        <ExternalLink className="w-5 h-5 text-theme-muted group-hover:text-primary transition-colors flex-shrink-0" />
                      </div>
                    </motion.div>
                  ))}
                </div>
              )}
            </div>

            {/* Footer - View All Results */}
            {results.length > 0 && totalCount > results.length && (
              <div className="border-t border-theme-primary p-4 flex-shrink-0 bg-theme-secondary">
                <button
                  onClick={handleViewAllResults}
                  className="w-full btn btn-primary flex items-center justify-center gap-2"
                >
                  View all {totalCount} results
                  <ExternalLink className="w-4 h-4" />
                </button>
              </div>
            )}
          </motion.div>
        </>
      )}
    </AnimatePresence>
  )
}

export default GlobalSearchPanel
