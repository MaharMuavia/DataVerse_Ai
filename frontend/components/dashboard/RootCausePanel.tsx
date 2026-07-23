'use client';

import { useState } from 'react';
import { Search, ChevronDown, ChevronRight, TrendingDown, TrendingUp } from 'lucide-react';
import { GlassCard } from './GlassCard';
import { formatNumber } from '@/lib/dashboard-format';
import type { RootCauseResult } from '@/lib/dataverse-api';

/**
 * Root-Cause Investigator: renders the deterministic multi-step investigation
 * behind a "why did X change?" answer, including the trace, ranked drivers, and
 * price-vs-volume split. Every step exposes its provenance receipt on demand.
 */
export function RootCausePanel({ result }: { result: RootCauseResult }) {
  const [openReceipt, setOpenReceipt] = useState<number | null>(null);
  const [showAllSteps, setShowAllSteps] = useState(false);

  if (result.status !== 'complete') {
    return null;
  }

  const isDrop = (result.delta ?? 0) < 0;
  const steps = result.steps ?? [];
  const visibleSteps = showAllSteps ? steps : steps.slice(0, 3);
  const drivers = (result.drivers ?? []).slice(0, 5);
  const pv = result.price_volume;

  return (
    <GlassCard className="p-6 bg-white border-[#E2E8F0] space-y-4">
      <div className="flex items-center gap-3">
        <div className={`w-8 h-8 rounded-lg flex items-center justify-center ${isDrop ? 'bg-rose-50 text-rose-500' : 'bg-emerald-50 text-emerald-600'}`}>
          <Search size={16} />
        </div>
        <div>
          <h3 className="text-sm font-semibold text-[#0F172A]">Root-Cause Investigation</h3>
          <p className="text-[10px] text-[#64748B]">
            {result.metric} · {result.period_a} → {result.period_b} · every step is receipt-backed
          </p>
        </div>
        <span className={`ml-auto flex items-center gap-1 text-xs font-bold ${isDrop ? 'text-rose-600' : 'text-emerald-600'}`}>
          {isDrop ? <TrendingDown size={14} /> : <TrendingUp size={14} />}
          {formatNumber(result.delta ?? 0)}
          {typeof result.pct_change === 'number' ? ` (${result.pct_change > 0 ? '+' : ''}${result.pct_change.toFixed(1)}%)` : ''}
        </span>
      </div>

      {/* Investigation trace */}
      <ol className="space-y-2">
        {visibleSteps.map((step, index) => (
          <li key={index} className="rounded-lg border border-[#E2E8F0] bg-[#F8FAFC] px-3 py-2">
            <div className="flex items-start gap-2">
              <span className="mt-0.5 flex h-4 w-4 shrink-0 items-center justify-center rounded-full bg-violet-100 text-[9px] font-bold text-violet-600">
                {index + 1}
              </span>
              <div className="min-w-0">
                <p className="text-[11px] font-semibold text-[#0F172A]">{step.action}</p>
                <p className="text-[11px] text-[#334155]">{step.finding}</p>
                {step.receipt && (
                  <button
                    onClick={() => setOpenReceipt(openReceipt === index ? null : index)}
                    className="mt-1 flex items-center gap-1 text-[10px] font-semibold text-violet-600 hover:text-violet-700"
                  >
                    {openReceipt === index ? <ChevronDown size={11} /> : <ChevronRight size={11} />}
                    Show the math
                  </button>
                )}
                {step.receipt && openReceipt === index && (
                  <p className="mt-1 rounded-md border border-violet-100 bg-violet-50/60 px-2 py-1 font-mono text-[10px] text-[#334155]">
                    {step.receipt.formula_plain}
                  </p>
                )}
              </div>
            </div>
          </li>
        ))}
      </ol>
      {steps.length > 3 && (
        <button
          onClick={() => setShowAllSteps(!showAllSteps)}
          className="text-[11px] font-semibold text-violet-600 hover:text-violet-700"
        >
          {showAllSteps ? 'Show fewer steps' : `Show all ${steps.length} steps`}
        </button>
      )}

      {/* Ranked drivers */}
      {drivers.length > 0 && (
        <div>
          <h4 className="mb-2 text-[10px] font-bold uppercase tracking-wider text-[#64748B]">
            Drivers by {result.primary_dimension}
          </h4>
          <div className="space-y-1.5">
            {drivers.map((driver) => {
              const share = typeof driver.share_of_delta === 'number' ? driver.share_of_delta : null;
              const width = share === null ? 0 : Math.min(Math.abs(share) * 100, 100);
              const offsetting = share !== null && share < 0;
              return (
                <div key={driver.value} className="flex items-center gap-2 text-[11px]">
                  <span className="w-28 truncate font-semibold text-[#0F172A]" title={driver.value}>{driver.value}</span>
                  <div className="h-2 flex-1 overflow-hidden rounded-full bg-[#E2E8F0]">
                    <div
                      className={`h-full rounded-full ${offsetting ? 'bg-emerald-400' : isDrop ? 'bg-rose-400' : 'bg-emerald-400'}`}
                      style={{ width: `${width}%` }}
                    />
                  </div>
                  <span className="w-20 text-right font-mono text-[#334155]">{formatNumber(driver.contribution)}</span>
                  <span className="w-14 text-right font-mono text-[#64748B]">
                    {share === null ? 'N/A' : `${(share * 100).toFixed(0)}%`}
                  </span>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Price vs volume split */}
      {pv && (
        <div className="flex flex-wrap gap-2">
          {[
            { label: 'Price effect', value: pv.price_effect },
            { label: 'Volume effect', value: pv.volume_effect },
            { label: 'Mix effect', value: pv.mix_effect },
          ].map((item) => (
            <span key={item.label} className="rounded-md border border-[#E2E8F0] bg-[#F8FAFC] px-2 py-1 text-[10px]">
              <span className="text-[#64748B]">{item.label}: </span>
              <span className={`font-mono font-semibold ${item.value < 0 ? 'text-rose-600' : 'text-emerald-600'}`}>
                {formatNumber(item.value)}
              </span>
            </span>
          ))}
        </div>
      )}
    </GlassCard>
  );
}
