import { useState, useRef, useEffect } from 'react'
import { Send } from 'lucide-react'

interface ChatInputProps {
  onSendMessage: (message: string) => void
  disabled?: boolean
  placeholder?: string
}

export function ChatInput({ onSendMessage, disabled = false, placeholder = "Ask about your data..." }: ChatInputProps) {
  const [message, setMessage] = useState('')
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (message.trim() && !disabled) {
      onSendMessage(message.trim())
      setMessage('')
      adjustTextareaHeight()
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSubmit(e)
    }
  }

  const adjustTextareaHeight = () => {
    const textarea = textareaRef.current
    if (textarea) {
      textarea.style.height = 'auto'
      textarea.style.height = `${Math.min(textarea.scrollHeight, 120)}px`
    }
  }

  useEffect(() => {
    adjustTextareaHeight()
  }, [message])

  return (
    <form onSubmit={handleSubmit} className="border-t border-dv-border bg-dv-surface p-4">
      <div className="flex gap-3 items-end">
        <div className="flex-1 relative">
          <textarea
            ref={textareaRef}
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={placeholder}
            disabled={disabled}
            className="w-full resize-none rounded-lg border border-dv-border bg-dv-bg px-3 py-2 text-sm text-dv-text placeholder-dv-text-secondary focus:border-dv-accent focus:outline-none disabled:opacity-50 disabled:cursor-not-allowed"
            rows={1}
            style={{ minHeight: '40px', maxHeight: '120px' }}
          />
        </div>
        <button
          type="submit"
          disabled={!message.trim() || disabled}
          className="flex-shrink-0 w-10 h-10 bg-dv-accent text-dv-accent-foreground rounded-lg flex items-center justify-center hover:bg-dv-accent/90 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
        >
          <Send size={18} />
        </button>
      </div>
    </form>
  )
}