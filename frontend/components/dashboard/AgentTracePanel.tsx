'use client';

import { useState } from 'react';
import { Bot, ChevronDown, ChevronRight, Wrench } from 'lucide-react';
import { GlassCard } from './GlassCard';
import type { AgentTraceStep } from '@/lib/dataverse-api';

/**
 * Agent Trace: the plan→act→observe loop the LLM agent ran to answer the
 * question. Thoughts come from the LLM; every observation is a deterministic
 * tool result computed in pandas — the agent plans, it never computes.
 */
export function AgentTracePanel({ trace }: { trace: AgentTraceStep[] }) {
  const [openStep, setOpenStep] = useState<number | null>(null);

  if (!trace.length) return null;

  return (
    <GlassCard className="p-6 bg-white border-[#E2E8F0] space-y-3">
      <div className="flex items-center gap-3">
        <div className="w-8 h-8 rounded-lg bg-blue-50 flex items-center justify-center text-blue-500">
          <Bot size={16} />
        </div>
        <div>
          <h3 className="text-sm font-semibold text-[#0F172A]">Agent Investigation</h3>
          <p className="text-[10px] text-[#64748B]">
            The agent planned {trace.length} tool call{trace.length === 1 ? '' : 's'} — all numbers computed deterministically
          </p>
        </div>
      </div>
      <ol className="space-y-2">
        {trace.map((step, index) => (
          <li key={index} className="rounded-lg border border-[#E2E8F0] bg-[#F8FAFC] px-3 py-2">
            {step.thought && (
              <p className="text-[11px] italic text-[#64748B]">&ldquo;{step.thought}&rdquo;</p>
            )}
            <div className="mt-1 flex items-center gap-1.5 text-[11px] font-semibold text-[#0F172A]">
              <Wrench size={11} className="text-blue-500" />
              <span className="font-mono">{step.tool}</span>
              {step.args && Object.keys(step.args).length > 0 && (
                <span className="truncate font-mono text-[10px] text-[#64748B]">
                  ({Object.entries(step.args).map(([key, value]) => `${key}=${String(value)}`).join(', ')})
                </span>
              )}
            </div>
            <button
              onClick={() => setOpenStep(openStep === index ? null : index)}
              className="mt-1 flex items-center gap-1 text-[10px] font-semibold text-blue-600 hover:text-blue-700"
            >
              {openStep === index ? <ChevronDown size={11} /> : <ChevronRight size={11} />}
              {openStep === index ? 'Hide observation' : 'Show observation'}
            </button>
            {openStep === index && (
              <pre className="mt-1 max-h-40 overflow-auto rounded-md border border-blue-100 bg-blue-50/50 px-2 py-1 font-mono text-[10px] text-[#334155]">
                {JSON.stringify(step.observation, null, 2)}
              </pre>
            )}
          </li>
        ))}
      </ol>
    </GlassCard>
  );
}
