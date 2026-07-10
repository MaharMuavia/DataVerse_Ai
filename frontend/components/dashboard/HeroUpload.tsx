'use client';

import { useRef, useState } from 'react';
import { Sparkles, Paperclip, ArrowUp, FileSpreadsheet, Loader2, AlertTriangle, ShieldCheck } from 'lucide-react';
import type { RecentDataset } from '@/lib/dataverse-api';

const EXTS = ['.csv', '.xlsx', '.xls'];
const EXAMPLES = [
  'What are my total sales?',
  'Top selling products',
  'Sales by region',
  'Most profitable category',
  'Generate a full report',
];

function greeting(): string {
  const h = new Date().getHours();
  if (h < 12) return 'Good morning';
  if (h < 18) return 'Good afternoon';
  return 'Good evening';
}

export function HeroUpload({
  onUpload,
  isUploading,
  uploadStatus,
  backendStatus,
  recentDatasets,
  onSelectRecent,
  userName,
}: {
  onUpload: (file: File) => void;
  isUploading: boolean;
  uploadStatus: string | null;
  backendStatus: 'checking' | 'connected' | 'disconnected';
  recentDatasets: RecentDataset[];
  onSelectRecent: (sessionId: string) => void;
  userName?: string;
}) {
  const [drag, setDrag] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const disconnected = backendStatus === 'disconnected';
  const pick = () => {
    if (!disconnected && !isUploading) inputRef.current?.click();
  };
  const validate = (file?: File) => {
    if (!file) return;
    if (!EXTS.some((e) => file.name.toLowerCase().endsWith(e))) {
      setErr(`Only ${EXTS.join(', ')} files are supported.`);
      return;
    }
    setErr(null);
    onUpload(file);
  };

  return (
    <div
      onDragOver={(e) => { e.preventDefault(); if (!isUploading) setDrag(true); }}
      onDragLeave={(e) => { e.preventDefault(); setDrag(false); }}
      onDrop={(e) => { e.preventDefault(); setDrag(false); if (!isUploading) validate(e.dataTransfer.files?.[0]); }}
      className="flex min-h-[68vh] flex-col items-center justify-center px-4 text-center"
    >
      <div className="mb-7">
        <div className="mx-auto mb-4 grid h-14 w-14 place-items-center rounded-2xl bg-gradient-to-br from-violet-500 to-blue-500 shadow-lg shadow-violet-500/25">
          <Sparkles size={26} className="text-white" />
        </div>
        <h1 className="text-3xl font-bold tracking-tight text-[#0F172A] md:text-4xl">
          {greeting()}{userName ? `, ${userName}` : ''}
        </h1>
        <p className="mx-auto mt-2.5 max-w-xl text-[15px] leading-relaxed text-[#64748B]">
          Upload a dataset and ask anything — DataVerse analyzes it like a data analyst, and proves every number.
        </p>
      </div>

      <div
        className={`w-full max-w-2xl rounded-[28px] border bg-white shadow-[0_4px_24px_rgba(15,23,42,0.06)] transition-all ${
          drag ? 'border-violet-400 ring-4 ring-violet-100' : 'border-[#E2E8F0]'
        }`}
      >
        {isUploading ? (
          <div className="flex items-center gap-3 px-5 py-5 text-left">
            <Loader2 size={20} className="animate-spin text-violet-500" />
            <div>
              <p className="text-sm font-semibold text-[#0F172A]">Processing your dataset…</p>
              <p className="mt-0.5 text-xs text-[#64748B]">{uploadStatus || 'Profiling · EDA · metrics · modeling · narration'}</p>
            </div>
          </div>
        ) : (
          <div className="flex items-center gap-2 px-3 py-2.5">
            <button onClick={pick} disabled={disconnected} className="grid h-10 w-10 shrink-0 place-items-center rounded-full text-[#64748B] transition hover:bg-[#F1F5F9] hover:text-violet-600 disabled:opacity-40" title="Attach a CSV or Excel file">
              <Paperclip size={18} />
            </button>
            <button onClick={pick} disabled={disconnected} className="min-w-0 flex-1 truncate text-left text-[15px] text-[#94A3B8] transition hover:text-[#64748B]">
              Drop a CSV / Excel file here, or click to upload…
            </button>
            <button onClick={pick} disabled={disconnected} className="grid h-10 w-10 shrink-0 place-items-center rounded-2xl bg-gradient-to-r from-violet-500 to-blue-500 text-white shadow-sm transition hover:brightness-110 active:scale-95 disabled:opacity-50" title="Upload a file">
              <ArrowUp size={18} />
            </button>
            <input
              ref={inputRef}
              type="file"
              accept={EXTS.join(',')}
              className="hidden"
              onChange={(e) => { validate(e.target.files?.[0]); e.target.value = ''; }}
            />
          </div>
        )}
      </div>

      {err && <p className="mt-3 flex items-center gap-1.5 text-xs text-rose-600"><AlertTriangle size={12} /> {err}</p>}
      {disconnected && <p className="mt-3 flex items-center gap-1.5 text-xs text-rose-600"><AlertTriangle size={12} /> Backend not reachable on port 8000.</p>}

      {!isUploading && (
        <div className="mt-5 flex flex-wrap items-center justify-center gap-2">
          {EXAMPLES.map((ex) => (
            <button
              key={ex}
              onClick={pick}
              title="Upload a dataset to ask this"
              className="rounded-full border border-[#E2E8F0] bg-white px-3.5 py-1.5 text-[13px] text-[#475569] transition hover:border-violet-200 hover:bg-violet-50 hover:text-violet-700"
            >
              {ex}
            </button>
          ))}
        </div>
      )}

      {!isUploading && recentDatasets.length > 0 && (
        <div className="mt-9 w-full max-w-2xl">
          <p className="mb-2.5 text-[11px] font-semibold uppercase tracking-wider text-[#94A3B8]">Recent datasets</p>
          <div className="flex flex-wrap justify-center gap-2">
            {recentDatasets.slice(0, 5).map((r) => (
              <button
                key={r.id}
                onClick={() => onSelectRecent(r.session_id)}
                className="flex items-center gap-2 rounded-xl border border-[#E2E8F0] bg-white px-3 py-1.5 text-[13px] text-[#334155] transition hover:bg-[#F8FAFC]"
              >
                <FileSpreadsheet size={14} className="text-violet-500" />
                <span className="max-w-[180px] truncate">{r.filename}</span>
                <span className="text-[#94A3B8]">· {r.row_count} rows</span>
              </button>
            ))}
          </div>
        </div>
      )}

      <p className="mt-8 flex items-center gap-1.5 text-[11px] text-[#94A3B8]">
        <ShieldCheck size={12} className="text-emerald-500" /> Every number is computed deterministically and verifiable.
      </p>
    </div>
  );
}
