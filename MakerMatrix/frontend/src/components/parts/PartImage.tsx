import React, { useState, useEffect } from 'react'
import { Package, Image as ImageIcon } from 'lucide-react'
import { normalizeImageUrl } from '@/utils/image.utils'
import { apiClient } from '@/services/api'

interface PartImageProps {
  imageUrl?: string | null
  partName: string
  className?: string
  size?: 'sm' | 'md' | 'lg' | 'xl'
  showFallback?: boolean
}

const sizeClasses = {
  sm: 'w-8 h-8',
  md: 'w-12 h-12',
  lg: 'w-24 h-24',
  xl: 'w-48 h-48',
}

const PartImage: React.FC<PartImageProps> = ({
  imageUrl,
  partName,
  className = '',
  size = 'md',
  showFallback = true,
}) => {
  const [imageError, setImageError] = useState(false)
  const [imageBlob, setImageBlob] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)
  const normalizedUrl = normalizeImageUrl(imageUrl)

  useEffect(() => {
    if (!normalizedUrl) return

    // Only fetch for our authenticated endpoints
    if (
      normalizedUrl.startsWith('/utility/get_image/') ||
      normalizedUrl.startsWith('/api/utility/get_image/')
    ) {
      fetchAuthenticatedImage(normalizedUrl)
    } else {
      // For external URLs or legacy static URLs, use direct loading
      setImageBlob(normalizedUrl)
    }
  }, [normalizedUrl])

  const fetchAuthenticatedImage = async (url: string) => {
    try {
      setLoading(true)
      setImageError(false)

      // Use the API client to make authenticated request
      const response = await apiClient.get(url, {
        responseType: 'blob',
      })

      // Create blob URL for the image
      const blobUrl = URL.createObjectURL(response)
      setImageBlob(blobUrl)
    } catch (error) {
      console.warn(`Failed to load authenticated image for part: ${partName}, URL: ${url}`, error)
      setImageError(true)
    } finally {
      setLoading(false)
    }
  }

  // Cleanup blob URL on unmount
  useEffect(() => {
    return () => {
      if (imageBlob && imageBlob.startsWith('blob:')) {
        URL.revokeObjectURL(imageBlob)
      }
    }
  }, [imageBlob])

  const baseClasses = `${sizeClasses[size]} object-contain rounded border border-border`
  const fallbackClasses = `${sizeClasses[size]} bg-background-secondary rounded border border-border flex items-center justify-center`

  // Show fallback if no URL, normalization failed, or image failed to load
  if (!normalizedUrl || imageError) {
    if (!showFallback) return null

    return (
      <div className={`${fallbackClasses} ${className}`}>
        {size === 'sm' ? (
          <Package className="w-4 h-4 text-muted" />
        ) : (
          <div className="text-center text-muted">
            <ImageIcon className={`mx-auto mb-1 ${size === 'md' ? 'w-4 h-4' : 'w-6 h-6'}`} />
            {size !== 'sm' && <p className="text-xs">No image</p>}
          </div>
        )}
      </div>
    )
  }

  // Show loading state
  if (loading || !imageBlob) {
    return (
      <div className={`${fallbackClasses} ${className}`}>
        <div className="text-center text-muted">
          <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-primary mx-auto mb-1"></div>
          {size !== 'sm' && <p className="text-xs">Loading...</p>}
        </div>
      </div>
    )
  }

  return (
    <img
      src={imageBlob}
      alt={partName}
      className={`${baseClasses} ${className}`}
      onError={() => setImageError(true)}
      loading="lazy"
    />
  )
}

export default PartImage
