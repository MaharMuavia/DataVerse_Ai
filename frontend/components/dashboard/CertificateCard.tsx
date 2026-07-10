'use client';

import { useState } from 'react';
import { ShieldCheck, BadgeCheck, Loader2, AlertTriangle, Fingerprint } from 'lucide-react';
import { GlassCard } from './GlassCard';
import type { VerificationCertificate, VerifyResult } from '@/lib/dataverse-api';

const short = (hash?: string) => (hash ? `${hash.slice(0, 10)}…${hash.slice(-6)}` : '—');

export function CertificateCard({
  certificate,
  onVerify,
}: {
  certificate: VerificationCertificate;
  onVerify: (cert: VerificationCertificate) => Promise<VerifyResult>;
}) {
  const [result, setResult] = useState<VerifyResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const verify = async () => {
    setLoading(true);
    setError(null);
    try {
      setResult(await onVerify(certificate));
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Verification failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-3">
      <h3 className="flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wider text-[#64748B]">
        <BadgeCheck size={13} className="text-emerald-500" /> Reproducibility Certificate
      </h3>
      <GlassCard className="space-y-3 border-[#E2E8F0] bg-white p-4">
        <p className="text-[12px] text-[#475569]">
          {certificate.verified_numbers} numbers are cryptographically fingerprinted ({certificate.algorithm}).
          Re-verify to prove they reproduce <span className="font-semibold text-[#334155]">exactly</span> from your raw
          data — and detect any tampering.
        </p>
        <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
          <div className="rounded-lg border border-[#E2E8F0] bg-[#F8FAFC] p-2.5">
            <div className="flex items-center gap-1 text-[10px] font-semibold uppercase tracking-wider text-[#94A3B8]">
              <Fingerprint size={11} /> Data fingerprint
            </div>
            <div className="mt-1 break-all font-mono text-[11px] text-[#334155]">{short(certificate.data_fingerprint)}</div>
          </div>
          <div className="rounded-lg border border-[#E2E8F0] bg-[#F8FAFC] p-2.5">
            <div className="flex items-center gap-1 text-[10px] font-semibold uppercase tracking-wider text-[#94A3B8]">
              <Fingerprint size={11} /> Results fingerprint
            </div>
            <div className="mt-1 break-all font-mono text-[11px] text-[#334155]">{short(certificate.results_fingerprint)}</div>
          </div>
        </div>
        <div className="flex flex-wrap items-center gap-3">
          <button
            onClick={verify}
            disabled={loading}
            className="flex items-center gap-1 rounded-lg bg-emerald-500 px-3 py-1.5 text-[11px] font-semibold text-white transition-all hover:bg-emerald-600 disabled:opacity-50"
          >
            {loading ? <Loader2 size={12} className="animate-spin" /> : <ShieldCheck size={12} />}
            {loading ? 'Re-running on your data…' : 'Re-verify against data'}
          </button>
          {result && (
            <span className={`flex items-center gap-1 text-[12px] font-semibold ${result.verified ? 'text-emerald-600' : 'text-red-600'}`}>
              {result.verified ? <BadgeCheck size={14} /> : <AlertTriangle size={14} />}
              {result.verified
                ? `Reproduced exactly — ${result.verified_numbers}/${result.verified_numbers} numbers match`
                : `Mismatch — data ${result.data_match ? 'OK' : 'changed'}, results ${result.results_match ? 'OK' : 'changed'}`}
            </span>
          )}
          {error && <span className="text-[12px] text-red-600">{error}</span>}
        </div>
      </GlassCard>
    </div>
  );
}
