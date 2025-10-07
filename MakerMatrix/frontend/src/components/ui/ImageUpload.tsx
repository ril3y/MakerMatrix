import React, { useState, useRef, useCallback, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Upload, Image as ImageIcon, X, Camera } from 'lucide-react'
import toast from 'react-hot-toast'
import { settingsService } from '@/services/settings.service'
import AuthenticatedImage from './AuthenticatedImage'

interface ImageUploadProps {
  onImageUploaded: (imageUrl: string) => void
  currentImageUrl?: string
  placeholder?: string
  maxSize?: number // in MB
  acceptedTypes?: string[]
  className?: string
  disabled?: boolean
  showPreview?: boolean
}

const ImageUpload: React.FC<ImageUploadProps> = ({
  onImageUploaded,
  currentImageUrl,
  placeholder = 'Click to upload or paste an image',
  maxSize = 5, // 5MB default
  acceptedTypes = ['image/png', 'image/jpeg', 'image/jpg', 'image/gif', 'image/webp'],
  className = '',
  disabled = false,
  showPreview = true,
}) => {
  const [dragActive, setDragActive] = useState(false)
  const [uploading, setUploading] = useState(false)
  const [previewUrl, setPreviewUrl] = useState<string | null>(currentImageUrl || null)
  const [pasteListening, setPasteListening] = useState(true)
  const fileInputRef = useRef<HTMLInputElement>(null)
  const dropZoneRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    setPreviewUrl(currentImageUrl || null)
  }, [currentImageUrl])

  const validateFile = (file: File): boolean => {
    // Check file type
    if (!acceptedTypes.includes(file.type)) {
      toast.error(`Invalid file type. Accepted types: ${acceptedTypes.join(', ')}`)
      return false
    }

    // Check file size (5MB limit)
    const maxFileSize = maxSize * 1024 * 1024 // Convert MB to bytes
    if (file.size > maxFileSize) {
      toast.error(`File too large. Maximum size: ${maxSize}MB`)
      return false
    }

    return true
  }

  const handleFileUpload = useCallback(
    async (file: File) => {
      console.log('🚀 handleFileUpload called with file:', file.name, file.size, file.type)
      if (!validateFile(file)) {
        console.log('❌ File validation failed')
        return
      }

      try {
        console.log('⏳ Setting uploading to true...')
        setUploading(true)

        // Create preview URL immediately
        const tempPreviewUrl = URL.createObjectURL(file)
        setPreviewUrl(tempPreviewUrl)

        // Upload to server using utilityService
        const { utilityService } = await import('@/services/utility.service')
        console.log('🔄 Starting image upload...')
        const imageUrl = await utilityService.uploadImage(file)
        console.log('✅ Upload successful, imageUrl:', imageUrl)

        // Clean up temp preview URL
        URL.revokeObjectURL(tempPreviewUrl)

        // Set final preview URL
        setPreviewUrl(imageUrl)
        onImageUploaded(imageUrl)
        console.log('📷 Set preview URL and called onImageUploaded with:', imageUrl)

        toast.success('✅ Image uploaded successfully!')
      } catch (error) {
        console.error('Upload error:', error)
        toast.error('❌ Failed to upload image')
        setPreviewUrl(currentImageUrl || null) // Reset to original
      } finally {
        setUploading(false)
      }
    },
    [currentImageUrl, onImageUploaded]
  )

  // Handle paste events
  useEffect(() => {
    const handlePaste = async (e: ClipboardEvent) => {
      if (!pasteListening || disabled) return

      // Don't interfere with text inputs, textareas, or contenteditable elements
      const target = e.target as HTMLElement
      if (
        target &&
        (target.tagName === 'INPUT' ||
          target.tagName === 'TEXTAREA' ||
          target.contentEditable === 'true' ||
          target.closest('input, textarea, [contenteditable]'))
      ) {
        return
      }

      const items = e.clipboardData?.items
      if (!items) return

      // Check if there's an image in the clipboard
      for (let i = 0; i < items.length; i++) {
        const item = items[i]
        if (item.type.indexOf('image') !== -1) {
          e.preventDefault()
          const file = item.getAsFile()
          if (file) {
            console.log('📋 Image pasted from clipboard:', file.name, file.type)
            toast.success('📎 Image detected in clipboard - uploading...')
            await handleFileUpload(file)
          }
          break
        }
      }
    }

    document.addEventListener('paste', handlePaste)
    return () => document.removeEventListener('paste', handlePaste)
  }, [pasteListening, disabled, handleFileUpload])

  const handleDrag = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true)
    } else if (e.type === 'dragleave') {
      setDragActive(false)
    }
  }, [])

  const handleDrop = useCallback(
    async (e: React.DragEvent) => {
      e.preventDefault()
      e.stopPropagation()
      setDragActive(false)

      if (disabled) return

      const files = e.dataTransfer.files
      if (files && files[0]) {
        await handleFileUpload(files[0])
      }
    },
    [disabled, handleFileUpload]
  )

  const handleFileInputChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files
    if (files && files[0]) {
      await handleFileUpload(files[0])
    }
    // Reset input value to allow selecting the same file again
    e.target.value = ''
  }

  const handleClick = () => {
    if (!disabled && fileInputRef.current) {
      fileInputRef.current.click()
    }
  }

  const handleRemoveImage = () => {
    setPreviewUrl(null)
    onImageUploaded('')
    if (fileInputRef.current) {
      fileInputRef.current.value = ''
    }
  }

  return (
    <div className={`relative ${className}`}>
      {/* Main Upload Area */}
      <div
        ref={dropZoneRef}
        onDragEnter={handleDrag}
        onDragLeave={handleDrag}
        onDragOver={handleDrag}
        onDrop={handleDrop}
        onClick={handleClick}
        className={`
          relative border-2 border-dashed rounded-lg transition-all duration-200 cursor-pointer
          ${dragActive ? 'border-accent bg-accent/10' : 'border-border hover:border-accent/50'}
          ${disabled ? 'opacity-50 cursor-not-allowed' : 'hover:bg-background-secondary/50'}
          ${previewUrl && showPreview ? 'aspect-video' : 'min-h-32'}
        `}
      >
        {/* Hidden file input */}
        <input
          ref={fileInputRef}
          type="file"
          accept={acceptedTypes.join(',')}
          onChange={handleFileInputChange}
          className="hidden"
          disabled={disabled}
        />

        {/* Upload content */}
        <AnimatePresence mode="wait">
          {previewUrl && showPreview ? (
            <motion.div
              key="preview"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="relative w-full h-full"
            >
              {previewUrl?.startsWith('/utility/get_image/') ||
              previewUrl?.startsWith('/api/utility/get_image/') ? (
                <AuthenticatedImage
                  src={previewUrl}
                  alt="Preview"
                  className="w-full h-full object-cover rounded-lg"
                />
              ) : (
                <img
                  src={previewUrl}
                  alt="Preview"
                  className="w-full h-full object-cover rounded-lg"
                />
              )}

              {/* Remove button */}
              <button
                onClick={(e) => {
                  e.stopPropagation()
                  handleRemoveImage()
                }}
                className="absolute top-2 right-2 bg-red-500 hover:bg-red-600 text-white rounded-full p-1 transition-colors"
                disabled={disabled}
              >
                <X className="w-3 h-3" />
              </button>

              {/* Overlay on hover */}
              <div className="absolute inset-0 bg-black/50 opacity-0 hover:opacity-100 transition-opacity rounded-lg flex items-center justify-center">
                <div className="text-white text-center">
                  <Camera className="w-6 h-6 mx-auto mb-1" />
                  <span className="text-sm">Click to change</span>
                </div>
              </div>
            </motion.div>
          ) : (
            <motion.div
              key="upload"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="flex flex-col items-center justify-center p-6 text-center"
            >
              {uploading ? (
                <>
                  <div className="w-8 h-8 border-2 border-accent/20 border-t-accent rounded-full animate-spin mb-3" />
                  <p className="text-sm text-secondary">Uploading...</p>
                </>
              ) : (
                <>
                  <Upload className="w-8 h-8 text-secondary mb-3" />
                  <p className="text-sm text-primary font-medium mb-2">{placeholder}</p>
                  <p className="text-xs text-secondary mb-1">
                    Drag & drop, click, or paste (Ctrl+V)
                  </p>
                  <p className="text-xs text-muted">
                    Max {maxSize}MB • {acceptedTypes.map((type) => type.split('/')[1]).join(', ')}
                  </p>
                </>
              )}
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  )
}

export default ImageUpload
