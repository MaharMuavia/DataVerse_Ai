export interface Session {
  id: string
  dataset_filename: string
  dataset_rows: number
  dataset_cols: number
  created_at: string
  message?: string
  is_retail?: boolean
  matched_keywords?: string[]
}

export interface ActiveFilter {
  column: string
  operator: string
  value: string | number | boolean | null
}

export interface ClarificationRequest {
  type: 'clarification'
  question: string
  options?: string[] | null
  session_id: string
}

export interface ProactiveInsight {
  title: string
  description: string
  follow_up_query?: string
  icon?: string
}

export interface AgentStep {
  step?: number
  tool: string
  purpose?: string | null
  success?: boolean
  error_message?: string | null
  result?: any
}

export interface Message {
  id: string
  type: 'user' | 'assistant'
  content: string
  timestamp: Date
  chartSpec?: any
  narration?: string
  tables?: any[]
  clarification?: ClarificationRequest | null
}

export interface AgentQueryResponse {
  session_id: string
  narrative: string
  charts: any[]
  tables: any[]
  model_results: any[]
  explanation: string
  steps: AgentStep[]
  clarification?: ClarificationRequest | null
  active_filters?: ActiveFilter[]
}

export interface StreamEvent {
  step: string
  message: string
  intent?: string
  confidence?: number
  narration?: string
  chart_spec?: any
  computed_facts?: any
}
