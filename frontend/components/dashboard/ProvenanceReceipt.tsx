'use client';

import { ShieldCheck } from 'lucide-react';
import { formatCell } from '@/lib/dashboard-format';
import type { KpiProvenance } from '@/lib/dataverse-api';

export function ProvenanceReceipt({ prov }: { prov: KpiProvenance }) {
  const columns = prov.sample_rows?.length ? Object.keys(prov.sample_rows[0]) : [];
  return (
    <div className="rounded-lg border border-violet-100 bg-violet-50/40 p-2.5 text-[11px] text-[#475569]">
      <p className="font-medium text-[#334155]">{prov.formula_plain}</p>
      <div className="mt-1.5 flex flex-wrap gap-1">
        <span className="rounded bg-white px-1.5 py-0.5 font-mono text-[10px] text-violet-700 border border-violet-100">{prov.operation}</span>
        {prov.source_columns.map((c) => (
          <span key={c} className="rounded bg-white px-1.5 py-0.5 font-mono text-[10px] text-[#64748B] border border-[#E2E8F0]">{c}</span>
        ))}
      </div>
      {columns.length > 0 && (
        <div className="mt-2 overflow-x-auto">
          <table className="w-full text-left text-[10px]">
            <thead>
              <tr>
                {columns.map((k) => (
                  <th key={k} className="pr-3 pb-1 font-semibold text-[#94A3B8]">{k}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {prov.sample_rows.map((row, i) => (
                <tr key={i} className="border-t border-violet-100/60">
                  {columns.map((k) => (
                    <td key={k} className="pr-3 py-0.5 text-[#475569]">{formatCell(row[k])}</td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      <p className="mt-2 flex items-center gap-1 text-[10px] text-emerald-600">
        <ShieldCheck size={11} /> Verified deterministically from your rows
      </p>
    </div>
  );
}
