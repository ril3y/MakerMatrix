import { ReactNode, useState, useRef, useEffect } from 'react'

interface TooltipProps {
  content: string
  children: ReactNode
  placement?: 'top' | 'bottom' | 'left' | 'right'
  delay?: number
  disabled?: boolean
}

const Tooltip = ({ 
  content, 
  children, 
  placement = 'top', 
  delay = 500,
  disabled = false 
}: TooltipProps) => {
  const [isVisible, setIsVisible] = useState(false)
  const [timeoutId, setTimeoutId] = useState<NodeJS.Timeout | null>(null)
  const tooltipRef = useRef<HTMLDivElement>(null)
  const triggerRef = useRef<HTMLDivElement>(null)

  const showTooltip = () => {
    if (disabled) return
    
    const id = setTimeout(() => {
      setIsVisible(true)
    }, delay)
    setTimeoutId(id)
  }

  const hideTooltip = () => {
    if (timeoutId) {
      clearTimeout(timeoutId)
      setTimeoutId(null)
    }
    setIsVisible(false)
  }

  useEffect(() => {
    return () => {
      if (timeoutId) {
        clearTimeout(timeoutId)
      }
    }
  }, [timeoutId])

  const getTooltipClasses = () => {
    const baseClasses = `
      absolute z-50 px-2 py-1 text-xs text-white bg-gray-900 dark:bg-gray-700 
      rounded shadow-lg transition-opacity duration-200 pointer-events-none
      whitespace-nowrap max-w-xs
    `
    
    const placementClasses = {
      top: 'bottom-full left-1/2 transform -translate-x-1/2 mb-1',
      bottom: 'top-full left-1/2 transform -translate-x-1/2 mt-1',
      left: 'right-full top-1/2 transform -translate-y-1/2 mr-1',
      right: 'left-full top-1/2 transform -translate-y-1/2 ml-1'
    }
    
    const visibilityClasses = isVisible ? 'opacity-100' : 'opacity-0'
    
    return `${baseClasses} ${placementClasses[placement]} ${visibilityClasses}`
  }

  const getArrowClasses = () => {
    const baseClasses = 'absolute w-2 h-2 bg-gray-900 dark:bg-gray-700 transform rotate-45'
    
    const placementClasses = {
      top: 'top-full left-1/2 transform -translate-x-1/2 -translate-y-1/2',
      bottom: 'bottom-full left-1/2 transform -translate-x-1/2 translate-y-1/2',
      left: 'left-full top-1/2 transform -translate-y-1/2 -translate-x-1/2',
      right: 'right-full top-1/2 transform -translate-y-1/2 translate-x-1/2'
    }
    
    return `${baseClasses} ${placementClasses[placement]}`
  }

  return (
    <div 
      ref={triggerRef}
      className="relative inline-block"
      onMouseEnter={showTooltip}
      onMouseLeave={hideTooltip}
      onFocus={showTooltip}
      onBlur={hideTooltip}
    >
      {children}
      {content && (
        <div ref={tooltipRef} className={getTooltipClasses()}>
          {content}
          <div className={getArrowClasses()}></div>
        </div>
      )}
    </div>
  )
}

export default Tooltip