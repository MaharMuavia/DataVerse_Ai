import { Bot } from 'lucide-react'

export function TypingIndicator() {
  return (
    <div className="flex gap-3 justify-start">
      <div className="flex-shrink-0 w-8 h-8 bg-dv-accent rounded-full flex items-center justify-center">
        <Bot size={16} className="text-dv-accent-foreground" />
      </div>

      <div className="bg-dv-surface border border-dv-border rounded-lg px-4 py-2">
        <div className="flex items-center gap-1">
          <div className="flex gap-1">
            <div className="w-2 h-2 bg-dv-text-secondary rounded-full animate-bounce"></div>
            <div className="w-2 h-2 bg-dv-text-secondary rounded-full animate-bounce" style={{ animationDelay: '0.1s' }}></div>
            <div className="w-2 h-2 bg-dv-text-secondary rounded-full animate-bounce" style={{ animationDelay: '0.2s' }}></div>
          </div>
          <span className="text-sm text-dv-text-secondary ml-2">Analyzing...</span>
        </div>
      </div>
    </div>
  )
}