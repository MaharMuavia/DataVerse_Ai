import { User, Bot } from 'lucide-react'
import { Message } from '../lib/types'

interface MessageBubbleProps {
  message: Message
}

export function MessageBubble({ message }: MessageBubbleProps) {
  const isUser = message.role === 'user'

  return (
    <div className={`flex gap-3 ${isUser ? 'justify-end' : 'justify-start'}`}>
      {!isUser && (
        <div className="flex-shrink-0 w-8 h-8 bg-dv-accent rounded-full flex items-center justify-center">
          <Bot size={16} className="text-dv-accent-foreground" />
        </div>
      )}

      <div className={`max-w-[70%] ${isUser ? 'order-first' : ''}`}>
        <div
          className={`rounded-lg px-4 py-2 ${
            isUser
              ? 'bg-dv-accent text-dv-accent-foreground'
              : 'bg-dv-surface border border-dv-border'
          }`}
        >
          <p className="text-sm whitespace-pre-wrap">{message.content}</p>
        </div>
        <p className="text-xs text-dv-text-secondary mt-1 px-1">
          {message.timestamp.toLocaleTimeString()}
        </p>
      </div>

      {isUser && (
        <div className="flex-shrink-0 w-8 h-8 bg-dv-surface border border-dv-border rounded-full flex items-center justify-center">
          <User size={16} className="text-dv-text" />
        </div>
      )}
    </div>
  )
}
