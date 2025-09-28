import { motion } from 'framer-motion'
import { Package, Plus, Search, Filter, ChevronLeft, ChevronRight, X, Copy, Check, ArrowUpDown, ArrowUp, ArrowDown } from 'lucide-react'
import { useState, useEffect, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { partsService } from '@/services/parts.service'
import { Part } from '@/types/parts'
import AddPartModal from '@/components/parts/AddPartModal'
import LoadingScreen from '@/components/ui/LoadingScreen'
import PartImage from '@/components/parts/PartImage'

const PartsPage = () => {
  const [showAddModal, setShowAddModal] = useState(false)
  const [parts, setParts] = useState<Part[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [currentPage, setCurrentPage] = useState(1)
  const [totalParts, setTotalParts] = useState(0)
  const [searchTerm, setSearchTerm] = useState('')
  const [isSearching, setIsSearching] = useState(false)
  
  // Autocomplete state
  const [suggestions, setSuggestions] = useState<string[]>([])
  const [showSuggestions, setShowSuggestions] = useState(false)
  const [activeSuggestionIndex, setActiveSuggestionIndex] = useState(-1)
  const [suggestionTimeout, setSuggestionTimeout] = useState<NodeJS.Timeout | null>(null)
  
  // Sorting state
  const [sortBy, setSortBy] = useState<string>('created_at')
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc')
  
  // Clipboard state - track copied items by part ID
  const [copiedItems, setCopiedItems] = useState<Record<string, 'name' | 'part_number'>>({})
  
  const searchInputRef = useRef<HTMLInputElement>(null)
  const suggestionsRef = useRef<HTMLDivElement>(null)
  const pageSize = 20
  const navigate = useNavigate()

  const getSortIcon = (field: string) => {
    if (sortBy !== field) {
      return <ArrowUpDown className="w-4 h-4 opacity-50" />
    }
    return sortOrder === 'asc' ? 
      <ArrowUp className="w-4 h-4" /> : 
      <ArrowDown className="w-4 h-4" />
  }

  const SortableHeader = ({ field, children }: { field: string, children: React.ReactNode }) => (
    <th 
      className="px-6 py-3 text-left text-xs font-medium text-secondary uppercase tracking-wider cursor-pointer hover:bg-background-secondary/50 transition-colors"
      onClick={() => handleSort(field)}
    >
      <div className="flex items-center gap-2">
        {children}
        {getSortIcon(field)}
      </div>
    </th>
  )

  const copyToClipboard = async (text: string, partId: string, type: 'name' | 'part_number') => {
    try {
      await navigator.clipboard.writeText(text)
      setCopiedItems(prev => ({ ...prev, [partId]: type }))
      setTimeout(() => {
        setCopiedItems(prev => {
          const newState = { ...prev }
          delete newState[partId]
          return newState
        })
      }, 2000)
    } catch (err) {
      console.error('Failed to copy to clipboard:', err)
    }
  }

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    })
  }

  const handleSort = (field: string) => {
    console.log('Sorting by field:', field, 'Current sort:', sortBy, sortOrder)
    if (sortBy === field) {
      const newOrder = sortOrder === 'asc' ? 'desc' : 'asc'
      console.log('Toggling sort order to:', newOrder)
      setSortOrder(newOrder)
    } else {
      console.log('Setting new sort field:', field)
      setSortBy(field)
      setSortOrder('asc')
    }
  }

  // Load parts using appropriate API based on search and sort requirements
  const loadParts = async (page = 1, search = '') => {
    try {
      setLoading(true)
      setError(null)
      
      setIsSearching(search && search.trim().length > 0)
      
      let response: any
      
      // Always use advanced search API for sorting support
      const searchParams = {
        search_term: search && search.trim() ? search.trim() : undefined,
        sort_by: sortBy || 'created_at',
        sort_order: sortOrder || 'desc',
        page,
        page_size: pageSize
      }
      
      console.log('Current state - sortBy:', sortBy, 'sortOrder:', sortOrder)
      console.log('Using advanced search with params:', searchParams)
      response = await partsService.searchParts(searchParams)
      
      // Debug logging to understand response structure
      console.log('API response:', response)
      
      // Handle different response formats
      let partsData: Part[] = []
      let totalCount = 0
      
      if (response.items && Array.isArray(response.items)) {
        // Direct PaginatedResponse format (from searchParts)
        partsData = response.items
        totalCount = response.total || 0
      } else if (response.data && response.data.items && Array.isArray(response.data.items)) {
        // Wrapped PaginatedResponse format: { data: { items: [...], total: ... } }
        partsData = response.data.items
        totalCount = response.data.total || 0
      } else if (response.data && Array.isArray(response.data)) {
        // Legacy format (getAllParts): { data: [...], total_parts: ... }
        partsData = response.data
        totalCount = response.total_parts || 0
      } else if (Array.isArray(response)) {
        // Direct array response
        partsData = response
        totalCount = response.length
      }
      
      // Map backend fields to frontend format if needed
      const mappedParts = partsData.map((part: any) => ({
        ...part,
        name: part.part_name || part.name,
        categories: part.categories || [],
        created_at: part.created_at || new Date().toISOString(),
        updated_at: part.updated_at || new Date().toISOString()
      }))
      
      console.log('Final mapped parts:', mappedParts, 'Total:', totalCount)
      
      setParts(mappedParts)
      setTotalParts(totalCount)
      setCurrentPage(page)
    } catch (err: any) {
      console.error('Error loading parts:', err)
      setError(err.response?.data?.error || err.message || 'Failed to load parts')
      // Set empty array on error to prevent map issues
      setParts([])
      setTotalParts(0)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadParts()
  }, [])

  // Reload parts when sorting changes
  useEffect(() => {
    if (parts.length > 0) { // Only reload if parts are already loaded
      loadParts(currentPage, searchTerm)
    }
  }, [sortBy, sortOrder]) // eslint-disable-line react-hooks/exhaustive-deps

  const handlePartAdded = () => {
    loadParts(currentPage)
  }

  // Fetch suggestions with debouncing
  const fetchSuggestions = async (query: string) => {
    if (query.length < 3) {
      setSuggestions([])
      setShowSuggestions(false)
      return
    }

    try {
      const suggestions = await partsService.getPartSuggestions(query, 8)
      setSuggestions(suggestions)
      setShowSuggestions(suggestions.length > 0)
      setActiveSuggestionIndex(-1)
    } catch (error) {
      console.error('Error fetching suggestions:', error)
      setSuggestions([])
      setShowSuggestions(false)
    }
  }

  // Handle search input change with debounced suggestions
  const handleSearchInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = e.target.value
    setSearchTerm(value)

    // Clear existing timeout
    if (suggestionTimeout) {
      clearTimeout(suggestionTimeout)
    }

    // Set new timeout for suggestions
    if (value.length >= 3) {
      const timeout = setTimeout(() => {
        fetchSuggestions(value)
      }, 300) // 300ms debounce
      setSuggestionTimeout(timeout)
    } else {
      setSuggestions([])
      setShowSuggestions(false)
    }
  }

  // Handle search form submission
  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault()
    setShowSuggestions(false)
    loadParts(1, searchTerm)
  }

  // Handle suggestion selection
  const handleSuggestionClick = (suggestion: string) => {
    setSearchTerm(suggestion)
    setShowSuggestions(false)
    loadParts(1, suggestion)
  }

  // Handle keyboard navigation in suggestions
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (!showSuggestions || suggestions.length === 0) return

    switch (e.key) {
      case 'ArrowDown':
        e.preventDefault()
        setActiveSuggestionIndex(prev => 
          prev < suggestions.length - 1 ? prev + 1 : prev
        )
        break
      case 'ArrowUp':
        e.preventDefault()
        setActiveSuggestionIndex(prev => prev > 0 ? prev - 1 : -1)
        break
      case 'Enter':
        e.preventDefault()
        if (activeSuggestionIndex >= 0) {
          handleSuggestionClick(suggestions[activeSuggestionIndex])
        } else {
          handleSearch(e)
        }
        break
      case 'Escape':
        setShowSuggestions(false)
        setActiveSuggestionIndex(-1)
        break
    }
  }

  // Clear search
  const clearSearch = () => {
    setSearchTerm('')
    setShowSuggestions(false)
    setSuggestions([])
    loadParts(1, '')
  }

  // Click outside to close suggestions
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (
        suggestionsRef.current &&
        !suggestionsRef.current.contains(event.target as Node) &&
        searchInputRef.current &&
        !searchInputRef.current.contains(event.target as Node)
      ) {
        setShowSuggestions(false)
      }
    }

    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  // Cleanup timeout on unmount
  useEffect(() => {
    return () => {
      if (suggestionTimeout) {
        clearTimeout(suggestionTimeout)
      }
    }
  }, [suggestionTimeout])

  const totalPages = Math.ceil(totalParts / pageSize)

  const handlePageChange = (page: number) => {
    if (page >= 1 && page <= totalPages) {
      loadParts(page, searchTerm)
    }
  }

  const handlePartClick = (partId: string) => {
    navigate(`/parts/${partId}`)
  }

  if (loading && parts.length === 0) {
    return <LoadingScreen />
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
            <Package className="w-6 h-6" />
            Parts Inventory
          </h1>
          <p className="text-secondary mt-1">
            Manage your parts inventory
          </p>
        </div>
        <button 
          onClick={() => setShowAddModal(true)}
          className="btn btn-primary flex items-center gap-2"
        >
          <Plus className="w-4 h-4" />
          Add Part
        </button>
      </motion.div>

      {/* Search and Filters */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.1 }}
        className="card p-4"
      >
        <form onSubmit={handleSearch} className="flex gap-4">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-muted" />
            <input
              ref={searchInputRef}
              type="text"
              placeholder="Search parts by name, number, or description..."
              value={searchTerm}
              onChange={handleSearchInputChange}
              onKeyDown={handleKeyDown}
              className="input pl-10 pr-10 w-full"
              autoComplete="off"
            />
            
            {/* Clear search button */}
            {searchTerm && (
              <button
                type="button"
                onClick={clearSearch}
                className="absolute right-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-muted hover:text-primary transition-colors"
              >
                <X className="w-4 h-4" />
              </button>
            )}
            
            {/* Autocomplete suggestions dropdown */}
            {showSuggestions && suggestions.length > 0 && (
              <div
                ref={suggestionsRef}
                className="absolute top-full left-0 right-0 mt-1 bg-background-primary border border-border rounded-lg shadow-lg z-50 max-h-60 overflow-y-auto"
              >
                {suggestions.map((suggestion, index) => (
                  <button
                    key={suggestion}
                    type="button"
                    onClick={() => handleSuggestionClick(suggestion)}
                    className={`w-full text-left px-4 py-2 hover:bg-background-secondary transition-colors border-b border-border last:border-b-0 ${
                      index === activeSuggestionIndex ? 'bg-background-secondary' : ''
                    }`}
                  >
                    <div className="text-sm text-primary">{suggestion}</div>
                  </button>
                ))}
              </div>
            )}
          </div>
          
          <button type="submit" className="btn btn-primary" disabled={loading}>
            {loading ? 'Searching...' : 'Search'}
          </button>
          
          {searchTerm && (
            <button 
              type="button" 
              onClick={clearSearch}
              className="btn btn-secondary"
            >
              Clear
            </button>
          )}
          
          <button type="button" className="btn btn-secondary flex items-center gap-2">
            <Filter className="w-4 h-4" />
            Filters
          </button>
        </form>
        
        {/* Search status */}
        {isSearching && searchTerm && (
          <div className="mt-3 text-sm text-muted">
            {loading ? 
              `Searching for "${searchTerm}"...` : 
              `Found ${totalParts} result${totalParts !== 1 ? 's' : ''} for "${searchTerm}"`
            }
          </div>
        )}
      </motion.div>

      {/* Error Display */}
      {error && (
        <motion.div
          initial={{ opacity: 0, height: 0 }}
          animate={{ opacity: 1, height: 'auto' }}
          className="bg-red-500/10 border border-red-500/20 rounded-lg p-4"
        >
          <p className="text-red-400">{error}</p>
          <button 
            onClick={() => setError(null)}
            className="text-red-300 hover:text-red-200 text-sm mt-2"
          >
            Dismiss
          </button>
        </motion.div>
      )}

      {/* Parts List */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.2 }}
        className="card"
      >
        <div className="card-header">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-semibold text-primary">
              Parts ({totalParts})
            </h2>
            {loading && (
              <div className="text-sm text-muted">Loading...</div>
            )}
          </div>
        </div>
        
        <div className="card-content p-0">
          {parts.length === 0 && !loading ? (
            <div className="text-center py-8">
              <Package className="w-16 h-16 text-muted mx-auto mb-4" />
              <h3 className="text-lg font-semibold text-primary mb-2">
                No Parts Found
              </h3>
              <p className="text-secondary">
                {searchTerm ? 'No parts match your search criteria.' : 'Start by adding your first part to the inventory.'}
              </p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead className="bg-background-secondary border-b border-border">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-medium text-secondary uppercase tracking-wider">
                      Image
                    </th>
                    <SortableHeader field="part_name">Name</SortableHeader>
                    <SortableHeader field="part_number">Part Number</SortableHeader>
                    <SortableHeader field="quantity">Quantity</SortableHeader>
                    <SortableHeader field="location">Location</SortableHeader>
                    <th className="px-6 py-3 text-left text-xs font-medium text-secondary uppercase tracking-wider">
                      Categories
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-secondary uppercase tracking-wider">
                      Supplier
                    </th>
                    <SortableHeader field="created_at">Added At</SortableHeader>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border">
                  {(parts || []).map((part) => (
                    <tr key={part.id} className="hover:bg-background-secondary/50 transition-colors">
                      <td className="px-6 py-4 whitespace-nowrap">
                        <PartImage 
                          imageUrl={part.image_url}
                          partName={part.name}
                          size="md"
                          showFallback={true}
                        />
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="flex items-center gap-2">
                          <button
                            onClick={() => handlePartClick(part.id)}
                            className="text-sm font-medium text-primary hover:text-primary-dark hover:underline transition-colors cursor-pointer"
                            title="Click to view part details"
                          >
                            {part.name}
                          </button>
                          <button
                            onClick={(e) => {
                              e.stopPropagation()
                              copyToClipboard(part.name, part.id, 'name')
                            }}
                            className="text-muted hover:text-primary transition-colors"
                            title="Copy part name"
                          >
                            {copiedItems[part.id] === 'name' ? (
                              <Check className="w-4 h-4 text-green-500" />
                            ) : (
                              <Copy className="w-4 h-4" />
                            )}
                          </button>
                        </div>
                        {part.additional_properties?.description && (
                          <div className="text-sm text-muted truncate max-w-xs">
                            {part.additional_properties.description}
                          </div>
                        )}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-secondary">
                        {part.part_number ? (
                          <div className="flex items-center gap-2">
                            <button
                              onClick={() => handlePartClick(part.id)}
                              className="text-sm text-secondary hover:text-primary hover:underline transition-colors cursor-pointer"
                              title="Click to view part details"
                            >
                              {part.part_number}
                            </button>
                            <button
                              onClick={(e) => {
                                e.stopPropagation()
                                copyToClipboard(part.part_number!, part.id, 'part_number')
                              }}
                              className="text-muted hover:text-primary transition-colors"
                              title="Copy part number"
                            >
                              {copiedItems[part.id] === 'part_number' ? (
                                <Check className="w-4 h-4 text-green-500" />
                              ) : (
                                <Copy className="w-4 h-4" />
                              )}
                            </button>
                          </div>
                        ) : (
                          '-'
                        )}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <span className={`text-sm font-medium ${
                          part.minimum_quantity && part.quantity <= part.minimum_quantity
                            ? 'text-red-400'
                            : 'text-primary'
                        }`}>
                          {part.quantity}
                        </span>
                        {part.minimum_quantity && (
                          <div className="text-xs text-muted">
                            Min: {part.minimum_quantity}
                          </div>
                        )}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-secondary">
                        {part.location?.name || '-'}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-secondary">
                        {part.categories && part.categories.length > 0 ? (
                          <div className="flex flex-wrap gap-1">
                            {part.categories.map((category, index) => (
                              <span
                                key={category.id}
                                className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-primary/20 text-primary"
                              >
                                {category.name}
                              </span>
                            ))}
                          </div>
                        ) : '-'}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-secondary">
                        {part.supplier || '-'}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-secondary">
                        {formatDate(part.created_at)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
        
        {/* Pagination */}
        {totalPages > 1 && (
          <div className="card-footer border-t border-border">
            <div className="flex items-center justify-between">
              <div className="text-sm text-muted">
                Showing {((currentPage - 1) * pageSize) + 1} to {Math.min(currentPage * pageSize, totalParts)} of {totalParts} parts
              </div>
              <div className="flex items-center gap-2">
                <button
                  onClick={() => handlePageChange(currentPage - 1)}
                  disabled={currentPage === 1}
                  className="btn btn-secondary btn-sm disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  <ChevronLeft className="w-4 h-4" />
                  Previous
                </button>
                
                <div className="flex items-center gap-1">
                  {Array.from({ length: Math.min(5, totalPages) }, (_, i) => {
                    const page = Math.max(1, Math.min(totalPages - 4, currentPage - 2)) + i
                    if (page > totalPages) return null
                    
                    return (
                      <button
                        key={page}
                        onClick={() => handlePageChange(page)}
                        className={`btn btn-sm ${
                          page === currentPage
                            ? 'btn-primary'
                            : 'btn-secondary'
                        }`}
                      >
                        {page}
                      </button>
                    )
                  })}
                </div>
                
                <button
                  onClick={() => handlePageChange(currentPage + 1)}
                  disabled={currentPage === totalPages}
                  className="btn btn-secondary btn-sm disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  Next
                  <ChevronRight className="w-4 h-4" />
                </button>
              </div>
            </div>
          </div>
        )}
      </motion.div>

      {/* Add Part Modal */}
      <AddPartModal
        isOpen={showAddModal}
        onClose={() => setShowAddModal(false)}
        onSuccess={handlePartAdded}
      />
    </div>
  )
}

export default PartsPage