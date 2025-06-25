import React, { useState, useEffect } from 'react'

interface AuthenticatedImageProps {
  src: string
  alt?: string
  className?: string
  onError?: () => void
}

const AuthenticatedImage: React.FC<AuthenticatedImageProps> = ({ 
  src, 
  alt = "", 
  className = "",
  onError 
}) => {
  const [imageSrc, setImageSrc] = useState<string>('')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(false)

  useEffect(() => {
    const fetchImage = async () => {
      try {
        setLoading(true)
        setError(false)
        
        const token = localStorage.getItem('auth_token')
        const response = await fetch(src, {
          headers: {
            'Authorization': `Bearer ${token}`
          }
        })

        if (!response.ok) {
          throw new Error(`Failed to load image: ${response.statusText}`)
        }

        const blob = await response.blob()
        const objectUrl = URL.createObjectURL(blob)
        setImageSrc(objectUrl)
      } catch (error) {
        console.error('Error loading authenticated image:', error)
        setError(true)
        onError?.()
      } finally {
        setLoading(false)
      }
    }

    if (src) {
      fetchImage()
    }

    // Cleanup function to revoke object URL
    return () => {
      if (imageSrc) {
        URL.revokeObjectURL(imageSrc)
      }
    }
  }, [src])

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
        onError?.()
      }}
    />
  )
}

export default AuthenticatedImage