import { useState, useEffect, useCallback, useRef } from 'react'
import { DataVerseWSClient, WSMessageType } from '../ws-client'
import { Message, Intent, EDAResults, MLResults, XAIResults } from '../types'

export function useAnalysis(sessionId: string) {
  const [messages, setMessages] = useState<Message[]>([])
  const [isConnected, setIsConnected] = useState(false)
  const [isTyping, setIsTyping] = useState(false)
  const [currentIntent, setCurrentIntent] = useState<Intent | null>(null)
  const [results, setResults] = useState<{
    eda?: EDAResults
    ml?: MLResults
    xai?: XAIResults
  }>({})
  const wsClientRef = useRef<DataVerseWSClient | null>(null)

  useEffect(() => {
    const wsClient = new DataVerseWSClient({
      url: process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8000/ws',
      sessionId,
      onMessage: handleWSMessage,
      onConnect: () => setIsConnected(true),
      onDisconnect: () => setIsConnected(false),
      onError: (error) => console.error('WS Error:', error),
    })

    wsClientRef.current = wsClient
    wsClient.connect()

    return () => {
      wsClient.disconnect()
    }
  }, [sessionId])

  const handleWSMessage = useCallback((message: any) => {
    switch (message.type) {
      case WSMessageType.INTENT_CLASSIFIED:
        setCurrentIntent(message.intent)
        break
      case WSMessageType.EDA_STARTED:
        setIsTyping(true)
        break
      case WSMessageType.EDA_COMPLETED:
        setResults(prev => ({ ...prev, eda: message.results }))
        setIsTyping(false)
        break
      case WSMessageType.VIZ_COMPLETED:
        // Handle visualization results if needed
        break
      case WSMessageType.ML_STARTED:
        setIsTyping(true)
        break
      case WSMessageType.ML_COMPLETED:
        setResults(prev => ({ ...prev, ml: message.results }))
        setIsTyping(false)
        break
      case WSMessageType.XAI_STARTED:
        setIsTyping(true)
        break
      case WSMessageType.XAI_COMPLETED:
        setResults(prev => ({ ...prev, xai: message.results }))
        setIsTyping(false)
        break
      case WSMessageType.ERROR:
        setMessages(prev => [...prev, {
          id: Date.now().toString(),
          role: 'assistant',
          content: `Error: ${message.error}`,
          timestamp: new Date(),
        }])
        setIsTyping(false)
        break
    }
  }, [])

  const sendMessage = useCallback((content: string) => {
    if (!wsClientRef.current || !isConnected) return

    const userMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content,
      timestamp: new Date(),
    }

    setMessages(prev => [...prev, userMessage])
    wsClientRef.current.send({
      type: WSMessageType.USER_MESSAGE,
      content,
      sessionId,
    })
  }, [isConnected, sessionId])

  const clearResults = useCallback(() => {
    setResults({})
    setCurrentIntent(null)
  }, [])

  return {
    messages,
    isConnected,
    isTyping,
    currentIntent,
    results,
    sendMessage,
    clearResults,
  }
}