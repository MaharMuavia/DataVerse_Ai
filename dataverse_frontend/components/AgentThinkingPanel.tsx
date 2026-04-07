'use client'

import { AlertCircle, CheckCircle2, Loader2, Sparkles } from 'lucide-react'

export interface ThinkingStep {
  key: string
  label: string
  detail?: string
  status: 'idle' | 'active' | 'done' | 'error'
}

interface AgentThinkingPanelProps {
  steps: ThinkingStep[]
}

function StatusIcon({ status }: { status: ThinkingStep['status'] }) {
  if (status === 'done') {
    return <CheckCircle2 className="h-4 w-4 text-emerald-500" />
  }

  if (status === 'error') {
    return <AlertCircle className="h-4 w-4 text-rose-500" />
  }

  if (status === 'active') {
    return <Loader2 className="h-4 w-4 animate-spin text-primary-600" />
  }

  return <Sparkles className="h-4 w-4 text-slate-400" />
}

export function AgentThinkingPanel({ steps }: AgentThinkingPanelProps) {
  return (
    <div className="rounded-2xl border border-slate-200 bg-slate-50/90 p-4 shadow-sm">
      <div className="mb-3 flex items-center gap-2">
        <div className="rounded-full bg-primary-100 p-2 text-primary-700">
          <Sparkles className="h-4 w-4" />
        </div>
        <div>
          <h3 className="text-sm font-semibold text-slate-900">Agent activity</h3>
          <p className="text-xs text-slate-500">Live plan, analysis, and synthesis updates</p>
        </div>
      </div>

      <div className="space-y-2">
        {steps.map((step) => (
          <div
            key={step.key}
            className={`rounded-xl border px-3 py-2 transition ${
              step.status === 'active'
                ? 'border-primary-200 bg-white shadow-sm'
                : 'border-transparent bg-white/70'
            }`}
          >
            <div className="flex items-start gap-3">
              <div className="mt-0.5">
                <StatusIcon status={step.status} />
              </div>
              <div className="min-w-0">
                <div className="text-sm font-medium text-slate-800">{step.label}</div>
                {step.detail && (
                  <div className="mt-1 text-xs leading-5 text-slate-500">{step.detail}</div>
                )}
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
