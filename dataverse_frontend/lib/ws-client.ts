export enum WSMessageType {
  USER_MESSAGE = 'user_message',
  INTENT_CLASSIFIED = 'intent_classified',
  EDA_STARTED = 'eda_started',
  EDA_COMPLETED = 'eda_completed',
  VIZ_COMPLETED = 'viz_completed',
  ML_STARTED = 'ml_started',
  ML_COMPLETED = 'ml_completed',
  XAI_STARTED = 'xai_started',
  XAI_COMPLETED = 'xai_completed',
  ERROR = 'error',
}

export interface WSMessage {
  type: WSMessageType
  content?: string
  intent?: any
  results?: any
  error?: string
  sessionId?: string
}

export interface WSClientOptions {
  url?: string
  sessionId: string
  onMessage: (msg: WSMessage) => void
  onConnect: () => void
  onDisconnect: () => void
  onError: (error: Error) => void
}

export class DataVerseWSClient {
  private ws: WebSocket | null = null
  private reconnectAttempts = 0
  private maxReconnects = 3
  private reconnectTimeout: NodeJS.Timeout | null = null

  constructor(private opts: WSClientOptions) {}

  connect() {
    const url = this.opts.url || `ws://localhost:8000/ws`
    this.ws = new WebSocket(`${url}/${this.opts.sessionId}`)

    this.ws.onopen = () => {
      this.reconnectAttempts = 0
      this.opts.onConnect()
    }

    this.ws.onmessage = (event) => {
      try {
        const message: WSMessage = JSON.parse(event.data)
        this.opts.onMessage(message)
      } catch (error) {
        this.opts.onError(new Error('Failed to parse WebSocket message'))
      }
    }

    this.ws.onclose = () => {
      this.opts.onDisconnect()
      this.attemptReconnect()
    }

    this.ws.onerror = (error) => {
      this.opts.onError(new Error('WebSocket error'))
    }
  }

  send(message: WSMessage) {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(message))
    }
  }

  disconnect() {
    if (this.reconnectTimeout) {
      clearTimeout(this.reconnectTimeout)
      this.reconnectTimeout = null
    }
    if (this.ws) {
      this.ws.close()
      this.ws = null
    }
  }

  private attemptReconnect() {
    if (this.reconnectAttempts < this.maxReconnects) {
      this.reconnectAttempts++
      this.reconnectTimeout = setTimeout(() => {
        this.connect()
      }, 1000 * this.reconnectAttempts)
    }
  }
}