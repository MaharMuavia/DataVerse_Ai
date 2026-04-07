import { useEffect, useRef } from 'react'
import { MessageBubble } from './MessageBubble'
import { TypingIndicator } from './TypingIndicator'
import { ChatInput } from './ChatInput'
import { Message } from '../lib/types'

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
    <div className="flex flex-col h-full">
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.length === 0 && !isTyping && (
          <div className="flex items-center justify-center h-full">
            <div className="text-center">
              <h3 className="text-lg font-medium text-dv-text mb-2">
                Welcome to DataVerse AI
              </h3>
              <p className="text-dv-text-secondary">
                Upload a dataset and start asking questions about your data
              </p>
            </div>
          </div>
        )}

        {messages.map((message) => (
          <MessageBubble key={message.id} message={message} />
        ))}

        {isTyping && <TypingIndicator />}

        <div ref={messagesEndRef} />
      </div>

      <ChatInput
        onSendMessage={onSendMessage}
        disabled={disabled}
      />
    </div>
  )
}