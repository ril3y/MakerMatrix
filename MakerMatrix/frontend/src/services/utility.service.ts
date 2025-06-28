import { apiClient } from '@/services/api'

export interface ImageUploadResponse {
  image_id: string
}

class UtilityService {
  async uploadImage(file: File): Promise<string> {
    const formData = new FormData()
    formData.append('file', file)

    const response = await apiClient.post<ImageUploadResponse>('/api/utility/upload_image', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    })

    // Return the full image URL - backend handles extension lookup
    const imageId = response.image_id
    return `/api/utility/get_image/${imageId}`
  }
}

export const utilityService = new UtilityService()