export type Intent = 'EDA' | 'VIZ' | 'ML' | 'XAI' | 'SQL' | 'CHITCHAT'

export type MessageRole = 'user' | 'assistant'

export interface EDAResults {
  rowCount: number
  columnCount: number
  missingValuesCount: number
  numericColumnsCount: number
  correlations?: Array<{
    feature1: string
    feature2: string
    correlation: number
  }>
  outliers?: {
    totalOutliers: number
    columnsWithOutliers: number
  }
}

export interface MLResults {
  status: 'pending' | 'running' | 'completed' | 'failed'
  bestModel?: {
    name: string
    accuracy: number
  }
  models?: Array<{
    name: string
    accuracy: number
  }>
  error?: string
}

export interface XAIResults {
  featureImportance?: Array<{
    name: string
    importance: number
  }>
  shapValues?: any[]
  limeExplanations?: Array<{
    explanation: string
    confidence: number
  }>
  recommendations?: string[]
}

export interface Message {
  id: string
  role: MessageRole
  content: string
  intent?: Intent
  timestamp: Date
  vizFigureJson?: string
  edaResults?: EDAResults
  taskId?: string
  metrics?: Record<string, number>
  shapPlotPath?: string
  topFeatures?: string
  isThinking?: boolean
  error?: string
}

export interface Dataset {
  datasetId: string
  filename: string
  columnNames: string[]
  columnDtypes: string[]
  rowCount: number
  uploadedAt: Date
}

export interface Session {
  sessionId: string
  dataset?: Dataset
  messages: Message[]
}