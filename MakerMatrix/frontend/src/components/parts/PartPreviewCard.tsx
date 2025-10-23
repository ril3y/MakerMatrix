import { Package, Hash, Tag } from 'lucide-react'
import type { Part } from '@/types/parts'

interface PartPreviewCardProps {
  part: Part
  className?: string
}

/**
 * Compact part preview card for hover tooltips
 */
const PartPreviewCard = ({ part, className = '' }: PartPreviewCardProps) => {
  return (
    <div
      className={`bg-theme-elevated border border-theme-primary rounded-lg shadow-xl p-3 w-64 ${className}`}
    >
      {/* Image */}
      {part.image_url && (
        <div className="mb-2">
          <img
            src={part.image_url}
            alt={part.part_name}
            className="w-full h-32 object-cover rounded border border-theme-primary"
          />
        </div>
      )}

      {/* Part Name */}
      <h4 className="font-semibold text-theme-primary text-sm mb-2 line-clamp-2">
        {part.part_name}
      </h4>

      {/* Part Number */}
      {part.part_number && (
        <div className="flex items-center gap-2 text-xs text-theme-secondary mb-1">
          <Hash className="w-3 h-3" />
          <span className="truncate">{part.part_number}</span>
        </div>
      )}

      {/* Quantity */}
      <div className="flex items-center gap-2 text-xs text-theme-secondary mb-1">
        <Package className="w-3 h-3" />
        <span>Qty: {part.quantity || 0}</span>
      </div>

      {/* Categories */}
      {part.categories && part.categories.length > 0 && (
        <div className="flex items-center gap-2 text-xs text-theme-secondary mb-1">
          <Tag className="w-3 h-3" />
          <span className="truncate">{part.categories.map((c) => c.name).join(', ')}</span>
        </div>
      )}

      {/* Description */}
      {part.description && (
        <p className="text-xs text-theme-muted mt-2 line-clamp-2">{part.description}</p>
      )}
    </div>
  )
}

export default PartPreviewCard
