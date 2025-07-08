import { apiClient, ApiResponse } from '@/services/api'

export interface ImageUploadResponse {
  image_id: string
}

class UtilityService {
  async uploadImage(file: File): Promise<string> {
    const formData = new FormData()
    formData.append('file', file)

    const response = await apiClient.post<ApiResponse<ImageUploadResponse>>('/api/utility/upload_image', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    })

    if (response.status === 'success' && response.data) {
      // Return the full image URL - backend handles extension lookup
      const imageId = response.data.image_id
      return `/api/utility/get_image/${imageId}`
    }
    throw new Error(response.message || 'Failed to upload image')
  }
}

export const utilityService = new UtilityService()