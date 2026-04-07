'use client'

import { useState } from 'react'
import { AppShell } from '../components/AppShell'
import { DropZone } from '../components/DropZone'
import { ColumnChips } from '../components/ColumnChips'
import { ChatWindow } from '../components/ChatWindow'
import { EDAPanel } from '../components/EDAPanel'
import { MLStatusCard } from '../components/MLStatusCard'
import { XAIPanel } from '../components/XAIPanel'
import { CommandPalette } from '../components/CommandPalette'
import { QuickActions } from '../components/QuickActions'
import { useAnalysis } from '../lib/hooks/useAnalysis'
import { Dataset } from '../lib/types'
import { useRouter } from 'next/navigation'

export default function Home() {
  const [dataset, setDataset] = useState<Dataset | null>(null)
  const [selectedColumns, setSelectedColumns] = useState<string[]>([])
  const [sessionId, setSessionId] = useState<string>('')
  const [isCommandPaletteOpen, setIsCommandPaletteOpen] = useState(false)
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

  const handleQuickAction = (action: string) => {
    const actionMessages: Record<string, string> = {
      eda: 'Generate an exploratory data analysis report',
      insights: 'What are the key insights from this data?',
      predict: 'Build a predictive model for the main target variable',
      profile: 'Show a quick data profile and summary statistics',
    }
    
    if (actionMessages[action]) {
      sendMessage(actionMessages[action])
    }
  }

  // Handle keyboard shortcut for command palette
  React.useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault()
        setIsCommandPaletteOpen(!isCommandPaletteOpen)
      }
    }
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [isCommandPaletteOpen])

  if (!dataset) {
    return (
      <AppShell>
        <CommandPalette 
          isOpen={isCommandPaletteOpen}
          onClose={() => setIsCommandPaletteOpen(false)}
        />
        <div className="max-w-4xl mx-auto py-12">
          <div className="text-center mb-12">
            <h1 className="text-5xl font-bold text-dv-text mb-4">
              Welcome to <span className="bg-gradient-to-r from-dv-accent to-purple-600 bg-clip-text text-transparent">DataVerse AI</span>
            </h1>
            <p className="text-lg text-dv-text-secondary max-w-2xl mx-auto">
              Transform your data into intelligence with AI-powered insights, visualizations, and predictive analytics.
            </p>
          </div>
          
          <div className="mb-12">
            <DropZone sessionId="" onDatasetUploaded={handleDatasetUploaded} />
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">
            <div className="p-6 rounded-lg bg-dv-bg border border-dv-border hover:border-dv-accent transition-colors">
              <div className="text-2xl mb-2">📊</div>
              <h3 className="font-semibold text-dv-text mb-2">Advanced Analytics</h3>
              <p className="text-sm text-dv-text-secondary">Get instant insights with AI-powered analysis</p>
            </div>
            <div className="p-6 rounded-lg bg-dv-bg border border-dv-border hover:border-dv-accent transition-colors">
              <div className="text-2xl mb-2">🤖</div>
              <h3 className="font-semibold text-dv-text mb-2">ML Models</h3>
              <p className="text-sm text-dv-text-secondary">Build and train predictive models instantly</p>
            </div>
            <div className="p-6 rounded-lg bg-dv-bg border border-dv-border hover:border-dv-accent transition-colors">
              <div className="text-2xl mb-2">🔍</div>
              <h3 className="font-semibold text-dv-text mb-2">Explainability</h3>
              <p className="text-sm text-dv-text-secondary">Understand your data with SHAP & LIME</p>
            </div>
          </div>

          <div className="text-center text-sm text-dv-text-secondary">
            <p>Press <kbd className="px-2 py-1 bg-dv-bg border border-dv-border rounded text-dv-text">⌘K</kbd> to view all commands</p>
          </div>
        </div>
      </AppShell>
    )
  }

  return (
    <AppShell>
      <CommandPalette 
        isOpen={isCommandPaletteOpen}
        onClose={() => setIsCommandPaletteOpen(false)}
      />
      
      <div className="flex flex-col h-screen">
        {/* Header */}
        <div className="border-b border-dv-border bg-dv-bg p-4">
          <div className="max-w-7xl mx-auto">
            <h2 className="text-lg font-semibold text-dv-text mb-2">
              📁 {dataset.filename}
            </h2>
            <ColumnChips
              dataset={dataset}
              selectedColumns={selectedColumns}
              onColumnToggle={handleColumnToggle}
            />
          </div>
        </div>

        {/* Quick Actions */}
        {messages.length === 0 && (
          <QuickActions onAction={handleQuickAction} />
        )}

        {/* Main Content */}
        <div className="flex-1 overflow-hidden">
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-0 h-full">
            {/* Chat Area */}
            <div className="lg:col-span-2 flex flex-col border-r border-dv-border">
              <ChatWindow
                messages={messages}
                isTyping={isTyping}
                onSendMessage={sendMessage}
                disabled={!isConnected}
              />
            </div>

            {/* Results Panel */}
            <div className="hidden lg:flex lg:flex-col overflow-y-auto bg-dv-bg-secondary">
              <div className="p-4 border-b border-dv-border">
                <h3 className="font-semibold text-dv-text text-sm">Analysis Results</h3>
              </div>
              <div className="flex-1 overflow-y-auto p-4 space-y-4">
                {results.eda && <EDAPanel results={results.eda} />}
                {results.ml && <MLStatusCard results={results.ml} />}
                {results.xai && <XAIPanel results={results.xai} />}
                {!results.eda && !results.ml && !results.xai && (
                  <div className="p-4 text-center text-dv-text-secondary text-sm">
                    <p>Results will appear here</p>
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      </div>
    </AppShell>
  )
}