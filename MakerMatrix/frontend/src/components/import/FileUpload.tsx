import React from 'react'
import { Upload, CheckCircle, X } from 'lucide-react'

interface FileUploadProps {
  file: File | null
  totalRows?: number
  parserName: string
  description: string
  filePattern?: string
  onFileSelect: (file: File) => void
  onFileChange: (event: React.ChangeEvent<HTMLInputElement>) => void
  onDrop: (event: React.DragEvent<HTMLDivElement>) => void
  onDragOver: (event: React.DragEvent<HTMLDivElement>) => void
  onClear: () => void
  fileInputRef: React.RefObject<HTMLInputElement>
}

const FileUpload: React.FC<FileUploadProps> = ({
  file,
  totalRows,
  parserName,
  description,
  filePattern,
  onFileChange,
  onDrop,
  onDragOver,
  onClear,
  fileInputRef
}) => {
  return (
    <div
      className={`border-2 border-dashed rounded-lg p-8 text-center transition-colors ${
        file ? 'border-accent bg-accent/10' : 'border-border-secondary hover:border-primary'
      }`}
      onDrop={onDrop}
      onDragOver={onDragOver}
    >
      <input
        ref={fileInputRef}
        type="file"
        accept=".csv,.xls,.xlsx"
        onChange={onFileChange}
        className="hidden"
      />

      {file ? (
        <div className="space-y-2">
          <CheckCircle className="w-8 h-8 text-accent mx-auto" />
          <p className="text-primary font-medium">{file.name}</p>
          <p className="text-sm text-secondary">
            {(file.size / 1024).toFixed(1)} KB • {totalRows || 0} rows
          </p>
          <button
            onClick={onClear}
            className="btn btn-secondary btn-sm mt-2"
          >
            <X className="w-4 h-4 mr-1" />
            Clear
          </button>
        </div>
      ) : (
        <div className="space-y-2">
          <Upload className="w-8 h-8 text-muted mx-auto" />
          <p className="text-primary font-medium">Drop {parserName} CSV file here or click to browse</p>
          <p className="text-sm text-secondary">{description}</p>
          {filePattern && (
            <p className="text-xs text-muted">Expected format: {filePattern}</p>
          )}
          <button
            onClick={() => fileInputRef.current?.click()}
            className="btn btn-primary mt-2"
          >
            Select File
          </button>
        </div>
      )}
    </div>
  )
}

export default FileUpload