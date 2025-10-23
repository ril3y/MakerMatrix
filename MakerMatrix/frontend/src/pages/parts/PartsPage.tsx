import { motion } from 'framer-motion'
import {
  Package,
  Plus,
  Search,
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
  Tag as TagIcon,
  HelpCircle,
  Loader2,
} from 'lucide-react'
import { useState, useEffect, useRef } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { partsService } from '@/services/parts.service'
import { supplierService } from '@/services/supplier.service'
import type { Part } from '@/types/parts'
import type { Tag } from '@/types/tags'
import AddPartModal from '@/components/parts/AddPartModal'
import BulkEditModal from '@/components/parts/BulkEditModal'
import PartImage from '@/components/parts/PartImage'
import { PermissionGuard } from '@/components/auth/PermissionGuard'
import TagBadge from '@/components/tags/TagBadge'
import TagFilter from '@/components/tags/TagFilter'
import TagManagementModal from '@/components/tags/TagManagementModal'

const PartsPage = () => {
  const [searchParams] = useSearchParams()
  const [showAddModal, setShowAddModal] = useState(false)
  const [showBulkEditModal, setShowBulkEditModal] = useState(false)
  const [parts, setParts] = useState<Part[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [currentPage, setCurrentPage] = useState(1)
  const [totalParts, setTotalParts] = useState(0)

  // Simplified state - separate concerns like global search
  const [searchTerm, setSearchTerm] = useState(searchParams.get('search') || '')
  const [supplierFilter, setSupplierFilter] = useState(searchParams.get('supplier') || '')

  const [isSearching, setIsSearching] = useState(false)
  const isFirstRender = useRef(true)

  // Infinite scroll state
  const [hasMore, setHasMore] = useState(true)
  const loadMoreRef = useRef<HTMLDivElement>(null)

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

  // Supplier state for logo display
  const [supplierImageMap, setSupplierImageMap] = useState<Record<string, string>>({})

  // Bulk edit mode state
  const [bulkEditMode, setBulkEditMode] = useState(false)
  const [selectedPartIds, setSelectedPartIds] = useState<Set<string>>(new Set())

  // Tag filtering state
  const [selectedTags, setSelectedTags] = useState<Tag[]>([])
  const [tagFilterMode, setTagFilterMode] = useState<'AND' | 'OR'>('OR')
  const [showTagManagement, setShowTagManagement] = useState(false)

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
  // Simplified like global search - no complex parameters
  // append=true for infinite scroll, false for new searches/filters
  const loadParts = async (page = 1, append = false) => {
    try {
      // Don't clear parts or set loading - handle that in useEffects
      setError(null)

      // Always use advanced search API for sorting support
      const searchParamsObj = {
        search_term: searchTerm && searchTerm.trim() ? searchTerm.trim() : undefined,
        supplier: supplierFilter || undefined,
        sort_by: sortBy || 'created_at',
        sort_order: sortOrder || 'desc',
        page,
        page_size: pageSize,
      }

      console.log('Loading parts with:', {
        searchTerm,
        supplierFilter,
        sortBy,
        sortOrder,
        page,
        append,
      })
      const response = (await partsService.searchParts(searchParamsObj)) as unknown

      // Debug logging to understand response structure
      console.log('API response:', response)

      // Handle different response formats
      let partsData: Part[] = []
      let totalCount = 0

      // Type assertions for response format checking
      const hasItems = (obj: unknown): obj is { items: Part[]; total?: number } => {
        return (
          typeof obj === 'object' &&
          obj !== null &&
          'items' in obj &&
          Array.isArray((obj as { items: unknown }).items)
        )
      }

      const hasData = (obj: unknown): obj is { data: unknown; total_parts?: number } => {
        return typeof obj === 'object' && obj !== null && 'data' in obj
      }

      if (hasItems(response)) {
        // Direct PaginatedResponse format (from searchParts)
        partsData = response.items
        totalCount = response.total || 0
      } else if (hasData(response) && hasItems(response.data)) {
        // Wrapped PaginatedResponse format: { data: { items: [...], total: ... } }
        partsData = response.data.items
        totalCount = response.data.total || 0
      } else if (hasData(response) && Array.isArray(response.data)) {
        // Legacy format (getAllParts): { data: [...], total_parts: ... }
        partsData = response.data as Part[]
        totalCount = response.total_parts || 0
      } else if (Array.isArray(response)) {
        // Direct array response
        partsData = response as Part[]
        totalCount = (response as Part[]).length
      }

      // Map backend fields to frontend format if needed
      const mappedParts = partsData.map((part: Part) => ({
        ...part,
        name: part.part_name || part.name,
        categories: part.categories || [],
        created_at: part.created_at || new Date().toISOString(),
        updated_at: part.updated_at || new Date().toISOString(),
      }))

      console.log('Final mapped parts:', mappedParts, 'Total:', totalCount)

      // Apply client-side tag filtering
      let filteredParts = mappedParts
      if (selectedTags.length > 0) {
        filteredParts = mappedParts.filter((part: Part) => {
          const partTagIds = (part as Part & { tags?: Tag[] }).tags?.map((t: Tag) => t.id) || []
          if (tagFilterMode === 'AND') {
            // All selected tags must be present
            return selectedTags.every((tag) => partTagIds.includes(tag.id))
          } else {
            // At least one selected tag must be present
            return selectedTags.some((tag) => partTagIds.includes(tag.id))
          }
        })
        console.log(`Filtered ${mappedParts.length} parts to ${filteredParts.length} based on tags`)
      }

      // Append vs replace logic for infinite scroll
      if (append) {
        setParts((prev) => [...prev, ...filteredParts])
      } else {
        setParts(filteredParts)
      }

      // Update total and page state
      setTotalParts(selectedTags.length > 0 ? filteredParts.length : totalCount)
      setCurrentPage(page)

      // Update hasMore flag for infinite scroll
      // Only use infinite scroll when not doing client-side tag filtering
      if (selectedTags.length === 0) {
        const totalLoaded = append ? parts.length + filteredParts.length : filteredParts.length
        setHasMore(totalLoaded < totalCount)
        console.log(
          `Infinite scroll: loaded ${totalLoaded}/${totalCount}, hasMore: ${totalLoaded < totalCount}`
        )
      } else {
        // All results already loaded when tag filtering
        setHasMore(false)
      }
    } catch (err) {
      const _error = err as {
        response?: { data?: { error?: string; message?: string; detail?: string }; status?: number }
        message?: string
      }
      console.error('Error loading parts:', err)
      setError(_error.response?.data?.error || _error.message || 'Failed to load parts')
      // Set empty array on error to prevent map issues
      setParts([])
      setTotalParts(0)
    } finally {
      setLoading(false)
    }
  }

  // Load suppliers on mount
  useEffect(() => {
    loadSuppliers()
  }, [])

  // Sync with URL params (browser back/forward navigation)
  useEffect(() => {
    const supplier = searchParams.get('supplier') || ''
    const search = searchParams.get('search') || ''

    setSearchTerm(search)
    setSupplierFilter(supplier)
  }, [searchParams])

  // Initial load
  useEffect(() => {
    setLoading(true)
    loadParts().finally(() => {
      setLoading(false)
      isFirstRender.current = false
    })
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  // Search with debounce (like global search - 300ms)
  useEffect(() => {
    if (isFirstRender.current) return

    // Reset pagination when search changes
    setCurrentPage(1)
    setHasMore(true)
    setIsSearching(true)

    const timeoutId = setTimeout(() => {
      loadParts(1).finally(() => setIsSearching(false))
    }, 300) // 300ms debounce like global search

    return () => clearTimeout(timeoutId)
  }, [searchTerm]) // eslint-disable-line react-hooks/exhaustive-deps

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

  // Reload when supplier filter changes (with loading state)
  useEffect(() => {
    if (isFirstRender.current) return

    // Reset pagination when supplier filter changes
    setCurrentPage(1)
    setHasMore(true)
    setLoading(true)

    loadParts(1).finally(() => setLoading(false))
  }, [supplierFilter]) // eslint-disable-line react-hooks/exhaustive-deps

  // Reload when tags change (client-side filtering, with loading state)
  useEffect(() => {
    if (isFirstRender.current) return

    // Reset pagination when tags change (though tags use client-side filtering)
    setCurrentPage(1)
    setHasMore(false) // No pagination when filtering by tags
    setLoading(true)

    loadParts(1).finally(() => setLoading(false))
  }, [selectedTags, tagFilterMode]) // eslint-disable-line react-hooks/exhaustive-deps

  // Reload when sorting changes (with loading state)
  useEffect(() => {
    if (isFirstRender.current) return

    // Reset pagination when sorting changes
    setCurrentPage(1)
    setHasMore(true)
    setLoading(true)

    loadParts(1).finally(() => setLoading(false))
  }, [sortBy, sortOrder]) // eslint-disable-line react-hooks/exhaustive-deps

  // Infinite scroll: load more when user scrolls to bottom
  useEffect(() => {
    if (!loadMoreRef.current || !hasMore || loading || selectedTags.length > 0) return

    // Copy ref to local variable for cleanup
    const currentElement = loadMoreRef.current

    const observer = new IntersectionObserver(
      (entries) => {
        const [entry] = entries
        if (entry.isIntersecting && hasMore && !loading) {
          console.log('Loading more parts, current page:', currentPage)
          loadParts(currentPage + 1, true) // append=true for infinite scroll
        }
      },
      {
        root: null, // viewport
        rootMargin: '100px', // trigger 100px before reaching bottom
        threshold: 0.1,
      }
    )

    observer.observe(currentElement)

    return () => {
      if (currentElement) {
        observer.unobserve(currentElement)
      }
    }
  }, [hasMore, loading, currentPage, selectedTags.length]) // eslint-disable-line react-hooks/exhaustive-deps

  const handlePartAdded = () => {
    // Reset to first page and reload when a new part is added
    setCurrentPage(1)
    setHasMore(true)
    setLoading(true)
    loadParts(1).finally(() => setLoading(false))
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

  // Handle search input change - simplified like global search
  const handleSearchInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = e.target.value
    setSearchTerm(value) // Just update state - useEffect handles debounced search

    // Clear existing suggestion timeout
    if (suggestionTimeout) {
      clearTimeout(suggestionTimeout)
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
  }

  // Handle search form submission
  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault()
    setShowSuggestions(false)
    // No need to call loadParts - useEffect handles it
  }

  // Handle suggestion selection
  const handleSuggestionClick = (suggestion: string) => {
    setSearchTerm(suggestion)
    setShowSuggestions(false)
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
    }
  }, [suggestionTimeout])

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

      // Extract all part IDs from response using same pattern as loadParts
      let allPartIds: string[] = []
      if (response.items && Array.isArray(response.items)) {
        allPartIds = response.items.map((p: Part) => p.id)
      } else if (Array.isArray(response)) {
        allPartIds = response.map((p: Part) => p.id)
      }

      console.log(`Selected all ${allPartIds.length} matching parts`)
      setSelectedPartIds(new Set(allPartIds))
    } catch (error) {
      console.error('Failed to select all parts:', error)
      // Note: toast is not imported, using console.error instead
    }
  }

  const exitBulkEditMode = () => {
    setBulkEditMode(false)
    setSelectedPartIds(new Set())
  }

  const isAllOnPageSelected = parts.length > 0 && parts.every((p) => selectedPartIds.has(p.id))

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
              <PermissionGuard permission="tags:update">
                <button
                  onClick={() => setShowTagManagement(true)}
                  className="btn btn-secondary flex items-center gap-2"
                  title="Manage tags"
                >
                  <TagIcon className="w-4 h-4" />
                  Manage Tags
                </button>
              </PermissionGuard>
              <PermissionGuard permission="parts:update">
                <button
                  onClick={() => setBulkEditMode(true)}
                  className="btn btn-secondary flex items-center gap-2"
                  title="Enter bulk edit mode (or Ctrl+click rows)"
                >
                  <Edit3 className="w-4 h-4" />
                  Bulk Edit
                </button>
              </PermissionGuard>
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
              className="input pl-10 pr-16 w-full"
              autoComplete="off"
            />

            {/* Clear search button */}
            {searchTerm && (
              <button
                type="button"
                onClick={clearSearch}
                className="absolute right-10 top-1/2 transform -translate-y-1/2 w-4 h-4 text-muted hover:text-primary transition-colors"
              >
                <X className="w-4 h-4" />
              </button>
            )}

            {/* Advanced search help icon */}
            <div className="absolute right-3 top-1/2 transform -translate-y-1/2 group">
              <HelpCircle className="w-4 h-4 text-muted hover:text-primary transition-colors cursor-help" />

              {/* Tooltip */}
              <div className="invisible group-hover:visible absolute right-0 top-full mt-2 w-80 bg-background-primary border border-border rounded-lg shadow-2xl p-4 z-[9999]">
                <div className="text-sm space-y-2">
                  <div className="font-semibold text-primary mb-2">Advanced Search Syntax:</div>

                  <div className="space-y-1.5 text-secondary">
                    <div>
                      <code className="bg-background-secondary px-1.5 py-0.5 rounded text-xs">
                        desc:capacitor
                      </code>{' '}
                      - Search in description only
                    </div>
                    <div>
                      <code className="bg-background-secondary px-1.5 py-0.5 rounded text-xs">
                        pn:STM32
                      </code>{' '}
                      - Search in part number only
                    </div>
                    <div>
                      <code className="bg-background-secondary px-1.5 py-0.5 rounded text-xs">
                        name:resistor
                      </code>{' '}
                      - Search in name only
                    </div>
                    <div>
                      <code className="bg-background-secondary px-1.5 py-0.5 rounded text-xs">
                        prop:package 0603
                      </code>{' '}
                      - Search in properties
                    </div>
                    <div>
                      <code className="bg-background-secondary px-1.5 py-0.5 rounded text-xs">
                        tag:missing
                      </code>{' '}
                      - Find parts with no tags
                    </div>
                    <div className="pt-1 border-t border-border mt-2">
                      <code className="bg-background-secondary px-1.5 py-0.5 rounded text-xs">
                        "exact match"
                      </code>{' '}
                      - Search for exact phrase
                    </div>
                  </div>
                </div>

                {/* Arrow pointer */}
                <div className="absolute -top-2 right-2 w-0 h-0 border-l-8 border-l-transparent border-r-8 border-r-transparent border-b-8 border-b-border"></div>
              </div>
            </div>

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

          <TagFilter
            selectedTags={selectedTags}
            onFilterChange={(tags, mode) => {
              setSelectedTags(tags)
              setTagFilterMode(mode)
            }}
            entityType="parts"
          />
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
            {isSearching ? (
              <div className="flex items-center gap-2 text-sm text-muted">
                <Loader2 className="w-3 h-3 animate-spin" />
                <span>Searching...</span>
              </div>
            ) : (
              loading && <div className="text-sm text-muted">Loading...</div>
            )}
          </div>
        </div>

        <div className="card-content p-0">
          {loading && parts.length === 0 ? (
            <div className="flex items-center justify-center py-32">
              <Loader2 className="w-8 h-8 text-primary animate-spin" />
            </div>
          ) : parts.length === 0 ? (
            <div className="text-center py-12">
              <Package className="w-16 h-16 text-muted mx-auto mb-4" />
              <h3 className="text-lg font-semibold text-primary mb-2">
                {error ? 'Unable to Load Parts' : 'No Parts Found'}
              </h3>
              <p className="text-secondary mb-6">
                {error
                  ? 'There was a problem connecting to the server. Please check that the backend is running.'
                  : searchTerm || selectedTags.length > 0
                    ? 'No parts match your filters. Try adjusting your search or tag filters.'
                    : 'Start by adding your first part to the inventory.'}
              </p>
              {!searchTerm && selectedTags.length === 0 && !error && (
                <PermissionGuard permission="parts:create">
                  <button
                    onClick={() => setShowAddModal(true)}
                    className="btn btn-primary flex items-center gap-2 mx-auto"
                  >
                    <Plus className="w-4 h-4" />
                    Add Your First Part
                  </button>
                </PermissionGuard>
              )}
            </div>
          ) : (
            <div className="overflow-x-auto relative">
              {/* Loading overlay when fetching new data with existing parts displayed */}
              {/* Don't show overlay during search typing - it blocks typing */}
              {loading && parts.length > 0 && !isSearching && (
                <div className="absolute inset-0 bg-black/10 backdrop-blur-[1px] z-10 flex items-center justify-center">
                  <div className="bg-background-primary/90 rounded-lg p-4 shadow-lg flex items-center gap-3">
                    <Loader2 className="w-5 h-5 text-primary animate-spin" />
                    <span className="text-sm text-secondary">Updating results...</span>
                  </div>
                </div>
              )}
              <table className="w-full">
                <thead className="bg-gradient-to-r from-purple-600/20 to-blue-600/20 border-b border-purple-500/10">
                  <tr>
                    {bulkEditMode && (
                      <th className="px-2 py-3 text-left text-xs font-bold text-primary uppercase tracking-wider w-10">
                        <button
                          onClick={toggleAllOnPage}
                          className="flex items-center justify-center w-5 h-5 text-primary hover:text-primary-dark transition-colors"
                          title={
                            isAllOnPageSelected
                              ? `Deselect all ${parts.length} parts on this page`
                              : `Select all ${parts.length} parts on this page`
                          }
                        >
                          {isAllOnPageSelected ? (
                            <CheckSquare className="w-5 h-5 text-blue-600" />
                          ) : (
                            <Square className="w-5 h-5" />
                          )}
                        </button>
                      </th>
                    )}
                    <th className="px-2 py-3 text-left text-xs font-bold text-primary uppercase tracking-wider w-16">
                      Image
                    </th>
                    <SortableHeader field="part_name">Name</SortableHeader>
                    <SortableHeader field="part_number">Part #</SortableHeader>
                    <SortableHeader field="quantity">Qty</SortableHeader>
                    <SortableHeader field="location">Location</SortableHeader>
                    <th className="px-3 py-3 text-left text-xs font-bold text-primary uppercase tracking-wider">
                      Categories
                    </th>
                    <th className="px-3 py-3 text-left text-xs font-bold text-primary uppercase tracking-wider">
                      Tags
                    </th>
                    <th className="px-3 py-3 text-left text-xs font-bold text-primary uppercase tracking-wider">
                      Projects
                    </th>
                    <th className="px-3 py-3 text-left text-xs font-bold text-primary uppercase tracking-wider">
                      Supplier
                    </th>
                    <SortableHeader field="created_at">Added</SortableHeader>
                  </tr>
                </thead>
                <tbody className="divide-y divide-purple-500/10 bg-theme-elevated/50">
                  {(parts || []).map((part) => {
                    const isSelected = selectedPartIds.has(part.id)
                    return (
                      <tr
                        key={part.id}
                        className={`transition-all duration-200 ${
                          isSelected
                            ? 'bg-blue-50 dark:bg-blue-900/20 hover:bg-blue-100 dark:hover:bg-blue-900/30'
                            : 'hover:bg-gradient-to-r hover:from-purple-600/5 hover:to-blue-600/5'
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
                        <td className="px-3 py-3 whitespace-nowrap w-20">
                          <div className="flex items-center justify-center w-12 h-12">
                            <PartImage
                              imageUrl={part.image_url}
                              partName={part.name}
                              size="md"
                              showFallback={true}
                            />
                          </div>
                        </td>
                        <td className="px-3 py-3 whitespace-nowrap max-w-xs">
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
                              className="text-sm font-medium text-primary hover:text-primary-dark hover:underline transition-colors cursor-pointer truncate max-w-[250px]"
                              title={part.name}
                            >
                              {part.name}
                            </button>
                            <button
                              onClick={(e) => {
                                e.stopPropagation()
                                copyToClipboard(part.name, part.id, 'name')
                              }}
                              className="text-muted hover:text-primary transition-colors flex-shrink-0"
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
                              {String(part.additional_properties.description)}
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
                                className="text-sm text-secondary hover:text-primary hover:underline transition-colors cursor-pointer truncate max-w-[150px]"
                                title={part.part_number}
                              >
                                {part.part_number}
                              </button>
                              <button
                                onClick={(e) => {
                                  e.stopPropagation()
                                  copyToClipboard(part.part_number!, part.id, 'part_number')
                                }}
                                className="text-muted hover:text-primary transition-colors flex-shrink-0"
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
                              {part.categories.map((category) => (
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
                          {(part as Part & { tags?: Tag[] }).tags &&
                          (part as Part & { tags?: Tag[] }).tags.length > 0 ? (
                            <div className="flex flex-wrap gap-1">
                              {(part as Part & { tags?: Tag[] }).tags.map((tag: Tag) => (
                                <TagBadge
                                  key={tag.id}
                                  tag={tag}
                                  size="sm"
                                  onClick={() => {
                                    // Add tag to filter when clicked
                                    if (!selectedTags.find((t) => t.id === tag.id)) {
                                      setSelectedTags([...selectedTags, tag])
                                    }
                                  }}
                                />
                              ))}
                            </div>
                          ) : (
                            '-'
                          )}
                        </td>
                        <td className="px-3 py-3 whitespace-nowrap text-sm text-secondary">
                          {part.projects && part.projects.length > 0 ? (
                            <div className="flex flex-wrap gap-1">
                              {part.projects.map((project) => (
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

        {/* Infinite scroll load more indicator */}
        {parts.length > 0 && (
          <div className="card-footer border-t border-border">
            <div className="flex items-center justify-center py-4">
              {hasMore ? (
                <div ref={loadMoreRef} className="flex items-center gap-2 text-sm text-muted">
                  <Loader2 className="w-4 h-4 animate-spin" />
                  <span>Loading more parts...</span>
                </div>
              ) : (
                <div className="text-sm text-muted">
                  {selectedTags.length > 0
                    ? `Showing all ${totalParts} matching parts`
                    : `Showing all ${parts.length} parts`}
                </div>
              )}
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
          // Reset to first page and reload after bulk edit
          setCurrentPage(1)
          setHasMore(true)
          loadParts(1)
          setSelectedPartIds(new Set())
          setBulkEditMode(false)
        }}
        selectedPartIds={Array.from(selectedPartIds)}
        selectedCount={selectedPartIds.size}
      />

      {/* Tag Management Modal */}
      <TagManagementModal isOpen={showTagManagement} onClose={() => setShowTagManagement(false)} />
    </div>
  )
}

export default PartsPage
