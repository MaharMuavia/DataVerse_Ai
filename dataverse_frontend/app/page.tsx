'use client'

import { useState } from 'react'
import { AppShell } from '../components/AppShell'
import { DropZone } from '../components/DropZone'
import { ColumnChips } from '../components/ColumnChips'
import { ChatWindow } from '../components/ChatWindow'
import { EDAPanel } from '../components/EDAPanel'
import { MLStatusCard } from '../components/MLStatusCard'
import { XAIPanel } from '../components/XAIPanel'
import { useAnalysis } from '../lib/hooks/useAnalysis'
import { Dataset } from '../lib/types'
import { useRouter } from 'next/navigation'

export default function Home() {
  const [dataset, setDataset] = useState<Dataset | null>(null)
  const [selectedColumns, setSelectedColumns] = useState<string[]>([])
  const [sessionId, setSessionId] = useState<string>('')
  const router = useRouter()

  const {
    messages,
    isConnected,
    isTyping,
    currentIntent,
    results,
    sendMessage,
  } = useAnalysis(sessionId)

  const handleDatasetUploaded = (uploadedDataset: Dataset) => {
    setDataset(uploadedDataset)
    setSelectedColumns(uploadedDataset.columnNames)
    const newSessionId = crypto.randomUUID()
    setSessionId(newSessionId)
    router.push(`/chat/${newSessionId}`)
  }

  const handleColumnToggle = (column: string) => {
    setSelectedColumns(prev =>
      prev.includes(column)
        ? prev.filter(c => c !== column)
        : [...prev, column]
    )
  }

  if (!dataset) {
    return (
      <AppShell>
        <div className="max-w-2xl mx-auto py-12">
          <div className="text-center mb-8">
            <h1 className="text-3xl font-bold text-dv-text mb-2">
              Welcome to DataVerse AI
            </h1>
            <p className="text-dv-text-secondary">
              Upload your dataset and start exploring insights with AI
            </p>
          </div>
          <DropZone sessionId="" onDatasetUploaded={handleDatasetUploaded} />
        </div>
      </AppShell>
    )
  }

  return (
    <AppShell>
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 h-full">
        <div className="lg:col-span-2 flex flex-col">
          <div className="mb-6">
            <h2 className="text-xl font-medium text-dv-text mb-4">
              Dataset: {dataset.filename}
            </h2>
            <ColumnChips
              dataset={dataset}
              selectedColumns={selectedColumns}
              onColumnToggle={handleColumnToggle}
            />
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