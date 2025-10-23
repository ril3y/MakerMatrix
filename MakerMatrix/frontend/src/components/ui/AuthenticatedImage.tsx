import React, { useState, useEffect, useCallback } from 'react'

interface AuthenticatedImageProps {
  src: string
  alt?: string
  className?: string
  onError?: () => void
}

const AuthenticatedImage: React.FC<AuthenticatedImageProps> = ({
  src,
  alt = '',
  className = '',
  onError,
}) => {
  const [imageSrc, setImageSrc] = useState<string>('')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(false)

  // Wrap onError in useCallback to stabilize the reference
  const handleError = useCallback(() => {
    onError?.()
  }, [onError])

  useEffect(() => {
    let objectUrl: string | null = null

    const fetchImage = async () => {
      try {
        setLoading(true)
        setError(false)

        // Import apiClient dynamically to avoid circular dependencies
        const { apiClient } = await import('@/services/api')

        // Use apiClient.get with blob response type
        const blob = await apiClient.get(src, {
          responseType: 'blob',
        })
        objectUrl = URL.createObjectURL(blob)
        setImageSrc(objectUrl)
      } catch (error) {
        console.error('Error loading authenticated image:', error)
        setError(true)
        handleError()
      } finally {
        setLoading(false)
      }
    }

    if (src) {
      fetchImage()
    }

    // Cleanup function to revoke object URL
    return () => {
      if (objectUrl) {
        URL.revokeObjectURL(objectUrl)
      }
    }
  }, [src, handleError])

  if (loading) {
    return (
      <div className={`flex items-center justify-center bg-gray-100 ${className}`}>
        <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-gray-600"></div>
      </div>
    )
  }

  if (error || !imageSrc) {
    return (
      <div className={`flex items-center justify-center bg-gray-100 text-gray-500 ${className}`}>
        <span className="text-sm">Failed to load image</span>
      </div>
    )
  }

  return (
    <img
      src={imageSrc}
      alt={alt}
      className={className}
      onError={() => {
        setError(true)
        handleError()
      }}
    />
  )
}

export default AuthenticatedImage
