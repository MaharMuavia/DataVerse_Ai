'use client'

import { useEffect, useMemo, useRef, useState } from 'react'
import { Database, Loader2, Send, Sparkles } from 'lucide-react'
import { DatasetUploader } from './DatasetUploader'
import { MessageBubble } from './MessageBubble'
import { AgentThinkingPanel, ThinkingStep } from './AgentThinkingPanel'
import { ClarificationWidget } from './ClarificationWidget'
import { FilterBadgeStrip } from './FilterBadgeStrip'
import { ProactiveInsightCard } from './ProactiveInsightCard'
import { useAppStore } from '@/store/appStore'
import {
  clearActiveFilters,
  createStream,
  getProactiveInsights,
  processAgentQuery,
} from '@/lib/api'
import { Message, Session, StreamEvent } from '@/types'

const THINKING_ORDER = ['intent_parsed', 'analysis_running', 'visualization_ready', 'narration', 'complete']

const THINKING_LABELS: Record<string, string> = {
  intent_parsed: 'Interpret the question',
  analysis_running: 'Run the analysis plan',
  visualization_ready: 'Prepare visual evidence',
  narration: 'Write the response',
  complete: 'Finalize the answer',
}

function buildDefaultThinkingSteps(): ThinkingStep[] {
  return THINKING_ORDER.map((key) => ({
    key,
    label: THINKING_LABELS[key],
    detail: undefined,
    status: 'idle',
  }))
}

function normalizeStreamStep(step: string): string {
  if (step === 'analysis_complete' || step === 'clarification_needed') {
    return 'analysis_running'
  }

  if (step === 'error' || step === 'heartbeat') {
    return step
  }

  return THINKING_ORDER.includes(step) ? step : 'analysis_running'
}

export function ChatInterface() {
  const [query, setQuery] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [thinkingSteps, setThinkingSteps] = useState<ThinkingStep[]>(buildDefaultThinkingSteps())
  const messagesEndRef = useRef<HTMLDivElement>(null)

  const {
    session,
    messages,
    isStreaming,
    activeFilters,
    proactiveInsights,
    pendingClarification,
    setSession,
    addMessage,
    setStreaming,
    setActiveFilters,
    setProactiveInsights,
    setPendingClarification,
    clearMessages,
  } = useAppStore()

  const hasConversation = useMemo(
    () => messages.some((message) => message.type === 'assistant' || message.type === 'user'),
    [messages]
  )

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages, pendingClarification])

  const resetThinkingSteps = () => {
    setThinkingSteps(buildDefaultThinkingSteps())
  }

  const advanceThinkingStep = (
    rawStep: string,
    detail: string,
    forceStatus?: ThinkingStep['status']
  ) => {
    const step = normalizeStreamStep(rawStep)
    if (!THINKING_ORDER.includes(step)) {
      if (rawStep === 'error') {
        setThinkingSteps((current) =>
          current.map((item, index) =>
            index === current.findIndex((candidate) => candidate.status === 'active')
              ? { ...item, status: 'error', detail }
              : item
          )
        )
      }
      return
    }

    const targetIndex = THINKING_ORDER.indexOf(step)
    setThinkingSteps((current) =>
      current.map((item, index) => {
        if (index < targetIndex) {
          return item.status === 'error' ? item : { ...item, status: 'done' }
        }

        if (index === targetIndex) {
          return {
            ...item,
            detail,
            status: forceStatus || (step === 'complete' ? 'done' : 'active'),
          }
        }

        return forceStatus === 'done' && step === 'complete'
          ? { ...item, status: 'done' }
          : { ...item, status: 'idle' }
      })
    )
  }

  const loadProactiveInsights = async (newSession: Session) => {
    try {
      const insights = await getProactiveInsights(newSession.id)
      setProactiveInsights(insights)
    } catch (error) {
      console.warn('Unable to load proactive insights:', error)
      setProactiveInsights([])
    }
  }

  const handleUploadSuccess = async (newSession: Session) => {
    setSession(newSession)
    clearMessages()
    setActiveFilters([])
    setPendingClarification(null)
    resetThinkingSteps()

    addMessage({
      id: `welcome-${Date.now()}`,
      type: 'assistant',
      content:
        newSession.message ||
        `Dataset "${newSession.dataset_filename}" uploaded successfully. Ask a question to begin exploring it.`,
      timestamp: new Date(),
    })

    await loadProactiveInsights(newSession)
  }

  const runQuery = async (nextQuery: string) => {
    if (!nextQuery.trim() || !session || isLoading) {
      return
    }

    const userMessage: Message = {
      id: `user-${Date.now()}`,
      type: 'user',
      content: nextQuery,
      timestamp: new Date(),
    }

    addMessage(userMessage)
    setQuery('')
    setIsLoading(true)
    setStreaming(true)
    setPendingClarification(null)
    resetThinkingSteps()

    let eventSource: EventSource | null = null

    try {
      eventSource = createStream(session.id, nextQuery, (event: StreamEvent) => {
        if (event.step === 'heartbeat') {
          return
        }

        if (event.step === 'error') {
          advanceThinkingStep('error', event.message, 'error')
          return
        }

        if (event.step === 'complete') {
          advanceThinkingStep('complete', event.message, 'done')
          return
        }

        if (event.step === 'analysis_complete') {
          advanceThinkingStep('analysis_complete', event.message, 'done')
          return
        }

        advanceThinkingStep(event.step, event.message)
      })

      const result = await processAgentQuery(session.id, nextQuery)

      addMessage({
        id: `assistant-${Date.now()}`,
        type: 'assistant',
        content: result.narrative,
        timestamp: new Date(),
        chartSpec: result.charts?.[0],
        tables: result.tables,
        narration: result.explanation,
        clarification: result.clarification || null,
      })

      setActiveFilters(result.active_filters || [])
      setPendingClarification(result.clarification || null)
      advanceThinkingStep('complete', 'Agent response ready.', 'done')
    } catch (error) {
      advanceThinkingStep('error', error instanceof Error ? error.message : 'Unknown error', 'error')
      addMessage({
        id: `error-${Date.now()}`,
        type: 'assistant',
        content: `Failed to process query: ${error instanceof Error ? error.message : 'Unknown error'}`,
        timestamp: new Date(),
      })
    } finally {
      setIsLoading(false)
      setStreaming(false)
      if (eventSource) {
        eventSource.close()
      }
    }
  }

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault()
    await runQuery(query)
  }

  const handleClearFilters = async () => {
    if (!session) return

    try {
      await clearActiveFilters(session.id)
      setActiveFilters([])
      addMessage({
        id: `filters-cleared-${Date.now()}`,
        type: 'assistant',
        content: 'Active filters cleared. Future analysis will use the original uploaded dataset.',
        timestamp: new Date(),
      })
    } catch (error) {
      addMessage({
        id: `filters-error-${Date.now()}`,
        type: 'assistant',
        content: `Failed to clear filters: ${error instanceof Error ? error.message : 'Unknown error'}`,
        timestamp: new Date(),
      })
    }
  }

  if (!session) {
    return (
      <div className="flex min-h-[60vh] flex-col items-center justify-center">
        <div className="mb-8 text-center">
          <h2 className="text-2xl font-semibold text-gray-900">Get started with your data</h2>
          <p className="mt-2 text-gray-600">
            Upload a CSV file to begin analyzing your data with AI
          </p>
        </div>
        <DatasetUploader onUploadSuccess={handleUploadSuccess} />
      </div>
    )
  }

  return (
    <div className="grid gap-4 lg:grid-cols-[minmax(0,1.45fr)_360px]">
      <div className="flex min-h-[80vh] flex-col overflow-hidden rounded-3xl border border-slate-200 bg-white shadow-lg">
        <div className="border-b border-slate-200 bg-slate-50 px-5 py-4">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div className="flex items-start gap-3">
              <div className="rounded-2xl bg-primary-50 p-3 text-primary-700">
                <Database className="h-5 w-5" />
              </div>
              <div>
                <h3 className="font-semibold text-slate-900">{session.dataset_filename}</h3>
                <p className="text-sm text-slate-500">
                  {session.dataset_rows} rows x {session.dataset_cols} columns
                </p>
              </div>
            </div>
            <button
              onClick={() => {
                setSession(null)
                clearMessages()
                resetThinkingSteps()
              }}
              className="rounded-full border border-slate-200 px-3 py-1.5 text-sm text-slate-600 transition hover:border-slate-300 hover:bg-slate-50"
            >
              Change dataset
            </button>
          </div>
        </div>

        <div className="border-b border-slate-100 px-4 py-3">
          <FilterBadgeStrip filters={activeFilters} onClearAll={handleClearFilters} />
        </div>

        <div className="flex-1 overflow-y-auto px-4 py-4">
          <div className="space-y-4">
            {messages.map((message) => (
              <MessageBubble key={message.id} message={message} />
            ))}

            {pendingClarification && (
              <ClarificationWidget
                clarification={pendingClarification}
                disabled={isLoading || isStreaming}
                onRespond={runQuery}
              />
            )}

            {(isStreaming || isLoading) && (
              <div className="flex items-center gap-2 text-sm text-slate-500">
                <Loader2 className="h-4 w-4 animate-spin" />
                Agent is working on your request...
              </div>
            )}

            <div ref={messagesEndRef} />
          </div>
        </div>

        <div className="border-t border-slate-200 p-4">
          <form onSubmit={handleSubmit} className="flex gap-2">
            <input
              type="text"
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="Ask a question about your data..."
              className="flex-1 rounded-2xl border border-slate-300 px-4 py-3 text-sm text-slate-900 outline-none transition focus:border-primary-400"
              disabled={isLoading || isStreaming}
            />
            <button
              type="submit"
              disabled={!query.trim() || isLoading || isStreaming}
              className="inline-flex items-center gap-2 rounded-2xl bg-primary-600 px-4 py-3 text-sm font-medium text-white transition hover:bg-primary-700 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {isLoading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
              Send
            </button>
          </form>
        </div>
      </div>

      <div className="space-y-4">
        <AgentThinkingPanel steps={thinkingSteps} />

        <div className="rounded-3xl border border-slate-200 bg-white p-4 shadow-sm">
          <div className="mb-3 flex items-center gap-2">
            <div className="rounded-full bg-amber-100 p-2 text-amber-700">
              <Sparkles className="h-4 w-4" />
            </div>
            <div>
              <h3 className="text-sm font-semibold text-slate-900">Proactive suggestions</h3>
              <p className="text-xs text-slate-500">Start from automatically suggested follow-up paths.</p>
            </div>
          </div>

          {proactiveInsights.length > 0 ? (
            <div className="space-y-3">
              {proactiveInsights.map((insight, index) => (
                <ProactiveInsightCard
                  key={`${insight.title}-${index}`}
                  insight={insight}
                  onRun={(suggestedQuery) => {
                    setQuery(suggestedQuery)
                    void runQuery(suggestedQuery)
                  }}
                />
              ))}
            </div>
          ) : (
            <div className="rounded-2xl bg-slate-50 px-4 py-5 text-sm text-slate-500">
              {hasConversation
                ? 'Suggestions will refresh as you keep exploring the dataset.'
                : 'Upload analysis hints appear here when proactive scanning succeeds.'}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
