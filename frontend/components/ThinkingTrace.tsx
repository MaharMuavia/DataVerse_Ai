'use client';

import React from 'react';
import { AnimatePresence, motion } from 'motion/react';
import { AlertTriangle, CheckCircle2, Loader2 } from 'lucide-react';
import type { ProgressEvent } from '@/lib/dataverse-api';

export type ThinkingStep = {
  stage: string;
  label: string;
  status: 'running' | 'done' | 'error';
  elapsed_ms?: number;
  detail?: string;
};

/**
 * Reduce a sequence of SSE progress events into a stable ordered list of steps.
 *
 * The reducer is idempotent: replaying the same events produces the same list.
 * Stages keep first-seen order; the latest status/elapsed_ms/detail wins.
 */
export function reduceProgress(steps: ThinkingStep[], event: ProgressEvent): ThinkingStep[] {
  if (event.stage.startsWith('_')) return steps;
  const next = [...steps];
  const existing = next.findIndex((step) => step.stage === event.stage);
  const normalized: ThinkingStep = {
    stage: event.stage,
    label: event.label || titleize(event.stage),
    status: event.status === 'ping' ? 'running' : event.status,
    elapsed_ms: event.elapsed_ms,
    detail: event.detail,
  };
  if (existing === -1) {
    next.push(normalized);
  } else {
    const previous = next[existing];
    next[existing] = {
      ...previous,
      ...normalized,
      // Preserve elapsed_ms from the done event over a stale running one
      elapsed_ms: normalized.elapsed_ms ?? previous.elapsed_ms,
      detail: normalized.detail ?? previous.detail,
    };
  }
  return next;
}

function titleize(stage: string): string {
  return stage.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());
}

function formatElapsed(ms?: number): string {
  if (typeof ms !== 'number') return '';
  if (ms < 1000) return `${ms} ms`;
  return `${(ms / 1000).toFixed(ms < 10_000 ? 1 : 0)}s`;
}

type Props = {
  steps: ThinkingStep[];
  title?: string;
  /** Show a subtle pulse on the latest running step. Defaults to true. */
  active?: boolean;
};

export function ThinkingTrace({ steps, title = 'Thinking', active = true }: Props) {
  if (steps.length === 0) {
    return (
      <div className="rounded-lg border border-[#E2E8F0] bg-white/80 p-3 text-xs text-[#64748B] flex items-center gap-2">
        <Loader2 size={14} className="animate-spin text-violet-500" />
        Waiting for the backend to start working…
      </div>
    );
  }
  return (
    <div className="rounded-lg border border-[#E2E8F0] bg-white/80 p-3">
      <div className="flex items-center gap-2 mb-2">
        <Loader2
          size={12}
          className={active ? 'animate-spin text-violet-500' : 'text-emerald-500'}
        />
        <span className="text-[10px] font-semibold uppercase tracking-wider text-[#64748B]">
          {title}
        </span>
      </div>
      <ul className="space-y-1.5">
        <AnimatePresence initial={false}>
          {steps.map((step) => (
            <motion.li
              key={step.stage}
              initial={{ opacity: 0, y: -4 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.18 }}
              className="flex items-start gap-2 text-xs"
            >
              <span className="mt-0.5 shrink-0">
                {step.status === 'done' && (
                  <CheckCircle2 size={14} className="text-emerald-500" />
                )}
                {step.status === 'error' && (
                  <AlertTriangle size={14} className="text-rose-500" />
                )}
                {step.status === 'running' && (
                  <Loader2 size={14} className="animate-spin text-violet-500" />
                )}
              </span>
              <span className="flex-1 min-w-0">
                <span
                  className={
                    step.status === 'error'
                      ? 'text-rose-600 font-medium'
                      : 'text-[#0F172A] font-medium'
                  }
                >
                  {step.label}
                </span>
                {step.detail && (
                  <span className="text-[#64748B] font-normal"> · {step.detail}</span>
                )}
              </span>
              {step.elapsed_ms !== undefined && step.status !== 'running' && (
                <span className="text-[10px] text-[#94A3B8] font-mono shrink-0">
                  {formatElapsed(step.elapsed_ms)}
                </span>
              )}
            </motion.li>
          ))}
        </AnimatePresence>
      </ul>
    </div>
  );
}
