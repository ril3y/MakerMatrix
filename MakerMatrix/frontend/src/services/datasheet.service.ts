/**
 * Datasheet blob helpers.
 *
 * The backend's `GET /api/utility/static/datasheets/{filename}` endpoint now
 * requires a Bearer token (CVE-002 hardening). `<iframe src>` and `<a href download>`
 * cannot attach the token, so consumers must fetch the bytes via `apiClient`
 * (which injects auth) and then expose them as an `blob:` object URL.
 *
 * Always call `revokeDatasheetBlob` on the returned URL in your cleanup
 * (component unmount / re-fetch) to avoid leaking memory.
 */
import { apiClient } from './api'

/**
 * Fetch a stored datasheet by filename and return an object URL pointing at
 * its bytes. The caller owns the URL and must revoke it.
 */
export async function fetchDatasheetBlob(filename: string): Promise<string> {
  const response = await apiClient.get<Blob>(
    `/api/utility/static/datasheets/${encodeURIComponent(filename)}`,
    {
      responseType: 'blob',
    }
  )
  return URL.createObjectURL(response)
}

/**
 * Release an object URL previously returned by `fetchDatasheetBlob`. Safe to
 * call with `null`/empty string — those are no-ops.
 */
export function revokeDatasheetBlob(url: string | null | undefined): void {
  if (url && url.startsWith('blob:')) {
    URL.revokeObjectURL(url)
  }
}
