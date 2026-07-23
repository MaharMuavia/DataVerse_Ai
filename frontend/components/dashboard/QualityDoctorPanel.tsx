'use client';

import { useState } from 'react';
import { Stethoscope, CheckCircle2, Loader2 } from 'lucide-react';
import { GlassCard } from './GlassCard';
import type { QualityDiagnosis } from '@/lib/dataverse-api';

const SEVERITY_STYLES: Record<string, string> = {
  high: 'bg-red-50 text-red-600 border-red-100',
  medium: 'bg-amber-50 text-amber-600 border-amber-100',
  low: 'bg-slate-50 text-slate-500 border-slate-200',
};

export function QualityDoctorPanel({
  diagnosis,
  onApply,
  isApplying,
}: {
  diagnosis: QualityDiagnosis;
  onApply: (fixIds: string[]) => void;
  isApplying: boolean;
}) {
  const issues = diagnosis?.issues ?? [];
  const [selected, setSelected] = useState<Set<string>>(() => new Set(issues.map((i) => i.id)));

  if (!issues.length) {
    return (
      <div className="space-y-2">
        <h3 className="flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wider text-[#64748B]">
          <Stethoscope size={13} className="text-violet-500" /> Data Quality Doctor
        </h3>
        <GlassCard className="flex items-center gap-2 border-[#E2E8F0] bg-white p-4 text-sm text-emerald-600">
          <CheckCircle2 size={16} /> No quality issues detected. Your data is clean.
        </GlassCard>
      </div>
    );
  }

  const toggle = (id: string) =>
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between gap-3">
        <h3 className="flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wider text-[#64748B]">
          <Stethoscope size={13} className="text-violet-500" /> Data Quality Doctor: {issues.length} issue
          {issues.length > 1 ? 's' : ''}
        </h3>
        <button
          onClick={() => onApply([...selected])}
          disabled={isApplying || selected.size === 0}
          className="flex items-center gap-1 rounded-lg bg-violet-500 px-3 py-1.5 text-[11px] font-semibold text-white transition-all hover:bg-violet-600 disabled:opacity-50"
        >
          {isApplying ? <Loader2 size={12} className="animate-spin" /> : <CheckCircle2 size={12} />}
          {isApplying ? 'Cleaning…' : `Apply ${selected.size} fix${selected.size === 1 ? '' : 'es'}`}
        </button>
      </div>
      <GlassCard className="divide-y divide-[#F1F5F9] border-[#E2E8F0] bg-white">
        {issues.map((issue) => (
          <label key={issue.id} className="flex cursor-pointer items-start gap-3 p-3">
            <input
              type="checkbox"
              checked={selected.has(issue.id)}
              onChange={() => toggle(issue.id)}
              disabled={isApplying}
              className="mt-0.5 accent-violet-500"
            />
            <div className="min-w-0 flex-1">
              <div className="flex items-center gap-2">
                <span className={`rounded border px-1.5 py-0.5 text-[9px] font-bold uppercase ${SEVERITY_STYLES[issue.severity] || SEVERITY_STYLES.low}`}>
                  {issue.severity}
                </span>
                <span className="text-xs font-medium text-[#334155]">{issue.issue}</span>
              </div>
              <div className="mt-1 flex flex-wrap items-center gap-1.5 text-[11px] text-violet-600">
                <CheckCircle2 size={11} /> {issue.fix}
                {issue.impact?.before && issue.impact?.after && (
                  <span className="text-[#94A3B8]">({issue.impact.before} → {issue.impact.after})</span>
                )}
              </div>
            </div>
          </label>
        ))}
      </GlassCard>
    </div>
  );
}
