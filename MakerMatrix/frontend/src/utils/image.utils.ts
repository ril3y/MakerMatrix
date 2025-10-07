/**
 * Image utility functions for handling different image URL patterns
 */

/**
 * Normalizes image URLs to ensure they work with our unified image system
 * @param imageUrl - The image URL from the API
 * @returns Normalized image URL or null if invalid
 */
export function normalizeImageUrl(imageUrl: string | null | undefined): string | null {
  if (!imageUrl || imageUrl.trim() === '') {
    return null
  }

  const url = imageUrl.trim()

  // Already normalized URLs (new format)
  if (url.startsWith('/utility/get_image/')) {
    return url
  }

  // Handle API prefixed URLs (keep the /api prefix)
  if (url.startsWith('/api/utility/get_image/')) {
    return url
  }

  // Legacy static URLs (backward compatibility)
  if (url.startsWith('/static/images/')) {
    return url
  }

  // External URLs (keep as-is)
  if (url.startsWith('http://') || url.startsWith('https://')) {
    return url
  }

  // Invalid or malformed URLs
  console.warn(`Invalid image URL format: ${url}`)
  return null
}

/**
 * Checks if an image URL is using the new unified format
 * @param imageUrl - The image URL to check
 * @returns True if using new format, false otherwise
 */
export function isNewImageFormat(imageUrl: string | null | undefined): boolean {
  return imageUrl?.startsWith('/utility/get_image/') ?? false
}

/**
 * Checks if an image URL is using the legacy format
 * @param imageUrl - The image URL to check
 * @returns True if using legacy format, false otherwise
 */
export function isLegacyImageFormat(imageUrl: string | null | undefined): boolean {
  return imageUrl?.startsWith('/static/images/') ?? false
}

/**
 * Gets a fallback image URL for failed loads
 * @returns Default placeholder image URL or null
 */
export function getFallbackImageUrl(): string | null {
  // Could return a default placeholder image URL here if needed
  return null
}
