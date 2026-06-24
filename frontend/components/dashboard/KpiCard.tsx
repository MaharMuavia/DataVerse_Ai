'use client';

import { useState } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import { ChevronDown, ShieldCheck, ArrowRight } from 'lucide-react';
import { GlassCard } from './GlassCard';
import { ProvenanceReceipt } from './ProvenanceReceipt';
import { formatCell } from '@/lib/dashboard-format';
import type { Kpi } from '@/lib/dataverse-api';

export function KpiCard({ kpi, onDrillDown }: { kpi: Kpi; onDrillDown?: (kpi: Kpi) => void }) {
  const [open, setOpen] = useState(false);
  const prov = kpi.provenance;

  return (
    <GlassCard className="p-4 bg-white border-[#E2E8F0]">
      <div className="text-[10px] text-[#64748B] uppercase font-semibold tracking-wider truncate">{kpi.label}</div>
      <div className="text-xl font-extrabold text-[#0F172A] mt-2 tracking-tight">{formatCell(kpi.value)}</div>

      {prov && (
        <>
          <button
            onClick={() => setOpen((v) => !v)}
            className="mt-2 flex items-center gap-1 text-[11px] font-semibold text-violet-600 hover:text-violet-700"
          >
            <ShieldCheck size={12} /> Show the math
            <ChevronDown size={12} className={`transition-transform ${open ? 'rotate-180' : ''}`} />
          </button>

          <AnimatePresence initial={false}>
            {open && (
              <motion.div
                initial={{ height: 0, opacity: 0 }}
                animate={{ height: 'auto', opacity: 1 }}
                exit={{ height: 0, opacity: 0 }}
                transition={{ duration: 0.18 }}
                className="overflow-hidden"
              >
                <div className="mt-2">
                  <ProvenanceReceipt prov={prov} />
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </>
      )}

      {onDrillDown && (
        <button
          onClick={() => onDrillDown(kpi)}
          className="mt-2 ml-auto flex items-center gap-1 text-[11px] font-semibold text-[#64748B] hover:text-violet-600"
          title="Ask a verified follow-up about this number"
        >
          Ask why <ArrowRight size={11} />
        </button>
      )}
    </GlassCard>
  );
}
