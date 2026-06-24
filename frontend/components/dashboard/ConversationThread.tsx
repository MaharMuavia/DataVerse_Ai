'use client';

import { useEffect, useRef } from 'react';
import ReactMarkdown from 'react-markdown';
import { formatCell } from '@/lib/dashboard-format';

type ThreadMessage = {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  kpis?: { label: string; value: string | number | null }[];
};

export function ConversationThread({ messages }: { messages: ThreadMessage[] }) {
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
  }, [messages.length]);

  if (messages.length === 0) return null;

  return (
    <div className="space-y-2.5 max-h-[38vh] overflow-y-auto custom-scrollbar pr-1">
      <h3 className="text-xs font-semibold text-[#64748B] uppercase tracking-wider">Conversation</h3>
      {messages.map((message) =>
        message.role === 'user' ? (
          <div key={message.id} className="flex justify-end">
            <div className="max-w-[80%] rounded-2xl rounded-br-sm bg-violet-500 px-3.5 py-2 text-sm text-white">
              {message.content}
            </div>
          </div>
        ) : (
          <div key={message.id} className="flex justify-start">
            <div className="max-w-[85%] rounded-2xl rounded-bl-sm border border-[#E2E8F0] bg-white px-3.5 py-2 text-sm text-[#334155]">
              <div className="dv-markdown">
                <ReactMarkdown>{message.content}</ReactMarkdown>
              </div>
              {message.kpis && message.kpis.length > 0 && (
                <div className="mt-2 flex flex-wrap gap-1.5">
                  {message.kpis.slice(0, 4).map((kpi, i) => (
                    <span key={i} className="rounded-md border border-[#E2E8F0] bg-[#F8FAFC] px-2 py-0.5 text-[11px]">
                      <span className="text-[#64748B]">{kpi.label}: </span>
                      <span className="font-semibold text-[#0F172A]">{formatCell(kpi.value)}</span>
                    </span>
                  ))}
                </div>
              )}
            </div>
          </div>
        ),
      )}
      <div ref={endRef} />
    </div>
  );
}
