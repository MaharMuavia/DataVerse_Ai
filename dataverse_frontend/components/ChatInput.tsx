import { useState, useRef, useEffect } from 'react'
import { Send, Command, Paperclip } from 'lucide-react'

interface ChatInputProps {
  onSendMessage: (message: string) => void
  disabled?: boolean
  placeholder?: string
}

export function ChatInput({ onSendMessage, disabled = false, placeholder = "Ask about your data... (⌘K for commands)" }: ChatInputProps) {
  const [message, setMessage] = useState('')
  const [showSuggestions, setShowSuggestions] = useState(false)
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  const suggestions = [
    "Analyze sales trends",
    "Find anomalies in the data",
    "Compare top products",
    "Generate a report",
    "Predict future values"
  ]

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (message.trim() && !disabled) {
      onSendMessage(message.trim())
      setMessage('')
      setShowSuggestions(false)
      adjustTextareaHeight()
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSubmit(e)
    }
    if (e.key === 'k' && (e.metaKey || e.ctrlKey)) {
      e.preventDefault()
      setShowSuggestions(!showSuggestions)
    }
  }

  const adjustTextareaHeight = () => {
    const textarea = textareaRef.current
    if (textarea) {
      textarea.style.height = 'auto'
      textarea.style.height = `${Math.min(textarea.scrollHeight, 120)}px`
    }
  }

  const handleSuggestionClick = (suggestion: string) => {
    setMessage(suggestion)
    setShowSuggestions(false)
  }

  useEffect(() => {
    adjustTextareaHeight()
  }, [message])

  return (
    <div className="px-4 pb-4">
      {showSuggestions && (
        <div className="mb-3 space-y-2">
          <p className="text-xs font-semibold text-dv-text-secondary uppercase tracking-wide">Suggestions</p>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
            {suggestions.map((suggestion, idx) => (
              <button
                key={idx}
                onClick={() => handleSuggestionClick(suggestion)}
                className="text-left p-3 rounded-lg bg-dv-bg border border-dv-border hover:border-dv-accent hover:bg-dv-accent/5 transition-all text-sm text-dv-text hover:text-dv-accent"
              >
                <Sparkles className="inline w-4 h-4 mr-2 text-dv-accent" />
                {suggestion}
              </button>
            ))}
          </div>
        </div>
      )}

      <form onSubmit={handleSubmit} className="relative">
        <div className="flex gap-2 items-end">
          <button
            type="button"
            className="flex-shrink-0 w-10 h-10 rounded-lg border border-dv-border text-dv-text-secondary hover:text-dv-text hover:border-dv-accent hover:bg-dv-accent/5 transition-all flex items-center justify-center"
            title="Attach file"
          >
            <Paperclip size={18} />
          </button>

          <div className="flex-1 relative bg-dv-bg rounded-lg border border-dv-border focus-within:border-dv-accent focus-within:shadow-lg focus-within:shadow-dv-accent/10 transition-all">
            <textarea
              ref={textareaRef}
              value={message}
              onChange={(e) => setMessage(e.target.value)}
              onKeyDown={handleKeyDown}
              onFocus={() => message === '' && setShowSuggestions(true)}
              placeholder={placeholder}
              disabled={disabled}
              className="w-full resize-none bg-transparent px-4 py-3 text-sm text-dv-text placeholder-dv-text-secondary focus:outline-none disabled:opacity-50 disabled:cursor-not-allowed"
              rows={1}
              style={{ minHeight: '44px', maxHeight: '120px' }}
            />
            <div className="absolute right-3 bottom-3 flex items-center gap-1 text-xs text-dv-text-secondary">
              <Command size={14} />
              <span>K</span>
            </div>
          </div>

          <button
            type="submit"
            disabled={!message.trim() || disabled}
            className="flex-shrink-0 w-10 h-10 bg-dv-accent text-white rounded-lg flex items-center justify-center hover:bg-dv-accent-hover hover:shadow-lg hover:shadow-dv-accent/30 transition-all disabled:opacity-50 disabled:cursor-not-allowed font-semibold"
            title="Send message"
          >
            <Send size={18} />
          </button>
        </div>
      </form>

      <p className="text-xs text-dv-text-secondary mt-2 text-center">
        Shift + Enter for new line
      </p>
    </div>
  )
}

import { Sparkles } from 'lucide-react'