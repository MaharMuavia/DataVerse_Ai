import { useState, useCallback } from 'react'
import { Dataset } from '../types'

export function useUpload() {
  const [isUploading, setIsUploading] = useState(false)
  const [uploadProgress, setUploadProgress] = useState(0)
  const [error, setError] = useState<string | null>(null)

  const uploadDataset = useCallback(async (
    file: File,
    sessionId: string
  ): Promise<Dataset | null> => {
    setIsUploading(true)
    setError(null)
    setUploadProgress(0)

    const formData = new FormData()
    formData.append('file', file)
    formData.append('session_id', sessionId)

    try {
      const xhr = new XMLHttpRequest()

      await new Promise<void>((resolve, reject) => {
        xhr.upload.onprogress = (e) => {
          if (e.lengthComputable) {
            setUploadProgress(Math.round((e.loaded / e.total) * 100))
          }
        }

        xhr.onload = () => {
          if (xhr.status === 200) resolve()
          else reject(new Error(xhr.responseText))
        }

        xhr.onerror = () => reject(new Error('Upload failed'))
        xhr.open('POST', `${process.env.NEXT_PUBLIC_API_URL}/api/upload`)
        xhr.send(formData)
      })

      const data = JSON.parse(xhr.responseText)
      return {
        datasetId: data.dataset_id,
        filename: file.name,
        columnNames: data.column_names,
        columnDtypes: data.column_dtypes,
        rowCount: data.row_count,
        uploadedAt: new Date(),
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Upload failed')
      return null
    } finally {
      setIsUploading(false)
    }
  }, [])

  return { uploadDataset, isUploading, uploadProgress, error }
}