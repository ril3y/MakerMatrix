import { Printer as PrinterIcon } from 'lucide-react'

interface LabelPreviewProps {
  /** Blob URL of the preview image, or null when no preview is available. */
  previewUrl: string | null
  /** Text shown when no preview is available. */
  emptyMessage?: string
  /** Caption below the image. */
  caption?: string
  /** Whether a preview is currently being generated. */
  loading?: boolean
  /** Optional extra class names on the outer wrapper. */
  className?: string
}

/**
 * Reusable label preview widget.
 *
 * Displays a label preview image inside a styled container, or a placeholder
 * when no preview URL is set.
 */
const LabelPreview = ({
  previewUrl,
  emptyMessage = 'Select a template or enter text to see preview',
  caption = 'Label Preview',
  loading = false,
  className = '',
}: LabelPreviewProps) => {
  return (
    <div
      className={`bg-background-secondary rounded-lg p-4 flex items-center justify-center min-h-64 ${className}`}
    >
      {loading ? (
        <div className="text-center text-muted">
          <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-primary mx-auto mb-2" />
          <p className="text-sm">Generating preview...</p>
        </div>
      ) : previewUrl ? (
        <div className="text-center">
          <img
            src={previewUrl}
            alt={caption}
            className="max-w-full max-h-48 border border-border rounded mx-auto block"
            style={{ transformOrigin: 'center' }}
          />
          <p className="text-sm text-secondary mt-2">{caption}</p>
        </div>
      ) : (
        <div className="text-center text-muted">
          <PrinterIcon className="w-12 h-12 mx-auto mb-2 opacity-50" />
          <p>{emptyMessage}</p>
        </div>
      )}
    </div>
  )
}

export default LabelPreview
