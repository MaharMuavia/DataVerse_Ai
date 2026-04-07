import { useEffect, useRef } from 'react'
import { MessageBubble } from './MessageBubble'
import { TypingIndicator } from './TypingIndicator'
import { ChatInput } from './ChatInput'
import { Message } from '../lib/types'
import { Sparkles } from 'lucide-react'

interface ChatWindowProps {
  messages: Message[]
  isTyping: boolean
  onSendMessage: (message: string) => void
  disabled?: boolean
}

export function ChatWindow({ messages, isTyping, onSendMessage, disabled }: ChatWindowProps) {
  const messagesEndRef = useRef<HTMLDivElement>(null)

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages, isTyping])

  return (
    <div className="flex flex-col h-full bg-gradient-to-b from-dv-bg to-dv-bg-secondary">
      {/* Chat Messages Area */}
      <div className="flex-1 overflow-y-auto p-6 space-y-4">
        {messages.length === 0 && !isTyping && (
          <div className="flex items-center justify-center h-full">
            <div className="text-center max-w-md mx-auto">
              <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-dv-accent/10 mb-4">
                <Sparkles className="text-dv-accent" size={32} />
              </div>
              <h3 className="text-2xl font-semibold text-dv-text mb-2">
                Welcome to DataVerse AI
              </h3>
              <p className="text-dv-text-secondary mb-6">
                Upload a dataset and ask natural language questions to unlock insights powered by AI.
              </p>
              <div className="grid grid-cols-2 gap-3">
                <div className="p-3 rounded-lg bg-dv-bg border border-dv-border">
                  <p className="text-xs font-semibold text-dv-text mb-1">📊 Analyze</p>
                  <p className="text-xs text-dv-text-secondary">Get instant insights</p>
                </div>
                <div className="p-3 rounded-lg bg-dv-bg border border-dv-border">
                  <p className="text-xs font-semibold text-dv-text mb-1">🤖 AI-Powered</p>
                  <p className="text-xs text-dv-text-secondary">Smart interpretation</p>
                </div>
                <div className="p-3 rounded-lg bg-dv-bg border border-dv-border">
                  <p className="text-xs font-semibold text-dv-text mb-1">📈 Visualize</p>
                  <p className="text-xs text-dv-text-secondary">Interactive charts</p>
                </div>
                <div className="p-3 rounded-lg bg-dv-bg border border-dv-border">
                  <p className="text-xs font-semibold text-dv-text mb-1">🔍 Explore</p>
                  <p className="text-xs text-dv-text-secondary">Deep dive analysis</p>
                </div>
              </div>
            </div>
          </div>
        )}

        {messages.map((message, index) => (
          <div key={message.id} className="animate-fade-up">
            <MessageBubble message={message} />
          </div>
        ))}

        {isTyping && (
          <div className="flex justify-start">
            <TypingIndicator />
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Chat Input Area */}
      <div className="border-t border-dv-border p-4 bg-dv-bg">
        <ChatInput
          onSendMessage={onSendMessage}
          disabled={disabled}
        />
      </div>
    </div>
  )
}