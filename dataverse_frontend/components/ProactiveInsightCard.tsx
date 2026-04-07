'use client'

import { ArrowRight, Lightbulb, LineChart, Sparkles } from 'lucide-react'
import { ProactiveInsight } from '@/types'

interface ProactiveInsightCardProps {
  insight: ProactiveInsight
  onRun: (query: string) => void
}

function InsightIcon({ icon }: { icon?: string }) {
  if (icon === 'trend') {
    return <LineChart className="h-5 w-5" />
  }

  if (icon === 'sparkles') {
    return <Sparkles className="h-5 w-5" />
  }

  return <Lightbulb className="h-5 w-5" />
}

export function ProactiveInsightCard({ insight, onRun }: ProactiveInsightCardProps) {
  const suggestedQuery = insight.follow_up_query || insight.title

  return (
    <button
      type="button"
      onClick={() => onRun(suggestedQuery)}
      className="group rounded-2xl border border-slate-200 bg-white p-4 text-left shadow-sm transition hover:-translate-y-0.5 hover:border-primary-200 hover:shadow-md"
    >
      <div className="flex items-start justify-between gap-3">
        <div className="rounded-2xl bg-primary-50 p-3 text-primary-700">
          <InsightIcon icon={insight.icon} />
        </div>
        <ArrowRight className="h-4 w-4 text-slate-400 transition group-hover:translate-x-0.5 group-hover:text-primary-600" />
      </div>

      <div className="mt-4">
        <h3 className="text-sm font-semibold text-slate-900">{insight.title}</h3>
        <p className="mt-2 text-sm leading-6 text-slate-600">{insight.description}</p>
      </div>

      <div className="mt-4 text-xs font-medium uppercase tracking-[0.18em] text-slate-400">
        Ask follow-up
      </div>
    </button>
  )
}
