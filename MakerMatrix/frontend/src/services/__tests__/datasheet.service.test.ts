import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { fetchDatasheetBlob, revokeDatasheetBlob } from '../datasheet.service'
import { apiClient, getErrorMessage } from '../api'

vi.mock('../api', async () => {
  const actual = await vi.importActual<typeof import('../api')>('../api')
  return {
    ...actual,
    apiClient: {
      get: vi.fn(),
    },
  }
})

const mockedApiClient = vi.mocked(apiClient)

describe('datasheet.service', () => {
  const createObjectURLMock = vi.fn()
  const revokeObjectURLMock = vi.fn()
  let originalCreate: typeof URL.createObjectURL | undefined
  let originalRevoke: typeof URL.revokeObjectURL | undefined

  beforeEach(() => {
    vi.clearAllMocks()
    createObjectURLMock.mockReset()
    revokeObjectURLMock.mockReset()
    originalCreate = URL.createObjectURL
    originalRevoke = URL.revokeObjectURL
    // jsdom only ships a partial URL impl; stub the bits we need.
    URL.createObjectURL = createObjectURLMock as unknown as typeof URL.createObjectURL
    URL.revokeObjectURL = revokeObjectURLMock as unknown as typeof URL.revokeObjectURL
  })

  afterEach(() => {
    if (originalCreate) URL.createObjectURL = originalCreate
    if (originalRevoke) URL.revokeObjectURL = originalRevoke
  })

  describe('fetchDatasheetBlob', () => {
    it('requests the datasheet endpoint with blob response type and returns an object URL', async () => {
      const blob = new Blob(['fake-pdf-bytes'], { type: 'application/pdf' })
      mockedApiClient.get.mockResolvedValueOnce(blob)
      createObjectURLMock.mockReturnValueOnce('blob:fake-url')

      const result = await fetchDatasheetBlob('TI-TLV9061.pdf')

      expect(mockedApiClient.get).toHaveBeenCalledWith(
        '/api/utility/static/datasheets/TI-TLV9061.pdf',
        { responseType: 'blob' }
      )
      expect(createObjectURLMock).toHaveBeenCalledWith(blob)
      expect(result).toBe('blob:fake-url')
    })

    it('URL-encodes filenames containing special characters', async () => {
      const blob = new Blob([''], { type: 'application/pdf' })
      mockedApiClient.get.mockResolvedValueOnce(blob)
      createObjectURLMock.mockReturnValueOnce('blob:enc')

      await fetchDatasheetBlob('foo bar+baz#1.pdf')

      expect(mockedApiClient.get).toHaveBeenCalledWith(
        '/api/utility/static/datasheets/foo%20bar%2Bbaz%231.pdf',
        { responseType: 'blob' }
      )
    })

    it('propagates errors from the apiClient so callers can surface them', async () => {
      const apiError = Object.assign(new Error('boom'), {
        response: { data: { detail: 'PDF not found' }, status: 404 },
      })
      mockedApiClient.get.mockRejectedValueOnce(apiError)

      await expect(fetchDatasheetBlob('missing.pdf')).rejects.toBe(apiError)
      expect(createObjectURLMock).not.toHaveBeenCalled()
      // getErrorMessage should pull the FastAPI-style detail out, so callers
      // can format the toast consistently.
      expect(getErrorMessage(apiError)).toBe('PDF not found')
    })
  })

  describe('revokeDatasheetBlob', () => {
    it('revokes blob: URLs', () => {
      revokeDatasheetBlob('blob:abc123')
      expect(revokeObjectURLMock).toHaveBeenCalledWith('blob:abc123')
    })

    it('is a no-op for null, empty, or non-blob URLs', () => {
      revokeDatasheetBlob(null)
      revokeDatasheetBlob(undefined)
      revokeDatasheetBlob('')
      revokeDatasheetBlob('https://example.com/file.pdf')
      expect(revokeObjectURLMock).not.toHaveBeenCalled()
    })
  })
})
