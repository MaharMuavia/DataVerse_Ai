import {
  ActiveFilter,
  AgentQueryResponse,
  ProactiveInsight,
  Session,
  StreamEvent,
} from '@/types'

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8001/api'

interface UploadApiResponse {
  session_id: string
  success: boolean
  message: string
  is_retail: boolean
  matched_keywords?: string[]
  dataset_filename?: string
  dataset_rows?: number
  dataset_cols?: number
  created_at?: string
}

function normalizeSession(payload: UploadApiResponse, fallbackFileName: string): Session {
  return {
    id: payload.session_id,
    dataset_filename: payload.dataset_filename || fallbackFileName,
    dataset_rows: payload.dataset_rows || 0,
    dataset_cols: payload.dataset_cols || 0,
    created_at: payload.created_at || new Date().toISOString(),
    message: payload.message,
    is_retail: payload.is_retail,
    matched_keywords: payload.matched_keywords || [],
  }
}

export async function uploadDataset(file: File): Promise<Session> {
  const formData = new FormData()
  formData.append('file', file)

  const response = await fetch(`${API_BASE}/upload`, {
    method: 'POST',
    body: formData,
  })

  if (!response.ok) {
    const errorText = await response.text()
    throw new Error(errorText || 'Failed to upload dataset')
  }

  const payload = (await response.json()) as UploadApiResponse
  return normalizeSession(payload, file.name)
}

export async function processAgentQuery(sessionId: string, query: string): Promise<AgentQueryResponse> {
  const response = await fetch(`${API_BASE}/agent/query`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ session_id: sessionId, query }),
  })

  if (!response.ok) {
    const errorText = await response.text()
    throw new Error(errorText || 'Failed to process query')
  }

  return response.json()
}

export function createStream(
  sessionId: string,
  query: string,
  onEvent: (event: StreamEvent) => void
): EventSource {
  const params = new URLSearchParams({
    session_id: sessionId,
    query,
  })
  const eventSource = new EventSource(`${API_BASE}/stream/query?${params.toString()}`)

  eventSource.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data) as StreamEvent
      onEvent(data)
    } catch (error) {
      console.error('Failed to parse stream event:', error)
    }
  }

  eventSource.onerror = () => {
    onEvent({ step: 'error', message: 'Stream connection failed' })
  }

  return eventSource
}

export async function getProactiveInsights(sessionId: string): Promise<ProactiveInsight[]> {
  const response = await fetch(`${API_BASE}/session/${sessionId}/proactive-insights`)

  if (!response.ok) {
    const errorText = await response.text()
    throw new Error(errorText || 'Failed to fetch proactive insights')
  }

  const payload = await response.json()
  return payload.insights || []
}

export async function clearActiveFilters(sessionId: string): Promise<ActiveFilter[]> {
  const response = await fetch(`${API_BASE}/session/${sessionId}/active-filters`, {
    method: 'DELETE',
  })

  if (!response.ok) {
    const errorText = await response.text()
    throw new Error(errorText || 'Failed to clear active filters')
  }

  const payload = await response.json()
  return payload.active_filters || []
}
