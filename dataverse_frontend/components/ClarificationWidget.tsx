'use client'

import { useState } from 'react'
import { HelpCircle, Send } from 'lucide-react'
import { ClarificationRequest } from '@/types'

interface ClarificationWidgetProps {
  clarification: ClarificationRequest
  disabled?: boolean
  onRespond: (answer: string) => void
}

export function ClarificationWidget({
  clarification,
  disabled = false,
  onRespond,
}: ClarificationWidgetProps) {
  const [answer, setAnswer] = useState('')

  return (
    <div className="rounded-2xl border border-amber-200 bg-amber-50 p-4 shadow-sm">
      <div className="mb-3 flex items-start gap-3">
        <div className="rounded-full bg-amber-100 p-2 text-amber-700">
          <HelpCircle className="h-4 w-4" />
        </div>
        <div>
          <h3 className="text-sm font-semibold text-amber-950">Clarification needed</h3>
          <p className="mt-1 text-sm text-amber-900">{clarification.question}</p>
        </div>
      </div>

      {clarification.options && clarification.options.length > 0 ? (
        <div className="flex flex-wrap gap-2">
          {clarification.options.map((option) => (
            <button
              key={option}
              type="button"
              onClick={() => onRespond(option)}
              disabled={disabled}
              className="rounded-full border border-amber-300 bg-white px-3 py-1.5 text-sm text-amber-950 transition hover:border-amber-400 hover:bg-amber-100 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {option}
            </button>
          ))}
        </div>
      ) : (
        <div className="flex gap-2">
          <input
            type="text"
            value={answer}
            onChange={(event) => setAnswer(event.target.value)}
            placeholder="Type your answer..."
            disabled={disabled}
            className="flex-1 rounded-xl border border-amber-200 bg-white px-3 py-2 text-sm text-slate-900 outline-none transition focus:border-amber-400"
          />
          <button
            type="button"
            onClick={() => {
              if (!answer.trim()) return
              onRespond(answer.trim())
              setAnswer('')
            }}
            disabled={disabled || !answer.trim()}
            className="inline-flex items-center gap-2 rounded-xl bg-amber-500 px-3 py-2 text-sm font-medium text-white transition hover:bg-amber-600 disabled:cursor-not-allowed disabled:opacity-50"
          >
            <Send className="h-4 w-4" />
            Reply
          </button>
        </div>
      )}
    </div>
  )
}
