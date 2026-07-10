'use client';

import { useState } from 'react';
import { Sparkles, Loader2, ArrowUpRight, ArrowDownRight, Minus } from 'lucide-react';
import { GlassCard } from './GlassCard';
import { formatCell } from '@/lib/dashboard-format';
import type { WhatIfResult } from '@/lib/dataverse-api';

export function WhatIfPanel({
  columns,
  onSimulate,
}: {
  columns: string[];
  onSimulate: (column: string, pct: number) => Promise<WhatIfResult>;
}) {
  const [column, setColumn] = useState(columns[0] ?? '');
  const [pct, setPct] = useState(10);
  const [result, setResult] = useState<WhatIfResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!columns.length) return null;

  const run = async () => {
    setLoading(true);
    setError(null);
    try {
      setResult(await onSimulate(column || columns[0], pct));
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Simulation failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-3">
      <h3 className="flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wider text-[#64748B]">
        <Sparkles size={13} className="text-violet-500" /> Verified What-If Simulator
      </h3>
      <GlassCard className="space-y-3 border-[#E2E8F0] bg-white p-4">
        <p className="text-[12px] text-[#475569]">
          Adjust a numeric lever and recompute the KPIs deterministically — every hypothetical number stays verifiable
          with its own receipt.
        </p>
        <div className="flex flex-wrap items-center gap-2">
          <select
            value={column}
            onChange={(e) => setColumn(e.target.value)}
            disabled={loading}
            className="rounded-lg border border-[#E2E8F0] bg-[#F8FAFC] px-2.5 py-1.5 text-sm text-[#0F172A] focus:outline-none focus:ring-2 focus:ring-violet-500/20"
          >
            {columns.map((c) => (
              <option key={c} value={c}>{c}</option>
            ))}
          </select>
          <div className="flex items-center gap-1 rounded-lg border border-[#E2E8F0] bg-[#F8FAFC] px-1.5 py-1">
            <button onClick={() => setPct((p) => p - 5)} disabled={loading} className="px-1.5 text-[#64748B] hover:text-violet-600">-</button>
            <span className={`w-14 text-center text-sm font-semibold ${pct >= 0 ? 'text-emerald-600' : 'text-red-600'}`}>
              {pct > 0 ? '+' : ''}{pct}%
            </span>
            <button onClick={() => setPct((p) => p + 5)} disabled={loading} className="px-1.5 text-[#64748B] hover:text-violet-600">+</button>
          </div>
          <button
            onClick={run}
            disabled={loading}
            className="flex items-center gap-1 rounded-lg bg-violet-500 px-3 py-1.5 text-[11px] font-semibold text-white transition-all hover:bg-violet-600 disabled:opacity-50"
          >
            {loading ? <Loader2 size={12} className="animate-spin" /> : <Sparkles size={12} />} Simulate
          </button>
        </div>
        {error && <p className="text-[12px] text-red-600">{error}</p>}
        {result && (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-[12px]">
              <thead>
                <tr className="text-[10px] uppercase tracking-wider text-[#94A3B8]">
                  <th className="pb-1 pr-4">KPI</th>
                  <th className="pb-1 pr-4">Baseline</th>
                  <th className="pb-1 pr-4">What-if ({result.pct_change > 0 ? '+' : ''}{result.pct_change}% {result.column})</th>
                  <th className="pb-1">Change</th>
                </tr>
              </thead>
              <tbody>
                {result.deltas.map((d) => {
                  const up = typeof d.pct === 'number' && d.pct > 0;
                  const down = typeof d.pct === 'number' && d.pct < 0;
                  return (
                    <tr key={d.label} className="border-t border-[#F1F5F9]">
                      <td className="py-1 pr-4 font-medium text-[#334155]">{d.label}</td>
                      <td className="py-1 pr-4 text-[#64748B]">{formatCell(d.baseline)}</td>
                      <td className="py-1 pr-4 font-semibold text-[#0F172A]">{formatCell(d.scenario)}</td>
                      <td className={`py-1 font-semibold ${up ? 'text-emerald-600' : down ? 'text-red-600' : 'text-[#94A3B8]'}`}>
                        <span className="inline-flex items-center gap-0.5">
                          {up ? <ArrowUpRight size={12} /> : down ? <ArrowDownRight size={12} /> : <Minus size={12} />}
                          {typeof d.pct === 'number' ? `${d.pct > 0 ? '+' : ''}${d.pct}%` : '—'}
                        </span>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
            <p className="mt-2 text-[10px] text-emerald-600">
              Hypothetical KPIs recomputed deterministically on the modified data — each carries its own receipt.
            </p>
          </div>
        )}
      </GlassCard>
    </div>
  );
}
