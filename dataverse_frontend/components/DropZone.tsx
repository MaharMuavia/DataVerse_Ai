import { useCallback, useState } from 'react'
import { Upload, File } from 'lucide-react'
import { useUpload } from '../lib/hooks/useUpload'
import { Dataset } from '../lib/types'

interface DropZoneProps {
  sessionId: string
  onDatasetUploaded: (dataset: Dataset) => void
}

export function DropZone({ sessionId, onDatasetUploaded }: DropZoneProps) {
  const [isDragOver, setIsDragOver] = useState(false)
  const { uploadDataset, isUploading, uploadProgress, error } = useUpload()

  const handleDrop = useCallback(async (e: React.DragEvent) => {
    e.preventDefault()
    setIsDragOver(false)

    const files = Array.from(e.dataTransfer.files)
    const csvFile = files.find(file => file.type === 'text/csv' || file.name.endsWith('.csv'))

    if (csvFile) {
      const dataset = await uploadDataset(csvFile, sessionId)
      if (dataset) {
        onDatasetUploaded(dataset)
      }
    }
  }, [uploadDataset, sessionId, onDatasetUploaded])

  const handleFileSelect = useCallback(async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (file) {
      const dataset = await uploadDataset(file, sessionId)
      if (dataset) {
        onDatasetUploaded(dataset)
      }
    }
  }, [uploadDataset, sessionId, onDatasetUploaded])

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setIsDragOver(true)
  }, [])

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setIsDragOver(false)
  }, [])

  return (
    <div className="w-full">
      <div
        onDrop={handleDrop}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        className={`border-2 border-dashed rounded-lg p-8 text-center transition-colors ${
          isDragOver
            ? 'border-dv-accent bg-dv-accent/10'
            : 'border-dv-border hover:border-dv-accent/50'
        }`}
      >
        <div className="flex flex-col items-center gap-4">
          {isUploading ? (
            <>
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-dv-accent"></div>
              <p className="text-sm text-dv-text-secondary">
                Uploading... {uploadProgress}%
              </p>
              <div className="w-full bg-dv-surface rounded-full h-2">
                <div
                  className="bg-dv-accent h-2 rounded-full transition-all duration-300"
                  style={{ width: `${uploadProgress}%` }}
                ></div>
              </div>
            </>
          ) : (
            <>
              <Upload size={48} className="text-dv-text-secondary" />
              <div>
                <p className="text-lg font-medium text-dv-text">
                  Drop your CSV file here
                </p>
                <p className="text-sm text-dv-text-secondary mt-1">
                  or click to browse
                </p>
              </div>
              <input
                type="file"
                accept=".csv"
                onChange={handleFileSelect}
                className="hidden"
                id="file-upload"
              />
              <label
                htmlFor="file-upload"
                className="px-4 py-2 bg-dv-accent text-dv-accent-foreground rounded-lg cursor-pointer hover:bg-dv-accent/90 transition-colors"
              >
                Choose File
              </label>
            </>
          )}
        </div>
      </div>

      {error && (
        <p className="text-sm text-red-500 mt-2">{error}</p>
      )}
    </div>
  )
}