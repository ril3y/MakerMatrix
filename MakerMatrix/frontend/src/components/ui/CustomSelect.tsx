/**
 * Custom Select Component
 *
 * Replaces native <select> to avoid browser dropdown positioning issues in modals.
 * Uses a div-based dropdown that we control completely.
 */

import { useState, useRef, useEffect } from 'react'
import { ChevronDown, Check } from 'lucide-react'

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
}

export const CustomSelect = ({
  value,
  onChange,
  options = [],
  optionGroups = [],
  placeholder = 'Select...',
  disabled = false,
  error,
  className = ''
}: CustomSelectProps) => {
  const [isOpen, setIsOpen] = useState(false)
  const containerRef = useRef<HTMLDivElement>(null)

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(event.target as Node)) {
        setIsOpen(false)
      }
    }

    if (isOpen) {
      document.addEventListener('mousedown', handleClickOutside)
      return () => document.removeEventListener('mousedown', handleClickOutside)
    }
  }, [isOpen])

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
  }

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
        <div className="absolute z-50 w-full mt-1 bg-theme-primary border border-theme-primary rounded-md shadow-lg max-h-60 overflow-auto">
          {/* Flat Options */}
          {options.length > 0 && (
            <div className="py-1">
              {options.map((option) => (
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
          {optionGroups.map((group, groupIndex) => (
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
        </div>
      )}
    </div>
  )
}

export default CustomSelect
