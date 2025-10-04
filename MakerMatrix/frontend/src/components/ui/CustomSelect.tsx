/**
 * Custom Select Component
 *
 * Replaces native <select> to avoid browser dropdown positioning issues in modals.
 * Uses a div-based dropdown that we control completely.
 */

import { useState, useRef, useEffect } from 'react'
import { ChevronDown, Check, Search, X } from 'lucide-react'

interface Option {
  value: string
  label: string
}

interface OptionGroup {
  label: string
  options: Option[]
}

interface CustomSelectProps {
  value: string
  onChange: (value: string) => void
  options?: Option[]
  optionGroups?: OptionGroup[]
  placeholder?: string
  disabled?: boolean
  error?: string
  className?: string
  searchable?: boolean
  searchPlaceholder?: string
}

export const CustomSelect = ({
  value,
  onChange,
  options = [],
  optionGroups = [],
  placeholder = 'Select...',
  disabled = false,
  error,
  className = '',
  searchable = false,
  searchPlaceholder = 'Search...'
}: CustomSelectProps) => {
  const [isOpen, setIsOpen] = useState(false)
  const [searchTerm, setSearchTerm] = useState('')
  const containerRef = useRef<HTMLDivElement>(null)
  const searchInputRef = useRef<HTMLInputElement>(null)

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(event.target as Node)) {
        setIsOpen(false)
        setSearchTerm('')
      }
    }

    if (isOpen) {
      document.addEventListener('mousedown', handleClickOutside)
      return () => document.removeEventListener('mousedown', handleClickOutside)
    }
  }, [isOpen])

  // Focus search input when dropdown opens
  useEffect(() => {
    if (isOpen && searchable && searchInputRef.current) {
      setTimeout(() => searchInputRef.current?.focus(), 50)
    }
  }, [isOpen, searchable])

  // Get display label for current value
  const getDisplayLabel = () => {
    if (!value) return placeholder

    // Check in flat options
    const flatOption = options.find(opt => opt.value === value)
    if (flatOption) return flatOption.label

    // Check in option groups
    for (const group of optionGroups) {
      const groupOption = group.options.find(opt => opt.value === value)
      if (groupOption) return groupOption.label
    }

    return value
  }

  const handleSelect = (optionValue: string) => {
    onChange(optionValue)
    setIsOpen(false)
    setSearchTerm('')
  }

  // Filter options based on search term
  const filterOptions = (opts: Option[]) => {
    if (!searchTerm) return opts
    const term = searchTerm.toLowerCase()
    return opts.filter(opt => opt.label.toLowerCase().includes(term))
  }

  // Filter option groups based on search term
  const filterOptionGroups = (groups: OptionGroup[]) => {
    if (!searchTerm) return groups
    return groups
      .map(group => ({
        ...group,
        options: filterOptions(group.options)
      }))
      .filter(group => group.options.length > 0)
  }

  const filteredOptions = filterOptions(options)
  const filteredOptionGroups = filterOptionGroups(optionGroups)

  return (
    <div ref={containerRef} className={`relative ${className}`}>
      {/* Trigger Button */}
      <button
        type="button"
        onClick={() => !disabled && setIsOpen(!isOpen)}
        disabled={disabled}
        className={`
          w-full px-3 py-2 border rounded-md text-left
          bg-theme-primary text-theme-primary
          focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent
          disabled:bg-theme-tertiary disabled:text-theme-muted disabled:cursor-not-allowed
          flex items-center justify-between gap-2
          ${error ? 'border-red-500' : 'border-theme-primary'}
        `}
      >
        <span className={!value ? 'text-theme-muted' : ''}>{getDisplayLabel()}</span>
        <ChevronDown className={`w-4 h-4 text-theme-secondary transition-transform ${isOpen ? 'rotate-180' : ''}`} />
      </button>

      {/* Dropdown Menu */}
      {isOpen && (
        <div className="absolute z-50 w-full mt-1 bg-theme-primary border border-theme-primary rounded-md shadow-lg max-h-60 overflow-hidden flex flex-col">
          {/* Search Input */}
          {searchable && (
            <div className="sticky top-0 p-2 border-b border-theme-primary bg-theme-primary">
              <div className="relative">
                <Search className="absolute left-2 top-1/2 transform -translate-y-1/2 w-4 h-4 text-theme-muted" />
                <input
                  ref={searchInputRef}
                  type="text"
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  placeholder={searchPlaceholder}
                  className="w-full pl-8 pr-8 py-1.5 text-sm bg-theme-secondary border border-theme-primary rounded text-theme-primary placeholder-theme-muted focus:outline-none focus:ring-2 focus:ring-primary"
                  onClick={(e) => e.stopPropagation()}
                />
                {searchTerm && (
                  <button
                    type="button"
                    onClick={(e) => {
                      e.stopPropagation()
                      setSearchTerm('')
                      searchInputRef.current?.focus()
                    }}
                    className="absolute right-2 top-1/2 transform -translate-y-1/2 text-theme-muted hover:text-theme-primary"
                  >
                    <X className="w-4 h-4" />
                  </button>
                )}
              </div>
            </div>
          )}

          {/* Options List */}
          <div className="overflow-auto flex-1">
            {/* Flat Options */}
            {filteredOptions.length > 0 && (
              <div className="py-1">
                {filteredOptions.map((option) => (
                <button
                  key={option.value}
                  type="button"
                  onClick={() => handleSelect(option.value)}
                  className={`
                    w-full px-3 py-2 text-left
                    flex items-center justify-between gap-2
                    transition-colors duration-150
                    ${value === option.value
                      ? 'bg-secondary/20 text-secondary font-medium'
                      : 'text-theme-primary hover:bg-secondary hover:text-white'
                    }
                  `}
                >
                  <span>{option.label}</span>
                  {value === option.value && <Check className="w-4 h-4" />}
                </button>
              ))}
            </div>
          )}

            {/* Option Groups */}
            {filteredOptionGroups.map((group, groupIndex) => (
              <div key={groupIndex}>
                <div className="px-3 py-2 text-xs font-semibold text-theme-secondary bg-theme-tertiary">
                  {group.label}
                </div>
                <div className="py-1">
                  {group.options.map((option) => (
                    <button
                      key={option.value}
                      type="button"
                      onClick={() => handleSelect(option.value)}
                      className={`
                        w-full px-3 py-2 text-left
                        flex items-center justify-between gap-2
                        transition-colors duration-150
                        ${value === option.value
                          ? 'bg-secondary/20 text-secondary font-medium'
                          : 'text-theme-primary hover:bg-secondary hover:text-white'
                        }
                      `}
                    >
                      <span>{option.label}</span>
                      {value === option.value && <Check className="w-4 h-4" />}
                    </button>
                  ))}
                </div>
              </div>
            ))}

            {/* No Results Message */}
            {searchTerm && filteredOptions.length === 0 && filteredOptionGroups.length === 0 && (
              <div className="py-8 text-center text-theme-muted">
                <Search className="w-8 h-8 mx-auto mb-2 opacity-50" />
                <p className="text-sm">No results found for "{searchTerm}"</p>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}

export default CustomSelect
