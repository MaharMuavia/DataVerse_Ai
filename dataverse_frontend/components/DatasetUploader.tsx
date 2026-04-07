'use client'

import { useState, useCallback } from 'react'
import { Upload, FileText, AlertCircle } from 'lucide-react'
import { uploadDataset } from '@/lib/api'
import { Session } from '@/types'

interface DatasetUploaderProps {
  onUploadSuccess: (session: Session) => void
}

export function DatasetUploader({ onUploadSuccess }: DatasetUploaderProps) {
  const [isDragging, setIsDragging] = useState(false)
  const [isUploading, setIsUploading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [uploadedFile, setUploadedFile] = useState<File | null>(null)

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(true)
  }, [])

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(false)
  }, [])

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(false)

    const files = Array.from(e.dataTransfer.files)
    if (files.length > 0) {
      handleFileSelect(files[0])
    }
  }, [])

  const handleFileSelect = async (file: File) => {
    // Validate file type
    const allowedTypes = ['text/csv', 'application/vnd.ms-excel', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet']
    if (!allowedTypes.includes(file.type) && !file.name.endsWith('.csv')) {
      setError('Please upload a CSV file')
      return
    }

    // Validate file size (max 50MB)
    if (file.size > 50 * 1024 * 1024) {
      setError('File size must be less than 50MB')
      return
    }

    setUploadedFile(file)
    setError(null)
    setIsUploading(true)

    try {
      const session = await uploadDataset(file)
      onUploadSuccess(session)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Upload failed')
    } finally {
      setIsUploading(false)
    }
  }

  const handleFileInput = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (file) {
      handleFileSelect(file)
    }
  }

  return (
    <div className="w-full max-w-md mx-auto">
      <div
        className={`relative border-2 border-dashed rounded-lg p-8 text-center transition-colors ${
          isDragging
            ? 'border-primary-500 bg-primary-50'
            : 'border-gray-300 hover:border-gray-400'
        } ${isUploading ? 'pointer-events-none opacity-50' : ''}`}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
      >
        <input
          type="file"
          accept=".csv,.xlsx,.xls"
          onChange={handleFileInput}
          className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
          disabled={isUploading}
        />

        <div className="flex flex-col items-center">
          {isUploading ? (
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600 mb-4"></div>
          ) : (
            <Upload className="h-12 w-12 text-gray-400 mb-4" />
          )}

          <h3 className="text-lg font-medium text-gray-900 mb-2">
            {isUploading ? 'Uploading...' : 'Upload your dataset'}
          </h3>

          <p className="text-sm text-gray-500 mb-4">
            Drag and drop your CSV file here, or click to browse
          </p>

          {uploadedFile && (
            <div className="flex items-center text-sm text-gray-600 mb-4">
              <FileText className="h-4 w-4 mr-2" />
              {uploadedFile.name} ({(uploadedFile.size / 1024 / 1024).toFixed(1)} MB)
            </div>
          )}

          <p className="text-xs text-gray-400">
            Supports CSV files up to 50MB
          </p>
        </div>
      </div>

      {error && (
        <div className="mt-4 p-3 bg-red-50 border border-red-200 rounded-md">
          <div className="flex items-center">
            <AlertCircle className="h-4 w-4 text-red-500 mr-2" />
            <span className="text-sm text-red-700">{error}</span>
          </div>
        </div>
      )}
    </div>
  )
}
