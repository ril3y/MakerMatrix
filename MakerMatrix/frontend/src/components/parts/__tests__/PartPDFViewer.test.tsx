import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import PartPDFViewer from '../PartPDFViewer'
import { apiClient } from '@/services/api'
import type { Datasheet } from '@/types/parts'

// Mock the api module so the apiClient.get call is observable and never hits
// MSW. The datasheet.service imports apiClient from here.
vi.mock('@/services/api', async () => {
  const actual = await vi.importActual<typeof import('@/services/api')>('@/services/api')
  return {
    ...actual,
    apiClient: {
      get: vi.fn(),
    },
  }
})

const mockedApiClient = vi.mocked(apiClient)

const datasheet: Datasheet = {
  id: 'ds-1',
  filename: 'TI-TLV9061.pdf',
  original_filename: 'TLV9061-Datasheet.pdf',
  file_size: 102_400,
  is_downloaded: true,
} as unknown as Datasheet

describe('PartPDFViewer', () => {
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
    URL.createObjectURL = createObjectURLMock as unknown as typeof URL.createObjectURL
    URL.revokeObjectURL = revokeObjectURLMock as unknown as typeof URL.revokeObjectURL
  })

  afterEach(() => {
    if (originalCreate) URL.createObjectURL = originalCreate
    if (originalRevoke) URL.revokeObjectURL = originalRevoke
  })

  it('does not fetch anything while closed', () => {
    render(<PartPDFViewer isOpen={false} onClose={() => {}} datasheet={datasheet} />)
    expect(mockedApiClient.get).not.toHaveBeenCalled()
  })

  it('fetches the datasheet as a blob and sets the iframe src to the object URL', async () => {
    const blob = new Blob(['%PDF-1.4'], { type: 'application/pdf' })
    mockedApiClient.get.mockResolvedValueOnce(blob)
    createObjectURLMock.mockReturnValueOnce('blob:datasheet-1')

    render(<PartPDFViewer isOpen={true} onClose={() => {}} datasheet={datasheet} />)

    await waitFor(() => {
      expect(mockedApiClient.get).toHaveBeenCalledWith(
        '/api/utility/static/datasheets/TI-TLV9061.pdf',
        { responseType: 'blob' }
      )
    })

    // Object URL is derived from the blob and assigned to the iframe.
    await waitFor(() => {
      const iframe = document.querySelector('iframe') as HTMLIFrameElement | null
      expect(iframe).not.toBeNull()
      expect(iframe?.src).toContain('blob:datasheet-1')
    })

    // Header still renders the friendly filename.
    expect(screen.getByText('TLV9061-Datasheet.pdf')).toBeInTheDocument()
  })

  it('revokes the object URL on unmount', async () => {
    const blob = new Blob(['%PDF-1.4'], { type: 'application/pdf' })
    mockedApiClient.get.mockResolvedValueOnce(blob)
    createObjectURLMock.mockReturnValueOnce('blob:datasheet-revoke')

    const { unmount } = render(
      <PartPDFViewer isOpen={true} onClose={() => {}} datasheet={datasheet} />
    )

    await waitFor(() => {
      expect(createObjectURLMock).toHaveBeenCalledTimes(1)
    })

    unmount()

    // Both the effect cleanup and the unmount cleanup may fire; what matters
    // is that the URL is revoked at least once.
    expect(revokeObjectURLMock).toHaveBeenCalledWith('blob:datasheet-revoke')
  })

  it('shows the error state when the fetch fails', async () => {
    mockedApiClient.get.mockRejectedValueOnce(new Error('network down'))

    render(<PartPDFViewer isOpen={true} onClose={() => {}} datasheet={datasheet} />)

    await waitFor(() => {
      expect(screen.getByText('Failed to Load PDF')).toBeInTheDocument()
    })
    // No iframe should be rendered when the fetch errors.
    expect(document.querySelector('iframe')).toBeNull()
  })
})
