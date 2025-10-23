import { useState, useEffect, useRef } from 'react'
import { Plus, X } from 'lucide-react'
import { tagsService } from '@/services/tags.service'
import type { Tag, CreateTagRequest } from '@/types/tags'
import TagBadge from './TagBadge'
import { motion, AnimatePresence } from 'framer-motion'
import toast from 'react-hot-toast'

interface TagInputProps {
  selectedTags: Tag[]
  onTagsChange: (tags: Tag[]) => void
  entityType: 'part' | 'tool'
  placeholder?: string
  disabled?: boolean
}

const TagInput = ({
  selectedTags,
  onTagsChange,
  entityType,
  placeholder = 'Add tags (e.g., #todo, #testing)...',
  disabled = false,
}: TagInputProps) => {
  const [inputValue, setInputValue] = useState('')
  const [suggestions, setSuggestions] = useState<Tag[]>([])
  const [showSuggestions, setShowSuggestions] = useState(false)
  const [activeSuggestionIndex, setActiveSuggestionIndex] = useState(-1)
  const [isCreatingTag, setIsCreatingTag] = useState(false)

  const inputRef = useRef<HTMLInputElement>(null)
  const suggestionsRef = useRef<HTMLDivElement>(null)

  // Fetch tag suggestions
  const fetchSuggestions = async (query: string) => {
    if (query.length < 1) {
      setSuggestions([])
      setShowSuggestions(false)
      return
    }

    try {
      // Strip # prefix if present
      const searchQuery = query.startsWith('#') ? query.slice(1) : query

      const allTags = await tagsService.searchTags(searchQuery, 10)

      // Filter out already selected tags
      const filtered = allTags.filter(
        (tag) => !selectedTags.find((selected) => selected.id === tag.id)
      )

      setSuggestions(filtered)
      setShowSuggestions(filtered.length > 0 || searchQuery.length > 0)
      setActiveSuggestionIndex(-1)
    } catch (error) {
      console.error('Error fetching tag suggestions:', error)
      setSuggestions([])
      setShowSuggestions(false)
    }
  }

  // Handle input change
  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = e.target.value
    setInputValue(value)

    // Debounce suggestions
    const timer = setTimeout(() => {
      fetchSuggestions(value)
    }, 200)

    return () => clearTimeout(timer)
  }

  // Create a new tag
  const createNewTag = async (name: string): Promise<Tag | null> => {
    try {
      setIsCreatingTag(true)

      // Strip # prefix and trim
      const tagName = name.startsWith('#') ? name.slice(1).trim() : name.trim()

      if (!tagName) {
        toast.error('Tag name cannot be empty')
        return null
      }

      // Check if tag already exists
      const exists = await tagsService.checkTagExists(tagName)
      if (exists) {
        // Find and return existing tag
        const allTags = await tagsService.searchTags(tagName, 1)
        const existingTag = allTags.find((tag) => tag.name.toLowerCase() === tagName.toLowerCase())
        if (existingTag) {
          return existingTag
        }
      }

      // Create new tag with a nice default color
      const newTagData: CreateTagRequest = {
        name: tagName,
        color: '#3B82F6', // Default blue
      }

      const newTag = await tagsService.createTag(newTagData)
      toast.success(`Tag "#${tagName}" created`)
      return newTag
    } catch (error: any) {
      toast.error(error.message || 'Failed to create tag')
      return null
    } finally {
      setIsCreatingTag(false)
    }
  }

  // Add tag to selection
  const addTag = async (tag: Tag | null) => {
    if (!tag) return

    // Check if already selected
    if (selectedTags.find((selected) => selected.id === tag.id)) {
      return
    }

    onTagsChange([...selectedTags, tag])
    setInputValue('')
    setSuggestions([])
    setShowSuggestions(false)
    inputRef.current?.focus()
  }

  // Handle suggestion selection
  const handleSuggestionClick = (tag: Tag) => {
    addTag(tag)
  }

  // Handle create new tag
  const handleCreateNew = async () => {
    const tagName = inputValue.startsWith('#') ? inputValue.slice(1).trim() : inputValue.trim()

    if (!tagName) return

    const newTag = await createNewTag(tagName)
    if (newTag) {
      await addTag(newTag)
    }
  }

  // Remove tag from selection
  const removeTag = (tagId: string) => {
    onTagsChange(selectedTags.filter((tag) => tag.id !== tagId))
  }

  // Handle keyboard navigation
  const handleKeyDown = async (e: React.KeyboardEvent) => {
    if (disabled) return

    // Handle Enter key
    if (e.key === 'Enter') {
      e.preventDefault()

      if (showSuggestions && suggestions.length > 0 && activeSuggestionIndex >= 0) {
        // Select highlighted suggestion
        handleSuggestionClick(suggestions[activeSuggestionIndex])
      } else if (inputValue.trim()) {
        // Create new tag
        await handleCreateNew()
      }
    }

    // Handle Escape key
    if (e.key === 'Escape') {
      setShowSuggestions(false)
      setActiveSuggestionIndex(-1)
    }

    // Handle arrow keys
    if (!showSuggestions || suggestions.length === 0) return

    if (e.key === 'ArrowDown') {
      e.preventDefault()
      setActiveSuggestionIndex((prev) => (prev < suggestions.length - 1 ? prev + 1 : prev))
    }

    if (e.key === 'ArrowUp') {
      e.preventDefault()
      setActiveSuggestionIndex((prev) => (prev > 0 ? prev - 1 : -1))
    }
  }

  // Click outside to close suggestions
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (
        suggestionsRef.current &&
        !suggestionsRef.current.contains(event.target as Node) &&
        inputRef.current &&
        !inputRef.current.contains(event.target as Node)
      ) {
        setShowSuggestions(false)
      }
    }

    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  return (
    <div className="space-y-2">
      {/* Selected tags display */}
      {selectedTags.length > 0 && (
        <div className="flex flex-wrap gap-2">
          <AnimatePresence>
            {selectedTags.map((tag) => (
              <TagBadge key={tag.id} tag={tag} size="md" onRemove={() => removeTag(tag.id)} />
            ))}
          </AnimatePresence>
        </div>
      )}

      {/* Input field */}
      <div className="relative">
        <input
          ref={inputRef}
          type="text"
          value={inputValue}
          onChange={handleInputChange}
          onKeyDown={handleKeyDown}
          onFocus={() => {
            if (inputValue) {
              fetchSuggestions(inputValue)
            }
          }}
          placeholder={placeholder}
          disabled={disabled || isCreatingTag}
          className="input w-full pr-10"
          autoComplete="off"
        />

        {/* Clear button */}
        {inputValue && !isCreatingTag && (
          <button
            type="button"
            onClick={() => {
              setInputValue('')
              setSuggestions([])
              setShowSuggestions(false)
              inputRef.current?.focus()
            }}
            className="absolute right-3 top-1/2 transform -translate-y-1/2 text-muted hover:text-primary transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        )}

        {isCreatingTag && (
          <div className="absolute right-3 top-1/2 transform -translate-y-1/2">
            <div className="w-4 h-4 border-2 border-primary border-t-transparent rounded-full animate-spin" />
          </div>
        )}

        {/* Suggestions dropdown */}
        {showSuggestions && (
          <motion.div
            ref={suggestionsRef}
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            className="absolute top-full left-0 right-0 mt-1 bg-background-primary border border-border rounded-lg shadow-lg z-50 max-h-60 overflow-y-auto"
          >
            {suggestions.length > 0 ? (
              <>
                {suggestions.map((tag, index) => (
                  <button
                    key={tag.id}
                    type="button"
                    onClick={() => handleSuggestionClick(tag)}
                    className={`w-full text-left px-4 py-2 hover:bg-background-secondary transition-colors border-b border-border last:border-b-0 ${
                      index === activeSuggestionIndex ? 'bg-background-secondary' : ''
                    }`}
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <TagBadge tag={tag} size="sm" />
                      </div>
                      <div className="text-xs text-muted">
                        {tag.parts_count + tag.tools_count} uses
                      </div>
                    </div>
                    {tag.description && (
                      <div className="text-xs text-muted mt-1 truncate">{tag.description}</div>
                    )}
                  </button>
                ))}
              </>
            ) : null}

            {/* Create new tag option */}
            {inputValue.trim() && (
              <button
                type="button"
                onClick={handleCreateNew}
                disabled={isCreatingTag}
                className="w-full text-left px-4 py-2 hover:bg-background-secondary transition-colors border-t border-border flex items-center gap-2 text-accent"
              >
                <Plus className="w-4 h-4" />
                <span>
                  Create tag "
                  <span className="font-semibold">
                    #{inputValue.startsWith('#') ? inputValue.slice(1) : inputValue}
                  </span>
                  "
                </span>
              </button>
            )}
          </motion.div>
        )}
      </div>

      <div className="text-xs text-muted">
        Type to search existing tags or create new ones. Press Enter to add.
      </div>
    </div>
  )
}

export default TagInput
