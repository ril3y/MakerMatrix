import { apiClient } from '@/services/api'

export interface ImageUploadResponse {
  image_id: string
}

class UtilityService {
  async uploadImage(file: File): Promise<string> {
    const formData = new FormData()
    formData.append('file', file)

    const response = await apiClient.post<ImageUploadResponse>('/utility/upload_image', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    })

    // Return the full image URL
    const imageId = response.image_id
    const fileExtension = file.name.split('.').pop() || 'png'
    return `/utility/get_image/${imageId}.${fileExtension}`
  }
}

export const utilityService = new UtilityService()