import type { ApiResponse } from '@/services/api'
import { apiClient } from '@/services/api'

export interface ImageUploadResponse {
  image_id: string
}

class UtilityService {
  async uploadImage(file: File): Promise<string> {
    const formData = new FormData()
    formData.append('file', file)

    const response = await apiClient.post<ApiResponse<ImageUploadResponse>>(
      '/api/utility/upload_image',
      formData,
      {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      }
    )

    console.log('🔍 Upload response:', response)
    console.log('📊 Response status:', response.status)
    console.log('📦 Response data:', response.data)

    if (response.status === 'success' && response.data) {
      // Return the full image URL - backend handles extension lookup
      const imageId = response.data.image_id
      const imageUrl = `/api/utility/get_image/${imageId}`
      console.log('🖼️ Generated image URL:', imageUrl)
      return imageUrl
    }
    console.error('❌ Upload failed - response:', response)
    throw new Error(response.message || 'Failed to upload image')
  }
}

export const utilityService = new UtilityService()
