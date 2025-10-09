/**
 * URL Utility Functions
 *
 * Utilities for parsing URLs, extracting domains, and generating favicon URLs
 */

/**
 * Parse a URL and extract the domain name
 * @param url - Full URL string
 * @returns Domain name (e.g., "github.com") or null if invalid
 */
export const extractDomain = (url: string): string | null => {
  try {
    // Ensure URL has a protocol
    const fullUrl = url.startsWith('http') ? url : `https://${url}`
    const parsed = new URL(fullUrl)
    return parsed.hostname
  } catch {
    return null
  }
}

/**
 * Extract a display name from a domain
 * @param domain - Domain name (e.g., "github.com")
 * @returns Capitalized display name (e.g., "GitHub")
 */
export const extractDisplayName = (domain: string): string => {
  // Remove common TLDs and www
  const name = domain
    .replace(/^www\./, '')
    .replace(/\.(com|org|net|io|dev|co|uk|us)$/, '')

  // Capitalize first letter of each word (handle domains like "github" -> "GitHub")
  return name
    .split(/[.-]/)
    .map(word => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ')
}

/**
 * Get favicon URL from Google's favicon service
 * @param url - Full URL or domain
 * @returns Favicon URL from Google's service
 */
export const getFaviconUrl = (url: string): string => {
  const domain = extractDomain(url)
  if (!domain) return ''

  // Use Google's favicon service - reliable and fast
  return `https://www.google.com/s2/favicons?domain=${domain}&sz=64`
}

/**
 * Parse a URL and extract both domain and display name
 * @param url - Full URL string
 * @returns Object with domain and display name, or null if invalid
 */
export const parseUrl = (url: string): { domain: string; displayName: string } | null => {
  const domain = extractDomain(url)
  if (!domain) return null

  return {
    domain,
    displayName: extractDisplayName(domain)
  }
}

/**
 * Normalize a URL to ensure it has a protocol
 * @param url - URL string that may or may not have protocol
 * @returns Normalized URL with https:// protocol
 */
export const normalizeUrl = (url: string): string => {
  if (!url) return ''
  return url.startsWith('http') ? url : `https://${url}`
}
