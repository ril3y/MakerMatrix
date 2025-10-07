/**
 * Tooltip Component
 *
 * A visually appealing tooltip that uses theme colors for styling.
 * Supports hover and click triggers with flexible positioning.
 */

import type { ReactNode } from 'react'
import { useState, useRef, useEffect } from 'react'
import { HelpCircle, Info, AlertCircle } from 'lucide-react'

interface TooltipProps {
  content: ReactNode
  children?: ReactNode
  position?: 'top' | 'bottom' | 'left' | 'right'
  variant?: 'info' | 'help' | 'warning'
  trigger?: 'hover' | 'click'
  maxWidth?: string
  minWidth?: string
  className?: string
}

export const Tooltip = ({
  content,
  children,
  position = 'top',
  variant = 'info',
  trigger = 'hover',
  maxWidth = '500px',
  minWidth = '300px',
  className = '',
}: TooltipProps) => {
  const [isVisible, setIsVisible] = useState(false)
  const [adjustedPosition, setAdjustedPosition] = useState(position)
  const tooltipRef = useRef<HTMLDivElement>(null)
  const triggerRef = useRef<HTMLDivElement>(null)

  // Close tooltip when clicking outside
  useEffect(() => {
    if (trigger === 'click' && isVisible) {
      const handleClickOutside = (event: MouseEvent) => {
        if (
          tooltipRef.current &&
          triggerRef.current &&
          !tooltipRef.current.contains(event.target as Node) &&
          !triggerRef.current.contains(event.target as Node)
        ) {
          setIsVisible(false)
        }
      }

      document.addEventListener('mousedown', handleClickOutside)
      return () => document.removeEventListener('mousedown', handleClickOutside)
    }
  }, [isVisible, trigger])

  // Adjust position if tooltip goes off-screen
  useEffect(() => {
    if (isVisible && tooltipRef.current && triggerRef.current) {
      const tooltipRect = tooltipRef.current.getBoundingClientRect()
      const viewportWidth = window.innerWidth
      const viewportHeight = window.innerHeight

      let newPosition = position

      // Check if tooltip goes off right edge
      if (tooltipRect.right > viewportWidth) {
        if (position === 'right') newPosition = 'left'
      }

      // Check if tooltip goes off left edge
      if (tooltipRect.left < 0) {
        if (position === 'left') newPosition = 'right'
      }

      // Check if tooltip goes off top
      if (tooltipRect.top < 0) {
        if (position === 'top') newPosition = 'bottom'
      }

      // Check if tooltip goes off bottom
      if (tooltipRect.bottom > viewportHeight) {
        if (position === 'bottom') newPosition = 'top'
      }

      setAdjustedPosition(newPosition)
    }
  }, [isVisible, position])

  const handleMouseEnter = () => {
    if (trigger === 'hover') {
      setIsVisible(true)
    }
  }

  const handleMouseLeave = () => {
    if (trigger === 'hover') {
      setIsVisible(false)
    }
  }

  const handleClick = () => {
    if (trigger === 'click') {
      setIsVisible(!isVisible)
    }
  }

  // Icon based on variant
  const getIcon = () => {
    switch (variant) {
      case 'help':
        return <HelpCircle className="w-4 h-4" />
      case 'warning':
        return <AlertCircle className="w-4 h-4" />
      case 'info':
      default:
        return <Info className="w-4 h-4" />
    }
  }

  // Colors based on variant
  const getVariantClasses = () => {
    switch (variant) {
      case 'help':
        return 'text-primary hover:text-primary-dark'
      case 'warning':
        return 'text-orange-500 hover:text-orange-600'
      case 'info':
      default:
        return 'text-blue-500 hover:text-blue-600'
    }
  }

  const getTooltipBgClass = () => {
    switch (variant) {
      case 'help':
        return 'bg-gray-800 border-gray-700'
      case 'warning':
        return 'bg-orange-600 border-orange-700'
      case 'info':
      default:
        return 'bg-gray-800 border-gray-700'
    }
  }

  // Position classes
  const getPositionClasses = () => {
    switch (adjustedPosition) {
      case 'bottom':
        return 'top-full left-1/2 -translate-x-1/2 mt-2'
      case 'left':
        return 'right-full top-1/2 -translate-y-1/2 mr-2'
      case 'right':
        return 'left-full top-1/2 -translate-y-1/2 ml-2'
      case 'top':
      default:
        return 'bottom-full left-1/2 -translate-x-1/2 mb-2'
    }
  }

  // Arrow position
  const getArrowPositionClasses = () => {
    switch (adjustedPosition) {
      case 'bottom':
        return '-top-4 left-1/2 -translate-x-1/2'
      case 'left':
        return '-right-4 top-1/2 -translate-y-1/2'
      case 'right':
        return '-left-4 top-1/2 -translate-y-1/2'
      case 'top':
      default:
        return '-bottom-4 left-1/2 -translate-x-1/2'
    }
  }

  // Arrow color classes
  const getArrowColorClasses = () => {
    const base = 'absolute w-0 h-0 border-8 border-transparent'

    if (variant === 'warning') {
      switch (adjustedPosition) {
        case 'bottom':
          return `${base} border-b-orange-600`
        case 'left':
          return `${base} border-l-orange-600`
        case 'right':
          return `${base} border-r-orange-600`
        case 'top':
        default:
          return `${base} border-t-orange-600`
      }
    }

    // Default (help/info) - gray-800
    switch (adjustedPosition) {
      case 'bottom':
        return `${base} border-b-gray-800`
      case 'left':
        return `${base} border-l-gray-800`
      case 'right':
        return `${base} border-r-gray-800`
      case 'top':
      default:
        return `${base} border-t-gray-800`
    }
  }

  return (
    <div className={`relative inline-flex items-center ${className}`}>
      <div
        ref={triggerRef}
        onMouseEnter={handleMouseEnter}
        onMouseLeave={handleMouseLeave}
        onClick={handleClick}
        className={`cursor-help transition-colors duration-200 ${getVariantClasses()}`}
      >
        {children || getIcon()}
      </div>

      {isVisible && (
        <div
          ref={tooltipRef}
          className={`absolute z-50 ${getPositionClasses()} animate-in fade-in-0 zoom-in-95 duration-200 w-max`}
          style={{ maxWidth, minWidth, width: minWidth }}
        >
          {/* Tooltip content */}
          <div
            className={`${getTooltipBgClass()} text-white px-4 py-3 rounded-lg shadow-xl border w-full`}
          >
            <div className="text-sm leading-relaxed">{content}</div>
          </div>

          {/* Arrow */}
          <div className={`${getArrowColorClasses()} ${getArrowPositionClasses()}`} />
        </div>
      )}
    </div>
  )
}

/**
 * Tooltip with underlined text trigger
 */
interface TooltipTextProps {
  text: string
  tooltip: ReactNode
  position?: 'top' | 'bottom' | 'left' | 'right'
  variant?: 'info' | 'help' | 'warning'
}

export const TooltipText = ({
  text,
  tooltip,
  position = 'top',
  variant = 'help',
}: TooltipTextProps) => {
  return (
    <Tooltip content={tooltip} position={position} variant={variant} trigger="hover">
      <span className="border-b border-dotted border-current cursor-help">{text}</span>
    </Tooltip>
  )
}

/**
 * Tooltip with icon only (no children)
 */
interface TooltipIconProps {
  tooltip: ReactNode
  position?: 'top' | 'bottom' | 'left' | 'right'
  variant?: 'info' | 'help' | 'warning'
  className?: string
}

export const TooltipIcon = ({
  tooltip,
  position = 'top',
  variant = 'help',
  className = '',
}: TooltipIconProps) => {
  return (
    <Tooltip
      content={tooltip}
      position={position}
      variant={variant}
      trigger="hover"
      className={className}
    />
  )
}

export default Tooltip
