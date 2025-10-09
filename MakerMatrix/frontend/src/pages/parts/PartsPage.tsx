import { motion } from 'framer-motion'
import {
  Package,
  Plus,
  Search,
  Filter,
  ChevronLeft,
  ChevronRight,
  X,
  Copy,
  Check,
  ArrowUpDown,
  ArrowUp,
  ArrowDown,
  MapPin,
  Edit3,
  CheckSquare,
  Square,
  Hash,
} from 'lucide-react'
import { useState, useEffect, useRef } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { partsService } from '@/services/parts.service'
import { supplierService } from '@/services/supplier.service'
import type { Part } from '@/types/parts'
import AddPartModal from '@/components/parts/AddPartModal'
import BulkEditModal from '@/components/parts/BulkEditModal'
import LoadingScreen from '@/components/ui/LoadingScreen'
import PartImage from '@/components/parts/PartImage'
import { PermissionGuard } from '@/components/auth/PermissionGuard'

const PartsPage = () => {
  const [searchParams] = useSearchParams()
  const [showAddModal, setShowAddModal] = useState(false)
  const [showBulkEditModal, setShowBulkEditModal] = useState(false)
  const [parts, setParts] = useState<Part[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [currentPage, setCurrentPage] = useState(1)
  const [totalParts, setTotalParts] = useState(0)
  const [searchTerm, setSearchTerm] = useState('')
  const [supplierFilter, setSupplierFilter] = useState<string>('')
  const [isSearching, setIsSearching] = useState(false)
  const [initialLoadComplete, setInitialLoadComplete] = useState(false)

  // Autocomplete state
  const [suggestions, setSuggestions] = useState<string[]>([])
  const [showSuggestions, setShowSuggestions] = useState(false)
  const [activeSuggestionIndex, setActiveSuggestionIndex] = useState(-1)
  const [suggestionTimeout, setSuggestionTimeout] = useState<NodeJS.Timeout | null>(null)

  // Auto-search debounce timeout
  const [searchTimeout, setSearchTimeout] = useState<NodeJS.Timeout | null>(null)

  // Sorting state
  const [sortBy, setSortBy] = useState<string>('created_at')
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc')

  // Clipboard state - track copied items by part ID
  const [copiedItems, setCopiedItems] = useState<Record<string, 'name' | 'part_number'>>({})

  // Supplier state for logo display
  const [supplierImageMap, setSupplierImageMap] = useState<Record<string, string>>({})

  // Bulk edit mode state
  const [bulkEditMode, setBulkEditMode] = useState(false)
  const [selectedPartIds, setSelectedPartIds] = useState<Set<string>>(new Set())
  const [lastClickedIndex, setLastClickedIndex] = useState<number | null>(null)

  const searchInputRef = useRef<HTMLInputElement>(null)
  const suggestionsRef = useRef<HTMLDivElement>(null)
  const pageSize = 20
  const navigate = useNavigate()

  const getSortIcon = (field: string) => {
    if (sortBy !== field) {
      return <ArrowUpDown className="w-4 h-4 opacity-50" />
    }
    return sortOrder === 'asc' ? <ArrowUp className="w-4 h-4" /> : <ArrowDown className="w-4 h-4" />
  }

  const SortableHeader = ({ field, children }: { field: string; children: React.ReactNode }) => (
    <th
      className="px-3 py-3 text-left text-xs font-medium text-secondary uppercase tracking-wider cursor-pointer hover:bg-background-secondary/50 transition-colors"
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
      setCopiedItems((prev) => ({ ...prev, [partId]: type }))
      setTimeout(() => {
        setCopiedItems((prev) => {
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
      month: 'short',
      day: 'numeric',
      year: '2-digit',
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
      const searchParamsObj = {
        search_term: search && search.trim() ? search.trim() : undefined,
        supplier: supplierFilter || undefined,
        sort_by: sortBy || 'created_at',
        sort_order: sortOrder || 'desc',
        page,
        page_size: pageSize,
      }

      console.log('Current state - sortBy:', sortBy, 'sortOrder:', sortOrder)
      console.log('Supplier filter:', supplierFilter)
      console.log('Using advanced search with params:', searchParamsObj)
      response = await partsService.searchParts(searchParamsObj)

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
        updated_at: part.updated_at || new Date().toISOString(),
      }))

      console.log('Final mapped parts:', mappedParts, 'Total:', totalCount)

      setParts(mappedParts)
      setTotalParts(totalCount)
      setCurrentPage(page)
    } catch (err) {
      const error = err as { response?: { data?: { error?: string; message?: string; detail?: string }; status?: number }; message?: string }
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
    // Read supplier filter and search term from URL params on mount
    const supplier = searchParams.get('supplier')
    const search = searchParams.get('search')
    if (supplier) {
      setSupplierFilter(supplier)
    }
    if (search) {
      setSearchTerm(search)
    }
    // Mark that initial URL params have been processed
    setInitialLoadComplete(true)
    // Load initial data
    loadSuppliers()
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  // Load parts when supplier filter changes OR on initial load
  useEffect(() => {
    // Only load parts after initial URL params have been processed
    if (initialLoadComplete) {
      loadParts(1, searchTerm)
    }
  }, [supplierFilter, initialLoadComplete]) // eslint-disable-line react-hooks/exhaustive-deps

  // Load suppliers for image display
  const loadSuppliers = async () => {
    try {
      const suppliers = await supplierService.getSuppliers()
      const imageMap: Record<string, string> = {}
      suppliers.forEach((supplier) => {
        if (supplier.image_url) {
          // Map both supplier_name and display_name to image_url
          imageMap[supplier.supplier_name.toLowerCase()] = supplier.image_url
          imageMap[supplier.display_name.toLowerCase()] = supplier.image_url
        }
      })
      setSupplierImageMap(imageMap)
    } catch (err) {
      console.error('Failed to load supplier images:', err)
      // Don't show error - this is just for visual enhancement
    }
  }

  // Reload parts when sorting changes
  useEffect(() => {
    if (parts.length > 0) {
      // Only reload if parts are already loaded
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

  // Handle search input change with debounced suggestions and auto-search
  const handleSearchInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = e.target.value
    setSearchTerm(value)

    // Clear existing suggestion timeout
    if (suggestionTimeout) {
      clearTimeout(suggestionTimeout)
    }

    // Clear existing search timeout
    if (searchTimeout) {
      clearTimeout(searchTimeout)
    }

    // Set new timeout for suggestions (only if 3+ chars)
    if (value.length >= 3) {
      const suggestionTimer = setTimeout(() => {
        fetchSuggestions(value)
      }, 300) // 300ms debounce
      setSuggestionTimeout(suggestionTimer)
    } else {
      setSuggestions([])
      setShowSuggestions(false)
    }

    // Set new timeout for auto-search (any length, including empty to show all)
    const searchTimer = setTimeout(() => {
      setShowSuggestions(false) // Hide suggestions when auto-searching
      loadParts(1, value)
    }, 500) // 500ms debounce for search
    setSearchTimeout(searchTimer)
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
        setActiveSuggestionIndex((prev) => (prev < suggestions.length - 1 ? prev + 1 : prev))
        break
      case 'ArrowUp':
        e.preventDefault()
        setActiveSuggestionIndex((prev) => (prev > 0 ? prev - 1 : -1))
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

  // Cleanup timeouts on unmount
  useEffect(() => {
    return () => {
      if (suggestionTimeout) {
        clearTimeout(suggestionTimeout)
      }
      if (searchTimeout) {
        clearTimeout(searchTimeout)
      }
    }
  }, [suggestionTimeout, searchTimeout])

  // Handle Escape key to deselect or exit bulk edit mode
  useEffect(() => {
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        // Don't handle escape if modal is open - let the modal handle it
        if (showBulkEditModal) {
          return
        }

        if (bulkEditMode) {
          if (selectedPartIds.size > 0) {
            // If items are selected, clear selection
            setSelectedPartIds(new Set())
          } else {
            // If no items selected, exit bulk edit mode
            exitBulkEditMode()
          }
        }
      }
    }

    document.addEventListener('keydown', handleEscape)
    return () => document.removeEventListener('keydown', handleEscape)
  }, [bulkEditMode, selectedPartIds.size, showBulkEditModal])

  const totalPages = Math.ceil(totalParts / pageSize)

  const handlePageChange = (page: number) => {
    if (page >= 1 && page <= totalPages) {
      loadParts(page, searchTerm)
    }
  }

  const handlePartClick = (partId: string, event?: React.MouseEvent) => {
    // In bulk edit mode, regular click toggles selection
    if (bulkEditMode) {
      togglePartSelection(partId)
      if (event) event.preventDefault()
      return
    }

    // Check if Ctrl/Cmd key is pressed (when NOT in bulk edit mode)
    if (event && (event.ctrlKey || event.metaKey)) {
      console.log('Ctrl+click detected, entering bulk edit mode')
      // Enter bulk edit mode and toggle selection
      setBulkEditMode(true)
      togglePartSelection(partId)
      event.preventDefault()
      event.stopPropagation()
      return
    }

    // Normal click - navigate to part details
    navigate(`/parts/${partId}`)
  }

  // Bulk edit functions
  const togglePartSelection = (partId: string) => {
    setSelectedPartIds((prev) => {
      const newSet = new Set(prev)
      if (newSet.has(partId)) {
        newSet.delete(partId)
      } else {
        newSet.add(partId)
      }
      return newSet
    })
  }

  const toggleAllOnPage = () => {
    if (selectedPartIds.size === parts.length && parts.every((p) => selectedPartIds.has(p.id))) {
      // All on page are selected, deselect all
      setSelectedPartIds(new Set())
    } else {
      // Select all on page
      setSelectedPartIds(new Set(parts.map((p) => p.id)))
    }
  }

  const selectAllInSearch = async () => {
    try {
      // If already all selected, deselect all
      if (selectedPartIds.size === totalParts) {
        setSelectedPartIds(new Set())
        return
      }

      // Build search params matching current filters
      const searchParamsObj = {
        search_term: searchTerm,
        supplier: supplierFilter || undefined,
        sort_by: sortBy,
        sort_order: sortOrder,
        page: 1,
        page_size: totalParts || 10000, // Request all results
      }

      console.log('Fetching all part IDs with params:', searchParamsObj)
      const response = await partsService.searchParts(searchParamsObj)

      // Extract all part IDs from response
      let allPartIds: string[] = []
      if (response.items && Array.isArray(response.items)) {
        allPartIds = response.items.map((p: Part) => p.id)
      } else if (response.data && response.data.items && Array.isArray(response.data.items)) {
        allPartIds = response.data.items.map((p: Part) => p.id)
      }

      console.log(`Selected all ${allPartIds.length} matching parts`)
      setSelectedPartIds(new Set(allPartIds))
    } catch (error) {
      console.error('Failed to select all parts:', error)
      toast.error('Failed to select all parts')
    }
  }

  const exitBulkEditMode = () => {
    setBulkEditMode(false)
    setSelectedPartIds(new Set())
    setLastClickedIndex(null)
  }

  const isAllOnPageSelected = parts.length > 0 && parts.every((p) => selectedPartIds.has(p.id))
  const isAllMatchingSelected = selectedPartIds.size === totalParts && totalParts > 0

  if (loading && parts.length === 0) {
    return <LoadingScreen />
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
            <Package className="w-6 h-6" />
            Parts Inventory
          </h1>
          <p className="text-secondary mt-1">Manage your parts inventory</p>
        </div>
        <div className="flex items-center gap-3">
          {!bulkEditMode ? (
            <>
              <button
                onClick={() => setBulkEditMode(true)}
                className="btn btn-secondary flex items-center gap-2"
                title="Enter bulk edit mode (or Ctrl+click rows)"
              >
                <Edit3 className="w-4 h-4" />
                Bulk Edit
              </button>
              <PermissionGuard permission="parts:create">
                <button
                  onClick={() => setShowAddModal(true)}
                  className="btn btn-primary flex items-center gap-2"
                >
                  <Plus className="w-4 h-4" />
                  Add Part
                </button>
              </PermissionGuard>
            </>
          ) : (
            <button
              onClick={exitBulkEditMode}
              className="btn btn-secondary flex items-center gap-2"
            >
              <X className="w-4 h-4" />
              Exit Bulk Edit
            </button>
          )}
        </div>
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
            <button type="button" onClick={clearSearch} className="btn btn-secondary">
              Clear
            </button>
          )}

          <button type="button" className="btn btn-secondary flex items-center gap-2">
            <Filter className="w-4 h-4" />
            Filters
          </button>
        </form>

        {/* Active filters display */}
        {(supplierFilter || (isSearching && searchTerm)) && (
          <div className="mt-3 flex flex-wrap gap-2 items-center">
            <span className="text-sm text-muted">Active filters:</span>

            {supplierFilter && (
              <div className="inline-flex items-center gap-2 px-3 py-1 bg-accent/10 border border-accent/30 rounded-full text-sm">
                <span className="text-accent">Supplier: {supplierFilter}</span>
                <button
                  type="button"
                  onClick={() => {
                    setSupplierFilter('')
                    loadParts(1, searchTerm)
                  }}
                  className="text-accent hover:text-accent-hover"
                  title="Clear supplier filter"
                >
                  <X className="w-3 h-3" />
                </button>
              </div>
            )}

            {isSearching && searchTerm && (
              <div className="text-sm text-muted">
                {loading
                  ? `Searching for "${searchTerm}"...`
                  : `Found ${totalParts} result${totalParts !== 1 ? 's' : ''}`}
              </div>
            )}
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
            <h2 className="text-lg font-semibold text-primary">Parts ({totalParts})</h2>
            {loading && <div className="text-sm text-muted">Loading...</div>}
          </div>
        </div>

        <div className="card-content p-0">
          {parts.length === 0 && !loading ? (
            <div className="text-center py-12">
              <Package className="w-16 h-16 text-muted mx-auto mb-4" />
              <h3 className="text-lg font-semibold text-primary mb-2">No Parts Found</h3>
              <p className="text-secondary mb-6">
                {searchTerm
                  ? 'No parts match your search criteria.'
                  : 'Start by adding your first part to the inventory.'}
              </p>
              {!searchTerm && (
                <button
                  onClick={() => setShowAddModal(true)}
                  className="btn btn-primary flex items-center gap-2 mx-auto"
                >
                  <Plus className="w-4 h-4" />
                  Add Your First Part
                </button>
              )}
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead className="bg-background-secondary border-b border-border">
                  <tr>
                    {bulkEditMode && (
                      <th className="px-2 py-3 text-left text-xs font-medium text-secondary uppercase tracking-wider w-10">
                        <button
                          onClick={selectAllInSearch}
                          className="flex items-center justify-center w-5 h-5 text-primary hover:text-primary-dark transition-colors"
                          title={
                            isAllMatchingSelected
                              ? `Deselect all ${totalParts} parts`
                              : `Select all ${totalParts} matching parts`
                          }
                        >
                          {isAllMatchingSelected ? (
                            <CheckSquare className="w-5 h-5 text-blue-600" />
                          ) : (
                            <Square className="w-5 h-5" />
                          )}
                        </button>
                      </th>
                    )}
                    <th className="px-2 py-3 text-left text-xs font-medium text-secondary uppercase tracking-wider w-16">
                      Image
                    </th>
                    <SortableHeader field="part_name">Name</SortableHeader>
                    <SortableHeader field="part_number">Part #</SortableHeader>
                    <SortableHeader field="quantity">Qty</SortableHeader>
                    <SortableHeader field="location">Location</SortableHeader>
                    <th className="px-3 py-3 text-left text-xs font-medium text-secondary uppercase tracking-wider">
                      Categories
                    </th>
                    <th className="px-3 py-3 text-left text-xs font-medium text-secondary uppercase tracking-wider">
                      Projects
                    </th>
                    <th className="px-3 py-3 text-left text-xs font-medium text-secondary uppercase tracking-wider">
                      Supplier
                    </th>
                    <SortableHeader field="created_at">Added</SortableHeader>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border">
                  {(parts || []).map((part) => {
                    const isSelected = selectedPartIds.has(part.id)
                    return (
                      <tr
                        key={part.id}
                        className={`transition-colors ${
                          isSelected
                            ? 'bg-blue-50 dark:bg-blue-900/20 hover:bg-blue-100 dark:hover:bg-blue-900/30'
                            : 'hover:bg-background-secondary/50'
                        }`}
                        onMouseDown={(e) => {
                          // Only handle Ctrl+click on the row itself, not on interactive elements
                          if (
                            (e.ctrlKey || e.metaKey) &&
                            (e.target as HTMLElement).tagName === 'TD'
                          ) {
                            e.preventDefault()
                            console.log('Ctrl+mousedown detected on row')
                            if (!bulkEditMode) {
                              setBulkEditMode(true)
                            }
                            togglePartSelection(part.id)
                          }
                        }}
                      >
                        {bulkEditMode && (
                          <td className="px-3 py-3 whitespace-nowrap w-12">
                            <button
                              onClick={() => togglePartSelection(part.id)}
                              className="flex items-center justify-center w-5 h-5 text-primary hover:text-primary-dark transition-colors"
                            >
                              {isSelected ? (
                                <CheckSquare className="w-5 h-5 text-blue-600" />
                              ) : (
                                <Square className="w-5 h-5" />
                              )}
                            </button>
                          </td>
                        )}
                        <td className="px-3 py-3 whitespace-nowrap">
                          <PartImage
                            imageUrl={part.image_url}
                            partName={part.name}
                            size="md"
                            showFallback={true}
                          />
                        </td>
                        <td className="px-3 py-3 whitespace-nowrap">
                          <div className="flex items-center gap-2">
                            <button
                              onMouseDown={(e) => {
                                // Check for Ctrl+click
                                if (e.ctrlKey || e.metaKey) {
                                  e.preventDefault()
                                  console.log('Ctrl+mousedown detected on part name')
                                  if (!bulkEditMode) {
                                    setBulkEditMode(true)
                                  }
                                  togglePartSelection(part.id)
                                }
                              }}
                              onClick={(e) => {
                                // Don't handle click if Ctrl was pressed (handled in mousedown)
                                if (e.ctrlKey || e.metaKey) {
                                  e.preventDefault()
                                  return
                                }
                                handlePartClick(part.id, e)
                              }}
                              className="text-sm font-medium text-primary hover:text-primary-dark hover:underline transition-colors cursor-pointer"
                              title={
                                bulkEditMode
                                  ? 'Click to select, Ctrl+click to toggle'
                                  : 'Click to view part details, Ctrl+click to enter bulk edit'
                              }
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
                        <td className="px-3 py-3 whitespace-nowrap text-sm text-secondary">
                          {part.part_number ? (
                            <div className="flex items-center gap-2">
                              <button
                                onMouseDown={(e) => {
                                  // Check for Ctrl+click
                                  if (e.ctrlKey || e.metaKey) {
                                    e.preventDefault()
                                    console.log('Ctrl+mousedown detected on part number')
                                    if (!bulkEditMode) {
                                      setBulkEditMode(true)
                                    }
                                    togglePartSelection(part.id)
                                  }
                                }}
                                onClick={(e) => {
                                  // Don't handle click if Ctrl was pressed (handled in mousedown)
                                  if (e.ctrlKey || e.metaKey) {
                                    e.preventDefault()
                                    return
                                  }
                                  handlePartClick(part.id, e)
                                }}
                                className="text-sm text-secondary hover:text-primary hover:underline transition-colors cursor-pointer"
                                title={
                                  bulkEditMode
                                    ? 'Click to select, Ctrl+click to toggle'
                                    : 'Click to view part details, Ctrl+click to enter bulk edit'
                                }
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
                        <td className="px-3 py-3 whitespace-nowrap">
                          <div className="flex items-center gap-2">
                            <span
                              className={`text-sm font-medium ${
                                part.minimum_quantity && part.quantity <= part.minimum_quantity
                                  ? 'text-red-400'
                                  : 'text-primary'
                              }`}
                            >
                              {part.total_quantity !== undefined
                                ? part.total_quantity
                                : part.quantity}
                            </span>
                            {part.location_count !== undefined && part.location_count > 1 && (
                              <span
                                className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-blue-100 dark:bg-blue-900/30 text-blue-800 dark:text-blue-200"
                                title={`Split across ${part.location_count} locations`}
                              >
                                <MapPin className="w-3 h-3" />
                                {part.location_count}
                              </span>
                            )}
                          </div>
                          {part.minimum_quantity && (
                            <div className="text-xs text-muted">Min: {part.minimum_quantity}</div>
                          )}
                        </td>
                        <td className="px-3 py-3 whitespace-nowrap text-sm text-secondary">
                          <div className="flex items-center gap-1">
                            {part.primary_location?.name || part.location?.name || '-'}
                            {part.primary_location && (
                              <span
                                className="text-xs text-blue-600 dark:text-blue-400"
                                title="Primary storage location"
                              >
                                ★
                              </span>
                            )}
                          </div>
                        </td>
                        <td className="px-3 py-3 whitespace-nowrap text-sm text-secondary">
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
                          ) : (
                            '-'
                          )}
                        </td>
                        <td className="px-3 py-3 whitespace-nowrap text-sm text-secondary">
                          {part.projects && part.projects.length > 0 ? (
                            <div className="flex flex-wrap gap-1">
                              {part.projects.map((project, index) => (
                                <span
                                  key={project.id}
                                  className="inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium bg-purple-600/20 text-purple-400 border border-purple-600/50"
                                >
                                  <Hash className="w-3 h-3" />
                                  {project.name}
                                </span>
                              ))}
                            </div>
                          ) : (
                            '-'
                          )}
                        </td>
                        <td className="px-3 py-3 whitespace-nowrap text-sm text-secondary">
                          {part.supplier ? (
                            <div className="flex items-center gap-2">
                              {supplierImageMap[part.supplier.toLowerCase()] ? (
                                <>
                                  <img
                                    src={supplierImageMap[part.supplier.toLowerCase()]}
                                    alt={part.supplier}
                                    className="w-6 h-6 rounded object-contain"
                                    title={part.supplier}
                                    onError={(e) => {
                                      e.currentTarget.style.display = 'none'
                                    }}
                                  />
                                  <span className="text-xs text-muted">{part.supplier}</span>
                                </>
                              ) : (
                                <span>{part.supplier}</span>
                              )}
                            </div>
                          ) : (
                            '-'
                          )}
                        </td>
                        <td className="px-3 py-3 whitespace-nowrap text-sm text-secondary">
                          {formatDate(part.created_at)}
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
          )}
        </div>

        {/* Floating Action Bar for Bulk Edit */}
        {bulkEditMode && selectedPartIds.size > 0 && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 20 }}
            className="fixed bottom-8 left-1/2 transform -translate-x-1/2 z-40"
          >
            <div className="bg-blue-600 text-white rounded-lg shadow-2xl px-6 py-4 flex items-center gap-6 border border-blue-500">
              <div className="flex items-center gap-2">
                <CheckSquare className="w-5 h-5" />
                <span className="font-semibold">
                  {selectedPartIds.size} {selectedPartIds.size === 1 ? 'part' : 'parts'} selected
                </span>
              </div>

              <div className="h-6 w-px bg-blue-400" />

              {selectedPartIds.size < totalParts && (
                <button
                  onClick={selectAllInSearch}
                  className="text-sm hover:text-blue-100 transition-colors flex items-center gap-1"
                >
                  Select all {totalParts} {isSearching ? 'in search' : 'parts'}
                </button>
              )}

              <button
                onClick={() => setShowBulkEditModal(true)}
                className="btn bg-white text-blue-600 hover:bg-blue-50 flex items-center gap-2 font-semibold"
              >
                <Edit3 className="w-4 h-4" />
                Edit Selected
              </button>

              <button
                onClick={() => setSelectedPartIds(new Set())}
                className="text-sm hover:text-blue-100 transition-colors"
              >
                Clear
              </button>
            </div>
          </motion.div>
        )}

        {/* Pagination */}
        {totalPages > 1 && (
          <div className="card-footer border-t border-border">
            <div className="flex items-center justify-between">
              <div className="text-sm text-muted">
                Showing {(currentPage - 1) * pageSize + 1} to{' '}
                {Math.min(currentPage * pageSize, totalParts)} of {totalParts} parts
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
                          page === currentPage ? 'btn-primary' : 'btn-secondary'
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

      {/* Bulk Edit Modal */}
      <BulkEditModal
        isOpen={showBulkEditModal}
        onClose={() => setShowBulkEditModal(false)}
        onSuccess={() => {
          loadParts(currentPage, searchTerm)
          setSelectedPartIds(new Set())
          setBulkEditMode(false)
        }}
        selectedPartIds={Array.from(selectedPartIds)}
        selectedCount={selectedPartIds.size}
      />
    </div>
  )
}

export default PartsPage
