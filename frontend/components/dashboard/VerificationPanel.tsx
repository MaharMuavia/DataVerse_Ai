'use client';

import { useState } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import { ShieldCheck, Download, ChevronDown } from 'lucide-react';
import { GlassCard } from './GlassCard';
import { ProvenanceReceipt } from './ProvenanceReceipt';
import { formatCell } from '@/lib/dashboard-format';
import type { AuditEntry } from '@/lib/dataverse-api';

const CATEGORY_LABELS: Record<string, string> = {
  kpi: 'KPIs',
  eda: 'Statistics',
  correlation: 'Correlations',
  trend: 'Trends',
  model: 'Model',
};

export function VerificationPanel({ audit }: { audit: AuditEntry[] }) {
  const [openKey, setOpenKey] = useState<string | null>(null);
  if (!audit?.length) return null;

  const counts = audit.reduce<Record<string, number>>((acc, entry) => {
    acc[entry.category] = (acc[entry.category] || 0) + 1;
    return acc;
  }, {});

  const download = () => {
    const blob = new Blob([JSON.stringify(audit, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `audit-log-${Date.now()}.json`;
    link.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between gap-3">
        <h3 className="flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wider text-[#64748B]">
          <ShieldCheck size={13} className="text-emerald-500" /> Verification — {audit.length} numbers verified
        </h3>
        <button
          onClick={download}
          className="flex items-center gap-1 rounded-lg border border-violet-200 px-2.5 py-1 text-[11px] font-semibold text-violet-600 transition-all hover:bg-violet-50 hover:text-violet-700"
        >
          <Download size={12} /> Download audit log
        </button>
      </div>

      <div className="flex flex-wrap gap-1.5">
        {Object.entries(counts).map(([cat, n]) => (
          <span key={cat} className="rounded-full border border-violet-100 bg-violet-50 px-2 py-0.5 text-[10px] font-semibold text-violet-700">
            {CATEGORY_LABELS[cat] || cat}: {n}
          </span>
        ))}
      </div>

      <GlassCard className="divide-y divide-[#F1F5F9] border-[#E2E8F0] bg-white">
        {audit.map((entry, i) => {
          const key = `${entry.metric_key || entry.category}-${i}`;
          const isOpen = openKey === key;
          return (
            <div key={key} className="p-3">
              <button
                onClick={() => setOpenKey(isOpen ? null : key)}
                className="flex w-full items-center justify-between gap-2 text-left"
              >
                <span className="flex min-w-0 items-center gap-2">
                  <span className="shrink-0 rounded bg-[#F1F5F9] px-1.5 py-0.5 text-[9px] font-bold uppercase text-[#64748B]">
                    {CATEGORY_LABELS[entry.category] || entry.category}
                  </span>
                  <span className="truncate text-xs font-medium text-[#334155]">{entry.label || entry.metric_key}</span>
                </span>
                <span className="flex shrink-0 items-center gap-1.5">
                  <span className="text-xs font-bold text-[#0F172A]">{formatCell(entry.value)}</span>
                  <ChevronDown size={13} className={`text-[#94A3B8] transition-transform ${isOpen ? 'rotate-180' : ''}`} />
                </span>
              </button>
              <AnimatePresence initial={false}>
                {isOpen && (
                  <motion.div
                    initial={{ height: 0, opacity: 0 }}
                    animate={{ height: 'auto', opacity: 1 }}
                    exit={{ height: 0, opacity: 0 }}
                    transition={{ duration: 0.18 }}
                    className="overflow-hidden"
                  >
                    <div className="mt-2">
                      <ProvenanceReceipt prov={entry} />
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>
            </div>
          );
        })}
      </GlassCard>
    </div>
  );
}
