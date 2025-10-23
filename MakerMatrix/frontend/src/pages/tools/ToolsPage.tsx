import { motion } from 'framer-motion'
import {
  Wrench,
  Plus,
  Search,
  ChevronLeft,
  ChevronRight,
  X,
  Copy,
  Check,
  ArrowUpDown,
  ArrowUp,
  ArrowDown,
  Edit3,
  Calendar,
  CheckCircle,
  XCircle,
  Tag as TagIcon,
} from 'lucide-react'
import { useState, useEffect, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { toolsService } from '@/services/tools.service'
import type { Tool } from '@/types/tools'
import type { Tag } from '@/types/tags'
import ToolModal from '@/components/tools/ToolModal'
import ToolDetailModal from '@/components/tools/ToolDetailModal'
import LoadingScreen from '@/components/ui/LoadingScreen'
import { PermissionGuard } from '@/components/auth/PermissionGuard'
import PartImage from '@/components/parts/PartImage'
import TagBadge from '@/components/tags/TagBadge'
import TagFilter from '@/components/tags/TagFilter'
import TagManagementModal from '@/components/tags/TagManagementModal'
import toast from 'react-hot-toast'

const ToolsPage = () => {
  const [showAddModal, setShowAddModal] = useState(false)
  const [showDetailModal, setShowDetailModal] = useState(false)
  const [selectedToolId, setSelectedToolId] = useState<string | null>(null)
  const [editingTool, setEditingTool] = useState<Tool | null>(null)
  const [tools, setTools] = useState<Tool[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [currentPage, setCurrentPage] = useState(1)
  const [totalTools, setTotalTools] = useState(0)
  const [searchTerm, setSearchTerm] = useState('')
  const [statusFilter, setStatusFilter] = useState<string>('')
  const [conditionFilter, setConditionFilter] = useState<string>('')
  const [isSearching, setIsSearching] = useState(false)

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

  // Clipboard state
  const [copiedItems, setCopiedItems] = useState<Record<string, 'name' | 'tool_number'>>({})

  // Tag filtering state
  const [selectedTags, setSelectedTags] = useState<Tag[]>([])
  const [tagFilterMode, setTagFilterMode] = useState<'AND' | 'OR'>('OR')
  const [showTagManagement, setShowTagManagement] = useState(false)

  const searchInputRef = useRef<HTMLInputElement>(null)
  const suggestionsRef = useRef<HTMLDivElement>(null)
  const pageSize = 20
  const navigate = useNavigate()

  // Condition color mapping
  const getConditionColor = (condition: string) => {
    switch (condition) {
      case 'excellent':
        return 'text-green-500'
      case 'good':
        return 'text-blue-500'
      case 'fair':
        return 'text-yellow-500'
      case 'poor':
        return 'text-orange-500'
      case 'needs_repair':
        return 'text-red-500'
      case 'out_of_service':
        return 'text-gray-500'
      default:
        return 'text-gray-500'
    }
  }

  // Status icon mapping (based on is_checked_out boolean)
  const getStatusIcon = (tool: Tool) => {
    if (tool.is_checked_out) {
      return <XCircle className="w-4 h-4 text-red-500" />
    }
    return <CheckCircle className="w-4 h-4 text-green-500" />
  }

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

  const copyToClipboard = async (text: string, toolId: string, type: 'name' | 'tool_number') => {
    try {
      await navigator.clipboard.writeText(text)
      setCopiedItems((prev) => ({ ...prev, [toolId]: type }))
      setTimeout(() => {
        setCopiedItems((prev) => {
          const newState = { ...prev }
          delete newState[toolId]
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
    if (sortBy === field) {
      setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc')
    } else {
      setSortBy(field)
      setSortOrder('asc')
    }
  }

  // Load tools
  const loadTools = async (page = 1, search = '') => {
    try {
      setLoading(true)
      setError(null)
      setIsSearching(search && search.trim().length > 0)

      const searchParams = {
        search_term: search && search.trim() ? search.trim() : undefined,
        status: statusFilter || undefined,
        condition: conditionFilter || undefined,
        sort_by: (sortBy as any) || 'created_at',
        sort_order: sortOrder || 'desc',
        page,
        page_size: pageSize,
      }

      const response = await toolsService.searchTools(searchParams)

      // Apply client-side tag filtering
      let filteredTools = response.items || []
      if (selectedTags.length > 0) {
        filteredTools = filteredTools.filter((tool: any) => {
          const toolTagIds = tool.tags?.map((t: Tag) => t.id) || []
          if (tagFilterMode === 'AND') {
            // All selected tags must be present
            return selectedTags.every((tag) => toolTagIds.includes(tag.id))
          } else {
            // At least one selected tag must be present
            return selectedTags.some((tag) => toolTagIds.includes(tag.id))
          }
        })
        console.log(
          `Filtered ${response.items?.length || 0} tools to ${filteredTools.length} based on tags`
        )
      }

      setTools(filteredTools)
      setTotalTools(selectedTags.length > 0 ? filteredTools.length : response.total || 0)
      setCurrentPage(page)
    } catch (err: any) {
      console.error('Error loading tools:', err)
      setError(err.message || 'Failed to load tools')
      setTools([])
      setTotalTools(0)
    } finally {
      setLoading(false)
    }
  }

  // Initial load
  useEffect(() => {
    loadTools(1, '')
  }, [])

  // Reload when filters or tags change
  useEffect(() => {
    loadTools(1, searchTerm)
  }, [statusFilter, conditionFilter, sortBy, sortOrder, selectedTags, tagFilterMode])

  const handleToolAdded = () => {
    loadTools(currentPage, searchTerm)
  }

  // Fetch suggestions with debouncing
  const fetchSuggestions = async (query: string) => {
    if (query.length < 3) {
      setSuggestions([])
      setShowSuggestions(false)
      return
    }

    try {
      const suggestions = await toolsService.getToolSuggestions(query, 8)
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

    // Clear existing timeouts
    if (suggestionTimeout) {
      clearTimeout(suggestionTimeout)
    }
    if (searchTimeout) {
      clearTimeout(searchTimeout)
    }

    // Set new timeout for suggestions (only if 3+ chars)
    if (value.length >= 3) {
      const suggestionTimer = setTimeout(() => {
        fetchSuggestions(value)
      }, 300)
      setSuggestionTimeout(suggestionTimer)
    } else {
      setSuggestions([])
      setShowSuggestions(false)
    }

    // Set new timeout for auto-search
    const searchTimer = setTimeout(() => {
      setShowSuggestions(false)
      loadTools(1, value)
    }, 500)
    setSearchTimeout(searchTimer)
  }

  // Handle search form submission
  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault()
    setShowSuggestions(false)
    loadTools(1, searchTerm)
  }

  // Handle suggestion selection
  const handleSuggestionClick = (suggestion: string) => {
    setSearchTerm(suggestion)
    setShowSuggestions(false)
    loadTools(1, suggestion)
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
    loadTools(1, '')
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

  const totalPages = Math.ceil(totalTools / pageSize)

  const handlePageChange = (page: number) => {
    if (page >= 1 && page <= totalPages) {
      loadTools(page, searchTerm)
    }
  }

  const handleToolClick = (tool: Tool) => {
    setSelectedToolId(tool.id)
    setShowDetailModal(true)
  }

  const handleEditTool = (tool: Tool) => {
    setEditingTool(tool)
    setShowAddModal(true)
  }

  const handleDeleteTool = async (toolId: string) => {
    if (window.confirm('Are you sure you want to delete this tool?')) {
      try {
        await toolsService.deleteTool(toolId)
        toast.success('Tool deleted successfully')
        loadTools(currentPage, searchTerm)
      } catch (error: any) {
        toast.error(error.message || 'Failed to delete tool')
      }
    }
  }

  if (loading && tools.length === 0) {
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
            <Wrench className="w-6 h-6" />
            Tools Inventory
          </h1>
          <p className="text-secondary mt-1">Manage your tools and equipment</p>
        </div>
        <div className="flex items-center gap-3">
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
          <PermissionGuard permission="tools:create">
            <button
              onClick={() => {
                setEditingTool(null)
                setShowAddModal(true)
              }}
              className="btn btn-primary flex items-center gap-2"
            >
              <Plus className="w-4 h-4" />
              Add Tool
            </button>
          </PermissionGuard>
        </div>
      </motion.div>

      {/* Search and Filters */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.1 }}
        className="card p-4"
      >
        <form onSubmit={handleSearch} className="space-y-3">
          {/* Search bar */}
          <div className="relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-muted" />
            <input
              ref={searchInputRef}
              type="text"
              placeholder="Search tools by name, number, manufacturer, or description..."
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

          {/* Filters row */}
          <div className="flex gap-3">
            {/* Status Filter */}
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="input w-40"
            >
              <option value="">All Status</option>
              <option value="available">Available</option>
              <option value="checked_out">Checked Out</option>
              <option value="maintenance">Maintenance</option>
              <option value="retired">Retired</option>
            </select>

            {/* Condition Filter */}
            <select
              value={conditionFilter}
              onChange={(e) => setConditionFilter(e.target.value)}
              className="input w-40"
            >
              <option value="">All Conditions</option>
              <option value="excellent">Excellent</option>
              <option value="good">Good</option>
              <option value="fair">Fair</option>
              <option value="poor">Poor</option>
              <option value="needs_repair">Needs Repair</option>
              <option value="out_of_service">Out of Service</option>
            </select>

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
              entityType="tools"
            />
          </div>
        </form>

        {/* Active filters display */}
        {(statusFilter || conditionFilter || (isSearching && searchTerm)) && (
          <div className="mt-3 flex flex-wrap gap-2 items-center">
            <span className="text-sm text-muted">Active filters:</span>

            {statusFilter && (
              <div className="inline-flex items-center gap-2 px-3 py-1 bg-accent/10 border border-accent/30 rounded-full text-sm">
                <span className="text-accent">Status: {statusFilter}</span>
                <button
                  type="button"
                  onClick={() => setStatusFilter('')}
                  className="text-accent hover:text-accent-hover"
                  title="Clear status filter"
                >
                  <X className="w-3 h-3" />
                </button>
              </div>
            )}

            {conditionFilter && (
              <div className="inline-flex items-center gap-2 px-3 py-1 bg-accent/10 border border-accent/30 rounded-full text-sm">
                <span className="text-accent">Condition: {conditionFilter}</span>
                <button
                  type="button"
                  onClick={() => setConditionFilter('')}
                  className="text-accent hover:text-accent-hover"
                  title="Clear condition filter"
                >
                  <X className="w-3 h-3" />
                </button>
              </div>
            )}

            {isSearching && searchTerm && (
              <div className="text-sm text-muted">
                {loading
                  ? `Searching for "${searchTerm}"...`
                  : `Found ${totalTools} result${totalTools !== 1 ? 's' : ''}`}
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

      {/* Tools List */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.2 }}
        className="card"
      >
        <div className="card-header">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-semibold text-primary">Tools ({totalTools})</h2>
            {loading && <div className="text-sm text-muted">Loading...</div>}
          </div>
        </div>

        <div className="card-content p-0">
          {tools.length === 0 && !loading ? (
            <div className="text-center py-12">
              <Wrench className="w-16 h-16 text-muted mx-auto mb-4" />
              <h3 className="text-lg font-semibold text-primary mb-2">No Tools Found</h3>
              <p className="text-secondary mb-6">
                {searchTerm
                  ? 'No tools match your search criteria.'
                  : 'Start by adding your first tool to the inventory.'}
              </p>
              {!searchTerm && (
                <button
                  onClick={() => {
                    setEditingTool(null)
                    setShowAddModal(true)
                  }}
                  className="btn btn-primary flex items-center gap-2 mx-auto"
                >
                  <Plus className="w-4 h-4" />
                  Add Your First Tool
                </button>
              )}
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead className="bg-gradient-to-r from-purple-600/20 to-blue-600/20 border-b border-purple-500/10">
                  <tr>
                    <th className="px-2 py-3 text-left text-xs font-bold text-primary uppercase tracking-wider w-10">
                      Status
                    </th>
                    <SortableHeader field="name">Name</SortableHeader>
                    <SortableHeader field="tool_number">Tool #</SortableHeader>
                    <th className="px-3 py-3 text-left text-xs font-bold text-primary uppercase tracking-wider">
                      Manufacturer
                    </th>
                    <SortableHeader field="condition">Condition</SortableHeader>
                    <th className="px-3 py-3 text-left text-xs font-bold text-primary uppercase tracking-wider">
                      Tags
                    </th>
                    <th className="px-3 py-3 text-left text-xs font-bold text-primary uppercase tracking-wider">
                      Location
                    </th>
                    <th className="px-3 py-3 text-left text-xs font-bold text-primary uppercase tracking-wider">
                      Checked Out
                    </th>
                    <th className="px-3 py-3 text-left text-xs font-bold text-primary uppercase tracking-wider">
                      Next Maint.
                    </th>
                    <SortableHeader field="created_at">Added</SortableHeader>
                    <th className="px-3 py-3 text-left text-xs font-bold text-primary uppercase tracking-wider">
                      Actions
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-purple-500/10 bg-theme-elevated/50">
                  {tools.map((tool) => (
                    <tr
                      key={tool.id}
                      className="hover:bg-gradient-to-r hover:from-purple-600/5 hover:to-blue-600/5 transition-all duration-200 cursor-pointer"
                      onClick={() => handleToolClick(tool)}
                    >
                      <td className="px-3 py-3 whitespace-nowrap">
                        {tool.image_url ? (
                          <div className="w-10 h-10 flex items-center justify-center">
                            <PartImage
                              imageUrl={tool.image_url}
                              partName={tool.tool_name}
                              size="sm"
                              showFallback={false}
                              className="w-10 h-10 rounded object-contain"
                            />
                          </div>
                        ) : (
                          getStatusIcon(tool)
                        )}
                      </td>
                      <td className="px-3 py-3 whitespace-nowrap max-w-xs">
                        <div className="flex items-center gap-2">
                          <button
                            onClick={(e) => {
                              e.stopPropagation()
                              handleToolClick(tool)
                            }}
                            className="text-sm font-medium text-primary hover:text-primary-dark hover:underline transition-colors cursor-pointer truncate max-w-[250px]"
                            title={tool.tool_name}
                          >
                            {tool.tool_name}
                          </button>
                          <button
                            onClick={(e) => {
                              e.stopPropagation()
                              copyToClipboard(tool.tool_name, tool.id, 'name')
                            }}
                            className="text-muted hover:text-primary transition-colors flex-shrink-0"
                            title="Copy tool name"
                          >
                            {copiedItems[tool.id] === 'name' ? (
                              <Check className="w-4 h-4 text-green-500" />
                            ) : (
                              <Copy className="w-4 h-4" />
                            )}
                          </button>
                        </div>
                        {tool.description && (
                          <div className="text-sm text-muted truncate max-w-xs">
                            {tool.description}
                          </div>
                        )}
                      </td>
                      <td className="px-3 py-3 whitespace-nowrap text-sm text-secondary">
                        {tool.tool_number ? (
                          <div className="flex items-center gap-2">
                            <span className="truncate max-w-[150px]" title={tool.tool_number}>
                              {tool.tool_number}
                            </span>
                            <button
                              onClick={(e) => {
                                e.stopPropagation()
                                copyToClipboard(tool.tool_number!, tool.id, 'tool_number')
                              }}
                              className="text-muted hover:text-primary transition-colors flex-shrink-0"
                              title="Copy tool number"
                            >
                              {copiedItems[tool.id] === 'tool_number' ? (
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
                      <td className="px-3 py-3 whitespace-nowrap text-sm text-secondary">
                        {tool.manufacturer ? (
                          <div>
                            <div>{tool.manufacturer}</div>
                            {tool.model_number && (
                              <div className="text-xs text-muted">{tool.model_number}</div>
                            )}
                          </div>
                        ) : (
                          '-'
                        )}
                      </td>
                      <td className="px-3 py-3 whitespace-nowrap">
                        <span
                          className={`text-sm font-medium ${getConditionColor(tool.condition)}`}
                        >
                          {tool.condition.charAt(0).toUpperCase() + tool.condition.slice(1)}
                        </span>
                      </td>
                      <td className="px-3 py-3 whitespace-nowrap text-sm text-secondary">
                        {(tool as any).tags && (tool as any).tags.length > 0 ? (
                          <div className="flex flex-wrap gap-1">
                            {(tool as any).tags.map((tag: Tag) => (
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
                        <div className="flex items-center gap-1">{tool.location?.name || '-'}</div>
                      </td>
                      <td className="px-3 py-3 whitespace-nowrap text-sm text-secondary">
                        {tool.checked_out_by ? (
                          <div>
                            <div className="text-red-500">{tool.checked_out_by}</div>
                            {tool.checked_out_at && (
                              <div className="text-xs text-muted">
                                Since {formatDate(tool.checked_out_at)}
                              </div>
                            )}
                          </div>
                        ) : (
                          '-'
                        )}
                      </td>
                      <td className="px-3 py-3 whitespace-nowrap text-sm text-secondary">
                        {tool.next_maintenance_date ? (
                          <div className="flex items-center gap-1">
                            <Calendar className="w-3 h-3" />
                            {formatDate(tool.next_maintenance_date)}
                          </div>
                        ) : (
                          '-'
                        )}
                      </td>
                      <td className="px-3 py-3 whitespace-nowrap text-sm text-secondary">
                        {formatDate(tool.created_at)}
                      </td>
                      <td className="px-3 py-3 whitespace-nowrap text-sm">
                        <div className="flex items-center gap-2">
                          <button
                            onClick={(e) => {
                              e.stopPropagation()
                              handleEditTool(tool)
                            }}
                            className="text-primary hover:text-primary-dark"
                            title="Edit tool"
                          >
                            <Edit3 className="w-4 h-4" />
                          </button>
                          <button
                            onClick={(e) => {
                              e.stopPropagation()
                              handleDeleteTool(tool.id)
                            }}
                            className="text-red-500 hover:text-red-600"
                            title="Delete tool"
                          >
                            <X className="w-4 h-4" />
                          </button>
                        </div>
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
                Showing {(currentPage - 1) * pageSize + 1} to{' '}
                {Math.min(currentPage * pageSize, totalTools)} of {totalTools} tools
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

      {/* Tool Modal */}
      <ToolModal
        isOpen={showAddModal}
        onClose={() => {
          setShowAddModal(false)
          setEditingTool(null)
        }}
        onSuccess={handleToolAdded}
        editingTool={editingTool}
      />

      {/* Tool Detail Modal */}
      {selectedToolId && (
        <ToolDetailModal
          isOpen={showDetailModal}
          onClose={() => {
            setShowDetailModal(false)
            setSelectedToolId(null)
          }}
          toolId={selectedToolId}
          onEdit={(tool) => {
            setShowDetailModal(false)
            handleEditTool(tool)
          }}
          onDelete={(toolId) => {
            setShowDetailModal(false)
            handleDeleteTool(toolId)
          }}
          onStatusChange={handleToolAdded}
        />
      )}

      {/* Tag Management Modal */}
      <TagManagementModal isOpen={showTagManagement} onClose={() => setShowTagManagement(false)} />
    </div>
  )
}

export default ToolsPage
