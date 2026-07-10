'use client';

import { useState } from 'react';
import { ArrowUp } from 'lucide-react';
import { GlassCard } from './GlassCard';

export function Composer({
  onSubmit,
  isQuerying,
  suggestedQuestions,
}: {
  onSubmit: (query: string) => void;
  isQuerying: boolean;
  suggestedQuestions: string[];
}) {
  const [value, setValue] = useState('');

  const send = (text: string) => {
    const trimmed = text.trim();
    if (!trimmed || isQuerying) return;
    onSubmit(trimmed);
    setValue('');
  };

  return (
    <div className="space-y-3">
      <h4 className="text-xs font-semibold text-[#64748B] uppercase tracking-wider">Ask AnalystAgent</h4>
      <GlassCard className="p-4 bg-white border-[#E2E8F0] flex items-center gap-3">
        <input
          type="text"
          value={value}
          onChange={(e) => setValue(e.target.value)}
          placeholder="Ask a question about this dataset (e.g. 'What are the top categories by sales?')..."
          className="flex-1 bg-[#F8FAFC] border border-[#E2E8F0] rounded-xl px-4 py-2.5 text-sm text-[#0F172A] focus:outline-none focus:ring-2 focus:ring-violet-500/20 placeholder-[#94A3B8]"
          disabled={isQuerying}
          onKeyDown={(e) => {
            if (e.key === 'Enter') send(value);
          }}
        />
        <button
          onClick={() => send(value)}
          disabled={isQuerying}
          className="bg-violet-500 hover:bg-violet-600 text-white p-2.5 rounded-xl transition-all disabled:opacity-50"
        >
          <ArrowUp size={16} />
        </button>
      </GlassCard>
      {suggestedQuestions.length > 0 && (
        <div className="flex flex-wrap gap-2 pt-1">
          {suggestedQuestions.map((q, idx) => (
            <button
              key={idx}
              onClick={() => send(q)}
              disabled={isQuerying}
              className="text-xs bg-white hover:bg-violet-50 hover:text-violet-600 text-[#64748B] hover:border-violet-200 px-3 py-1.5 rounded-lg border border-[#E2E8F0] transition-all"
            >
              {q}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
