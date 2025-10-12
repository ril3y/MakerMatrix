import { X } from 'lucide-react'
import type { Tag } from '@/types/tags'
import { motion } from 'framer-motion'

interface TagBadgeProps {
  tag: Tag
  size?: 'sm' | 'md' | 'lg'
  onRemove?: () => void
  onClick?: () => void
  className?: string
  showCount?: boolean
}

const TagBadge = ({
  tag,
  size = 'md',
  onRemove,
  onClick,
  className = '',
  showCount = false,
}: TagBadgeProps) => {
  const sizeClasses = {
    sm: 'px-2 py-0.5 text-xs',
    md: 'px-3 py-1 text-sm',
    lg: 'px-4 py-2 text-base',
  }

  const iconSizes = {
    sm: 'text-xs',
    md: 'text-sm',
    lg: 'text-base',
  }

  // Use tag color or default to blue
  const bgColor = tag.color || '#3B82F6'

  // Calculate text color based on background brightness
  const getTextColor = (hexColor: string) => {
    const rgb = parseInt(hexColor.slice(1), 16)
    const r = (rgb >> 16) & 0xff
    const g = (rgb >> 8) & 0xff
    const b = (rgb >> 0) & 0xff
    const brightness = (r * 299 + g * 587 + b * 114) / 1000
    return brightness > 128 ? '#000000' : '#FFFFFF'
  }

  const textColor = getTextColor(bgColor)
  const totalCount = tag.parts_count + tag.tools_count

  const handleClick = (e: React.MouseEvent) => {
    if (onRemove) {
      e.stopPropagation()
    }
    onClick?.()
  }

  const handleRemove = (e: React.MouseEvent) => {
    e.stopPropagation()
    onRemove?.()
  }

  return (
    <motion.span
      initial={{ scale: 0.8, opacity: 0 }}
      animate={{ scale: 1, opacity: 1 }}
      exit={{ scale: 0.8, opacity: 0 }}
      transition={{ duration: 0.15 }}
      className={`inline-flex items-center gap-1.5 rounded-full font-medium transition-all ${
        sizeClasses[size]
      } ${onClick ? 'cursor-pointer hover:shadow-md hover:scale-105' : ''} ${className}`}
      style={{
        backgroundColor: bgColor,
        color: textColor,
      }}
      onClick={handleClick}
      title={tag.description || tag.name}
    >
      {tag.icon && <span className={iconSizes[size]}>{tag.icon}</span>}
      <span className="truncate max-w-[150px]">#{tag.name}</span>
      {showCount && totalCount > 0 && (
        <span
          className="px-1.5 py-0.5 rounded-full text-xs font-bold"
          style={{
            backgroundColor: textColor,
            color: bgColor,
            opacity: 0.8,
          }}
        >
          {totalCount}
        </span>
      )}
      {onRemove && (
        <button
          onClick={handleRemove}
          className="hover:opacity-80 transition-opacity focus:outline-none"
          title="Remove tag"
          type="button"
        >
          <X className="w-3 h-3" />
        </button>
      )}
    </motion.span>
  )
}

export default TagBadge
