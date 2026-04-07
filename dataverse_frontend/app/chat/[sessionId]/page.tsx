'use client'

import { useState, useEffect } from 'react'
import { useParams } from 'next/navigation'
import { AppShell } from '../../components/AppShell'
import { ChatWindow } from '../../components/ChatWindow'
import { EDAPanel } from '../../components/EDAPanel'
import { MLStatusCard } from '../../components/MLStatusCard'
import { XAIPanel } from '../../components/XAIPanel'
import { useAnalysis } from '../../lib/hooks/useAnalysis'
import { Dataset } from '../../lib/types'

export default function ChatPage() {
  const params = useParams()
  const sessionId = params.sessionId as string

  const [dataset, setDataset] = useState<Dataset | null>(null)

  const {
    messages,
    isConnected,
    isTyping,
    currentIntent,
    results,
    sendMessage,
  } = useAnalysis(sessionId)

  // Load dataset from session storage or API
  useEffect(() => {
    const loadSessionData = async () => {
      try {
        const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/session/${sessionId}`)
        if (response.ok) {
          const sessionData = await response.json()
          if (sessionData.dataset) {
            setDataset(sessionData.dataset)
          }
        }
      } catch (error) {
        console.error('Failed to load session data:', error)
      }
    }

    if (sessionId) {
      loadSessionData()
    }
  }, [sessionId])

  return (
    <AppShell>
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 h-full">
        <div className="lg:col-span-2 flex flex-col">
          <div className="mb-6">
            <h2 className="text-xl font-medium text-dv-text">
              {dataset ? `Dataset: ${dataset.filename}` : 'Loading session...'}
            </h2>
          </div>

          <div className="flex-1 bg-dv-surface border border-dv-border rounded-lg overflow-hidden">
            <ChatWindow
              messages={messages}
              isTyping={isTyping}
              onSendMessage={sendMessage}
              disabled={!isConnected}
            />
          </div>
        </div>

        <div className="space-y-6 overflow-y-auto">
          {results.eda && <EDAPanel results={results.eda} />}
          {results.ml && <MLStatusCard results={results.ml} />}
          {results.xai && <XAIPanel results={results.xai} />}
        </div>
      </div>
    </AppShell>
  )
}