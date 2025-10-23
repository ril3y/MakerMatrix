import { useState, useEffect, useRef } from 'react'
import { Filter, X, ChevronDown } from 'lucide-react'
import { tagsService } from '@/services/tags.service'
import type { Tag } from '@/types/tags'
import TagBadge from './TagBadge'
import { motion, AnimatePresence } from 'framer-motion'

interface TagFilterProps {
  selectedTags: Tag[]
  onFilterChange: (tags: Tag[], mode: 'AND' | 'OR') => void
  entityType: 'parts' | 'tools'
  className?: string
}

const TagFilter = ({
  selectedTags,
  onFilterChange,
  entityType,
  className = '',
}: TagFilterProps) => {
  const [isOpen, setIsOpen] = useState(false)
  const [availableTags, setAvailableTags] = useState<Tag[]>([])
  const [loading, setLoading] = useState(false)
  const [searchQuery, setSearchQuery] = useState('')
  const [filterMode, setFilterMode] = useState<'AND' | 'OR'>('OR')

  const dropdownRef = useRef<HTMLDivElement>(null)

  // Load available tags
  const loadTags = async () => {
    try {
      setLoading(true)
      const response = await tagsService.getAllTags({
        entity_type: entityType,
        sort_by: 'usage',
        sort_order: 'desc',
        page_size: 100,
      })
      setAvailableTags(response.items || [])
    } catch (error) {
      console.error('Error loading tags:', error)
      setAvailableTags([])
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (isOpen && availableTags.length === 0) {
      loadTags()
    }
  }, [isOpen])

  // Filter tags based on search
  const filteredTags = availableTags.filter((tag) =>
    tag.name.toLowerCase().includes(searchQuery.toLowerCase())
  )

  // Toggle tag selection
  const toggleTag = (tag: Tag) => {
    const isSelected = selectedTags.find((t) => t.id === tag.id)

    if (isSelected) {
      const newTags = selectedTags.filter((t) => t.id !== tag.id)
      onFilterChange(newTags, filterMode)
    } else {
      onFilterChange([...selectedTags, tag], filterMode)
    }
  }

  // Clear all filters
  const clearAll = () => {
    onFilterChange([], filterMode)
    setIsOpen(false)
  }

  // Toggle filter mode
  const toggleMode = () => {
    const newMode = filterMode === 'AND' ? 'OR' : 'AND'
    setFilterMode(newMode)
    if (selectedTags.length > 0) {
      onFilterChange(selectedTags, newMode)
    }
  }

  // Click outside to close
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false)
      }
    }

    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  return (
    <div className={`relative ${className}`} ref={dropdownRef}>
      {/* Filter button */}
      <button
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        className={`btn btn-secondary flex items-center gap-2 ${
          selectedTags.length > 0 ? 'btn-accent' : ''
        }`}
      >
        <Filter className="w-4 h-4" />
        <span>Tags</span>
        {selectedTags.length > 0 && (
          <span className="px-2 py-0.5 bg-accent text-white rounded-full text-xs font-bold">
            {selectedTags.length}
          </span>
        )}
        <ChevronDown className={`w-4 h-4 transition-transform ${isOpen ? 'rotate-180' : ''}`} />
      </button>

      {/* Selected tags preview (inline) */}
      {selectedTags.length > 0 && !isOpen && (
        <div className="absolute left-full top-0 ml-2 flex items-center gap-1">
          <AnimatePresence>
            {selectedTags.slice(0, 3).map((tag) => (
              <TagBadge key={tag.id} tag={tag} size="sm" onClick={() => setIsOpen(true)} />
            ))}
          </AnimatePresence>
          {selectedTags.length > 3 && (
            <span className="text-xs text-muted">+{selectedTags.length - 3} more</span>
          )}
        </div>
      )}

      {/* Dropdown */}
      <AnimatePresence>
        {isOpen && (
          <motion.div
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            className="absolute top-full left-0 mt-2 w-80 bg-background-primary border border-border rounded-lg shadow-lg z-50"
          >
            <div className="p-4 space-y-3">
              {/* Header */}
              <div className="flex items-center justify-between">
                <h3 className="text-sm font-semibold text-primary">Filter by Tags</h3>
                {selectedTags.length > 0 && (
                  <button
                    type="button"
                    onClick={clearAll}
                    className="text-xs text-accent hover:text-accent-hover transition-colors"
                  >
                    Clear all
                  </button>
                )}
              </div>

              {/* Filter mode toggle */}
              {selectedTags.length > 1 && (
                <div className="flex items-center gap-2 text-xs">
                  <span className="text-muted">Match:</span>
                  <button
                    type="button"
                    onClick={toggleMode}
                    className="px-2 py-1 rounded bg-background-secondary hover:bg-background-tertiary transition-colors text-primary font-medium"
                  >
                    {filterMode === 'AND' ? 'All tags (AND)' : 'Any tag (OR)'}
                  </button>
                </div>
              )}

              {/* Search input */}
              <div className="relative">
                <input
                  type="text"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  placeholder="Search tags..."
                  className="input input-sm w-full pr-8"
                  autoComplete="off"
                />
                {searchQuery && (
                  <button
                    type="button"
                    onClick={() => setSearchQuery('')}
                    className="absolute right-2 top-1/2 transform -translate-y-1/2 text-muted hover:text-primary"
                  >
                    <X className="w-3 h-3" />
                  </button>
                )}
              </div>

              {/* Selected tags */}
              {selectedTags.length > 0 && (
                <div className="space-y-1">
                  <div className="text-xs text-muted font-medium">Selected:</div>
                  <div className="flex flex-wrap gap-1">
                    <AnimatePresence>
                      {selectedTags.map((tag) => (
                        <TagBadge
                          key={tag.id}
                          tag={tag}
                          size="sm"
                          onRemove={() => toggleTag(tag)}
                        />
                      ))}
                    </AnimatePresence>
                  </div>
                </div>
              )}

              {/* Available tags list */}
              <div className="space-y-1">
                <div className="text-xs text-muted font-medium">Available Tags:</div>
                <div className="max-h-60 overflow-y-auto space-y-1">
                  {loading ? (
                    <div className="text-center py-4">
                      <div className="w-6 h-6 border-2 border-primary border-t-transparent rounded-full animate-spin mx-auto" />
                    </div>
                  ) : filteredTags.length === 0 ? (
                    <div className="text-center py-4 text-sm text-muted">
                      {searchQuery ? 'No tags found' : 'No tags available'}
                    </div>
                  ) : (
                    filteredTags.map((tag) => {
                      const isSelected = !!selectedTags.find((t) => t.id === tag.id)
                      return (
                        <button
                          key={tag.id}
                          type="button"
                          onClick={() => toggleTag(tag)}
                          className={`w-full text-left px-3 py-2 rounded hover:bg-background-secondary transition-colors flex items-center justify-between ${
                            isSelected ? 'bg-background-secondary' : ''
                          }`}
                        >
                          <div className="flex items-center gap-2 flex-1 min-w-0">
                            <input
                              type="checkbox"
                              checked={isSelected}
                              onChange={() => {}}
                              className="w-4 h-4 rounded border-border"
                            />
                            <TagBadge tag={tag} size="sm" />
                          </div>
                          <div className="text-xs text-muted ml-2">
                            {entityType === 'parts' ? tag.parts_count : tag.tools_count}
                          </div>
                        </button>
                      )
                    })
                  )}
                </div>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}

export default TagFilter
